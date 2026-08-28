"""Executable acceptance coverage for NYRON-T-20260825-029."""

from __future__ import annotations

import json
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
from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.effect import EffectAuthority
from nyron_kernel.execution import (
    ActivationRepository,
    AttemptExecutionError,
    AttemptExecutor,
    DeliveryProjector,
    DurableValueRepository,
    PacketRepository,
    RunRepository,
    RuntimeAuthorityResolver,
)
from nyron_kernel.graph import GraphRepository, ModuleInstanceRevision
from nyron_kernel.host import Completed, Failed, TrustedModuleHost
from nyron_kernel.modules import builtin_text_concat
from nyron_kernel.resource import ResourceManager
from nyron_kernel.store import SQLiteStore


GRAPH = "graph:attempt-execution@1"
MODULE = "module-instance:attempt-execution@1"
EXECUTION = "execution:attempt-execution/1"
ACTIVATION = "activation:attempt-execution/1"
RUN = "run:attempt-execution/1"


class RecordingHost:
    def __init__(self, store: SQLiteStore, actual: TrustedModuleHost) -> None:
        self.store = store
        self.actual = actual
        self.calls: list[tuple[object, ...]] = []

    def execute(self, module_ref_version, inputs, config, runtime_context=None):
        state = self.store.connection.execute(
            "SELECT state FROM run_attempts WHERE run_ref = ? AND attempt_seq = 1",
            (RUN,),
        ).fetchone()["state"]
        self.calls.append((module_ref_version, inputs, config, runtime_context, state))
        return self.actual.execute(
            module_ref_version, inputs, config, runtime_context
        )


class RaisingHost:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, *_args, **_kwargs):
        self.calls += 1
        raise RuntimeError("injected host crash")


class ResultHost:
    def __init__(self, result: object) -> None:
        self.result = result
        self.calls = 0

    def execute(self, *_args, **_kwargs):
        self.calls += 1
        return self.result


class AttemptExecutionCommitTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self._prepare(self.store)

    def tearDown(self) -> None:
        self.store.close()

    @staticmethod
    def _prepare(store: SQLiteStore) -> None:
        registry = ModuleRegistry(store)
        registry.register(builtin_text_concat.definition())
        GraphRepository(store, registry).publish(
            GRAPH,
            ModuleInstanceRevision(
                module_instance_revision_ref=MODULE,
                graph_revision_ref=GRAPH,
                module_instance_ref="concat",
                module_ref="builtin.text.concat",
                module_version="1",
                config_ref="config:concat@1",
                config_hash="sha256:empty-config",
                input_port_contract={"a": "REQUIRED_LATEST", "b": "TRIGGER"},
                output_port_contract={"text": {"type": "string"}},
                static_composite_path=("root",),
                static_accounting_scope_ref="accounting:concat",
            ),
        )
        with store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO execution_admissions(
                    admission_ref, execution_ref, graph_revision_ref,
                    runtime_policy_ref, admitted_at_owner_order, state
                ) VALUES ('admission:attempt-execution/1', ?, ?,
                          'policy:attempt-execution@1', 1, 'ADMITTED')
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO workflow_executions(
                    execution_ref, graph_revision_ref, admission_ref,
                    runtime_policy_ref, state
                ) VALUES (?, ?, 'admission:attempt-execution/1',
                          'policy:attempt-execution@1', 'ADMITTED')
                """,
                (EXECUTION, GRAPH),
            )
            edges = (
                ("edge:input-a", "input:a", "out", "a", 0, 0),
                ("edge:input-b", "input:b", "out", "b", 1, 1),
                ("edge:output", MODULE, "text", "a", 2, 0),
            )
            for edge_ref, source_ref, source_port, target_port, ordinal, target_ordinal in edges:
                connection.execute(
                    """
                    INSERT INTO graph_edges(
                        graph_revision_ref, edge_ref, source_ref,
                        source_port_ref, target_module_instance_revision_ref,
                        target_port_ref, edge_ordinal, target_port_ordinal
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        GRAPH, edge_ref, source_ref, source_port, MODULE,
                        target_port, ordinal, target_ordinal,
                    ),
                )

        values = DurableValueRepository(store)
        packets = PacketRepository(store)
        projector = DeliveryProjector(store)
        for index, (name, value) in enumerate((("a", "old-"), ("a", "hello "), ("b", "world")), start=1):
            value_ref = f"value:input:{index}"
            packet_ref = f"packet:input:{index}"
            values.put(value_ref, value)
            packets.commit(
                packet_ref=packet_ref,
                execution_ref=EXECUTION,
                graph_revision_ref=GRAPH,
                source_kind="EXTERNAL_INPUT",
                source_ref=f"input:{name}",
                source_port_ref="out",
                value_ref=value_ref,
                schema_ref="schema:string",
                caused_by_ref="test:input",
                created_event_ref=f"event:input:{index}",
            )
            projector.project(packet_ref, (f"edge:input-{name}",))

        ActivationRepository(store, registry).create_next(
            activation_ref=ACTIVATION,
            execution_ref=EXECUTION,
            module_instance_revision_ref=MODULE,
            created_event_ref="event:activation:attempt-execution/1",
        )
        RunRepository(store).create_initial(
            run_ref=RUN, activation_ref=ACTIVATION, execution_ref=EXECUTION
        )

    def _executor(self, host=None, calls=None) -> AttemptExecutor:
        registry = ModuleRegistry(self.store)

        def loader(config_ref: str, config_hash: str):
            if calls is not None:
                calls.append((config_ref, config_hash))
            if (config_ref, config_hash) != (
                "config:concat@1", "sha256:empty-config"
            ):
                raise LookupError("not exact")
            return {}

        return AttemptExecutor(self.store, registry, loader, host=host)

    def _authority(self):
        run, attempt = RunRepository(self.store).resolve(RUN)
        from nyron_kernel.execution import AttemptAuthority
        return AttemptAuthority(
            run.execution_ref, run.activation_ref, run.run_ref,
            attempt.attempt_seq, attempt.fencing_token, run.fencing_generation,
        )

    def _state(self):
        return self.store.connection.execute(
            """
            SELECT r.state run_state, r.terminal_attempt_seq,
                   r.terminal_event_ref, a.state attempt_state
            FROM runs r JOIN run_attempts a ON a.run_ref = r.run_ref
            WHERE r.run_ref = ? AND a.attempt_seq = 1
            """,
            (RUN,),
        ).fetchone()

    def _count(self, table: str) -> int:
        return self.store.connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

    def _make_model_effect_capable(self) -> None:
        row = self.store.connection.execute(
            "SELECT contract_json FROM module_definitions WHERE module_ref = 'builtin.text.concat' AND version = '1'"
        ).fetchone()
        contract = json.loads(row["contract_json"])
        contract["effect_classes"] = ["MODEL_CALL"]
        contract["required_capability_types"] = ["MODEL_INVOKE"]
        with self.store.transaction() as connection:
            connection.execute(
                "UPDATE module_definitions SET contract_json = ? WHERE module_ref = 'builtin.text.concat' AND version = '1'",
                (json.dumps(contract, sort_keys=True, separators=(",", ":")),),
            )

    def _model_authorities(self, managed_root: Path):
        runtime = RuntimeAuthorityResolver(self.store)
        types = CapabilityTypeRegistry(self.store)
        types.register(
            CapabilityTypeDefinition(
                "capability.model-invoke",
                "1",
                "schema:model-invoke@1",
                None,
                ("MODEL_INVOKE",),
                {},
            )
        )
        capability = CapabilityAuthority(
            self.store,
            types,
            runtime,
            lambda _request: CapabilityDecision("GRANTED", "decision:model"),
            lambda schema, scope: schema == "schema:model-invoke@1"
            and scope
            == {
                "effect_class": "MODEL_INVOKE",
                "provider_ref": "provider:test",
                "model_ref": "model:test",
            },
            lambda: 100,
        )
        resources = ResourceManager(self.store, managed_root, runtime, lambda: 100)
        effect = EffectAuthority(
            self.store, runtime, capability, resources, lambda: 100
        )
        authority = runtime.resolve_current(RUN)
        assert authority is not None
        capability.issue(
            CapabilityRequest(
                "grant:attempt/model",
                "capability.model-invoke",
                "1",
                authority,
                {
                    "effect_class": "MODEL_INVOKE",
                    "provider_ref": "provider:test",
                    "model_ref": "model:test",
                },
                "capability-authority:test",
            ),
            expires_at=200,
        )
        return capability, effect

    def test_happy_path_uses_exact_activation_inputs_config_and_host_boundary(self):
        config_calls = []
        host = RecordingHost(
            self.store, TrustedModuleHost(ModuleRegistry(self.store))
        )
        packets = self._executor(host, config_calls).execute(RUN)

        self.assertEqual(
            [("config:concat@1", "sha256:empty-config")], config_calls
        )
        self.assertEqual(
            ("builtin.text.concat@1", {"a": "hello ", "b": "world"}, {}, None, "ACTIVE"),
            host.calls[0],
        )
        self.assertEqual(1, len(packets))
        self.assertEqual("MODULE_OUTPUT", packets[0].source_kind)
        self.assertEqual(MODULE, packets[0].source_ref)
        self.assertEqual("text", packets[0].source_port_ref)
        self.assertEqual("hello world", DurableValueRepository(self.store).resolve(packets[0].value_ref))
        state = self._state()
        self.assertEqual(("SUCCESS", 1, "SUCCEEDED"), (state["run_state"], state["terminal_attempt_seq"], state["attempt_state"]))
        self.assertEqual(1, self._count("run_terminal_events"))

    def test_effect_capable_attempt_receives_only_bounded_runtime_context(self):
        self._make_model_effect_capable()
        with tempfile.TemporaryDirectory() as directory:
            capability, effect = self._model_authorities(Path(directory) / "managed")
            registry = ModuleRegistry(self.store)
            class EffectHost:
                def __init__(self):
                    self.calls = []

                def execute(self, module_ref_version, inputs, config, runtime_context=None):
                    self.calls.append((module_ref_version, inputs, config, runtime_context))
                    return Completed({"text": inputs["a"] + inputs["b"]})

            host = EffectHost()
            executor = AttemptExecutor(
                self.store,
                registry,
                lambda _ref, _digest: {},
                host=host,
                capability_authority=capability,
                effect_authority=effect,
            )
            executor.execute(RUN)
        context = host.calls[0][3]
        self.assertIsNotNone(context)
        self.assertIsNotNone(context.effect_broker)
        self.assertEqual(
            ("grant:attempt/model",),
            tuple(handle.grant_ref for handle in context.capability_handles),
        )
        self.assertEqual((), context.resource_handles)

    def test_effect_capable_attempt_without_canonical_grant_fails_before_host(self):
        self._make_model_effect_capable()
        host = ResultHost(Completed({"text": "should-not-run"}))
        executor = AttemptExecutor(
            self.store,
            ModuleRegistry(self.store),
            lambda _ref, _digest: {},
            host=host,
        )
        with self.assertRaises(AttemptExecutionError) as raised:
            executor.execute(RUN)
        self.assertEqual("MODULE_INVOCATION_INTERRUPTED", raised.exception.code)
        self.assertEqual(0, host.calls)

    def test_post_activation_new_delivery_cannot_replace_recorded_input(self):
        values = DurableValueRepository(self.store)
        values.put("value:input:newest", "wrong-latest-")
        packet = PacketRepository(self.store).commit(
            packet_ref="packet:input:newest",
            execution_ref=EXECUTION,
            graph_revision_ref=GRAPH,
            source_kind="EXTERNAL_INPUT",
            source_ref="input:a",
            source_port_ref="out",
            value_ref="value:input:newest",
            schema_ref="schema:string",
            caused_by_ref="test:after-activation",
            created_event_ref="event:input:newest",
        )
        DeliveryProjector(self.store).project(packet.packet_ref, ("edge:input-a",))
        host = RecordingHost(
            self.store, TrustedModuleHost(ModuleRegistry(self.store))
        )

        self._executor(host).execute(RUN)

        self.assertEqual(
            {"a": "hello ", "b": "world"}, host.calls[0][1]
        )

    def test_exact_config_failure_and_missing_value_stop_before_active(self):
        executor = AttemptExecutor(
            self.store,
            ModuleRegistry(self.store),
            lambda _ref, _digest: {"mutable": True},
        )
        with self.assertRaises(AttemptExecutionError) as bad_config:
            executor.execute(RUN)
        self.assertEqual("CONFIG_SCHEMA_MISMATCH", bad_config.exception.code)
        self.assertEqual("CREATED", self._state()["attempt_state"])

        self.store.connection.execute(
            "DELETE FROM durable_values WHERE value_ref = 'value:input:2'"
        )
        with self.assertRaises(AttemptExecutionError) as missing:
            self._executor().execute(RUN)
        self.assertEqual("UNRESOLVED_DURABLE_VALUE", missing.exception.code)
        self.assertEqual("CREATED", self._state()["attempt_state"])

    def test_durable_value_identity_is_immutable_and_identical_reput_is_idempotent(self):
        values = DurableValueRepository(self.store)
        self.assertEqual("value:test", values.put("value:test", {"x": 1}))
        self.assertEqual("value:test", values.put("value:test", {"x": 1}))
        from nyron_kernel.execution import DurableValueError
        with self.assertRaises(DurableValueError) as conflict:
            values.put("value:test", {"x": 2})
        self.assertEqual("DURABLE_VALUE_IDENTITY_CONFLICT", conflict.exception.code)

    def test_active_boundary_is_durable_and_ambiguous_attempt_never_reexecutes(self):
        host = RaisingHost()
        executor = self._executor(host)
        with self.assertRaises(AttemptExecutionError) as first:
            executor.execute(RUN)
        self.assertEqual("MODULE_INVOCATION_INTERRUPTED", first.exception.code)
        self.assertEqual("ACTIVE", self._state()["attempt_state"])

        with self.assertRaises(AttemptExecutionError) as second:
            executor.execute(RUN)
        self.assertEqual("ATTEMPT_DISPATCH_AMBIGUOUS", second.exception.code)
        self.assertEqual(1, host.calls)
        self.assertEqual(0, self._count("packets") - 3)

    def test_output_schema_mismatch_fails_attempt_without_success_truth(self):
        executor = self._executor(ResultHost(Completed({"text": 42})))
        with self.assertRaises(AttemptExecutionError) as raised:
            executor.execute(RUN)
        self.assertEqual("MODULE_OUTPUT_SCHEMA_MISMATCH", raised.exception.code)
        state = self._state()
        self.assertEqual(("OPEN", "FAILED"), (state["run_state"], state["attempt_state"]))
        self.assertEqual(0, self._count("run_terminal_events"))
        self.assertEqual(3, self._count("packets"))

    def test_orphan_output_then_recovery_commit_without_reexecution(self):
        authority = self._authority()
        host = RecordingHost(self.store, TrustedModuleHost(ModuleRegistry(self.store)))
        executor = self._executor(host)
        with self.assertRaises(AttemptExecutionError):
            executor.execute(RUN, inject_failure="before_canonical_transaction")

        value_ref = executor.output_value_ref(authority, "text")
        self.assertEqual("hello world", DurableValueRepository(self.store).resolve(value_ref))
        self.assertEqual(("OPEN", "ACTIVE"), (self._state()["run_state"], self._state()["attempt_state"]))
        self.assertEqual(3, self._count("packets"))
        committed = executor.commit_prepared_success(authority)
        replayed = executor.commit_prepared_success(authority)
        self.assertEqual(committed, replayed)
        self.assertEqual(1, len(host.calls))
        self.assertEqual(4, self._count("packets"))
        self.assertEqual(1, self._count("run_terminal_events"))

    def test_inside_transaction_failure_rolls_back_then_clean_commit_once(self):
        authority = self._authority()
        executor = self._executor()
        with self.assertRaises(AttemptExecutionError):
            executor.execute(RUN, inject_failure="inside_after_terminal_writes")
        state = self._state()
        self.assertEqual(("OPEN", "ACTIVE", None, None), (state["run_state"], state["attempt_state"], state["terminal_attempt_seq"], state["terminal_event_ref"]))
        self.assertEqual(3, self._count("packets"))
        self.assertEqual(0, self._count("run_terminal_events"))

        executor.commit_prepared_success(authority)
        executor.commit_prepared_success(authority)
        self.assertEqual(4, self._count("packets"))
        self.assertEqual(1, self._count("run_terminal_events"))

    def test_every_fencing_component_mismatch_rejects_without_packet(self):
        authority = self._authority()
        executor = self._executor()
        with self.assertRaises(AttemptExecutionError):
            executor.execute(RUN, inject_failure="before_canonical_transaction")
        variants = (
            replace(authority, execution_ref="execution:stale"),
            replace(authority, activation_ref="activation:stale"),
            replace(authority, run_ref="run:stale"),
            replace(authority, attempt_seq=2),
            replace(authority, fencing_token="fencing:stale"),
            replace(authority, fencing_generation=2),
        )
        for stale in variants:
            with self.subTest(stale=stale):
                with self.assertRaises(AttemptExecutionError) as raised:
                    executor.commit_prepared_success(stale)
                self.assertEqual("STALE_ATTEMPT_REJECTED", raised.exception.code)
        self.assertEqual(3, self._count("packets"))
        self.assertEqual("OPEN", self._state()["run_state"])

    def test_replaced_r1_cannot_commit_prepared_terminal_outputs(self):
        authority = self._authority()
        executor = self._executor()
        with self.assertRaises(AttemptExecutionError):
            executor.execute(RUN, inject_failure="before_canonical_transaction")
        RunRepository(self.store).replace_attempt(
            run_ref=RUN,
            expected_attempt_seq=authority.attempt_seq,
            expected_fencing_generation=authority.fencing_generation,
        )
        with self.assertRaises(AttemptExecutionError) as raised:
            executor.commit_prepared_success(authority)
        self.assertEqual("STALE_ATTEMPT_REJECTED", raised.exception.code)
        self.assertEqual(3, self._count("packets"))
        self.assertEqual(0, self._count("run_terminal_events"))

    def test_failed_result_creates_no_output_or_new_attempt(self):
        result = self._executor(ResultHost(Failed("bad"))).execute(RUN)
        self.assertIsInstance(result, Failed)
        self.assertEqual(("OPEN", "FAILED"), (self._state()["run_state"], self._state()["attempt_state"]))
        self.assertEqual(1, self._count("run_attempts"))
        self.assertEqual(3, self._count("packets"))

    def test_reopen_preserves_terminal_truth_and_projection_replays(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nyron.db"
            with SQLiteStore(path) as store:
                self._prepare(store)
                registry = ModuleRegistry(store)
                executor = AttemptExecutor(store, registry, lambda ref, digest: {})
                packet = executor.execute(RUN)[0]
                expected = DurableValueRepository(store).resolve(packet.value_ref)

            with SQLiteStore(path) as reopened:
                packet_after = PacketRepository(reopened).resolve(packet.packet_ref)
                self.assertEqual(packet, packet_after)
                self.assertEqual(expected, DurableValueRepository(reopened).resolve(packet.value_ref))
                state = reopened.connection.execute(
                    "SELECT state, terminal_attempt_seq FROM runs WHERE run_ref = ?",
                    (RUN,),
                ).fetchone()
                self.assertEqual(("SUCCESS", 1), tuple(state))
                projector = DeliveryProjector(reopened)
                first = projector.project(packet.packet_ref)
                second = projector.project(packet.packet_ref)
                self.assertEqual(first, second)
                self.assertEqual(1, len(first))


if __name__ == "__main__":
    unittest.main()
