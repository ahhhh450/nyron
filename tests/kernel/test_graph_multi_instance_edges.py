"""NYRON-T-20260828-171 — Graph multi-instance / Edge publication validation.

Closes NYRON-T-20260828-170-F-001 (single-instance-only ``publish()``) and
F-002 (edge/port/topology correctness checked too late): proves
``GraphRepository.publish()`` atomically writes an ordered set of
``ModuleInstanceRevision``s and ``Edge``s and performs the frozen G-INV-04
through G-INV-09 validation at publish time.
"""

from __future__ import annotations

import unittest

from nyron_kernel.definitions import ModuleDefinition, ModuleRegistry, PortDefinition
from nyron_kernel.graph import (
    EdgeRequest,
    GraphError,
    GraphRepository,
    ModuleInstanceRevision,
)
from nyron_kernel.store import SQLiteStore

GRAPH = "graph:multi@1"


def module_x() -> ModuleDefinition:
    """One independent SINGLE_SOURCE/TRIGGER input, one string output."""
    return ModuleDefinition(
        module_ref="test.graph.x",
        version="1",
        input_port_definitions=(
            PortDefinition("in", {"type": "string"}, "TRIGGER", "SINGLE_SOURCE"),
        ),
        output_port_definitions=(PortDefinition("out", {"type": "string"}),),
        config_schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        effect_classes=("PURE",),
        required_capability_types=(),
        execution_contract={"kind": "execute"},
    )


def module_y() -> ModuleDefinition:
    """One independent MULTI_SOURCE/TRIGGER input, one string output."""
    return ModuleDefinition(
        module_ref="test.graph.y",
        version="1",
        input_port_definitions=(
            PortDefinition("in", {"type": "string"}, "TRIGGER", "MULTI_SOURCE"),
        ),
        output_port_definitions=(PortDefinition("out", {"type": "string"}),),
        config_schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        effect_classes=("PURE",),
        required_capability_types=(),
        execution_contract={"kind": "execute"},
    )


def module_z() -> ModuleDefinition:
    """One TRIGGER integer input -- incompatible with X/Y's string output."""
    return ModuleDefinition(
        module_ref="test.graph.z",
        version="1",
        input_port_definitions=(
            PortDefinition("in", {"type": "integer"}, "TRIGGER", "SINGLE_SOURCE"),
        ),
        output_port_definitions=(PortDefinition("out", {"type": "integer"}),),
        config_schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        effect_classes=("PURE",),
        required_capability_types=(),
        execution_contract={"kind": "execute"},
    )


def instance(
    module_instance_ref: str,
    module_ref: str = "test.graph.x",
    module_version: str = "1",
    graph_revision_ref: str = GRAPH,
) -> ModuleInstanceRevision:
    return ModuleInstanceRevision(
        module_instance_revision_ref=f"module-instance:{module_instance_ref}",
        graph_revision_ref=graph_revision_ref,
        module_instance_ref=module_instance_ref,
        module_ref=module_ref,
        module_version=module_version,
        config_ref="config:empty",
        config_hash="sha256:empty",
        input_port_contract={},
        output_port_contract={},
        static_composite_path=("root",),
        static_accounting_scope_ref=f"accounting:{module_instance_ref}",
    )


class GraphMultiInstanceEdgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.registry = ModuleRegistry(self.store)
        self.registry.register(module_x())
        self.registry.register(module_y())
        self.registry.register(module_z())
        self.graphs = GraphRepository(self.store, self.registry)

    def tearDown(self) -> None:
        self.store.close()

    def _row_counts(self, graph_revision_ref: str) -> tuple[int, int, int]:
        connection = self.store.connection
        revisions = connection.execute(
            "SELECT COUNT(*) FROM graph_revisions WHERE graph_revision_ref = ?",
            (graph_revision_ref,),
        ).fetchone()[0]
        instances = connection.execute(
            "SELECT COUNT(*) FROM module_instance_revisions WHERE graph_revision_ref = ?",
            (graph_revision_ref,),
        ).fetchone()[0]
        edges = connection.execute(
            "SELECT COUNT(*) FROM graph_edges WHERE graph_revision_ref = ?",
            (graph_revision_ref,),
        ).fetchone()[0]
        return revisions, instances, edges

    def test_valid_multi_instance_and_edge_set_publishes_atomically(self) -> None:
        a = instance("a")
        b = instance("b")
        published = self.graphs.publish(
            GRAPH,
            (a, b),
            (
                EdgeRequest(
                    edge_ref="edge:a-b",
                    source_ref="a",
                    source_port_ref="out",
                    target_ref="b",
                    target_port_ref="in",
                ),
            ),
        )
        self.assertTrue(published.executable)
        self.assertIsNone(published.reason_code)
        self.assertEqual(2, len(published.module_instance_revisions))
        self.assertEqual(1, len(published.edges))
        self.assertEqual((1, 2, 1), self._row_counts(GRAPH))
        self.assertEqual(published, self.graphs.resolve(GRAPH))

    def test_missing_target_instance_fails_closed_with_no_partial_write(self) -> None:
        with self.assertRaises(GraphError) as raised:
            self.graphs.publish(
                GRAPH,
                (instance("a"),),
                (
                    EdgeRequest(
                        edge_ref="edge:bad",
                        source_ref="a",
                        source_port_ref="out",
                        target_ref="does-not-exist",
                        target_port_ref="in",
                    ),
                ),
            )
        self.assertEqual("UNRESOLVED_EDGE_TARGET", raised.exception.code)
        self.assertEqual((0, 0, 0), self._row_counts(GRAPH))

    def test_missing_target_port_fails_closed(self) -> None:
        with self.assertRaises(GraphError) as raised:
            self.graphs.publish(
                GRAPH,
                (instance("a"), instance("b")),
                (
                    EdgeRequest(
                        edge_ref="edge:bad",
                        source_ref="a",
                        source_port_ref="out",
                        target_ref="b",
                        target_port_ref="does-not-exist",
                    ),
                ),
            )
        self.assertEqual("UNRESOLVED_EDGE_TARGET_PORT", raised.exception.code)

    def test_wrong_direction_source_port_fails_closed(self) -> None:
        # "in" is an input port on `a`, never a valid Edge source port.
        with self.assertRaises(GraphError) as raised:
            self.graphs.publish(
                GRAPH,
                (instance("a"), instance("b")),
                (
                    EdgeRequest(
                        edge_ref="edge:bad",
                        source_ref="a",
                        source_port_ref="in",
                        target_ref="b",
                        target_port_ref="in",
                    ),
                ),
            )
        self.assertEqual("UNRESOLVED_EDGE_SOURCE_PORT", raised.exception.code)

    def test_incompatible_schema_fails_closed(self) -> None:
        with self.assertRaises(GraphError) as raised:
            self.graphs.publish(
                GRAPH,
                (instance("a"), instance("z", module_ref="test.graph.z")),
                (
                    EdgeRequest(
                        edge_ref="edge:bad",
                        source_ref="a",
                        source_port_ref="out",
                        target_ref="z",
                        target_port_ref="in",
                    ),
                ),
            )
        self.assertEqual("EDGE_SCHEMA_INCOMPATIBLE", raised.exception.code)

    def test_duplicate_illegal_edge_fails_closed(self) -> None:
        edge = EdgeRequest(
            edge_ref="edge:1",
            source_ref="a",
            source_port_ref="out",
            target_ref="b",
            target_port_ref="in",
        )
        duplicate = EdgeRequest(
            edge_ref="edge:2",
            source_ref="a",
            source_port_ref="out",
            target_ref="b",
            target_port_ref="in",
        )
        with self.assertRaises(GraphError) as raised:
            self.graphs.publish(GRAPH, (instance("a"), instance("b")), (edge, duplicate))
        self.assertEqual("DUPLICATE_EDGE", raised.exception.code)

    def test_single_source_cardinality_overflow_fails_closed(self) -> None:
        # "b".in is explicitly SINGLE_SOURCE: two distinct sources
        # feeding it is a cardinality violation.
        with self.assertRaises(GraphError) as raised:
            self.graphs.publish(
                GRAPH,
                (instance("a"), instance("c"), instance("b")),
                (
                    EdgeRequest("edge:1", "a", "out", "b", "in"),
                    EdgeRequest("edge:2", "c", "out", "b", "in"),
                ),
            )
        self.assertEqual("EDGE_CARDINALITY_VIOLATION", raised.exception.code)

    def test_multi_source_trigger_tolerates_multiple_edges(self) -> None:
        # "y".in is MULTI_SOURCE TRIGGER: two sources is frozen-legal.
        published = self.graphs.publish(
            GRAPH,
            (instance("a"), instance("c"), instance("y", module_ref="test.graph.y")),
            (
                EdgeRequest("edge:1", "a", "out", "y", "in"),
                EdgeRequest("edge:2", "c", "out", "y", "in"),
            ),
        )
        self.assertTrue(published.executable)
        self.assertEqual(2, len(published.edges))

    def test_undeclared_two_node_cycle_fails_closed(self) -> None:
        with self.assertRaises(GraphError) as raised:
            self.graphs.publish(
                GRAPH,
                (instance("a"), instance("b")),
                (
                    EdgeRequest("edge:1", "a", "out", "b", "in"),
                    EdgeRequest("edge:2", "b", "out", "a", "in"),
                ),
            )
        self.assertEqual("UNDECLARED_GRAPH_CYCLE", raised.exception.code)

    def test_feedback_role_makes_the_same_cycle_legal(self) -> None:
        published = self.graphs.publish(
            GRAPH,
            (instance("a"), instance("b")),
            (
                EdgeRequest("edge:1", "a", "out", "b", "in"),
                EdgeRequest("edge:2", "b", "out", "a", "in", role="FEEDBACK"),
            ),
        )
        self.assertTrue(published.executable)
        roles = {edge.edge_ref: edge.role for edge in published.edges}
        self.assertEqual("NORMAL", roles["edge:1"])
        self.assertEqual("FEEDBACK", roles["edge:2"])

    def test_self_loop_requires_feedback(self) -> None:
        with self.assertRaises(GraphError) as raised:
            self.graphs.publish(
                GRAPH,
                (instance("a"),),
                (EdgeRequest("edge:self", "a", "out", "a", "in"),),
            )
        self.assertEqual("UNDECLARED_GRAPH_CYCLE", raised.exception.code)

        published = self.graphs.publish(
            "graph:multi@2",
            (instance("a", graph_revision_ref="graph:multi@2"),),
            (EdgeRequest("edge:self", "a", "out", "a", "in", role="FEEDBACK"),),
        )
        self.assertTrue(published.executable)

    def test_external_ingress_edge_is_not_part_of_module_cycle_topology(self) -> None:
        published = self.graphs.publish(
            GRAPH,
            (instance("a"),),
            (
                EdgeRequest(
                    edge_ref="edge:ingress",
                    source_ref="external:workflow-start",
                    source_port_ref="out",
                    target_ref="a",
                    target_port_ref="in",
                ),
            ),
        )
        self.assertTrue(published.executable)
        self.assertEqual("external:workflow-start", published.edges[0].source_ref)

    def test_identical_replay_is_idempotent(self) -> None:
        edges = (EdgeRequest("edge:1", "a", "out", "b", "in"),)
        first = self.graphs.publish(GRAPH, (instance("a"), instance("b")), edges)
        second = self.graphs.publish(GRAPH, (instance("a"), instance("b")), edges)
        self.assertEqual(first, second)
        self.assertEqual((1, 2, 1), self._row_counts(GRAPH))

    def test_conflicting_replay_fails_closed(self) -> None:
        self.graphs.publish(
            GRAPH,
            (instance("a"), instance("b")),
            (EdgeRequest("edge:1", "a", "out", "b", "in"),),
        )
        with self.assertRaises(GraphError) as raised:
            self.graphs.publish(GRAPH, (instance("a"), instance("b")), ())
        self.assertEqual("GRAPH_REVISION_IMMUTABLE", raised.exception.code)

    def test_unresolved_module_reference_stores_non_executable_without_full_validation(
        self,
    ) -> None:
        broken = instance("missing", module_ref="does.not.exist", module_version="9")
        published = self.graphs.publish(GRAPH, (instance("a"), broken), ())
        self.assertFalse(published.executable)
        self.assertEqual("UNRESOLVED_MODULE_REFERENCE", published.reason_code)
        self.assertEqual(published, self.graphs.resolve(GRAPH))

    def test_reusing_module_instance_revision_ref_across_graphs_rolls_back(self) -> None:
        shared = instance("a")
        self.graphs.publish(GRAPH, (shared,))

        colliding = ModuleInstanceRevision(
            module_instance_revision_ref=shared.module_instance_revision_ref,
            graph_revision_ref="graph:multi@other",
            module_instance_ref="a",
            module_ref="test.graph.x",
            module_version="1",
            config_ref="config:empty",
            config_hash="sha256:empty",
            input_port_contract={},
            output_port_contract={},
            static_composite_path=("root",),
            static_accounting_scope_ref="accounting:a",
        )
        with self.assertRaises(GraphError) as raised:
            self.graphs.publish("graph:multi@other", (colliding,))
        self.assertEqual("GRAPH_REVISION_IMMUTABLE", raised.exception.code)
        self.assertEqual((0, 0, 0), self._row_counts("graph:multi@other"))

    def test_legacy_single_instance_call_shape_still_works(self) -> None:
        published = self.graphs.publish(GRAPH, instance("a"))
        self.assertTrue(published.executable)
        self.assertEqual(1, len(published.module_instance_revisions))
        self.assertEqual("a", published.module_instance_revision.module_instance_ref)


if __name__ == "__main__":
    unittest.main()
