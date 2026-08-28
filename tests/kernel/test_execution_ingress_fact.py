"""Focused acceptance tests for Runtime ExecutionIngressFact foundation."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from nyron_kernel.execution import (
    EXECUTION_INGRESS_EVENT_TYPE,
    RUNTIME_TARGET_OWNER,
    ExecutionIngressError,
    ExecutionIngressRepository,
)
from nyron_kernel.store import SQLiteStore


FACT_REF = "execution-ingress:provider/event-1"


class ExecutionIngressFactTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.store.connection.execute(
            "INSERT INTO graph_revisions VALUES (?, '{}', 1, NULL)",
            ("graph:workflow@7",),
        )
        self.repository = ExecutionIngressRepository(self.store)

    def tearDown(self) -> None:
        self.store.close()

    @staticmethod
    def request(**changes: object) -> dict[str, object]:
        values: dict[str, object] = {
            "execution_ingress_ref": FACT_REF,
            "ingress_route_revision_ref": "ingress-route:provider@3",
            "external_source_identity_ref": "provider:account-4",
            "external_event_ref": "provider-event:evt-1",
            "canonical_payload_ref": "value:payload/1",
            "payload_hash": "sha256:payload-1",
            "authentication_evidence_ref": "evidence:auth/1",
            "validation_evidence_ref": "evidence:validation/1",
            "canonical_target_owner_ref": RUNTIME_TARGET_OWNER,
            "canonical_event_type": EXECUTION_INGRESS_EVENT_TYPE,
            "project_ref": "project:alpha",
            "workspace_ref": "workspace:alpha/main",
            "project_config_revision_ref": "project-config:alpha@2",
            "workspace_config_revision_ref": "workspace-config:alpha/main@5",
            "policy_context_revision_ref": "policy-context:alpha@9",
            "environment_binding_revision_ref": "environment:alpha/prod@4",
            "graph_revision_ref": "graph:workflow@7",
            "graph_ingress_binding_ref": "graph-ingress:workflow/start@7",
            "caused_by_ref": "external-receipt:evt-1",
        }
        values.update(changes)
        return values

    def test_records_exact_route_target_and_context_binding(self) -> None:
        fact = self.repository.record(**self.request())  # type: ignore[arg-type]

        self.assertEqual(FACT_REF, fact.execution_ingress_ref)
        self.assertEqual("ingress-route:provider@3", fact.ingress_route_revision_ref)
        self.assertEqual(RUNTIME_TARGET_OWNER, fact.canonical_target_owner_ref)
        self.assertEqual("project-config:alpha@2", fact.project_config_revision_ref)
        self.assertEqual("workspace-config:alpha/main@5", fact.workspace_config_revision_ref)
        self.assertEqual("policy-context:alpha@9", fact.policy_context_revision_ref)
        self.assertEqual("environment:alpha/prod@4", fact.environment_binding_revision_ref)
        self.assertEqual("graph:workflow@7", fact.graph_revision_ref)
        self.assertEqual("graph-ingress:workflow/start@7", fact.graph_ingress_binding_ref)
        self.assertEqual(1, fact.admitted_at_owner_order)

    def test_identical_replay_is_idempotent_and_identity_is_stable(self) -> None:
        first = self.repository.record(**self.request())  # type: ignore[arg-type]
        second = self.repository.record(**self.request())  # type: ignore[arg-type]

        self.assertEqual(first, second)
        self.assertEqual(1, self._count("execution_ingress_facts"))

    def test_conflicting_identity_reuse_fails_closed(self) -> None:
        self.repository.record(**self.request())  # type: ignore[arg-type]

        with self.assertRaises(ExecutionIngressError) as raised:
            self.repository.record(  # type: ignore[arg-type]
                **self.request(payload_hash="sha256:conflict")
            )
        self.assertEqual("EXECUTION_INGRESS_IDENTITY_CONFLICT", raised.exception.code)
        self.assertEqual(1, self._count("execution_ingress_facts"))

    def test_same_external_identity_cannot_be_recorded_under_second_fact(self) -> None:
        self.repository.record(**self.request())  # type: ignore[arg-type]

        with self.assertRaises(ExecutionIngressError) as raised:
            self.repository.record(  # type: ignore[arg-type]
                **self.request(execution_ingress_ref="execution-ingress:duplicate")
            )
        self.assertEqual("EXECUTION_INGRESS_IDENTITY_CONFLICT", raised.exception.code)

    def test_fact_is_immutable_even_through_raw_store_access(self) -> None:
        self.repository.record(**self.request())  # type: ignore[arg-type]

        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "UPDATE execution_ingress_facts SET payload_hash = 'changed'"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute("DELETE FROM execution_ingress_facts")

    def test_only_runtime_execution_ingress_target_is_accepted(self) -> None:
        for change in (
            {"canonical_target_owner_ref": "HUMAN_INTERACTION"},
            {"canonical_event_type": "HumanResponse"},
        ):
            with self.assertRaises(ExecutionIngressError) as raised:
                self.repository.record(**self.request(**change))  # type: ignore[arg-type]
            self.assertEqual("EXECUTION_INGRESS_TARGET_INVALID", raised.exception.code)
        self.assertEqual(0, self._count("execution_ingress_facts"))

    def test_workspace_identity_and_revision_are_both_present_or_absent(self) -> None:
        with self.assertRaises(ExecutionIngressError) as raised:
            self.repository.record(  # type: ignore[arg-type]
                **self.request(workspace_config_revision_ref=None)
            )
        self.assertEqual("EXECUTION_INGRESS_CONTEXT_INVALID", raised.exception.code)

        fact = self.repository.record(  # type: ignore[arg-type]
            **self.request(workspace_ref=None, workspace_config_revision_ref=None)
        )
        self.assertIsNone(fact.workspace_ref)
        self.assertIsNone(fact.workspace_config_revision_ref)

    def test_restart_preserves_fact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "nyron.db"
            with SQLiteStore(database) as initial:
                initial.connection.execute(
                    "INSERT INTO graph_revisions VALUES (?, '{}', 1, NULL)",
                    ("graph:workflow@7",),
                )
                expected = ExecutionIngressRepository(initial).record(  # type: ignore[arg-type]
                    **self.request()
                )
            with SQLiteStore(database) as reopened:
                actual = ExecutionIngressRepository(reopened).resolve(FACT_REF)
        self.assertEqual(expected, actual)

    def test_recording_creates_no_activation_or_foreign_owner_fact(self) -> None:
        self.repository.record(**self.request())  # type: ignore[arg-type]

        for table in (
            "execution_admissions",
            "workflow_executions",
            "packets",
            "deliveries",
            "accounting_scopes",
        ):
            self.assertEqual(0, self._count(table))
        later_runtime_tables = self.store.connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name IN ('activations', 'runs', 'run_attempts')
            """
        ).fetchall()
        self.assertEqual([], later_runtime_tables)

    def _count(self, table: str) -> int:
        return self.store.connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]


if __name__ == "__main__":
    unittest.main()
