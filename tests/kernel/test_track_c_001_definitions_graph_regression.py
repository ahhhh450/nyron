"""Track C regression hardening for frozen definitions + graph invariants.

TRACK_C_TASK_001 (LOW risk, test-only). Locks in fail-closed validation and
immutability branches of the stable `definitions` and `graph` modules that are
not covered by `test_segment_a.py`. No production code is modified.
"""

from __future__ import annotations

import sqlite3
import unittest

from nyron_kernel.definitions import (
    DefinitionError,
    ModuleDefinition,
    ModuleRegistry,
    PortDefinition,
)
from nyron_kernel.definitions.schema import validate_json_schema, validate_ports
from nyron_kernel.graph import GraphError, GraphRepository, ModuleInstanceRevision
from nyron_kernel.store import SQLiteStore


def concat_definition(**changes: object) -> ModuleDefinition:
    values: dict[str, object] = {
        "module_ref": "builtin.text.concat",
        "version": "1",
        "input_port_definitions": (
            PortDefinition("a", {"type": "string"}, "REQUIRED_LATEST", "SINGLE_SOURCE"),
            PortDefinition("b", {"type": "string"}, "TRIGGER", "SINGLE_SOURCE"),
        ),
        "output_port_definitions": (
            PortDefinition("text", {"type": "string"}),
        ),
        "config_schema": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "effect_classes": ("PURE",),
        "required_capability_types": (),
        "execution_contract": {"kind": "execute"},
        "metadata": {"display_name": "Text Concatenate"},
    }
    values.update(changes)
    return ModuleDefinition(**values)  # type: ignore[arg-type]


def module_instance(**changes: object) -> ModuleInstanceRevision:
    values: dict[str, object] = {
        "module_instance_revision_ref": "module-instance:text-concat@1",
        "graph_revision_ref": "graph:text-flow@1",
        "module_instance_ref": "text-concat",
        "module_ref": "builtin.text.concat",
        "module_version": "1",
        "config_ref": "config:text-concat@1",
        "config_hash": "sha256:config-1",
        "input_port_contract": {"a": "REQUIRED_LATEST", "b": "TRIGGER"},
        "output_port_contract": {"text": {"type": "string"}},
        "static_composite_path": ("root",),
        "static_accounting_scope_ref": "accounting:project/alpha",
    }
    values.update(changes)
    return ModuleInstanceRevision(**values)  # type: ignore[arg-type]


class SchemaValidationTest(unittest.TestCase):
    def test_schema_type_must_be_a_known_object_type(self) -> None:
        with self.assertRaises(ValueError):
            validate_json_schema("not-a-dict")
        with self.assertRaises(ValueError):
            validate_json_schema({"type": "unknown"})
        with self.assertRaises(ValueError):
            validate_json_schema({"type": 3})

    def test_object_required_must_name_unique_existing_properties(self) -> None:
        with self.assertRaises(ValueError):
            validate_json_schema(
                {
                    "type": "object",
                    "properties": {"a": {"type": "string"}},
                    "required": ["a", "a"],
                }
            )
        with self.assertRaises(ValueError):
            validate_json_schema(
                {
                    "type": "object",
                    "properties": {"a": {"type": "string"}},
                    "required": ["missing"],
                }
            )
        with self.assertRaises(ValueError):
            validate_json_schema(
                {
                    "type": "object",
                    "properties": {"a": {"type": "string"}},
                    "required": [1],
                }
            )

    def test_object_properties_must_be_a_dict(self) -> None:
        with self.assertRaises(ValueError):
            validate_json_schema({"type": "object", "properties": "not-a-dict"})

    def test_additional_properties_must_be_boolean(self) -> None:
        with self.assertRaises(ValueError):
            validate_json_schema(
                {"type": "object", "properties": {}, "additionalProperties": "yes"}
            )

    def test_array_must_declare_items(self) -> None:
        with self.assertRaises(ValueError):
            validate_json_schema({"type": "array"})

    def test_nested_schema_recursion_is_validated(self) -> None:
        with self.assertRaises(ValueError):
            validate_json_schema(
                {"type": "object", "properties": {"a": {"type": "unknown"}}}
            )
        with self.assertRaises(ValueError):
            validate_json_schema({"type": "array", "items": {"type": "unknown"}})

    def test_valid_schemas_pass(self) -> None:
        validate_json_schema(
            {
                "type": "object",
                "properties": {"a": {"type": "string"}},
                "required": ["a"],
                "additionalProperties": False,
            }
        )
        validate_json_schema({"type": "array", "items": {"type": "integer"}})
        validate_json_schema({"type": "boolean"})


class PortValidationTest(unittest.TestCase):
    def test_port_names_must_be_non_empty_and_unique(self) -> None:
        with self.assertRaises(ValueError):
            validate_ports(
                (PortDefinition("", {"type": "string"}, "TRIGGER", "SINGLE_SOURCE"),), inputs=True
            )
        with self.assertRaises(ValueError):
            validate_ports(
                (
                    PortDefinition("a", {"type": "string"}, "TRIGGER", "SINGLE_SOURCE"),
                    PortDefinition("a", {"type": "string"}, "TRIGGER", "SINGLE_SOURCE"),
                ),
                inputs=True,
            )

    def test_input_port_must_declare_known_activation_mode(self) -> None:
        with self.assertRaises(ValueError):
            validate_ports(
                (PortDefinition("a", {"type": "string"}, "BOGUS", "SINGLE_SOURCE"),), inputs=True
            )

    def test_output_port_cannot_declare_activation_mode(self) -> None:
        with self.assertRaises(ValueError):
            validate_ports(
                (PortDefinition("a", {"type": "string"}, "TRIGGER"),), inputs=False
            )

    def test_input_port_must_declare_known_connection_policy(self) -> None:
        with self.assertRaises(ValueError):
            validate_ports(
                (PortDefinition("a", {"type": "string"}, "TRIGGER", "BOGUS"),),
                inputs=True,
            )


class ModuleRegistryContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.registry = ModuleRegistry(self.store)

    def tearDown(self) -> None:
        self.store.close()

    def test_empty_module_ref_or_version_is_rejected(self) -> None:
        for changes in ({"module_ref": ""}, {"version": ""}):
            with self.subTest(changes=changes), self.assertRaises(DefinitionError) as raised:
                self.registry.register(concat_definition(**changes))
            self.assertEqual("MODULE_CONTRACT_INVALID", raised.exception.code)

    def test_non_serializable_contract_is_rejected(self) -> None:
        with self.assertRaises(DefinitionError) as raised:
            self.registry.register(concat_definition(metadata={"bad": {1, 2}}))
        self.assertEqual("MODULE_CONTRACT_INVALID", raised.exception.code)


class GraphRepositoryIdentityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.registry = ModuleRegistry(self.store)
        self.registry.register(concat_definition())
        self.graphs = GraphRepository(self.store, self.registry)

    def tearDown(self) -> None:
        self.store.close()

    def assert_graph_error(
        self, code: str, graph_ref: str, instance: ModuleInstanceRevision
    ) -> None:
        with self.assertRaises(GraphError) as raised:
            self.graphs.publish(graph_ref, instance)
        self.assertEqual(code, raised.exception.code)

    def test_empty_graph_revision_ref_is_rejected(self) -> None:
        self.assert_graph_error("GRAPH_REVISION_INVALID", "", module_instance())

    def test_instance_graph_revision_ref_mismatch_is_rejected(self) -> None:
        self.assert_graph_error(
            "GRAPH_REVISION_INVALID",
            "graph:other@1",
            module_instance(graph_revision_ref="graph:text-flow@1"),
        )

    def test_empty_identity_fields_are_rejected(self) -> None:
        fields = (
            "module_instance_revision_ref",
            "module_ref",
            "module_version",
            "config_ref",
            "config_hash",
            "static_accounting_scope_ref",
        )
        for field in fields:
            with self.subTest(field=field):
                self.assert_graph_error(
                    "GRAPH_REVISION_INVALID",
                    "graph:text-flow@1",
                    module_instance(**{field: ""}),
                )

    def test_static_composite_path_must_be_non_empty_tuple_of_strings(self) -> None:
        self.assert_graph_error(
            "GRAPH_REVISION_INVALID",
            "graph:text-flow@1",
            module_instance(static_composite_path=["root"]),
        )
        self.assert_graph_error(
            "GRAPH_REVISION_INVALID",
            "graph:text-flow@1",
            module_instance(static_composite_path=("",)),
        )

    def test_port_contracts_must_be_dicts(self) -> None:
        self.assert_graph_error(
            "GRAPH_REVISION_INVALID",
            "graph:text-flow@1",
            module_instance(input_port_contract="not-a-dict"),
        )
        self.assert_graph_error(
            "GRAPH_REVISION_INVALID",
            "graph:text-flow@1",
            module_instance(output_port_contract="not-a-dict"),
        )


class GraphSchemaIntegrityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.registry = ModuleRegistry(self.store)
        self.registry.register(concat_definition())
        self.graphs = GraphRepository(self.store, self.registry)
        self.graphs.publish("graph:text-flow@1", module_instance())

    def tearDown(self) -> None:
        self.store.close()

    def test_executable_check_rejects_out_of_domain(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "UPDATE graph_revisions SET executable = 2 WHERE graph_revision_ref = ?",
                ("graph:text-flow@1",),
            )

    def test_duplicate_module_instance_per_graph_is_rejected(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                """
                INSERT INTO module_instance_revisions (
                    module_instance_revision_ref, graph_revision_ref,
                    module_instance_ref, module_ref, module_version,
                    config_ref, config_hash, input_port_contract_json,
                    output_port_contract_json, static_composite_path_json,
                    static_accounting_scope_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "module-instance:dup@1",
                    "graph:text-flow@1",
                    "text-concat",
                    "builtin.text.concat",
                    "1",
                    "config:text-concat@1",
                    "sha256:config-1",
                    "{}",
                    "{}",
                    '["root"]',
                    "accounting:project/alpha",
                ),
            )

    def test_orphan_instance_reference_is_rejected(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                """
                INSERT INTO module_instance_revisions (
                    module_instance_revision_ref, graph_revision_ref,
                    module_instance_ref, module_ref, module_version,
                    config_ref, config_hash, input_port_contract_json,
                    output_port_contract_json, static_composite_path_json,
                    static_accounting_scope_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "module-instance:orphan@1",
                    "graph:missing@1",
                    "text-concat",
                    "builtin.text.concat",
                    "1",
                    "config:text-concat@1",
                    "sha256:config-1",
                    "{}",
                    "{}",
                    '["root"]',
                    "accounting:project/alpha",
                ),
            )


if __name__ == "__main__":
    unittest.main()
