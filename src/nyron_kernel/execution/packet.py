"""Immutable durable Runtime Packet facts."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from nyron_kernel.store import SQLiteStore


class PacketError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class Packet:
    packet_ref: str
    execution_ref: str
    graph_revision_ref: str
    source_kind: str
    source_ref: str
    source_port_ref: str | None
    value_ref: str
    schema_ref: str
    source_packet_seq: int
    caused_by_ref: str
    created_event_ref: str


class PacketRepository:
    """Commit and resolve immutable Packet facts."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def commit(
        self,
        *,
        packet_ref: str,
        execution_ref: str,
        graph_revision_ref: str,
        source_kind: str,
        source_ref: str,
        source_port_ref: str | None,
        value_ref: str,
        schema_ref: str,
        caused_by_ref: str,
        created_event_ref: str,
    ) -> Packet:
        values = (
            packet_ref,
            execution_ref,
            graph_revision_ref,
            source_kind,
            source_ref,
            value_ref,
            schema_ref,
            caused_by_ref,
            created_event_ref,
        )
        if any(not isinstance(value, str) or not value for value in values):
            raise PacketError("PACKET_INVALID")
        if source_port_ref is not None and (
            not isinstance(source_port_ref, str) or not source_port_ref
        ):
            raise PacketError("PACKET_INVALID")

        requested = (
            execution_ref,
            graph_revision_ref,
            source_kind,
            source_ref,
            source_port_ref,
            value_ref,
            schema_ref,
            caused_by_ref,
            created_event_ref,
        )
        try:
            with self._store.transaction() as connection:
                existing = self._resolve_with(connection, packet_ref)
                if existing is not None:
                    if self._request_fields(existing) != requested:
                        raise PacketError(
                            "PACKET_IDENTITY_CONFLICT", packet_ref=packet_ref
                        )
                    return existing

                self._require_executable_graph(connection, graph_revision_ref)
                self._validate_module_source(
                    connection,
                    graph_revision_ref,
                    source_kind,
                    source_ref,
                    source_port_ref,
                )
                source_packet_seq = connection.execute(
                    """
                    SELECT COALESCE(MAX(source_packet_seq), 0) + 1
                    FROM packets WHERE execution_ref = ?
                    """,
                    (execution_ref,),
                ).fetchone()[0]
                connection.execute(
                    """
                    INSERT INTO packets(
                        packet_ref, execution_ref, graph_revision_ref,
                        source_kind, source_ref, source_port_ref, value_ref,
                        schema_ref, source_packet_seq, caused_by_ref,
                        created_event_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        packet_ref,
                        execution_ref,
                        graph_revision_ref,
                        source_kind,
                        source_ref,
                        source_port_ref,
                        value_ref,
                        schema_ref,
                        source_packet_seq,
                        caused_by_ref,
                        created_event_ref,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise PacketError(
                "PACKET_IDENTITY_CONFLICT", packet_ref=packet_ref
            ) from error

        resolved = self.resolve(packet_ref)
        if resolved is None:  # pragma: no cover - guards store corruption
            raise PacketError("PACKET_COMMIT_FAILED", packet_ref=packet_ref)
        return resolved

    def resolve(self, packet_ref: str) -> Packet | None:
        return self._resolve_with(self._store.connection, packet_ref)

    @staticmethod
    def _resolve_with(
        connection: sqlite3.Connection, packet_ref: str
    ) -> Packet | None:
        row = connection.execute(
            """
            SELECT packet_ref, execution_ref, graph_revision_ref, source_kind,
                   source_ref, source_port_ref, value_ref, schema_ref,
                   source_packet_seq, caused_by_ref, created_event_ref
            FROM packets WHERE packet_ref = ?
            """,
            (packet_ref,),
        ).fetchone()
        if row is None:
            return None
        return Packet(**dict(row))

    @staticmethod
    def _request_fields(packet: Packet) -> tuple[object, ...]:
        return (
            packet.execution_ref,
            packet.graph_revision_ref,
            packet.source_kind,
            packet.source_ref,
            packet.source_port_ref,
            packet.value_ref,
            packet.schema_ref,
            packet.caused_by_ref,
            packet.created_event_ref,
        )

    @staticmethod
    def _require_executable_graph(
        connection: sqlite3.Connection, graph_revision_ref: str
    ) -> None:
        row = connection.execute(
            """
            SELECT executable FROM graph_revisions
            WHERE graph_revision_ref = ?
            """,
            (graph_revision_ref,),
        ).fetchone()
        if row is None or not bool(row["executable"]):
            raise PacketError(
                "UNRESOLVED_GRAPH_REFERENCE",
                graph_revision_ref=graph_revision_ref,
            )

    @staticmethod
    def _validate_module_source(
        connection: sqlite3.Connection,
        graph_revision_ref: str,
        source_kind: str,
        source_ref: str,
        source_port_ref: str | None,
    ) -> None:
        if source_kind != "MODULE_OUTPUT":
            return
        if source_port_ref is None:
            raise PacketError("UNRESOLVED_MODULE_ROUTING_REFERENCE")
        row = connection.execute(
            """
            SELECT output_port_contract_json
            FROM module_instance_revisions
            WHERE module_instance_revision_ref = ?
              AND graph_revision_ref = ?
            """,
            (source_ref, graph_revision_ref),
        ).fetchone()
        if row is None:
            raise PacketError("UNRESOLVED_MODULE_ROUTING_REFERENCE")

        ports = json.loads(row["output_port_contract_json"])
        if source_port_ref not in ports:
            raise PacketError("UNRESOLVED_MODULE_ROUTING_REFERENCE")
