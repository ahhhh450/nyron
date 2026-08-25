"""Executable acceptance coverage for ARE-GATE-1A / Task 034."""

from __future__ import annotations

import inspect
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

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


class CapabilityFoundationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self._seed_runtime(self.store)
        self.registry = CapabilityTypeRegistry(self.store)
        self.registry.register(capability_type())
        self.runtime = RuntimeAuthorityResolver(self.store)
        self.attempt_authority = self.runtime.resolve_current(RUN)
        assert self.attempt_authority is not None
        self.now = 100
        self.policy_status = "GRANTED"
        self.policy_calls = []
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

    def _authority(self) -> CapabilityAuthority:
        def policy(request: CapabilityRequest) -> CapabilityDecision:
            self.policy_calls.append(request)
            return CapabilityDecision(
                self.policy_status, "decision:capability/1"
            )

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
            lambda: self.now,
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

    def test_type_registration_exact_resolution_idempotency_and_conflict(self):
        registered = self.registry.resolve(TYPE_REF, TYPE_VERSION)
        self.assertEqual(capability_type(), registered)
        self.assertEqual(registered, self.registry.register(capability_type()))
        self.assertIsNone(self.registry.resolve(TYPE_REF, "2"))
        self.assertEqual(0, self._grant_count())

        conflicting = replace(
            capability_type(), scope_schema_ref="schema:different@1"
        )
        with self.assertRaises(CapabilityTypeError) as raised:
            self.registry.register(conflicting)
        self.assertEqual(
            "CAPABILITY_TYPE_VERSION_CONFLICT", raised.exception.code
        )
        self.assertEqual(capability_type(), self.registry.resolve(TYPE_REF, "1"))

    def test_policy_denied_and_requires_approval_create_zero_grant(self):
        for status, code in (
            ("DENIED", "CAPABILITY_DENIED"),
            ("REQUIRES_APPROVAL", "CAPABILITY_REQUIRES_APPROVAL"),
        ):
            with self.subTest(status=status):
                self.policy_status = status
                with self.assertRaises(CapabilityError) as raised:
                    self.authority.issue(
                        self._request(grant_ref=f"grant:{status}")
                    )
                self.assertEqual(code, raised.exception.code)
                self.assertEqual(0, self._grant_count())

    def test_policy_exception_and_malformed_decision_fail_closed(self):
        request = self._request(grant_ref="grant:bad-policy")
        for evaluator in (
            lambda _: (_ for _ in ()).throw(RuntimeError("policy failed")),
            lambda _: CapabilityDecision("ALLOW"),
            lambda _: "GRANTED",
        ):
            with self.subTest(evaluator=evaluator):
                authority = CapabilityAuthority(
                    self.store,
                    self.registry,
                    self.runtime,
                    evaluator,
                    lambda ref, scope: ref == SCOPE_SCHEMA and scope == {
                        "workspace_ref": "workspace:1",
                        "access": "READ",
                    },
                    lambda: self.now,
                )
                with self.assertRaises(CapabilityError) as raised:
                    authority.issue(request)
                self.assertEqual(
                    "CAPABILITY_POLICY_DECISION_INVALID",
                    raised.exception.code,
                )
                self.assertEqual(0, self._grant_count())

    def test_granted_scope_and_current_attempt_create_one_immutable_grant(self):
        caller_scope = {"workspace_ref": "workspace:1", "access": "READ"}
        grant = self.authority.issue(self._request(scope=caller_scope))
        caller_scope["workspace_ref"] = "workspace:expanded"

        self.assertEqual("ACTIVE", grant.state)
        self.assertEqual(TYPE_REF, grant.capability_type_ref)
        self.assertEqual(TYPE_VERSION, grant.capability_type_version)
        self.assertEqual(self.attempt_authority.execution_ref, grant.execution_ref)
        self.assertEqual(self.attempt_authority.activation_ref, grant.activation_ref)
        self.assertEqual(self.attempt_authority.run_ref, grant.run_ref)
        self.assertEqual(self.attempt_authority.attempt_seq, grant.attempt_seq)
        self.assertEqual(self.attempt_authority.fencing_token, grant.fencing_token)
        self.assertEqual(
            self.attempt_authority.fencing_generation,
            grant.fencing_generation,
        )
        self.assertEqual(
            {"workspace_ref": "workspace:1", "access": "READ"},
            grant.scope,
        )
        self.assertEqual("decision:capability/1", grant.policy_decision_ref)
        self.assertEqual(1, self._grant_count())

    def test_unknown_type_and_invalid_scope_fail_closed_before_policy(self):
        with self.assertRaises(CapabilityError) as missing:
            self.authority.issue(
                self._request(
                    capability_type_ref="capability:missing",
                    grant_ref="grant:missing",
                )
            )
        self.assertEqual("UNRESOLVED_CAPABILITY_TYPE", missing.exception.code)

        invalid_scopes = (
            {},
            {"workspace_ref": "workspace:1", "access": "WRITE"},
            {
                "workspace_ref": "workspace:1",
                "access": "READ",
                "hidden_expand": True,
            },
        )
        for index, scope in enumerate(invalid_scopes):
            with self.subTest(scope=scope):
                with self.assertRaises(CapabilityError) as invalid:
                    self.authority.issue(
                        self._request(grant_ref=f"grant:invalid:{index}", scope=scope)
                    )
                self.assertEqual("CAPABILITY_SCOPE_INVALID", invalid.exception.code)
        self.assertEqual(0, self._grant_count())
        self.assertEqual([], self.policy_calls)

    def test_every_attempt_authority_component_mismatch_cannot_receive_grant(self):
        stale_values = (
            replace(self.attempt_authority, execution_ref="execution:stale"),
            replace(self.attempt_authority, activation_ref="activation:stale"),
            replace(self.attempt_authority, run_ref="run:stale"),
            replace(self.attempt_authority, attempt_seq=2),
            replace(self.attempt_authority, fencing_token="fencing:stale"),
            replace(self.attempt_authority, fencing_generation=2),
        )
        for index, stale in enumerate(stale_values):
            with self.subTest(authority=stale):
                with self.assertRaises(CapabilityError) as raised:
                    self.authority.issue(
                        self._request(
                            grant_ref=f"grant:stale:{index}", authority=stale
                        )
                    )
                self.assertEqual("STALE_ATTEMPT_AUTHORITY", raised.exception.code)
        self.assertEqual(0, self._grant_count())

    def test_grant_replay_is_stable_and_identity_cannot_transfer_or_widen(self):
        first = self.authority.issue(self._request(), expires_at=200)
        replay = self.authority.issue(self._request(), expires_at=200)
        self.assertEqual(first, replay)
        self.assertEqual(1, len(self.policy_calls))

        with self.assertRaises(CapabilityError) as widen:
            self.authority.issue(
                self._request(scope={"workspace_ref": "workspace:2", "access": "READ"}),
                expires_at=200,
            )
        self.assertEqual("CAPABILITY_GRANT_IDENTITY_CONFLICT", widen.exception.code)

        second_authority = self._seed_second_current_attempt()
        with self.assertRaises(CapabilityError) as transfer:
            self.authority.issue(
                self._request(authority=second_authority), expires_at=200
            )
        self.assertEqual(
            "CAPABILITY_GRANT_IDENTITY_CONFLICT", transfer.exception.code
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                """
                UPDATE capability_grants
                SET scope_json = '{"access":"READ","workspace_ref":"workspace:2"}'
                WHERE grant_ref = 'grant:capability/1'
                """
            )

    def _seed_second_current_attempt(self):
        with self.store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO activations(
                    activation_ref, execution_ref, graph_revision_ref,
                    module_instance_revision_ref, trigger_delivery_ref,
                    input_bindings_json, static_accounting_scope_ref,
                    created_event_ref
                ) VALUES ('activation:capability/2', ?, ?, ?,
                          'delivery:capability-trigger:2', '[]',
                          'accounting:capability',
                          'event:activation:capability/2')
                """,
                (EXECUTION, GRAPH, MODULE),
            )
            connection.execute(
                """
                INSERT INTO activation_created_events(
                    created_event_ref, activation_ref, event_kind
                ) VALUES ('event:activation:capability/2',
                          'activation:capability/2', 'ActivationCreated')
                """
            )
        RunRepository(self.store).create_initial(
            run_ref="run:capability/2",
            activation_ref="activation:capability/2",
            execution_ref=EXECUTION,
        )
        resolved = self.runtime.resolve_current("run:capability/2")
        assert resolved is not None
        return resolved

    def test_revoke_is_durable_and_advisory_validation_rejects_it(self):
        self.authority.issue(self._request())
        before = self.authority.validate_advisory(
            "grant:capability/1",
            self.attempt_authority,
            {"workspace_ref": "workspace:1", "access": "READ"},
        )
        self.assertEqual(
            AdvisoryCapabilityValidation(True, "ADVISORY_VALID"), before
        )

        revoked = self.authority.revoke("grant:capability/1")
        after = self.authority.validate_advisory(
            "grant:capability/1",
            self.attempt_authority,
            {"workspace_ref": "workspace:1", "access": "READ"},
        )
        self.assertEqual("REVOKED", revoked.state)
        self.assertEqual(
            AdvisoryCapabilityValidation(False, "CAPABILITY_REVOKED"), after
        )

    def test_revoke_after_expiry_is_durable_expired_not_revoked(self):
        self.authority.issue(self._request(), expires_at=105)
        self.assertEqual(
            "ACTIVE", self.authority.resolve("grant:capability/1").state
        )

        self.now = 110
        expired = self.authority.revoke("grant:capability/1")
        self.assertEqual("EXPIRED", expired.state)
        self.assertEqual(
            "EXPIRED", self.authority.resolve("grant:capability/1").state
        )
        validation = self.authority.validate_advisory(
            "grant:capability/1",
            self.attempt_authority,
            {"workspace_ref": "workspace:1", "access": "READ"},
        )
        self.assertEqual(
            AdvisoryCapabilityValidation(False, "CAPABILITY_EXPIRED"),
            validation,
        )

    def test_expiry_and_not_before_are_fail_closed_and_expiry_persists(self):
        self.authority.issue(self._request(), not_before=105, expires_at=110)
        early = self.authority.validate_advisory(
            "grant:capability/1",
            self.attempt_authority,
            {"workspace_ref": "workspace:1", "access": "READ"},
        )
        self.assertEqual("CAPABILITY_NOT_YET_VALID", early.reason_code)

        self.now = 105
        self.assertTrue(
            self.authority.validate_advisory(
                "grant:capability/1",
                self.attempt_authority,
                {"workspace_ref": "workspace:1", "access": "READ"},
            ).valid
        )
        self.now = 110
        expired = self.authority.validate_advisory(
            "grant:capability/1",
            self.attempt_authority,
            {"workspace_ref": "workspace:1", "access": "READ"},
        )
        self.assertEqual("CAPABILITY_EXPIRED", expired.reason_code)
        self.assertEqual("EXPIRED", self.authority.resolve("grant:capability/1").state)

        self.now = 106
        self.assertEqual(
            "CAPABILITY_EXPIRED",
            self.authority.validate_advisory(
                "grant:capability/1",
                self.attempt_authority,
                {"workspace_ref": "workspace:1", "access": "READ"},
            ).reason_code,
        )

    def test_advisory_validation_rechecks_runtime_and_is_not_use_admission(self):
        self.authority.issue(self._request())
        cached = self.authority.validate_advisory(
            "grant:capability/1",
            self.attempt_authority,
            {"workspace_ref": "workspace:1", "access": "READ"},
        )
        self.assertTrue(cached.valid)
        self.store.connection.execute(
            "UPDATE runs SET fencing_generation = 2 WHERE run_ref = ?",
            (RUN,),
        )
        current = self.authority.validate_advisory(
            "grant:capability/1",
            self.attempt_authority,
            {"workspace_ref": "workspace:1", "access": "READ"},
        )
        self.assertEqual(
            AdvisoryCapabilityValidation(False, "STALE_ATTEMPT_AUTHORITY"),
            current,
        )
        self.assertFalse(hasattr(cached, "consume"))
        self.assertFalse(hasattr(cached, "permit_external_use"))
        self.assertIn(
            "without admitting or consuming authority",
            inspect.getsource(CapabilityAuthority).lower(),
        )

    def test_file_reopen_preserves_exact_type_and_grant_facts(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "capability.db"
            with SQLiteStore(database) as initial:
                self._seed_runtime(initial)
                registry = CapabilityTypeRegistry(initial)
                registered = registry.register(capability_type())
                runtime = RuntimeAuthorityResolver(initial)
                attempt = runtime.resolve_current(RUN)
                assert attempt is not None
                authority = CapabilityAuthority(
                    initial,
                    registry,
                    runtime,
                    lambda _: CapabilityDecision("GRANTED", "decision:reopen"),
                    lambda ref, scope: ref == SCOPE_SCHEMA and scope == {
                        "workspace_ref": "workspace:1",
                        "access": "READ",
                    },
                    lambda: 100,
                )
                grant = authority.issue(
                    CapabilityRequest(
                        "grant:reopen", TYPE_REF, TYPE_VERSION, attempt,
                        {"workspace_ref": "workspace:1", "access": "READ"},
                        "capability-authority:test",
                    )
                )

            with SQLiteStore(database) as reopened:
                registry_after = CapabilityTypeRegistry(reopened)
                authority_after = CapabilityAuthority(
                    reopened,
                    registry_after,
                    RuntimeAuthorityResolver(reopened),
                    lambda _: CapabilityDecision("DENIED"),
                    lambda _ref, _scope: False,
                    lambda: 100,
                )
                self.assertEqual(registered, registry_after.resolve(TYPE_REF, "1"))
                self.assertEqual(grant, authority_after.resolve("grant:reopen"))

    def test_no_resource_effect_command_or_consumption_surface_is_introduced(self):
        tables = {
            row["name"]
            for row in self.store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        for forbidden in (
            "resources", "resource_leases", "effect_operations",
            "canonical_commands", "authority_use_permits",
        ):
            self.assertNotIn(forbidden, tables)
        public = {
            name for name, _ in inspect.getmembers(
                CapabilityAuthority, predicate=inspect.isfunction
            ) if not name.startswith("_")
        }
        self.assertEqual(
            {"issue", "resolve", "revoke", "validate_advisory"}, public
        )


if __name__ == "__main__":
    unittest.main()
