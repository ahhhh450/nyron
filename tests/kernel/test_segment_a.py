from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from nyron_kernel.definitions import (
    DefinitionError,
    ModuleDefinition,
    ModuleRegistry,
    PortDefinition,
)
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


def module_instance(
    *,
    graph_revision_ref: str = "graph:text-flow@1",
    module_instance_revision_ref: str = "module-instance:text-concat@1",
    module_ref: str = "builtin.text.concat",
    module_version: str = "1",
    static_accounting_scope_ref: str = "accounting:project/alpha",
) -> ModuleInstanceRevision:
    return ModuleInstanceRevision(
        module_instance_revision_ref=module_instance_revision_ref,
        graph_revision_ref=graph_revision_ref,
        module_instance_ref="text-concat",
        module_ref=module_ref,
        module_version=module_version,
        config_ref="config:text-concat@1",
        config_hash="sha256:config-1",
        input_port_contract={
            "a": "REQUIRED_LATEST",
            "b": "TRIGGER",
        },
        output_port_contract={"text": {"type": "string"}},
        static_composite_path=("root",),
        static_accounting_scope_ref=static_accounting_scope_ref,
    )


class SegmentATest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.registry = ModuleRegistry(self.store)
        self.graphs = GraphRepository(self.store, self.registry)

    def tearDown(self) -> None:
        self.store.close()

    def assert_definition_error(self, code: str, definition: ModuleDefinition) -> None:
        with self.assertRaises(DefinitionError) as raised:
            self.registry.register(definition)
        self.assertEqual(code, raised.exception.code)

    def test_registers_and_exactly_resolves_immutable_definition(self) -> None:
        original = concat_definition()
        registered = self.registry.register(original)
        original.config_schema["properties"]["later_mutation"] = {"type": "string"}

        resolved = self.registry.resolve("builtin.text.concat", "1")

        self.assertEqual(registered, resolved)
        self.assertNotIn("later_mutation", resolved.config_schema["properties"])
        self.assertEqual(registered, self.registry.register(registered))

    def test_definition_is_durable_across_store_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "nyron.db"
            with SQLiteStore(database) as first_store:
                ModuleRegistry(first_store).register(concat_definition())

            with SQLiteStore(database) as reopened_store:
                resolved = ModuleRegistry(reopened_store).resolve(
                    "builtin.text.concat", "1"
                )

        self.assertEqual(concat_definition(), resolved)

    def test_conflicting_contract_for_same_version_is_rejected(self) -> None:
        self.registry.register(concat_definition())

        self.assert_definition_error(
            "MODULE_VERSION_CONFLICT",
            concat_definition(
                output_port_definitions=(
                    PortDefinition("different", {"type": "string"}),
                )
            ),
        )

    def test_invalid_port_and_config_schemas_are_rejected(self) -> None:
        self.assert_definition_error(
            "PORT_SCHEMA_INVALID",
            concat_definition(
                input_port_definitions=(
                    PortDefinition("a", {"type": "unknown"}, "TRIGGER", "SINGLE_SOURCE"),
                )
            ),
        )
        self.assert_definition_error(
            "MODULE_CONTRACT_INVALID",
            concat_definition(config_schema={"type": "array"}),
        )

    def test_unknown_effect_and_capability_are_rejected(self) -> None:
        self.assert_definition_error(
            "UNKNOWN_EFFECT_CLASS",
            concat_definition(effect_classes=("UNKNOWN",)),
        )
        self.assert_definition_error(
            "UNKNOWN_CAPABILITY_TYPE",
            concat_definition(
                effect_classes=("MODEL_CALL",),
                required_capability_types=("UNKNOWN",),
            ),
        )

    def test_pure_definition_cannot_require_external_capability(self) -> None:
        self.assert_definition_error(
            "CAPABILITY_EFFECT_MISMATCH",
            concat_definition(required_capability_types=("NETWORK_ACCESS",)),
        )

    def test_effect_capability_mapping_must_be_complete(self) -> None:
        self.assert_definition_error(
            "CAPABILITY_EFFECT_MISMATCH",
            concat_definition(
                effect_classes=("WORKSPACE_WRITE",),
                required_capability_types=(),
            ),
        )

    def test_publish_resolved_graph_revision_succeeds(self) -> None:
        self.registry.register(concat_definition())

        published = self.graphs.publish("graph:text-flow@1", module_instance())

        self.assertTrue(published.executable)
        self.assertIsNone(published.reason_code)
        self.assertEqual(published, self.graphs.resolve("graph:text-flow@1"))

    def test_unresolved_module_reference_is_stored_non_executable(self) -> None:
        published = self.graphs.publish(
            "graph:text-flow@1",
            module_instance(module_ref="missing.module", module_version="7"),
        )

        self.assertFalse(published.executable)
        self.assertEqual("UNRESOLVED_MODULE_REFERENCE", published.reason_code)
        self.assertEqual(published, self.graphs.resolve("graph:text-flow@1"))

    def test_graph_revision_identity_cannot_be_republished_or_mutated(self) -> None:
        # NYRON-T-20260828-171: identical replay is now idempotent (required
        # for deterministic Product recompile); only conflicting content
        # under the same immutable revision identity fails closed.
        self.registry.register(concat_definition())
        first = self.graphs.publish("graph:text-flow@1", module_instance())

        identical_replay = self.graphs.publish(
            "graph:text-flow@1", module_instance()
        )
        self.assertEqual(first, identical_replay)

        with self.assertRaises(GraphError) as changed:
            self.graphs.publish(
                "graph:text-flow@1",
                module_instance(static_accounting_scope_ref="accounting:changed"),
            )
        self.assertEqual("GRAPH_REVISION_IMMUTABLE", changed.exception.code)

    def test_static_accounting_scope_reference_is_preserved_without_interpretation(self) -> None:
        self.registry.register(concat_definition())
        opaque_reference = "accounting://owner-defined/%2Fscope?revision=17#exact"

        self.graphs.publish(
            "graph:text-flow@1",
            module_instance(static_accounting_scope_ref=opaque_reference),
        )

        resolved = self.graphs.resolve("graph:text-flow@1")
        self.assertEqual(
            opaque_reference,
            resolved.module_instance_revision.static_accounting_scope_ref,
        )

    def test_injected_transaction_failure_rolls_back_registry_and_graph_rows(self) -> None:
        definition_json = json.dumps(concat_definition().as_dict(), sort_keys=True)
        instance = module_instance()

        with self.assertRaisesRegex(RuntimeError, "injected failure"):
            with self.store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO module_definitions(module_ref, version, contract_json)
                    VALUES (?, ?, ?)
                    """,
                    ("builtin.text.concat", "1", definition_json),
                )
                connection.execute(
                    """
                    INSERT INTO graph_revisions(
                        graph_revision_ref, contract_json, executable, reason_code
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        "graph:text-flow@1",
                        json.dumps(instance.as_dict(), sort_keys=True),
                        1,
                        None,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO module_instance_revisions(
                        module_instance_revision_ref,
                        graph_revision_ref,
                        module_instance_ref,
                        module_ref,
                        module_version,
                        config_ref,
                        config_hash,
                        input_port_contract_json,
                        output_port_contract_json,
                        static_composite_path_json,
                        static_accounting_scope_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        instance.module_instance_revision_ref,
                        instance.graph_revision_ref,
                        instance.module_instance_ref,
                        instance.module_ref,
                        instance.module_version,
                        instance.config_ref,
                        instance.config_hash,
                        json.dumps(instance.input_port_contract, sort_keys=True),
                        json.dumps(instance.output_port_contract, sort_keys=True),
                        json.dumps(instance.static_composite_path),
                        instance.static_accounting_scope_ref,
                    ),
                )
                raise RuntimeError("injected failure")

        self.assertIsNone(self.registry.resolve("builtin.text.concat", "1"))
        self.assertIsNone(self.graphs.resolve("graph:text-flow@1"))
        instance_count = self.store.connection.execute(
            "SELECT COUNT(*) FROM module_instance_revisions"
        ).fetchone()[0]
        self.assertEqual(0, instance_count)


if __name__ == "__main__":
    unittest.main()
