from __future__ import annotations

import tempfile
import unittest
from collections.abc import Iterator
from pathlib import Path

from nyron_kernel.definitions import (
    ModuleDefinition,
    ModuleRegistry,
    PortDefinition,
)
from nyron_kernel.execution import (
    DeliveryError,
    DeliveryProjector,
    PacketError,
    PacketRepository,
)
from nyron_kernel.graph import GraphRepository, ModuleInstanceRevision
from nyron_kernel.store import SQLiteStore


GRAPH_REF = "graph:delivery@1"
MODULE_REVISION_REF = "module-instance:concat@1"


def concat_definition() -> ModuleDefinition:
    return ModuleDefinition(
        module_ref="builtin.text.concat",
        version="1",
        input_port_definitions=(
            PortDefinition("a", {"type": "string"}, "REQUIRED_LATEST"),
            PortDefinition("b", {"type": "string"}, "TRIGGER"),
        ),
        output_port_definitions=(
            PortDefinition("text", {"type": "string"}),
        ),
        config_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        effect_classes=("PURE",),
        required_capability_types=(),
        execution_contract={"kind": "execute"},
        metadata={"display_name": "Text Concatenate"},
    )


def module_instance() -> ModuleInstanceRevision:
    return ModuleInstanceRevision(
        module_instance_revision_ref=MODULE_REVISION_REF,
        graph_revision_ref=GRAPH_REF,
        module_instance_ref="concat",
        module_ref="builtin.text.concat",
        module_version="1",
        config_ref="config:concat@1",
        config_hash="sha256:config-1",
        input_port_contract={"a": "REQUIRED_LATEST", "b": "TRIGGER"},
        output_port_contract={"text": {"type": "string"}},
        static_composite_path=("root",),
        static_accounting_scope_ref="accounting:project/alpha",
    )


class SegmentBPacketDeliveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self._publish_graph(self.store)
        self.packets = PacketRepository(self.store)
        self.projector = DeliveryProjector(self.store)

    def tearDown(self) -> None:
        self.store.close()

    @staticmethod
    def _publish_graph(store: SQLiteStore) -> None:
        registry = ModuleRegistry(store)
        registry.register(concat_definition())
        GraphRepository(store, registry).publish(GRAPH_REF, module_instance())

    @staticmethod
    def _seed_edge(
        store: SQLiteStore,
        *,
        edge_ref: str,
        target_port_ref: str,
        edge_ordinal: int,
        target_port_ordinal: int,
    ) -> None:
        # This fixture stands in for the Graph Owner writing immutable Edge facts.
        with store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO graph_edges(
                    graph_revision_ref, edge_ref, source_ref, source_port_ref,
                    target_module_instance_revision_ref, target_port_ref,
                    edge_ordinal, target_port_ordinal
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    GRAPH_REF,
                    edge_ref,
                    MODULE_REVISION_REF,
                    "text",
                    MODULE_REVISION_REF,
                    target_port_ref,
                    edge_ordinal,
                    target_port_ordinal,
                ),
            )

    @staticmethod
    def _commit_packet(
        repository: PacketRepository,
        *,
        packet_ref: str = "packet:1",
        value_ref: str = "value:1",
    ):
        return repository.commit(
            packet_ref=packet_ref,
            execution_ref="execution:1",
            graph_revision_ref=GRAPH_REF,
            source_kind="MODULE_OUTPUT",
            source_ref=MODULE_REVISION_REF,
            source_port_ref="text",
            value_ref=value_ref,
            schema_ref="schema:string@1",
            caused_by_ref="attempt:1",
            created_event_ref=f"event:{packet_ref}",
        )

    def test_packet_is_exact_immutable_and_durable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "nyron.db"
            with SQLiteStore(database) as first_store:
                self._publish_graph(first_store)
                packets = PacketRepository(first_store)
                committed = self._commit_packet(packets)
                self.assertEqual(committed, self._commit_packet(packets))
                with self.assertRaises(PacketError) as raised:
                    self._commit_packet(packets, value_ref="value:changed")
                self.assertEqual("PACKET_IDENTITY_CONFLICT", raised.exception.code)

            with SQLiteStore(database) as reopened_store:
                resolved = PacketRepository(reopened_store).resolve("packet:1")

        self.assertEqual(committed, resolved)
        self.assertEqual(1, resolved.source_packet_seq)

    def test_one_packet_across_one_edge_creates_exactly_one_delivery(self) -> None:
        self._seed_edge(
            self.store,
            edge_ref="edge:1",
            target_port_ref="b",
            edge_ordinal=4,
            target_port_ordinal=1,
        )
        packet = self._commit_packet(self.packets)

        deliveries = self.projector.project(packet.packet_ref)

        self.assertEqual(1, len(deliveries))
        self.assertEqual(
            ("packet:1", GRAPH_REF, "edge:1", "b"),
            deliveries[0].uniqueness_key,
        )

    def test_reprojection_is_idempotent_by_frozen_uniqueness_key(self) -> None:
        self._seed_edge(
            self.store,
            edge_ref="edge:1",
            target_port_ref="b",
            edge_ordinal=4,
            target_port_ordinal=1,
        )
        self._commit_packet(self.packets)

        first = self.projector.project("packet:1")
        second = self.projector.project("packet:1", ["edge:1"])

        self.assertEqual(first, second)
        self.assertEqual(1, len(second))

    def test_delivery_order_key_uses_only_committed_packet_and_edge_facts(self) -> None:
        self._seed_edge(
            self.store,
            edge_ref="edge:late-ordinal",
            target_port_ref="b",
            edge_ordinal=9,
            target_port_ordinal=1,
        )
        self._seed_edge(
            self.store,
            edge_ref="edge:early-ordinal",
            target_port_ref="a",
            edge_ordinal=2,
            target_port_ordinal=0,
        )
        packet = self._commit_packet(self.packets)

        deliveries = self.projector.project(
            packet.packet_ref, ["edge:late-ordinal", "edge:early-ordinal"]
        )

        self.assertEqual(
            [(1, 2, 0), (1, 9, 1)],
            [delivery.delivery_order_key for delivery in deliveries],
        )

    def test_same_history_is_deterministic_under_varied_projection_order(self) -> None:
        histories: list[tuple[tuple[object, ...], ...]] = []
        for edge_order in (
            ("edge:a", "edge:b"),
            ("edge:b", "edge:a"),
        ):
            store = SQLiteStore()
            try:
                self._publish_graph(store)
                self._seed_edge(
                    store,
                    edge_ref="edge:a",
                    target_port_ref="a",
                    edge_ordinal=3,
                    target_port_ordinal=0,
                )
                self._seed_edge(
                    store,
                    edge_ref="edge:b",
                    target_port_ref="b",
                    edge_ordinal=8,
                    target_port_ordinal=1,
                )
                packets = PacketRepository(store)
                self._commit_packet(packets, packet_ref="packet:1")
                self._commit_packet(packets, packet_ref="packet:2")
                projector = DeliveryProjector(store)
                projector.project("packet:2", edge_order)
                projector.project("packet:1", reversed(edge_order))
                histories.append(
                    tuple(
                        delivery.uniqueness_key + delivery.delivery_order_key
                        for delivery in projector.list_all()
                    )
                )
            finally:
                store.close()

        self.assertEqual(histories[0], histories[1])

    def test_interrupted_fan_out_replay_repairs_only_missing_deliveries(self) -> None:
        def interrupted_edges() -> Iterator[str]:
            yield "edge:a"
            raise RuntimeError("injected fan-out interruption")

        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "nyron.db"
            with SQLiteStore(database) as first_store:
                self._publish_graph(first_store)
                for edge_ref, port_ref, edge_ordinal, port_ordinal in (
                    ("edge:a", "a", 1, 0),
                    ("edge:b", "b", 2, 1),
                ):
                    self._seed_edge(
                        first_store,
                        edge_ref=edge_ref,
                        target_port_ref=port_ref,
                        edge_ordinal=edge_ordinal,
                        target_port_ordinal=port_ordinal,
                    )
                self._commit_packet(PacketRepository(first_store))
                first_projector = DeliveryProjector(first_store)
                with self.assertRaisesRegex(RuntimeError, "fan-out interruption"):
                    first_projector.project("packet:1", interrupted_edges())
                self.assertEqual(
                    1, len(first_projector.list_for_packet("packet:1"))
                )

            with SQLiteStore(database) as reopened_store:
                recovered_projector = DeliveryProjector(reopened_store)
                recovered = recovered_projector.project("packet:1")
                replayed = recovered_projector.project("packet:1")

        self.assertEqual(2, len(recovered))
        self.assertEqual(recovered, replayed)

    def test_unresolved_graph_edge_and_module_routing_fail_closed(self) -> None:
        with self.assertRaises(PacketError) as graph_error:
            self.packets.commit(
                packet_ref="packet:missing-graph",
                execution_ref="execution:1",
                graph_revision_ref="graph:missing",
                source_kind="MODULE_OUTPUT",
                source_ref=MODULE_REVISION_REF,
                source_port_ref="text",
                value_ref="value:1",
                schema_ref="schema:string@1",
                caused_by_ref="attempt:1",
                created_event_ref="event:1",
            )
        self.assertEqual("UNRESOLVED_GRAPH_REFERENCE", graph_error.exception.code)

        self._commit_packet(self.packets)
        with self.assertRaises(DeliveryError) as edge_error:
            self.projector.project("packet:1", ["edge:missing"])
        self.assertEqual("UNRESOLVED_EDGE_REFERENCE", edge_error.exception.code)

        self._seed_edge(
            self.store,
            edge_ref="edge:bad-port",
            target_port_ref="missing-port",
            edge_ordinal=1,
            target_port_ordinal=0,
        )
        with self.assertRaises(DeliveryError) as routing_error:
            self.projector.project("packet:1", ["edge:bad-port"])
        self.assertEqual(
            "UNRESOLVED_MODULE_ROUTING_REFERENCE", routing_error.exception.code
        )

    def test_failed_delivery_transaction_leaves_no_partial_row_and_can_retry(self) -> None:
        self._seed_edge(
            self.store,
            edge_ref="edge:1",
            target_port_ref="b",
            edge_ordinal=1,
            target_port_ordinal=1,
        )
        self._commit_packet(self.packets)
        self.store.connection.execute(
            """
            CREATE TRIGGER fail_delivery BEFORE INSERT ON deliveries
            BEGIN SELECT RAISE(ABORT, 'injected transaction failure'); END
            """
        )

        with self.assertRaises(DeliveryError) as raised:
            self.projector.project("packet:1")
        self.assertEqual("DELIVERY_PROJECTION_CONFLICT", raised.exception.code)
        self.assertEqual((), self.projector.list_for_packet("packet:1"))

        self.store.connection.execute("DROP TRIGGER fail_delivery")
        self.assertEqual(1, len(self.projector.project("packet:1")))

    def test_packet_source_routing_fails_closed(self) -> None:
        with self.assertRaises(PacketError) as raised:
            self.packets.commit(
                packet_ref="packet:bad-source",
                execution_ref="execution:1",
                graph_revision_ref=GRAPH_REF,
                source_kind="MODULE_OUTPUT",
                source_ref=MODULE_REVISION_REF,
                source_port_ref="missing-output",
                value_ref="value:1",
                schema_ref="schema:string@1",
                caused_by_ref="attempt:1",
                created_event_ref="event:1",
            )
        self.assertEqual(
            "UNRESOLVED_MODULE_ROUTING_REFERENCE", raised.exception.code
        )


if __name__ == "__main__":
    unittest.main()
