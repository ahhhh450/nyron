"""Acceptance tests for Task 102 known-actual settlement / overrun."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nyron_kernel.accounting import (
    AccountingScope,
    AccountingScopeResolver,
    BudgetAuthority,
    BudgetDimension,
    BudgetPolicyRevision,
    BudgetReservationRequest,
    BudgetRule,
    SettlementAuthority,
    SettlementAuthorityError,
    SettlementRequest,
    UsageAdjustmentFactRequest,
    UsageFactRequest,
    UsageLedger,
    compute_ancestry_hash,
)
from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.execution import (
    ActivationRepository,
    RunRepository,
    RuntimeAuthorityResolver,
)
from nyron_kernel.store import SQLiteStore


GRAPH = "graph:settlement@1"
MODULE = "module-instance:settlement@1"
EXECUTION = "execution:settlement/1"
ACTIVATION = "activation:settlement/1"
RUN = "run:settlement/1"
ROOT_SCOPE = "accounting:settlement/root"
CHILD_SCOPE = "accounting:settlement/child"


class InjectedCrash(RuntimeError):
    pass


class BudgetSettlementFoundationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "kernel.db"
        self.store = SQLiteStore(self.db_path)
        self.now = 100
        self._seed_runtime()
        self.resolver = AccountingScopeResolver(self.store)
        self.resolver.publish(self._scope(ROOT_SCOPE, GRAPH, (ROOT_SCOPE,), None))
        self.resolver.publish(
            self._scope(CHILD_SCOPE, MODULE, (ROOT_SCOPE, CHILD_SCOPE), ROOT_SCOPE)
        )
        self.activations = ActivationRepository(self.store, ModuleRegistry(self.store))
        self.runtime_authority = RuntimeAuthorityResolver(self.store)
        self.budget = BudgetAuthority(
            self.store,
            self.resolver,
            self.activations,
            self.runtime_authority,
            lambda: self.now,
        )
        self.ledger = UsageLedger(self.store, lambda: self.now)
        self.settlement = SettlementAuthority(self.store, lambda: self.now)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    @staticmethod
    def _scope(ref, anchor, ancestry, parent):
        return AccountingScope(
            accounting_scope_ref=ref,
            graph_revision_ref=GRAPH,
            definition_anchor_ref=anchor,
            parent_accounting_scope_ref=parent,
            scope_kind="GRAPH" if parent is None else "MODULE",
            ancestry_hash=compute_ancestry_hash(ancestry),
            created_from_definition_ref=anchor,
            state="ACTIVE",
        )

    def _seed_runtime(self) -> None:
        self.store.create_run_attempt_schema()
        with self.store.transaction() as connection:
            connection.execute(
                "INSERT INTO graph_revisions VALUES (?, '{}', 1, NULL)", (GRAPH,)
            )
            connection.execute(
                """
                INSERT INTO module_instance_revisions VALUES (
                    ?, ?, 'settlement', 'test.settlement', '1',
                    'config:settlement@1', 'sha256:settlement', '{}', '{}',
                    '["root"]', ?
                )
                """,
                (MODULE, GRAPH, CHILD_SCOPE),
            )
            connection.execute(
                """
                INSERT INTO execution_admissions VALUES
                ('admission:settlement/1', ?, ?, 'policy:settlement@1', 1, 'ADMITTED')
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO workflow_executions VALUES
                (?, ?, 'admission:settlement/1', 'policy:settlement@1', 'ADMITTED')
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO activations VALUES
                (?, ?, ?, ?, 'delivery:settlement', '[]', ?, 'event:activation')
                """,
                (ACTIVATION, EXECUTION, GRAPH, MODULE, CHILD_SCOPE),
            )
            connection.execute(
                """
                INSERT INTO activation_created_events VALUES
                ('event:activation', ?, 'ActivationCreated')
                """,
                (ACTIVATION,),
            )
        RunRepository(self.store).create_initial(
            run_ref=RUN, activation_ref=ACTIVATION, execution_ref=EXECUTION
        )

    def _publish_limit(self, amount: int) -> None:
        self.budget.publish_policy_revision(
            BudgetPolicyRevision(
                "policy:root@1",
                ROOT_SCOPE,
                0,
                None,
                (BudgetDimension("tokens", "TOKEN", "sem:tokens@1"),),
                (BudgetRule("rule:tokens", "tokens", amount, "LIFETIME_LIMIT", "HARD"),),
                "admin:test",
                None,
            )
        )

    def _reserve(self, request_ref: str, amount: int = 100):
        return self.budget.reserve(
            BudgetReservationRequest(
                request_ref=request_ref,
                activation_ref=ACTIVATION,
                run_ref=RUN,
                attempt_seq=1,
                accounting_scope_ref=CHILD_SCOPE,
                graph_revision_ref=GRAPH,
                definition_anchor_ref=MODULE,
                estimate_ref=f"estimate:{request_ref}",
                reserved_dimensions=(("tokens", amount),),
                subject_refs=("subject:settlement",),
                caused_by_ref="delivery:settlement",
            )
        )

    def _usage(self, reservation_ref: str, quantity: int, source_id: str = "line:1"):
        return self.ledger.record_usage(
            UsageFactRequest(
                source_authority_ref="provider:test",
                source_fact_id=source_id,
                fact_kind="METERED_USAGE",
                dimension_ref="tokens",
                accounting_scope_ref=CHILD_SCOPE,
                quantity=quantity,
                unit="TOKEN",
                external_evidence_ref=f"evidence:{source_id}",
                caused_by_ref=f"event:{source_id}",
                reservation_ref=reservation_ref,
            )
        )

    @staticmethod
    def _request(reservation_ref: str, request_ref: str = "settle:1"):
        return SettlementRequest(request_ref, reservation_ref, "event:settlement")

    def test_actual_less_than_reserved_commits_and_releases_remainder(self) -> None:
        reservation = self._reserve("reserve:less")
        self._usage(reservation.reservation_ref, 60)

        result = self.settlement.settle(self._request(reservation.reservation_ref))

        self.assertEqual((('tokens', 60),), result.actual_dimensions)
        self.assertEqual((('tokens', 40),), result.released_dimensions)
        self.assertEqual((), result.overrun_dimensions)
        self.assertEqual("COMMITTED", result.resulting_state)
        for scope_ref in (ROOT_SCOPE, CHILD_SCOPE):
            self.assertEqual((0, 60), self.budget.exposure(scope_ref, "tokens"))
        settled = self.budget.resolve(reservation.reservation_ref)
        self.assertEqual("COMMITTED", settled.state)
        self.assertEqual((('tokens', 60),), settled.committed_dimensions)
        self.assertEqual((('tokens', 40),), settled.released_dimensions)

    def test_actual_equal_reserved_commits_exactly(self) -> None:
        reservation = self._reserve("reserve:equal")
        self._usage(reservation.reservation_ref, 100)
        result = self.settlement.settle(self._request(reservation.reservation_ref))
        self.assertEqual((('tokens', 100),), result.actual_dimensions)
        self.assertEqual((), result.released_dimensions)
        self.assertEqual((0, 100), self.budget.exposure(ROOT_SCOPE, "tokens"))

    def test_overrun_commits_full_actual_and_blocks_future_reserve(self) -> None:
        self._publish_limit(120)
        reservation = self._reserve("reserve:overrun")
        self._usage(reservation.reservation_ref, 135)

        result = self.settlement.settle(self._request(reservation.reservation_ref))

        self.assertEqual((('tokens', 135),), result.actual_dimensions)
        self.assertEqual((('tokens', 35),), result.overrun_dimensions)
        for scope_ref in (ROOT_SCOPE, CHILD_SCOPE):
            self.assertEqual((0, 135), self.budget.exposure(scope_ref, "tokens"))
        denied = self._reserve("reserve:after-overrun", amount=1)
        self.assertEqual("DENIED", denied.state)
        self.assertEqual("ANCESTOR_LIMIT_EXCEEDED", denied.deny_reason_code)

    def test_actual_in_unreserved_dimension_is_full_overrun(self) -> None:
        reservation = self._reserve("reserve:new-dimension")
        self.ledger.record_usage(
            UsageFactRequest(
                source_authority_ref="provider:test",
                source_fact_id="line:requests",
                fact_kind="METERED_USAGE",
                dimension_ref="requests",
                accounting_scope_ref=CHILD_SCOPE,
                quantity=5,
                unit="REQUEST",
                external_evidence_ref="evidence:requests",
                caused_by_ref="event:requests",
                reservation_ref=reservation.reservation_ref,
            )
        )

        result = self.settlement.settle(self._request(reservation.reservation_ref))

        self.assertEqual((('requests', 5),), result.overrun_dimensions)
        self.assertEqual((('tokens', 100),), result.released_dimensions)
        for scope_ref in (ROOT_SCOPE, CHILD_SCOPE):
            self.assertEqual((0, 5), self.budget.exposure(scope_ref, "requests"))

    def test_refund_is_append_only_and_reduces_initial_settlement(self) -> None:
        reservation = self._reserve("reserve:refund")
        fact = self._usage(reservation.reservation_ref, 100)
        adjustment = self.ledger.record_adjustment(
            UsageAdjustmentFactRequest(
                adjusts_usage_fact_ref=fact.usage_fact_ref,
                source_authority_ref="provider:test",
                source_fact_id="refund:1",
                fact_kind="PROVIDER_REFUND",
                dimension_ref="tokens",
                delta_quantity=-25,
                unit="TOKEN",
                reason="provider refund",
                evidence_ref="evidence:refund:1",
                caused_by_ref="event:refund:1",
            )
        )

        result = self.settlement.settle(self._request(reservation.reservation_ref))

        self.assertEqual((('tokens', 75),), result.actual_dimensions)
        self.assertEqual((adjustment.adjustment_fact_ref,), result.adjustment_fact_refs)
        original = self.ledger.resolve(fact.usage_fact_ref)
        self.assertEqual(100, original.quantity)
        self.assertEqual(
            1,
            self.store.connection.execute(
                "SELECT COUNT(*) AS n FROM usage_adjustment_facts"
            ).fetchone()["n"],
        )

    def test_exact_replay_and_restart_do_not_double_apply(self) -> None:
        reservation = self._reserve("reserve:replay")
        self._usage(reservation.reservation_ref, 80)
        request = self._request(reservation.reservation_ref)
        first = self.settlement.settle(request)
        second = self.settlement.settle(request)
        self.assertEqual(first, second)
        self.assertEqual((0, 80), self.budget.exposure(ROOT_SCOPE, "tokens"))

        self.store.close()
        self.store = SQLiteStore(self.db_path)
        restarted = SettlementAuthority(self.store, lambda: self.now)
        third = restarted.settle(request)
        self.assertEqual(first, third)
        row = self.store.connection.execute(
            "SELECT reserved_amount, committed_amount FROM budget_scope_exposure "
            "WHERE accounting_scope_ref = ? AND dimension_ref = 'tokens'",
            (ROOT_SCOPE,),
        ).fetchone()
        self.assertEqual((0, 80), (row["reserved_amount"], row["committed_amount"]))

    def test_crash_rolls_back_exposure_reservation_and_settlement(self) -> None:
        reservation = self._reserve("reserve:crash")
        self._usage(reservation.reservation_ref, 70)

        def crash(stage: str) -> None:
            if stage == "AFTER_RESERVATION_UPDATE":
                raise InjectedCrash(stage)

        crashing = SettlementAuthority(self.store, lambda: self.now, crash)
        with self.assertRaises(InjectedCrash):
            crashing.settle(self._request(reservation.reservation_ref))

        self.assertEqual((100, 0), self.budget.exposure(ROOT_SCOPE, "tokens"))
        self.assertEqual("RESERVED", self.budget.resolve(reservation.reservation_ref).state)
        count = self.store.connection.execute(
            "SELECT COUNT(*) AS n FROM budget_settlements"
        ).fetchone()["n"]
        self.assertEqual(0, count)
        result = self.settlement.settle(self._request(reservation.reservation_ref))
        self.assertEqual((('tokens', 70),), result.actual_dimensions)

    def test_same_request_identity_with_different_reservation_fails_closed(self) -> None:
        first_reservation = self._reserve("reserve:identity:1")
        second_reservation = self._reserve("reserve:identity:2")
        self._usage(first_reservation.reservation_ref, 10, "line:identity:1")
        self._usage(second_reservation.reservation_ref, 10, "line:identity:2")
        self.settlement.settle(self._request(first_reservation.reservation_ref))

        with self.assertRaises(SettlementAuthorityError) as raised:
            self.settlement.settle(self._request(second_reservation.reservation_ref))
        self.assertEqual("SETTLEMENT_REQUEST_CONFLICT", raised.exception.code)
        self.assertEqual((100, 10), self.budget.exposure(ROOT_SCOPE, "tokens"))

    def test_fact_scope_binding_conflict_fails_without_counter_change(self) -> None:
        reservation = self._reserve("reserve:binding")
        self.ledger.record_usage(
            UsageFactRequest(
                source_authority_ref="provider:test",
                source_fact_id="line:bad-binding",
                fact_kind="METERED_USAGE",
                dimension_ref="tokens",
                accounting_scope_ref=ROOT_SCOPE,
                quantity=20,
                unit="TOKEN",
                external_evidence_ref="evidence:bad-binding",
                caused_by_ref="event:bad-binding",
                reservation_ref=reservation.reservation_ref,
            )
        )
        with self.assertRaises(SettlementAuthorityError) as raised:
            self.settlement.settle(self._request(reservation.reservation_ref))
        self.assertEqual("SETTLEMENT_FACT_BINDING_CONFLICT", raised.exception.code)
        self.assertEqual((100, 0), self.budget.exposure(ROOT_SCOPE, "tokens"))
        self.assertEqual("RESERVED", self.budget.resolve(reservation.reservation_ref).state)

    def test_raw_exposure_invariant_failure_rolls_back_ancestor_conversion(self) -> None:
        reservation = self._reserve("reserve:raw-invariant")
        self._usage(reservation.reservation_ref, 50)
        self.store.connection.execute(
            """
            UPDATE budget_scope_exposure SET reserved_amount = 40
            WHERE accounting_scope_ref = ? AND dimension_ref = 'tokens'
            """,
            (CHILD_SCOPE,),
        )

        with self.assertRaises(SettlementAuthorityError) as raised:
            self.settlement.settle(self._request(reservation.reservation_ref))

        self.assertEqual(
            "SETTLEMENT_EXPOSURE_INVARIANT_VIOLATION", raised.exception.code
        )
        self.assertEqual((100, 0), self.budget.exposure(ROOT_SCOPE, "tokens"))
        self.assertEqual((40, 0), self.budget.exposure(CHILD_SCOPE, "tokens"))
        self.assertEqual("RESERVED", self.budget.resolve(reservation.reservation_ref).state)


if __name__ == "__main__":
    unittest.main()
