"""Acceptance tests for NYRON-T-20260825-013: trusted host + builtin.text.concat@1.

Maps 1:1 to the Task Validation checklist (10 items) plus fail-closed and
module-failure paths exercised by the frozen execute ABI (§11).
"""

from __future__ import annotations

import inspect
import unittest
from dataclasses import replace

from nyron_kernel.definitions import (
    ModuleDefinition,
    ModuleRegistry,
    PortDefinition,
)
from nyron_kernel.host import (
    Completed,
    Failed,
    TrustedHostError,
    TrustedModuleHost,
)
from nyron_kernel.host import trusted_host
from nyron_kernel.modules import builtin_text_concat
from nyron_kernel.store import SQLiteStore


def other_definition(
    module_ref: str = "example.noop",
    version: str = "1",
) -> ModuleDefinition:
    """A registered-but-not-hosted PURE definition for fail-closed tests."""
    return ModuleDefinition(
        module_ref=module_ref,
        version=version,
        input_port_definitions=(
            PortDefinition("x", {"type": "string"}, "TRIGGER"),
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
        metadata={},
    )


class TrustedHostBuiltinConcatTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.registry = ModuleRegistry(self.store)
        self.host = TrustedModuleHost(self.registry)

    def tearDown(self) -> None:
        self.store.close()

    # 1. Definition matches the frozen builtin.text.concat@1 contract exactly.
    def test_definition_matches_frozen_concat_contract(self) -> None:
        definition = builtin_text_concat.definition()

        self.assertEqual("builtin.text.concat", definition.module_ref)
        self.assertEqual("1", definition.version)
        self.assertEqual(
            "builtin.text.concat@1", builtin_text_concat.MODULE_REF_VERSION
        )
        self.assertEqual(
            (
                PortDefinition("a", {"type": "string"}, "REQUIRED_LATEST"),
                PortDefinition("b", {"type": "string"}, "TRIGGER"),
            ),
            definition.input_port_definitions,
        )
        self.assertEqual(
            (PortDefinition("text", {"type": "string"}),),
            definition.output_port_definitions,
        )
        self.assertEqual(
            {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            definition.config_schema,
        )
        self.assertEqual(("PURE",), definition.effect_classes)
        self.assertEqual((), definition.required_capability_types)
        self.assertEqual({"kind": "execute"}, definition.execution_contract)

    # 2. Builtin registers and resolves through the existing ModuleRegistry.
    def test_registers_and_resolves_through_registry(self) -> None:
        registered = self.registry.register(builtin_text_concat.definition())

        resolved = self.registry.resolve("builtin.text.concat", "1")

        self.assertEqual(registered, resolved)
        self.assertEqual(
            registered, self.registry.register(builtin_text_concat.definition())
        )

    # 3. Host invokes the exact pinned module_ref@version, not latest-by-name.
    def test_host_invokes_exact_pinned_ref_version(self) -> None:
        self.registry.register(builtin_text_concat.definition())
        self.registry.register(
            other_definition(module_ref="builtin.text.concat", version="2")
        )

        result = self.host.execute(
            "builtin.text.concat@1",
            {"a": "foo", "b": "bar"},
            {},
        )

        self.assertIsInstance(result, Completed)
        self.assertEqual({"text": "foobar"}, result.outputs)

        # A registered newer version of the same ref is NOT selected.
        with self.assertRaises(TrustedHostError) as newer:
            self.host.execute(
                "builtin.text.concat@2", {"x": "ignored"}, {}
            )
        self.assertEqual("UNSUPPORTED_MODULE_REFERENCE", newer.exception.code)

        # A name without an exact pinned version is refused (no latest-by-name).
        with self.assertRaises(TrustedHostError) as name_only:
            self.host.execute("builtin.text.concat", {"a": "foo", "b": "bar"}, {})
        self.assertEqual("INVALID_MODULE_REFERENCE", name_only.exception.code)

    # 4. Deterministic for identical inputs/config/runtime_context.
    #
    # NYRON-T-20260825-017 (F-001): this slice has no RuntimeContext shape
    # yet, so the only accepted runtime_context is None; determinism is
    # exercised at that one allowed value rather than an arbitrary dict.
    def test_execution_is_deterministic(self) -> None:
        self.registry.register(builtin_text_concat.definition())
        inputs = {"a": "abc", "b": "def"}
        config = {}
        runtime_context = None

        first = self.host.execute("builtin.text.concat@1", inputs, config, runtime_context)
        second = self.host.execute("builtin.text.concat@1", inputs, config, runtime_context)

        self.assertEqual(first, second)
        self.assertEqual(
            {"text": "abcdef"},
            self.host.execute(
                "builtin.text.concat@1", inputs, config, runtime_context
            ).outputs,
        )

    # 5. Output is exactly the expected text value.
    def test_output_is_exact_text_value(self) -> None:
        self.registry.register(builtin_text_concat.definition())

        cases = (
            ({"a": "", "b": ""}, {"text": ""}),
            ({"a": "hello ", "b": "world"}, {"text": "hello world"}),
            ({"a": "a", "b": "b"}, {"text": "ab"}),
        )
        for inputs, expected in cases:
            with self.subTest(inputs=inputs):
                result = self.host.execute("builtin.text.concat@1", inputs, {})
                self.assertEqual(expected, result.outputs)

    # 6. Unknown / unregistered module ref@version fails closed.
    def test_unknown_module_fails_closed(self) -> None:
        self.registry.register(builtin_text_concat.definition())

        with self.assertRaises(TrustedHostError) as missing:
            self.host.execute(
                "missing.module@9", {"a": "x", "b": "y"}, {}
            )
        self.assertEqual("UNRESOLVED_MODULE_REFERENCE", missing.exception.code)

        with self.assertRaises(TrustedHostError) as no_version:
            self.host.execute("builtin.text.concat", {"a": "x", "b": "y"}, {})
        self.assertEqual("INVALID_MODULE_REFERENCE", no_version.exception.code)

        with self.assertRaises(TrustedHostError) as malformed:
            self.host.execute("a@b@c", {"a": "x", "b": "y"}, {})
        self.assertEqual("INVALID_MODULE_REFERENCE", malformed.exception.code)

    # 6b. Registered module that this host does not host also fails closed.
    def test_registered_but_unsupported_module_fails_closed(self) -> None:
        self.registry.register(
            other_definition(module_ref="example.noop", version="1")
        )

        with self.assertRaises(TrustedHostError) as unsupported:
            self.host.execute("example.noop@1", {"x": "ignored"}, {})
        self.assertEqual("UNSUPPORTED_MODULE_REFERENCE", unsupported.exception.code)

    # F-002 (NYRON-T-20260825-017): resolving the right module_ref@version is
    # not sufficient — the registered ModuleDefinition must exactly match the
    # hosted implementation's own canonical contract before invocation.
    def test_canonical_registered_definition_still_executes(self) -> None:
        self.registry.register(builtin_text_concat.definition())

        result = self.host.execute("builtin.text.concat@1", {"a": "x", "b": "y"}, {})

        self.assertIsInstance(result, Completed)
        self.assertEqual({"text": "xy"}, result.outputs)

    def test_conflicting_valid_definition_fails_closed_without_invoking_implementation(
        self,
    ) -> None:
        conflicting = replace(
            builtin_text_concat.definition(),
            config_schema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": True,
            },
        )
        self.registry.register(conflicting)

        # Inputs deliberately omit 'a'/'b': the real implementation would
        # raise KeyError if ever invoked, which the host would surface as
        # Failed(...), not TrustedHostError. Getting TrustedHostError proves
        # the mismatch was caught strictly before invocation.
        with self.assertRaises(TrustedHostError) as raised:
            self.host.execute("builtin.text.concat@1", {}, {})
        self.assertEqual("DEFINITION_CONTRACT_MISMATCH", raised.exception.code)

    def test_definition_mismatch_is_detected_across_observable_contract_fields(
        self,
    ) -> None:
        canonical = builtin_text_concat.definition()
        conflicting_variants = {
            "input_port_definitions": (
                PortDefinition("a", {"type": "string"}, "TRIGGER"),
                PortDefinition("b", {"type": "string"}, "TRIGGER"),
            ),
            "output_port_definitions": (
                PortDefinition("different", {"type": "string"}),
            ),
            "config_schema": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": True,
            },
            "execution_contract": {"kind": "execute", "extra_hint": "nonstandard"},
            "metadata": {"display_name": "Different Name"},
        }
        for field_name, changed_value in conflicting_variants.items():
            with self.subTest(field=field_name):
                store = SQLiteStore()
                try:
                    registry = ModuleRegistry(store)
                    host = TrustedModuleHost(registry)
                    registry.register(
                        replace(canonical, **{field_name: changed_value})
                    )
                    with self.assertRaises(TrustedHostError) as raised:
                        host.execute(
                            "builtin.text.concat@1", {"a": "x", "b": "y"}, {}
                        )
                    self.assertEqual(
                        "DEFINITION_CONTRACT_MISMATCH", raised.exception.code
                    )
                finally:
                    store.close()

        # effect_classes / required_capability_types are coupled by the
        # frozen PURE-mismatch rule, so exercise them together as one
        # valid-but-different registration.
        store = SQLiteStore()
        try:
            registry = ModuleRegistry(store)
            host = TrustedModuleHost(registry)
            registry.register(
                replace(
                    canonical,
                    effect_classes=("WORKSPACE_READ",),
                    required_capability_types=("WORKSPACE_READ",),
                )
            )
            with self.assertRaises(TrustedHostError) as raised:
                host.execute("builtin.text.concat@1", {"a": "x", "b": "y"}, {})
            self.assertEqual("DEFINITION_CONTRACT_MISMATCH", raised.exception.code)
        finally:
            store.close()

    # 7. Module implementation receives no raw SQLiteStore / connection handle.
    def test_module_receives_no_raw_store_or_connection(self) -> None:
        parameters = inspect.signature(builtin_text_concat.execute).parameters
        self.assertEqual(
            ["inputs", "config", "runtime_context"], list(parameters)
        )

        source = inspect.getsource(builtin_text_concat).lower()
        for token in ("sqlite", "store", "connection"):
            self.assertNotIn(token, source)

    # F-001 (NYRON-T-20260825-017): this PURE-only slice has no RuntimeContext
    # shape yet, so runtime_context must be exactly None; any other value —
    # including a raw store, a raw DB connection, or an authority/handle-like
    # object — must fail closed before module code runs.
    def test_sqlite_store_as_runtime_context_fails_closed(self) -> None:
        self.registry.register(builtin_text_concat.definition())

        with self.assertRaises(TrustedHostError) as raised:
            self.host.execute(
                "builtin.text.concat@1", {"a": "x", "b": "y"}, {}, self.store
            )
        self.assertEqual("INVALID_RUNTIME_CONTEXT", raised.exception.code)

    def test_raw_sqlite_connection_as_runtime_context_fails_closed(self) -> None:
        self.registry.register(builtin_text_concat.definition())

        with self.assertRaises(TrustedHostError) as raised:
            self.host.execute(
                "builtin.text.concat@1",
                {"a": "x", "b": "y"},
                {},
                self.store.connection,
            )
        self.assertEqual("INVALID_RUNTIME_CONTEXT", raised.exception.code)

    def test_authority_handle_like_object_as_runtime_context_fails_closed(
        self,
    ) -> None:
        self.registry.register(builtin_text_concat.definition())

        class FakeCapabilityHandle:
            """Stands in for a Capability/Resource/authority handle object."""

            grant_ref = "grant:fake@1"

        with self.assertRaises(TrustedHostError) as raised:
            self.host.execute(
                "builtin.text.concat@1",
                {"a": "x", "b": "y"},
                {},
                FakeCapabilityHandle(),
            )
        self.assertEqual("INVALID_RUNTIME_CONTEXT", raised.exception.code)

    def test_none_runtime_context_executes(self) -> None:
        self.registry.register(builtin_text_concat.definition())

        result = self.host.execute(
            "builtin.text.concat@1", {"a": "x", "b": "y"}, {}, None
        )

        self.assertIsInstance(result, Completed)
        self.assertEqual({"text": "xy"}, result.outputs)

    # 8. PURE path uses no clock/random/env/filesystem/network/mutable globals.
    def test_pure_path_has_no_external_or_mutable_state(self) -> None:
        source = inspect.getsource(builtin_text_concat)
        for token in (
            "import os",
            "import random",
            "import time",
            "datetime",
            "socket",
            "urllib",
            "os.environ",
            "getenv",
            "open(",
            "subprocess",
            "pathlib",
        ):
            self.assertNotIn(token, source)

        for name, value in vars(builtin_text_concat).items():
            if name.startswith("__"):
                continue
            self.assertNotIsInstance(value, (dict, list, set), name)

    # 9. Host/builtin do not import or depend on Packet/Delivery/Activation/
    #    Run/Accounting/Effect machinery themselves.
    #
    # NYRON-T-20260825-017 (F-003): Packet / Delivery (`nyron_kernel.execution`)
    # is now integrated on current main, so asserting its global absence from
    # the whole repository is no longer valid. This is a Task-scoped leakage
    # check instead: the Host/builtin boundary itself must not import or
    # reference that package or its concepts, regardless of whether the
    # package exists elsewhere in the tree.
    def test_no_runtime_execution_machinery_introduced(self) -> None:
        for module in (builtin_text_concat, trusted_host):
            source = inspect.getsource(module)
            self.assertNotIn("nyron_kernel.execution", source)
            self.assertNotIn("import execution", source)

            lowered = source.lower()
            for token in (
                "packet",
                "delivery",
                "activation",
                "attempt",
                "accounting",
            ):
                self.assertNotIn(token, lowered, f"{module.__name__} contains {token}")

    # 10. Coexistence smoke check with accepted Segment A graph surface.
    def test_coexists_with_segment_a_graph_repository(self) -> None:
        from nyron_kernel.graph import GraphRepository, ModuleInstanceRevision

        self.registry.register(builtin_text_concat.definition())
        graphs = GraphRepository(self.store, self.registry)
        instance = ModuleInstanceRevision(
            module_instance_revision_ref="module-instance:text-concat@1",
            graph_revision_ref="graph:text-flow@1",
            module_instance_ref="text-concat",
            module_ref="builtin.text.concat",
            module_version="1",
            config_ref="config:text-concat@1",
            config_hash="sha256:config-1",
            input_port_contract={"a": "REQUIRED_LATEST", "b": "TRIGGER"},
            output_port_contract={"text": {"type": "string"}},
            static_composite_path=("root",),
            static_accounting_scope_ref="accounting:project/alpha",
        )

        published = graphs.publish("graph:text-flow@1", instance)

        self.assertTrue(published.executable)

        result = self.host.execute(
            "builtin.text.concat@1", {"a": "x", "b": "y"}, {}
        )
        self.assertEqual({"text": "xy"}, result.outputs)

    # Extra: non-string inputs surface as a Failed module result, not a crash.
    def test_non_string_inputs_surface_as_failed(self) -> None:
        self.registry.register(builtin_text_concat.definition())

        result = self.host.execute(
            "builtin.text.concat@1", {"a": 1, "b": 2}, {}
        )

        self.assertIsInstance(result, Failed)
        self.assertEqual("MODULE_EXECUTION_FAILED", result.reason_code)


if __name__ == "__main__":
    unittest.main()
