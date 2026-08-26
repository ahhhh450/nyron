"""Track C Task 004 — fail-closed regression coverage for the frozen Capability slice.

Test-only delivery. It adds branch coverage for the frozen Capability Authority /
CapabilityTypeRegistry validation and lifecycle error paths, plus raw-SQL schema
probes against the canonical ``capability_grants`` / ``capability_types`` tables.

All stores are in-memory :memory: SQLite; no file-backed database is used.

Branches already covered by ``tests/kernel/test_capability_foundation.py`` are not
repeated here (unresolved type -> UNRESOLVED_CAPABILITY_TYPE, version conflict ->
CAPABILITY_TYPE_VERSION_CONFLICT, stale-attempt authority, replay identity, and
the advisory-expiry / not-yet-valid / stale-runtime paths).
"""

from __future__ import annotations

import sqlite3
import unittest
from dataclasses import replace

from nyron_kernel.capability import (
    AdvisoryCapabilityValidation,
    CapabilityAuthority,
    CapabilityDecision,
    CapabilityError,
    CapabilityRequest,
    CapabilityTypeDefinition,
    CapabilityTypeError,
    CapabilityTypeRegistry,
)
from nyron_kernel.execution import RunRepository, RuntimeAuthorityResolver
from nyron_kernel.store import SQLiteStore


GRAPH = "graph:capability@1"
MODULE = "module-instance:capability@1"
EXECUTION = "execution:capability/1"
ACTIVATION = "activation:capability/1"
RUN = "run:capability/1"
TYPE_REF = "capability.workspace.read"
TYPE_VERSION = "1"
SCOPE_SCHEMA = "schema:capability-workspace-read@1"


def capability_type() -> CapabilityTypeDefinition:
    return CapabilityTypeDefinition(
        capability_type_ref=TYPE_REF,
        version=TYPE_VERSION,
        scope_schema_ref=SCOPE_SCHEMA,
        operation_schema_ref=None,
        compatible_effect_classes=("WORKSPACE_READ",),
        metadata={"description": "bounded workspace read"},
    )


