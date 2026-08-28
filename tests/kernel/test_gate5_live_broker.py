"""Focused executable contract for Task 070's Gate-5 live broker."""

from __future__ import annotations

import dataclasses
import tempfile
import unittest
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path

from nyron_kernel.capability import (
    CapabilityAuthority,
    CapabilityDecision,
    CapabilityRequest,
    CapabilityTypeDefinition,
    CapabilityTypeRegistry,
)
from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.effect import EffectAuthority, EffectError, EffectRequest
from nyron_kernel.execution import (
    ActivationRepository,
    RunRepository,
    RuntimeAuthorityResolver,
)
from nyron_kernel.host import (
    BoundedWriteDispatched,
    BoundedWriteIdentityConflict,
    BoundedWriteRejected,
    BoundedWriteUnknown,
    CapabilityHandle,
    ModelInvokeDispatched,
    ModelInvokeIdentityConflict,
    ModelInvokeRejected,
    ModelInvokeUnknown,
    ResourceHandle,
    RuntimeContext,
    TrustedHostError,
    TrustedModuleHost,
    build_runtime_context,
)
from nyron_kernel.host import trusted_host
from nyron_kernel.modules import builtin_text_concat
from nyron_kernel.resource import ResourceManager, ResourceRequest
from nyron_kernel.store import SQLiteStore


class InjectedCrash(RuntimeError):
    pass


