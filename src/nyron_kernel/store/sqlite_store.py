"""Minimal SQLite state store for Nyron's current canonical facts."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class SQLiteStore:
    """Own one SQLite connection and its explicit write transactions."""

    def __init__(self, database: str | Path = ":memory:") -> None:
        self.connection = sqlite3.connect(str(database), isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS module_definitions (
                module_ref TEXT NOT NULL,
                version TEXT NOT NULL,
                contract_json TEXT NOT NULL,
                PRIMARY KEY (module_ref, version)
            );

            CREATE TABLE IF NOT EXISTS graph_revisions (
                graph_revision_ref TEXT PRIMARY KEY,
                contract_json TEXT NOT NULL,
                executable INTEGER NOT NULL CHECK (executable IN (0, 1)),
                reason_code TEXT
            );

            CREATE TABLE IF NOT EXISTS module_instance_revisions (
                module_instance_revision_ref TEXT PRIMARY KEY,
                graph_revision_ref TEXT NOT NULL,
                module_instance_ref TEXT NOT NULL,
                module_ref TEXT NOT NULL,
                module_version TEXT NOT NULL,
                config_ref TEXT NOT NULL,
                config_hash TEXT NOT NULL,
                input_port_contract_json TEXT NOT NULL,
                output_port_contract_json TEXT NOT NULL,
                static_composite_path_json TEXT NOT NULL,
                static_accounting_scope_ref TEXT NOT NULL,
                UNIQUE (graph_revision_ref, module_instance_ref),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref)
            );

            CREATE TABLE IF NOT EXISTS graph_edges (
                graph_revision_ref TEXT NOT NULL,
                edge_ref TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                source_port_ref TEXT NOT NULL,
                target_module_instance_revision_ref TEXT NOT NULL,
                target_port_ref TEXT NOT NULL,
                edge_ordinal INTEGER NOT NULL CHECK (edge_ordinal >= 0),
                target_port_ordinal INTEGER NOT NULL
                    CHECK (target_port_ordinal >= 0),
                PRIMARY KEY (graph_revision_ref, edge_ref),
                UNIQUE (graph_revision_ref, edge_ordinal),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref),
                FOREIGN KEY (target_module_instance_revision_ref)
                    REFERENCES module_instance_revisions(
                        module_instance_revision_ref
                    )
            );

            CREATE TABLE IF NOT EXISTS packets (
                packet_ref TEXT PRIMARY KEY,
                execution_ref TEXT NOT NULL,
                graph_revision_ref TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                source_port_ref TEXT,
                value_ref TEXT NOT NULL,
                schema_ref TEXT NOT NULL,
                source_packet_seq INTEGER NOT NULL
                    CHECK (source_packet_seq > 0),
                caused_by_ref TEXT NOT NULL,
                created_event_ref TEXT NOT NULL,
                UNIQUE (execution_ref, source_packet_seq),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref)
            );

            CREATE TABLE IF NOT EXISTS deliveries (
                packet_ref TEXT NOT NULL,
                graph_revision_ref TEXT NOT NULL,
                edge_ref TEXT NOT NULL,
                target_module_instance_revision_ref TEXT NOT NULL,
                target_port_ref TEXT NOT NULL,
                source_packet_seq INTEGER NOT NULL,
                edge_ordinal INTEGER NOT NULL,
                target_port_ordinal INTEGER NOT NULL,
                PRIMARY KEY (
                    packet_ref,
                    graph_revision_ref,
                    edge_ref,
                    target_port_ref
                ),
                FOREIGN KEY (packet_ref) REFERENCES packets(packet_ref),
                FOREIGN KEY (graph_revision_ref, edge_ref)
                    REFERENCES graph_edges(graph_revision_ref, edge_ref),
                FOREIGN KEY (target_module_instance_revision_ref)
                    REFERENCES module_instance_revisions(
                        module_instance_revision_ref
                    )
            );

            CREATE TABLE IF NOT EXISTS accounting_scopes (
                accounting_scope_ref TEXT PRIMARY KEY,
                graph_revision_ref TEXT NOT NULL,
                definition_anchor_ref TEXT NOT NULL,
                parent_accounting_scope_ref TEXT,
                scope_kind TEXT NOT NULL,
                ancestry_hash TEXT NOT NULL,
                created_from_definition_ref TEXT NOT NULL,
                state TEXT NOT NULL,
                UNIQUE (graph_revision_ref, definition_anchor_ref)
            );

            CREATE TABLE IF NOT EXISTS execution_admissions (
                admission_ref TEXT PRIMARY KEY,
                execution_ref TEXT NOT NULL UNIQUE,
                graph_revision_ref TEXT NOT NULL,
                runtime_policy_ref TEXT NOT NULL,
                admitted_at_owner_order INTEGER NOT NULL UNIQUE
                    CHECK (admitted_at_owner_order > 0),
                state TEXT NOT NULL CHECK (state = 'ADMITTED'),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref)
            );

            CREATE TABLE IF NOT EXISTS workflow_executions (
                execution_ref TEXT PRIMARY KEY,
                graph_revision_ref TEXT NOT NULL,
                admission_ref TEXT NOT NULL UNIQUE,
                runtime_policy_ref TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state = 'ADMITTED'),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref),
                FOREIGN KEY (admission_ref)
                    REFERENCES execution_admissions(admission_ref)
            );

            """
        )

    def create_activation_schema(self) -> None:
        """Install the Task-scoped Runtime Activation canonical tables."""

        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS activations (
                activation_ref TEXT PRIMARY KEY,
                execution_ref TEXT NOT NULL,
                graph_revision_ref TEXT NOT NULL,
                module_instance_revision_ref TEXT NOT NULL,
                trigger_delivery_ref TEXT NOT NULL UNIQUE,
                input_bindings_json TEXT NOT NULL,
                static_accounting_scope_ref TEXT NOT NULL,
                created_event_ref TEXT NOT NULL UNIQUE,
                FOREIGN KEY (execution_ref)
                    REFERENCES workflow_executions(execution_ref),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref),
                FOREIGN KEY (module_instance_revision_ref)
                    REFERENCES module_instance_revisions(
                        module_instance_revision_ref
                    )
            );

            CREATE TABLE IF NOT EXISTS delivery_bindings (
                delivery_ref TEXT PRIMARY KEY,
                packet_ref TEXT NOT NULL,
                graph_revision_ref TEXT NOT NULL,
                edge_ref TEXT NOT NULL,
                target_port_ref TEXT NOT NULL,
                activation_ref TEXT NOT NULL,
                FOREIGN KEY (
                    packet_ref, graph_revision_ref, edge_ref, target_port_ref
                ) REFERENCES deliveries(
                    packet_ref, graph_revision_ref, edge_ref, target_port_ref
                ),
                FOREIGN KEY (activation_ref)
                    REFERENCES activations(activation_ref)
                    DEFERRABLE INITIALLY DEFERRED
            );

            CREATE TABLE IF NOT EXISTS activation_created_events (
                created_event_ref TEXT PRIMARY KEY,
                activation_ref TEXT NOT NULL UNIQUE,
                event_kind TEXT NOT NULL CHECK (event_kind = 'ActivationCreated'),
                FOREIGN KEY (activation_ref)
                    REFERENCES activations(activation_ref)
            );
            """
        )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Commit all writes together, or roll the entire transaction back."""

        if self.connection.in_transaction:
            raise RuntimeError("nested transactions are not supported")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> SQLiteStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
