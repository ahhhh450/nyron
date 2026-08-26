"""Acceptance tests for ARE-GATE-6A / Task 074: BudgetPolicyRevision and
BudgetReservation foundation.

Maps to the Task's Required Tests list (18 items) plus the §H crash/replay
windows. This slice does not implement UsageFact settlement or Recovery;
tests here only exercise REQUESTED/RESERVED/DENIED and the atomic
full-ancestry reserve/deny path.
"""

from __future__ import annotations

import dataclasses
import inspect
import re
import tempfile
import unittest
from pathlib import Path

from nyron_kernel.accounting import (
    AccountingScope,
    AccountingScopeResolver,
    BudgetAuthority,
    BudgetAuthorityError,
    BudgetDimension,
    BudgetPolicyRevision,
    BudgetReservationRequest,
    BudgetRule,
    compute_ancestry_hash,
)
from nyron_kernel.accounting import budget_authority as budget_authority_module
from nyron_kernel.execution import RunRepository
from nyron_kernel.store import SQLiteStore


GRAPH = "graph:budget@1"
MODULE = "module-instance:budget@1"
EXECUTION = "execution:budget/1"
ACTIVATION = "activation:budget/1"
RUN = "run:budget/1"
ROOT_SCOPE = "accounting:budget/root"
CHILD_SCOPE = "accounting:budget/child"
GRANDCHILD_SCOPE = "accounting:budget/grandchild"


class InjectedCrash(RuntimeError):
    pass


def scope(
    accounting_scope_ref: str,
    definition_anchor_ref: str,
    ancestry: tuple[str, ...],
    *,
    parent: str | None = None,
    scope_kind: str = "MODULE",
) -> AccountingScope:
    return AccountingScope(
        accounting_scope_ref=accounting_scope_ref,
        graph_revision_ref=GRAPH,
        definition_anchor_ref=definition_anchor_ref,
        parent_accounting_scope_ref=parent,
        scope_kind=scope_kind,
        ancestry_hash=compute_ancestry_hash(ancestry),
        created_from_definition_ref=definition_anchor_ref,
        state="ACTIVE",
    )


class BudgetReservationFoundationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root_dir = Path(self.temp.name)
        self.store = SQLiteStore(self.root_dir / "kernel.db")
        self._seed_runtime()
        self.resolver = AccountingScopeResolver(self.store)
        self.now = 100
        self.authority = self._authority()

        self.resolver.publish(scope(ROOT_SCOPE, GRAPH, (ROOT_SCOPE,), scope_kind="GRAPH"))
        self.resolver.publish(
            scope(CHILD_SCOPE, MODULE, (ROOT_SCOPE, CHILD_SCOPE), parent=ROOT_SCOPE)
        )
        self.resolver.publish(
            scope(
                GRANDCHILD_SCOPE,
                "port:budget/text@1",
                (ROOT_SCOPE, CHILD_SCOPE, GRANDCHILD_SCOPE),
                parent=CHILD_SCOPE,
                scope_kind="PORT",
            )
        )

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def _authority(self, crash_hook=None) -> BudgetAuthority:
        return BudgetAuthority(self.store, self.resolver, lambda: self.now, crash_hook)

    def _seed_runtime(self) -> None:
        self.store.create_run_attempt_schema()
        with self.store.transaction() as connection:
            connection.execute(
                "INSERT INTO graph_revisions VALUES (?, '{}', 1, NULL)", (GRAPH,)
            )
            connection.execute(
                """
                INSERT INTO module_instance_revisions VALUES (
                    ?, ?, 'budget', 'test.budget', '1', 'config:budget@1',
                    'sha256:budget', '{}', '{}', '["root"]', ?
                )
                """,
                (MODULE, GRAPH, CHILD_SCOPE),
            )
            connection.execute(
                """
                INSERT INTO execution_admissions VALUES
                ('admission:budget/1', ?, ?, 'policy:budget@1', 1, 'ADMITTED')
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO workflow_executions VALUES
                (?, ?, 'admission:budget/1', 'policy:budget@1', 'ADMITTED')
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO activations VALUES
                (?, ?, ?, ?, 'delivery:budget-trigger', '[]', ?, 'event:budget-activation')
                """,
                (ACTIVATION, EXECUTION, GRAPH, MODULE, CHILD_SCOPE),
            )
            connection.execute(
                """
                INSERT INTO activation_created_events VALUES
                ('event:budget-activation', ?, 'ActivationCreated')
                """,
                (ACTIVATION,),
            )
        RunRepository(self.store).create_initial(
            run_ref=RUN, activation_ref=ACTIVATION, execution_ref=EXECUTION
        )

    def _rule(
        self,
        rule_ref: str,
        dimension_ref: str,
        limit_amount: int,
        enforcement: str = "HARD",
        limit_kind: str = "LIFETIME_LIMIT",
    ) -> BudgetRule:
        return BudgetRule(rule_ref, dimension_ref, limit_amount, limit_kind, enforcement)

    def _publish_policy(
        self,
        accounting_scope_ref: str,
        rules: tuple[BudgetRule, ...],
        *,
        ref: str | None = None,
        effective_from: int = 0,
        effective_until: int | None = None,
        supersedes_ref: str | None = None,
    ) -> BudgetPolicyRevision:
        revision = BudgetPolicyRevision(
            budget_policy_revision_ref=ref or f"policy:{accounting_scope_ref}@1",
            accounting_scope_ref=accounting_scope_ref,
            effective_from=effective_from,
            effective_until=effective_until,
            dimensions=(BudgetDimension("tokens", "count", "sem:tokens@1"),),
            enforcement_rules=rules,
            created_by_ref="admin:test",
            supersedes_ref=supersedes_ref,
        )
        return self.authority.publish_policy_revision(revision)

    def _request(
        self,
        request_ref: str,
        *,
        accounting_scope_ref: str = GRANDCHILD_SCOPE,
        graph_revision_ref: str = GRAPH,
        definition_anchor_ref: str = "port:budget/text@1",
        estimate_ref: str = "estimate:1",
        amount: int = 10,
        dimension: str = "tokens",
        subject_refs: tuple[str, ...] = ("subject:1",),
        attempt_seq: int = 1,
        caused_by_ref: str = "delivery:budget-trigger",
    ) -> BudgetReservationRequest:
        return BudgetReservationRequest(
            request_ref=request_ref,
            activation_ref=ACTIVATION,
            run_ref=RUN,
            attempt_seq=attempt_seq,
            accounting_scope_ref=accounting_scope_ref,
            graph_revision_ref=graph_revision_ref,
            definition_anchor_ref=definition_anchor_ref,
            estimate_ref=estimate_ref,
            reserved_dimensions=((dimension, amount),),
            subject_refs=subject_refs,
            caused_by_ref=caused_by_ref,
        )

    # ------------------------------------------------------------------
    # 1. BudgetPolicyRevision / rule shapes are immutable and machine-checkable.
    # ------------------------------------------------------------------

    def test_policy_revision_and_rule_are_frozen_and_checkable(self) -> None:
        rule = self._rule("rule:1", "tokens", 100)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            rule.limit_amount = 200  # type: ignore[misc]
        revision = self._publish_policy(ROOT_SCOPE, (rule,))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            revision.effective_from = 999  # type: ignore[misc]

        with self.assertRaises(BudgetAuthorityError) as raised:
            self._publish_policy(
                ROOT_SCOPE,
                (self._rule("rule:bad", "tokens", 100, limit_kind="ROLLING_WINDOW_QUOTA"),),
                ref="policy:bad@1",
            )
        self.assertEqual("BUDGET_RULE_LIMIT_KIND_UNSUPPORTED", raised.exception.code)

        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.publish_policy_revision(
                BudgetPolicyRevision(
                    "policy:invalid@1", ROOT_SCOPE, 0, None, (), (), "", None
                )
            )
        self.assertEqual("BUDGET_POLICY_REVISION_INVALID", raised.exception.code)

    # ------------------------------------------------------------------
    # 1b. Task-080 correction (077-F-003): dimensions/enforcement_rules
    # must be exact immutable tuples, dimension_ref/rule_ref must be
    # unique within one revision, and every rule must reference exactly
    # one dimension declared in that same revision.
    # ------------------------------------------------------------------

    def _unpublished_revision(
        self,
        accounting_scope_ref: str,
        dimensions,
        rules,
        *,
        ref: str,
    ) -> BudgetPolicyRevision:
        return BudgetPolicyRevision(
            budget_policy_revision_ref=ref,
            accounting_scope_ref=accounting_scope_ref,
            effective_from=0,
            effective_until=None,
            dimensions=dimensions,
            enforcement_rules=rules,
            created_by_ref="admin:test",
            supersedes_ref=None,
        )

    def test_list_shaped_dimensions_rejected(self) -> None:
        revision = self._unpublished_revision(
            ROOT_SCOPE,
            [BudgetDimension("tokens", "count", "sem:tokens@1")],
            (self._rule("rule:1", "tokens", 100),),
            ref="policy:list-dims@1",
        )
        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.publish_policy_revision(revision)
        self.assertEqual("BUDGET_POLICY_REVISION_INVALID", raised.exception.code)

    def test_list_shaped_enforcement_rules_rejected(self) -> None:
        revision = self._unpublished_revision(
            ROOT_SCOPE,
            (BudgetDimension("tokens", "count", "sem:tokens@1"),),
            [self._rule("rule:1", "tokens", 100)],
            ref="policy:list-rules@1",
        )
        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.publish_policy_revision(revision)
        self.assertEqual("BUDGET_POLICY_REVISION_INVALID", raised.exception.code)

    def test_duplicate_dimension_ref_rejected(self) -> None:
        revision = self._unpublished_revision(
            ROOT_SCOPE,
            (
                BudgetDimension("tokens", "count", "sem:tokens@1"),
                BudgetDimension("tokens", "count", "sem:tokens@2"),
            ),
            (self._rule("rule:1", "tokens", 100),),
            ref="policy:dup-dim@1",
        )
        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.publish_policy_revision(revision)
        self.assertEqual(
            "BUDGET_POLICY_REVISION_DIMENSION_DUPLICATE", raised.exception.code
        )

    def test_duplicate_rule_ref_rejected(self) -> None:
        revision = self._unpublished_revision(
            ROOT_SCOPE,
            (
                BudgetDimension("tokens", "count", "sem:tokens@1"),
                BudgetDimension("requests", "count", "sem:requests@1"),
            ),
            (
                self._rule("rule:1", "tokens", 100),
                self._rule("rule:1", "requests", 5),
            ),
            ref="policy:dup-rule@1",
        )
        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.publish_policy_revision(revision)
        self.assertEqual(
            "BUDGET_POLICY_REVISION_RULE_DUPLICATE", raised.exception.code
        )

    def test_rule_referring_to_undeclared_dimension_rejected(self) -> None:
        revision = self._unpublished_revision(
            ROOT_SCOPE,
            (BudgetDimension("tokens", "count", "sem:tokens@1"),),
            (self._rule("rule:1", "requests", 5),),
            ref="policy:orphan-rule@1",
        )
        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.publish_policy_revision(revision)
        self.assertEqual(
            "BUDGET_POLICY_REVISION_RULE_DIMENSION_UNDECLARED", raised.exception.code
        )

    def test_valid_tuple_shaped_policy_still_publishes_and_round_trips(self) -> None:
        revision = self._unpublished_revision(
            ROOT_SCOPE,
            (
                BudgetDimension("tokens", "count", "sem:tokens@1"),
                BudgetDimension("requests", "count", "sem:requests@1"),
            ),
            (
                self._rule("rule:tokens", "tokens", 100),
                self._rule("rule:requests", "requests", 5),
            ),
            ref="policy:valid-multi@1",
        )
        published = self.authority.publish_policy_revision(revision)
        self.assertEqual(revision, published)
        self.assertEqual(published, self.authority.publish_policy_revision(revision))

    def test_policy_revision_publish_is_idempotent_else_conflict(self) -> None:
        revision = self._publish_policy(ROOT_SCOPE, (self._rule("rule:1", "tokens", 100),))

        self.assertEqual(revision, self.authority.publish_policy_revision(revision))

        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.publish_policy_revision(
                dataclasses.replace(revision, effective_from=1)
            )
        self.assertEqual(
            "BUDGET_POLICY_REVISION_IDENTITY_CONFLICT", raised.exception.code
        )

    # ------------------------------------------------------------------
    # 2. BudgetReservation canonical identity and state round-trip.
    # ------------------------------------------------------------------

    def test_reservation_round_trips_through_resolve(self) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:1", "tokens", 1000),))
        reservation = self.authority.reserve(self._request("req:round-trip"))

        self.assertEqual(reservation, self.authority.resolve(reservation.reservation_ref))
        self.assertEqual(
            reservation, self.authority.resolve_by_request("req:round-trip")
        )
        self.assertEqual("RESERVED", reservation.state)
        self.assertIsNone(reservation.deny_reason_code)
        self.assertEqual((), reservation.committed_dimensions)
        self.assertEqual((), reservation.released_dimensions)

    # ------------------------------------------------------------------
    # 3. Same request replay is idempotent and does not double reserve.
    # (also covers §H "replay after RESERVED commit but before response")
    # ------------------------------------------------------------------

    def test_same_request_replay_is_idempotent_no_double_reserve(self) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:1", "tokens", 1000),))
        request = self._request("req:idempotent", amount=30)

        first = self.authority.reserve(request)
        second = self.authority.reserve(request)

        self.assertEqual(first, second)
        self.assertEqual((30, 0), self.authority.exposure(GRANDCHILD_SCOPE, "tokens"))
        self.assertEqual((30, 0), self.authority.exposure(ROOT_SCOPE, "tokens"))

    # ------------------------------------------------------------------
    # 4. Changed estimate/scope/subject binding is rejected as identity
    # conflict; old row/counters remain unchanged.
    # ------------------------------------------------------------------

    def test_changed_request_is_identity_conflict_and_leaves_state_unchanged(
        self,
    ) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:1", "tokens", 1000),))
        original = self.authority.reserve(self._request("req:conflict", amount=30))
        before_exposure = self.authority.exposure(GRANDCHILD_SCOPE, "tokens")

        variants = (
            self._request("req:conflict", amount=99),
            self._request("req:conflict", accounting_scope_ref=CHILD_SCOPE, definition_anchor_ref="module-instance:budget@1", amount=30),
            self._request("req:conflict", subject_refs=("subject:other",), amount=30),
            self._request("req:conflict", estimate_ref="estimate:other", amount=30),
        )
        for variant in variants:
            with self.subTest(variant=variant):
                with self.assertRaises(BudgetAuthorityError) as raised:
                    self.authority.reserve(variant)
                self.assertEqual("RESERVATION_REQUEST_CONFLICT", raised.exception.code)

        self.assertEqual(original, self.authority.resolve(original.reservation_ref))
        self.assertEqual(
            before_exposure, self.authority.exposure(GRANDCHILD_SCOPE, "tokens")
        )

    # ------------------------------------------------------------------
    # 074-F-001 correction: static-binding (graph_revision_ref /
    # definition_anchor_ref) must independently participate in same-
    # request_ref replay-identity comparison. Each probe below changes
    # EXACTLY ONE static-binding field and holds accounting_scope_ref (and
    # every other compared field) fixed, so the scope-mismatch path can
    # never be what raises the conflict.
    # ------------------------------------------------------------------

    def test_graph_revision_only_replay_conflict_after_reserved(self) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:1", "tokens", 1000),))
        original = self.authority.reserve(self._request("req:graph-reserved", amount=15))
        self.assertEqual("RESERVED", original.state)
        before_exposure = self.authority.exposure(GRANDCHILD_SCOPE, "tokens")

        variant = self._request(
            "req:graph-reserved", amount=15, graph_revision_ref="graph:different@1"
        )
        self.assertEqual(variant.accounting_scope_ref, original.accounting_scope_ref)
        self.assertEqual(
            variant.definition_anchor_ref, original.definition_anchor_ref
        )

        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.reserve(variant)
        self.assertEqual("RESERVATION_REQUEST_CONFLICT", raised.exception.code)

        self.assertEqual(original, self.authority.resolve(original.reservation_ref))
        self.assertEqual(
            before_exposure, self.authority.exposure(GRANDCHILD_SCOPE, "tokens")
        )

    def test_definition_anchor_only_replay_conflict_after_reserved(self) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:1", "tokens", 1000),))
        original = self.authority.reserve(
            self._request("req:anchor-reserved", amount=15)
        )
        self.assertEqual("RESERVED", original.state)
        before_exposure = self.authority.exposure(GRANDCHILD_SCOPE, "tokens")

        variant = self._request(
            "req:anchor-reserved",
            amount=15,
            definition_anchor_ref="port:budget/other@1",
        )
        self.assertEqual(variant.accounting_scope_ref, original.accounting_scope_ref)
        self.assertEqual(variant.graph_revision_ref, original.graph_revision_ref)

        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.reserve(variant)
        self.assertEqual("RESERVATION_REQUEST_CONFLICT", raised.exception.code)

        self.assertEqual(original, self.authority.resolve(original.reservation_ref))
        self.assertEqual(
            before_exposure, self.authority.exposure(GRANDCHILD_SCOPE, "tokens")
        )

    def test_graph_revision_only_replay_conflict_after_denied(self) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:1", "tokens", 10),))
        original = self.authority.reserve(self._request("req:graph-denied", amount=50))
        self.assertEqual("DENIED", original.state)
        before_root_exposure = self.authority.exposure(ROOT_SCOPE, "tokens")

        variant = self._request(
            "req:graph-denied", amount=50, graph_revision_ref="graph:different@1"
        )
        self.assertEqual(variant.accounting_scope_ref, original.accounting_scope_ref)
        self.assertEqual(
            variant.definition_anchor_ref, original.definition_anchor_ref
        )

        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.reserve(variant)
        self.assertEqual("RESERVATION_REQUEST_CONFLICT", raised.exception.code)

        self.assertEqual(original, self.authority.resolve(original.reservation_ref))
        self.assertEqual(
            before_root_exposure, self.authority.exposure(ROOT_SCOPE, "tokens")
        )

    def test_definition_anchor_only_replay_conflict_after_denied(self) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:1", "tokens", 10),))
        original = self.authority.reserve(
            self._request("req:anchor-denied", amount=50)
        )
        self.assertEqual("DENIED", original.state)
        before_root_exposure = self.authority.exposure(ROOT_SCOPE, "tokens")

        variant = self._request(
            "req:anchor-denied",
            amount=50,
            definition_anchor_ref="port:budget/other@1",
        )
        self.assertEqual(variant.accounting_scope_ref, original.accounting_scope_ref)
        self.assertEqual(variant.graph_revision_ref, original.graph_revision_ref)

        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.reserve(variant)
        self.assertEqual("RESERVATION_REQUEST_CONFLICT", raised.exception.code)

        self.assertEqual(original, self.authority.resolve(original.reservation_ref))
        self.assertEqual(
            before_root_exposure, self.authority.exposure(ROOT_SCOPE, "tokens")
        )

    def test_truly_identical_replay_still_idempotent_after_static_binding_fix(
        self,
    ) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:1", "tokens", 1000),))
        request = self._request("req:still-idempotent", amount=25)

        first = self.authority.reserve(request)
        second = self.authority.reserve(request)
        third = self.authority.reserve(
            self._request("req:still-idempotent", amount=25)
        )

        self.assertEqual(first, second)
        self.assertEqual(first, third)
        self.assertEqual((25, 0), self.authority.exposure(GRANDCHILD_SCOPE, "tokens"))

    # ------------------------------------------------------------------
    # 5. Full root->leaf ancestry is pinned from AccountingScopeResolver.
    # ------------------------------------------------------------------

    def test_ancestry_snapshot_is_full_root_to_leaf_chain(self) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:1", "tokens", 1000),))
        reservation = self.authority.reserve(self._request("req:ancestry"))

        self.assertEqual(
            (ROOT_SCOPE, CHILD_SCOPE, GRANDCHILD_SCOPE), reservation.ancestry_snapshot
        )

    # ------------------------------------------------------------------
    # 6/7/8. Hard ancestor limit denies a child even with local capacity;
    # denial leaves zero partial ancestor reserve; success updates every
    # ancestor atomically.
    # ------------------------------------------------------------------

    def test_hard_ancestor_limit_denies_despite_local_capacity_no_partial_reserve(
        self,
    ) -> None:
        # Root is tight (limit 50); leaf-local policy would allow far more.
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:root", "tokens", 50),))
        self._publish_policy(
            GRANDCHILD_SCOPE, (self._rule("rule:leaf", "tokens", 10_000),)
        )

        denied = self.authority.reserve(self._request("req:ancestor-deny", amount=60))

        self.assertEqual("DENIED", denied.state)
        self.assertEqual("ANCESTOR_LIMIT_EXCEEDED", denied.deny_reason_code)
        self.assertEqual((), denied.reserved_dimensions)
        for scope_ref in (ROOT_SCOPE, CHILD_SCOPE, GRANDCHILD_SCOPE):
            with self.subTest(scope=scope_ref):
                self.assertEqual((0, 0), self.authority.exposure(scope_ref, "tokens"))

    def test_successful_reserve_updates_every_ancestor_atomically(self) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:root", "tokens", 1000),))

        self.authority.reserve(self._request("req:atomic", amount=42))

        for scope_ref in (ROOT_SCOPE, CHILD_SCOPE, GRANDCHILD_SCOPE):
            with self.subTest(scope=scope_ref):
                self.assertEqual((42, 0), self.authority.exposure(scope_ref, "tokens"))

    # ------------------------------------------------------------------
    # 9. Two sequential reservations cannot oversubscribe remaining capacity.
    # ------------------------------------------------------------------

    def test_sequential_reservations_cannot_oversubscribe(self) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:root", "tokens", 100),))

        first = self.authority.reserve(self._request("req:seq-1", amount=60))
        second = self.authority.reserve(self._request("req:seq-2", amount=60))

        self.assertEqual("RESERVED", first.state)
        self.assertEqual("DENIED", second.state)
        self.assertEqual("ANCESTOR_LIMIT_EXCEEDED", second.deny_reason_code)
        self.assertEqual((60, 0), self.authority.exposure(ROOT_SCOPE, "tokens"))

    def test_local_scope_hard_limit_reports_hard_limit_exceeded(self) -> None:
        self._publish_policy(GRANDCHILD_SCOPE, (self._rule("rule:leaf", "tokens", 50),))

        denied = self.authority.reserve(self._request("req:local-deny", amount=60))

        self.assertEqual("DENIED", denied.state)
        self.assertEqual("HARD_LIMIT_EXCEEDED", denied.deny_reason_code)

    # ------------------------------------------------------------------
    # 10. Policy revision is pinned; later publication does not rewrite
    # prior reservation basis.
    # ------------------------------------------------------------------

    def test_policy_revision_pinned_later_publication_does_not_rewrite(self) -> None:
        v1 = self._publish_policy(ROOT_SCOPE, (self._rule("rule:root", "tokens", 1000),))
        reservation = self.authority.reserve(self._request("req:pinned", amount=10))
        self.assertIn(v1.budget_policy_revision_ref, reservation.policy_revision_refs)

        v2 = self._publish_policy(
            ROOT_SCOPE,
            (self._rule("rule:root-v2", "tokens", 5),),
            ref="policy:accounting:budget/root@2",
            effective_from=1,
            supersedes_ref=v1.budget_policy_revision_ref,
        )
        self.assertNotEqual(v1, v2)

        unchanged = self.authority.resolve(reservation.reservation_ref)
        self.assertEqual(reservation, unchanged)
        self.assertIn(v1.budget_policy_revision_ref, unchanged.policy_revision_refs)
        self.assertNotIn(v2.budget_policy_revision_ref, unchanged.policy_revision_refs)

    # ------------------------------------------------------------------
    # 11. DENIED reservation does not auto-revive under later policy.
    # (also covers §H "DENIED replay -> same denial")
    # ------------------------------------------------------------------

    def test_denied_reservation_does_not_auto_revive_under_later_policy(self) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:root", "tokens", 10),))
        request = self._request("req:denied-fixed", amount=50)
        denied = self.authority.reserve(request)
        self.assertEqual("DENIED", denied.state)

        # Time advances past a hypothetical widened effective window, but the
        # published revision for ROOT_SCOPE at the SAME ref is immutable, so
        # simulate a policy change by publishing a new, more permissive
        # revision effective later, then replay the exact same request_ref.
        self.now = 200
        self._publish_policy(
            ROOT_SCOPE,
            (self._rule("rule:root-wide", "tokens", 10_000),),
            ref="policy:accounting:budget/root@wide",
            effective_from=150,
            supersedes_ref="policy:accounting:budget/root@1",
        )

        replay = self.authority.reserve(request)
        self.assertEqual(denied, replay)
        self.assertEqual("DENIED", replay.state)

    # ------------------------------------------------------------------
    # 12. Stale/different Attempt does not dynamically reassign static
    # accounting membership.
    # ------------------------------------------------------------------

    def test_scope_resolution_ignores_attempt_seq(self) -> None:
        parameters = inspect.signature(AccountingScopeResolver.resolve).parameters
        self.assertNotIn("attempt_seq", parameters)

        self._publish_policy(ROOT_SCOPE, (self._rule("rule:root", "tokens", 1000),))
        low = self.authority.reserve(
            self._request("req:attempt-1", attempt_seq=1, amount=5)
        )
        RunRepository(self.store).replace_attempt(
            run_ref=RUN, expected_attempt_seq=1, expected_fencing_generation=1
        )
        high = self.authority.reserve(
            self._request("req:attempt-2", attempt_seq=2, amount=5)
        )

        self.assertEqual(low.ancestry_snapshot, high.ancestry_snapshot)
        self.assertEqual(low.accounting_scope_ref, high.accounting_scope_ref)

    # ------------------------------------------------------------------
    # 13. No Packet/PWP/current-pointer input participates in historical
    # membership -- source inspection of this Task's own new module.
    # ------------------------------------------------------------------

    def test_budget_authority_source_excludes_dynamic_provenance_inputs(self) -> None:
        source = inspect.getsource(budget_authority_module).lower()
        for forbidden in ("packet", "delivery_edge", "current_workspace", "current_project", "pwp"):
            self.assertNotIn(forbidden, source)

    # ------------------------------------------------------------------
    # 14. BudgetReservation state does not mutate EffectOperation /
    # ResourceLease / CapabilityGrant.
    # ------------------------------------------------------------------

    def test_budget_authority_never_touches_other_owner_tables(self) -> None:
        source = inspect.getsource(budget_authority_module)
        for table in (
            "effect_operations",
            "resource_leases",
            "resources ",
            "capability_grants",
            "run_attempts SET",
            "runs SET",
        ):
            self.assertNotIn(table, source)

        mutation_targets = [
            target
            for target in re.findall(
                r"\b(?:INSERT\s+INTO|(?<!DO )UPDATE)\s+([A-Za-z_][A-Za-z0-9_]*)",
                source,
                re.IGNORECASE,
            )
            if target.upper() != "SET"
        ]
        self.assertTrue(mutation_targets, "expected to find at least one mutation statement")
        for target in mutation_targets:
            with self.subTest(target=target):
                self.assertTrue(
                    target.startswith("budget_"),
                    f"unexpected canonical mutation target table: {target!r}",
                )

    # ------------------------------------------------------------------
    # 15. Transaction failure leaves no partial child/ancestor exposure.
    # (§H "failure/exception before transaction commit")
    # ------------------------------------------------------------------

    def test_crash_after_exposure_increment_before_commit_leaves_no_partial_state(
        self,
    ) -> None:
        self._publish_policy(ROOT_SCOPE, (self._rule("rule:root", "tokens", 1000),))

        def crash(stage: str) -> None:
            if stage == "AFTER_EXPOSURE_INCREMENT":
                raise InjectedCrash

        crashing_authority = self._authority(crash_hook=crash)
        with self.assertRaises(InjectedCrash):
            crashing_authority.reserve(self._request("req:crash", amount=77))

        for scope_ref in (ROOT_SCOPE, CHILD_SCOPE, GRANDCHILD_SCOPE):
            with self.subTest(scope=scope_ref):
                self.assertEqual((0, 0), self.authority.exposure(scope_ref, "tokens"))
        self.assertIsNone(self.authority.resolve_by_request("req:crash"))

        # Replay after the crash (no partial row exists) must process once,
        # cleanly, from scratch.
        recovered = self.authority.reserve(self._request("req:crash", amount=77))
        self.assertEqual("RESERVED", recovered.state)
        self.assertEqual((77, 0), self.authority.exposure(ROOT_SCOPE, "tokens"))

    # ------------------------------------------------------------------
    # 16. No raw cross-owner canonical mutation path is added.
    # ------------------------------------------------------------------

    def test_no_raw_cross_owner_mutation_imports(self) -> None:
        source = inspect.getsource(budget_authority_module)
        for forbidden_import in (
            "from nyron_kernel.effect",
            "from nyron_kernel.resource",
            "from nyron_kernel.capability",
            "from nyron_kernel.execution",
        ):
            self.assertNotIn(forbidden_import, source)

    # ------------------------------------------------------------------
    # Additional: unsupported dimension request amount / shape validation,
    # SOFT rules never deny, unresolved scope fails closed.
    # ------------------------------------------------------------------

    def test_soft_rule_never_denies(self) -> None:
        self._publish_policy(
            ROOT_SCOPE, (self._rule("rule:soft", "tokens", 1, enforcement="SOFT"),)
        )
        reservation = self.authority.reserve(self._request("req:soft", amount=999))
        self.assertEqual("RESERVED", reservation.state)

    def test_unresolved_accounting_scope_fails_closed(self) -> None:
        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.reserve(
                self._request(
                    "req:missing-scope",
                    accounting_scope_ref="accounting:missing",
                    definition_anchor_ref="does-not-exist",
                )
            )
        self.assertEqual("ACCOUNTING_SCOPE_INVALID", raised.exception.code)

    def test_malformed_reservation_request_rejected(self) -> None:
        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.reserve(
                dataclasses.replace(self._request("req:bad"), attempt_seq=0)
            )
        self.assertEqual("RESERVATION_REQUEST_INVALID", raised.exception.code)

        with self.assertRaises(BudgetAuthorityError) as raised:
            self.authority.reserve(
                dataclasses.replace(
                    self._request("req:bad-dim"),
                    reserved_dimensions=(("tokens", -5),),
                )
            )
        self.assertEqual("RESERVATION_REQUEST_INVALID", raised.exception.code)


if __name__ == "__main__":
    unittest.main()
