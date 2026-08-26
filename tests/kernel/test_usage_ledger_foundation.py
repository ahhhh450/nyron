"""Acceptance tests for ARE-GATE-6 Track A / Task 090: UsageFact and
UsageAdjustmentFact ledger foundation.

Maps to the Task's Reviewer-Blocking Tests list. This slice does not
implement BudgetReservation settlement transitions or Recovery Owner
state; tests here only exercise immutable-fact commit, stable source
dedupe, fail-closed conflict detection, and append-only correction.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nyron_kernel.accounting import (
    AccountingScope,
    AccountingScopeResolver,
    UsageAdjustmentFactRequest,
    UsageFactRequest,
    UsageLedger,
    UsageLedgerError,
    compute_ancestry_hash,
)
from nyron_kernel.store import SQLiteStore


GRAPH = "graph:usage@1"
SCOPE = "accounting:usage/root"
OTHER_SCOPE = "accounting:usage/other"


def scope(accounting_scope_ref: str) -> AccountingScope:
    return AccountingScope(
        accounting_scope_ref=accounting_scope_ref,
        graph_revision_ref=GRAPH,
        definition_anchor_ref=accounting_scope_ref,
        parent_accounting_scope_ref=None,
        scope_kind="GRAPH",
        ancestry_hash=compute_ancestry_hash((accounting_scope_ref,)),
        created_from_definition_ref=accounting_scope_ref,
        state="ACTIVE",
    )


def usage_request(**overrides: object) -> UsageFactRequest:
    fields: dict[str, object] = dict(
        source_authority_ref="provider:acme",
        source_fact_id="invoice-line:1",
        fact_kind="METERED_USAGE",
        dimension_ref="tokens",
        accounting_scope_ref=SCOPE,
        quantity=100,
        unit="TOKEN",
        external_evidence_ref="evidence:invoice-line-1",
        caused_by_ref="event:usage-callback-1",
    )
    fields.update(overrides)
    return UsageFactRequest(**fields)


class UsageLedgerFoundationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.temp.name)
        self.store = SQLiteStore(self.root_dir / "kernel.db")
        self.resolver = AccountingScopeResolver(self.store)
        self.resolver.publish(scope(SCOPE))
        self.resolver.publish(scope(OTHER_SCOPE))
        self.now = 1000
        self.ledger = UsageLedger(self.store, lambda: self.now)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    # -- Test 1: one valid UsageFact persists and resolves exactly -------

    def test_valid_usage_fact_persists_and_resolves_exactly(self) -> None:
        fact = self.ledger.record_usage(usage_request())

        self.assertEqual(fact.accounting_scope_ref, SCOPE)
        self.assertEqual(fact.source_authority_ref, "provider:acme")
        self.assertEqual(fact.source_fact_id, "invoice-line:1")
        self.assertEqual(fact.quantity, 100)
        self.assertEqual(fact.unit, "TOKEN")
        self.assertEqual(fact.fact_kind, "METERED_USAGE")
        self.assertEqual(fact.ingested_at, self.now)

        resolved = self.ledger.resolve(fact.usage_fact_ref)
        self.assertEqual(resolved, fact)

    # -- Test 2: exact duplicate callback is idempotent -------------------

    def test_exact_duplicate_callback_returns_one_canonical_fact(self) -> None:
        first = self.ledger.record_usage(usage_request())
        second = self.ledger.record_usage(usage_request())

        self.assertEqual(first, second)
        self.assertEqual(first.usage_fact_ref, second.usage_fact_ref)

        rows = self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM usage_facts"
        ).fetchone()
        self.assertEqual(rows["n"], 1)

    # -- Test 3: same identity, changed payload fails closed --------------

    def test_conflicting_payload_same_identity_fails_closed(self) -> None:
        original = self.ledger.record_usage(usage_request())

        with self.assertRaises(UsageLedgerError) as ctx:
            self.ledger.record_usage(usage_request(quantity=999))
        self.assertEqual(ctx.exception.code, "USAGE_FACT_RECONCILIATION_REQUIRED")

        # existing fact is untouched, and no duplicate/overwritten row exists
        preserved = self.ledger.resolve(original.usage_fact_ref)
        self.assertEqual(preserved, original)
        rows = self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM usage_facts"
        ).fetchone()
        self.assertEqual(rows["n"], 1)

    def test_conflicting_unit_same_identity_fails_closed(self) -> None:
        self.ledger.record_usage(usage_request())
        with self.assertRaises(UsageLedgerError) as ctx:
            self.ledger.record_usage(usage_request(unit="USD_CENT"))
        self.assertEqual(ctx.exception.code, "USAGE_FACT_RECONCILIATION_REQUIRED")

    def test_conflicting_binding_same_identity_fails_closed(self) -> None:
        self.ledger.record_usage(usage_request())
        with self.assertRaises(UsageLedgerError) as ctx:
            self.ledger.record_usage(usage_request(accounting_scope_ref=OTHER_SCOPE))
        self.assertEqual(ctx.exception.code, "USAGE_FACT_RECONCILIATION_REQUIRED")

    # -- Test 4: distinct provider line items both persist ----------------

    def test_distinct_line_item_identities_both_persist(self) -> None:
        first = self.ledger.record_usage(
            usage_request(source_fact_id="invoice-line:1")
        )
        second = self.ledger.record_usage(
            usage_request(source_fact_id="invoice-line:2")
        )

        self.assertNotEqual(first.usage_fact_ref, second.usage_fact_ref)
        rows = self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM usage_facts"
        ).fetchone()
        self.assertEqual(rows["n"], 2)

    # -- Test 5: UsageFact canonical fields are immutable after commit ----

    def test_usage_fact_is_immutable_after_commit(self) -> None:
        fact = self.ledger.record_usage(usage_request())

        with self.assertRaises(Exception):
            self.store.connection.execute(
                "UPDATE usage_facts SET quantity = 1 WHERE usage_fact_ref = ?",
                (fact.usage_fact_ref,),
            )

    def test_usage_fact_delete_is_rejected_and_row_persists(self) -> None:
        fact = self.ledger.record_usage(usage_request())

        with self.assertRaises(Exception):
            self.store.connection.execute(
                "DELETE FROM usage_facts WHERE usage_fact_ref = ?",
                (fact.usage_fact_ref,),
            )

        rows = self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM usage_facts"
        ).fetchone()
        self.assertEqual(rows["n"], 1)
        preserved = self.ledger.resolve(fact.usage_fact_ref)
        self.assertEqual(preserved, fact)

    def test_replay_after_rejected_usage_fact_delete_remains_idempotent(
        self,
    ) -> None:
        request = usage_request()
        original = self.ledger.record_usage(request)

        with self.assertRaises(Exception):
            self.store.connection.execute(
                "DELETE FROM usage_facts WHERE usage_fact_ref = ?",
                (original.usage_fact_ref,),
            )

        replayed = self.ledger.record_usage(request)

        self.assertEqual(replayed.usage_fact_ref, original.usage_fact_ref)
        self.assertEqual(replayed, original)
        rows = self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM usage_facts"
        ).fetchone()
        self.assertEqual(rows["n"], 1)

    # -- Test 6: UsageAdjustmentFact appends and references original -----

    def test_adjustment_appends_and_references_original_fact(self) -> None:
        original = self.ledger.record_usage(usage_request())

        adjustment = self.ledger.record_adjustment(
            UsageAdjustmentFactRequest(
                adjusts_usage_fact_ref=original.usage_fact_ref,
                source_authority_ref="provider:acme",
                source_fact_id="correction:1",
                fact_kind="PROVIDER_REFUND",
                dimension_ref="tokens",
                delta_quantity=-10,
                unit="TOKEN",
                reason="provider over-billed",
                evidence_ref="evidence:correction-1",
                caused_by_ref="event:correction-callback-1",
            )
        )

        self.assertEqual(adjustment.adjusts_usage_fact_ref, original.usage_fact_ref)
        self.assertEqual(adjustment.delta_quantity, -10)

        # original fact is untouched by the adjustment
        preserved = self.ledger.resolve(original.usage_fact_ref)
        self.assertEqual(preserved, original)

    def test_adjustment_target_must_exist(self) -> None:
        with self.assertRaises(UsageLedgerError) as ctx:
            self.ledger.record_adjustment(
                UsageAdjustmentFactRequest(
                    adjusts_usage_fact_ref="usage-fact:does-not-exist",
                    source_authority_ref="provider:acme",
                    source_fact_id="correction:1",
                    fact_kind="PROVIDER_REFUND",
                    dimension_ref="tokens",
                    delta_quantity=-10,
                    unit="TOKEN",
                    reason="provider over-billed",
                    evidence_ref="evidence:correction-1",
                    caused_by_ref="event:correction-callback-1",
                )
            )
        self.assertEqual(ctx.exception.code, "USAGE_ADJUSTMENT_TARGET_UNRESOLVED")

    # -- Test 7: duplicate identical adjustment is idempotent -------------

    def test_duplicate_identical_adjustment_is_idempotent(self) -> None:
        original = self.ledger.record_usage(usage_request())

        def make_request() -> UsageAdjustmentFactRequest:
            return UsageAdjustmentFactRequest(
                adjusts_usage_fact_ref=original.usage_fact_ref,
                source_authority_ref="provider:acme",
                source_fact_id="correction:1",
                fact_kind="PROVIDER_REFUND",
                dimension_ref="tokens",
                delta_quantity=-10,
                unit="TOKEN",
                reason="provider over-billed",
                evidence_ref="evidence:correction-1",
                caused_by_ref="event:correction-callback-1",
            )

        first = self.ledger.record_adjustment(make_request())
        second = self.ledger.record_adjustment(make_request())

        self.assertEqual(first, second)
        rows = self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM usage_adjustment_facts"
        ).fetchone()
        self.assertEqual(rows["n"], 1)

    # -- UsageAdjustmentFact immutability: UPDATE and DELETE rejected -----

    def test_usage_adjustment_fact_is_immutable_after_commit(self) -> None:
        original = self.ledger.record_usage(usage_request())
        adjustment = self.ledger.record_adjustment(
            UsageAdjustmentFactRequest(
                adjusts_usage_fact_ref=original.usage_fact_ref,
                source_authority_ref="provider:acme",
                source_fact_id="correction:1",
                fact_kind="PROVIDER_REFUND",
                dimension_ref="tokens",
                delta_quantity=-10,
                unit="TOKEN",
                reason="provider over-billed",
                evidence_ref="evidence:correction-1",
                caused_by_ref="event:correction-callback-1",
            )
        )

        with self.assertRaises(Exception):
            self.store.connection.execute(
                "UPDATE usage_adjustment_facts SET delta_quantity = -1 "
                "WHERE adjustment_fact_ref = ?",
                (adjustment.adjustment_fact_ref,),
            )

    def test_usage_adjustment_fact_delete_is_rejected_and_row_persists(
        self,
    ) -> None:
        original = self.ledger.record_usage(usage_request())
        adjustment = self.ledger.record_adjustment(
            UsageAdjustmentFactRequest(
                adjusts_usage_fact_ref=original.usage_fact_ref,
                source_authority_ref="provider:acme",
                source_fact_id="correction:1",
                fact_kind="PROVIDER_REFUND",
                dimension_ref="tokens",
                delta_quantity=-10,
                unit="TOKEN",
                reason="provider over-billed",
                evidence_ref="evidence:correction-1",
                caused_by_ref="event:correction-callback-1",
            )
        )

        with self.assertRaises(Exception):
            self.store.connection.execute(
                "DELETE FROM usage_adjustment_facts "
                "WHERE adjustment_fact_ref = ?",
                (adjustment.adjustment_fact_ref,),
            )

        rows = self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM usage_adjustment_facts"
        ).fetchone()
        self.assertEqual(rows["n"], 1)
        preserved = self.store.connection.execute(
            "SELECT delta_quantity FROM usage_adjustment_facts "
            "WHERE adjustment_fact_ref = ?",
            (adjustment.adjustment_fact_ref,),
        ).fetchone()
        self.assertEqual(preserved["delta_quantity"], -10)

    def test_replay_after_rejected_adjustment_delete_remains_idempotent(
        self,
    ) -> None:
        original = self.ledger.record_usage(usage_request())

        def make_request() -> UsageAdjustmentFactRequest:
            return UsageAdjustmentFactRequest(
                adjusts_usage_fact_ref=original.usage_fact_ref,
                source_authority_ref="provider:acme",
                source_fact_id="correction:1",
                fact_kind="PROVIDER_REFUND",
                dimension_ref="tokens",
                delta_quantity=-10,
                unit="TOKEN",
                reason="provider over-billed",
                evidence_ref="evidence:correction-1",
                caused_by_ref="event:correction-callback-1",
            )

        first = self.ledger.record_adjustment(make_request())

        with self.assertRaises(Exception):
            self.store.connection.execute(
                "DELETE FROM usage_adjustment_facts "
                "WHERE adjustment_fact_ref = ?",
                (first.adjustment_fact_ref,),
            )

        replayed = self.ledger.record_adjustment(make_request())

        self.assertEqual(replayed.adjustment_fact_ref, first.adjustment_fact_ref)
        self.assertEqual(replayed, first)
        rows = self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM usage_adjustment_facts"
        ).fetchone()
        self.assertEqual(rows["n"], 1)

    # -- Test 8: adjustment identity conflict fails closed -----------------

    def test_adjustment_identity_conflict_fails_closed(self) -> None:
        original = self.ledger.record_usage(usage_request())

        self.ledger.record_adjustment(
            UsageAdjustmentFactRequest(
                adjusts_usage_fact_ref=original.usage_fact_ref,
                source_authority_ref="provider:acme",
                source_fact_id="correction:1",
                fact_kind="PROVIDER_REFUND",
                dimension_ref="tokens",
                delta_quantity=-10,
                unit="TOKEN",
                reason="provider over-billed",
                evidence_ref="evidence:correction-1",
                caused_by_ref="event:correction-callback-1",
            )
        )

        with self.assertRaises(UsageLedgerError) as ctx:
            self.ledger.record_adjustment(
                UsageAdjustmentFactRequest(
                    adjusts_usage_fact_ref=original.usage_fact_ref,
                    source_authority_ref="provider:acme",
                    source_fact_id="correction:1",
                    fact_kind="PROVIDER_REFUND",
                    dimension_ref="tokens",
                    delta_quantity=-20,
                    unit="TOKEN",
                    reason="provider over-billed",
                    evidence_ref="evidence:correction-1",
                    caused_by_ref="event:correction-callback-1",
                )
            )
        self.assertEqual(
            ctx.exception.code, "USAGE_ADJUSTMENT_RECONCILIATION_REQUIRED"
        )
        rows = self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM usage_adjustment_facts"
        ).fetchone()
        self.assertEqual(rows["n"], 1)

    # -- Test 9: no path converts missing/unknown evidence into zero ------

    def test_quantity_is_required_and_never_defaulted(self) -> None:
        with self.assertRaises(TypeError):
            UsageFactRequest(  # type: ignore[call-arg]
                source_authority_ref="provider:acme",
                source_fact_id="invoice-line:1",
                fact_kind="METERED_USAGE",
                dimension_ref="tokens",
                accounting_scope_ref=SCOPE,
                unit="TOKEN",
                external_evidence_ref="evidence:invoice-line-1",
                caused_by_ref="event:usage-callback-1",
            )

    def test_negative_quantity_rejected_not_coerced_to_zero(self) -> None:
        with self.assertRaises(UsageLedgerError) as ctx:
            self.ledger.record_usage(usage_request(quantity=-1))
        self.assertEqual(ctx.exception.code, "USAGE_FACT_REQUEST_INVALID")
        rows = self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM usage_facts"
        ).fetchone()
        self.assertEqual(rows["n"], 0)

    # -- Test 10: simulated retry after commit does not double-count ------

    def test_retry_after_commit_does_not_double_count(self) -> None:
        request = usage_request()
        first = self.ledger.record_usage(request)

        # Simulate provider/transport retry delivering the identical
        # callback again after the original commit succeeded.
        retried = self.ledger.record_usage(request)

        self.assertEqual(first.usage_fact_ref, retried.usage_fact_ref)
        rows = self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM usage_facts"
        ).fetchone()
        self.assertEqual(rows["n"], 1)

    # -- Test 11: no BudgetReservation settlement state is touched --------

    def test_ledger_never_touches_budget_reservation_tables(self) -> None:
        self.store.create_budget_schema()
        self.ledger.record_usage(usage_request())

        # BudgetAuthority's own tables remain untouched by the ledger --
        # UsageLedger never writes to budget_reservations /
        # budget_scope_exposure / budget_policy_revisions.
        for table in (
            "budget_reservations",
            "budget_scope_exposure",
            "budget_policy_revisions",
        ):
            rows = self.store.connection.execute(
                f"SELECT COUNT(*) AS n FROM {table}"
            ).fetchone()
            self.assertEqual(rows["n"], 0, f"{table} unexpectedly non-empty")

    # -- Accounting scope validation ---------------------------------------

    def test_unresolved_accounting_scope_fails_closed(self) -> None:
        with self.assertRaises(UsageLedgerError) as ctx:
            self.ledger.record_usage(
                usage_request(accounting_scope_ref="accounting:usage/nonexistent")
            )
        self.assertEqual(
            ctx.exception.code, "USAGE_FACT_ACCOUNTING_SCOPE_UNRESOLVED"
        )


if __name__ == "__main__":
    unittest.main()
