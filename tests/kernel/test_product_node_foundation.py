"""NYRON-T-20260828-171 — ProductNodeDefinition / VisualWorkflowRevision.

Proves the new bounded Product subsystem: exact Module binding without
duplicated Module identity, fail-closed NodeConnection/Graph validation,
immutable VisualWorkflowRevision replay/conflict semantics, and exact
Product-node/Module version pinning for reproducibility.
"""

from __future__ import annotations

import unittest

from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.modules import builtin_text_concat
from nyron_kernel.product import (
    EntrypointBinding,
    NodeConnection,
    NodeInstance,
    OutputBinding,
    ProductDefinitionError,
    ProductNodeDefinition,
    ProductNodeRegistry,
    ProductPortBinding,
    ProductWorkflowError,
    ProductWorkflowRepository,
    VisualWorkflowRevision,
    WorkflowLayoutRecord,
    WorkflowLayoutRepository,
)
from nyron_kernel.store import SQLiteStore


def concat_node_definition(**changes: object) -> ProductNodeDefinition:
    values: dict[str, object] = dict(
        product_node_type_ref="product.concat",
        product_node_version="1",
        bound_module_ref=builtin_text_concat.MODULE_REF,
        bound_module_version=builtin_text_concat.MODULE_VERSION,
        input_port_bindings=(
            ProductPortBinding("a", "a"),
            ProductPortBinding("b", "b"),
        ),
        output_port_bindings=(ProductPortBinding("text", "text"),),
        product_config_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        display_metadata={"label": "Concat"},
    )
    values.update(changes)
    return ProductNodeDefinition(**values)  # type: ignore[arg-type]


class ProductNodeDefinitionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.modules = ModuleRegistry(self.store)
        self.modules.register(builtin_text_concat.definition())
        self.nodes = ProductNodeRegistry(self.store, self.modules)

    def tearDown(self) -> None:
        self.store.close()

    def test_registers_and_exactly_resolves(self) -> None:
        registered = self.nodes.register(concat_node_definition())
        resolved = self.nodes.resolve("product.concat", "1")
        self.assertEqual(registered, resolved)

    def test_identical_reregister_is_idempotent(self) -> None:
        first = self.nodes.register(concat_node_definition())
        second = self.nodes.register(concat_node_definition())
        self.assertEqual(first, second)

    def test_conflicting_reregister_fails_closed(self) -> None:
        self.nodes.register(concat_node_definition())
        with self.assertRaises(ProductDefinitionError) as raised:
            self.nodes.register(
                concat_node_definition(display_metadata={"label": "Different"})
            )
        self.assertEqual("PRODUCT_NODE_VERSION_CONFLICT", raised.exception.code)

    def test_unresolved_bound_module_fails_closed(self) -> None:
        with self.assertRaises(ProductDefinitionError) as raised:
            self.nodes.register(
                concat_node_definition(bound_module_ref="does.not.exist")
            )
        self.assertEqual("UNRESOLVED_MODULE_REFERENCE", raised.exception.code)

    def test_port_binding_to_missing_module_port_fails_closed(self) -> None:
        with self.assertRaises(ProductDefinitionError) as raised:
            self.nodes.register(
                concat_node_definition(
                    input_port_bindings=(
                        ProductPortBinding("a", "a"),
                        ProductPortBinding("b", "nonexistent"),
                    )
                )
            )
        self.assertEqual("PRODUCT_PORT_BINDING_UNRESOLVED", raised.exception.code)

    def test_incomplete_port_binding_fails_closed(self) -> None:
        with self.assertRaises(ProductDefinitionError) as raised:
            self.nodes.register(
                concat_node_definition(input_port_bindings=(ProductPortBinding("a", "a"),))
            )
        self.assertEqual("PRODUCT_PORT_BINDING_INCOMPLETE", raised.exception.code)

    def test_config_schema_cannot_widen_additional_properties(self) -> None:
        with self.assertRaises(ProductDefinitionError) as raised:
            self.nodes.register(
                concat_node_definition(
                    product_config_schema={
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": True,
                    }
                )
            )
        self.assertEqual(
            "PRODUCT_CONFIG_WIDENS_MODULE_AUTHORITY", raised.exception.code
        )

    def test_config_schema_cannot_declare_property_module_does_not_have(self) -> None:
        with self.assertRaises(ProductDefinitionError) as raised:
            self.nodes.register(
                concat_node_definition(
                    product_config_schema={
                        "type": "object",
                        "properties": {"extra": {"type": "string"}},
                        "required": [],
                        "additionalProperties": False,
                    }
                )
            )
        self.assertEqual(
            "PRODUCT_CONFIG_WIDENS_MODULE_AUTHORITY", raised.exception.code
        )


