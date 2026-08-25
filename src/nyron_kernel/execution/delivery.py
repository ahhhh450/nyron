"""Deterministic, replay-safe Packet to Delivery projection."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass

from nyron_kernel.store import SQLiteStore

from .packet import Packet, PacketRepository


class DeliveryError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class Delivery:
    packet_ref: str
    graph_revision_ref: str
    edge_ref: str
    target_module_instance_revision_ref: str
    target_port_ref: str
    source_packet_seq: int
    edge_ordinal: int
    target_port_ordinal: int

    @property
    def uniqueness_key(self) -> tuple[str, str, str, str]:
        return (
            self.packet_ref,
            self.graph_revision_ref,
            self.edge_ref,
            self.target_port_ref,
        )

    @property
    def delivery_order_key(self) -> tuple[int, int, int]:
        return (
            self.source_packet_seq,
            self.edge_ordinal,
            self.target_port_ordinal,
        )


class DeliveryProjector:
    """Read immutable Graph Edge facts and persist target Deliveries."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._packets = PacketRepository(store)

    def project(
        self, packet_ref: str, edge_refs: Iterable[str] | None = None
    ) -> tuple[Delivery, ...]:
        packet = self._packets.resolve(packet_ref)
        if packet is None:
            raise DeliveryError("UNRESOLVED_PACKET_REFERENCE", packet_ref=packet_ref)

        if edge_refs is None:
            rows = self._store.connection.execute(
                """
                SELECT * FROM graph_edges
                WHERE graph_revision_ref = ?
                  AND source_ref = ?
                  AND source_port_ref = ?
                ORDER BY edge_ordinal, target_port_ordinal, edge_ref
                """,
                (
                    packet.graph_revision_ref,
                    packet.source_ref,
                    packet.source_port_ref,
                ),
            ).fetchall()
            selected_edge_refs: Iterable[str] = (row["edge_ref"] for row in rows)
        else:
            selected_edge_refs = edge_refs

        for edge_ref in selected_edge_refs:
            self._project_edge(packet, edge_ref)
        return self.list_for_packet(packet_ref)

    def list_for_packet(self, packet_ref: str) -> tuple[Delivery, ...]:
        return self._list("WHERE packet_ref = ?", (packet_ref,))

    def list_all(self) -> tuple[Delivery, ...]:
        """Return canonical Delivery order, independent of projection order."""

        return self._list("", ())

    def _list(
        self, where_clause: str, parameters: tuple[object, ...]
    ) -> tuple[Delivery, ...]:
        rows = self._store.connection.execute(
            f"""
            SELECT packet_ref, graph_revision_ref, edge_ref,
                   target_module_instance_revision_ref, target_port_ref,
                   source_packet_seq, edge_ordinal, target_port_ordinal
            FROM deliveries {where_clause}
            ORDER BY source_packet_seq, edge_ordinal, target_port_ordinal,
                     edge_ref, target_port_ref
            """,
            parameters,
        ).fetchall()
        return tuple(Delivery(**dict(row)) for row in rows)

    def _project_edge(self, packet: Packet, edge_ref: str) -> None:
        if not isinstance(edge_ref, str) or not edge_ref:
            raise DeliveryError("UNRESOLVED_EDGE_REFERENCE", edge_ref=edge_ref)

        with self._store.transaction() as connection:
            graph = connection.execute(
                """
                SELECT executable FROM graph_revisions
                WHERE graph_revision_ref = ?
                """,
                (packet.graph_revision_ref,),
            ).fetchone()
            if graph is None or not bool(graph["executable"]):
                raise DeliveryError(
                    "UNRESOLVED_GRAPH_REFERENCE",
                    graph_revision_ref=packet.graph_revision_ref,
                )

            edge = connection.execute(
                """
                SELECT * FROM graph_edges
                WHERE graph_revision_ref = ? AND edge_ref = ?
                """,
                (packet.graph_revision_ref, edge_ref),
            ).fetchone()
            if edge is None:
                raise DeliveryError(
                    "UNRESOLVED_EDGE_REFERENCE", edge_ref=edge_ref
                )
            if (
                edge["source_ref"] != packet.source_ref
                or edge["source_port_ref"] != packet.source_port_ref
            ):
                raise DeliveryError(
                    "EDGE_SOURCE_MISMATCH", edge_ref=edge_ref
                )

            target = connection.execute(
                """
                SELECT input_port_contract_json
                FROM module_instance_revisions
                WHERE module_instance_revision_ref = ?
                  AND graph_revision_ref = ?
                """,
                (
                    edge["target_module_instance_revision_ref"],
                    packet.graph_revision_ref,
                ),
            ).fetchone()
            if target is None or edge["target_port_ref"] not in json.loads(
                target["input_port_contract_json"]
            ):
                raise DeliveryError(
                    "UNRESOLVED_MODULE_ROUTING_REFERENCE", edge_ref=edge_ref
                )

            try:
                connection.execute(
                    """
                    INSERT INTO deliveries(
                        packet_ref, graph_revision_ref, edge_ref,
                        target_module_instance_revision_ref, target_port_ref,
                        source_packet_seq, edge_ordinal, target_port_ordinal
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(
                        packet_ref, graph_revision_ref, edge_ref, target_port_ref
                    ) DO NOTHING
                    """,
                    (
                        packet.packet_ref,
                        packet.graph_revision_ref,
                        edge["edge_ref"],
                        edge["target_module_instance_revision_ref"],
                        edge["target_port_ref"],
                        packet.source_packet_seq,
                        edge["edge_ordinal"],
                        edge["target_port_ordinal"],
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise DeliveryError(
                    "DELIVERY_PROJECTION_CONFLICT", edge_ref=edge_ref
                ) from error
