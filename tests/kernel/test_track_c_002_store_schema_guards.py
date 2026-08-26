"""Schema-guard regression tests for the SQLite store layer (Track C Task 002).

This file only adds tests against the frozen production schema in
``src/nyron_kernel/store/sqlite_store.py``. It does not modify any production
code. Every probe runs against an in-memory ``SQLiteStore()`` (default
``:memory:``) plus raw SQL, never a file-backed database.

Guards are exercised one-by-one: each constraint is asserted to reject an
illegal value (``sqlite3.IntegrityError``) and is paired with a legal positive
case. Trigger state machines are asserted to reject illegal transitions and to
accept legal transitions plus same-state no-ops.

Schema guard inventory (read from ``sqlite_store.py``, exact base
``84156a5be8d77dc69fd21b02ffa2cf49f5154a8b``):

Core ``_create_schema``
- module_definitions: PK(module_ref, version); NOT NULL all columns.
- graph_revisions: PK(graph_revision_ref); NOT NULL contract_json, executable;
  CHECK executable IN (0, 1).
- module_instance_revisions: PK(module_instance_revision_ref);
  UNIQUE(graph_revision_ref, module_instance_ref); NOT NULL all columns;
  FK graph_revision_ref -> graph_revisions.
- graph_edges: PK(graph_revision_ref, edge_ref);
  UNIQUE(graph_revision_ref, edge_ordinal); NOT NULL all columns;
  CHECK edge_ordinal >= 0; CHECK target_port_ordinal >= 0;
  FK graph_revision_ref -> graph_revisions;
  FK target_module_instance_revision_ref -> module_instance_revisions.
- packets: PK(packet_ref); UNIQUE(execution_ref, source_packet_seq);
  NOT NULL non-null columns; CHECK source_packet_seq > 0;
  FK graph_revision_ref -> graph_revisions.
- deliveries: PK(packet_ref, graph_revision_ref, edge_ref, target_port_ref);
  NOT NULL all columns; FK packet_ref -> packets;
  FK (graph_revision_ref, edge_ref) -> graph_edges;
  FK target_module_instance_revision_ref -> module_instance_revisions.
- accounting_scopes: PK(accounting_scope_ref);
  UNIQUE(graph_revision_ref, definition_anchor_ref); NOT NULL non-null columns.
- execution_admissions: PK(admission_ref); UNIQUE execution_ref;
  UNIQUE admitted_at_owner_order; NOT NULL non-null columns;
  CHECK admitted_at_owner_order > 0; CHECK state = 'ADMITTED';
  FK graph_revision_ref -> graph_revisions.
- workflow_executions: PK(execution_ref); UNIQUE admission_ref;
  NOT NULL non-null columns; CHECK state = 'ADMITTED';
  FK graph_revision_ref -> graph_revisions; FK admission_ref -> execution_admissions.

``create_activation_schema``
- activations: PK(activation_ref); UNIQUE trigger_delivery_ref;
  UNIQUE created_event_ref; NOT NULL non-null columns;
  FK execution_ref -> workflow_executions; FK graph_revision_ref -> graph_revisions;
  FK module_instance_revision_ref -> module_instance_revisions.
- delivery_bindings: PK(delivery_ref); NOT NULL all columns;
  FK (packet_ref, graph_revision_ref, edge_ref, target_port_ref) -> deliveries;
  FK activation_ref -> activations (DEFERRABLE INITIALLY DEFERRED).
- activation_created_events: PK(created_event_ref); UNIQUE activation_ref;
  NOT NULL non-null columns; CHECK event_kind = 'ActivationCreated';
  FK activation_ref -> activations.

``create_run_attempt_schema``
- runs: PK(run_ref); UNIQUE activation_ref; NOT NULL non-null columns;
  CHECK current_attempt_seq > 0; CHECK fencing_generation > 0;
  FK activation_ref -> activations; FK execution_ref -> workflow_executions.
- run_attempts: PK(run_ref, attempt_seq); UNIQUE fencing_token;
  NOT NULL non-null columns; CHECK attempt_seq > 0;
  CHECK length(fencing_token) > 0;
  CHECK state IN ('CREATED','ACTIVE','SUCCEEDED','FAILED','REPLACED');
  FK run_ref -> runs.
- TRIGGER run_attempt_state_transition: BEFORE UPDATE OF state;
  legal: no-op; CREATED -> ACTIVE/FAILED/REPLACED; ACTIVE -> SUCCEEDED/FAILED/REPLACED.
- TRIGGER run_authority_counter_transition: BEFORE UPDATE OF
  current_attempt_seq, fencing_generation; legal: no-op, or equal positive delta.

``create_attempt_execution_schema``
- durable_values: PK(value_ref); NOT NULL value_json.
- run_terminal_events: PK(event_ref); UNIQUE run_ref; NOT NULL non-null columns;
  CHECK event_kind = 'RunSucceeded'; FK run_ref -> runs;
  FK (run_ref, attempt_seq) -> run_attempts.

``create_capability_schema``
- capability_types: PK(capability_type_ref, version); NOT NULL all columns.
- capability_grants: PK(grant_ref); NOT NULL non-null columns;
  CHECK attempt_seq > 0; CHECK length(fencing_token) > 0;
  CHECK fencing_generation > 0; CHECK state IN ('ACTIVE','REVOKED','EXPIRED');
  FK (capability_type_ref, capability_type_version) -> capability_types;
  FK activation_ref -> activations; FK (run_ref, attempt_seq) -> run_attempts.
- TRIGGER capability_grant_immutable_fields: identity fields immutable (state mutable).
- TRIGGER capability_grant_state_transition: ACTIVE -> REVOKED/EXPIRED or no-op.

``create_resource_schema``
- resources: PK(resource_ref); UNIQUE external_ref; NOT NULL non-null columns;
  CHECK state IN ('PROVISIONING','AVAILABLE','DESTROYING','DESTROYED','UNKNOWN').
- resource_leases: PK(lease_ref); NOT NULL non-null columns;
  CHECK attempt_seq > 0; CHECK length(fencing_token) > 0;
  CHECK fencing_generation > 0;
  CHECK state IN ('ACTIVE','REVOKE_REQUESTED','RELEASED','EXPIRED','UNKNOWN');
  FK resource_ref -> resources; FK activation_ref -> activations;
  FK (run_ref, attempt_seq) -> run_attempts.
- TRIGGER resource_immutable_fields; TRIGGER resource_lease_immutable_fields.
- TRIGGER resource_state_transition:
  PROVISIONING -> AVAILABLE/UNKNOWN; AVAILABLE -> DESTROYING/UNKNOWN;
  DESTROYING -> DESTROYED/UNKNOWN; or no-op.
- TRIGGER resource_lease_state_transition:
  ACTIVE -> REVOKE_REQUESTED/RELEASED/EXPIRED/UNKNOWN; or no-op.

``create_effect_schema``
- effect_operations: PK(operation_ref); UNIQUE target_ref;
  UNIQUE dispatch_admission_ref; NOT NULL non-null columns;
  CHECK attempt_seq > 0; CHECK length(fencing_token) > 0;
  CHECK fencing_generation > 0;
  CHECK state IN ('PREPARED','ACTIVE','REVOKE_REQUESTED','FENCED','COMPLETED','UNKNOWN');
  CHECK dispatch_admission_ref/dispatch_admitted_at pair;
  CHECK state != 'ACTIVE' OR dispatch_admission_ref IS NOT NULL;
  CHECK COMPLETED requires admission + completion_evidence_json;
  CHECK FENCED requires fence_evidence_json;
  FK capability_grant_ref -> capability_grants; FK resource_ref -> resources;
  FK resource_lease_ref -> resource_leases; FK (run_ref, attempt_seq) -> run_attempts.
- TRIGGER effect_operation_immutable_fields;
  TRIGGER effect_dispatch_admission_immutable;
  TRIGGER effect_dispatch_admission_requires_prepared;
  TRIGGER effect_completion_evidence_immutable;
  TRIGGER effect_fence_evidence_immutable;
  TRIGGER effect_operation_state_transition:
  PREPARED -> ACTIVE/FENCED/UNKNOWN; ACTIVE -> COMPLETED/REVOKE_REQUESTED/UNKNOWN;
  REVOKE_REQUESTED -> FENCED/COMPLETED/UNKNOWN; or no-op.
- TRIGGER effect_active_requires_admission.

``create_budget_schema``
- budget_policy_revisions: PK(budget_policy_revision_ref); NOT NULL non-null columns;
  CHECK effective_until IS NULL OR effective_until > effective_from;
  FK accounting_scope_ref -> accounting_scopes;
  FK supersedes_ref -> budget_policy_revisions (self).
- TRIGGER budget_policy_revision_immutable: any UPDATE aborted.
- budget_reservations: PK(reservation_ref); UNIQUE request_ref;
  NOT NULL non-null columns; CHECK attempt_seq > 0;
  CHECK state IN ('REQUESTED','RESERVED','DENIED','RECONCILING','COMMITTED','RELEASED');
  CHECK (state = 'DENIED' AND deny_reason_code IS NOT NULL)
        OR (state != 'DENIED' AND deny_reason_code IS NULL);
  FK accounting_scope_ref -> accounting_scopes; FK (run_ref, attempt_seq) -> run_attempts.
- TRIGGER budget_reservation_identity_immutable (committed/released dims + updated_at mutable).
- TRIGGER budget_reservation_state_transition:
  REQUESTED -> RESERVED/DENIED; RESERVED -> COMMITTED/RELEASED/RECONCILING;
  RELEASED -> RECONCILING; COMMITTED -> RECONCILING;
  RECONCILING -> COMMITTED/RELEASED; or no-op.
- budget_scope_exposure: PK(accounting_scope_ref, dimension_ref);
  NOT NULL non-null columns; CHECK reserved_amount >= 0; CHECK committed_amount >= 0;
  FK accounting_scope_ref -> accounting_scopes.
"""

from __future__ import annotations

import sqlite3
import unittest

from nyron_kernel.store import SQLiteStore


GRAPH = "graph:schema@1"
MODULE = "module-instance:schema@1"
EDGE = "edge:schema@1"
PACKET = "packet:schema@1"
DELIVERY = "delivery:schema@1"
SCOPE = "accounting:schema@1"
ADMISSION = "admission:schema@1"
EXECUTION = "execution:schema/1"
ACTIVATION = "activation:schema@1"
ACTIVATION_EVENT = "event:activation@1"
RUN = "run:schema@1"
ATTEMPT_TOKEN = "token:attempt@1"
CAP_TYPE = "capability-type:schema@1"
CAP_VERSION = "1"


