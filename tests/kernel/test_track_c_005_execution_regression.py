"""Track C Task 005 — frozen Run-authority fail-closed regression coverage.

This module only asserts the *existing* frozen behavior of
``RunRepository`` / ``RuntimeAuthorityResolver``.  It adds tests, never
reinterprets fencing / replacement semantics, and modifies no production
code.  Every test uses an in-memory ``SQLiteStore()``.
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from nyron_kernel.execution import (
    RuntimeAuthorityResolver,
    RunError,
    RunRepository,
)
from nyron_kernel.store import SQLiteStore


GRAPH_REF = "graph:track-c-005@1"
MODULE_REVISION_REF = "module-instance:track-c-005@1"
EXECUTION_REF = "execution:track-c-005/1"
ACTIVATION_REF = "activation:track-c-005/1"
RUN_REF = "run:track-c-005/1"


class TrackC005ExecutionRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.runs = RunRepository(self.store)
        self.resolver = RuntimeAuthorityResolver(self.store)

    def tearDown(self) -> None:
        self.store.close()

    def _seed(
        self,
        *,
        workflow_state: str = "ADMITTED",
        include_workflow: bool = True,
    ) -> None:
        with self.store.transaction() as connection:
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
                ) VALUES (?, ?, 'track-c-005', 'test.track-c-005', '1',
                          'config:track-c-005@1', 'sha256:track-c-005', '{}',
                          '{}', '["root"]', 'accounting:track-c-005')
                """,
                (MODULE_REVISION_REF, GRAPH_REF),
            )
            if include_workflow:
                connection.execute(
                    """
                    INSERT INTO execution_admissions(
                        admission_ref, execution_ref, graph_revision_ref,
                        runtime_policy_ref, admitted_at_owner_order, state
                    ) VALUES ('admission:track-c-005/1', ?, ?,
                              'policy:track-c-005@1', 1, 'ADMITTED')
                    """,
                    (EXECUTION_REF, GRAPH_REF),
                )
                connection.execute(
                    """
                    INSERT INTO workflow_executions(
                        execution_ref, graph_revision_ref, admission_ref,
                        runtime_policy_ref, state
                    ) VALUES (?, ?, 'admission:track-c-005/1',
                              'policy:track-c-005@1', ?)
                    """,
                    (EXECUTION_REF, GRAPH_REF, workflow_state),
                )
            connection.execute(
                """
                INSERT INTO activations(
                    activation_ref, execution_ref, graph_revision_ref,
                    module_instance_revision_ref, trigger_delivery_ref,
                    input_bindings_json, static_accounting_scope_ref,
                    created_event_ref
                ) VALUES (?, ?, ?, ?, 'delivery:track-c-005-trigger', '[]',
                          'accounting:track-c-005',
                          'event:activation:track-c-005/1')
                """,
                (ACTIVATION_REF, EXECUTION_REF, GRAPH_REF, MODULE_REVISION_REF),
            )
            connection.execute(
                """
                INSERT INTO activation_created_events(
                    created_event_ref, activation_ref, event_kind
                ) VALUES ('event:activation:track-c-005/1', ?, 'ActivationCreated')
                """,
                (ACTIVATION_REF,),
            )

    def _create_run(self):
        return self.runs.create_initial(
            run_ref=RUN_REF,
            activation_ref=ACTIVATION_REF,
            execution_ref=EXECUTION_REF,
        )

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

    def test_create_initial_rejects_empty_and_non_string_refs(self) -> None:
        for field in ("run_ref", "activation_ref", "execution_ref"):
            for bad in ("", None, 123):
                with self.subTest(field=field, bad=bad):
                    kwargs = {
                        "run_ref": RUN_REF,
                        "activation_ref": ACTIVATION_REF,
                        "execution_ref": EXECUTION_REF,
                    }
                    kwargs[field] = bad
                    with self.assertRaises(RunError) as raised:
                        self.runs.create_initial(**kwargs)
                    self.assertEqual("RUN_INVALID", raised.exception.code)
        self.assertEqual(0, self._count("runs"))
        self.assertEqual(0, self._count("run_attempts"))

    def test_create_initial_missing_workflow_execution_fails_closed(self) -> None:
        # An Activation may only reference an admitted workflow execution, so
        # reaching the "missing row" branch requires disabling the FK guard for
        # the seed only; the Run path still fails closed.
        self.store.connection.execute("PRAGMA foreign_keys = OFF")
        self._seed(include_workflow=False)

        with self.assertRaises(RunError) as raised:
            self._create_run()

        self.assertEqual(
            "WORKFLOW_EXECUTION_NOT_ADMITTED", raised.exception.code
        )
        self.assertEqual(0, self._count("runs"))
        self.assertEqual(0, self._count("run_attempts"))

    def test_create_initial_unadmitted_workflow_execution_fails_closed(self) -> None:
        # workflow_executions.state is schema-constrained to 'ADMITTED'; the
        # defensive branch is reached by relaxing only the CHECK constraint.
        self.store.connection.execute("PRAGMA ignore_check_constraints = ON")
        self._seed(workflow_state="REJECTED")

        with self.assertRaises(RunError) as raised:
            self._create_run()

        self.assertEqual(
            "WORKFLOW_EXECUTION_NOT_ADMITTED", raised.exception.code
        )
        self.assertEqual(0, self._count("runs"))
        self.assertEqual(0, self._count("run_attempts"))

    def test_replace_attempt_invalid_inputs_fail_closed_without_mutation(self) -> None:
        self._seed()
        self._create_run()
        before = self.runs.resolve(RUN_REF)

        invalid_cases = [
            ("empty run_ref", {"run_ref": ""}),
            ("none run_ref", {"run_ref": None}),
            ("non-string run_ref", {"run_ref": 123}),
            ("none attempt_seq", {"expected_attempt_seq": None}),
            ("string attempt_seq", {"expected_attempt_seq": "1"}),
            ("float attempt_seq", {"expected_attempt_seq": 1.5}),
            ("bool attempt_seq", {"expected_attempt_seq": True}),
            ("zero attempt_seq", {"expected_attempt_seq": 0}),
            ("negative attempt_seq", {"expected_attempt_seq": -1}),
            ("none generation", {"expected_fencing_generation": None}),
            ("string generation", {"expected_fencing_generation": "1"}),
            ("float generation", {"expected_fencing_generation": 1.5}),
            ("bool generation", {"expected_fencing_generation": True}),
            ("zero generation", {"expected_fencing_generation": 0}),
            ("negative generation", {"expected_fencing_generation": -1}),
        ]
        base = {
            "run_ref": RUN_REF,
            "expected_attempt_seq": 1,
            "expected_fencing_generation": 1,
        }
        for label, overrides in invalid_cases:
            with self.subTest(label=label):
                kwargs = {**base, **overrides}
                with self.assertRaises(RunError) as raised:
                    self.runs.replace_attempt(**kwargs)
                self.assertEqual(
                    "RUN_REPLACEMENT_INVALID", raised.exception.code
                )

        self.assertEqual(before, self.runs.resolve(RUN_REF))
        self.assertEqual(1, self._count("run_attempts"))

    def test_replace_attempt_unknown_run_ref_fails_closed(self) -> None:
        with self.assertRaises(RunError) as raised:
            self.runs.replace_attempt(
                run_ref="run:missing",
                expected_attempt_seq=1,
                expected_fencing_generation=1,
            )

        self.assertEqual("UNRESOLVED_RUN", raised.exception.code)
        self.assertEqual(0, self._count("runs"))
        self.assertEqual(0, self._count("run_attempts"))

    def test_resolve_current_with_rejects_non_string_and_empty_run_ref(self) -> None:
        for bad in (None, "", 123, True):
            with self.subTest(bad=bad):
                self.assertIsNone(self.resolver.resolve_current(bad))
                self.assertIsNone(
                    RuntimeAuthorityResolver.resolve_current_with(
                        self.store.connection, bad
                    )
                )

    def test_resolve_current_with_returns_none_for_non_open_run(self) -> None:
        self._seed()
        self._create_run()
        self.store.connection.execute(
            "UPDATE runs SET state = 'TERMINAL' WHERE run_ref = ?",
            (RUN_REF,),
        )

        self.assertIsNone(self.resolver.resolve_current(RUN_REF))
        self.assertIsNone(
            RuntimeAuthorityResolver.resolve_current_with(
                self.store.connection, RUN_REF
            )
        )

    def test_resolve_current_with_returns_none_for_non_current_attempt_state(
        self,
    ) -> None:
        self._seed()
        self._create_run()
        # CREATED -> FAILED is a legal transition but FAILED is not current.
        self.store.connection.execute(
            "UPDATE run_attempts SET state = 'FAILED' "
            "WHERE run_ref = ? AND attempt_seq = 1",
            (RUN_REF,),
        )
        run_state = self.store.connection.execute(
            "SELECT state FROM runs WHERE run_ref = ?", (RUN_REF,)
        ).fetchone()[0]
        self.assertEqual("OPEN", run_state)

        self.assertIsNone(self.resolver.resolve_current(RUN_REF))
        self.assertIsNone(
            RuntimeAuthorityResolver.resolve_current_with(
                self.store.connection, RUN_REF
            )
        )

    def test_is_current_requires_exact_authority_match(self) -> None:
        self._seed()
        self._create_run()
        authority = self.resolver.resolve_current(RUN_REF)
        assert authority is not None

        self.assertTrue(self.resolver.is_current(authority))
        self.assertTrue(
            RuntimeAuthorityResolver.is_current_with(
                self.store.connection, authority
            )
        )

        altered_fields = {
            "execution_ref": "execution:other",
            "activation_ref": "activation:other",
            "run_ref": "run:other",
            "attempt_seq": 2,
            "fencing_token": "fencing:other",
            "fencing_generation": 2,
        }
        for field, value in altered_fields.items():
            with self.subTest(field=field):
                altered = replace(authority, **{field: value})
                self.assertFalse(self.resolver.is_current(altered))
                self.assertFalse(
                    RuntimeAuthorityResolver.is_current_with(
                        self.store.connection, altered
                    )
                )

    def test_initial_fencing_token_is_deterministic_and_identity_sensitive(
        self,
    ) -> None:
        token = RunRepository._initial_fencing_token(
            EXECUTION_REF, ACTIVATION_REF, RUN_REF
        )
        self.assertTrue(token.startswith("fencing:sha256:"))
        self.assertEqual(
            token,
            RunRepository._initial_fencing_token(
                EXECUTION_REF, ACTIVATION_REF, RUN_REF
            ),
        )

        for field, value in (
            ("execution_ref", "execution:other"),
            ("activation_ref", "activation:other"),
            ("run_ref", "run:other"),
        ):
            with self.subTest(field=field):
                kwargs = {
                    "execution_ref": EXECUTION_REF,
                    "activation_ref": ACTIVATION_REF,
                    "run_ref": RUN_REF,
                }
                kwargs[field] = value
                self.assertNotEqual(
                    token, RunRepository._initial_fencing_token(**kwargs)
                )


if __name__ == "__main__":
    unittest.main()
