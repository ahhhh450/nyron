"""NYRON-T-20260828-175 — multi-instance ExecutionAdmissionGate.admit() coverage.

Closes NYRON-T-20260828-171-F-003 (reclassified BLOCKING by Task 172):
``ExecutionAdmissionGate.admit()`` must eagerly validate every
``ModuleInstanceRevision`` in a multi-instance ``GraphRevision`` -- not only
the first, via the ``graph.module_instance_revision`` backward-compatibility
accessor -- before any canonical ``WorkflowExecution``/admission fact is
created.
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from nyron_kernel.accounting import (
    AccountingScope,
    AccountingScopeResolver,
    compute_ancestry_hash,
)
from nyron_kernel.definitions import ModuleDefinition, ModuleRegistry, PortDefinition
from nyron_kernel.execution import AdmissionError, ExecutionAdmissionGate
from nyron_kernel.graph import GraphRepository, ModuleInstanceRevision
from nyron_kernel.store import SQLiteStore

GRAPH_REF = "graph:multi-admission@1"
POLICY_REF = "runtime-policy:pure@1"
ADMISSION_REF = "admission:multi/1"
EXECUTION_REF = "execution:multi/1"
ROOT_SCOPE_REF = "accounting:graph/multi-admission@1"


def module_definition(module_ref: str) -> ModuleDefinition:
    """No-input/one-output PURE module; no Edge is required to admit it."""

    return ModuleDefinition(
        module_ref=module_ref,
        version="1",
        input_port_definitions=(),
        output_port_definitions=(PortDefinition("out", {"type": "string"}),),
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


def instance(
    instance_ref: str,
    *,
    module_ref: str,
    module_version: str = "1",
    config_ref: str = "config:empty",
    config_hash: str = "sha256:empty",
) -> ModuleInstanceRevision:
    scope_ref = f"accounting:module/{instance_ref}@1"
    return ModuleInstanceRevision(
        module_instance_revision_ref=f"module-instance:{instance_ref}",
        graph_revision_ref=GRAPH_REF,
        module_instance_ref=instance_ref,
        module_ref=module_ref,
        module_version=module_version,
        config_ref=config_ref,
        config_hash=config_hash,
        input_port_contract={},
        output_port_contract={"out": {"type": "string"}},
        static_composite_path=("root",),
        static_accounting_scope_ref=scope_ref,
    )


def root_scope() -> AccountingScope:
    return AccountingScope(
        accounting_scope_ref=ROOT_SCOPE_REF,
        graph_revision_ref=GRAPH_REF,
        definition_anchor_ref=GRAPH_REF,
        parent_accounting_scope_ref=None,
        scope_kind="GRAPH",
        ancestry_hash=compute_ancestry_hash((ROOT_SCOPE_REF,)),
        created_from_definition_ref=GRAPH_REF,
        state="ACTIVE",
    )


def module_scope(instance_ref: str) -> AccountingScope:
    scope_ref = f"accounting:module/{instance_ref}@1"
    revision_ref = f"module-instance:{instance_ref}"
    return AccountingScope(
        accounting_scope_ref=scope_ref,
        graph_revision_ref=GRAPH_REF,
        definition_anchor_ref=revision_ref,
        parent_accounting_scope_ref=ROOT_SCOPE_REF,
        scope_kind="MODULE",
        ancestry_hash=compute_ancestry_hash((ROOT_SCOPE_REF, scope_ref)),
        created_from_definition_ref=revision_ref,
        state="ACTIVE",
    )


class ExecutionAdmissionMultiInstanceTest(unittest.TestCase):
    INSTANCE_REFS = ("a", "b", "c")

    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.registry = ModuleRegistry(self.store)
        self.graphs = GraphRepository(self.store, self.registry)
        self.accounting = AccountingScopeResolver(self.store)
        self.config_calls: list[tuple[str, str]] = []
        self.gate = self._gate()

    def tearDown(self) -> None:
        self.store.close()

    def _gate(self) -> ExecutionAdmissionGate:
        def resolve_config(config_ref: str, config_hash: str) -> bool:
            self.config_calls.append((config_ref, config_hash))
            return True

        def resolve_policy(runtime_policy_ref: str) -> bool:
            return runtime_policy_ref == POLICY_REF

        return ExecutionAdmissionGate(
            self.store,
            self.graphs,
            self.registry,
            self.accounting,
            resolve_config,
            resolve_policy,
        )

    def _instances(self) -> tuple[ModuleInstanceRevision, ...]:
        return tuple(
            instance(ref, module_ref=f"test.multi.{ref}")
            for ref in self.INSTANCE_REFS
        )

    def _register_all_modules(self) -> None:
        for ref in self.INSTANCE_REFS:
            self.registry.register(module_definition(f"test.multi.{ref}"))

    def _publish_graph(
        self, instances: tuple[ModuleInstanceRevision, ...] | None = None
    ) -> None:
        self.graphs.publish(GRAPH_REF, instances or self._instances())

    def _publish_all_accounting(self) -> None:
        self.accounting.publish(root_scope())
        for ref in self.INSTANCE_REFS:
            self.accounting.publish(module_scope(ref))

    def _prepare_success(self) -> None:
        self._register_all_modules()
        self._publish_graph()
        self._publish_all_accounting()

    def _admit(self) -> object:
        return self.gate.admit(
            admission_ref=ADMISSION_REF,
            execution_ref=EXECUTION_REF,
            graph_revision_ref=GRAPH_REF,
            runtime_policy_ref=POLICY_REF,
        )

    def assert_admission_error(self, code: str) -> None:
        with self.assertRaises(AdmissionError) as raised:
            self._admit()
        self.assertEqual(code, raised.exception.code)
        self.assertEqual(
            0,
            self.store.connection.execute(
                "SELECT COUNT(*) FROM execution_admissions"
            ).fetchone()[0],
        )
        self.assertEqual(
            0,
            self.store.connection.execute(
                "SELECT COUNT(*) FROM workflow_executions"
            ).fetchone()[0],
        )

    # 1. valid 3-instance Graph admission succeeds.
    def test_valid_three_instance_graph_admits_successfully(self) -> None:
        self._prepare_success()

        admission, execution = self._admit()  # type: ignore[misc]

        self.assertEqual(ADMISSION_REF, admission.admission_ref)
        self.assertEqual(EXECUTION_REF, execution.execution_ref)
        self.assertEqual(
            {(f"config:empty", f"sha256:empty")},
            set(self.config_calls),
        )
        self.assertEqual(3, len(self.config_calls))

    # 2. invalid/unresolved ModuleDefinition in instance 2 fails before
    #    WorkflowExecution admission persistence.
    def test_unresolved_module_in_second_instance_fails_closed(self) -> None:
        self.registry.register(module_definition("test.multi.a"))
        # "b" and "c" modules are deliberately never registered; the Graph
        # cache still publishes as non-executable in that case, so instead
        # register "b"/"c" then remove them from the registry post-publish
        # to reproduce a registry-state drift between publish and admission.
        self.registry.register(module_definition("test.multi.b"))
        self.registry.register(module_definition("test.multi.c"))
        self._publish_graph()
        self._publish_all_accounting()
        self.store.connection.execute(
            "DELETE FROM module_definitions WHERE module_ref = ? AND version = ?",
            ("test.multi.b", "1"),
        )

        self.assert_admission_error("UNRESOLVED_MODULE_REFERENCE")

    # 3. invalid config in instance 2/3 fails before admission persistence.
    def test_invalid_config_in_second_instance_fails_closed(self) -> None:
        self._register_all_modules()
        self._publish_graph()
        self._publish_all_accounting()

        # Only the first instance's config resolves; failure is
        # attributable to the second instance, not the first.
        calls: list[str] = []

        def resolve_config(config_ref: str, config_hash: str) -> bool:
            calls.append(config_ref)
            return len(calls) == 1

        self.gate = ExecutionAdmissionGate(
            self.store,
            self.graphs,
            self.registry,
            self.accounting,
            resolve_config,
            lambda ref: ref == POLICY_REF,
        )

        self.assert_admission_error("UNRESOLVED_CONFIG_REFERENCE")
        self.assertEqual(2, len(calls))

    def test_invalid_config_in_third_instance_fails_closed(self) -> None:
        self._register_all_modules()
        self._publish_graph()
        self._publish_all_accounting()

        calls: list[str] = []

        def resolve_config(config_ref: str, config_hash: str) -> bool:
            calls.append(config_ref)
            return len(calls) <= 2

        self.gate = ExecutionAdmissionGate(
            self.store,
            self.graphs,
            self.registry,
            self.accounting,
            resolve_config,
            lambda ref: ref == POLICY_REF,
        )

        self.assert_admission_error("UNRESOLVED_CONFIG_REFERENCE")
        self.assertEqual(3, len(calls))

    # 4. missing/invalid required accounting scope/reference in a later
    #    instance fails before admission persistence.
    def test_missing_accounting_scope_in_third_instance_fails_closed(self) -> None:
        self._register_all_modules()
        self._publish_graph()
        self.accounting.publish(root_scope())
        self.accounting.publish(module_scope("a"))
        self.accounting.publish(module_scope("b"))
        # "c" scope is never published.

        self.assert_admission_error("UNRESOLVED_ACCOUNTING_SCOPE_REFERENCE")

    def test_accounting_ancestry_invalid_in_second_instance_fails_closed(
        self,
    ) -> None:
        self._register_all_modules()
        self._publish_graph()
        self.accounting.publish(root_scope())
        self.accounting.publish(module_scope("a"))
        # "b" published without its parent scope link/ancestry being valid.
        self.accounting.publish(
            replace(module_scope("b"), parent_accounting_scope_ref=None)
        )
        self.accounting.publish(module_scope("c"))

        self.assert_admission_error("ACCOUNTING_SCOPE_ANCESTRY_INVALID")

    # 5. first-instance-invalid behavior remains fail closed.
    def test_first_instance_invalid_module_fails_closed(self) -> None:
        self.registry.register(module_definition("test.multi.a"))
        self.registry.register(module_definition("test.multi.b"))
        self.registry.register(module_definition("test.multi.c"))
        self._publish_graph()
        self._publish_all_accounting()
        self.store.connection.execute(
            "DELETE FROM module_definitions WHERE module_ref = ? AND version = ?",
            ("test.multi.a", "1"),
        )

        self.assert_admission_error("UNRESOLVED_MODULE_REFERENCE")

    # 6. single-instance accepted behavior remains compatible.
    def test_single_instance_graph_still_admits_successfully(self) -> None:
        self.registry.register(module_definition("test.multi.solo"))
        solo = instance("solo", module_ref="test.multi.solo")
        self.graphs.publish(GRAPH_REF, solo)
        self.accounting.publish(root_scope())
        self.accounting.publish(module_scope("solo"))

        admission, execution = self._admit()  # type: ignore[misc]

        self.assertEqual(ADMISSION_REF, admission.admission_ref)
        self.assertEqual(EXECUTION_REF, execution.execution_ref)

    # 7. admission replay/idempotency remains unchanged for multi-instance.
    def test_multi_instance_admission_is_idempotent(self) -> None:
        self._prepare_success()

        first = self._admit()
        second = self._admit()

        self.assertEqual(first, second)
        self.assertEqual(
            1,
            self.store.connection.execute(
                "SELECT COUNT(*) FROM execution_admissions"
            ).fetchone()[0],
        )


if __name__ == "__main__":
    unittest.main()
