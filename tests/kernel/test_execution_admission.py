"""Acceptance tests for NYRON-T-20260825-023 ExecutionAdmission."""

from __future__ import annotations

import inspect
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from nyron_kernel.accounting import (
    AccountingScope,
    AccountingScopeResolver,
    compute_ancestry_hash,
)
from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.execution import AdmissionError, ExecutionAdmissionGate
from nyron_kernel.graph import GraphRepository, ModuleInstanceRevision
from nyron_kernel.modules import builtin_text_concat
from nyron_kernel.store import SQLiteStore


GRAPH_REF = "graph:admission@1"
MODULE_INSTANCE_REF = "module-instance:text-concat@1"
ROOT_SCOPE_REF = "accounting:graph/admission@1"
MODULE_SCOPE_REF = "accounting:module/text-concat@1"
CONFIG_REF = "config:text-concat@1"
CONFIG_HASH = "sha256:config-1"
POLICY_REF = "runtime-policy:pure@1"
ADMISSION_REF = "admission:text-flow/1"
EXECUTION_REF = "execution:text-flow/1"


def module_instance(
    *,
    graph_revision_ref: str = GRAPH_REF,
    module_ref: str = "builtin.text.concat",
    module_version: str = "1",
    config_ref: str = CONFIG_REF,
    config_hash: str = CONFIG_HASH,
    accounting_scope_ref: str = MODULE_SCOPE_REF,
) -> ModuleInstanceRevision:
    return ModuleInstanceRevision(
        module_instance_revision_ref=MODULE_INSTANCE_REF,
        graph_revision_ref=graph_revision_ref,
        module_instance_ref="text-concat",
        module_ref=module_ref,
        module_version=module_version,
        config_ref=config_ref,
        config_hash=config_hash,
        input_port_contract={"a": "REQUIRED_LATEST", "b": "TRIGGER"},
        output_port_contract={"text": {"type": "string"}},
        static_composite_path=("root",),
        static_accounting_scope_ref=accounting_scope_ref,
    )


def root_scope(*, graph_revision_ref: str = GRAPH_REF) -> AccountingScope:
    return AccountingScope(
        accounting_scope_ref=ROOT_SCOPE_REF,
        graph_revision_ref=graph_revision_ref,
        definition_anchor_ref=graph_revision_ref,
        parent_accounting_scope_ref=None,
        scope_kind="GRAPH",
        ancestry_hash=compute_ancestry_hash((ROOT_SCOPE_REF,)),
        created_from_definition_ref=graph_revision_ref,
        state="ACTIVE",
    )


def module_scope(*, graph_revision_ref: str = GRAPH_REF) -> AccountingScope:
    return AccountingScope(
        accounting_scope_ref=MODULE_SCOPE_REF,
        graph_revision_ref=graph_revision_ref,
        definition_anchor_ref=MODULE_INSTANCE_REF,
        parent_accounting_scope_ref=ROOT_SCOPE_REF,
        scope_kind="MODULE",
        ancestry_hash=compute_ancestry_hash(
            (ROOT_SCOPE_REF, MODULE_SCOPE_REF)
        ),
        created_from_definition_ref=MODULE_INSTANCE_REF,
        state="ACTIVE",
    )


class ExecutionAdmissionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.registry = ModuleRegistry(self.store)
        self.graphs = GraphRepository(self.store, self.registry)
        self.accounting = AccountingScopeResolver(self.store)
        self.config_calls: list[tuple[str, str]] = []
        self.policy_calls: list[str] = []
        self.gate = self._gate()

    def tearDown(self) -> None:
        self.store.close()

    def _gate(
        self,
        *,
        config_allowed: bool = True,
        policy_allowed: bool = True,
    ) -> ExecutionAdmissionGate:
        def resolve_config(config_ref: str, config_hash: str) -> bool:
            self.config_calls.append((config_ref, config_hash))
            return (
                config_allowed
                and config_ref == CONFIG_REF
                and config_hash == CONFIG_HASH
            )

        def resolve_policy(runtime_policy_ref: str) -> bool:
            self.policy_calls.append(runtime_policy_ref)
            return policy_allowed and runtime_policy_ref == POLICY_REF

        return ExecutionAdmissionGate(
            self.store,
            self.graphs,
            self.registry,
            self.accounting,
            resolve_config,
            resolve_policy,
        )

    def _publish_graph(
        self, instance: ModuleInstanceRevision | None = None
    ) -> None:
        self.registry.register(builtin_text_concat.definition())
        self.graphs.publish(GRAPH_REF, instance or module_instance())

    def _publish_accounting(self) -> None:
        self.accounting.publish(root_scope())
        self.accounting.publish(module_scope())

    def _prepare_success(self) -> None:
        self._publish_graph()
        self._publish_accounting()

    def _admit(
        self,
        *,
        admission_ref: str = ADMISSION_REF,
        execution_ref: str = EXECUTION_REF,
        graph_revision_ref: str = GRAPH_REF,
        runtime_policy_ref: str = POLICY_REF,
    ) -> object:
        return self.gate.admit(
            admission_ref=admission_ref,
            execution_ref=execution_ref,
            graph_revision_ref=graph_revision_ref,
            runtime_policy_ref=runtime_policy_ref,
        )

    def assert_admission_error(
        self, code: str, action: Callable[[], object]
    ) -> None:
        with self.assertRaises(AdmissionError) as raised:
            action()
        self.assertEqual(code, raised.exception.code)
        self.assert_no_runtime_rows()

    def assert_no_runtime_rows(self) -> None:
        admission_count = self.store.connection.execute(
            "SELECT COUNT(*) FROM execution_admissions"
        ).fetchone()[0]
        execution_count = self.store.connection.execute(
            "SELECT COUNT(*) FROM workflow_executions"
        ).fetchone()[0]
        self.assertEqual(0, admission_count)
        self.assertEqual(0, execution_count)

    def test_success_creates_exact_admission_and_workflow_execution(self) -> None:
        self._prepare_success()

        admission, execution = self._admit()  # type: ignore[misc]

        self.assertEqual(ADMISSION_REF, admission.admission_ref)
        self.assertEqual(EXECUTION_REF, admission.execution_ref)
        self.assertEqual(GRAPH_REF, admission.graph_revision_ref)
        self.assertEqual(POLICY_REF, admission.runtime_policy_ref)
        self.assertEqual(1, admission.admitted_at_owner_order)
        self.assertEqual("ADMITTED", admission.state)
        self.assertEqual(EXECUTION_REF, execution.execution_ref)
        self.assertEqual(ADMISSION_REF, execution.admission_ref)
        self.assertEqual(GRAPH_REF, execution.graph_revision_ref)
        self.assertEqual(POLICY_REF, execution.runtime_policy_ref)
        self.assertEqual("ADMITTED", execution.state)
        self.assertEqual([(CONFIG_REF, CONFIG_HASH)], self.config_calls)
        self.assertEqual([POLICY_REF], self.policy_calls)

    def test_exact_module_version_remains_pinned_without_latest_lookup(self) -> None:
        self._publish_graph()
        self._publish_accounting()
        self.registry.register(replace(builtin_text_concat.definition(), version="2"))
        self.store.connection.execute(
            "DELETE FROM module_definitions WHERE module_ref = ? AND version = ?",
            ("builtin.text.concat", "1"),
        )

        self.assert_admission_error(
            "UNRESOLVED_MODULE_REFERENCE",
            self._admit,
        )

    def test_unresolved_graph_fails_before_canonical_creation(self) -> None:
        self.assert_admission_error("UNRESOLVED_GRAPH_REVISION", self._admit)

    def test_persisted_non_executable_graph_fails_closed(self) -> None:
        self.graphs.publish(
            GRAPH_REF,
            module_instance(module_ref="missing.module", module_version="7"),
        )

        self.assert_admission_error("GRAPH_REVISION_NOT_EXECUTABLE", self._admit)

    def test_config_denial_fails_before_canonical_creation(self) -> None:
        self._prepare_success()
        self.gate = self._gate(config_allowed=False)

        self.assert_admission_error("UNRESOLVED_CONFIG_REFERENCE", self._admit)

    def test_config_reference_and_hash_must_resolve_exactly(self) -> None:
        self._publish_graph(module_instance(config_hash="sha256:different"))
        self._publish_accounting()

        self.assert_admission_error("UNRESOLVED_CONFIG_REFERENCE", self._admit)

    def test_runtime_policy_denial_fails_before_canonical_creation(self) -> None:
        self._prepare_success()
        self.gate = self._gate(policy_allowed=False)

        self.assert_admission_error(
            "UNRESOLVED_RUNTIME_POLICY_REFERENCE", self._admit
        )

    def test_runtime_policy_reference_must_resolve_exactly(self) -> None:
        self._prepare_success()

        self.assert_admission_error(
            "UNRESOLVED_RUNTIME_POLICY_REFERENCE",
            lambda: self._admit(runtime_policy_ref="runtime-policy:other@1"),
        )

    def test_unresolved_accounting_scope_reason_is_preserved(self) -> None:
        self._publish_graph()

        self.assert_admission_error(
            "UNRESOLVED_ACCOUNTING_SCOPE_REFERENCE", self._admit
        )

    def test_accounting_binding_invalid_reason_is_preserved(self) -> None:
        self._publish_graph()
        wrong_graph = "graph:other@1"
        self.accounting.publish(root_scope(graph_revision_ref=wrong_graph))
        self.accounting.publish(module_scope(graph_revision_ref=wrong_graph))

        self.assert_admission_error("ACCOUNTING_SCOPE_BINDING_INVALID", self._admit)

    def test_accounting_ancestry_invalid_reason_is_preserved(self) -> None:
        self._publish_graph()
        self.accounting.publish(module_scope())

        self.assert_admission_error(
            "ACCOUNTING_SCOPE_ANCESTRY_INVALID", self._admit
        )

    def test_runtime_uses_accounting_owner_without_rederiving_ancestry(self) -> None:
        self._prepare_success()

        with patch.object(
            self.accounting,
            "resolve",
            wraps=self.accounting.resolve,
        ) as resolve:
            self._admit()

        resolve.assert_called_once_with(
            MODULE_SCOPE_REF,
            GRAPH_REF,
            MODULE_INSTANCE_REF,
        )
        source = inspect.getsource(ExecutionAdmissionGate)
        for forbidden in (
            "accounting_scopes",
            "compute_ancestry_hash",
            "parent_accounting_scope_ref",
            ".ancestry",
        ):
            self.assertNotIn(forbidden, source)

    def test_identical_admission_is_idempotent(self) -> None:
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
        self.assertEqual(
            1,
            self.store.connection.execute(
                "SELECT COUNT(*) FROM workflow_executions"
            ).fetchone()[0],
        )

    def test_conflicting_admission_identity_fails_closed(self) -> None:
        self._prepare_success()
        self._admit()

        with self.assertRaises(AdmissionError) as raised:
            self._admit(execution_ref="execution:conflict")

        self.assertEqual(
            "EXECUTION_ADMISSION_IDENTITY_CONFLICT", raised.exception.code
        )
        with self.assertRaises(AdmissionError) as execution_conflict:
            self._admit(admission_ref="admission:conflict")
        self.assertEqual(
            "EXECUTION_ADMISSION_IDENTITY_CONFLICT",
            execution_conflict.exception.code,
        )
        self.assertEqual(1, self._table_count("execution_admissions"))
        self.assertEqual(1, self._table_count("workflow_executions"))

    def test_mid_transaction_failure_rolls_back_both_rows(self) -> None:
        self._prepare_success()
        self.store.connection.executescript(
            """
            CREATE TRIGGER inject_workflow_failure
            BEFORE INSERT ON workflow_executions
            BEGIN
                SELECT RAISE(ABORT, 'injected workflow insert failure');
            END;
            """
        )

        self.assert_admission_error(
            "EXECUTION_ADMISSION_TRANSACTION_FAILED", self._admit
        )
        self.store.connection.execute("DROP TRIGGER inject_workflow_failure")
        admission, execution = self._admit()  # type: ignore[misc]
        self.assertEqual(ADMISSION_REF, admission.admission_ref)
        self.assertEqual(EXECUTION_REF, execution.execution_ref)

    def test_file_backed_reopen_preserves_both_runtime_facts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "nyron.db"
            with SQLiteStore(database) as initial_store:
                registry = ModuleRegistry(initial_store)
                graphs = GraphRepository(initial_store, registry)
                accounting = AccountingScopeResolver(initial_store)
                registry.register(builtin_text_concat.definition())
                graphs.publish(GRAPH_REF, module_instance())
                accounting.publish(root_scope())
                accounting.publish(module_scope())
                initial_gate = ExecutionAdmissionGate(
                    initial_store,
                    graphs,
                    registry,
                    accounting,
                    lambda ref, digest: (ref, digest) == (CONFIG_REF, CONFIG_HASH),
                    lambda ref: ref == POLICY_REF,
                )
                before = initial_gate.admit(
                    admission_ref=ADMISSION_REF,
                    execution_ref=EXECUTION_REF,
                    graph_revision_ref=GRAPH_REF,
                    runtime_policy_ref=POLICY_REF,
                )

            with SQLiteStore(database) as reopened_store:
                reopened_registry = ModuleRegistry(reopened_store)
                reopened_gate = ExecutionAdmissionGate(
                    reopened_store,
                    GraphRepository(reopened_store, reopened_registry),
                    reopened_registry,
                    AccountingScopeResolver(reopened_store),
                    lambda ref, digest: (ref, digest) == (CONFIG_REF, CONFIG_HASH),
                    lambda ref: ref == POLICY_REF,
                )
                after = (
                    reopened_gate.resolve_admission(ADMISSION_REF),
                    reopened_gate.resolve_execution(EXECUTION_REF),
                )

        self.assertEqual(before, after)

    def test_admission_creates_no_packet_or_later_execution_facts(self) -> None:
        self._prepare_success()
        self._admit()

        self.assertEqual(0, self._table_count("packets"))
        self.assertEqual(0, self._table_count("deliveries"))
        later_tables = self.store.connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table'
              AND name IN ('activations', 'runs', 'run_attempts')
            """
        ).fetchall()
        self.assertEqual([], later_tables)

    def _table_count(self, table: str) -> int:
        return self.store.connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]


if __name__ == "__main__":
    unittest.main()
