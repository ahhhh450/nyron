"""Minimal SQLite state store for immutable definitions and graph revisions."""

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
