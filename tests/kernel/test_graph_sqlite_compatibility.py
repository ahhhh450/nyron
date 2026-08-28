"""Regression coverage for Task 174 Graph/SQLite compatibility."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from nyron_kernel.definitions import ModuleDefinition, ModuleRegistry, PortDefinition
from nyron_kernel.graph import EdgeRequest, GraphRepository, ModuleInstanceRevision
from nyron_kernel.store import SQLiteStore


def _module(module_ref: str, *, input_policy: str | None = None) -> ModuleDefinition:
    inputs = ()
    outputs = (PortDefinition("out", {"type": "string"}),)
    if input_policy is not None:
        inputs = (
            PortDefinition("in", {"type": "string"}, "TRIGGER", input_policy),
        )
        outputs = ()
    return ModuleDefinition(
        module_ref=module_ref,
        version="1",
        input_port_definitions=inputs,
        output_port_definitions=outputs,
        config_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        effect_classes=("PURE",),
        required_capability_types=(),
        execution_contract={"kind": "execute"},
    )


def _instance(graph_ref: str, instance_ref: str, module_ref: str) -> ModuleInstanceRevision:
    return ModuleInstanceRevision(
        module_instance_revision_ref=f"revision:{graph_ref}:{instance_ref}",
        graph_revision_ref=graph_ref,
        module_instance_ref=instance_ref,
        module_ref=module_ref,
        module_version="1",
        config_ref=f"config:{instance_ref}",
        config_hash=f"hash:{instance_ref}",
        input_port_contract={},
        output_port_contract={},
        static_composite_path=("root",),
        static_accounting_scope_ref=f"accounting:{instance_ref}",
    )


class GraphSQLiteCompatibilityTest(unittest.TestCase):
    def test_pre_role_database_upgrade_preserves_rows_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "pre-171.sqlite3"
            legacy_instance = _instance("graph:legacy", "legacy", "legacy.module")
            legacy_contract = {
                "module_instance_revisions": [legacy_instance.as_dict()],
                "edges": [],
                "executable": True,
                "reason_code": None,
            }
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                CREATE TABLE graph_revisions (
                    graph_revision_ref TEXT PRIMARY KEY,
                    contract_json TEXT NOT NULL,
                    executable INTEGER NOT NULL,
                    reason_code TEXT
                );
                CREATE TABLE graph_edges (
                    graph_revision_ref TEXT NOT NULL,
                    edge_ref TEXT NOT NULL,
                    source_ref TEXT NOT NULL,
                    source_port_ref TEXT NOT NULL,
                    target_module_instance_revision_ref TEXT NOT NULL,
                    target_port_ref TEXT NOT NULL,
                    edge_ordinal INTEGER NOT NULL,
                    target_port_ordinal INTEGER NOT NULL,
                    PRIMARY KEY (graph_revision_ref, edge_ref)
                );
                """
            )
            connection.execute(
                "INSERT INTO graph_revisions VALUES (?, ?, 1, NULL)",
                ("graph:legacy", json.dumps(legacy_contract)),
            )
            connection.commit()
            connection.close()

            store = SQLiteStore(database)
            self.assertIn(
                "role",
                {
                    row["name"]
                    for row in store.connection.execute("PRAGMA table_info(graph_edges)")
                },
            )
            registry = ModuleRegistry(store)
            registry.register(_module("source.module"))
            registry.register(_module("sink.module", input_policy="MULTI_SOURCE"))
            graphs = GraphRepository(store, registry)
            self.assertEqual("graph:legacy", graphs.resolve("graph:legacy").graph_revision_ref)

            graph_ref = "graph:post-upgrade"
            published = graphs.publish(
                graph_ref,
                (
                    _instance(graph_ref, "a-source", "source.module"),
                    _instance(graph_ref, "b-sink", "sink.module"),
                ),
                (EdgeRequest("edge:new", "a-source", "out", "b-sink", "in"),),
            )
            self.assertEqual("NORMAL", published.edges[0].role)
            store.close()

            reopened = SQLiteStore(database)
            reopened_graphs = GraphRepository(reopened, ModuleRegistry(reopened))
            self.assertEqual(published, reopened_graphs.resolve(graph_ref))
            stored_sink = ModuleRegistry(reopened).resolve("sink.module", "1")
            self.assertEqual("TRIGGER", stored_sink.input_port_definitions[0].activation_mode)
            self.assertEqual(
                "MULTI_SOURCE",
                stored_sink.input_port_definitions[0].connection_policy,
            )
            reopened.close()


if __name__ == "__main__":
    unittest.main()