class SQLiteStoreSchemaGuardTest(unittest.TestCase):
    """Regression coverage for every store-layer schema guard."""

    def setUp(self) -> None:
        self.store = SQLiteStore()
        # Install the full Task-scoped schema (idempotent; effect pulls in
        # capability + resource + run-attempt + activation + core).
        self.store.create_effect_schema()
        self.store.create_attempt_execution_schema()
        self.store.create_budget_schema()
        self.conn = self.store.connection

        self._effect_counter = 0
        self._grant_counter = 0
        self._resource_counter = 0
        self._lease_counter = 0
        self._attempt_counter = 1

        self._seed_backbone()

    def tearDown(self) -> None:
        self.store.close()

    # ------------------------------------------------------------------
    # Seeding helpers (valid rows; also serve as positive coverage)
    # ------------------------------------------------------------------

    def _seed_backbone(self) -> None:
        self._insert_graph()
        self._insert_module()
        self._insert_edge()
        self._insert_packet()
        self._insert_delivery()
        self._insert_scope()
        self._insert_admission()
        self._insert_execution()
        self._insert_activation()
        self._insert_run()
        self._insert_attempt()
        self._cap_type = self._insert_capability_type()
        self._grant = self._insert_capability_grant()
        self._resource = self._insert_resource()
        self._lease = self._insert_resource_lease()

    def _insert_graph(self, ref: str = GRAPH, executable: int = 1) -> str:
        self.conn.execute(
            "INSERT INTO graph_revisions(graph_revision_ref, contract_json,"
            " executable, reason_code) VALUES (?, '{}', ?, NULL)",
            (ref, executable),
        )
        return ref

    def _insert_module(
        self,
        ref: str = MODULE,
        graph: str = GRAPH,
        instance_ref: str = "probe",
    ) -> str:
        self.conn.execute(
            "INSERT INTO module_instance_revisions(module_instance_revision_ref,"
            " graph_revision_ref, module_instance_ref, module_ref, module_version,"
            " config_ref, config_hash, input_port_contract_json,"
            " output_port_contract_json, static_composite_path_json,"
            " static_accounting_scope_ref)"
            " VALUES (?, ?, ?, 'test.probe', '1', 'config:probe',"
            " 'sha256:probe', '{}', '{}', '[]', 'accounting:probe')",
            (ref, graph, instance_ref),
        )
        return ref

    def _insert_edge(
        self,
        ref: str = EDGE,
        graph: str = GRAPH,
        target_module: str = MODULE,
        edge_ordinal: int = 1,
    ) -> str:
        self.conn.execute(
            "INSERT INTO graph_edges(graph_revision_ref, edge_ref, source_ref,"
            " source_port_ref, target_module_instance_revision_ref, target_port_ref,"
            " edge_ordinal, target_port_ordinal)"
            " VALUES (?, ?, 'src:probe', 'out', ?, 'in', ?, 0)",
            (graph, ref, target_module, edge_ordinal),
        )
        return ref

    def _insert_packet(
        self,
        ref: str = PACKET,
        graph: str = GRAPH,
        execution: str = EXECUTION,
        seq: int = 1,
    ) -> str:
        self.conn.execute(
            "INSERT INTO packets(packet_ref, execution_ref, graph_revision_ref,"
            " source_kind, source_ref, source_port_ref, value_ref, schema_ref,"
            " source_packet_seq, caused_by_ref, created_event_ref)"
            " VALUES (?, ?, ?, 'runtime', 'src:probe', 'out', 'value:probe',"
            " 'schema:probe', ?, 'cause:probe', 'event:packet@1')",
            (ref, execution, graph, seq),
        )
        return ref

    def _insert_delivery(
        self,
        ref: str = DELIVERY,
        packet: str = PACKET,
        graph: str = GRAPH,
        edge: str = EDGE,
        target_module: str = MODULE,
        target_port: str = "in",
    ) -> str:
        self.conn.execute(
            "INSERT INTO deliveries(packet_ref, graph_revision_ref, edge_ref,"
            " target_module_instance_revision_ref, target_port_ref,"
            " source_packet_seq, edge_ordinal, target_port_ordinal)"
            " VALUES (?, ?, ?, ?, ?, 1, 1, 0)",
            (packet, graph, edge, target_module, target_port),
        )
        return ref

    def _insert_scope(
        self,
        ref: str = SCOPE,
        graph: str = GRAPH,
        anchor: str = "anchor:probe@1",
    ) -> str:
        self.conn.execute(
            "INSERT INTO accounting_scopes(accounting_scope_ref,"
            " graph_revision_ref, definition_anchor_ref, parent_accounting_scope_ref,"
            " scope_kind, ancestry_hash, created_from_definition_ref, state)"
            " VALUES (?, ?, ?, NULL, 'MODULE', 'hash:probe', ?, 'ACTIVE')",
            (ref, graph, anchor, anchor),
        )
        return ref

    def _insert_admission(
        self,
        ref: str = ADMISSION,
        execution: str = EXECUTION,
        graph: str = GRAPH,
        order: int = 1,
    ) -> str:
        self.conn.execute(
            "INSERT INTO execution_admissions(admission_ref, execution_ref,"
            " graph_revision_ref, runtime_policy_ref, admitted_at_owner_order, state)"
            " VALUES (?, ?, ?, 'policy:probe', ?, 'ADMITTED')",
            (ref, execution, graph, order),
        )
        return ref

    def _insert_execution(
        self,
        ref: str = EXECUTION,
        graph: str = GRAPH,
        admission: str = ADMISSION,
    ) -> str:
        self.conn.execute(
            "INSERT INTO workflow_executions(execution_ref, graph_revision_ref,"
            " admission_ref, runtime_policy_ref, state)"
            " VALUES (?, ?, ?, 'policy:probe', 'ADMITTED')",
            (ref, graph, admission),
        )
        return ref

    def _insert_activation(
        self,
        ref: str = ACTIVATION,
        execution: str = EXECUTION,
        graph: str = GRAPH,
        module: str = MODULE,
        trigger: str = "delivery:trigger@1",
        event: str = ACTIVATION_EVENT,
    ) -> str:
        self.conn.execute(
            "INSERT INTO activations(activation_ref, execution_ref,"
            " graph_revision_ref, module_instance_revision_ref, trigger_delivery_ref,"
            " input_bindings_json, static_accounting_scope_ref, created_event_ref)"
            " VALUES (?, ?, ?, ?, ?, '[]', 'accounting:probe', ?)",
            (ref, execution, graph, module, trigger, event),
        )
        self.conn.execute(
            "INSERT INTO activation_created_events(created_event_ref,"
            " activation_ref, event_kind) VALUES (?, ?, 'ActivationCreated')",
            (event, ref),
        )
        return ref

    def _insert_run(
        self,
        ref: str = RUN,
        activation: str = ACTIVATION,
        execution: str = EXECUTION,
    ) -> str:
        self.conn.execute(
            "INSERT INTO runs(run_ref, activation_ref, execution_ref,"
            " current_attempt_seq, fencing_generation, state)"
            " VALUES (?, ?, ?, 1, 1, 'OPEN')",
            (ref, activation, execution),
        )
        return ref

    def _insert_attempt(
        self,
        run: str = RUN,
        seq: int = 1,
        token: str = ATTEMPT_TOKEN,
        state: str = "CREATED",
    ) -> tuple[str, int]:
        self.conn.execute(
            "INSERT INTO run_attempts(run_ref, attempt_seq, fencing_token, state)"
            " VALUES (?, ?, ?, ?)",
            (run, seq, token, state),
        )
        return (run, seq)

    def _insert_capability_type(
        self,
        ref: str = CAP_TYPE,
        version: str = CAP_VERSION,
    ) -> tuple[str, str]:
        self.conn.execute(
            "INSERT INTO capability_types(capability_type_ref, version,"
            " contract_json) VALUES (?, ?, '{}')",
            (ref, version),
        )
        return (ref, version)

    def _insert_capability_grant(
        self,
        *,
        grant_ref: str | None = None,
        capability_type_ref: str | None = None,
        capability_type_version: str | None = None,
        activation_ref: str | None = None,
        run_ref: str | None = None,
        attempt_seq: int | None = None,
        state: str = "ACTIVE",
    ) -> str:
        if grant_ref is None:
            self._grant_counter += 1
            grant_ref = f"grant:schema:{self._grant_counter}"
        cap_type = capability_type_ref if capability_type_ref is not None else CAP_TYPE
        cap_ver = (
            capability_type_version
            if capability_type_version is not None
            else CAP_VERSION
        )
        activation = activation_ref if activation_ref is not None else ACTIVATION
        run = run_ref if run_ref is not None else RUN
        seq = attempt_seq if attempt_seq is not None else 1
        self.conn.execute(
            "INSERT INTO capability_grants(grant_ref, capability_type_ref,"
            " capability_type_version, execution_ref, activation_ref, run_ref,"
            " attempt_seq, fencing_token, fencing_generation, scope_json,"
            " issued_by, policy_decision_ref, issued_at, not_before, expires_at,"
            " state)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, '{}', 'issuer:probe', NULL,"
            " 100, NULL, NULL, ?)",
            (
                grant_ref,
                cap_type,
                cap_ver,
                EXECUTION,
                activation,
                run,
                seq,
                f"token:grant:{grant_ref}",
                state,
            ),
        )
        return grant_ref

    def _insert_resource(
        self,
        *,
        resource_ref: str | None = None,
        external_ref: str | None = None,
        state: str = "AVAILABLE",
    ) -> str:
        if resource_ref is None:
            self._resource_counter += 1
            resource_ref = f"resource:schema:{self._resource_counter}"
        external = (
            external_ref if external_ref is not None else f"external:{resource_ref}"
        )
        self.conn.execute(
            "INSERT INTO resources(resource_ref, resource_type, resource_owner_ref,"
            " scope_json, state, external_ref, provenance_json)"
            " VALUES (?, 'type:probe', 'owner:probe', '{}', ?, ?, '{}')",
            (resource_ref, state, external),
        )
        return resource_ref

    def _insert_resource_lease(
        self,
        *,
        lease_ref: str | None = None,
        resource_ref: str | None = None,
        activation_ref: str | None = None,
        run_ref: str | None = None,
        attempt_seq: int | None = None,
        state: str = "ACTIVE",
    ) -> str:
        if lease_ref is None:
            self._lease_counter += 1
            lease_ref = f"lease:schema:{self._lease_counter}"
        resource = resource_ref if resource_ref is not None else self._resource
        activation = activation_ref if activation_ref is not None else ACTIVATION
        run = run_ref if run_ref is not None else RUN
        seq = attempt_seq if attempt_seq is not None else 1
        self.conn.execute(
            "INSERT INTO resource_leases(lease_ref, resource_ref, lease_holder_ref,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, issued_at, expires_at, state)"
            " VALUES (?, ?, 'holder:probe', ?, ?, ?, ?, ?, 1, 100, NULL, ?)",
            (
                lease_ref,
                resource,
                EXECUTION,
                activation,
                run,
                seq,
                f"token:lease:{lease_ref}",
                state,
            ),
        )
        return lease_ref

    def _insert_effect(
        self,
        state: str = "PREPARED",
        *,
        admitted: bool = False,
        completion: bool = False,
        fence: bool = False,
        admission_ref: str | None = None,
        target_ref: str | None = None,
        capability_grant_ref: str | None = None,
        resource_ref: str | None = None,
        resource_lease_ref: str | None = None,
        run_ref: str | None = None,
        attempt_seq: int | None = None,
    ) -> str:
        self._effect_counter += 1
        operation_ref = f"operation:schema:{self._effect_counter}"
        if target_ref is None:
            target_ref = f"target:schema:{self._effect_counter}"
        if admitted and admission_ref is None:
            admission_ref = f"admission:op:{self._effect_counter}"
        admitted_at = 200 if admitted else None
        completion_json = '{"done": true}' if completion else None
        fence_json = '{"fenced": true}' if fence else None
        grant = (
            capability_grant_ref
            if capability_grant_ref is not None
            else self._grant
        )
        resource = resource_ref if resource_ref is not None else self._resource
        lease = resource_lease_ref if resource_lease_ref is not None else self._lease
        run = run_ref if run_ref is not None else RUN
        seq = attempt_seq if attempt_seq is not None else 1
        self.conn.execute(
            "INSERT INTO effect_operations(operation_ref, effect_class,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, capability_grant_ref, resource_ref,"
            " resource_lease_ref, target_ref, payload_json, payload_hash,"
            " caused_by_ref, state, prepared_at, dispatch_admission_ref,"
            " dispatch_admitted_at, completion_evidence_json, fence_evidence_json)"
            " VALUES (?, 'class:probe', ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, '{}',"
            " 'hash:probe', 'cause:probe', ?, 100, ?, ?, ?, ?)",
            (
                operation_ref,
                EXECUTION,
                ACTIVATION,
                run,
                seq,
                f"token:op:{self._effect_counter}",
                grant,
                resource,
                lease,
                target_ref,
                state,
                admission_ref,
                admitted_at,
                completion_json,
                fence_json,
            ),
        )
        return operation_ref

    # ------------------------------------------------------------------
    # Generic assertions
    # ------------------------------------------------------------------

    def _expect_integrity(self, sql: str, params: tuple = ()) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(sql, params)

    def _attempt_state(self, seq: int) -> str:
        return self.conn.execute(
            "SELECT state FROM run_attempts WHERE run_ref = ? AND attempt_seq = ?",
            (RUN, seq),
        ).fetchone()[0]

    def _run_counters(self) -> tuple[int, int]:
        row = self.conn.execute(
            "SELECT current_attempt_seq, fencing_generation FROM runs"
            " WHERE run_ref = ?",
            (RUN,),
        ).fetchone()
        return (row[0], row[1])

    def _new_attempt(self, state: str = "CREATED") -> int:
        """Insert an additional attempt under the seeded run and return its seq."""
        self._attempt_counter += 1
        seq = self._attempt_counter
        self._insert_attempt(run=RUN, seq=seq, token=f"token:attempt:{seq}", state=state)
        return seq

    # ------------------------------------------------------------------
    # Core schema
    # ------------------------------------------------------------------

    def test_module_definitions_primary_key_and_not_null(self) -> None:
        self.conn.execute(
            "INSERT INTO module_definitions(module_ref, version, contract_json)"
            " VALUES ('mod:probe', '1', '{}')"
        )
        self._expect_integrity(
            "INSERT INTO module_definitions(module_ref, version, contract_json)"
            " VALUES ('mod:probe', '1', '{}')"
        )
        self._expect_integrity(
            "INSERT INTO module_definitions(module_ref, version, contract_json)"
            " VALUES ('mod:probe', '2', NULL)"
        )

    def test_graph_revisions_executable_check_and_not_null(self) -> None:
        self._insert_graph("graph:schema@2", executable=0)
        self._expect_integrity(
            "INSERT INTO graph_revisions(graph_revision_ref, contract_json,"
            " executable, reason_code) VALUES ('graph:bad@1', '{}', 2, NULL)"
        )
        self._expect_integrity(
            "INSERT INTO graph_revisions(graph_revision_ref, contract_json,"
            " executable, reason_code) VALUES ('graph:bad@2', NULL, 1, NULL)"
        )

    def test_module_instance_revisions_unique_and_foreign_key(self) -> None:
        self._insert_module("module-instance:schema@2", instance_ref="probe2")
        self._expect_integrity(
            "INSERT INTO module_instance_revisions(module_instance_revision_ref,"
            " graph_revision_ref, module_instance_ref, module_ref, module_version,"
            " config_ref, config_hash, input_port_contract_json,"
            " output_port_contract_json, static_composite_path_json,"
            " static_accounting_scope_ref)"
            " VALUES ('module-instance:schema@3', ?, 'probe', 'test.probe', '1',"
            " 'config:x', 'sha256:x', '{}', '{}', '[]', 'accounting:x')",
            (GRAPH,),
        )
        self._expect_integrity(
            "INSERT INTO module_instance_revisions(module_instance_revision_ref,"
            " graph_revision_ref, module_instance_ref, module_ref, module_version,"
            " config_ref, config_hash, input_port_contract_json,"
            " output_port_contract_json, static_composite_path_json,"
            " static_accounting_scope_ref)"
            " VALUES ('module-instance:schema@4', 'graph:missing', 'other',"
            " 'test.probe', '1', 'config:x', 'sha256:x', '{}', '{}', '[]', 'a')"
        )

    def test_graph_edges_ordinal_checks_unique_and_foreign_key(self) -> None:
        self._insert_edge("edge:schema@2", edge_ordinal=2)
        self._expect_integrity(
            "INSERT INTO graph_edges(graph_revision_ref, edge_ref, source_ref,"
            " source_port_ref, target_module_instance_revision_ref, target_port_ref,"
            " edge_ordinal, target_port_ordinal)"
            " VALUES (?, 'edge:bad@1', 's', 'out', ?, 'in', -1, 0)",
            (GRAPH, MODULE),
        )
        self._expect_integrity(
            "INSERT INTO graph_edges(graph_revision_ref, edge_ref, source_ref,"
            " source_port_ref, target_module_instance_revision_ref, target_port_ref,"
            " edge_ordinal, target_port_ordinal)"
            " VALUES (?, 'edge:bad@2', 's', 'out', ?, 'in', 0, -1)",
            (GRAPH, MODULE),
        )
        self._expect_integrity(
            "INSERT INTO graph_edges(graph_revision_ref, edge_ref, source_ref,"
            " source_port_ref, target_module_instance_revision_ref, target_port_ref,"
            " edge_ordinal, target_port_ordinal)"
            " VALUES (?, 'edge:bad@3', 's', 'out', ?, 'in', 1, 0)",
            (GRAPH, MODULE),
        )
        self._expect_integrity(
            "INSERT INTO graph_edges(graph_revision_ref, edge_ref, source_ref,"
            " source_port_ref, target_module_instance_revision_ref, target_port_ref,"
            " edge_ordinal, target_port_ordinal)"
            " VALUES ('graph:missing', 'edge:bad@4', 's', 'out', ?, 'in', 3, 0)",
            (MODULE,),
        )

    def test_packets_source_packet_seq_check_unique_and_fk(self) -> None:
        self._insert_packet("packet:schema@2", seq=2)
        self._expect_integrity(
            "INSERT INTO packets(packet_ref, execution_ref, graph_revision_ref,"
            " source_kind, source_ref, source_port_ref, value_ref, schema_ref,"
            " source_packet_seq, caused_by_ref, created_event_ref)"
            " VALUES ('packet:bad@1', ?, ?, 'runtime', 's', 'out', 'v', 'sc',"
            " 0, 'c', 'e')",
            (EXECUTION, GRAPH),
        )
        self._expect_integrity(
            "INSERT INTO packets(packet_ref, execution_ref, graph_revision_ref,"
            " source_kind, source_ref, source_port_ref, value_ref, schema_ref,"
            " source_packet_seq, caused_by_ref, created_event_ref)"
            " VALUES ('packet:bad@2', ?, ?, 'runtime', 's', 'out', 'v', 'sc',"
            " 1, 'c', 'e')",
            (EXECUTION, GRAPH),
        )
        self._expect_integrity(
            "INSERT INTO packets(packet_ref, execution_ref, graph_revision_ref,"
            " source_kind, source_ref, source_port_ref, value_ref, schema_ref,"
            " source_packet_seq, caused_by_ref, created_event_ref)"
            " VALUES ('packet:bad@3', ?, 'graph:missing', 'runtime', 's', 'out',"
            " 'v', 'sc', 3, 'c', 'e')",
            (EXECUTION,),
        )

    def test_deliveries_foreign_keys(self) -> None:
        self._insert_delivery("delivery:schema@2", target_port="in2")
        self._expect_integrity(
            "INSERT INTO deliveries(packet_ref, graph_revision_ref, edge_ref,"
            " target_module_instance_revision_ref, target_port_ref,"
            " source_packet_seq, edge_ordinal, target_port_ordinal)"
            " VALUES ('packet:missing', ?, ?, ?, 'in', 1, 1, 0)",
            (GRAPH, EDGE, MODULE),
        )
        self._expect_integrity(
            "INSERT INTO deliveries(packet_ref, graph_revision_ref, edge_ref,"
            " target_module_instance_revision_ref, target_port_ref,"
            " source_packet_seq, edge_ordinal, target_port_ordinal)"
            " VALUES (?, ?, 'edge:missing', ?, 'in', 1, 1, 0)",
            (PACKET, GRAPH, MODULE),
        )
        self._expect_integrity(
            "INSERT INTO deliveries(packet_ref, graph_revision_ref, edge_ref,"
            " target_module_instance_revision_ref, target_port_ref,"
            " source_packet_seq, edge_ordinal, target_port_ordinal)"
            " VALUES (?, ?, ?, 'module:missing', 'in', 1, 1, 0)",
            (PACKET, GRAPH, EDGE),
        )

    def test_accounting_scopes_unique_and_not_null(self) -> None:
        self._insert_scope("accounting:schema@2", anchor="anchor:probe@2")
        self._expect_integrity(
            "INSERT INTO accounting_scopes(accounting_scope_ref,"
            " graph_revision_ref, definition_anchor_ref, parent_accounting_scope_ref,"
            " scope_kind, ancestry_hash, created_from_definition_ref, state)"
            " VALUES ('accounting:schema@3', ?, 'anchor:probe@1', NULL, 'MODULE',"
            " 'h', 'anchor:probe@1', 'ACTIVE')",
            (GRAPH,),
        )
        self._expect_integrity(
            "INSERT INTO accounting_scopes(accounting_scope_ref,"
            " graph_revision_ref, definition_anchor_ref, parent_accounting_scope_ref,"
            " scope_kind, ancestry_hash, created_from_definition_ref, state)"
            " VALUES ('accounting:schema@4', ?, NULL, NULL, 'MODULE', 'h', 'x',"
            " 'ACTIVE')",
            (GRAPH,),
        )

    def test_execution_admissions_guards(self) -> None:
        self._insert_admission("admission:schema@2", "execution:schema/2", order=2)
        self._expect_integrity(
            "INSERT INTO execution_admissions(admission_ref, execution_ref,"
            " graph_revision_ref, runtime_policy_ref, admitted_at_owner_order, state)"
            " VALUES ('admission:bad@1', 'execution:schema/3', ?, 'p', 0, 'ADMITTED')",
            (GRAPH,),
        )
        self._expect_integrity(
            "INSERT INTO execution_admissions(admission_ref, execution_ref,"
            " graph_revision_ref, runtime_policy_ref, admitted_at_owner_order, state)"
            " VALUES ('admission:bad@2', 'execution:schema/4', ?, 'p', 3, 'OTHER')",
            (GRAPH,),
        )
        self._expect_integrity(
            "INSERT INTO execution_admissions(admission_ref, execution_ref,"
            " graph_revision_ref, runtime_policy_ref, admitted_at_owner_order, state)"
            " VALUES ('admission:bad@3', ?, ?, 'p', 4, 'ADMITTED')",
            (EXECUTION, GRAPH),
        )
        self._expect_integrity(
            "INSERT INTO execution_admissions(admission_ref, execution_ref,"
            " graph_revision_ref, runtime_policy_ref, admitted_at_owner_order, state)"
            " VALUES ('admission:bad@4', 'execution:schema/5', ?, 'p', 1, 'ADMITTED')",
            (GRAPH,),
        )

    def test_workflow_executions_guards(self) -> None:
        # positive: distinct admission requires a distinct admission row first
        self._insert_admission("admission:schema@3", "execution:schema/7", order=5)
        self._insert_execution("execution:schema/7", admission="admission:schema@3")
        self._expect_integrity(
            "INSERT INTO workflow_executions(execution_ref, graph_revision_ref,"
            " admission_ref, runtime_policy_ref, state)"
            " VALUES ('execution:schema/8', ?, ?, 'p', 'OTHER')",
            (GRAPH, ADMISSION),
        )
        self._expect_integrity(
            "INSERT INTO workflow_executions(execution_ref, graph_revision_ref,"
            " admission_ref, runtime_policy_ref, state)"
            " VALUES ('execution:schema/9', ?, ?, 'p', 'ADMITTED')",
            (GRAPH, ADMISSION),
        )

    # ------------------------------------------------------------------
    # Activation schema
    # ------------------------------------------------------------------

    def test_activations_unique_and_foreign_key(self) -> None:
        self._insert_activation(
            "activation:schema@2", event="event:activation@2", trigger="delivery:trigger@2"
        )
        self._expect_integrity(
            "INSERT INTO activations(activation_ref, execution_ref,"
            " graph_revision_ref, module_instance_revision_ref, trigger_delivery_ref,"
            " input_bindings_json, static_accounting_scope_ref, created_event_ref)"
            " VALUES ('activation:bad@1', ?, ?, ?, 'delivery:trigger@1', '[]',"
            " 'a', 'event:activation@3')",
            (EXECUTION, GRAPH, MODULE),
        )
        self._expect_integrity(
            "INSERT INTO activations(activation_ref, execution_ref,"
            " graph_revision_ref, module_instance_revision_ref, trigger_delivery_ref,"
            " input_bindings_json, static_accounting_scope_ref, created_event_ref)"
            " VALUES ('activation:bad@2', ?, ?, ?, 'delivery:trigger@3', '[]',"
            " 'a', ?)",
            (EXECUTION, GRAPH, MODULE, ACTIVATION_EVENT),
        )
        self._expect_integrity(
            "INSERT INTO activations(activation_ref, execution_ref,"
            " graph_revision_ref, module_instance_revision_ref, trigger_delivery_ref,"
            " input_bindings_json, static_accounting_scope_ref, created_event_ref)"
            " VALUES ('activation:bad@3', 'execution:missing', ?, ?,"
            " 'delivery:trigger@4', '[]', 'a', 'event:activation@4')",
            (GRAPH, MODULE),
        )

    def test_delivery_bindings_foreign_key(self) -> None:
        self.conn.execute(
            "INSERT INTO delivery_bindings(delivery_ref, packet_ref,"
            " graph_revision_ref, edge_ref, target_port_ref, activation_ref)"
            " VALUES ('db:probe@1', ?, ?, ?, 'in', ?)",
            (PACKET, GRAPH, EDGE, ACTIVATION),
        )
        self._expect_integrity(
            "INSERT INTO delivery_bindings(delivery_ref, packet_ref,"
            " graph_revision_ref, edge_ref, target_port_ref, activation_ref)"
            " VALUES ('db:bad@1', ?, ?, ?, 'in', 'activation:missing')",
            (PACKET, GRAPH, EDGE),
        )

    def test_activation_created_events_check_unique_and_fk(self) -> None:
        self._expect_integrity(
            "INSERT INTO activation_created_events(created_event_ref,"
            " activation_ref, event_kind) VALUES ('event:bad@1', ?, 'OTHER')",
            (ACTIVATION,),
        )
        self._expect_integrity(
            "INSERT INTO activation_created_events(created_event_ref,"
            " activation_ref, event_kind) VALUES ('event:bad@2', ?,"
            " 'ActivationCreated')",
            (ACTIVATION,),
        )
        self._expect_integrity(
            "INSERT INTO activation_created_events(created_event_ref,"
            " activation_ref, event_kind) VALUES ('event:bad@3',"
            " 'activation:missing', 'ActivationCreated')"
        )

    # ------------------------------------------------------------------
    # Run / Attempt schema
    # ------------------------------------------------------------------

    def test_runs_checks_unique_and_foreign_key(self) -> None:
        self._expect_integrity(
            "INSERT INTO runs(run_ref, activation_ref, execution_ref,"
            " current_attempt_seq, fencing_generation, state)"
            " VALUES ('run:bad@1', 'activation:schema@2', ?, 0, 1, 'OPEN')",
            (EXECUTION,),
        )
        self._expect_integrity(
            "INSERT INTO runs(run_ref, activation_ref, execution_ref,"
            " current_attempt_seq, fencing_generation, state)"
            " VALUES ('run:bad@2', 'activation:schema@2', ?, 1, 0, 'OPEN')",
            (EXECUTION,),
        )
        self._expect_integrity(
            "INSERT INTO runs(run_ref, activation_ref, execution_ref,"
            " current_attempt_seq, fencing_generation, state)"
            " VALUES ('run:bad@3', ?, ?, 1, 1, 'OPEN')",
            (ACTIVATION, EXECUTION),
        )
        self._expect_integrity(
            "INSERT INTO runs(run_ref, activation_ref, execution_ref,"
            " current_attempt_seq, fencing_generation, state)"
            " VALUES ('run:bad@4', 'activation:schema@2', 'execution:missing',"
            " 1, 1, 'OPEN')"
        )

    def test_run_attempts_checks_unique_and_foreign_key(self) -> None:
        self._insert_attempt(seq=2, token="token:attempt@2")
        self._expect_integrity(
            "INSERT INTO run_attempts(run_ref, attempt_seq, fencing_token, state)"
            " VALUES (?, 0, 'token:attempt@3', 'CREATED')",
            (RUN,),
        )
        self._expect_integrity(
            "INSERT INTO run_attempts(run_ref, attempt_seq, fencing_token, state)"
            " VALUES (?, 3, '', 'CREATED')",
            (RUN,),
        )
        self._expect_integrity(
            "INSERT INTO run_attempts(run_ref, attempt_seq, fencing_token, state)"
            " VALUES (?, 4, 'token:attempt@4', 'OPEN')",
            (RUN,),
        )
        self._expect_integrity(
            "INSERT INTO run_attempts(run_ref, attempt_seq, fencing_token, state)"
            " VALUES (?, 5, 'token:attempt@2', 'CREATED')",
            (RUN,),
        )
        self._expect_integrity(
            "INSERT INTO run_attempts(run_ref, attempt_seq, fencing_token, state)"
            " VALUES ('run:missing', 1, 'token:attempt@5', 'CREATED')"
        )

    def test_run_attempt_state_transition_trigger(self) -> None:
        valid = [
            ("CREATED", "ACTIVE"),
            ("CREATED", "FAILED"),
            ("CREATED", "REPLACED"),
            ("ACTIVE", "SUCCEEDED"),
            ("ACTIVE", "FAILED"),
            ("ACTIVE", "REPLACED"),
        ]
        for old, new in valid:
            seq = self._new_attempt(state=old)
            with self.subTest(transition=f"{old}->{new}"):
                self.conn.execute(
                    "UPDATE run_attempts SET state = ?"
                    " WHERE run_ref = ? AND attempt_seq = ?",
                    (new, RUN, seq),
                )
                self.assertEqual(new, self._attempt_state(seq))

        for state in ("CREATED", "ACTIVE", "SUCCEEDED", "FAILED", "REPLACED"):
            seq = self._new_attempt(state=state)
            with self.subTest(noop=state):
                self.conn.execute(
                    "UPDATE run_attempts SET state = ?"
                    " WHERE run_ref = ? AND attempt_seq = ?",
                    (state, RUN, seq),
                )
                self.assertEqual(state, self._attempt_state(seq))

        invalid = [
            ("CREATED", "SUCCEEDED"),
            ("ACTIVE", "CREATED"),
            ("SUCCEEDED", "ACTIVE"),
            ("SUCCEEDED", "FAILED"),
            ("FAILED", "ACTIVE"),
            ("REPLACED", "ACTIVE"),
        ]
        for old, new in invalid:
            seq = self._new_attempt(state=old)
            with self.subTest(transition=f"{old}->{new}"):
                self._expect_integrity(
                    "UPDATE run_attempts SET state = ?"
                    " WHERE run_ref = ? AND attempt_seq = ?",
                    (new, RUN, seq),
                )

    def test_run_authority_counter_transition_trigger(self) -> None:
        # no-op passes
        self.conn.execute(
            "UPDATE runs SET current_attempt_seq = 1, fencing_generation = 1"
            " WHERE run_ref = ?",
            (RUN,),
        )
        # equal positive delta passes
        self.conn.execute(
            "UPDATE runs SET current_attempt_seq = 2, fencing_generation = 2"
            " WHERE run_ref = ?",
            (RUN,),
        )
        self.assertEqual((2, 2), self._run_counters())

        self._expect_integrity(
            "UPDATE runs SET current_attempt_seq = 3 WHERE run_ref = ?", (RUN,)
        )
        self._expect_integrity(
            "UPDATE runs SET fencing_generation = 3 WHERE run_ref = ?", (RUN,)
        )
        self._expect_integrity(
            "UPDATE runs SET current_attempt_seq = 4, fencing_generation = 3"
            " WHERE run_ref = ?",
            (RUN,),
        )
        self._expect_integrity(
            "UPDATE runs SET current_attempt_seq = 1, fencing_generation = 1"
            " WHERE run_ref = ?",
            (RUN,),
        )
        self.assertEqual((2, 2), self._run_counters())

    # ------------------------------------------------------------------
    # Attempt execution schema
    # ------------------------------------------------------------------

    def test_durable_values_not_null(self) -> None:
        self.conn.execute(
            "INSERT INTO durable_values(value_ref, value_json) VALUES ('v:probe', '{}')"
        )
        self._expect_integrity(
            "INSERT INTO durable_values(value_ref, value_json) VALUES ('v:bad', NULL)"
        )

    def test_run_terminal_events_check_unique_and_fk(self) -> None:
        self.conn.execute(
            "INSERT INTO run_terminal_events(event_ref, execution_ref,"
            " activation_ref, run_ref, attempt_seq, event_kind)"
            " VALUES ('rte:probe@1', ?, ?, ?, 1, 'RunSucceeded')",
            (EXECUTION, ACTIVATION, RUN),
        )
        self._expect_integrity(
            "INSERT INTO run_terminal_events(event_ref, execution_ref,"
            " activation_ref, run_ref, attempt_seq, event_kind)"
            " VALUES ('rte:bad@1', ?, ?, ?, 1, 'OTHER')",
            (EXECUTION, ACTIVATION, RUN),
        )
        self._expect_integrity(
            "INSERT INTO run_terminal_events(event_ref, execution_ref,"
            " activation_ref, run_ref, attempt_seq, event_kind)"
            " VALUES ('rte:bad@2', ?, ?, ?, 1, 'RunSucceeded')",
            (EXECUTION, ACTIVATION, RUN),
        )
        self._expect_integrity(
            "INSERT INTO run_terminal_events(event_ref, execution_ref,"
            " activation_ref, run_ref, attempt_seq, event_kind)"
            " VALUES ('rte:bad@3', ?, ?, 'run:missing', 1, 'RunSucceeded')",
            (EXECUTION, ACTIVATION),
        )
        self._expect_integrity(
            "INSERT INTO run_terminal_events(event_ref, execution_ref,"
            " activation_ref, run_ref, attempt_seq, event_kind)"
            " VALUES ('rte:bad@4', ?, ?, ?, 99, 'RunSucceeded')",
            (EXECUTION, ACTIVATION, RUN),
        )

    # ------------------------------------------------------------------
    # Capability schema
    # ------------------------------------------------------------------

    def test_capability_types_primary_key(self) -> None:
        self._expect_integrity(
            "INSERT INTO capability_types(capability_type_ref, version,"
            " contract_json) VALUES (?, ?, '{}')",
            (CAP_TYPE, CAP_VERSION),
        )

    def test_capability_grants_checks_and_fk(self) -> None:
        self._insert_capability_grant(
            grant_ref="grant:schema@2", state="REVOKED"
        )
        self._expect_integrity(
            "INSERT INTO capability_grants(grant_ref, capability_type_ref,"
            " capability_type_version, execution_ref, activation_ref, run_ref,"
            " attempt_seq, fencing_token, fencing_generation, scope_json,"
            " issued_by, policy_decision_ref, issued_at, not_before, expires_at,"
            " state)"
            " VALUES ('grant:bad@1', ?, ?, ?, ?, ?, 0, 'tk1', 1, '{}', 'i',"
            " NULL, 1, NULL, NULL, 'ACTIVE')",
            (CAP_TYPE, CAP_VERSION, EXECUTION, ACTIVATION, RUN),
        )
        self._expect_integrity(
            "INSERT INTO capability_grants(grant_ref, capability_type_ref,"
            " capability_type_version, execution_ref, activation_ref, run_ref,"
            " attempt_seq, fencing_token, fencing_generation, scope_json,"
            " issued_by, policy_decision_ref, issued_at, not_before, expires_at,"
            " state)"
            " VALUES ('grant:bad@2', ?, ?, ?, ?, ?, 1, '', 1, '{}', 'i',"
            " NULL, 1, NULL, NULL, 'ACTIVE')",
            (CAP_TYPE, CAP_VERSION, EXECUTION, ACTIVATION, RUN),
        )
        self._expect_integrity(
            "INSERT INTO capability_grants(grant_ref, capability_type_ref,"
            " capability_type_version, execution_ref, activation_ref, run_ref,"
            " attempt_seq, fencing_token, fencing_generation, scope_json,"
            " issued_by, policy_decision_ref, issued_at, not_before, expires_at,"
            " state)"
            " VALUES ('grant:bad@3', ?, ?, ?, ?, ?, 1, 'tk3', 0, '{}', 'i',"
            " NULL, 1, NULL, NULL, 'ACTIVE')",
            (CAP_TYPE, CAP_VERSION, EXECUTION, ACTIVATION, RUN),
        )
        self._expect_integrity(
            "INSERT INTO capability_grants(grant_ref, capability_type_ref,"
            " capability_type_version, execution_ref, activation_ref, run_ref,"
            " attempt_seq, fencing_token, fencing_generation, scope_json,"
            " issued_by, policy_decision_ref, issued_at, not_before, expires_at,"
            " state)"
            " VALUES ('grant:bad@4', ?, ?, ?, ?, ?, 1, 'tk4', 1, '{}', 'i',"
            " NULL, 1, NULL, NULL, 'OTHER')",
            (CAP_TYPE, CAP_VERSION, EXECUTION, ACTIVATION, RUN),
        )
        self._expect_integrity(
            "INSERT INTO capability_grants(grant_ref, capability_type_ref,"
            " capability_type_version, execution_ref, activation_ref, run_ref,"
            " attempt_seq, fencing_token, fencing_generation, scope_json,"
            " issued_by, policy_decision_ref, issued_at, not_before, expires_at,"
            " state)"
            " VALUES ('grant:bad@5', 'cap:missing', '1', ?, ?, ?, 1, 'tk5', 1,"
            " '{}', 'i', NULL, 1, NULL, NULL, 'ACTIVE')",
            (EXECUTION, ACTIVATION, RUN),
        )
        self._expect_integrity(
            "INSERT INTO capability_grants(grant_ref, capability_type_ref,"
            " capability_type_version, execution_ref, activation_ref, run_ref,"
            " attempt_seq, fencing_token, fencing_generation, scope_json,"
            " issued_by, policy_decision_ref, issued_at, not_before, expires_at,"
            " state)"
            " VALUES ('grant:bad@6', ?, ?, ?, ?, ?, 99, 'tk6', 1, '{}', 'i',"
            " NULL, 1, NULL, NULL, 'ACTIVE')",
            (CAP_TYPE, CAP_VERSION, EXECUTION, ACTIVATION, RUN),
        )

    def test_capability_grant_immutable_fields_trigger(self) -> None:
        immutable_changes = [
            ("grant_ref", "grant:changed"),
            ("capability_type_ref", "cap:changed"),
            ("capability_type_version", "99"),
            ("execution_ref", "execution:changed"),
            ("activation_ref", "activation:changed"),
            ("run_ref", "run:changed"),
            ("attempt_seq", 99),
            ("fencing_token", "token:changed"),
            ("fencing_generation", 99),
            ("scope_json", '{"changed": true}'),
            ("issued_by", "issuer:changed"),
            ("policy_decision_ref", "policy:changed"),
            ("issued_at", 999),
            ("not_before", 999),
            ("expires_at", 999),
        ]
        for column, value in immutable_changes:
            with self.subTest(column=column):
                self._expect_integrity(
                    f"UPDATE capability_grants SET {column} = ? WHERE grant_ref = ?",
                    (value, self._grant),
                )
        # state is the single mutable column; a legal transition still succeeds
        self.conn.execute(
            "UPDATE capability_grants SET state = 'REVOKED' WHERE grant_ref = ?",
            (self._grant,),
        )

    def test_capability_grant_state_transition_trigger(self) -> None:
        for new in ("REVOKED", "EXPIRED"):
            grant = self._insert_capability_grant(grant_ref=f"grant:t:{new}", state="ACTIVE")
            with self.subTest(transition=f"ACTIVE->{new}"):
                self.conn.execute(
                    "UPDATE capability_grants SET state = ? WHERE grant_ref = ?",
                    (new, grant),
                )
        for state in ("ACTIVE", "REVOKED", "EXPIRED"):
            grant = self._insert_capability_grant(grant_ref=f"grant:n:{state}", state=state)
            with self.subTest(noop=state):
                self.conn.execute(
                    "UPDATE capability_grants SET state = ? WHERE grant_ref = ?",
                    (state, grant),
                )
        invalid = [
            ("REVOKED", "ACTIVE"),
            ("REVOKED", "EXPIRED"),
            ("EXPIRED", "ACTIVE"),
            ("EXPIRED", "REVOKED"),
        ]
        for old, new in invalid:
            grant = self._insert_capability_grant(grant_ref=f"grant:i:{old}{new}", state=old)
            with self.subTest(transition=f"{old}->{new}"):
                self._expect_integrity(
                    "UPDATE capability_grants SET state = ? WHERE grant_ref = ?",
                    (new, grant),
                )

    # ------------------------------------------------------------------
    # Resource schema
    # ------------------------------------------------------------------

    def test_resources_state_check_unique_and_not_null(self) -> None:
        self._insert_resource(resource_ref="resource:schema@9", state="PROVISIONING")
        self._expect_integrity(
            "INSERT INTO resources(resource_ref, resource_type, resource_owner_ref,"
            " scope_json, state, external_ref, provenance_json)"
            " VALUES ('resource:bad@1', 't', 'o', '{}', 'MISSING', 'ext:bad@1', '{}')"
        )
        self._expect_integrity(
            "INSERT INTO resources(resource_ref, resource_type, resource_owner_ref,"
            " scope_json, state, external_ref, provenance_json)"
            " VALUES ('resource:bad@2', 't', 'o', '{}', 'AVAILABLE', ?, '{}')",
            (f"external:{self._resource}",),
        )

    def test_resource_leases_checks_and_fk(self) -> None:
        self._insert_resource_lease(lease_ref="lease:schema@9", state="RELEASED")
        self._expect_integrity(
            "INSERT INTO resource_leases(lease_ref, resource_ref, lease_holder_ref,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, issued_at, expires_at, state)"
            " VALUES ('lease:bad@1', ?, 'h', ?, ?, ?, 0, 'tk', 1, 1, NULL,"
            " 'ACTIVE')",
            (self._resource, EXECUTION, ACTIVATION, RUN),
        )
        self._expect_integrity(
            "INSERT INTO resource_leases(lease_ref, resource_ref, lease_holder_ref,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, issued_at, expires_at, state)"
            " VALUES ('lease:bad@2', ?, 'h', ?, ?, ?, 1, '', 1, 1, NULL,"
            " 'ACTIVE')",
            (self._resource, EXECUTION, ACTIVATION, RUN),
        )
        self._expect_integrity(
            "INSERT INTO resource_leases(lease_ref, resource_ref, lease_holder_ref,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, issued_at, expires_at, state)"
            " VALUES ('lease:bad@3', ?, 'h', ?, ?, ?, 1, 'tk3', 1, 1, NULL,"
            " 'OTHER')",
            (self._resource, EXECUTION, ACTIVATION, RUN),
        )
        self._expect_integrity(
            "INSERT INTO resource_leases(lease_ref, resource_ref, lease_holder_ref,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, issued_at, expires_at, state)"
            " VALUES ('lease:bad@4', 'resource:missing', 'h', ?, ?, ?, 1, 'tk4',"
            " 1, 1, NULL, 'ACTIVE')",
            (EXECUTION, ACTIVATION, RUN),
        )
        self._expect_integrity(
            "INSERT INTO resource_leases(lease_ref, resource_ref, lease_holder_ref,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, issued_at, expires_at, state)"
            " VALUES ('lease:bad@5', ?, 'h', ?, ?, 'run:missing', 1, 'tk5', 1,"
            " 1, NULL, 'ACTIVE')",
            (self._resource, EXECUTION, ACTIVATION),
        )

    def test_resource_immutable_fields_trigger(self) -> None:
        immutable_changes = [
            ("resource_ref", "resource:changed"),
            ("resource_type", "type:changed"),
            ("resource_owner_ref", "owner:changed"),
            ("scope_json", '{"changed": true}'),
            ("external_ref", "external:changed"),
            ("provenance_json", '{"changed": true}'),
        ]
        for column, value in immutable_changes:
            with self.subTest(column=column):
                self._expect_integrity(
                    f"UPDATE resources SET {column} = ? WHERE resource_ref = ?",
                    (value, self._resource),
                )
        self.conn.execute(
            "UPDATE resources SET state = 'DESTROYING' WHERE resource_ref = ?",
            (self._resource,),
        )

    def test_resource_lease_immutable_fields_trigger(self) -> None:
        immutable_changes = [
            ("lease_ref", "lease:changed"),
            ("resource_ref", "resource:changed"),
            ("lease_holder_ref", "holder:changed"),
            ("execution_ref", "execution:changed"),
            ("activation_ref", "activation:changed"),
            ("run_ref", "run:changed"),
            ("attempt_seq", 99),
            ("fencing_token", "token:changed"),
            ("fencing_generation", 99),
            ("issued_at", 999),
            ("expires_at", 999),
        ]
        for column, value in immutable_changes:
            with self.subTest(column=column):
                self._expect_integrity(
                    f"UPDATE resource_leases SET {column} = ? WHERE lease_ref = ?",
                    (value, self._lease),
                )
        self.conn.execute(
            "UPDATE resource_leases SET state = 'RELEASED' WHERE lease_ref = ?",
            (self._lease,),
        )

    def test_resource_state_transition_trigger(self) -> None:
        valid = [
            ("PROVISIONING", "AVAILABLE"),
            ("PROVISIONING", "UNKNOWN"),
            ("AVAILABLE", "DESTROYING"),
            ("AVAILABLE", "UNKNOWN"),
            ("DESTROYING", "DESTROYED"),
            ("DESTROYING", "UNKNOWN"),
        ]
        for old, new in valid:
            resource = self._insert_resource(state=old)
            with self.subTest(transition=f"{old}->{new}"):
                self.conn.execute(
                    "UPDATE resources SET state = ? WHERE resource_ref = ?",
                    (new, resource),
                )
        for state in ("PROVISIONING", "AVAILABLE", "DESTROYING", "DESTROYED", "UNKNOWN"):
            resource = self._insert_resource(state=state)
            with self.subTest(noop=state):
                self.conn.execute(
                    "UPDATE resources SET state = ? WHERE resource_ref = ?",
                    (state, resource),
                )
        invalid = [
            ("AVAILABLE", "PROVISIONING"),
            ("DESTROYED", "AVAILABLE"),
            ("UNKNOWN", "AVAILABLE"),
            ("PROVISIONING", "DESTROYING"),
        ]
        for old, new in invalid:
            resource = self._insert_resource(state=old)
            with self.subTest(transition=f"{old}->{new}"):
                self._expect_integrity(
                    "UPDATE resources SET state = ? WHERE resource_ref = ?",
                    (new, resource),
                )

    def test_resource_lease_state_transition_trigger(self) -> None:
        valid = ["REVOKE_REQUESTED", "RELEASED", "EXPIRED", "UNKNOWN"]
        for new in valid:
            lease = self._insert_resource_lease(state="ACTIVE")
            with self.subTest(transition=f"ACTIVE->{new}"):
                self.conn.execute(
                    "UPDATE resource_leases SET state = ? WHERE lease_ref = ?",
                    (new, lease),
                )
        for state in ("ACTIVE", "REVOKE_REQUESTED", "RELEASED", "EXPIRED", "UNKNOWN"):
            lease = self._insert_resource_lease(state=state)
            with self.subTest(noop=state):
                self.conn.execute(
                    "UPDATE resource_leases SET state = ? WHERE lease_ref = ?",
                    (state, lease),
                )
        invalid = [
            ("RELEASED", "ACTIVE"),
            ("REVOKE_REQUESTED", "ACTIVE"),
            ("EXPIRED", "ACTIVE"),
            ("UNKNOWN", "ACTIVE"),
        ]
        for old, new in invalid:
            lease = self._insert_resource_lease(state=old)
            with self.subTest(transition=f"{old}->{new}"):
                self._expect_integrity(
                    "UPDATE resource_leases SET state = ? WHERE lease_ref = ?",
                    (new, lease),
                )

    # ------------------------------------------------------------------
    # Effect schema
    # ------------------------------------------------------------------

    def test_effect_operations_checks_unique_and_fk(self) -> None:
        self._insert_effect()
        # dispatch pair must be all-null or all-set
        self._expect_integrity(
            "INSERT INTO effect_operations(operation_ref, effect_class,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, capability_grant_ref, resource_ref,"
            " resource_lease_ref, target_ref, payload_json, payload_hash,"
            " caused_by_ref, state, prepared_at, dispatch_admission_ref,"
            " dispatch_admitted_at, completion_evidence_json, fence_evidence_json)"
            " VALUES ('op:bad@1', 'c', ?, ?, ?, 1, 'tk1', 1, ?, ?, ?, 't1',"
            " '{}', 'h', 'c', 'PREPARED', 1, 'adm:1', NULL, NULL, NULL)",
            (EXECUTION, ACTIVATION, RUN, self._grant, self._resource, self._lease),
        )
        # ACTIVE requires dispatch admission
        self._expect_integrity(
            "INSERT INTO effect_operations(operation_ref, effect_class,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, capability_grant_ref, resource_ref,"
            " resource_lease_ref, target_ref, payload_json, payload_hash,"
            " caused_by_ref, state, prepared_at, dispatch_admission_ref,"
            " dispatch_admitted_at, completion_evidence_json, fence_evidence_json)"
            " VALUES ('op:bad@2', 'c', ?, ?, ?, 1, 'tk2', 1, ?, ?, ?, 't2',"
            " '{}', 'h', 'c', 'ACTIVE', 1, NULL, NULL, NULL, NULL)",
            (EXECUTION, ACTIVATION, RUN, self._grant, self._resource, self._lease),
        )
        # COMPLETED requires admission + completion evidence
        self._expect_integrity(
            "INSERT INTO effect_operations(operation_ref, effect_class,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, capability_grant_ref, resource_ref,"
            " resource_lease_ref, target_ref, payload_json, payload_hash,"
            " caused_by_ref, state, prepared_at, dispatch_admission_ref,"
            " dispatch_admitted_at, completion_evidence_json, fence_evidence_json)"
            " VALUES ('op:bad@3', 'c', ?, ?, ?, 1, 'tk3', 1, ?, ?, ?, 't3',"
            " '{}', 'h', 'c', 'COMPLETED', 1, 'adm:3', 1, NULL, NULL)",
            (EXECUTION, ACTIVATION, RUN, self._grant, self._resource, self._lease),
        )
        # FENCED requires fence evidence
        self._expect_integrity(
            "INSERT INTO effect_operations(operation_ref, effect_class,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, capability_grant_ref, resource_ref,"
            " resource_lease_ref, target_ref, payload_json, payload_hash,"
            " caused_by_ref, state, prepared_at, dispatch_admission_ref,"
            " dispatch_admitted_at, completion_evidence_json, fence_evidence_json)"
            " VALUES ('op:bad@4', 'c', ?, ?, ?, 1, 'tk4', 1, ?, ?, ?, 't4',"
            " '{}', 'h', 'c', 'FENCED', 1, NULL, NULL, NULL, NULL)",
            (EXECUTION, ACTIVATION, RUN, self._grant, self._resource, self._lease),
        )
        # UNIQUE target_ref
        first_target = "target:dup@1"
        self._insert_effect(target_ref=first_target)
        self._expect_integrity(
            "INSERT INTO effect_operations(operation_ref, effect_class,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, capability_grant_ref, resource_ref,"
            " resource_lease_ref, target_ref, payload_json, payload_hash,"
            " caused_by_ref, state, prepared_at, dispatch_admission_ref,"
            " dispatch_admitted_at, completion_evidence_json, fence_evidence_json)"
            " VALUES ('op:bad@5', 'c', ?, ?, ?, 1, 'tk5', 1, ?, ?, ?, ?, '{}',"
            " 'h', 'c', 'PREPARED', 1, NULL, NULL, NULL, NULL)",
            (
                EXECUTION,
                ACTIVATION,
                RUN,
                self._grant,
                self._resource,
                self._lease,
                first_target,
            ),
        )
        # UNIQUE dispatch_admission_ref
        self._insert_effect(admitted=True, admission_ref="adm:dup@1")
        self._expect_integrity(
            "INSERT INTO effect_operations(operation_ref, effect_class,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, capability_grant_ref, resource_ref,"
            " resource_lease_ref, target_ref, payload_json, payload_hash,"
            " caused_by_ref, state, prepared_at, dispatch_admission_ref,"
            " dispatch_admitted_at, completion_evidence_json, fence_evidence_json)"
            " VALUES ('op:bad@6', 'c', ?, ?, ?, 1, 'tk6', 1, ?, ?, ?, 't6',"
            " '{}', 'h', 'c', 'PREPARED', 1, 'adm:dup@1', 1, NULL, NULL)",
            (EXECUTION, ACTIVATION, RUN, self._grant, self._resource, self._lease),
        )
        # FK capability_grant_ref
        self._expect_integrity(
            "INSERT INTO effect_operations(operation_ref, effect_class,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, capability_grant_ref, resource_ref,"
            " resource_lease_ref, target_ref, payload_json, payload_hash,"
            " caused_by_ref, state, prepared_at, dispatch_admission_ref,"
            " dispatch_admitted_at, completion_evidence_json, fence_evidence_json)"
            " VALUES ('op:bad@7', 'c', ?, ?, ?, 1, 'tk7', 1, 'grant:missing',"
            " ?, ?, 't7', '{}', 'h', 'c', 'PREPARED', 1, NULL, NULL, NULL, NULL)",
            (EXECUTION, ACTIVATION, RUN, self._resource, self._lease),
        )
        # FK (run_ref, attempt_seq)
        self._expect_integrity(
            "INSERT INTO effect_operations(operation_ref, effect_class,"
            " execution_ref, activation_ref, run_ref, attempt_seq, fencing_token,"
            " fencing_generation, capability_grant_ref, resource_ref,"
            " resource_lease_ref, target_ref, payload_json, payload_hash,"
            " caused_by_ref, state, prepared_at, dispatch_admission_ref,"
            " dispatch_admitted_at, completion_evidence_json, fence_evidence_json)"
            " VALUES ('op:bad@8', 'c', ?, ?, 'run:missing', 1, 'tk8', 1, ?,"
            " ?, ?, 't8', '{}', 'h', 'c', 'PREPARED', 1, NULL, NULL, NULL, NULL)",
            (EXECUTION, ACTIVATION, self._grant, self._resource, self._lease),
        )

    def test_effect_operation_immutable_fields_trigger(self) -> None:
        op = self._insert_effect()
        immutable_changes = [
            ("operation_ref", "operation:changed"),
            ("effect_class", "class:changed"),
            ("execution_ref", "execution:changed"),
            ("activation_ref", "activation:changed"),
            ("run_ref", "run:changed"),
            ("attempt_seq", 99),
            ("fencing_token", "token:changed"),
            ("fencing_generation", 99),
            ("capability_grant_ref", "grant:changed"),
            ("resource_ref", "resource:changed"),
            ("resource_lease_ref", "lease:changed"),
            ("target_ref", "target:changed"),
            ("payload_json", '{"changed": true}'),
            ("payload_hash", "hash:changed"),
            ("caused_by_ref", "cause:changed"),
            ("prepared_at", 999),
        ]
        for column, value in immutable_changes:
            with self.subTest(column=column):
                self._expect_integrity(
                    f"UPDATE effect_operations SET {column} = ?"
                    " WHERE operation_ref = ?",
                    (value, op),
                )

    def test_effect_dispatch_admission_guards(self) -> None:
        # positive: admit while still PREPARED
        op = self._insert_effect()
        self.conn.execute(
            "UPDATE effect_operations SET dispatch_admission_ref = 'adm:new',"
            " dispatch_admitted_at = 200 WHERE operation_ref = ?",
            (op,),
        )
        # once admitted, the admission is immutable
        self._expect_integrity(
            "UPDATE effect_operations SET dispatch_admission_ref = 'adm:other'"
            " WHERE operation_ref = ?",
            (op,),
        )
        self._expect_integrity(
            "UPDATE effect_operations SET dispatch_admitted_at = 300"
            " WHERE operation_ref = ?",
            (op,),
        )
        # admission requires PREPARED state
        unknown = self._insert_effect(state="UNKNOWN")
        self._expect_integrity(
            "UPDATE effect_operations SET dispatch_admission_ref = 'adm:late',"
            " dispatch_admitted_at = 200 WHERE operation_ref = ?",
            (unknown,),
        )

    def test_effect_completion_and_fence_evidence_immutable(self) -> None:
        completed = self._insert_effect(state="COMPLETED", admitted=True, completion=True)
        self._expect_integrity(
            "UPDATE effect_operations SET completion_evidence_json = '{\"x\": 1}'"
            " WHERE operation_ref = ?",
            (completed,),
        )
        fenced = self._insert_effect(state="FENCED", fence=True)
        self._expect_integrity(
            "UPDATE effect_operations SET fence_evidence_json = '{\"x\": 1}'"
            " WHERE operation_ref = ?",
            (fenced,),
        )

    def test_effect_active_requires_admission_trigger(self) -> None:
        op = self._insert_effect()  # PREPARED, no admission
        self._expect_integrity(
            "UPDATE effect_operations SET state = 'ACTIVE' WHERE operation_ref = ?",
            (op,),
        )

    def test_effect_operation_state_transition_trigger(self) -> None:
        # PREPARED -> ACTIVE requires admission set in a prior step
        admitted_prepared = self._insert_effect(admitted=True)
        self.conn.execute(
            "UPDATE effect_operations SET state = 'ACTIVE' WHERE operation_ref = ?",
            (admitted_prepared,),
        )
        # PREPARED -> FENCED sets fence evidence in the same update
        fenced_from_prepared = self._insert_effect()
        self.conn.execute(
            "UPDATE effect_operations SET state = 'FENCED',"
            " fence_evidence_json = '{\"fenced\": true}' WHERE operation_ref = ?",
            (fenced_from_prepared,),
        )
        # PREPARED -> UNKNOWN
        unknown_from_prepared = self._insert_effect()
        self.conn.execute(
            "UPDATE effect_operations SET state = 'UNKNOWN' WHERE operation_ref = ?",
            (unknown_from_prepared,),
        )
        # ACTIVE -> COMPLETED
        active = self._insert_effect(state="ACTIVE", admitted=True)
        self.conn.execute(
            "UPDATE effect_operations SET state = 'COMPLETED',"
            " completion_evidence_json = '{\"done\": true}' WHERE operation_ref = ?",
            (active,),
        )
        # ACTIVE -> REVOKE_REQUESTED
        active2 = self._insert_effect(state="ACTIVE", admitted=True)
        self.conn.execute(
            "UPDATE effect_operations SET state = 'REVOKE_REQUESTED'"
            " WHERE operation_ref = ?",
            (active2,),
        )
        # REVOKE_REQUESTED -> FENCED / COMPLETED / UNKNOWN
        rr_fence = self._insert_effect(state="REVOKE_REQUESTED", admitted=True)
        self.conn.execute(
            "UPDATE effect_operations SET state = 'FENCED',"
            " fence_evidence_json = '{\"fenced\": true}' WHERE operation_ref = ?",
            (rr_fence,),
        )
        rr_complete = self._insert_effect(state="REVOKE_REQUESTED", admitted=True)
        self.conn.execute(
            "UPDATE effect_operations SET state = 'COMPLETED',"
            " completion_evidence_json = '{\"done\": true}' WHERE operation_ref = ?",
            (rr_complete,),
        )
        rr_unknown = self._insert_effect(state="REVOKE_REQUESTED", admitted=True)
        self.conn.execute(
            "UPDATE effect_operations SET state = 'UNKNOWN' WHERE operation_ref = ?",
            (rr_unknown,),
        )
        # no-op
        for state in ("PREPARED", "ACTIVE", "REVOKE_REQUESTED", "FENCED", "COMPLETED", "UNKNOWN"):
            if state in ("ACTIVE", "REVOKE_REQUESTED"):
                op = self._insert_effect(state=state, admitted=True)
            elif state == "COMPLETED":
                op = self._insert_effect(state=state, admitted=True, completion=True)
            elif state == "FENCED":
                op = self._insert_effect(state=state, fence=True)
            else:
                op = self._insert_effect(state=state)
            with self.subTest(noop=state):
                self.conn.execute(
                    "UPDATE effect_operations SET state = ? WHERE operation_ref = ?",
                    (state, op),
                )
        # invalid transitions
        invalid = [
            ("PREPARED", "REVOKE_REQUESTED"),
            ("PREPARED", "COMPLETED"),
            ("ACTIVE", "PREPARED"),
            ("ACTIVE", "FENCED"),
            ("COMPLETED", "ACTIVE"),
            ("FENCED", "PREPARED"),
        ]
        for old, new in invalid:
            if old == "PREPARED":
                op = self._insert_effect(state=old)
            elif old == "ACTIVE":
                op = self._insert_effect(state=old, admitted=True)
            elif old == "COMPLETED":
                op = self._insert_effect(state=old, admitted=True, completion=True)
            elif old == "FENCED":
                op = self._insert_effect(state=old, fence=True)
            else:
                op = self._insert_effect(state=old)
            with self.subTest(transition=f"{old}->{new}"):
                self._expect_integrity(
                    "UPDATE effect_operations SET state = ? WHERE operation_ref = ?",
                    (new, op),
                )

    # ------------------------------------------------------------------
    # Budget schema
    # ------------------------------------------------------------------

    def _insert_budget_policy(
        self,
        ref: str = "budget-policy:probe@1",
        scope: str = SCOPE,
        effective_from: int = 100,
        effective_until: int | None = None,
    ) -> str:
        self.conn.execute(
            "INSERT INTO budget_policy_revisions(budget_policy_revision_ref,"
            " accounting_scope_ref, effective_from, effective_until,"
            " dimensions_json, enforcement_rules_json, created_by_ref,"
            " supersedes_ref) VALUES (?, ?, ?, ?, '[]', '[]', 'creator:probe', NULL)",
            (ref, scope, effective_from, effective_until),
        )
        return ref

    def _insert_budget_reservation(
        self,
        ref: str = "reservation:probe@1",
        request: str = "request:probe@1",
        scope: str = SCOPE,
        run: str = RUN,
        seq: int = 1,
        state: str = "REQUESTED",
        deny_reason: str | None = None,
    ) -> str:
        self.conn.execute(
            "INSERT INTO budget_reservations(reservation_ref, request_ref,"
            " activation_ref, run_ref, attempt_seq, accounting_scope_ref,"
            " graph_revision_ref, definition_anchor_ref, ancestry_snapshot_json,"
            " policy_revision_refs_json, estimate_ref, requested_dimensions_json,"
            " reserved_dimensions_json, committed_dimensions_json,"
            " released_dimensions_json, state, deny_reason_code, subject_refs_json,"
            " created_at, updated_at, caused_by_ref)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 'anchor:probe@1', '[]', '[]',"
            " 'estimate:probe', '[]', '[]', '[]', '[]', ?, ?, '[]', 100, 100,"
            " 'cause:probe')",
            (ref, request, ACTIVATION, run, seq, scope, GRAPH, state, deny_reason),
        )
        return ref

    def test_budget_policy_revisions_check_and_fk(self) -> None:
        self._insert_budget_policy(effective_until=101)
        self._expect_integrity(
            "INSERT INTO budget_policy_revisions(budget_policy_revision_ref,"
            " accounting_scope_ref, effective_from, effective_until,"
            " dimensions_json, enforcement_rules_json, created_by_ref,"
            " supersedes_ref) VALUES ('bp:bad@1', ?, 100, 100, '[]', '[]', 'c',"
            " NULL)",
            (SCOPE,),
        )
        self._expect_integrity(
            "INSERT INTO budget_policy_revisions(budget_policy_revision_ref,"
            " accounting_scope_ref, effective_from, effective_until,"
            " dimensions_json, enforcement_rules_json, created_by_ref,"
            " supersedes_ref) VALUES ('bp:bad@2', 'accounting:missing', 100, NULL,"
            " '[]', '[]', 'c', NULL)"
        )
        self._expect_integrity(
            "INSERT INTO budget_policy_revisions(budget_policy_revision_ref,"
            " accounting_scope_ref, effective_from, effective_until,"
            " dimensions_json, enforcement_rules_json, created_by_ref,"
            " supersedes_ref) VALUES ('bp:bad@3', ?, 100, NULL, '[]', '[]', 'c',"
            " 'bp:missing')",
            (SCOPE,),
        )

    def test_budget_policy_revision_immutable_trigger(self) -> None:
        self._insert_budget_policy()
        self._expect_integrity(
            "UPDATE budget_policy_revisions SET dimensions_json = '[\"x\"]'"
            " WHERE budget_policy_revision_ref = 'budget-policy:probe@1'"
        )

    def test_budget_reservations_checks_unique_and_fk(self) -> None:
        self._insert_budget_reservation()
        self._insert_budget_reservation(
            ref="reservation:probe@2", request="request:probe@2", state="RESERVED"
        )
        self._expect_integrity(
            "INSERT INTO budget_reservations(reservation_ref, request_ref,"
            " activation_ref, run_ref, attempt_seq, accounting_scope_ref,"
            " graph_revision_ref, definition_anchor_ref, ancestry_snapshot_json,"
            " policy_revision_refs_json, estimate_ref, requested_dimensions_json,"
            " reserved_dimensions_json, committed_dimensions_json,"
            " released_dimensions_json, state, deny_reason_code, subject_refs_json,"
            " created_at, updated_at, caused_by_ref)"
            " VALUES ('res:bad@1', 'req:bad@1', ?, ?, 0, ?, ?, 'a', '[]', '[]',"
            " 'e', '[]', '[]', '[]', '[]', 'REQUESTED', NULL, '[]', 1, 1, 'c')",
            (ACTIVATION, RUN, SCOPE, GRAPH),
        )
        self._expect_integrity(
            "INSERT INTO budget_reservations(reservation_ref, request_ref,"
            " activation_ref, run_ref, attempt_seq, accounting_scope_ref,"
            " graph_revision_ref, definition_anchor_ref, ancestry_snapshot_json,"
            " policy_revision_refs_json, estimate_ref, requested_dimensions_json,"
            " reserved_dimensions_json, committed_dimensions_json,"
            " released_dimensions_json, state, deny_reason_code, subject_refs_json,"
            " created_at, updated_at, caused_by_ref)"
            " VALUES ('res:bad@2', 'req:bad@2', ?, ?, 1, ?, ?, 'a', '[]', '[]',"
            " 'e', '[]', '[]', '[]', '[]', 'OTHER', NULL, '[]', 1, 1, 'c')",
            (ACTIVATION, RUN, SCOPE, GRAPH),
        )
        # DENIED requires deny_reason_code
        self._expect_integrity(
            "INSERT INTO budget_reservations(reservation_ref, request_ref,"
            " activation_ref, run_ref, attempt_seq, accounting_scope_ref,"
            " graph_revision_ref, definition_anchor_ref, ancestry_snapshot_json,"
            " policy_revision_refs_json, estimate_ref, requested_dimensions_json,"
            " reserved_dimensions_json, committed_dimensions_json,"
            " released_dimensions_json, state, deny_reason_code, subject_refs_json,"
            " created_at, updated_at, caused_by_ref)"
            " VALUES ('res:bad@3', 'req:bad@3', ?, ?, 1, ?, ?, 'a', '[]', '[]',"
            " 'e', '[]', '[]', '[]', '[]', 'DENIED', NULL, '[]', 1, 1, 'c')",
            (ACTIVATION, RUN, SCOPE, GRAPH),
        )
        # non-DENIED must not carry deny_reason_code
        self._expect_integrity(
            "INSERT INTO budget_reservations(reservation_ref, request_ref,"
            " activation_ref, run_ref, attempt_seq, accounting_scope_ref,"
            " graph_revision_ref, definition_anchor_ref, ancestry_snapshot_json,"
            " policy_revision_refs_json, estimate_ref, requested_dimensions_json,"
            " reserved_dimensions_json, committed_dimensions_json,"
            " released_dimensions_json, state, deny_reason_code, subject_refs_json,"
            " created_at, updated_at, caused_by_ref)"
            " VALUES ('res:bad@4', 'req:bad@4', ?, ?, 1, ?, ?, 'a', '[]', '[]',"
            " 'e', '[]', '[]', '[]', '[]', 'REQUESTED', 'X', '[]', 1, 1, 'c')",
            (ACTIVATION, RUN, SCOPE, GRAPH),
        )
        # positive DENIED with reason
        self._insert_budget_reservation(
            ref="reservation:denied@1",
            request="request:denied@1",
            state="DENIED",
            deny_reason="POLICY",
        )
        self._expect_integrity(
            "INSERT INTO budget_reservations(reservation_ref, request_ref,"
            " activation_ref, run_ref, attempt_seq, accounting_scope_ref,"
            " graph_revision_ref, definition_anchor_ref, ancestry_snapshot_json,"
            " policy_revision_refs_json, estimate_ref, requested_dimensions_json,"
            " reserved_dimensions_json, committed_dimensions_json,"
            " released_dimensions_json, state, deny_reason_code, subject_refs_json,"
            " created_at, updated_at, caused_by_ref)"
            " VALUES ('res:bad@5', 'request:probe@1', ?, ?, 1, ?, ?, 'a', '[]',"
            " '[]', 'e', '[]', '[]', '[]', '[]', 'REQUESTED', NULL, '[]', 1, 1,"
            " 'c')",
            (ACTIVATION, RUN, SCOPE, GRAPH),
        )
        self._expect_integrity(
            "INSERT INTO budget_reservations(reservation_ref, request_ref,"
            " activation_ref, run_ref, attempt_seq, accounting_scope_ref,"
            " graph_revision_ref, definition_anchor_ref, ancestry_snapshot_json,"
            " policy_revision_refs_json, estimate_ref, requested_dimensions_json,"
            " reserved_dimensions_json, committed_dimensions_json,"
            " released_dimensions_json, state, deny_reason_code, subject_refs_json,"
            " created_at, updated_at, caused_by_ref)"
            " VALUES ('res:bad@6', 'req:bad@6', ?, ?, 1, 'accounting:missing', ?,"
            " 'a', '[]', '[]', 'e', '[]', '[]', '[]', '[]', 'REQUESTED', NULL,"
            " '[]', 1, 1, 'c')",
            (ACTIVATION, RUN, GRAPH),
        )
        self._expect_integrity(
            "INSERT INTO budget_reservations(reservation_ref, request_ref,"
            " activation_ref, run_ref, attempt_seq, accounting_scope_ref,"
            " graph_revision_ref, definition_anchor_ref, ancestry_snapshot_json,"
            " policy_revision_refs_json, estimate_ref, requested_dimensions_json,"
            " reserved_dimensions_json, committed_dimensions_json,"
            " released_dimensions_json, state, deny_reason_code, subject_refs_json,"
            " created_at, updated_at, caused_by_ref)"
            " VALUES ('res:bad@7', 'req:bad@7', ?, 'run:missing', 1, ?, ?, 'a',"
            " '[]', '[]', 'e', '[]', '[]', '[]', '[]', 'REQUESTED', NULL, '[]',"
            " 1, 1, 'c')",
            (ACTIVATION, SCOPE, GRAPH),
        )

    def test_budget_reservation_identity_immutable_trigger(self) -> None:
        self._insert_budget_reservation()
        immutable_changes = [
            ("reservation_ref", "res:changed"),
            ("request_ref", "req:changed"),
            ("activation_ref", "activation:changed"),
            ("run_ref", "run:changed"),
            ("attempt_seq", 99),
            ("accounting_scope_ref", "accounting:changed"),
            ("graph_revision_ref", "graph:changed"),
            ("definition_anchor_ref", "anchor:changed"),
            ("ancestry_snapshot_json", '["changed"]'),
            ("policy_revision_refs_json", '["changed"]'),
            ("estimate_ref", "estimate:changed"),
            ("requested_dimensions_json", '["changed"]'),
            ("reserved_dimensions_json", '["changed"]'),
            ("subject_refs_json", '["changed"]'),
            ("caused_by_ref", "cause:changed"),
            ("created_at", 999),
        ]
        for column, value in immutable_changes:
            with self.subTest(column=column):
                self._expect_integrity(
                    f"UPDATE budget_reservations SET {column} = ?"
                    " WHERE reservation_ref = 'reservation:probe@1'",
                    (value,),
                )
        # mutable columns (committed/released dims, updated_at) are updatable
        self.conn.execute(
            "UPDATE budget_reservations SET committed_dimensions_json = '[\"c\"]',"
            " released_dimensions_json = '[\"r\"]', updated_at = 101"
            " WHERE reservation_ref = 'reservation:probe@1'"
        )

    def test_budget_reservation_state_transition_trigger(self) -> None:
        valid = [
            ("REQUESTED", "RESERVED"),
            ("REQUESTED", "DENIED"),
            ("RESERVED", "COMMITTED"),
            ("RESERVED", "RELEASED"),
            ("RESERVED", "RECONCILING"),
            ("RELEASED", "RECONCILING"),
            ("COMMITTED", "RECONCILING"),
            ("RECONCILING", "COMMITTED"),
            ("RECONCILING", "RELEASED"),
        ]
        for old, new in valid:
            ref = f"reservation:t:{old}:{new}"
            self._insert_budget_reservation(
                ref=ref, request=f"request:t:{old}:{new}", state=old
            )
            with self.subTest(transition=f"{old}->{new}"):
                if new == "DENIED":
                    self.conn.execute(
                        "UPDATE budget_reservations SET state = ?,"
                        " deny_reason_code = 'X' WHERE reservation_ref = ?",
                        (new, ref),
                    )
                else:
                    self.conn.execute(
                        "UPDATE budget_reservations SET state = ?"
                        " WHERE reservation_ref = ?",
                        (new, ref),
                    )
        for state in ("REQUESTED", "RESERVED", "DENIED", "RECONCILING", "COMMITTED", "RELEASED"):
            ref = f"reservation:n:{state}"
            self._insert_budget_reservation(
                ref=ref,
                request=f"request:n:{state}",
                state=state,
                deny_reason="X" if state == "DENIED" else None,
            )
            with self.subTest(noop=state):
                self.conn.execute(
                    "UPDATE budget_reservations SET state = ? WHERE reservation_ref = ?",
                    (state, ref),
                )
        invalid = [
            ("REQUESTED", "COMMITTED"),
            ("RESERVED", "DENIED"),
            ("COMMITTED", "REQUESTED"),
            ("RELEASED", "REQUESTED"),
            ("DENIED", "RESERVED"),
        ]
        for old, new in invalid:
            ref = f"reservation:i:{old}:{new}"
            self._insert_budget_reservation(
                ref=ref,
                request=f"request:i:{old}:{new}",
                state=old,
                deny_reason="X" if old == "DENIED" else None,
            )
            with self.subTest(transition=f"{old}->{new}"):
                self._expect_integrity(
                    "UPDATE budget_reservations SET state = ?"
                    " WHERE reservation_ref = ?",
                    (new, ref),
                )

    def test_budget_scope_exposure_checks_and_fk(self) -> None:
        self.conn.execute(
            "INSERT INTO budget_scope_exposure(accounting_scope_ref, dimension_ref,"
            " reserved_amount, committed_amount) VALUES (?, 'dim:probe', 0, 0)",
            (SCOPE,),
        )
        self._expect_integrity(
            "INSERT INTO budget_scope_exposure(accounting_scope_ref, dimension_ref,"
            " reserved_amount, committed_amount) VALUES (?, 'dim:bad@1', -1, 0)",
            (SCOPE,),
        )
        self._expect_integrity(
            "INSERT INTO budget_scope_exposure(accounting_scope_ref, dimension_ref,"
            " reserved_amount, committed_amount) VALUES (?, 'dim:bad@2', 0, -1)",
            (SCOPE,),
        )
        self._expect_integrity(
            "INSERT INTO budget_scope_exposure(accounting_scope_ref, dimension_ref,"
            " reserved_amount, committed_amount) VALUES ('accounting:missing',"
            " 'dim:bad@3', 0, 0)"
        )


if __name__ == "__main__":
    unittest.main()
