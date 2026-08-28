"""Runtime-owned immutable evidence for admitted workflow ingress."""

from __future__ import annotations

import sqlite3
from dataclasses import astuple, dataclass

from nyron_kernel.store import SQLiteStore


RUNTIME_TARGET_OWNER = "RUNTIME_ORCHESTRATION"
EXECUTION_INGRESS_EVENT_TYPE = "ExecutionIngressFact"


class ExecutionIngressError(RuntimeError):
    """Fail-closed execution-ingress recording error."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class ExecutionIngressFact:
    execution_ingress_ref: str
    ingress_route_revision_ref: str
    external_source_identity_ref: str
    external_event_ref: str
    canonical_payload_ref: str
    payload_hash: str
    authentication_evidence_ref: str
    validation_evidence_ref: str
    canonical_target_owner_ref: str
    canonical_event_type: str
    project_ref: str
    workspace_ref: str | None
    project_config_revision_ref: str
    workspace_config_revision_ref: str | None
    policy_context_revision_ref: str
    environment_binding_revision_ref: str | None
    graph_revision_ref: str
    graph_ingress_binding_ref: str
    caused_by_ref: str
    admitted_at_owner_order: int


class ExecutionIngressRepository:
    """Record and retrieve Runtime canonical ingress-admission evidence only."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def record(
        self,
        *,
        execution_ingress_ref: str,
        ingress_route_revision_ref: str,
        external_source_identity_ref: str,
        external_event_ref: str,
        canonical_payload_ref: str,
        payload_hash: str,
        authentication_evidence_ref: str,
        validation_evidence_ref: str,
        canonical_target_owner_ref: str,
        canonical_event_type: str,
        project_ref: str,
        workspace_ref: str | None,
        project_config_revision_ref: str,
        workspace_config_revision_ref: str | None,
        policy_context_revision_ref: str,
        environment_binding_revision_ref: str | None,
        graph_revision_ref: str,
        graph_ingress_binding_ref: str,
        caused_by_ref: str,
    ) -> ExecutionIngressFact:
        request = (
            execution_ingress_ref,
            ingress_route_revision_ref,
            external_source_identity_ref,
            external_event_ref,
            canonical_payload_ref,
            payload_hash,
            authentication_evidence_ref,
            validation_evidence_ref,
            canonical_target_owner_ref,
            canonical_event_type,
            project_ref,
            workspace_ref,
            project_config_revision_ref,
            workspace_config_revision_ref,
            policy_context_revision_ref,
            environment_binding_revision_ref,
            graph_revision_ref,
            graph_ingress_binding_ref,
            caused_by_ref,
        )
        self._validate(request)

        try:
            with self._store.transaction() as connection:
                existing = self._resolve_with(connection, execution_ingress_ref)
                if existing is not None:
                    if astuple(existing)[:-1] == request:
                        return existing
                    raise ExecutionIngressError(
                        "EXECUTION_INGRESS_IDENTITY_CONFLICT",
                        execution_ingress_ref=execution_ingress_ref,
                    )

                owner_order = connection.execute(
                    """
                    SELECT COALESCE(MAX(admitted_at_owner_order), 0) + 1
                    FROM execution_ingress_facts
                    """
                ).fetchone()[0]
                connection.execute(
                    """
                    INSERT INTO execution_ingress_facts VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (*request, owner_order),
                )
                fact = self._resolve_with(connection, execution_ingress_ref)
                if fact is None:  # pragma: no cover
                    raise ExecutionIngressError("EXECUTION_INGRESS_RECORD_FAILED")
                return fact
        except sqlite3.IntegrityError as error:
            raise ExecutionIngressError(
                "EXECUTION_INGRESS_IDENTITY_CONFLICT",
                execution_ingress_ref=execution_ingress_ref,
            ) from error

    def resolve(self, execution_ingress_ref: str) -> ExecutionIngressFact | None:
        return self._resolve_with(self._store.connection, execution_ingress_ref)

    @staticmethod
    def _validate(request: tuple[object, ...]) -> None:
        optional_indexes = {11, 13, 15}
        for index, value in enumerate(request):
            if index in optional_indexes and value is None:
                continue
            if not isinstance(value, str) or not value:
                raise ExecutionIngressError("EXECUTION_INGRESS_INVALID")
        if request[8] != RUNTIME_TARGET_OWNER or request[9] != EXECUTION_INGRESS_EVENT_TYPE:
            raise ExecutionIngressError("EXECUTION_INGRESS_TARGET_INVALID")
        if (request[11] is None) != (request[13] is None):
            raise ExecutionIngressError("EXECUTION_INGRESS_CONTEXT_INVALID")

    @staticmethod
    def _resolve_with(
        connection: sqlite3.Connection, execution_ingress_ref: str
    ) -> ExecutionIngressFact | None:
        row = connection.execute(
            """
            SELECT * FROM execution_ingress_facts
            WHERE execution_ingress_ref = ?
            """,
            (execution_ingress_ref,),
        ).fetchone()
        return ExecutionIngressFact(**dict(row)) if row is not None else None
