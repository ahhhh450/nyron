"""NYRON-T-20260828-171 -- deterministic compile, restart, and the required
first end-to-end Product proof:

    Text Input -> Mock LLM -> Text Output

through the existing, unmodified Runtime:

    Module -> ProductNodeDefinition -> NodeInstance/Ports/NodeConnection
    -> VisualWorkflowRevision -> deterministic Product compiler
    -> GraphRevision -> Runtime execution -> deterministic text Result

No real Network/Provider/Credential/Browser/external effect is exercised:
every Module involved declares ``effect_classes=("PURE",)`` and no
``required_capability_types``.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nyron_kernel.accounting import (
    AccountingScope,
    AccountingScopeResolver,
    compute_ancestry_hash,
)
from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.execution import (
    ActivationRepository,
    DeliveryProjector,
    DurableValueRepository,
    ExecutionAdmissionGate,
    PacketRepository,
    RunRepository,
)
from nyron_kernel.execution.executor import AttemptExecutor
from nyron_kernel.graph import GraphRepository
from nyron_kernel.host import TrustedModuleHost
from nyron_kernel.modules import builtin_mock_llm_echo, builtin_text_constant, builtin_text_identity
from nyron_kernel.product import (
    EntrypointBinding,
    NodeConnection,
    NodeInstance,
    OutputBinding,
    ProductGraphCompiler,
    ProductNodeDefinition,
    ProductNodeRegistry,
    ProductPortBinding,
    ProductWorkflowRepository,
    VisualWorkflowRevision,
)
from nyron_kernel.store import SQLiteStore

WORKFLOW_REVISION_REF = "workflow-revision:first-slice@1"
POLICY_REF = "runtime-policy:pure@1"
INPUT_TEXT = "hello product node foundation"
EXPECTED_RESULT = f"[MOCK_LLM_RESPONSE] {INPUT_TEXT}"


def register_node_definitions(nodes: ProductNodeRegistry) -> None:
    nodes.register(
        ProductNodeDefinition(
            product_node_type_ref="product.text_input",
            product_node_version="1",
            bound_module_ref=builtin_text_constant.MODULE_REF,
            bound_module_version=builtin_text_constant.MODULE_VERSION,
            input_port_bindings=(ProductPortBinding("start", "start"),),
            output_port_bindings=(ProductPortBinding("text", "text"),),
            product_config_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            },
            display_metadata={"label": "Text Input"},
        )
    )
    nodes.register(
        ProductNodeDefinition(
            product_node_type_ref="product.mock_llm",
            product_node_version="1",
            bound_module_ref=builtin_mock_llm_echo.MODULE_REF,
            bound_module_version=builtin_mock_llm_echo.MODULE_VERSION,
            input_port_bindings=(ProductPortBinding("prompt", "prompt"),),
            output_port_bindings=(ProductPortBinding("text", "text"),),
            product_config_schema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            display_metadata={"label": "Mock LLM"},
        )
    )
    nodes.register(
        ProductNodeDefinition(
            product_node_type_ref="product.text_output",
            product_node_version="1",
            bound_module_ref=builtin_text_identity.MODULE_REF,
            bound_module_version=builtin_text_identity.MODULE_VERSION,
            input_port_bindings=(ProductPortBinding("text", "text"),),
            output_port_bindings=(ProductPortBinding("text", "text"),),
            product_config_schema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            display_metadata={"label": "Text Output"},
        )
    )


def build_workflow() -> VisualWorkflowRevision:
    return VisualWorkflowRevision(
        workflow_revision_ref=WORKFLOW_REVISION_REF,
        workflow_ref="workflow:first-slice",
        predecessor_workflow_revision_ref=None,
        node_instances=(
            NodeInstance("input-node", "product.text_input", "1", config={"text": INPUT_TEXT}),
            NodeInstance("llm-node", "product.mock_llm", "1", config={}),
            NodeInstance("output-node", "product.text_output", "1", config={}),
        ),
        node_connections=(
            NodeConnection("conn-input-llm", "input-node", "text", "llm-node", "prompt"),
            NodeConnection("conn-llm-output", "llm-node", "text", "output-node", "text"),
        ),
        entrypoints=(EntrypointBinding("input-node", "start"),),
        product_outputs=(OutputBinding("result", "output-node", "text"),),
        product_metadata={"name": "Text Input -> Mock LLM -> Text Output"},
    )


class ProductCompilerDeterminismTest(unittest.TestCase):
    def _build_compiler(self, store: SQLiteStore) -> ProductGraphCompiler:
        modules = ModuleRegistry(store)
        modules.register(builtin_text_constant.definition())
        modules.register(builtin_mock_llm_echo.definition())
        modules.register(builtin_text_identity.definition())
        nodes = ProductNodeRegistry(store, modules)
        register_node_definitions(nodes)
        workflows = ProductWorkflowRepository(store, nodes, modules)
        workflows.publish(build_workflow())
        graphs = GraphRepository(store, modules)
        return ProductGraphCompiler(graphs, nodes, modules)

    def test_recompiling_the_same_workflow_revision_is_deterministic(self) -> None:
        store = SQLiteStore()
        compiler = self._build_compiler(store)
        first = compiler.compile(build_workflow())
        second = compiler.compile(build_workflow())
        self.assertEqual(
            first.graph_revision.graph_revision_ref,
            second.graph_revision.graph_revision_ref,
        )
        self.assertEqual(first.graph_revision, second.graph_revision)
        self.assertEqual(3, len(first.graph_revision.module_instance_revisions))
        self.assertEqual(3, len(first.graph_revision.edges))
        store.close()

    def test_recompile_after_restart_reproduces_the_identical_graph_revision(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "nyron.db"
            with SQLiteStore(database) as store:
                compiler = self._build_compiler(store)
                before = compiler.compile(build_workflow())

            with SQLiteStore(database) as reopened_store:
                reopened_modules = ModuleRegistry(reopened_store)
                reopened_nodes = ProductNodeRegistry(reopened_store, reopened_modules)
                reopened_graphs = GraphRepository(reopened_store, reopened_modules)
                reopened_compiler = ProductGraphCompiler(
                    reopened_graphs, reopened_nodes, reopened_modules
                )
                reopened_workflows = ProductWorkflowRepository(
                    reopened_store, reopened_nodes, reopened_modules
                )
                restored_workflow = reopened_workflows.resolve(WORKFLOW_REVISION_REF)
                after = reopened_compiler.compile(restored_workflow)

        self.assertEqual(
            before.graph_revision.graph_revision_ref,
            after.graph_revision.graph_revision_ref,
        )
        self.assertEqual(before.graph_revision, after.graph_revision)


class ProductFirstSliceEndToEndTest(unittest.TestCase):
    """Real, persisted execution of Text Input -> Mock LLM -> Text Output."""

    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.modules = ModuleRegistry(self.store)
        self.modules.register(builtin_text_constant.definition())
        self.modules.register(builtin_mock_llm_echo.definition())
        self.modules.register(builtin_text_identity.definition())
        self.nodes = ProductNodeRegistry(self.store, self.modules)
        register_node_definitions(self.nodes)
        self.workflows = ProductWorkflowRepository(self.store, self.nodes, self.modules)
        self.graphs = GraphRepository(self.store, self.modules)
        self.compiler = ProductGraphCompiler(self.graphs, self.nodes, self.modules)
        self.accounting = AccountingScopeResolver(self.store)
        self.packets = PacketRepository(self.store)
        self.values = DurableValueRepository(self.store)
        self.projector = DeliveryProjector(self.store)
        self.activations = ActivationRepository(self.store, self.modules)
        self.runs = RunRepository(self.store)
        self.host = TrustedModuleHost(self.modules)
        self.executor = self._build_executor()

    def tearDown(self) -> None:
        self.store.close()

    def _build_executor(self) -> AttemptExecutor:
        return AttemptExecutor(
            self.store,
            self.modules,
            lambda ref, digest: (
                self.compiled.config_by_ref[ref]
                if ref in self.compiled.config_by_ref and ref == digest
                else (_ for _ in ()).throw(LookupError("not exact"))
            ),
            host=self.host,
        )

    def _publish_accounting_scopes(self) -> None:
        root = "accounting:product/first-slice/root"
        self.accounting.publish(
            AccountingScope(
                accounting_scope_ref=root,
                graph_revision_ref=self.compiled.graph_revision.graph_revision_ref,
                definition_anchor_ref=self.compiled.graph_revision.graph_revision_ref,
                parent_accounting_scope_ref=None,
                scope_kind="GRAPH",
                ancestry_hash=compute_ancestry_hash((root,)),
                created_from_definition_ref=self.compiled.graph_revision.graph_revision_ref,
                state="ACTIVE",
            )
        )
        for instance in self.compiled.graph_revision.module_instance_revisions:
            scope_ref = instance.static_accounting_scope_ref
            self.accounting.publish(
                AccountingScope(
                    accounting_scope_ref=scope_ref,
                    graph_revision_ref=self.compiled.graph_revision.graph_revision_ref,
                    definition_anchor_ref=instance.module_instance_revision_ref,
                    parent_accounting_scope_ref=root,
                    scope_kind="MODULE",
                    ancestry_hash=compute_ancestry_hash((root, scope_ref)),
                    created_from_definition_ref=instance.module_instance_revision_ref,
                    state="ACTIVE",
                )
            )

    def _admit(self) -> None:
        gate = ExecutionAdmissionGate(
            self.store,
            self.graphs,
            self.modules,
            self.accounting,
            lambda ref, digest: ref in self.compiled.config_by_ref and ref == digest,
            lambda ref: ref == POLICY_REF,
        )
        gate.admit(
            admission_ref="admission:first-slice/1",
            execution_ref=self.execution_ref,
            graph_revision_ref=self.compiled.graph_revision.graph_revision_ref,
            runtime_policy_ref=POLICY_REF,
        )

    def _run_module_instance(
        self, module_instance_revision_ref: str, step: str
    ) -> tuple:
        activation_ref = f"activation:first-slice/{step}"
        run_ref = f"run:first-slice/{step}"
        activation = self.activations.create_next(
            activation_ref=activation_ref,
            execution_ref=self.execution_ref,
            module_instance_revision_ref=module_instance_revision_ref,
            created_event_ref=f"event:activation:{step}",
        )
        self.runs.create_initial(
            run_ref=run_ref, activation_ref=activation_ref, execution_ref=self.execution_ref
        )
        output_packets = self.executor.execute(run_ref)
        self.assertEqual(1, len(output_packets))
        output = output_packets[0]
        for packet in output_packets:
            self.projector.project(packet.packet_ref)
        return activation, output

    def test_text_input_to_mock_llm_to_text_output_end_to_end(self) -> None:
        workflow = self.workflows.publish(build_workflow())
        self.compiled = self.compiler.compile(workflow)
        self.executor = self._build_executor()
        self.execution_ref = "execution:first-slice/1"

        self.assertTrue(self.compiled.graph_revision.executable)
        self.assertEqual(3, len(self.compiled.graph_revision.module_instance_revisions))
        self.assertEqual(3, len(self.compiled.graph_revision.edges))

        self._publish_accounting_scopes()
        self._admit()

        # Kick off execution through the ordinary EXTERNAL_INPUT Packet ->
        # Delivery -> Activation ingress path (never a direct Activation).
        ingress_source_ref, ingress_source_port = self.compiled.ingress_by_entrypoint[
            ("input-node", "start")
        ]
        self.values.put("value:workflow-start", None)
        ingress_packet = self.packets.commit(
            packet_ref="packet:workflow-start",
            execution_ref=self.execution_ref,
            graph_revision_ref=self.compiled.graph_revision.graph_revision_ref,
            source_kind="EXTERNAL_INPUT",
            source_ref=ingress_source_ref,
            source_port_ref=ingress_source_port,
            value_ref="value:workflow-start",
            schema_ref="schema:null",
            caused_by_ref="cause:workflow-start",
            created_event_ref="event:workflow-start",
        )
        self.projector.project(ingress_packet.packet_ref)

        input_module_ref = self.compiled.module_instance_revision_ref_by_node[
            "input-node"
        ]
        llm_module_ref = self.compiled.module_instance_revision_ref_by_node["llm-node"]
        output_module_ref = self.compiled.module_instance_revision_ref_by_node[
            "output-node"
        ]

        _, input_output = self._run_module_instance(input_module_ref, "input")
        self.assertEqual(INPUT_TEXT, self.values.resolve(input_output.value_ref))

        _, llm_output = self._run_module_instance(llm_module_ref, "llm")
        self.assertEqual(EXPECTED_RESULT, self.values.resolve(llm_output.value_ref))

        _, output_output = self._run_module_instance(output_module_ref, "output")
        self.assertEqual(EXPECTED_RESULT, self.values.resolve(output_output.value_ref))

        # The declared Product output resolves to the exact final value.
        output_ref, module_instance_revision_ref, module_output_port_name = (
            self.compiled.output_bindings[0]
        )
        self.assertEqual("result", output_ref)
        self.assertEqual(output_module_ref, module_instance_revision_ref)
        self.assertEqual("text", module_output_port_name)
        self.assertEqual(output_module_ref, output_output.source_ref)
        self.assertEqual("text", output_output.source_port_ref)

        # Replay-safe: projecting the terminal output Packet again is
        # idempotent, exactly as the accepted single-module first slice.
        replay = self.projector.project(output_output.packet_ref)
        self.assertEqual((), replay)


if __name__ == "__main__":
    unittest.main()
