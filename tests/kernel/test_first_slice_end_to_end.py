"""NYRON-T-20260825-032 — one connected First Slice end-to-end test.

Proves the complete first-slice pipeline in a single executable path,
closing NYRON-T-20260825-031-F-001 (TEST / BLOCKING):

register builtin.text.concat@1
-> publish immutable graph / ModuleInstanceRevision
-> publish canonical AccountingScope
-> real AccountingScopeResolver
-> real ExecutionAdmissionGate.admit()
-> admitted WorkflowExecution
-> PacketRepository
-> DeliveryProjector
-> ActivationRepository.create_next()
-> RunRepository.create_initial()
-> AttemptExecutor.execute()
-> TrustedModuleHost.execute()
-> durable output value
-> full fenced terminal canonical commit
-> Output Packet
-> replay-safe Delivery projection

No canonical admission/runtime row is created by direct SQL here: the
execution_admissions / workflow_executions / activations / runs /
run_attempts / terminal facts are all produced by the real repository
and gate boundaries.  The only raw-SQL write is graph topology
(graph_edges), which has no repository API in the current accepted
implementation and is a Graph-Owner fact, not a Runtime fact.
"""

from __future__ import annotations

import unittest

from nyron_kernel.accounting import (
    AccountingScope,
    AccountingScopeResolver,
    compute_ancestry_hash,
)
from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.execution import (
    ActivationRepository,
    AttemptAuthority,
    AttemptExecutor,
    DeliveryProjector,
    DurableValueRepository,
    ExecutionAdmissionGate,
    PacketRepository,
    RunRepository,
)
from nyron_kernel.graph import GraphRepository, ModuleInstanceRevision
from nyron_kernel.host import TrustedModuleHost
from nyron_kernel.modules import builtin_text_concat
from nyron_kernel.store import SQLiteStore

GRAPH = "graph:first-slice@1"
MODULE = "module-instance:first-slice@1"
EXECUTION = "execution:first-slice/1"
ACTIVATION = "activation:first-slice/1"
RUN = "run:first-slice/1"
SCOPE_ROOT = "accounting:first-slice/root"
SCOPE_MODULE = "accounting:first-slice/module"
CONFIG_REF = "config:concat@1"
CONFIG_HASH = "sha256:empty-config"
POLICY_REF = "runtime-policy:pure@1"
ADMISSION_REF = "admission:first-slice/1"


class RecordingHost:
    """Observe the durable boundary, then delegate to the real trusted host."""

    def __init__(self, store: SQLiteStore, actual: TrustedModuleHost) -> None:
        self._store = store
        self._actual = actual
        self.calls: list[tuple[object, ...]] = []

    def execute(self, module_ref_version, inputs, config, runtime_context=None):
        state = self._store.connection.execute(
            "SELECT state FROM run_attempts WHERE run_ref = ? AND attempt_seq = 1",
            (RUN,),
        ).fetchone()["state"]
        self.calls.append(
            (module_ref_version, inputs, config, runtime_context, state)
        )
        return self._actual.execute(
            module_ref_version, inputs, config, runtime_context
        )


class FirstSliceEndToEndTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.registry = ModuleRegistry(self.store)
        self.graphs = GraphRepository(self.store, self.registry)
        self.accounting = AccountingScopeResolver(self.store)
        self.packets = PacketRepository(self.store)
        self.values = DurableValueRepository(self.store)
        self.projector = DeliveryProjector(self.store)
        self.activations = ActivationRepository(self.store, self.registry)
        self.runs = RunRepository(self.store)

    def tearDown(self) -> None:
        self.store.close()

    def _publish_definition_and_graph(self) -> None:
        self.registry.register(builtin_text_concat.definition())
        self.graphs.publish(
            GRAPH,
            ModuleInstanceRevision(
                module_instance_revision_ref=MODULE,
                graph_revision_ref=GRAPH,
                module_instance_ref="concat",
                module_ref="builtin.text.concat",
                module_version="1",
                config_ref=CONFIG_REF,
                config_hash=CONFIG_HASH,
                input_port_contract={"a": "REQUIRED_LATEST", "b": "TRIGGER"},
                output_port_contract={"text": {"type": "string"}},
                static_composite_path=("root",),
                static_accounting_scope_ref=SCOPE_MODULE,
            ),
        )

    def _publish_accounting_scopes(self) -> None:
        self.accounting.publish(
            AccountingScope(
                accounting_scope_ref=SCOPE_ROOT,
                graph_revision_ref=GRAPH,
                definition_anchor_ref=GRAPH,
                parent_accounting_scope_ref=None,
                scope_kind="GRAPH",
                ancestry_hash=compute_ancestry_hash((SCOPE_ROOT,)),
                created_from_definition_ref=GRAPH,
                state="ACTIVE",
            )
        )
        self.accounting.publish(
            AccountingScope(
                accounting_scope_ref=SCOPE_MODULE,
                graph_revision_ref=GRAPH,
                definition_anchor_ref=MODULE,
                parent_accounting_scope_ref=SCOPE_ROOT,
                scope_kind="MODULE",
                ancestry_hash=compute_ancestry_hash(
                    (SCOPE_ROOT, SCOPE_MODULE)
                ),
                created_from_definition_ref=MODULE,
                state="ACTIVE",
            )
        )

    def _admit(self) -> tuple[object, object]:
        gate = ExecutionAdmissionGate(
            self.store,
            self.graphs,
            self.registry,
            self.accounting,
            lambda ref, digest: (ref, digest) == (CONFIG_REF, CONFIG_HASH),
            lambda ref: ref == POLICY_REF,
        )
        return gate.admit(
            admission_ref=ADMISSION_REF,
            execution_ref=EXECUTION,
            graph_revision_ref=GRAPH,
            runtime_policy_ref=POLICY_REF,
        )

    def _seed_graph_edges(self) -> None:
        edges = (
            # input:a -> module port a (REQUIRED_LATEST)
            ("edge:input-a", "input:a", "out", "a", 0, 0),
            # input:b -> module port b (TRIGGER)
            ("edge:input-b", "input:b", "out", "b", 1, 1),
            # module output text -> module port a (for output projection replay)
            ("edge:output", MODULE, "text", "a", 2, 0),
        )
        for edge_ref, source_ref, source_port, target_port, ordinal, target_ordinal in edges:
            self.store.connection.execute(
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

    def _commit_input_packet(self, name: str, value: str) -> object:
        value_ref = f"value:input:{name}"
        packet_ref = f"packet:input:{name}"
        self.values.put(value_ref, value)
        packet = self.packets.commit(
            packet_ref=packet_ref,
            execution_ref=EXECUTION,
            graph_revision_ref=GRAPH,
            source_kind="EXTERNAL_INPUT",
            source_ref=f"input:{name}",
            source_port_ref="out",
            value_ref=value_ref,
            schema_ref="schema:string",
            caused_by_ref=f"cause:input:{name}",
            created_event_ref=f"event:input:{name}",
        )
        delivery = self.projector.project(
            packet.packet_ref, (f"edge:input-{name}",)
        )
        return packet, delivery

    def test_first_slice_full_chain_end_to_end(self) -> None:
        # 1/2. exact pinned module version + exact immutable graph revision
        self._publish_definition_and_graph()
        self.assertEqual(
            "builtin.text.concat@1", builtin_text_concat.MODULE_REF_VERSION
        )
        self.assertIsNotNone(
            self.registry.resolve("builtin.text.concat", "1")
        )

        # 3. canonical AccountingScope published and resolvable before admission
        self._publish_accounting_scopes()
        resolved_scope = self.accounting.resolve(
            SCOPE_MODULE, GRAPH, MODULE
        )
        self.assertEqual(SCOPE_MODULE, resolved_scope.accounting_scope_ref)

        # 4/5. real ExecutionAdmissionGate creates the admitted WorkflowExecution
        admission, execution = self._admit()
        self.assertEqual(ADMISSION_REF, admission.admission_ref)
        self.assertEqual("ADMITTED", admission.state)
        self.assertEqual(EXECUTION, execution.execution_ref)
        self.assertEqual(GRAPH, execution.graph_revision_ref)
        self.assertEqual("ADMITTED", execution.state)
        # WorkflowExecution exists before any Packet / Activation work:
        self.assertEqual(
            "ADMITTED",
            self.store.connection.execute(
                "SELECT state FROM workflow_executions WHERE execution_ref = ?",
                (EXECUTION,),
            ).fetchone()["state"],
        )

        # 6. input Packets and projected Deliveries are canonical facts
        self._seed_graph_edges()
        (packet_a, deliveries_a) = self._commit_input_packet("a", "hello ")
        (packet_b, deliveries_b) = self._commit_input_packet("b", "world")
        self.assertEqual(EXECUTION, packet_a.execution_ref)
        self.assertEqual(GRAPH, packet_a.graph_revision_ref)
        self.assertEqual(1, len(deliveries_a))
        self.assertEqual("a", deliveries_a[0].target_port_ref)
        self.assertEqual(1, len(deliveries_b))
        self.assertEqual("b", deliveries_b[0].target_port_ref)

        # 7. Activation created by the real readiness/binding path
        activation = self.activations.create_next(
            activation_ref=ACTIVATION,
            execution_ref=EXECUTION,
            module_instance_revision_ref=MODULE,
            created_event_ref="event:activation:first-slice/1",
        )
        self.assertEqual(EXECUTION, activation.execution_ref)
        self.assertEqual(GRAPH, activation.graph_revision_ref)
        self.assertEqual(MODULE, activation.module_instance_revision_ref)
        self.assertEqual(SCOPE_MODULE, activation.static_accounting_scope_ref)
        bindings = {
            binding.port_ref: (binding.activation_mode, binding.delivery_ref)
            for binding in activation.input_bindings
        }
        self.assertEqual(
            ("REQUIRED_LATEST", deliveries_a[0].delivery_ref),
            bindings["a"],
        )
        self.assertEqual(
            ("TRIGGER", deliveries_b[0].delivery_ref),
            bindings["b"],
        )

        # 8/9. exactly one Run; initial Attempt is (1, CREATED)
        run, attempt = self.runs.create_initial(
            run_ref=RUN,
            activation_ref=ACTIVATION,
            execution_ref=EXECUTION,
        )
        self.assertEqual(
            1,
            self.store.connection.execute(
                "SELECT COUNT(*) FROM runs WHERE activation_ref = ?",
                (ACTIVATION,),
            ).fetchone()[0],
        )
        self.assertEqual(1, run.current_attempt_seq)
        self.assertEqual(1, run.fencing_generation)
        self.assertEqual("OPEN", run.state)
        self.assertEqual(1, attempt.attempt_seq)
        self.assertEqual("CREATED", attempt.state)

        # 10-13. execute crosses CREATED -> ACTIVE before host invocation;
        # exact builtin runs through the real host; value correct and durable.
        host = RecordingHost(self.store, TrustedModuleHost(self.registry))
        executor = AttemptExecutor(
            self.store,
            self.registry,
            lambda ref, digest: {} if (ref, digest) == (CONFIG_REF, CONFIG_HASH)
            else (_ for _ in ()).throw(LookupError("not exact")),
            host=host,
        )
        output_packets = executor.execute(RUN)
        self.assertEqual(
            (
                "builtin.text.concat@1",
                {"a": "hello ", "b": "world"},
                {},
                None,
                "ACTIVE",
            ),
            host.calls[0],
        )
        self.assertEqual(1, len(output_packets))
        output = output_packets[0]
        self.assertEqual("hello world", self.values.resolve(output.value_ref))

        # 14-16. fenced terminal canonical commit: attempt SUCCEEDED,
        # run SUCCESS pins terminal attempt/event.
        row = self.store.connection.execute(
            """
            SELECT r.state AS run_state, r.terminal_attempt_seq,
                   r.terminal_event_ref, r.fencing_generation,
                   a.state AS attempt_state, a.attempt_seq, a.fencing_token
            FROM runs r JOIN run_attempts a ON a.run_ref = r.run_ref
            WHERE r.run_ref = ? AND a.attempt_seq = 1
            """,
            (RUN,),
        ).fetchone()
        self.assertEqual("SUCCEEDED", row["attempt_state"])
        self.assertEqual("SUCCESS", row["run_state"])
        self.assertEqual(1, row["terminal_attempt_seq"])
        self.assertIsNotNone(row["terminal_event_ref"])
        authority = AttemptAuthority(
            EXECUTION,
            ACTIVATION,
            RUN,
            row["attempt_seq"],
            row["fencing_token"],
            row["fencing_generation"],
        )
        self.assertEqual(
            AttemptExecutor.terminal_event_ref(authority),
            row["terminal_event_ref"],
        )

        # 17. Output Packet immutable, exact execution/graph, source-bound.
        self.assertEqual("MODULE_OUTPUT", output.source_kind)
        self.assertEqual(MODULE, output.source_ref)
        self.assertEqual("text", output.source_port_ref)
        self.assertEqual(EXECUTION, output.execution_ref)
        self.assertEqual(GRAPH, output.graph_revision_ref)
        resolved_output = self.packets.resolve(output.packet_ref)
        self.assertEqual(output, resolved_output)

        # 18. replay-safe Delivery projection for the Output Packet.
        first = self.projector.project(output.packet_ref)
        second = self.projector.project(output.packet_ref)
        self.assertEqual(first, second)
        self.assertEqual(1, len(first))
        self.assertEqual("a", first[0].target_port_ref)
        self.assertEqual(
            MODULE, first[0].target_module_instance_revision_ref
        )


if __name__ == "__main__":
    unittest.main()
