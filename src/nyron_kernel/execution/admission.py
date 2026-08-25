"""Minimal Runtime-owned WorkflowExecution admission boundary."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

from nyron_kernel.accounting import AccountingScopeError, AccountingScopeResolver
from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.graph import GraphRepository
from nyron_kernel.store import SQLiteStore


class AdmissionError(RuntimeError):
    """Fail-closed Runtime admission error with a stable reason code."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class ExecutionAdmission:
    admission_ref: str
    execution_ref: str
    graph_revision_ref: str
    runtime_policy_ref: str
    admitted_at_owner_order: int
    state: str


@dataclass(frozen=True)
class WorkflowExecution:
    execution_ref: str
    graph_revision_ref: str
    admission_ref: str
    runtime_policy_ref: str
    state: str


class ExecutionAdmissionGate:
    """Validate exact foreign-owner evidence, then atomically admit execution."""

    def __init__(
        self,
        store: SQLiteStore,
        graphs: GraphRepository,
        registry: ModuleRegistry,
        accounting: AccountingScopeResolver,
        config_resolver: Callable[[str, str], bool],
        runtime_policy_resolver: Callable[[str], bool],
    ) -> None:
        self._store = store
        self._graphs = graphs
        self._registry = registry
        self._accounting = accounting
        self._config_resolver = config_resolver
        self._runtime_policy_resolver = runtime_policy_resolver

    def admit(
        self,
        *,
        admission_ref: str,
        execution_ref: str,
        graph_revision_ref: str,
        runtime_policy_ref: str,
    ) -> tuple[ExecutionAdmission, WorkflowExecution]:
        """Create both Runtime facts only after every exact check succeeds."""

        values = (
            admission_ref,
            execution_ref,
            graph_revision_ref,
            runtime_policy_ref,
        )
        if any(not isinstance(value, str) or not value for value in values):
            raise AdmissionError("EXECUTION_ADMISSION_INVALID")

        graph = self._graphs.resolve(graph_revision_ref)
        if graph is None:
            raise AdmissionError(
                "UNRESOLVED_GRAPH_REVISION",
                graph_revision_ref=graph_revision_ref,
            )
        if not graph.executable:
            raise AdmissionError(
                "GRAPH_REVISION_NOT_EXECUTABLE",
                graph_revision_ref=graph_revision_ref,
                graph_reason_code=graph.reason_code,
            )

        instance = graph.module_instance_revision
        if self._registry.resolve(instance.module_ref, instance.module_version) is None:
            raise AdmissionError(
                "UNRESOLVED_MODULE_REFERENCE",
                module_ref=instance.module_ref,
                module_version=instance.module_version,
            )
        if not self._resolve_config(instance.config_ref, instance.config_hash):
            raise AdmissionError(
                "UNRESOLVED_CONFIG_REFERENCE",
                config_ref=instance.config_ref,
                config_hash=instance.config_hash,
            )
        if not self._resolve_runtime_policy(runtime_policy_ref):
            raise AdmissionError(
                "UNRESOLVED_RUNTIME_POLICY_REFERENCE",
                runtime_policy_ref=runtime_policy_ref,
            )

        try:
            self._accounting.resolve(
                instance.static_accounting_scope_ref,
                graph.graph_revision_ref,
                instance.module_instance_revision_ref,
            )
        except AccountingScopeError as error:
            raise AdmissionError(error.code, **error.context) from error

        try:
            with self._store.transaction() as connection:
                existing_admission = self._resolve_admission_with(
                    connection, admission_ref
                )
                existing_execution = self._resolve_execution_with(
                    connection, execution_ref
                )
                if existing_admission is not None or existing_execution is not None:
                    if self._is_identical_request(
                        existing_admission,
                        existing_execution,
                        admission_ref,
                        execution_ref,
                        graph_revision_ref,
                        runtime_policy_ref,
                    ):
                        return existing_admission, existing_execution
                    raise AdmissionError(
                        "EXECUTION_ADMISSION_IDENTITY_CONFLICT",
                        admission_ref=admission_ref,
                        execution_ref=execution_ref,
                    )

                owner_order = connection.execute(
                    """
                    SELECT COALESCE(MAX(admitted_at_owner_order), 0) + 1
                    FROM execution_admissions
                    """
                ).fetchone()[0]
                connection.execute(
                    """
                    INSERT INTO execution_admissions(
                        admission_ref, execution_ref, graph_revision_ref,
                        runtime_policy_ref, admitted_at_owner_order, state
                    ) VALUES (?, ?, ?, ?, ?, 'ADMITTED')
                    """,
                    (
                        admission_ref,
                        execution_ref,
                        graph_revision_ref,
                        runtime_policy_ref,
                        owner_order,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO workflow_executions(
                        execution_ref, graph_revision_ref, admission_ref,
                        runtime_policy_ref, state
                    ) VALUES (?, ?, ?, ?, 'ADMITTED')
                    """,
                    (
                        execution_ref,
                        graph_revision_ref,
                        admission_ref,
                        runtime_policy_ref,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise AdmissionError(
                "EXECUTION_ADMISSION_TRANSACTION_FAILED",
                admission_ref=admission_ref,
                execution_ref=execution_ref,
            ) from error

        admission = self.resolve_admission(admission_ref)
        execution = self.resolve_execution(execution_ref)
        if admission is None or execution is None:  # pragma: no cover
            raise AdmissionError("EXECUTION_ADMISSION_TRANSACTION_FAILED")
        return admission, execution

    def resolve_admission(self, admission_ref: str) -> ExecutionAdmission | None:
        return self._resolve_admission_with(self._store.connection, admission_ref)

    def resolve_execution(self, execution_ref: str) -> WorkflowExecution | None:
        return self._resolve_execution_with(self._store.connection, execution_ref)

    def _resolve_config(self, config_ref: str, config_hash: str) -> bool:
        try:
            return self._config_resolver(config_ref, config_hash) is True
        except Exception as error:  # noqa: BLE001 - foreign resolver denies closed
            raise AdmissionError(
                "UNRESOLVED_CONFIG_REFERENCE",
                config_ref=config_ref,
                config_hash=config_hash,
            ) from error

    def _resolve_runtime_policy(self, runtime_policy_ref: str) -> bool:
        try:
            return self._runtime_policy_resolver(runtime_policy_ref) is True
        except Exception as error:  # noqa: BLE001 - foreign resolver denies closed
            raise AdmissionError(
                "UNRESOLVED_RUNTIME_POLICY_REFERENCE",
                runtime_policy_ref=runtime_policy_ref,
            ) from error

    @staticmethod
    def _resolve_admission_with(
        connection: sqlite3.Connection, admission_ref: str
    ) -> ExecutionAdmission | None:
        row = connection.execute(
            """
            SELECT admission_ref, execution_ref, graph_revision_ref,
                   runtime_policy_ref, admitted_at_owner_order, state
            FROM execution_admissions WHERE admission_ref = ?
            """,
            (admission_ref,),
        ).fetchone()
        return ExecutionAdmission(**dict(row)) if row is not None else None

    @staticmethod
    def _resolve_execution_with(
        connection: sqlite3.Connection, execution_ref: str
    ) -> WorkflowExecution | None:
        row = connection.execute(
            """
            SELECT execution_ref, graph_revision_ref, admission_ref,
                   runtime_policy_ref, state
            FROM workflow_executions WHERE execution_ref = ?
            """,
            (execution_ref,),
        ).fetchone()
        return WorkflowExecution(**dict(row)) if row is not None else None

    @staticmethod
    def _is_identical_request(
        admission: ExecutionAdmission | None,
        execution: WorkflowExecution | None,
        admission_ref: str,
        execution_ref: str,
        graph_revision_ref: str,
        runtime_policy_ref: str,
    ) -> bool:
        return (
            admission is not None
            and execution is not None
            and admission.admission_ref == admission_ref
            and admission.execution_ref == execution_ref
            and admission.graph_revision_ref == graph_revision_ref
            and admission.runtime_policy_ref == runtime_policy_ref
            and admission.state == "ADMITTED"
            and execution.execution_ref == execution_ref
            and execution.admission_ref == admission_ref
            and execution.graph_revision_ref == graph_revision_ref
            and execution.runtime_policy_ref == runtime_policy_ref
            and execution.state == "ADMITTED"
        )
