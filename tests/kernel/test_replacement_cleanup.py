"""Adversarial coverage for ARE-GATE-4B exact-R1 cleanup."""

from __future__ import annotations

import inspect
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from nyron_kernel.capability import (
    CapabilityAuthority,
    CapabilityDecision,
    CapabilityRequest,
    CapabilityTypeDefinition,
    CapabilityTypeRegistry,
)
from nyron_kernel.effect import EffectAuthority, EffectError, EffectRequest
from nyron_kernel.execution import (
    ReplacementCleanup,
    ReplacementCleanupError,
    RunRepository,
    RuntimeAuthorityResolver,
)
from nyron_kernel.resource import ResourceManager, ResourceRequest
from nyron_kernel.store import SQLiteStore


GRAPH = "graph:replacement-cleanup@1"
MODULE = "module-instance-revision:replacement-cleanup@1"
EXECUTION = "execution:replacement-cleanup/1"
ACTIVATION = "activation:replacement-cleanup/1"
RUN = "run:replacement-cleanup/1"
RESOURCE = "resource:replacement-cleanup/1"
CAPABILITY_TYPE = "capability.managed-resource-bounded-write"
CAPABILITY_VERSION = "1"
SCOPE_SCHEMA = "schema:bounded-effect-scope@1"


class InjectedCrash(RuntimeError):
    pass


class ReplacementCleanupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.store = SQLiteStore(self.base / "cleanup.db")
        self._seed_runtime()
        self.runs = RunRepository(self.store)
        self.runtime = RuntimeAuthorityResolver(self.store)
        self.r1 = self.runtime.resolve_current(RUN)
        assert self.r1 is not None
        self.now = 100

        registry = CapabilityTypeRegistry(self.store)
        registry.register(
            CapabilityTypeDefinition(
                CAPABILITY_TYPE,
                CAPABILITY_VERSION,
                SCOPE_SCHEMA,
                None,
                (EffectAuthority.EFFECT_CLASS,),
                {"description": "replacement cleanup test"},
            )
        )
        self.capability = CapabilityAuthority(
            self.store,
            registry,
            self.runtime,
            lambda _request: CapabilityDecision("GRANTED", "decision:cleanup/1"),
            self._scope_validator,
            lambda: self.now,
        )
        self.resource = ResourceManager(
            self.store,
            self.base / "managed-root",
            self.runtime,
            lambda: self.now,
        )
        self.resource.provision(
            ResourceRequest(
                RESOURCE,
                ResourceManager.RESOURCE_TYPE,
                "resource-manager:kernel",
                {"workspace_ref": "workspace:replacement-cleanup"},
            )
        )
        self.r1_lease = self._issue_lease("lease:r1", self.r1)
        self.r1_grant = self._issue_grant("grant:r1", self.r1)
        self.effect = self._effect_authority()
        self.cleanup = ReplacementCleanup(self.store, self.effect, self.resource)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def _seed_runtime(self) -> None:
        RunRepository(self.store)
        with self.store.transaction() as connection:
            connection.execute(
                "INSERT INTO graph_revisions VALUES (?, '{}', 1, NULL)",
                (GRAPH,),
            )
            connection.execute(
                """
                INSERT INTO module_instance_revisions VALUES (
                    ?, ?, 'replacement-cleanup', 'test.cleanup', '1',
                    'config:cleanup@1', 'sha256:cleanup', '{}', '{}',
                    '["root"]', 'accounting:cleanup'
                )
                """,
                (MODULE, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO execution_admissions VALUES (
                    'admission:cleanup/1', ?, ?, 'policy:cleanup@1', 1,
                    'ADMITTED'
                )
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO workflow_executions VALUES (
                    ?, ?, 'admission:cleanup/1', 'policy:cleanup@1', 'ADMITTED'
                )
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO activations VALUES (
                    ?, ?, ?, ?, 'delivery:cleanup-trigger', '[]',
                    'accounting:cleanup', 'event:activation:cleanup/1'
                )
                """,
                (ACTIVATION, EXECUTION, GRAPH, MODULE),
            )
            connection.execute(
                "INSERT INTO activation_created_events VALUES ('event:activation:cleanup/1', ?, 'ActivationCreated')",
                (ACTIVATION,),
            )
        RunRepository(self.store).create_initial(
            run_ref=RUN,
            activation_ref=ACTIVATION,
            execution_ref=EXECUTION,
        )

    @staticmethod
    def _scope_validator(schema_ref: str, scope: object) -> bool:
        return (
            schema_ref == SCOPE_SCHEMA
            and isinstance(scope, dict)
            and set(scope) == {"effect_class", "resource_ref"}
            and scope["effect_class"] == EffectAuthority.EFFECT_CLASS
            and scope["resource_ref"] == RESOURCE
        )

    def _issue_grant(self, grant_ref, authority):
        return self.capability.issue(
            CapabilityRequest(
                grant_ref,
                CAPABILITY_TYPE,
                CAPABILITY_VERSION,
                authority,
                {"effect_class": EffectAuthority.EFFECT_CLASS, "resource_ref": RESOURCE},
                "capability-authority:test",
            ),
            expires_at=200,
        )

    def _issue_lease(self, lease_ref, authority):
        return self.resource.issue_lease(
            lease_ref,
            RESOURCE,
            f"holder:{lease_ref}",
            authority,
            expires_at=200,
        )

    def _effect_authority(self, hook=None):
        return EffectAuthority(
            self.store,
            self.runtime,
            self.capability,
            self.resource,
            lambda: self.now,
            hook,
        )

    def _request(
        self,
        operation_ref: str,
        authority=None,
        grant_ref: str = "grant:r1",
        lease_ref: str = "lease:r1",
    ) -> EffectRequest:
        return EffectRequest(
            operation_ref,
            EffectAuthority.EFFECT_CLASS,
            authority or self.r1,
            grant_ref,
            RESOURCE,
            lease_ref,
            f"payload:{operation_ref}",
            "activation-output:cleanup/1",
        )

    def _leave_active(self, operation_ref: str):
        def crash(stage, _operation):
            if stage == "AFTER_ACTIVE_COMMIT":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._effect_authority(crash).execute(self._request(operation_ref))
        operation = self.effect.resolve(operation_ref)
        assert operation is not None
        self.assertEqual("ACTIVE", operation.state)
        return operation

    def _replace(self):
        self.runs.replace_attempt(
            run_ref=RUN,
            expected_attempt_seq=self.r1.attempt_seq,
            expected_fencing_generation=self.r1.fencing_generation,
        )
        r2 = self.runtime.resolve_current(RUN)
        assert r2 is not None
        return r2

    def test_exact_attempt_scoping_leaves_same_run_r2_rows_unchanged(self):
        self.effect.prepare(self._request("operation:r1"))
        r2 = self._replace()
        self._issue_grant("grant:r2", r2)
        self._issue_lease("lease:r2", r2)
        self.effect.prepare(
            self._request(
                "operation:r2", r2, grant_ref="grant:r2", lease_ref="lease:r2"
            )
        )
        r2_effect_before = self._row("effect_operations", "operation_ref", "operation:r2")
        r2_lease_before = self._row("resource_leases", "lease_ref", "lease:r2")

        result = self.cleanup.cleanup(self.r1)

        self.assertEqual(["FENCED"], [item.state for item in result.effects])
        self.assertEqual(["REVOKE_REQUESTED"], [item.state for item in result.leases])
        self.assertEqual(r2_effect_before, self._row("effect_operations", "operation_ref", "operation:r2"))
        self.assertEqual(r2_lease_before, self._row("resource_leases", "lease_ref", "lease:r2"))

    def test_not_replaced_and_corrupted_r1_tuple_fail_closed_before_owner_calls(self):
        with self.assertRaises(ReplacementCleanupError) as not_replaced:
            self.cleanup.cleanup(self.r1)
        self.assertEqual("REPLACED_ATTEMPT_NOT_PROVEN", not_replaced.exception.code)

        corrupted = replace(self.r1, execution_ref="execution:corrupt")
        self.effect.prepare(self._request("operation:corrupt", corrupted))
        self._replace()
        with self.assertRaises(ReplacementCleanupError) as mismatch:
            self.cleanup.cleanup(self.r1)
        self.assertEqual("REPLACED_ATTEMPT_TUPLE_MISMATCH", mismatch.exception.code)
        self.assertEqual("PREPARED", self.effect.resolve("operation:corrupt").state)
        self.assertEqual("ACTIVE", self.resource.resolve_lease("lease:r1").state)

    def test_prepared_absent_fences_and_substituted_target_becomes_unknown(self):
        absent = self.effect.prepare(self._request("operation:prepared-absent"))
        mismatch = self.effect.prepare(self._request("operation:prepared-mismatch"))
        Path(mismatch.target_ref).write_text("substituted", encoding="utf-8")
        self._replace()

        self.cleanup.cleanup(self.r1)

        fenced = self.effect.resolve(absent.operation_ref)
        unknown = self.effect.resolve(mismatch.operation_ref)
        self.assertEqual("FENCED", fenced.state)
        self.assertEqual("PREPARED_NEVER_ACTIVE", fenced.fence_evidence["basis"])
        self.assertEqual("UNKNOWN", unknown.state)
        self.assertFalse(Path(absent.target_ref).exists())

    def test_active_without_completion_never_fabricates_fenced(self):
        operation = self._leave_active("operation:active-absent")
        self._replace()

        self.cleanup.cleanup(self.r1)

        resolved = self.effect.resolve(operation.operation_ref)
        self.assertEqual("UNKNOWN", resolved.state)
        self.assertIsNone(resolved.fence_evidence)
        self.assertFalse(Path(resolved.target_ref).exists())

    def test_replacement_context_does_not_reintroduce_false_fenced_race(self):
        operation = self._leave_active("operation:false-fenced-race")
        self._replace()

        self.cleanup.cleanup(self.r1)
        resolved = self.effect.resolve(operation.operation_ref)
        self.assertEqual("UNKNOWN", resolved.state)
        self.assertIsNone(resolved.fence_evidence)

        with self.assertRaises(EffectError) as resumed_executor:
            self.effect._mutate_and_complete(resolved)
        self.assertEqual(
            "EFFECT_OPERATION_NOT_MUTABLE", resumed_executor.exception.code
        )
        self.assertFalse(Path(resolved.target_ref).exists())
        self.assertNotEqual("FENCED", self.effect.resolve(operation.operation_ref).state)

    def test_active_and_revoke_requested_with_exact_completion_become_completed(self):
        active = self._leave_active("operation:active-exact")
        Path(active.target_ref).write_text(active.payload, encoding="utf-8")
        requested = self._leave_active("operation:requested-exact")
        Path(requested.target_ref).write_text(requested.payload, encoding="utf-8")
        self.effect.request_revoke(requested.operation_ref)
        self._replace()

        self.cleanup.cleanup(self.r1)

        for operation in (active, requested):
            resolved = self.effect.resolve(operation.operation_ref)
            self.assertEqual("COMPLETED", resolved.state)
            self.assertEqual(operation.payload_hash, resolved.completion_evidence["payload_hash"])
            before = resolved.completion_evidence
            self.cleanup.cleanup(self.r1)
            self.assertEqual(before, self.effect.resolve(operation.operation_ref).completion_evidence)

    def test_only_executor_can_supply_stop_before_first_mutation_evidence(self):
        active = self._leave_active("operation:executor-stop")
        self._replace()
        original_resolve = self.effect.resolve_revoke

        def executor_resumes_then_resolve(operation_ref):
            current = self.effect.resolve(operation_ref)
            self.effect._mutate_and_complete(current)
            return original_resolve(operation_ref)

        self.effect.resolve_revoke = executor_resumes_then_resolve
        self.cleanup.cleanup(self.r1)

        resolved = self.effect.resolve(active.operation_ref)
        self.assertEqual("FENCED", resolved.state)
        self.assertEqual(
            "EXECUTOR_STOPPED_BEFORE_FIRST_MUTATION",
            resolved.fence_evidence["basis"],
        )
        self.assertFalse(Path(resolved.target_ref).exists())

    def test_active_r1_lease_revoked_while_r2_and_inactive_r1_leases_untouched(self):
        inactive = self._issue_lease("lease:r1-inactive", self.r1)
        self.resource.release_lease(inactive.lease_ref)
        r2 = self._replace()
        self._issue_lease("lease:r2", r2)
        inactive_before = self._row("resource_leases", "lease_ref", inactive.lease_ref)
        r2_before = self._row("resource_leases", "lease_ref", "lease:r2")

        self.cleanup.cleanup(self.r1)

        self.assertEqual("REVOKE_REQUESTED", self.resource.resolve_lease("lease:r1").state)
        self.assertEqual(inactive_before, self._row("resource_leases", "lease_ref", inactive.lease_ref))
        self.assertEqual(r2_before, self._row("resource_leases", "lease_ref", "lease:r2"))

    def test_cleanup_replay_is_idempotent_and_contains_no_owner_table_writes(self):
        operation = self.effect.prepare(self._request("operation:replay"))
        self._replace()
        first = self.cleanup.cleanup(self.r1)
        effect_before = self._row("effect_operations", "operation_ref", operation.operation_ref)
        lease_before = self._row("resource_leases", "lease_ref", "lease:r1")

        second = self.cleanup.cleanup(self.r1)

        self.assertEqual((), second.effects)
        self.assertEqual((), second.leases)
        self.assertEqual(effect_before, self._row("effect_operations", "operation_ref", operation.operation_ref))
        self.assertEqual(lease_before, self._row("resource_leases", "lease_ref", "lease:r1"))
        source = inspect.getsource(ReplacementCleanup).lower()
        for verb in ("update ", "insert ", "delete "):
            self.assertNotIn(verb, source)

    def _row(self, table: str, key: str, value: str):
        row = self.store.connection.execute(
            f"SELECT * FROM {table} WHERE {key} = ?", (value,)
        ).fetchone()
        assert row is not None
        return tuple(row)
