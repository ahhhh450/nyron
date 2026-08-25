"""Acceptance tests for NYRON-T-20260825-027 Run authority foundation."""

from __future__ import annotations

import inspect
import sqlite3
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from nyron_kernel.execution import RunError, RunRepository
from nyron_kernel.store import SQLiteStore


GRAPH_REF = "graph:run-authority@1"
MODULE_REVISION_REF = "module-instance:run-authority@1"
EXECUTION_REF = "execution:run-authority/1"
ACTIVATION_REF = "activation:run-authority/1"
SECOND_ACTIVATION_REF = "activation:run-authority/2"
RUN_REF = "run:authority/1"


class RunAttemptAuthorityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.runs = RunRepository(self.store)
        self._seed_dependencies(self.store)

    def tearDown(self) -> None:
        self.store.close()

    @staticmethod
    def _seed_dependencies(store: SQLiteStore) -> None:
        with store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO graph_revisions(
                    graph_revision_ref, contract_json, executable, reason_code
                ) VALUES (?, '{}', 1, NULL)
                """,
                (GRAPH_REF,),
            )
            connection.execute(
                """
                INSERT INTO module_instance_revisions(
                    module_instance_revision_ref, graph_revision_ref,
                    module_instance_ref, module_ref, module_version,
                    config_ref, config_hash, input_port_contract_json,
                    output_port_contract_json, static_composite_path_json,
                    static_accounting_scope_ref
                ) VALUES (?, ?, 'run-authority', 'test.run', '1',
                          'config:run@1', 'sha256:run-config', '{}', '{}',
                          '["root"]', 'accounting:run')
                """,
                (MODULE_REVISION_REF, GRAPH_REF),
            )
            connection.execute(
                """
                INSERT INTO execution_admissions(
                    admission_ref, execution_ref, graph_revision_ref,
                    runtime_policy_ref, admitted_at_owner_order, state
                ) VALUES ('admission:run/1', ?, ?, 'policy:run@1', 1,
                          'ADMITTED')
                """,
                (EXECUTION_REF, GRAPH_REF),
            )
            connection.execute(
                """
                INSERT INTO workflow_executions(
                    execution_ref, graph_revision_ref, admission_ref,
                    runtime_policy_ref, state
                ) VALUES (?, ?, 'admission:run/1', 'policy:run@1',
                          'ADMITTED')
                """,
                (EXECUTION_REF, GRAPH_REF),
            )
            for index, activation_ref in enumerate(
                (ACTIVATION_REF, SECOND_ACTIVATION_REF), start=1
            ):
                connection.execute(
                    """
                    INSERT INTO activations(
                        activation_ref, execution_ref, graph_revision_ref,
                        module_instance_revision_ref, trigger_delivery_ref,
                        input_bindings_json, static_accounting_scope_ref,
                        created_event_ref
                    ) VALUES (?, ?, ?, ?, ?, '[]', 'accounting:run', ?)
                    """,
                    (
                        activation_ref,
                        EXECUTION_REF,
                        GRAPH_REF,
                        MODULE_REVISION_REF,
                        f"delivery:trigger:{index}",
                        f"event:activation:{index}",
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO activation_created_events(
                        created_event_ref, activation_ref, event_kind
                    ) VALUES (?, ?, 'ActivationCreated')
                    """,
                    (f"event:activation:{index}", activation_ref),
                )

    def _create(
        self,
        *,
        run_ref: str = RUN_REF,
        activation_ref: str = ACTIVATION_REF,
        execution_ref: str = EXECUTION_REF,
    ):
        return self.runs.create_initial(
            run_ref=run_ref,
            activation_ref=activation_ref,
            execution_ref=execution_ref,
        )

    def test_creation_establishes_exact_run_and_initial_current_attempt(self) -> None:
        run, attempt = self._create()

        self.assertEqual(RUN_REF, run.run_ref)
        self.assertEqual(ACTIVATION_REF, run.activation_ref)
        self.assertEqual(EXECUTION_REF, run.execution_ref)
        self.assertEqual(1, run.current_attempt_seq)
        self.assertEqual(1, run.fencing_generation)
        self.assertEqual("OPEN", run.state)
        self.assertEqual((RUN_REF, 1), (attempt.run_ref, attempt.attempt_seq))
        self.assertEqual("CREATED", attempt.state)
        self.assertTrue(attempt.fencing_token)

    def test_fencing_token_is_replay_stable_and_tied_to_authority_identity(
        self,
    ) -> None:
        first = self._create()
        replayed = self._create()
        other = self._create(
            run_ref="run:authority/2",
            activation_ref=SECOND_ACTIVATION_REF,
        )

        self.assertEqual(first, replayed)
        self.assertEqual(first[1].fencing_token, replayed[1].fencing_token)
        self.assertNotEqual(first[1].fencing_token, other[1].fencing_token)
        self.assertEqual(1, self._count("runs", "run_ref = ?", (RUN_REF,)))
        self.assertEqual(
            1,
            self._count("run_attempts", "run_ref = ?", (RUN_REF,)),
        )

    def test_nonexistent_activation_fails_with_zero_run_attempt_facts(self) -> None:
        with self.assertRaises(RunError) as raised:
            self._create(activation_ref="activation:missing")

        self.assertEqual("UNRESOLVED_ACTIVATION_REFERENCE", raised.exception.code)
        self.assertEqual(0, self._count("runs"))
        self.assertEqual(0, self._count("run_attempts"))

    def test_activation_execution_mismatch_fails_closed(self) -> None:
        with self.assertRaises(RunError) as raised:
            self._create(execution_ref="execution:other")

        self.assertEqual(
            "RUN_ACTIVATION_EXECUTION_MISMATCH", raised.exception.code
        )
        self.assertEqual(0, self._count("runs"))
        self.assertEqual(0, self._count("run_attempts"))

    def test_run_ref_conflict_cannot_rebind_identity(self) -> None:
        before = self._create()

        with self.assertRaises(RunError) as activation_conflict:
            self._create(activation_ref=SECOND_ACTIVATION_REF)
        self.assertEqual(
            "RUN_IDENTITY_CONFLICT", activation_conflict.exception.code
        )
        with self.assertRaises(RunError) as execution_conflict:
            self._create(execution_ref="execution:other")
        self.assertEqual(
            "RUN_IDENTITY_CONFLICT", execution_conflict.exception.code
        )
        self.assertEqual(before, self.runs.resolve(RUN_REF))
        self.assertEqual(1, self._count("runs"))
        self.assertEqual(1, self._count("run_attempts"))

    def test_second_run_for_same_activation_fails_durable_uniqueness(self) -> None:
        self._create()

        with self.assertRaises(RunError) as raised:
            self._create(run_ref="run:authority/other")
        self.assertEqual("ACTIVATION_RUN_CONFLICT", raised.exception.code)
        self.assertEqual(1, self._count("runs"))

        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO runs(
                        run_ref, activation_ref, execution_ref,
                        current_attempt_seq, fencing_generation, state
                    ) VALUES ('run:direct-conflict', ?, ?, 1, 1, 'OPEN')
                    """,
                    (ACTIVATION_REF, EXECUTION_REF),
                )

    def test_attempt_insert_failure_rolls_back_run_then_clean_retry_succeeds(
        self,
    ) -> None:
        self.store.connection.executescript(
            """
            CREATE TRIGGER inject_initial_attempt_failure
            BEFORE INSERT ON run_attempts
            BEGIN SELECT RAISE(ABORT, 'injected attempt failure'); END;
            """
        )

        with self.assertRaises(RunError) as raised:
            self._create()
        self.assertEqual("RUN_CREATION_CONFLICT", raised.exception.code)
        self.assertEqual(0, self._count("runs"))
        self.assertEqual(0, self._count("run_attempts"))

        self.store.connection.execute(
            "DROP TRIGGER inject_initial_attempt_failure"
        )
        created = self._create()
        self.assertEqual(created, self.runs.resolve(RUN_REF))
        self.assertEqual(1, self._count("runs"))
        self.assertEqual(1, self._count("run_attempts"))

    def test_current_authority_inconsistency_fails_closed(self) -> None:
        self._create()
        self.store.connection.execute(
            "UPDATE runs SET fencing_generation = 2 WHERE run_ref = ?",
            (RUN_REF,),
        )

        with self.assertRaises(RunError) as raised:
            self.runs.resolve(RUN_REF)

        self.assertEqual(
            "RUN_CURRENT_AUTHORITY_INCONSISTENT", raised.exception.code
        )

    def test_file_reopen_preserves_current_authority_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "nyron.db"
            with SQLiteStore(database) as initial_store:
                initial_runs = RunRepository(initial_store)
                self._seed_dependencies(initial_store)
                before = initial_runs.create_initial(
                    run_ref=RUN_REF,
                    activation_ref=ACTIVATION_REF,
                    execution_ref=EXECUTION_REF,
                )

            with SQLiteStore(database) as reopened_store:
                after = RunRepository(reopened_store).resolve(RUN_REF)

        self.assertEqual(before, after)

    def test_task_surface_cannot_create_attempt_two_or_terminal_state(self) -> None:
        run, attempt = self._create()

        self.assertNotIn(
            "attempt_seq", inspect.signature(self.runs.create_initial).parameters
        )
        self.assertEqual(1, self._count("run_attempts"))
        self.assertEqual(
            1,
            self.store.connection.execute(
                "SELECT MAX(attempt_seq) FROM run_attempts"
            ).fetchone()[0],
        )
        self.assertEqual("OPEN", run.state)
        self.assertEqual("CREATED", attempt.state)
        self.assertEqual(0, self._count("packets"))

    def test_authority_facts_are_immutable_values_and_scope_is_contained(self) -> None:
        run, attempt = self._create()
        with self.assertRaises(FrozenInstanceError):
            run.current_attempt_seq = 2  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            attempt.state = "ACTIVE"  # type: ignore[misc]

        source = inspect.getsource(RunRepository)
        for forbidden in (
            "TrustedModuleHost",
            "runtime_context",
            "AccountingScope",
            "Capability",
            "ResourceLease",
            "EffectOperation",
            "Recovery",
            "attempt_seq = 2",
            '"SUCCEEDED"',
            '"FAILED"',
            '"ACTIVE"',
        ):
            self.assertNotIn(forbidden, source)

    def _count(
        self,
        table: str,
        where: str = "",
        parameters: tuple[object, ...] = (),
    ) -> int:
        clause = f" WHERE {where}" if where else ""
        return self.store.connection.execute(
            f"SELECT COUNT(*) FROM {table}{clause}", parameters
        ).fetchone()[0]


if __name__ == "__main__":
    unittest.main()
