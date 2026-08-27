"""Executable acceptance coverage for ARE-GATE-3A / Task 042."""

from __future__ import annotations

import inspect
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from nyron_kernel.capability import (
    CapabilityAuthority,
    CapabilityDecision,
    CapabilityError,
    CapabilityRequest,
    CapabilityTypeDefinition,
    CapabilityTypeRegistry,
)
from nyron_kernel.effect import (
    EffectAuthority,
    EffectError,
    EffectRequest,
    HistoricalOutcome,
)
from nyron_kernel.execution import RunRepository, RuntimeAuthorityResolver
from nyron_kernel.resource import ResourceError, ResourceManager, ResourceRequest
from nyron_kernel.store import SQLiteStore


GRAPH = "graph:effect@1"
MODULE = "module-instance-revision:effect@1"
EXECUTION = "execution:effect/1"
ACTIVATION = "activation:effect/1"
RUN = "run:effect/1"
RESOURCE = "resource:effect/1"
LEASE = "lease:effect/1"
GRANT = "grant:effect/1"
OPERATION = "effect-operation:bounded/1"
CAPABILITY_TYPE = "capability.managed-resource-bounded-write"
CAPABILITY_VERSION = "1"
SCOPE_SCHEMA = "schema:bounded-effect-scope@1"


class InjectedCrash(RuntimeError):
    pass


class EffectOperationFoundationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.database = self.base / "effect.db"
        self.root = self.base / "managed-root"
        self.store = SQLiteStore(self.database)
        self._seed_runtime(self.store)
        self.runtime = RuntimeAuthorityResolver(self.store)
        self.attempt = self.runtime.resolve_current(RUN)
        assert self.attempt is not None
        self.now = 100
        self.registry = CapabilityTypeRegistry(self.store)
        self.registry.register(self._capability_type())
        self.capability = self._capability_authority()
        self.resource = ResourceManager(
            self.store, self.root, self.runtime, lambda: self.now
        )
        self.resource.provision(self._resource_request())
        self.resource.issue_lease(
            LEASE, RESOURCE, "holder:trusted-effect", self.attempt,
            expires_at=200,
        )
        self._issue_grant(GRANT)
        self.effect = self._effect_authority()

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    @staticmethod
    def _seed_runtime(store: SQLiteStore) -> None:
        store.create_run_attempt_schema()
        with store.transaction() as connection:
            connection.execute(
                "INSERT INTO graph_revisions VALUES (?, '{}', 1, NULL)",
                (GRAPH,),
            )
            connection.execute(
                """
                INSERT INTO module_instance_revisions VALUES (
                    ?, ?, 'effect-test', 'test.effect', '1',
                    'config:effect@1', 'sha256:effect-config', '{}', '{}',
                    '["root"]', 'accounting:effect'
                )
                """,
                (MODULE, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO execution_admissions VALUES (
                    'admission:effect/1', ?, ?, 'policy:effect@1', 1, 'ADMITTED'
                )
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO workflow_executions VALUES (
                    ?, ?, 'admission:effect/1', 'policy:effect@1', 'ADMITTED'
                )
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO activations VALUES (
                    ?, ?, ?, ?, 'delivery:effect-trigger', '[]',
                    'accounting:effect', 'event:activation:effect/1'
                )
                """,
                (ACTIVATION, EXECUTION, GRAPH, MODULE),
            )
            connection.execute(
                """
                INSERT INTO activation_created_events VALUES (
                    'event:activation:effect/1', ?, 'ActivationCreated'
                )
                """,
                (ACTIVATION,),
            )
        RunRepository(store).create_initial(
            run_ref=RUN,
            activation_ref=ACTIVATION,
            execution_ref=EXECUTION,
        )

    @staticmethod
    def _capability_type() -> CapabilityTypeDefinition:
        return CapabilityTypeDefinition(
            capability_type_ref=CAPABILITY_TYPE,
            version=CAPABILITY_VERSION,
            scope_schema_ref=SCOPE_SCHEMA,
            operation_schema_ref=None,
            compatible_effect_classes=(EffectAuthority.EFFECT_CLASS,),
            metadata={"description": "exact bounded managed-resource write"},
        )

    def _capability_authority(self) -> CapabilityAuthority:
        def scope_validator(schema_ref: str, scope: object) -> bool:
            return (
                schema_ref == SCOPE_SCHEMA
                and isinstance(scope, dict)
                and set(scope) == {"effect_class", "resource_ref"}
                and scope["effect_class"] == EffectAuthority.EFFECT_CLASS
                and isinstance(scope["resource_ref"], str)
                and bool(scope["resource_ref"])
            )

        return CapabilityAuthority(
            self.store,
            self.registry,
            self.runtime,
            lambda _request: CapabilityDecision("GRANTED", "decision:effect/1"),
            scope_validator,
            lambda: self.now,
        )

    def _issue_grant(
        self,
        grant_ref: str,
        *,
        resource_ref: str = RESOURCE,
        expires_at: int | None = 200,
    ):
        return self.capability.issue(
            CapabilityRequest(
                grant_ref,
                CAPABILITY_TYPE,
                CAPABILITY_VERSION,
                self.attempt,
                {
                    "effect_class": EffectAuthority.EFFECT_CLASS,
                    "resource_ref": resource_ref,
                },
                "capability-authority:test",
            ),
            expires_at=expires_at,
        )

    @staticmethod
    def _resource_request(**changes) -> ResourceRequest:
        values = {
            "resource_ref": RESOURCE,
            "resource_type": ResourceManager.RESOURCE_TYPE,
            "resource_owner_ref": "resource-manager:kernel",
            "scope": {"workspace_ref": "workspace:effect-test"},
        }
        values.update(changes)
        return ResourceRequest(**values)

    def _effect_authority(self, hook=None) -> EffectAuthority:
        return EffectAuthority(
            self.store,
            self.runtime,
            self.capability,
            self.resource,
            lambda: self.now,
            hook,
        )

    def _request(self, **changes) -> EffectRequest:
        values = {
            "operation_ref": OPERATION,
            "effect_class": EffectAuthority.EFFECT_CLASS,
            "authority": self.attempt,
            "capability_grant_ref": GRANT,
            "resource_ref": RESOURCE,
            "resource_lease_ref": LEASE,
            "payload": "bounded payload",
            "caused_by_ref": "activation-output:effect/1",
        }
        values.update(changes)
        return EffectRequest(**values)

    def _target(self, operation_ref: str = OPERATION) -> Path:
        operation = self.effect.resolve(operation_ref)
        assert operation is not None
        return Path(operation.target_ref)

    def _leave_active(self, operation_ref: str = OPERATION):
        def crash(stage, _operation):
            if stage == "AFTER_ACTIVE_COMMIT":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._effect_authority(crash).execute(
                self._request(operation_ref=operation_ref)
            )
        operation = self.effect.resolve(operation_ref)
        assert operation is not None
        self.assertEqual("ACTIVE", operation.state)
        return operation

    def test_prepared_commits_before_mutation_and_contains_no_admission_claim(self):
        observed = []

        def crash(stage, operation):
            if stage == "AFTER_PREPARED_COMMIT":
                observed.append(operation)
                self.assertFalse(Path(operation.target_ref).exists())
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._effect_authority(crash).execute(self._request())
        prepared = self.effect.resolve(OPERATION)
        assert prepared is not None
        self.assertEqual([prepared], observed)
        self.assertEqual("PREPARED", prepared.state)
        self.assertIsNone(prepared.dispatch_admission_ref)
        self.assertIsNone(prepared.dispatch_admitted_at)
        self.assertIsNone(prepared.completion_evidence)

    def test_exact_attempt_and_fencing_are_required_at_dispatch(self):
        stale_values = (
            replace(self.attempt, execution_ref="execution:stale"),
            replace(self.attempt, activation_ref="activation:stale"),
            replace(self.attempt, run_ref="run:stale"),
            replace(self.attempt, attempt_seq=2),
            replace(self.attempt, fencing_token="fencing:stale"),
            replace(self.attempt, fencing_generation=2),
        )
        for index, stale in enumerate(stale_values):
            operation_ref = f"effect-operation:stale/{index}"
            with self.subTest(stale=stale), self.assertRaises(EffectError) as raised:
                self.effect.execute(
                    self._request(operation_ref=operation_ref, authority=stale)
                )
            self.assertIn(
                raised.exception.code,
                {
                    "EFFECT_DISPATCH_AUTHORITY_REJECTED",
                    "EFFECT_OPERATION_IDENTITY_CONFLICT",
                },
            )
            operation = self.effect.resolve(operation_ref)
            if operation is not None:
                self.assertEqual("FENCED", operation.state)
                self.assertIsNotNone(operation.fence_evidence)
                self.assertIsNone(operation.completion_evidence)
                self.assertFalse(Path(operation.target_ref).exists())

    def test_replacement_cutover_rejects_r1_at_all_existing_admission_boundaries(self):
        prepared = self.effect.prepare(self._request())
        RunRepository(self.store).replace_attempt(
            run_ref=RUN,
            expected_attempt_seq=self.attempt.attempt_seq,
            expected_fencing_generation=self.attempt.fencing_generation,
        )

        with self.assertRaises(CapabilityError) as capability_error:
            self._issue_grant("grant:effect/stale-r1")
        self.assertEqual("STALE_ATTEMPT_AUTHORITY", capability_error.exception.code)
        with self.assertRaises(ResourceError) as lease_error:
            self.resource.issue_lease(
                "lease:effect/stale-r1",
                RESOURCE,
                "holder:trusted-effect",
                self.attempt,
            )
        self.assertEqual("STALE_ATTEMPT_AUTHORITY", lease_error.exception.code)
        with self.assertRaises(EffectError) as effect_error:
            self.effect.execute(self._request())
        self.assertEqual("EFFECT_DISPATCH_AUTHORITY_REJECTED", effect_error.exception.code)
        fenced = self.effect.resolve(OPERATION)
        assert fenced is not None
        self.assertEqual("FENCED", fenced.state)
        self.assertFalse(Path(prepared.target_ref).exists())

    def test_attempt_becoming_stale_after_prepared_prevents_dispatch(self):
        prepared = self.effect.prepare(self._request())
        self.assertEqual("PREPARED", prepared.state)
        RunRepository(self.store).replace_attempt(
            run_ref=RUN,
            expected_attempt_seq=1,
            expected_fencing_generation=1,
        )
        with self.assertRaises(EffectError) as raised:
            self.effect.execute(self._request())
        self.assertEqual("EFFECT_DISPATCH_AUTHORITY_REJECTED", raised.exception.code)
        operation = self.effect.resolve(OPERATION)
        assert operation is not None
        self.assertEqual("FENCED", operation.state)
        self.assertIsNone(operation.dispatch_admission_ref)
        self.assertFalse(Path(operation.target_ref).exists())

    def test_exact_active_capability_and_machine_scope_are_required(self):
        wrong_grant = "grant:effect/wrong-scope"
        self._issue_grant(wrong_grant, resource_ref="resource:other")
        with self.assertRaises(EffectError):
            self.effect.execute(self._request(capability_grant_ref=wrong_grant))
        self.assertFalse(self._target().exists())

        operation_ref = "effect-operation:revoked"
        self.capability.revoke(GRANT)
        with self.assertRaises(EffectError):
            self.effect.execute(self._request(operation_ref=operation_ref))
        self.assertFalse(self._target(operation_ref).exists())

    def test_capability_expiry_before_admission_prevents_mutation(self):
        self.now = 200
        scope = {
            "effect_class": EffectAuthority.EFFECT_CLASS,
            "resource_ref": RESOURCE,
        }
        self.assertFalse(
            self.capability.validate_advisory(GRANT, self.attempt, scope).valid
        )
        self.assertEqual("EXPIRED", self.capability.resolve(GRANT).state)
        with self.assertRaises(EffectError):
            self.effect.execute(self._request())
        self.assertFalse(self._target().exists())

    def test_lease_expiry_before_admission_prevents_mutation(self):
        long_grant = "grant:effect/long"
        self._issue_grant(long_grant, expires_at=300)
        self.now = 200
        self.assertFalse(
            self.resource.validate_lease_advisory(
                LEASE, RESOURCE, "holder:trusted-effect", self.attempt
            ).valid
        )
        self.assertEqual("EXPIRED", self.resource.resolve_lease(LEASE).state)
        with self.assertRaises(EffectError):
            self.effect.execute(self._request(capability_grant_ref=long_grant))
        self.assertFalse(self._target().exists())

    def test_resource_and_exact_active_lease_are_independently_required(self):
        self.resource.release_lease(LEASE)
        with self.assertRaises(EffectError):
            self.effect.execute(self._request())
        self.assertFalse(self._target().exists())

        operation_ref = "effect-operation:resource-unavailable"
        with self.store.transaction() as connection:
            connection.execute(
                "UPDATE resources SET state = 'UNKNOWN' WHERE resource_ref = ?",
                (RESOURCE,),
            )
        with self.assertRaises(EffectError):
            self.effect.execute(self._request(operation_ref=operation_ref))
        self.assertFalse(self._target(operation_ref).exists())

        missing_lease_operation = "effect-operation:missing-lease"
        with self.assertRaises(EffectError):
            self.effect.execute(
                self._request(
                    operation_ref=missing_lease_operation,
                    resource_lease_ref="lease:missing",
                )
            )
        self.assertIsNone(self.effect.resolve(missing_lease_operation))

    def test_cached_advisory_results_cannot_authorize_after_revoke_and_release(self):
        scope = {
            "effect_class": EffectAuthority.EFFECT_CLASS,
            "resource_ref": RESOURCE,
        }
        self.assertTrue(
            self.capability.validate_advisory(GRANT, self.attempt, scope).valid
        )
        self.assertTrue(
            self.resource.validate_lease_advisory(
                LEASE, RESOURCE, "holder:trusted-effect", self.attempt
            ).valid
        )
        self.capability.revoke(GRANT)
        self.resource.release_lease(LEASE)
        with self.assertRaises(EffectError):
            self.effect.execute(self._request())
        self.assertFalse(self._target().exists())

    def test_dispatch_admission_is_durable_before_mutation_and_not_completion(self):
        def crash(stage, operation):
            if stage == "AFTER_DISPATCH_ADMISSION":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._effect_authority(crash).execute(self._request())
        admitted = self.effect.resolve(OPERATION)
        assert admitted is not None
        self.assertEqual("PREPARED", admitted.state)
        self.assertIsNotNone(admitted.dispatch_admission_ref)
        self.assertIsNotNone(admitted.dispatch_admitted_at)
        self.assertIsNone(admitted.completion_evidence)
        self.assertFalse(Path(admitted.target_ref).exists())
        self.assertEqual(admitted, self.effect.recover(OPERATION))

    def test_active_is_durable_after_admission_and_before_mutation(self):
        observed = []

        def crash(stage, operation):
            observed.append(stage)
            if stage == "AFTER_ACTIVE_COMMIT":
                current = self.effect.resolve(operation.operation_ref)
                assert current is not None
                self.assertEqual("ACTIVE", current.state)
                self.assertIsNotNone(current.dispatch_admission_ref)
                self.assertIsNone(current.completion_evidence)
                self.assertFalse(Path(current.target_ref).exists())
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._effect_authority(crash).execute(self._request())
        self.assertEqual(
            ["AFTER_PREPARED_COMMIT", "AFTER_DISPATCH_ADMISSION", "AFTER_ACTIVE_COMMIT"],
            observed,
        )
        active = self.effect.resolve(OPERATION)
        assert active is not None
        self.assertEqual("ACTIVE", active.state)

    def test_active_with_absent_evidence_recovers_unknown_and_never_retries(self):
        def crash(stage, _operation):
            if stage == "AFTER_ACTIVE_COMMIT":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._effect_authority(crash).execute(self._request())
        target = self._target()
        self.assertFalse(target.exists())
        recovered = self._effect_authority().recover(OPERATION)
        self.assertEqual("UNKNOWN", recovered.state)
        self.assertIsNone(recovered.completion_evidence)
        with self.assertRaises(EffectError):
            self.effect.execute(self._request())
        self.assertFalse(target.exists())

    def test_admission_wins_then_later_revoke_does_not_erase_inflight_work(self):
        def revoke_after_admission(stage, _operation):
            if stage == "AFTER_DISPATCH_ADMISSION":
                self.capability.revoke(GRANT)
                self.resource.release_lease(LEASE)

        completed = self._effect_authority(revoke_after_admission).execute(
            self._request()
        )
        self.assertEqual("COMPLETED", completed.state)
        self.assertEqual("REVOKED", self.capability.resolve(GRANT).state)
        self.assertEqual("RELEASED", self.resource.resolve_lease(LEASE).state)

    def test_mutation_is_deterministic_bounded_and_accepts_no_caller_path(self):
        completed = self.effect.execute(self._request(operation_ref="../../escape"))
        target = Path(completed.target_ref)
        resource = self.resource.resolve_resource(RESOURCE)
        assert resource is not None
        self.assertEqual(Path(resource.external_ref), target.parent)
        self.assertEqual("bounded payload", target.read_text())
        self.assertFalse((self.base / "escape").exists())
        self.assertNotIn("path", inspect.signature(EffectRequest).parameters)
        self.assertNotIn("target_ref", inspect.signature(EffectRequest).parameters)

    def test_crash_after_prepared_recovers_without_fabricating_dispatch(self):
        def crash(stage, _operation):
            if stage == "AFTER_PREPARED_COMMIT":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._effect_authority(crash).execute(self._request())
        recovered = self.effect.recover(OPERATION)
        self.assertEqual("PREPARED", recovered.state)
        self.assertIsNone(recovered.dispatch_admission_ref)
        self.assertFalse(Path(recovered.target_ref).exists())

    def test_crash_after_exact_mutation_recovers_completed_from_exact_evidence(self):
        def crash(stage, _operation):
            if stage == "AFTER_EXTERNAL_MUTATION":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._effect_authority(crash).execute(self._request())
        before = self.effect.resolve(OPERATION)
        assert before is not None
        self.assertEqual("ACTIVE", before.state)
        self.assertIsNotNone(before.dispatch_admission_ref)
        self.assertEqual(before.payload, Path(before.target_ref).read_text())
        recovered = self.effect.recover(OPERATION)
        self.assertEqual("COMPLETED", recovered.state)
        self.assertEqual(before.payload_hash, recovered.completion_evidence["payload_hash"])

    def test_mismatched_or_partial_external_evidence_becomes_unknown(self):
        def crash(stage, _operation):
            if stage == "AFTER_ACTIVE_COMMIT":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._effect_authority(crash).execute(self._request())
        target = self._target()
        target.write_text("partial or foreign")
        recovered = self.effect.recover(OPERATION)
        self.assertEqual("UNKNOWN", recovered.state)
        self.assertIsNone(recovered.completion_evidence)
        with self.assertRaises(EffectError):
            self.effect.execute(self._request())
        self.assertEqual("partial or foreign", target.read_text())

    def test_active_with_substituted_target_object_becomes_unknown(self):
        def crash(stage, _operation):
            if stage == "AFTER_ACTIVE_COMMIT":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._effect_authority(crash).execute(self._request())
        target = self._target()
        target.mkdir()
        (target / "foreign.txt").write_text("foreign")
        recovered = self._effect_authority().recover(OPERATION)
        self.assertEqual("UNKNOWN", recovered.state)
        self.assertIsNone(recovered.completion_evidence)
        self.assertEqual("foreign", (target / "foreign.txt").read_text())

    def test_active_revoke_request_is_durable_and_idempotent(self):
        self._leave_active()
        revoked = self.effect.request_revoke(OPERATION)
        self.assertEqual("REVOKE_REQUESTED", revoked.state)
        self.assertIsNone(revoked.completion_evidence)
        self.assertIsNone(revoked.fence_evidence)
        self.assertEqual(revoked, self.effect.request_revoke(OPERATION))

    def test_prepared_revoke_fences_only_exact_non_dispatch(self):
        prepared = self.effect.prepare(self._request())
        fenced = self.effect.request_revoke(OPERATION)
        self.assertEqual("FENCED", fenced.state)
        self.assertEqual(HistoricalOutcome.KNOWN, fenced.historical_outcome)
        self.assertEqual(
            "NONE_PROVEN",
            fenced.historical_outcome_evidence["evidence"]["consequence"],
        )
        self.assertIsNone(fenced.completion_evidence)
        self.assertEqual("PREPARED_NEVER_ACTIVE", fenced.fence_evidence["basis"])
        self.assertEqual("STOPPED", fenced.fence_evidence["continuation"])
        self.assertNotIn("safe_to_retry", fenced.fence_evidence)
        self.assertNotIn("no_effect", fenced.fence_evidence)
        self.assertFalse(Path(prepared.target_ref).exists())

    def test_prepared_revoke_with_external_evidence_fails_closed_unknown(self):
        prepared = self.effect.prepare(self._request())
        Path(prepared.target_ref).write_text(prepared.payload)
        resolved = self.effect.request_revoke(OPERATION)
        self.assertEqual("UNKNOWN", resolved.state)
        self.assertIsNone(resolved.fence_evidence)
        self.assertIsNone(resolved.completion_evidence)

    def test_revoke_resolution_prefers_exact_completion_evidence(self):
        def crash(stage, _operation):
            if stage == "AFTER_EXTERNAL_MUTATION":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._effect_authority(crash).execute(self._request())
        self.assertEqual(
            "REVOKE_REQUESTED", self.effect.request_revoke(OPERATION).state
        )
        completed = self.effect.resolve_revoke(OPERATION)
        self.assertEqual("COMPLETED", completed.state)
        self.assertIsNotNone(completed.completion_evidence)
        self.assertIsNone(completed.fence_evidence)

    def test_resolver_absence_cannot_claim_executor_cessation(self):
        self._leave_active()
        self.effect.request_revoke(OPERATION)
        resolved = self.effect.resolve_revoke(OPERATION)
        self.assertEqual("UNKNOWN", resolved.state)
        self.assertIsNone(resolved.completion_evidence)
        self.assertIsNone(resolved.fence_evidence)

    def test_executor_observes_revoke_and_fences_before_first_mutation(self):
        def revoke_after_active(stage, operation):
            if stage == "AFTER_ACTIVE_COMMIT":
                self.effect.request_revoke(operation.operation_ref)

        fenced = self._effect_authority(revoke_after_active).execute(self._request())
        self.assertEqual("FENCED", fenced.state)
        self.assertFalse(Path(fenced.target_ref).exists())
        self.assertIsNone(fenced.completion_evidence)
        self.assertEqual(
            "EXECUTOR_STOPPED_BEFORE_FIRST_MUTATION",
            fenced.fence_evidence["basis"],
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "UPDATE effect_operations SET fence_evidence_json = '{}' WHERE operation_ref = ?",
                (OPERATION,),
            )

    def test_reviewer_race_resolver_unknown_prevents_original_mutation(self):
        observed = []

        def revoke_and_resolve(stage, operation):
            if stage == "AFTER_ACTIVE_COMMIT":
                self.effect.request_revoke(operation.operation_ref)
                observed.append(self.effect.resolve_revoke(operation.operation_ref))

        with self.assertRaises(EffectError) as raised:
            self._effect_authority(revoke_and_resolve).execute(self._request())
        self.assertEqual("EFFECT_OPERATION_NOT_MUTABLE", raised.exception.code)
        self.assertEqual("UNKNOWN", observed[0].state)
        final = self.effect.resolve(OPERATION)
        assert final is not None
        self.assertEqual("UNKNOWN", final.state)
        self.assertIsNone(final.fence_evidence)
        self.assertFalse(Path(final.target_ref).exists())

    def test_revoke_resolution_mismatch_or_substitution_is_unknown(self):
        for index, substitute in enumerate((False, True)):
            if index:
                self.tearDown()
                self.setUp()
            operation_ref = f"effect-operation:revoke-ambiguous/{index}"
            self._leave_active(operation_ref)
            self.effect.request_revoke(operation_ref)
            target = self._target(operation_ref)
            if substitute:
                target.mkdir()
                (target / "foreign.txt").write_text("foreign")
            else:
                target.write_text("mismatch")
            resolved = self.effect.resolve_revoke(operation_ref)
            self.assertEqual("UNKNOWN", resolved.state)
            self.assertIsNone(resolved.completion_evidence)
            self.assertIsNone(resolved.fence_evidence)

    def test_capability_or_lease_end_alone_never_manufactures_fence(self):
        active = self._leave_active()
        self.capability.revoke(GRANT)
        self.resource.revoke_lease(LEASE)
        current = self.effect.resolve(OPERATION)
        assert current is not None
        self.assertEqual(active, current)
        self.assertEqual("ACTIVE", current.state)
        self.assertIsNone(current.fence_evidence)

    def test_capability_and_lease_expiry_alone_never_manufactures_fence(self):
        active = self._leave_active()
        self.now = 200
        self.capability.validate_advisory(
            GRANT,
            self.attempt,
            {"effect_class": EffectAuthority.EFFECT_CLASS, "resource_ref": RESOURCE},
        )
        self.resource.validate_lease_advisory(
            LEASE, RESOURCE, "holder:trusted-effect", self.attempt
        )
        self.assertEqual("EXPIRED", self.capability.resolve(GRANT).state)
        self.assertEqual("EXPIRED", self.resource.resolve_lease(LEASE).state)
        current = self.effect.resolve(OPERATION)
        assert current is not None
        self.assertEqual(active, current)
        self.assertEqual("ACTIVE", current.state)
        self.assertIsNone(current.fence_evidence)

    def test_fenced_never_retries_or_creates_replacement(self):
        self.effect.prepare(self._request())
        fenced = self.effect.request_revoke(OPERATION)
        before_count = self.store.connection.execute(
            "SELECT COUNT(*) FROM effect_operations"
        ).fetchone()[0]
        with self.assertRaises(EffectError):
            self.effect.execute(self._request())
        self.assertEqual(fenced, self.effect.resolve(OPERATION))
        self.assertEqual(
            before_count,
            self.store.connection.execute(
                "SELECT COUNT(*) FROM effect_operations"
            ).fetchone()[0],
        )

    def test_historical_outcome_is_deterministic_for_bounded_write(self):
        prepared = self.effect.prepare(self._request())
        self.assertEqual(HistoricalOutcome.UNKNOWN, prepared.historical_outcome)
        self.assertIsNone(prepared.historical_outcome_evidence)

        completed = self.effect.execute(self._request())
        self.assertEqual(HistoricalOutcome.KNOWN, completed.historical_outcome)
        self.assertEqual(
            "EXACT_COMPLETION_EVIDENCE",
            completed.historical_outcome_evidence["evidence"]["basis"],
        )

    def test_lifecycle_and_historical_outcome_refine_independently(self):
        active = self._leave_active()
        partial = self.effect.refine_historical_outcome(
            active.operation_ref,
            HistoricalOutcome.PARTIAL,
            {"evidence_ref": "evidence:partial/1", "observed": "PREFIX"},
        )
        self.assertEqual("ACTIVE", partial.state)
        self.assertEqual(HistoricalOutcome.PARTIAL, partial.historical_outcome)

    def test_fenced_unknown_and_partial_survive_restart(self):
        unknown_ref = "effect-operation:fenced-unknown/1"
        partial_ref = "effect-operation:fenced-partial/1"
        unknown = self.effect.prepare(self._request(operation_ref=unknown_ref))
        partial = self.effect.prepare(self._request(operation_ref=partial_ref))
        self.effect.refine_historical_outcome(
            partial_ref,
            HistoricalOutcome.PARTIAL,
            {"evidence_ref": "evidence:partial/2", "observed": "PARTIAL"},
        )
        for operation in (unknown, partial):
            fence_evidence = self.effect._canonical_json(
                self.effect._fence_evidence(operation, "TEST_CONFIRMED_STOP")
            )
            with self.store.transaction() as connection:
                connection.execute(
                    """
                    UPDATE effect_operations
                    SET state = 'FENCED', fence_evidence_json = ?
                    WHERE operation_ref = ?
                    """,
                    (fence_evidence, operation.operation_ref),
                )

        self.store.close()
        with SQLiteStore(self.database) as reopened:
            reopened.create_effect_schema()
            rows = {
                row["operation_ref"]: row
                for row in reopened.connection.execute(
                    """
                    SELECT operation_ref, state, historical_outcome
                    FROM effect_operations
                    WHERE operation_ref IN (?, ?)
                    """,
                    (unknown_ref, partial_ref),
                ).fetchall()
            }
            self.assertEqual("FENCED", rows[unknown_ref]["state"])
            self.assertEqual("UNKNOWN", rows[unknown_ref]["historical_outcome"])
            self.assertEqual("FENCED", rows[partial_ref]["state"])
            self.assertEqual("PARTIAL", rows[partial_ref]["historical_outcome"])
        self.store = SQLiteStore(self.database)

    def test_historical_outcome_replay_is_idempotent_and_conflict_closed(self):
        self.effect.prepare(self._request())
        evidence = {"evidence_ref": "evidence:partial/3", "observed": "PARTIAL"}
        first = self.effect.refine_historical_outcome(
            OPERATION, HistoricalOutcome.PARTIAL, evidence
        )
        self.assertEqual(
            first,
            self.effect.refine_historical_outcome(
                OPERATION, HistoricalOutcome.PARTIAL, evidence
            ),
        )
        with self.assertRaises(EffectError) as conflicting:
            self.effect.refine_historical_outcome(
                OPERATION,
                HistoricalOutcome.PARTIAL,
                {"evidence_ref": "evidence:conflict", "observed": "OTHER"},
            )
        self.assertEqual(
            "EFFECT_HISTORICAL_OUTCOME_REPLAY_CONFLICT",
            conflicting.exception.code,
        )
        known = self.effect.refine_historical_outcome(
            OPERATION,
            HistoricalOutcome.KNOWN,
            {"evidence_ref": "evidence:known/1", "observed": "TERMINAL"},
        )
        self.assertEqual(HistoricalOutcome.KNOWN, known.historical_outcome)
        with self.assertRaises(EffectError) as downgrade:
            self.effect.refine_historical_outcome(
                OPERATION, HistoricalOutcome.PARTIAL, evidence
            )
        self.assertEqual(
            "EFFECT_HISTORICAL_OUTCOME_DOWNGRADE", downgrade.exception.code
        )
        for invalid_outcome in ("PARTIAL", HistoricalOutcome.UNKNOWN):
            with self.subTest(outcome=invalid_outcome), self.assertRaises(
                EffectError
            ) as invalid:
                self.effect.refine_historical_outcome(
                    OPERATION, invalid_outcome, evidence
                )
            self.assertEqual(
                "EFFECT_HISTORICAL_OUTCOME_INVALID", invalid.exception.code
            )

    def test_persistence_rejects_raw_invalid_historical_transitions(self):
        self.effect.prepare(self._request())
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                """
                UPDATE effect_operations
                SET historical_outcome = 'PARTIAL'
                WHERE operation_ref = ?
                """,
                (OPERATION,),
            )
        with self.store.transaction() as connection:
            connection.execute(
                """
                UPDATE effect_operations
                SET historical_outcome = 'PARTIAL',
                    historical_outcome_evidence_json = '{}'
                WHERE operation_ref = ?
                """,
                (OPERATION,),
            )
        for statement in (
            """
            UPDATE effect_operations
            SET historical_outcome = 'UNKNOWN',
                historical_outcome_evidence_json = NULL
            WHERE operation_ref = ?
            """,
            """
            UPDATE effect_operations
            SET historical_outcome_evidence_json = '{"changed":true}'
            WHERE operation_ref = ?
            """,
            """
            UPDATE effect_operations
            SET historical_outcome = 'INVALID'
            WHERE operation_ref = ?
            """,
        ):
            with self.subTest(statement=statement), self.assertRaises(
                sqlite3.IntegrityError
            ):
                self.store.connection.execute(statement, (OPERATION,))

    def test_terminal_and_unknown_states_cannot_reactivate_by_code_or_sql(self):
        completed_ref = "effect-operation:terminal/completed"
        fenced_ref = "effect-operation:terminal/fenced"
        unknown_ref = "effect-operation:terminal/unknown"
        completed = self.effect.execute(self._request(operation_ref=completed_ref))
        self.effect.prepare(self._request(operation_ref=fenced_ref))
        fenced = self.effect.request_revoke(fenced_ref)
        unknown = self.effect.prepare(self._request(operation_ref=unknown_ref))
        Path(unknown.target_ref).write_text("foreign")
        unknown = self.effect.recover(unknown_ref)
        for operation in (completed, fenced, unknown):
            with self.subTest(state=operation.state), self.assertRaises(EffectError):
                self.effect._activate(operation)
            for target_state in ("ACTIVE", "PREPARED"):
                with self.subTest(
                    state=operation.state, target_state=target_state
                ), self.assertRaises(sqlite3.IntegrityError):
                    self.store.connection.execute(
                        "UPDATE effect_operations SET state = ? WHERE operation_ref = ?",
                        (target_state, operation.operation_ref),
                    )

    def test_unadmitted_preexisting_target_is_unknown_not_admitted_or_completed(self):
        prepared = self.effect.prepare(self._request())
        Path(prepared.target_ref).write_text(prepared.payload)
        recovered = self.effect.recover(OPERATION)
        self.assertEqual("UNKNOWN", recovered.state)
        self.assertIsNone(recovered.dispatch_admission_ref)
        self.assertIsNone(recovered.completion_evidence)
        with self.assertRaises(EffectError):
            self.effect.execute(self._request())

    def test_exact_replay_is_stable_and_every_binding_is_non_transferable(self):
        completed = self.effect.execute(self._request())
        self.assertEqual(completed, self.effect.execute(self._request()))
        conflicts = (
            {"effect_class": "other.effect@1"},
            {"authority": replace(self.attempt, fencing_generation=2)},
            {"capability_grant_ref": "grant:other"},
            {"resource_ref": "resource:other"},
            {"resource_lease_ref": "lease:other"},
            {"payload": "different"},
            {"caused_by_ref": "cause:other"},
        )
        for changes in conflicts:
            with self.subTest(changes=changes), self.assertRaises(EffectError) as raised:
                self.effect.execute(self._request(**changes))
            self.assertIn(
                raised.exception.code,
                {"EFFECT_OPERATION_IDENTITY_CONFLICT", "EFFECT_REQUEST_INVALID"},
            )

    def test_file_reopen_preserves_operation_and_recovers_exact_evidence(self):
        def crash(stage, _operation):
            if stage == "AFTER_EXTERNAL_MUTATION":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._effect_authority(crash).execute(self._request())
        before = self.effect.resolve(OPERATION)
        self.store.close()
        with SQLiteStore(self.database) as reopened:
            runtime = RuntimeAuthorityResolver(reopened)
            registry = CapabilityTypeRegistry(reopened)
            capability = CapabilityAuthority(
                reopened, registry, runtime,
                lambda _request: CapabilityDecision("DENIED"),
                lambda _schema, _scope: False,
                lambda: 100,
            )
            resource = ResourceManager(
                reopened, self.root, runtime, lambda: 100
            )
            effect = EffectAuthority(
                reopened, runtime, capability, resource, lambda: 100
            )
            self.assertEqual(before, effect.resolve(OPERATION))
            self.assertEqual("COMPLETED", effect.recover(OPERATION).state)
        self.store = SQLiteStore(self.database)

    def test_storage_constraints_backstop_identity_admission_and_state(self):
        self.effect.prepare(self._request())
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "UPDATE effect_operations SET payload_hash = 'changed' WHERE operation_ref = ?",
                (OPERATION,),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "UPDATE effect_operations SET state = 'ACTIVE' WHERE operation_ref = ?",
                (OPERATION,),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "UPDATE effect_operations SET state = 'FENCED' WHERE operation_ref = ?",
                (OPERATION,),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "UPDATE effect_operations SET fence_evidence_json = '{}' WHERE operation_ref = ?",
                (OPERATION,),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                """
                UPDATE effect_operations
                SET state = 'COMPLETED', completion_evidence_json = '{}'
                WHERE operation_ref = ?
                """,
                (OPERATION,),
            )
        with self.store.transaction() as connection:
            connection.execute(
                """
                UPDATE effect_operations
                SET dispatch_admission_ref = 'admission:test', dispatch_admitted_at = 100
                WHERE operation_ref = ?
                """,
                (OPERATION,),
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "UPDATE effect_operations SET dispatch_admission_ref = NULL, dispatch_admitted_at = NULL WHERE operation_ref = ?",
                (OPERATION,),
            )

    def test_no_generic_effect_or_trust_boundary_surface_is_introduced(self):
        source = inspect.getsource(EffectAuthority)
        for forbidden in (
            "Permit", "Ticket", "Provider", "Plugin", "CanonicalCommand",
            "Retry", "Replacement", "Reconciliation", "BudgetReservation",
            "EffectConflictScope",
        ):
            self.assertNotIn(forbidden, source)
        public = {
            name for name, function in inspect.getmembers(
                EffectAuthority, predicate=inspect.isfunction
            ) if not name.startswith("_")
        }
        self.assertEqual(
            {
                "execute", "prepare", "recover", "resolve",
                "request_revoke", "resolve_revoke", "refine_historical_outcome",
            },
            public,
        )
        self.assertFalse(hasattr(self.effect, "module"))
        self.assertFalse(hasattr(self.effect, "managed_root"))
        self.assertNotIn("ResourceManager", inspect.signature(EffectRequest).parameters)
        for forbidden in ("threading", "asyncio", "multiprocessing", "ThreadPool"):
            self.assertNotIn(forbidden, source)
        transaction_source = inspect.getsource(SQLiteStore.transaction)
        self.assertIn('execute("BEGIN IMMEDIATE")', transaction_source)


if __name__ == "__main__":
    unittest.main()