class TrackC004CapabilityRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self._seed_runtime(self.store)
        self.registry = CapabilityTypeRegistry(self.store)
        self.registry.register(capability_type())
        self.runtime = RuntimeAuthorityResolver(self.store)
        self.attempt_authority = self.runtime.resolve_current(RUN)
        assert self.attempt_authority is not None
        self.now = 100
        self.authority = self._authority()

    def tearDown(self) -> None:
        self.store.close()

    @staticmethod
    def _seed_runtime(store: SQLiteStore) -> None:
        RunRepository(store)
        with store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO graph_revisions(
                    graph_revision_ref, contract_json, executable, reason_code
                ) VALUES (?, '{}', 1, NULL)
                """,
                (GRAPH,),
            )
            connection.execute(
                """
                INSERT INTO module_instance_revisions(
                    module_instance_revision_ref, graph_revision_ref,
                    module_instance_ref, module_ref, module_version,
                    config_ref, config_hash, input_port_contract_json,
                    output_port_contract_json, static_composite_path_json,
                    static_accounting_scope_ref
                ) VALUES (?, ?, 'capability-test', 'test.capability', '1',
                          'config:capability@1', 'sha256:capability-config',
                          '{}', '{}', '["root"]', 'accounting:capability')
                """,
                (MODULE, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO execution_admissions(
                    admission_ref, execution_ref, graph_revision_ref,
                    runtime_policy_ref, admitted_at_owner_order, state
                ) VALUES ('admission:capability/1', ?, ?,
                          'policy:capability@1', 1, 'ADMITTED')
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO workflow_executions(
                    execution_ref, graph_revision_ref, admission_ref,
                    runtime_policy_ref, state
                ) VALUES (?, ?, 'admission:capability/1',
                          'policy:capability@1', 'ADMITTED')
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO activations(
                    activation_ref, execution_ref, graph_revision_ref,
                    module_instance_revision_ref, trigger_delivery_ref,
                    input_bindings_json, static_accounting_scope_ref,
                    created_event_ref
                ) VALUES (?, ?, ?, ?, 'delivery:capability-trigger', '[]',
                          'accounting:capability',
                          'event:activation:capability/1')
                """,
                (ACTIVATION, EXECUTION, GRAPH, MODULE),
            )
            connection.execute(
                """
                INSERT INTO activation_created_events(
                    created_event_ref, activation_ref, event_kind
                ) VALUES ('event:activation:capability/1', ?,
                          'ActivationCreated')
                """,
                (ACTIVATION,),
            )
        RunRepository(store).create_initial(
            run_ref=RUN,
            activation_ref=ACTIVATION,
            execution_ref=EXECUTION,
        )

    def _authority(self, clock=None) -> CapabilityAuthority:
        def policy(request: CapabilityRequest) -> CapabilityDecision:
            return CapabilityDecision("GRANTED", "decision:capability/1")

        def scope_validator(schema_ref: str, scope: object) -> bool:
            return (
                schema_ref == SCOPE_SCHEMA
                and isinstance(scope, dict)
                and set(scope) == {"workspace_ref", "access"}
                and isinstance(scope["workspace_ref"], str)
                and bool(scope["workspace_ref"])
                and scope["access"] == "READ"
            )

        return CapabilityAuthority(
            self.store,
            self.registry,
            self.runtime,
            policy,
            scope_validator,
            clock if clock is not None else (lambda: self.now),
        )

    def _request(self, **changes) -> CapabilityRequest:
        values = {
            "grant_ref": "grant:capability/1",
            "capability_type_ref": TYPE_REF,
            "capability_type_version": TYPE_VERSION,
            "authority": self.attempt_authority,
            "scope": {"workspace_ref": "workspace:1", "access": "READ"},
            "issued_by": "capability-authority:test",
            "policy_context_ref": "policy-context:1",
        }
        values.update(changes)
        return CapabilityRequest(**values)

    def _grant_count(self) -> int:
        return self.store.connection.execute(
            "SELECT COUNT(*) FROM capability_grants"
        ).fetchone()[0]

    def _insert_grant_raw(self, **overrides) -> None:
        values = {
            "grant_ref": "grant:raw/1",
            "capability_type_ref": TYPE_REF,
            "capability_type_version": TYPE_VERSION,
            "execution_ref": EXECUTION,
            "activation_ref": ACTIVATION,
            "run_ref": RUN,
            "attempt_seq": 1,
            "fencing_token": "fencing:capability/1",
            "fencing_generation": 1,
            "scope_json": '{"access":"READ","workspace_ref":"workspace:1"}',
            "issued_by": "capability-authority:test",
            "policy_decision_ref": None,
            "issued_at": 100,
            "not_before": None,
            "expires_at": None,
            "state": "ACTIVE",
        }
        values.update(overrides)
        columns = list(values)
        placeholders = ", ".join("?" for _ in columns)
        sql = (
            "INSERT INTO capability_grants("
            + ", ".join(columns)
            + ") VALUES ("
            + placeholders
            + ")"
        )
        self.store.connection.execute(sql, tuple(values[col] for col in columns))

    # --- _validate_request fail-closed branches ---------------------------

    def test_issue_rejects_non_capability_request(self):
        for value in (None, "not-a-request", {"grant_ref": "x"}, 42):
            with self.subTest(value=value):
                with self.assertRaises(CapabilityError) as raised:
                    self.authority.issue(value)
                self.assertEqual("CAPABILITY_REQUEST_INVALID", raised.exception.code)
        self.assertEqual(0, self._grant_count())

    def test_validate_request_field_validation_fail_closed(self):
        valid = self._request()
        CapabilityAuthority._validate_request(valid)  # sanity: no raise

        invalid = []
        for field in (
            "grant_ref",
            "capability_type_ref",
            "capability_type_version",
            "issued_by",
        ):
            invalid.append(replace(valid, **{field: ""}))
        invalid.append(replace(valid, grant_ref=123))
        invalid.append(replace(valid, issued_by=None))
        invalid.append(replace(valid, authority=None))
        invalid.append(replace(valid, authority="not-an-attempt-authority"))
        invalid.append(replace(valid, scope=None))
        invalid.append(replace(valid, scope=["workspace_ref"]))
        invalid.append(replace(valid, scope="workspace:1"))
        invalid.append(replace(valid, policy_context_ref=""))
        invalid.append(replace(valid, policy_context_ref=123))

        for index, request in enumerate(invalid):
            with self.subTest(index=index, request=request):
                with self.assertRaises(CapabilityError) as raised:
                    CapabilityAuthority._validate_request(request)
                self.assertEqual(
                    "CAPABILITY_REQUEST_INVALID", raised.exception.code
                )

    # --- _canonical_scope fail-closed branches ----------------------------

    def test_canonical_scope_fail_closed(self):
        for value in (None, "scope", ["a"], 5, True):
            with self.subTest(value=value):
                with self.assertRaises(CapabilityError) as raised:
                    CapabilityAuthority._canonical_scope(value)
                self.assertEqual("CAPABILITY_SCOPE_INVALID", raised.exception.code)

        for value in (
            {"x": object()},
            {"x": {1, 2}},
            {"x": float("nan")},
            {"x": float("inf")},
        ):
            with self.subTest(serializable=value):
                with self.assertRaises(CapabilityError) as raised:
                    CapabilityAuthority._canonical_scope(value)
                self.assertEqual("CAPABILITY_SCOPE_INVALID", raised.exception.code)

        self.assertEqual(
            '{"a":1}', CapabilityAuthority._canonical_scope({"a": 1})
        )

    def test_issue_rejects_non_serializable_scope(self):
        with self.assertRaises(CapabilityError) as raised:
            self.authority.issue(
                self._request(grant_ref="grant:nonserializable", scope={"x": object()})
            )
        self.assertEqual("CAPABILITY_SCOPE_INVALID", raised.exception.code)
        self.assertEqual(0, self._grant_count())

    # --- _validate_validity fail-closed branches --------------------------

    def test_validate_validity_fail_closed(self):
        invalid = (
            (100, "105", None),
            (100, 105.0, None),
            (100, True, None),
            (100, None, "200"),
            (100, None, 200.0),
            (100, None, False),
            (100, None, 100),
            (100, None, 99),
            (100, 105, 105),
            (100, 105, 104),
        )
        for issued_at, not_before, expires_at in invalid:
            with self.subTest(
                issued_at=issued_at, not_before=not_before, expires_at=expires_at
            ):
                with self.assertRaises(CapabilityError) as raised:
                    CapabilityAuthority._validate_validity(
                        issued_at, not_before, expires_at
                    )
                self.assertEqual(
                    "CAPABILITY_VALIDITY_INVALID", raised.exception.code
                )

        for args in ((100, None, None), (100, None, 101), (100, 100, 101), (100, 105, 110)):
            with self.subTest(valid=args):
                CapabilityAuthority._validate_validity(*args)  # no raise

    def test_issue_rejects_invalid_validity_window(self):
        for kwargs in (
            {"not_before": "105"},
            {"expires_at": True},
            {"expires_at": 50},
            {"not_before": 105, "expires_at": 105},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(CapabilityError) as raised:
                    self.authority.issue(
                        self._request(grant_ref="grant:validity"), **kwargs
                    )
                self.assertEqual("CAPABILITY_VALIDITY_INVALID", raised.exception.code)
                self.assertEqual(0, self._grant_count())

    # --- _now clock fail-closed branches ----------------------------------

    def test_clock_fail_closed(self):
        self.assertEqual(100, self.authority._now())

        for index, bad_clock in enumerate(
            (lambda: True, lambda: "100", lambda: 100.5, lambda: None)
        ):
            with self.subTest(index=index):
                authority = self._authority(clock=bad_clock)
                with self.assertRaises(CapabilityError) as raised:
                    authority.issue(self._request(grant_ref=f"grant:clock:{index}"))
                self.assertEqual("CAPABILITY_CLOCK_INVALID", raised.exception.code)
        self.assertEqual(0, self._grant_count())

    # --- revoke unknown grant ---------------------------------------------

    def test_revoke_unknown_grant(self):
        with self.assertRaises(CapabilityError) as raised:
            self.authority.revoke("grant:missing")
        self.assertEqual("UNRESOLVED_CAPABILITY_GRANT", raised.exception.code)

    # --- validate_advisory fail-closed branches ---------------------------

    def test_validate_advisory_fail_closed_branches(self):
        valid_scope = {"workspace_ref": "workspace:1", "access": "READ"}

        unknown = self.authority.validate_advisory(
            "grant:missing", self.attempt_authority, valid_scope
        )
        self.assertEqual(
            AdvisoryCapabilityValidation(False, "UNRESOLVED_CAPABILITY_GRANT"),
            unknown,
        )

        self.authority.issue(self._request())

        mismatch = self.authority.validate_advisory(
            "grant:capability/1",
            self.attempt_authority,
            {"workspace_ref": "workspace:2", "access": "READ"},
        )
        self.assertEqual(
            AdvisoryCapabilityValidation(False, "CAPABILITY_SCOPE_MISMATCH"),
            mismatch,
        )

        wrong_authority = replace(
            self.attempt_authority, fencing_token="fencing:wrong"
        )
        non_transferable = self.authority.validate_advisory(
            "grant:capability/1", wrong_authority, valid_scope
        )
        self.assertEqual(
            AdvisoryCapabilityValidation(False, "CAPABILITY_NON_TRANSFERABLE"),
            non_transferable,
        )

    # --- CapabilityTypeRegistry malformed definition fail-closed ----------

    def test_registry_malformed_definition_fail_closed(self):
        malformed = (
            replace(capability_type(), capability_type_ref=""),
            replace(capability_type(), version=""),
            replace(capability_type(), scope_schema_ref=""),
            replace(capability_type(), capability_type_ref=123),
            replace(capability_type(), operation_schema_ref=123),
            replace(capability_type(), operation_schema_ref=""),
            replace(
                capability_type(), compatible_effect_classes=["WORKSPACE_READ"]
            ),
            replace(capability_type(), compatible_effect_classes=("",)),
            replace(
                capability_type(),
                compatible_effect_classes=("WORKSPACE_READ", "WORKSPACE_READ"),
            ),
            replace(capability_type(), metadata="not-a-dict"),
            replace(capability_type(), metadata={"x": object()}),
        )
        for index, definition in enumerate(malformed):
            with self.subTest(index=index, definition=definition):
                with self.assertRaises(CapabilityTypeError) as raised:
                    self.registry.register(definition)
                self.assertEqual("CAPABILITY_TYPE_INVALID", raised.exception.code)

        self.assertEqual(
            capability_type(), self.registry.resolve(TYPE_REF, TYPE_VERSION)
        )

    # --- raw SQL schema probes (CHECK / UNIQUE / NOT NULL / FK) ------------

    def test_capability_grants_raw_schema_constraints_fail_closed(self):
        self._insert_grant_raw(grant_ref="grant:raw/1")
        self.assertEqual(1, self._grant_count())

        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_grant_raw(grant_ref="grant:check-seq", attempt_seq=0)
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_grant_raw(grant_ref="grant:check-token", fencing_token="")
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_grant_raw(
                grant_ref="grant:check-generation", fencing_generation=0
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_grant_raw(grant_ref="grant:check-state", state="BOGUS")

        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_grant_raw(grant_ref="grant:null-issued-at", issued_at=None)
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_grant_raw(grant_ref="grant:null-scope", scope_json=None)
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_grant_raw(grant_ref="grant:null-issued-by", issued_by=None)

        self._insert_grant_raw(grant_ref="grant:dup")
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_grant_raw(grant_ref="grant:dup")

        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_grant_raw(
                grant_ref="grant:fk-type", capability_type_ref="capability:missing"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_grant_raw(
                grant_ref="grant:fk-activation", activation_ref="activation:missing"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_grant_raw(grant_ref="grant:fk-run", run_ref="run:missing")
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_grant_raw(grant_ref="grant:fk-attempt", attempt_seq=999)

    def test_capability_types_raw_schema_constraints_fail_closed(self):
        self.store.connection.execute(
            """
            INSERT INTO capability_types(capability_type_ref, version, contract_json)
            VALUES ('type:raw', '1', '{}')
            """
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                """
                INSERT INTO capability_types(
                    capability_type_ref, version, contract_json
                ) VALUES ('type:raw', '1', '{}')
                """
            )

        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                """
                INSERT INTO capability_types(
                    capability_type_ref, version, contract_json
                ) VALUES ('type:null-contract', '1', NULL)
                """
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                """
                INSERT INTO capability_types(
                    capability_type_ref, version, contract_json
                ) VALUES (NULL, '1', '{}')
                """
            )


if __name__ == "__main__":
    unittest.main()
