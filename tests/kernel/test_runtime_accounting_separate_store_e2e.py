from __future__ import annotations

import dataclasses
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
from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.execution import (
    ActivationRepository,
    RunRepository,
    RuntimeAuthorityResolver,
)
from nyron_kernel.recovery import RecoveryEvidence, RecoveryRepository
from nyron_kernel.resource import ResourceManager, ResourceRequest
from nyron_kernel.store import SQLiteStore


GRAPH = "graph:cross-owner@1"
MODULE = "module-instance:cross-owner@1"
EXECUTION = "execution:cross-owner/1"
ACTIVATION = "activation:cross-owner/1"
RUN = "run:cross-owner/1"
ROOT_SCOPE = "accounting:cross-owner/root"
CHILD_SCOPE = "accounting:cross-owner/child"


class InjectedCrash(RuntimeError):
    pass


class RuntimeAccountingSeparateStoreE2E(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.runtime_path = self.base / "runtime.db"
        self.accounting_path = self.base / "accounting.db"
        self.recovery_path = self.base / "recovery.db"
        self.now = 100
        self.runtime_store = SQLiteStore(self.runtime_path)
        self.accounting_store = SQLiteStore(self.accounting_path)
        self.recovery_store = SQLiteStore(self.recovery_path)
        self._seed_runtime()
        self._seed_accounting(limit=10)

    def tearDown(self) -> None:
        for name in ("runtime_store", "accounting_store", "recovery_store"):
            store = getattr(self, name, None)
            if store is not None:
                try:
                    store.close()
                except Exception:
                    pass
        self.temp.cleanup()

    def _seed_runtime(self) -> None:
        self.runtime_store.create_run_attempt_schema()
        with self.runtime_store.transaction() as connection:
            connection.execute(
                "INSERT INTO graph_revisions VALUES (?, '{}', 1, NULL)", (GRAPH,)
            )
            connection.execute(
                """
                INSERT INTO module_instance_revisions VALUES (
                    ?, ?, 'cross-owner', 'test.cross-owner', '1',
                    'config:cross-owner@1', 'sha256:config', '{}', '{}',
                    '["root"]', ?
                )
                """,
                (MODULE, GRAPH, CHILD_SCOPE),
            )
            connection.execute(
                "INSERT INTO execution_admissions VALUES ('admission:1', ?, ?, 'policy:runtime@1', 1, 'ADMITTED')",
                (EXECUTION, GRAPH),
            )
            connection.execute(
                "INSERT INTO workflow_executions VALUES (?, ?, 'admission:1', 'policy:runtime@1', 'ADMITTED')",
                (EXECUTION, GRAPH),
            )
            connection.execute(
                "INSERT INTO activations VALUES (?, ?, ?, ?, 'delivery:trigger', '[]', ?, 'event:activation')",
                (ACTIVATION, EXECUTION, GRAPH, MODULE, CHILD_SCOPE),
            )
            connection.execute(
                "INSERT INTO activation_created_events VALUES ('event:activation', ?, 'ActivationCreated')",
                (ACTIVATION,),
            )
        RunRepository(self.runtime_store).create_initial(
            run_ref=RUN, activation_ref=ACTIVATION, execution_ref=EXECUTION
        )

    def _seed_accounting(self, limit: int) -> None:
        resolver = AccountingScopeResolver(self.accounting_store)
        resolver.publish(
            AccountingScope(
                ROOT_SCOPE, GRAPH, GRAPH, None, "GRAPH",
                compute_ancestry_hash((ROOT_SCOPE,)), GRAPH, "ACTIVE",
            )
        )
        resolver.publish(
            AccountingScope(
                CHILD_SCOPE, GRAPH, MODULE, ROOT_SCOPE, "MODULE",
                compute_ancestry_hash((ROOT_SCOPE, CHILD_SCOPE)), MODULE, "ACTIVE",
            )
        )
        self._authority().publish_policy_revision(
            BudgetPolicyRevision(
                "policy:accounting@1", ROOT_SCOPE, 0, None,
                (BudgetDimension("tokens", "count", "sem:tokens@1"),),
                (BudgetRule("rule:tokens", "tokens", limit, "LIFETIME_LIMIT", "HARD"),),
                "accounting-admin:test", None,
            )
        )

    def _authority(self, crash_hook=None) -> BudgetAuthority:
        return BudgetAuthority(
            self.accounting_store,
            AccountingScopeResolver(self.accounting_store),
            ActivationRepository(self.runtime_store, ModuleRegistry(self.runtime_store)),
            RuntimeAuthorityResolver(self.runtime_store),
            lambda: self.now,
            crash_hook,
        )

    @staticmethod
    def _request(request_ref: str = "command:reserve/1", amount: int = 5):
        return BudgetReservationRequest(
            request_ref, ACTIVATION, RUN, 1, CHILD_SCOPE, GRAPH, MODULE,
            "estimate:1", (("tokens", amount),),
            ("effect-operation:1", "resource-lease:1"), "event:activation",
        )

    def test_schema_and_valid_admission_are_owner_local(self) -> None:
        reservation = self._authority().reserve(self._request())
        self.assertEqual("RESERVED", reservation.state)
        tables = {
            row[0] for row in self.accounting_store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertNotIn("runs", tables)
        self.assertNotIn("run_attempts", tables)
        self.assertEqual(RUN, reservation.run_ref)
        self.assertEqual(1, reservation.attempt_seq)

    def test_first_decision_requires_current_runtime_proof(self) -> None:
        with self.assertRaises(BudgetAuthorityError) as missing:
            self._authority().reserve(
                dataclasses.replace(self._request("command:missing"), run_ref="run:missing")
            )
        self.assertEqual("RESERVATION_RUNTIME_AUTHORITY_MISMATCH", missing.exception.code)

        RunRepository(self.runtime_store).replace_attempt(
            run_ref=RUN, expected_attempt_seq=1, expected_fencing_generation=1
        )
        with self.assertRaises(BudgetAuthorityError) as stale:
            self._authority().reserve(self._request("command:stale"))
        self.assertEqual("RESERVATION_RUNTIME_AUTHORITY_MISMATCH", stale.exception.code)

    def test_exact_replay_uses_accounting_truth_and_conflict_fails_closed(self) -> None:
        authority = self._authority()
        original = authority.reserve(self._request())
        self.runtime_store.close()
        self.assertEqual(original, authority.reserve(self._request()))
        with self.assertRaises(BudgetAuthorityError) as conflict:
            authority.reserve(dataclasses.replace(self._request(), estimate_ref="estimate:changed"))
        self.assertEqual("RESERVATION_REQUEST_CONFLICT", conflict.exception.code)
        self.assertEqual((5, 0), authority.exposure(CHILD_SCOPE, "tokens"))

    def test_crash_before_accounting_commit_then_restart_converges(self) -> None:
        def crash(stage: str) -> None:
            if stage == "AFTER_EXPOSURE_INCREMENT":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._authority(crash).reserve(self._request())
        self.assertIsNone(self._authority().resolve_by_request("command:reserve/1"))
        self.assertEqual((0, 0), self._authority().exposure(CHILD_SCOPE, "tokens"))

        self.accounting_store.close()
        self.accounting_store = SQLiteStore(self.accounting_path)
        committed = self._authority().reserve(self._request())
        self.assertEqual("RESERVED", committed.state)
        self.assertEqual((5, 0), self._authority().exposure(CHILD_SCOPE, "tokens"))

    def test_crash_after_commit_before_observation_replays_once_after_restart(self) -> None:
        committed = self._authority().reserve(self._request())
        self.accounting_store.close()  # caller loses the response after owner-local commit
        self.accounting_store = SQLiteStore(self.accounting_path)
        replayed = self._authority().reserve(self._request())
        self.assertEqual(committed, replayed)
        self.assertEqual((5, 0), self._authority().exposure(CHILD_SCOPE, "tokens"))

    def test_denial_and_recovery_evidence_do_not_mutate_resource_truth(self) -> None:
        runtime = RuntimeAuthorityResolver(self.runtime_store)
        attempt = runtime.resolve_current(RUN)
        assert attempt is not None
        manager = ResourceManager(
            self.runtime_store, self.base / "managed-root", runtime, lambda: self.now
        )
        resource = manager.provision(
            ResourceRequest(
                "resource:1", ResourceManager.RESOURCE_TYPE,
                "resource-manager:kernel", {"workspace_ref": "workspace:1"},
            )
        )
        lease = manager.issue_lease("resource-lease:1", resource.resource_ref, "holder:1", attempt)
        denied = self._authority().reserve(self._request(amount=11))
        self.assertEqual("DENIED", denied.state)
        self.assertEqual("ACTIVE", manager.resolve_lease(lease.lease_ref).state)

        recovery = RecoveryRepository(self.recovery_store, lambda: self.now)
        recovery.open_case(
            reconciliation_case_ref="case:lease-unknown", open_request_ref="open:lease-unknown",
            subject_owner_ref="resource-manager", subject_ref=lease.lease_ref,
            reason_code="RESOURCE_DETACHMENT_UNKNOWN", opened_by_ref="runtime:1",
            max_attempts=2, retry_policy_ref="retry:fixed", backoff_seconds=1,
            deadline=200, escalation_policy_ref="escalate:operator",
            caused_by_ref="event:lease-unknown",
        )
        evidence = RecoveryEvidence(
            "event:lease-unknown", "LeaseUnknown", "resource-manager",
            lease.lease_ref, lease.lease_ref, "payload:unknown", "sha256:unknown",
            99, 100, "AUTHENTICATED", "semantics:LeaseUnknown@1",
            "event:lease-unknown",
        )
        recovery.append_evidence("case:lease-unknown", evidence)
        self.assertEqual("ACTIVE", manager.resolve_lease(lease.lease_ref).state)
        self.assertEqual((), denied.committed_dimensions)


if __name__ == "__main__":
    unittest.main()