def two_node_workflow(**changes: object) -> VisualWorkflowRevision:
    values: dict[str, object] = dict(
        workflow_revision_ref="workflow-revision:1",
        workflow_ref="workflow:demo",
        predecessor_workflow_revision_ref=None,
        node_instances=(
            NodeInstance("node-a", "product.concat", "1", config={}),
            NodeInstance("node-b", "product.concat", "1", config={}),
        ),
        node_connections=(
            NodeConnection("conn-1", "node-a", "text", "node-b", "a"),
        ),
        entrypoints=(EntrypointBinding("node-a", "b"), EntrypointBinding("node-b", "b")),
        product_outputs=(OutputBinding("out-1", "node-b", "text"),),
        product_metadata={"name": "Demo"},
    )
    values.update(changes)
    return VisualWorkflowRevision(**values)  # type: ignore[arg-type]


class ProductWorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.modules = ModuleRegistry(self.store)
        self.modules.register(builtin_text_concat.definition())
        self.nodes = ProductNodeRegistry(self.store, self.modules)
        self.nodes.register(concat_node_definition())
        self.workflows = ProductWorkflowRepository(self.store, self.nodes, self.modules)

    def tearDown(self) -> None:
        self.store.close()

    def test_valid_workflow_publishes_and_resolves(self) -> None:
        published = self.workflows.publish(two_node_workflow())
        self.assertEqual(published, self.workflows.resolve("workflow-revision:1"))

    def test_unresolved_node_definition_fails_closed(self) -> None:
        with self.assertRaises(ProductWorkflowError) as raised:
            self.workflows.publish(
                two_node_workflow(
                    node_instances=(
                        NodeInstance("node-a", "product.missing", "1", config={}),
                        NodeInstance("node-b", "product.concat", "1", config={}),
                    )
                )
            )
        self.assertEqual(
            "PRODUCT_NODE_DEFINITION_UNRESOLVED", raised.exception.code
        )

    def test_bad_config_against_product_schema_fails_closed(self) -> None:
        with self.assertRaises(ProductWorkflowError) as raised:
            self.workflows.publish(
                two_node_workflow(
                    node_instances=(
                        NodeInstance(
                            "node-a", "product.concat", "1", config={"unexpected": 1}
                        ),
                        NodeInstance("node-b", "product.concat", "1", config={}),
                    )
                )
            )
        self.assertEqual("PRODUCT_NODE_CONFIG_INVALID", raised.exception.code)

    def test_connection_unresolved_endpoint_fails_closed(self) -> None:
        with self.assertRaises(ProductWorkflowError) as raised:
            self.workflows.publish(
                two_node_workflow(
                    node_connections=(
                        NodeConnection("conn-1", "node-a", "text", "missing", "a"),
                    )
                )
            )
        self.assertEqual(
            "PRODUCT_CONNECTION_UNRESOLVED_ENDPOINT", raised.exception.code
        )

    def test_connection_wrong_direction_port_fails_closed(self) -> None:
        with self.assertRaises(ProductWorkflowError) as raised:
            self.workflows.publish(
                two_node_workflow(
                    node_connections=(
                        # "a" is node-a's *input* port name, never a valid source.
                        NodeConnection("conn-1", "node-a", "a", "node-b", "a"),
                    )
                )
            )
        self.assertEqual(
            "PRODUCT_CONNECTION_UNRESOLVED_ENDPOINT", raised.exception.code
        )

    def test_duplicate_connection_fails_closed(self) -> None:
        with self.assertRaises(ProductWorkflowError) as raised:
            self.workflows.publish(
                two_node_workflow(
                    node_connections=(
                        NodeConnection("conn-1", "node-a", "text", "node-b", "a"),
                        NodeConnection("conn-2", "node-a", "text", "node-b", "a"),
                    )
                )
            )
        self.assertEqual("PRODUCT_CONNECTION_DUPLICATE", raised.exception.code)

    def test_entrypoint_unresolved_fails_closed(self) -> None:
        with self.assertRaises(ProductWorkflowError) as raised:
            self.workflows.publish(
                two_node_workflow(entrypoints=(EntrypointBinding("node-a", "missing"),))
            )
        self.assertEqual(
            "PRODUCT_WORKFLOW_ENTRYPOINT_UNRESOLVED", raised.exception.code
        )

    def test_output_unresolved_fails_closed(self) -> None:
        with self.assertRaises(ProductWorkflowError) as raised:
            self.workflows.publish(
                two_node_workflow(
                    product_outputs=(OutputBinding("out-1", "node-b", "missing"),)
                )
            )
        self.assertEqual("PRODUCT_WORKFLOW_OUTPUT_UNRESOLVED", raised.exception.code)

    def test_unresolved_predecessor_fails_closed(self) -> None:
        with self.assertRaises(ProductWorkflowError) as raised:
            self.workflows.publish(
                two_node_workflow(
                    workflow_revision_ref="workflow-revision:2",
                    predecessor_workflow_revision_ref="workflow-revision:does-not-exist",
                )
            )
        self.assertEqual(
            "PRODUCT_WORKFLOW_PREDECESSOR_UNRESOLVED", raised.exception.code
        )

    def test_valid_predecessor_chain_preserves_both_revisions(self) -> None:
        first = self.workflows.publish(two_node_workflow())
        second = self.workflows.publish(
            two_node_workflow(
                workflow_revision_ref="workflow-revision:2",
                predecessor_workflow_revision_ref="workflow-revision:1",
                product_metadata={"name": "Demo v2"},
            )
        )
        self.assertEqual(first, self.workflows.resolve("workflow-revision:1"))
        self.assertEqual(second, self.workflows.resolve("workflow-revision:2"))
        self.assertEqual(
            "workflow-revision:1", second.predecessor_workflow_revision_ref
        )

    def test_identical_replay_is_idempotent(self) -> None:
        first = self.workflows.publish(two_node_workflow())
        second = self.workflows.publish(two_node_workflow())
        self.assertEqual(first, second)

    def test_conflicting_replay_fails_closed(self) -> None:
        self.workflows.publish(two_node_workflow())
        with self.assertRaises(ProductWorkflowError) as raised:
            self.workflows.publish(
                two_node_workflow(product_metadata={"name": "Changed"})
            )
        self.assertEqual(
            "PRODUCT_WORKFLOW_REVISION_CONFLICT", raised.exception.code
        )

    def test_newer_node_definition_version_does_not_alter_saved_workflow(self) -> None:
        self.workflows.publish(two_node_workflow())

        self.nodes.register(
            concat_node_definition(
                product_node_version="2", display_metadata={"label": "Concat v2"}
            )
        )

        resolved = self.workflows.resolve("workflow-revision:1")
        node_a = next(
            node for node in resolved.node_instances if node.node_instance_ref == "node-a"
        )
        self.assertEqual("1", node_a.node_version)
        pinned = self.workflows.resolve_node_definition(node_a)
        self.assertEqual("1", pinned.product_node_version)

    def test_layout_is_freely_rewritable_without_new_workflow_revision(self) -> None:
        published = self.workflows.publish(two_node_workflow())
        layouts = WorkflowLayoutRepository(self.store)

        layouts.put(
            WorkflowLayoutRecord("workflow-revision:1", "node-a", {"x": 0, "y": 0})
        )
        layouts.put(
            WorkflowLayoutRecord("workflow-revision:1", "node-a", {"x": 120, "y": 40})
        )

        moved = layouts.resolve("workflow-revision:1", "node-a")
        self.assertEqual({"x": 120, "y": 40}, moved.layout)
        self.assertEqual(published, self.workflows.resolve("workflow-revision:1"))


if __name__ == "__main__":
    unittest.main()