class Gate5LiveBrokerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = SQLiteStore(self.root / "kernel.db")
        self.registry = ModuleRegistry(self.store)
        self._seed_runtime()
        self.runtime = RuntimeAuthorityResolver(self.store)
        self.attempt = self.runtime.resolve_current("run:gate5/1")
        assert self.attempt is not None
        self.now = 100
        self.capability_types = CapabilityTypeRegistry(self.store)
        self.capability_types.register(
            CapabilityTypeDefinition(
                "capability.managed-resource-bounded-write",
                "1",
                "schema:gate5-scope@1",
                None,
                (EffectAuthority.EFFECT_CLASS,),
                {},
            )
        )
        self.capability_types.register(
            CapabilityTypeDefinition(
                "capability.model-invoke",
                "1",
                "schema:model-invoke-scope@1",
                None,
                (EffectAuthority.MODEL_INVOKE_EFFECT_CLASS,),
                {},
            )
        )
        self.capability = CapabilityAuthority(
            self.store,
            self.capability_types,
            self.runtime,
            lambda _request: CapabilityDecision("GRANTED", "decision:gate5"),
            self._scope_valid,
            lambda: self.now,
        )
        self.resources = ResourceManager(
            self.store, self.root / "managed", self.runtime, lambda: self.now
        )
        self.resources.provision(self._resource_request("resource:gate5/1"))
        self.resources.provision(self._resource_request("resource:gate5/2"))
        self.lease1 = self.resources.issue_lease(
            "lease:gate5/1", "resource:gate5/1", "holder:gate5", self.attempt, expires_at=200
        )
        self.lease2 = self.resources.issue_lease(
            "lease:gate5/2", "resource:gate5/2", "holder:gate5", self.attempt, expires_at=200
        )
        self.grant1 = self._grant("grant:gate5/1", "resource:gate5/1")
        self.grant1b = self._grant("grant:gate5/1b", "resource:gate5/1")
        self.grant2 = self._grant("grant:gate5/2", "resource:gate5/2")
        self.model_grant = self.capability.issue(
            CapabilityRequest(
                "grant:gate5/model",
                "capability.model-invoke",
                "1",
                self.attempt,
                {
                    "effect_class": "MODEL_INVOKE",
                    "provider_ref": "provider:test",
                    "model_ref": "model:test",
                },
                "capability-authority:test",
            ),
            expires_at=200,
        )
        self.effect = EffectAuthority(
            self.store, self.runtime, self.capability, self.resources, lambda: self.now
        )
        self.context = self._context()
        assert self.context.effect_broker is not None

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def _seed_runtime(self) -> None:
        self.store.create_run_attempt_schema()
        with self.store.transaction() as connection:
            connection.execute("INSERT INTO graph_revisions VALUES ('graph:gate5@1', '{}', 1, NULL)")
            connection.execute(
                """INSERT INTO module_instance_revisions VALUES (
                'module:gate5@1', 'graph:gate5@1', 'gate5', 'test.gate5', '1',
                'config:gate5', 'sha256:gate5', '{}', '{}', '[\"root\"]', 'accounting:gate5')"""
            )
            connection.execute(
                """INSERT INTO execution_admissions VALUES
                ('admission:gate5', 'execution:gate5/1', 'graph:gate5@1', 'policy:gate5', 1, 'ADMITTED')"""
            )
            connection.execute(
                """INSERT INTO workflow_executions VALUES
                ('execution:gate5/1', 'graph:gate5@1', 'admission:gate5', 'policy:gate5', 'ADMITTED')"""
            )
            connection.execute(
                """INSERT INTO activations VALUES
                ('activation:gate5/1', 'execution:gate5/1', 'graph:gate5@1',
                 'module:gate5@1', 'delivery:gate5-trigger', '[]',
                 'accounting:gate5', 'event:gate5-activation')"""
            )
            connection.execute(
                """INSERT INTO activation_created_events VALUES
                ('event:gate5-activation', 'activation:gate5/1', 'ActivationCreated')"""
            )
        RunRepository(self.store).create_initial(
            run_ref="run:gate5/1",
            activation_ref="activation:gate5/1",
            execution_ref="execution:gate5/1",
        )

    @staticmethod
    def _scope_valid(schema: str, value: object) -> bool:
        return (
            isinstance(value, dict)
            and (
                (
                    schema == "schema:gate5-scope@1"
                    and value.get("effect_class") == EffectAuthority.EFFECT_CLASS
                    and isinstance(value.get("resource_ref"), str)
                )
                or (
                    schema == "schema:model-invoke-scope@1"
                    and value
                    == {
                        "effect_class": "MODEL_INVOKE",
                        "provider_ref": "provider:test",
                        "model_ref": "model:test",
                    }
                )
            )
        )

    @staticmethod
    def _resource_request(resource_ref: str) -> ResourceRequest:
        return ResourceRequest(
            resource_ref,
            ResourceManager.RESOURCE_TYPE,
            "resource-manager:kernel",
            {"workspace_ref": resource_ref},
        )

    def _grant(self, grant_ref: str, resource_ref: str):
        return self.capability.issue(
            CapabilityRequest(
                grant_ref,
                "capability.managed-resource-bounded-write",
                "1",
                self.attempt,
                {"effect_class": EffectAuthority.EFFECT_CLASS, "resource_ref": resource_ref},
                "capability-authority:test",
            ),
            expires_at=200,
        )

    def _context(self, effect=None) -> RuntimeContext:
        return build_runtime_context(
            authority=self.attempt,
            activation_repository=ActivationRepository(self.store, self.registry),
            accounting_scope_ref="accounting:gate5",
            capability_grants=(
                self.grant1,
                self.grant1b,
                self.grant2,
                self.model_grant,
            ),
            resource_leases=(self.lease1, self.lease2),
            effect_authority=effect or self.effect,
            metadata=(("mode", "trusted"),),
        )

    def _dispatch(self, intent="write.1", payload="payload", grant=0, resource=0):
        assert self.context.effect_broker is not None
        return self.context.effect_broker.dispatch_bounded_write(
            self.context.capability_handles[grant],
            self.context.resource_handles[resource],
            intent,
            payload,
        )

    def _invoke(self, intent="invoke.1", input_text="hello", context=None):
        runtime_context = context or self.context
        assert runtime_context.effect_broker is not None
        return runtime_context.effect_broker.dispatch_model_invoke(
            runtime_context.capability_handles[3],
            intent,
            provider_ref="provider:test",
            model_ref="model:test",
            conflict_scope_ref="conversation:test",
            input_text=input_text,
        )

    def test_shapes_are_frozen_and_resource_handle_has_no_path(self) -> None:
        self.assertEqual(
            ["capability_type_ref", "capability_type_version", "grant_ref"],
            [field.name for field in dataclasses.fields(CapabilityHandle)],
        )
        self.assertEqual(
            ["resource_ref", "lease_ref"],
            [field.name for field in dataclasses.fields(ResourceHandle)],
        )
        self.assertNotIn("external_ref", repr(self.context.resource_handles))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            self.context.run_ref = "run:forged"  # type: ignore[misc]

    def test_host_exact_type_checks_and_forwards_runtime_context(self) -> None:
        self.registry.register(builtin_text_concat.definition())
        host = TrustedModuleHost(self.registry)
        for invalid in ({}, object()):
            with self.assertRaises(TrustedHostError) as raised:
                host.execute("builtin.text.concat@1", {"a": "x", "b": "y"}, {}, invalid)  # type: ignore[arg-type]
            self.assertEqual("INVALID_RUNTIME_CONTEXT", raised.exception.code)

        class Derived(RuntimeContext):
            pass

        with self.assertRaises(TrustedHostError):
            host.execute("builtin.text.concat@1", {"a": "x", "b": "y"}, {}, Derived(**self.context.__dict__))

        original = trusted_host._TRUSTED_IMPLEMENTATIONS[("builtin.text.concat", "1")]
        seen = []
        trusted_host._TRUSTED_IMPLEMENTATIONS[("builtin.text.concat", "1")] = (
            lambda _inputs, _config, runtime_context: seen.append(runtime_context) or {"ok": True}
        )
        try:
            result = host.execute("builtin.text.concat@1", {}, {}, self.context)
        finally:
            trusted_host._TRUSTED_IMPLEMENTATIONS[("builtin.text.concat", "1")] = original
        self.assertEqual([self.context], seen)
        self.assertEqual({"ok": True}, result.outputs)

    def test_host_rejects_recursive_field_smuggling_before_module_call(self) -> None:
        self.registry.register(builtin_text_concat.definition())
        host = TrustedModuleHost(self.registry)
        calls = []
        original = trusted_host._TRUSTED_IMPLEMENTATIONS[("builtin.text.concat", "1")]
        trusted_host._TRUSTED_IMPLEMENTATIONS[("builtin.text.concat", "1")] = (
            lambda _inputs, _config, context: calls.append(context) or {"called": True}
        )
        malformed_capability = CapabilityHandle(
            object(), "1", "grant:gate5/1"  # type: ignore[arg-type]
        )
        malformed_resource = ResourceHandle(
            object(), "lease:gate5/1"  # type: ignore[arg-type]
        )
        invalid_contexts = (
            replace(self.context, accounting_scope_ref=object()),  # type: ignore[arg-type]
            replace(self.context, metadata=(("store", self.store),)),  # type: ignore[arg-type]
            replace(self.context, metadata=(("owner", self.effect),)),  # type: ignore[arg-type]
            replace(self.context, metadata=(("object", object()),)),  # type: ignore[arg-type]
            replace(self.context, capability_handles=(malformed_capability,)),
            replace(self.context, resource_handles=(malformed_resource,)),
            replace(self.context, effect_broker=self.effect),  # type: ignore[arg-type]
            replace(self.context, effect_broker=object()),  # type: ignore[arg-type]
            replace(self.context, attempt_seq=True),
            replace(self.context, attempt_seq=object()),  # type: ignore[arg-type]
        )
        try:
            for context in invalid_contexts:
                with self.subTest(context=context), self.assertRaises(
                    TrustedHostError
                ) as raised:
                    host.execute("builtin.text.concat@1", {}, {}, context)
                self.assertEqual("INVALID_RUNTIME_CONTEXT", raised.exception.code)
        finally:
            trusted_host._TRUSTED_IMPLEMENTATIONS[("builtin.text.concat", "1")] = original
        self.assertEqual([], calls)

    def test_real_dispatch_causal_binding_and_completed_replay(self) -> None:
        first = self._dispatch()
        self.assertIsInstance(first, BoundedWriteDispatched)
        operation = self.effect.resolve(first.operation_ref)
        assert operation is not None
        self.assertEqual("delivery:gate5-trigger", operation.caused_by_ref)
        target = Path(operation.target_ref)
        before = target.stat().st_mtime_ns
        self.assertEqual(first, self._dispatch())
        self.assertEqual(before, target.stat().st_mtime_ns)

    def test_shape_and_membership_fail_before_operation_identity(self) -> None:
        broker = self.context.effect_broker
        assert broker is not None
        fabricated = CapabilityHandle("x", "1", "grant:not-issued")
        cases = (
            (fabricated, self.context.resource_handles[0], "ok", "x", "BROKER_HANDLE_NOT_IN_CONTEXT"),
            (self.context.capability_handles[0], self.context.resource_handles[0], "bad ref", "x", "BROKER_INTENT_REF_INVALID"),
            (self.context.capability_handles[0], self.context.resource_handles[0], "ok", "x" * 4097, "BROKER_PAYLOAD_INVALID"),
        )
        for cap, resource, intent, payload, code in cases:
            result = broker.dispatch_bounded_write(cap, resource, intent, payload)
            self.assertEqual(BoundedWriteRejected(None, code), result)

    def test_payload_grant_and_resource_conflicts_are_source_agnostic(self) -> None:
        self.assertIsInstance(self._dispatch("conflict.payload", "old"), BoundedWriteDispatched)
        self.assertIsInstance(self._dispatch("conflict.payload", "new"), BoundedWriteIdentityConflict)
        self.assertIsInstance(self._dispatch("conflict.grant", "same"), BoundedWriteDispatched)
        self.assertIsInstance(self._dispatch("conflict.grant", "same", grant=1), BoundedWriteIdentityConflict)
        self.assertIsInstance(self._dispatch("conflict.resource", "same"), BoundedWriteDispatched)
        self.assertIsInstance(self._dispatch("conflict.resource", "same", grant=2, resource=1), BoundedWriteIdentityConflict)

    def test_identity_conflict_has_precedence_for_all_six_states(self) -> None:
        for state in ("PREPARED", "ACTIVE", "REVOKE_REQUESTED", "FENCED", "COMPLETED", "UNKNOWN"):
            intent = "matrix." + state.lower()
            stop_stage = (
                "AFTER_PREPARED_COMMIT" if state in {"PREPARED", "FENCED"}
                else "AFTER_ACTIVE_COMMIT" if state in {"ACTIVE", "REVOKE_REQUESTED", "UNKNOWN"}
                else None
            )
            def crash(stage, _operation):
                if stage == stop_stage:
                    raise InjectedCrash
            context = self._context(
                EffectAuthority(
                    self.store, self.runtime, self.capability, self.resources,
                    lambda: self.now, crash,
                )
            )
            assert context.effect_broker is not None
            with self.assertRaises(InjectedCrash) if stop_stage else nullcontext():
                result = context.effect_broker.dispatch_bounded_write(
                    context.capability_handles[0], context.resource_handles[0], intent, "original"
                )
            operation_ref = context.effect_broker._operation_ref(intent)
            if state == "REVOKE_REQUESTED":
                self.effect.request_revoke(operation_ref)
            elif state == "FENCED":
                self.effect.request_revoke(operation_ref)
            elif state == "UNKNOWN":
                self.effect.recover(operation_ref)
            before = self.effect.resolve(operation_ref)
            assert before is not None
            self.assertEqual(state, before.state)
            conflict = context.effect_broker.dispatch_bounded_write(
                context.capability_handles[0], context.resource_handles[0], intent, "different"
            )
            self.assertEqual(
                BoundedWriteIdentityConflict(operation_ref, state), conflict
            )
            self.assertEqual(before, self.effect.resolve(operation_ref))
            target = Path(before.target_ref)
            if target.exists():
                target.unlink()
            with self.store.transaction() as connection:
                connection.execute("DELETE FROM effect_operations WHERE operation_ref = ?", (operation_ref,))

    def test_same_identity_unknown_is_distinct(self) -> None:
        def crash(stage, _operation):
            if stage == "AFTER_ACTIVE_COMMIT":
                raise InjectedCrash
        effect = EffectAuthority(
            self.store, self.runtime, self.capability, self.resources,
            lambda: self.now, crash,
        )
        context = self._context(effect)
        assert context.effect_broker is not None
        with self.assertRaises(InjectedCrash):
            context.effect_broker.dispatch_bounded_write(
                context.capability_handles[0], context.resource_handles[0], "unknown.same", "payload"
            )
        operation_ref = context.effect_broker._operation_ref("unknown.same")
        self.effect.recover(operation_ref)
        self.assertEqual(
            BoundedWriteUnknown(operation_ref),
            context.effect_broker.dispatch_bounded_write(
                context.capability_handles[0], context.resource_handles[0], "unknown.same", "payload"
            ),
        )

    def test_same_call_transition_to_unknown_is_distinct(self) -> None:
        def substitute_target(stage, operation):
            if stage == "AFTER_ACTIVE_COMMIT":
                Path(operation.target_ref).write_text("substituted", encoding="utf-8")
        effect = EffectAuthority(
            self.store, self.runtime, self.capability, self.resources,
            lambda: self.now, substitute_target,
        )
        context = self._context(effect)
        assert context.effect_broker is not None
        operation_ref = context.effect_broker._operation_ref("unknown.same-call")
        result = context.effect_broker.dispatch_bounded_write(
            context.capability_handles[0], context.resource_handles[0],
            "unknown.same-call", "payload",
        )
        self.assertEqual(BoundedWriteUnknown(operation_ref), result)
        self.assertEqual("UNKNOWN", self.effect.resolve(operation_ref).state)

    def test_missing_canonical_activation_withholds_live_broker(self) -> None:
        missing = replace(self.attempt, activation_ref="activation:missing")
        context = build_runtime_context(
            authority=missing,
            activation_repository=ActivationRepository(self.store, self.registry),
            accounting_scope_ref="accounting:gate5",
            capability_grants=(),
            resource_leases=(),
            effect_authority=self.effect,
        )
        self.assertIsNone(context.effect_broker)

    def test_stale_original_attempt_is_not_substituted(self) -> None:
        old_context = self.context
        RunRepository(self.store).replace_attempt(
            run_ref="run:gate5/1",
            expected_attempt_seq=self.attempt.attempt_seq,
            expected_fencing_generation=self.attempt.fencing_generation,
        )
        assert old_context.effect_broker is not None
        result = old_context.effect_broker.dispatch_bounded_write(
            old_context.capability_handles[0], old_context.resource_handles[0], "stale.r1", "x"
        )
        self.assertIsInstance(result, BoundedWriteRejected)
        self.assertEqual("EFFECT_DISPATCH_AUTHORITY_REJECTED", result.reason_code)

    def test_revoked_grant_and_lease_and_gate4_conflict_use_real_boundary(self) -> None:
        self.capability.revoke(self.grant1.grant_ref)
        rejected = self._dispatch("revoked.grant")
        self.assertIsInstance(rejected, BoundedWriteRejected)
        self.assertEqual("EFFECT_DISPATCH_AUTHORITY_REJECTED", rejected.reason_code)

        self.tearDown()
        self.setUp()
        self.resources.release_lease(self.lease1.lease_ref)
        rejected = self._dispatch("released.lease")
        self.assertIsInstance(rejected, BoundedWriteRejected)
        self.assertEqual("EFFECT_DISPATCH_AUTHORITY_REJECTED", rejected.reason_code)

        # A fresh fixture proves Gate-4 conflict independently of local broker checks.
        self.tearDown()
        self.setUp()
        def crash(stage, _operation):
            if stage == "AFTER_ACTIVE_COMMIT":
                raise InjectedCrash
        effect = EffectAuthority(
            self.store, self.runtime, self.capability, self.resources,
            lambda: self.now, crash,
        )
        context = self._context(effect)
        assert context.effect_broker is not None
        with self.assertRaises(InjectedCrash):
            context.effect_broker.dispatch_bounded_write(
                context.capability_handles[0], context.resource_handles[0],
                "gate4.blocker", "payload",
            )
        blocker_ref = context.effect_broker._operation_ref("gate4.blocker")
        self.effect.recover(blocker_ref)
        self.assertEqual("UNKNOWN", self.effect.resolve(blocker_ref).state)
        blocked = self._dispatch("gate4.second")
        self.assertIsInstance(blocked, BoundedWriteRejected)
        self.assertEqual("EFFECT_DISPATCH_AUTHORITY_REJECTED", blocked.reason_code)

    def test_model_invoke_prepared_before_local_dispatch_and_completion_evidence(self) -> None:
        stages = []
        effect = EffectAuthority(
            self.store,
            self.runtime,
            self.capability,
            self.resources,
            lambda: self.now,
            lambda stage, operation: stages.append((stage, operation.state)),
        )
        result = self._invoke(context=self._context(effect))
        self.assertIsInstance(result, ModelInvokeDispatched)
        operation = effect.resolve(result.operation_ref)
        assert operation is not None and operation.completion_evidence is not None
        self.assertEqual("COMPLETED", operation.state)
        self.assertEqual("KNOWN", operation.historical_outcome.value)
        self.assertEqual(
            "BOUNDED_LOCAL_SIMULATION",
            operation.completion_evidence["dispatch_boundary"],
        )
        self.assertEqual("NONE", operation.completion_evidence["external_consequence"])
        self.assertEqual("PREPARED", stages[0][1])

    def test_model_invoke_replay_conflict_and_fabricated_handle_fail_closed(self) -> None:
        first = self._invoke("invoke.replay", "same")
        self.assertEqual(first, self._invoke("invoke.replay", "same"))
        self.assertIsInstance(
            self._invoke("invoke.replay", "different"), ModelInvokeIdentityConflict
        )
        broker = self.context.effect_broker
        assert broker is not None
        fabricated = CapabilityHandle("capability.model-invoke", "1", "grant:missing")
        self.assertEqual(
            ModelInvokeRejected(None, "BROKER_HANDLE_NOT_IN_CONTEXT"),
            broker.dispatch_model_invoke(
                fabricated,
                "invoke.invalid",
                provider_ref="provider:test",
                model_ref="model:test",
                conflict_scope_ref="conversation:test",
                input_text="x",
            ),
        )

    def test_model_invoke_stale_attempt_and_ambiguous_recovery_fail_closed(self) -> None:
        old_context = self.context
        RunRepository(self.store).replace_attempt(
            run_ref="run:gate5/1",
            expected_attempt_seq=self.attempt.attempt_seq,
            expected_fencing_generation=self.attempt.fencing_generation,
        )
        rejected = self._invoke("invoke.stale", context=old_context)
        self.assertIsInstance(rejected, ModelInvokeRejected)
        self.assertEqual("EFFECT_DISPATCH_AUTHORITY_REJECTED", rejected.reason_code)

        self.tearDown()
        self.setUp()

        def crash(stage, _operation):
            if stage == "AFTER_ACTIVE_COMMIT":
                raise InjectedCrash

        effect = EffectAuthority(
            self.store,
            self.runtime,
            self.capability,
            self.resources,
            lambda: self.now,
            crash,
        )
        context = self._context(effect)
        with self.assertRaises(InjectedCrash):
            self._invoke("invoke.unknown", context=context)
        assert context.effect_broker is not None
        operation_ref = context.effect_broker._operation_ref("invoke.unknown")
        recovered = self.effect.recover(operation_ref)
        self.assertEqual("UNKNOWN", recovered.state)
        self.assertEqual("UNKNOWN", recovered.historical_outcome.value)
        self.assertIsInstance(
            self._invoke("invoke.unknown", context=context), ModelInvokeUnknown
        )

    def test_model_invoke_conflict_scope_resource_shape_and_sqlite_restart(self) -> None:
        def crash(stage, _operation):
            if stage == "AFTER_PREPARED_COMMIT":
                raise InjectedCrash

        preparing = EffectAuthority(
            self.store,
            self.runtime,
            self.capability,
            self.resources,
            lambda: self.now,
            crash,
        )
        prepared_context = self._context(preparing)
        with self.assertRaises(InjectedCrash):
            self._invoke("invoke.blocker", context=prepared_context)
        blocked = self._invoke("invoke.conflicting")
        self.assertIsInstance(blocked, ModelInvokeRejected)
        self.assertEqual("EFFECT_DISPATCH_AUTHORITY_REJECTED", blocked.reason_code)

        broker = self.context.effect_broker
        assert broker is not None
        disjoint = broker.dispatch_model_invoke(
            self.context.capability_handles[3],
            "invoke.disjoint",
            provider_ref="provider:test",
            model_ref="model:test",
            conflict_scope_ref="conversation:other",
            input_text="hello",
        )
        self.assertIsInstance(disjoint, ModelInvokeDispatched)

        with self.assertRaises(EffectError) as invalid_resource:
            self.effect.prepare(
                EffectRequest(
                    operation_ref="effect:model-invalid-resource",
                    effect_class="MODEL_INVOKE",
                    authority=self.attempt,
                    capability_grant_ref=self.model_grant.grant_ref,
                    resource_ref=self.lease1.resource_ref,
                    resource_lease_ref=self.lease1.lease_ref,
                    payload='{"conflict_scope_ref":"x","input":"x","model_ref":"model:test","provider_ref":"provider:test"}',
                    caused_by_ref="delivery:gate5-trigger",
                )
            )
        self.assertEqual("EFFECT_REQUEST_INVALID", invalid_resource.exception.code)

        completed_ref = disjoint.operation_ref
        database_path = self.root / "kernel.db"
        self.store.close()
        self.store = SQLiteStore(database_path)
        runtime = RuntimeAuthorityResolver(self.store)
        capability = CapabilityAuthority(
            self.store,
            CapabilityTypeRegistry(self.store),
            runtime,
            lambda _request: CapabilityDecision("GRANTED", "decision:gate5"),
            self._scope_valid,
            lambda: self.now,
        )
        resources = ResourceManager(
            self.store, self.root / "managed", runtime, lambda: self.now
        )
        reopened = EffectAuthority(
            self.store, runtime, capability, resources, lambda: self.now
        ).resolve(completed_ref)
        assert reopened is not None
        self.assertEqual("COMPLETED", reopened.state)
        self.assertEqual("KNOWN", reopened.historical_outcome.value)


if __name__ == "__main__":
    unittest.main()
