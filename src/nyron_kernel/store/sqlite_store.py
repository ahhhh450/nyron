"""Minimal SQLite state store for Nyron's current canonical facts."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class SQLiteStore:
    """Own one SQLite connection and its explicit write transactions."""

    def __init__(self, database: str | Path = ":memory:") -> None:
        self.connection = sqlite3.connect(str(database), isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS module_definitions (
                module_ref TEXT NOT NULL,
                version TEXT NOT NULL,
                contract_json TEXT NOT NULL,
                PRIMARY KEY (module_ref, version)
            );

            CREATE TABLE IF NOT EXISTS graph_revisions (
                graph_revision_ref TEXT PRIMARY KEY,
                contract_json TEXT NOT NULL,
                executable INTEGER NOT NULL CHECK (executable IN (0, 1)),
                reason_code TEXT
            );

            CREATE TABLE IF NOT EXISTS module_instance_revisions (
                module_instance_revision_ref TEXT PRIMARY KEY,
                graph_revision_ref TEXT NOT NULL,
                module_instance_ref TEXT NOT NULL,
                module_ref TEXT NOT NULL,
                module_version TEXT NOT NULL,
                config_ref TEXT NOT NULL,
                config_hash TEXT NOT NULL,
                input_port_contract_json TEXT NOT NULL,
                output_port_contract_json TEXT NOT NULL,
                static_composite_path_json TEXT NOT NULL,
                static_accounting_scope_ref TEXT NOT NULL,
                UNIQUE (graph_revision_ref, module_instance_ref),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref)
            );

            CREATE TABLE IF NOT EXISTS graph_edges (
                graph_revision_ref TEXT NOT NULL,
                edge_ref TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                source_port_ref TEXT NOT NULL,
                target_module_instance_revision_ref TEXT NOT NULL,
                target_port_ref TEXT NOT NULL,
                edge_ordinal INTEGER NOT NULL CHECK (edge_ordinal >= 0),
                target_port_ordinal INTEGER NOT NULL
                    CHECK (target_port_ordinal >= 0),
                PRIMARY KEY (graph_revision_ref, edge_ref),
                UNIQUE (graph_revision_ref, edge_ordinal),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref),
                FOREIGN KEY (target_module_instance_revision_ref)
                    REFERENCES module_instance_revisions(
                        module_instance_revision_ref
                    )
            );

            CREATE TABLE IF NOT EXISTS packets (
                packet_ref TEXT PRIMARY KEY,
                execution_ref TEXT NOT NULL,
                graph_revision_ref TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                source_port_ref TEXT,
                value_ref TEXT NOT NULL,
                schema_ref TEXT NOT NULL,
                source_packet_seq INTEGER NOT NULL
                    CHECK (source_packet_seq > 0),
                caused_by_ref TEXT NOT NULL,
                created_event_ref TEXT NOT NULL,
                UNIQUE (execution_ref, source_packet_seq),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref)
            );

            CREATE TABLE IF NOT EXISTS deliveries (
                packet_ref TEXT NOT NULL,
                graph_revision_ref TEXT NOT NULL,
                edge_ref TEXT NOT NULL,
                target_module_instance_revision_ref TEXT NOT NULL,
                target_port_ref TEXT NOT NULL,
                source_packet_seq INTEGER NOT NULL,
                edge_ordinal INTEGER NOT NULL,
                target_port_ordinal INTEGER NOT NULL,
                PRIMARY KEY (
                    packet_ref,
                    graph_revision_ref,
                    edge_ref,
                    target_port_ref
                ),
                FOREIGN KEY (packet_ref) REFERENCES packets(packet_ref),
                FOREIGN KEY (graph_revision_ref, edge_ref)
                    REFERENCES graph_edges(graph_revision_ref, edge_ref),
                FOREIGN KEY (target_module_instance_revision_ref)
                    REFERENCES module_instance_revisions(
                        module_instance_revision_ref
                    )
            );

            CREATE TABLE IF NOT EXISTS accounting_scopes (
                accounting_scope_ref TEXT PRIMARY KEY,
                graph_revision_ref TEXT NOT NULL,
                definition_anchor_ref TEXT NOT NULL,
                parent_accounting_scope_ref TEXT,
                scope_kind TEXT NOT NULL,
                ancestry_hash TEXT NOT NULL,
                created_from_definition_ref TEXT NOT NULL,
                state TEXT NOT NULL,
                UNIQUE (graph_revision_ref, definition_anchor_ref)
            );

            CREATE TABLE IF NOT EXISTS execution_admissions (
                admission_ref TEXT PRIMARY KEY,
                execution_ref TEXT NOT NULL UNIQUE,
                graph_revision_ref TEXT NOT NULL,
                runtime_policy_ref TEXT NOT NULL,
                admitted_at_owner_order INTEGER NOT NULL UNIQUE
                    CHECK (admitted_at_owner_order > 0),
                state TEXT NOT NULL CHECK (state = 'ADMITTED'),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref)
            );

            CREATE TABLE IF NOT EXISTS workflow_executions (
                execution_ref TEXT PRIMARY KEY,
                graph_revision_ref TEXT NOT NULL,
                admission_ref TEXT NOT NULL UNIQUE,
                runtime_policy_ref TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state = 'ADMITTED'),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref),
                FOREIGN KEY (admission_ref)
                    REFERENCES execution_admissions(admission_ref)
            );

            CREATE TABLE IF NOT EXISTS execution_ingress_facts (
                execution_ingress_ref TEXT PRIMARY KEY,
                ingress_route_revision_ref TEXT NOT NULL,
                external_source_identity_ref TEXT NOT NULL,
                external_event_ref TEXT NOT NULL,
                canonical_payload_ref TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                authentication_evidence_ref TEXT NOT NULL,
                validation_evidence_ref TEXT NOT NULL,
                canonical_target_owner_ref TEXT NOT NULL
                    CHECK (canonical_target_owner_ref = 'RUNTIME_ORCHESTRATION'),
                canonical_event_type TEXT NOT NULL
                    CHECK (canonical_event_type = 'ExecutionIngressFact'),
                project_ref TEXT NOT NULL,
                workspace_ref TEXT,
                project_config_revision_ref TEXT NOT NULL,
                workspace_config_revision_ref TEXT,
                policy_context_revision_ref TEXT NOT NULL,
                environment_binding_revision_ref TEXT,
                graph_revision_ref TEXT NOT NULL,
                graph_ingress_binding_ref TEXT NOT NULL,
                caused_by_ref TEXT NOT NULL,
                admitted_at_owner_order INTEGER NOT NULL UNIQUE
                    CHECK (admitted_at_owner_order > 0),
                UNIQUE (
                    ingress_route_revision_ref,
                    external_source_identity_ref,
                    external_event_ref
                ),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref)
            );

            CREATE TRIGGER IF NOT EXISTS execution_ingress_facts_no_update
            BEFORE UPDATE ON execution_ingress_facts
            BEGIN
                SELECT RAISE(ABORT, 'execution ingress facts are immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS execution_ingress_facts_no_delete
            BEFORE DELETE ON execution_ingress_facts
            BEGIN
                SELECT RAISE(ABORT, 'execution ingress facts are immutable');
            END;

            """
        )

    def create_activation_schema(self) -> None:
        """Install the Task-scoped Runtime Activation canonical tables."""

        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS activations (
                activation_ref TEXT PRIMARY KEY,
                execution_ref TEXT NOT NULL,
                graph_revision_ref TEXT NOT NULL,
                module_instance_revision_ref TEXT NOT NULL,
                trigger_delivery_ref TEXT NOT NULL UNIQUE,
                input_bindings_json TEXT NOT NULL,
                static_accounting_scope_ref TEXT NOT NULL,
                created_event_ref TEXT NOT NULL UNIQUE,
                FOREIGN KEY (execution_ref)
                    REFERENCES workflow_executions(execution_ref),
                FOREIGN KEY (graph_revision_ref)
                    REFERENCES graph_revisions(graph_revision_ref),
                FOREIGN KEY (module_instance_revision_ref)
                    REFERENCES module_instance_revisions(
                        module_instance_revision_ref
                    )
            );

            CREATE TABLE IF NOT EXISTS delivery_bindings (
                delivery_ref TEXT PRIMARY KEY,
                packet_ref TEXT NOT NULL,
                graph_revision_ref TEXT NOT NULL,
                edge_ref TEXT NOT NULL,
                target_port_ref TEXT NOT NULL,
                activation_ref TEXT NOT NULL,
                FOREIGN KEY (
                    packet_ref, graph_revision_ref, edge_ref, target_port_ref
                ) REFERENCES deliveries(
                    packet_ref, graph_revision_ref, edge_ref, target_port_ref
                ),
                FOREIGN KEY (activation_ref)
                    REFERENCES activations(activation_ref)
                    DEFERRABLE INITIALLY DEFERRED
            );

            CREATE TABLE IF NOT EXISTS activation_created_events (
                created_event_ref TEXT PRIMARY KEY,
                activation_ref TEXT NOT NULL UNIQUE,
                event_kind TEXT NOT NULL CHECK (event_kind = 'ActivationCreated'),
                FOREIGN KEY (activation_ref)
                    REFERENCES activations(activation_ref)
            );
            """
        )

    def create_run_attempt_schema(self) -> None:
        """Install the Task-scoped Run and RunAttempt authority tables."""

        self.create_activation_schema()
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_ref TEXT PRIMARY KEY,
                activation_ref TEXT NOT NULL UNIQUE,
                execution_ref TEXT NOT NULL,
                current_attempt_seq INTEGER NOT NULL
                    CHECK (current_attempt_seq > 0),
                fencing_generation INTEGER NOT NULL
                    CHECK (fencing_generation > 0),
                state TEXT NOT NULL,
                terminal_attempt_seq INTEGER,
                terminal_event_ref TEXT,
                FOREIGN KEY (activation_ref)
                    REFERENCES activations(activation_ref),
                FOREIGN KEY (execution_ref)
                    REFERENCES workflow_executions(execution_ref)
            );

            CREATE TABLE IF NOT EXISTS run_attempts (
                run_ref TEXT NOT NULL,
                attempt_seq INTEGER NOT NULL CHECK (attempt_seq > 0),
                fencing_token TEXT NOT NULL UNIQUE
                    CHECK (length(fencing_token) > 0),
                state TEXT NOT NULL CHECK (state IN (
                    'CREATED', 'ACTIVE', 'SUCCEEDED', 'FAILED', 'REPLACED'
                )),
                PRIMARY KEY (run_ref, attempt_seq),
                FOREIGN KEY (run_ref) REFERENCES runs(run_ref)
            );

            CREATE TRIGGER IF NOT EXISTS run_attempt_state_transition
            BEFORE UPDATE OF state ON run_attempts
            WHEN NOT (
                NEW.state = OLD.state
                OR (OLD.state = 'CREATED'
                    AND NEW.state IN ('ACTIVE', 'FAILED', 'REPLACED'))
                OR (OLD.state = 'ACTIVE'
                    AND NEW.state IN ('SUCCEEDED', 'FAILED', 'REPLACED'))
            )
            BEGIN
                SELECT RAISE(ABORT, 'invalid run attempt state transition');
            END;

            CREATE TRIGGER IF NOT EXISTS run_authority_counter_transition
            BEFORE UPDATE OF current_attempt_seq, fencing_generation ON runs
            WHEN NOT (
                (NEW.current_attempt_seq = OLD.current_attempt_seq
                 AND NEW.fencing_generation = OLD.fencing_generation)
                OR
                (NEW.current_attempt_seq > OLD.current_attempt_seq
                 AND NEW.fencing_generation > OLD.fencing_generation
                 AND NEW.current_attempt_seq - OLD.current_attempt_seq
                     = NEW.fencing_generation - OLD.fencing_generation)
            )
            BEGIN
                SELECT RAISE(ABORT, 'invalid run authority counter transition');
            END;
            """
        )

        columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(runs)")
        }
        if "terminal_attempt_seq" not in columns:
            self.connection.execute(
                "ALTER TABLE runs ADD COLUMN terminal_attempt_seq INTEGER"
            )
        if "terminal_event_ref" not in columns:
            self.connection.execute(
                "ALTER TABLE runs ADD COLUMN terminal_event_ref TEXT"
            )

    def create_attempt_execution_schema(self) -> None:
        """Install the minimal Task 029 durable-value and terminal evidence tables."""

        self.create_run_attempt_schema()
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS durable_values (
                value_ref TEXT PRIMARY KEY,
                value_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS run_terminal_events (
                event_ref TEXT PRIMARY KEY,
                execution_ref TEXT NOT NULL,
                activation_ref TEXT NOT NULL,
                run_ref TEXT NOT NULL UNIQUE,
                attempt_seq INTEGER NOT NULL,
                event_kind TEXT NOT NULL CHECK (event_kind = 'RunSucceeded'),
                FOREIGN KEY (run_ref) REFERENCES runs(run_ref),
                FOREIGN KEY (run_ref, attempt_seq)
                    REFERENCES run_attempts(run_ref, attempt_seq)
            );
            """
        )

    def create_capability_schema(self) -> None:
        """Install ARE-GATE-1A Capability Authority canonical tables."""

        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS capability_types (
                capability_type_ref TEXT NOT NULL,
                version TEXT NOT NULL,
                contract_json TEXT NOT NULL,
                PRIMARY KEY (capability_type_ref, version)
            );

            CREATE TABLE IF NOT EXISTS capability_grants (
                grant_ref TEXT PRIMARY KEY,
                capability_type_ref TEXT NOT NULL,
                capability_type_version TEXT NOT NULL,
                execution_ref TEXT NOT NULL,
                activation_ref TEXT NOT NULL,
                run_ref TEXT NOT NULL,
                attempt_seq INTEGER NOT NULL CHECK (attempt_seq > 0),
                fencing_token TEXT NOT NULL CHECK (length(fencing_token) > 0),
                fencing_generation INTEGER NOT NULL
                    CHECK (fencing_generation > 0),
                scope_json TEXT NOT NULL,
                issued_by TEXT NOT NULL,
                policy_decision_ref TEXT,
                issued_at INTEGER NOT NULL,
                not_before INTEGER,
                expires_at INTEGER,
                state TEXT NOT NULL
                    CHECK (state IN ('ACTIVE', 'REVOKED', 'EXPIRED')),
                FOREIGN KEY (capability_type_ref, capability_type_version)
                    REFERENCES capability_types(capability_type_ref, version),
                FOREIGN KEY (activation_ref) REFERENCES activations(activation_ref),
                FOREIGN KEY (run_ref, attempt_seq)
                    REFERENCES run_attempts(run_ref, attempt_seq)
            );

            CREATE TRIGGER IF NOT EXISTS capability_grant_immutable_fields
            BEFORE UPDATE ON capability_grants
            WHEN NEW.grant_ref != OLD.grant_ref
              OR NEW.capability_type_ref != OLD.capability_type_ref
              OR NEW.capability_type_version != OLD.capability_type_version
              OR NEW.execution_ref != OLD.execution_ref
              OR NEW.activation_ref != OLD.activation_ref
              OR NEW.run_ref != OLD.run_ref
              OR NEW.attempt_seq != OLD.attempt_seq
              OR NEW.fencing_token != OLD.fencing_token
              OR NEW.fencing_generation != OLD.fencing_generation
              OR NEW.scope_json != OLD.scope_json
              OR NEW.issued_by != OLD.issued_by
              OR NEW.policy_decision_ref IS NOT OLD.policy_decision_ref
              OR NEW.issued_at != OLD.issued_at
              OR NEW.not_before IS NOT OLD.not_before
              OR NEW.expires_at IS NOT OLD.expires_at
            BEGIN
                SELECT RAISE(ABORT, 'capability grant immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS capability_grant_state_transition
            BEFORE UPDATE OF state ON capability_grants
            WHEN NOT (
                NEW.state = OLD.state
                OR (OLD.state = 'ACTIVE'
                    AND NEW.state IN ('REVOKED', 'EXPIRED'))
            )
            BEGIN
                SELECT RAISE(ABORT, 'invalid capability state transition');
            END;
            """
        )

    def create_resource_schema(self) -> None:
        """Install ARE-GATE-2 Resource Manager canonical tables."""

        self.create_run_attempt_schema()
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS resources (
                resource_ref TEXT PRIMARY KEY,
                resource_type TEXT NOT NULL,
                resource_owner_ref TEXT NOT NULL,
                scope_json TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN (
                    'PROVISIONING', 'AVAILABLE', 'DESTROYING',
                    'DESTROYED', 'UNKNOWN'
                )),
                external_ref TEXT NOT NULL UNIQUE,
                provenance_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS resource_leases (
                lease_ref TEXT PRIMARY KEY,
                resource_ref TEXT NOT NULL,
                lease_holder_ref TEXT NOT NULL,
                execution_ref TEXT NOT NULL,
                activation_ref TEXT NOT NULL,
                run_ref TEXT NOT NULL,
                attempt_seq INTEGER NOT NULL CHECK (attempt_seq > 0),
                fencing_token TEXT NOT NULL CHECK (length(fencing_token) > 0),
                fencing_generation INTEGER NOT NULL
                    CHECK (fencing_generation > 0),
                issued_at INTEGER NOT NULL,
                expires_at INTEGER,
                state TEXT NOT NULL CHECK (state IN (
                    'ACTIVE', 'REVOKE_REQUESTED', 'RELEASED',
                    'EXPIRED', 'UNKNOWN'
                )),
                FOREIGN KEY (resource_ref) REFERENCES resources(resource_ref),
                FOREIGN KEY (activation_ref) REFERENCES activations(activation_ref),
                FOREIGN KEY (run_ref, attempt_seq)
                    REFERENCES run_attempts(run_ref, attempt_seq)
            );

            CREATE TRIGGER IF NOT EXISTS resource_immutable_fields
            BEFORE UPDATE ON resources
            WHEN NEW.resource_ref != OLD.resource_ref
              OR NEW.resource_type != OLD.resource_type
              OR NEW.resource_owner_ref != OLD.resource_owner_ref
              OR NEW.scope_json != OLD.scope_json
              OR NEW.external_ref != OLD.external_ref
              OR NEW.provenance_json != OLD.provenance_json
            BEGIN
                SELECT RAISE(ABORT, 'resource identity immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS resource_lease_immutable_fields
            BEFORE UPDATE ON resource_leases
            WHEN NEW.lease_ref != OLD.lease_ref
              OR NEW.resource_ref != OLD.resource_ref
              OR NEW.lease_holder_ref != OLD.lease_holder_ref
              OR NEW.execution_ref != OLD.execution_ref
              OR NEW.activation_ref != OLD.activation_ref
              OR NEW.run_ref != OLD.run_ref
              OR NEW.attempt_seq != OLD.attempt_seq
              OR NEW.fencing_token != OLD.fencing_token
              OR NEW.fencing_generation != OLD.fencing_generation
              OR NEW.issued_at != OLD.issued_at
              OR NEW.expires_at IS NOT OLD.expires_at
            BEGIN
                SELECT RAISE(ABORT, 'resource lease identity immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS resource_state_transition
            BEFORE UPDATE OF state ON resources
            WHEN NOT (
                NEW.state = OLD.state
                OR (OLD.state = 'PROVISIONING'
                    AND NEW.state IN ('AVAILABLE', 'UNKNOWN'))
                OR (OLD.state = 'AVAILABLE'
                    AND NEW.state IN ('DESTROYING', 'UNKNOWN'))
                OR (OLD.state = 'DESTROYING'
                    AND NEW.state IN ('DESTROYED', 'UNKNOWN'))
            )
            BEGIN
                SELECT RAISE(ABORT, 'invalid resource state transition');
            END;

            CREATE TRIGGER IF NOT EXISTS resource_lease_state_transition
            BEFORE UPDATE OF state ON resource_leases
            WHEN NOT (
                NEW.state = OLD.state
                OR (OLD.state = 'ACTIVE' AND NEW.state IN (
                    'REVOKE_REQUESTED', 'RELEASED', 'EXPIRED', 'UNKNOWN'
                ))
            )
            BEGIN
                SELECT RAISE(ABORT, 'invalid resource lease state transition');
            END;
            """
        )

    def create_effect_schema(self) -> None:
        """Install ARE-GATE-3A Effect Authority canonical tables."""

        self.create_capability_schema()
        self.create_resource_schema()
        existing_effect_table = self.connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'effect_operations'
            """
        ).fetchone()
        migrated_historical_outcome = False
        if existing_effect_table is not None:
            columns = {
                row["name"]
                for row in self.connection.execute(
                    "PRAGMA table_info(effect_operations)"
                ).fetchall()
            }
            with self.transaction() as connection:
                if "historical_outcome" not in columns:
                    connection.execute(
                        """
                        ALTER TABLE effect_operations
                        ADD COLUMN historical_outcome TEXT NOT NULL DEFAULT 'UNKNOWN'
                            CHECK (historical_outcome IN (
                                'UNKNOWN', 'PARTIAL', 'KNOWN'
                            ))
                        """
                    )
                    migrated_historical_outcome = True
                if "historical_outcome_evidence_json" not in columns:
                    connection.execute(
                        """
                        ALTER TABLE effect_operations
                        ADD COLUMN historical_outcome_evidence_json TEXT
                        """
                    )
                    migrated_historical_outcome = True
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS effect_operations (
                operation_ref TEXT PRIMARY KEY,
                effect_class TEXT NOT NULL,
                execution_ref TEXT NOT NULL,
                activation_ref TEXT NOT NULL,
                run_ref TEXT NOT NULL,
                attempt_seq INTEGER NOT NULL CHECK (attempt_seq > 0),
                fencing_token TEXT NOT NULL CHECK (length(fencing_token) > 0),
                fencing_generation INTEGER NOT NULL
                    CHECK (fencing_generation > 0),
                capability_grant_ref TEXT NOT NULL,
                resource_ref TEXT NOT NULL,
                resource_lease_ref TEXT NOT NULL,
                target_ref TEXT NOT NULL UNIQUE,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                caused_by_ref TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN (
                    'PREPARED', 'ACTIVE', 'REVOKE_REQUESTED',
                    'FENCED', 'COMPLETED', 'UNKNOWN'
                )),
                prepared_at INTEGER NOT NULL,
                dispatch_admission_ref TEXT UNIQUE,
                dispatch_admitted_at INTEGER,
                completion_evidence_json TEXT,
                fence_evidence_json TEXT,
                historical_outcome TEXT NOT NULL DEFAULT 'UNKNOWN' CHECK (
                    historical_outcome IN ('UNKNOWN', 'PARTIAL', 'KNOWN')
                ),
                historical_outcome_evidence_json TEXT,
                FOREIGN KEY (capability_grant_ref)
                    REFERENCES capability_grants(grant_ref),
                FOREIGN KEY (resource_ref) REFERENCES resources(resource_ref),
                FOREIGN KEY (resource_lease_ref)
                    REFERENCES resource_leases(lease_ref),
                FOREIGN KEY (run_ref, attempt_seq)
                    REFERENCES run_attempts(run_ref, attempt_seq),
                CHECK (
                    (dispatch_admission_ref IS NULL
                     AND dispatch_admitted_at IS NULL)
                    OR
                    (dispatch_admission_ref IS NOT NULL
                     AND dispatch_admitted_at IS NOT NULL)
                ),
                CHECK (
                    state != 'ACTIVE'
                    OR dispatch_admission_ref IS NOT NULL
                ),
                CHECK (
                    (state = 'COMPLETED'
                     AND dispatch_admission_ref IS NOT NULL
                     AND completion_evidence_json IS NOT NULL)
                    OR
                    (state != 'COMPLETED'
                     AND completion_evidence_json IS NULL)
                ),
                CHECK (
                    (state = 'FENCED' AND fence_evidence_json IS NOT NULL)
                    OR
                    (state != 'FENCED' AND fence_evidence_json IS NULL)
                ),
                CHECK (
                    historical_outcome = 'UNKNOWN'
                    OR historical_outcome_evidence_json IS NOT NULL
                )
            );

            CREATE TABLE IF NOT EXISTS effect_historical_outcome_refinements (
                operation_ref TEXT NOT NULL,
                historical_outcome TEXT NOT NULL CHECK (
                    historical_outcome IN ('PARTIAL', 'KNOWN')
                ),
                evidence_json TEXT NOT NULL CHECK (length(evidence_json) > 0),
                PRIMARY KEY (operation_ref, historical_outcome),
                FOREIGN KEY (operation_ref)
                    REFERENCES effect_operations(operation_ref) ON DELETE CASCADE
            );

            CREATE TRIGGER IF NOT EXISTS effect_historical_refinement_immutable
            BEFORE UPDATE ON effect_historical_outcome_refinements
            BEGIN
                SELECT RAISE(ABORT, 'effect historical refinement immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS effect_historical_refinement_no_delete
            BEFORE DELETE ON effect_historical_outcome_refinements
            WHEN EXISTS (
                SELECT 1 FROM effect_operations
                WHERE operation_ref = OLD.operation_ref
            )
            BEGIN
                SELECT RAISE(ABORT, 'effect historical refinement immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS effect_operation_immutable_fields
            BEFORE UPDATE ON effect_operations
            WHEN NEW.operation_ref != OLD.operation_ref
              OR NEW.effect_class != OLD.effect_class
              OR NEW.execution_ref != OLD.execution_ref
              OR NEW.activation_ref != OLD.activation_ref
              OR NEW.run_ref != OLD.run_ref
              OR NEW.attempt_seq != OLD.attempt_seq
              OR NEW.fencing_token != OLD.fencing_token
              OR NEW.fencing_generation != OLD.fencing_generation
              OR NEW.capability_grant_ref != OLD.capability_grant_ref
              OR NEW.resource_ref != OLD.resource_ref
              OR NEW.resource_lease_ref != OLD.resource_lease_ref
              OR NEW.target_ref != OLD.target_ref
              OR NEW.payload_json != OLD.payload_json
              OR NEW.payload_hash != OLD.payload_hash
              OR NEW.caused_by_ref != OLD.caused_by_ref
              OR NEW.prepared_at != OLD.prepared_at
            BEGIN
                SELECT RAISE(ABORT, 'effect operation identity immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS effect_dispatch_admission_immutable
            BEFORE UPDATE ON effect_operations
            WHEN OLD.dispatch_admission_ref IS NOT NULL
             AND (
                NEW.dispatch_admission_ref IS NOT OLD.dispatch_admission_ref
                OR NEW.dispatch_admitted_at IS NOT OLD.dispatch_admitted_at
             )
            BEGIN
                SELECT RAISE(ABORT, 'effect dispatch admission immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS effect_dispatch_admission_requires_prepared
            BEFORE UPDATE OF dispatch_admission_ref, dispatch_admitted_at
            ON effect_operations
            WHEN OLD.dispatch_admission_ref IS NULL
             AND NEW.dispatch_admission_ref IS NOT NULL
             AND (OLD.state != 'PREPARED' OR NEW.state != 'PREPARED')
            BEGIN
                SELECT RAISE(ABORT, 'effect dispatch admission requires prepared');
            END;

            CREATE TRIGGER IF NOT EXISTS effect_completion_evidence_immutable
            BEFORE UPDATE ON effect_operations
            WHEN OLD.completion_evidence_json IS NOT NULL
             AND NEW.completion_evidence_json IS NOT OLD.completion_evidence_json
            BEGIN
                SELECT RAISE(ABORT, 'effect completion evidence immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS effect_fence_evidence_immutable
            BEFORE UPDATE ON effect_operations
            WHEN OLD.fence_evidence_json IS NOT NULL
             AND NEW.fence_evidence_json IS NOT OLD.fence_evidence_json
            BEGIN
                SELECT RAISE(ABORT, 'effect fence evidence immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS effect_operation_state_transition
            BEFORE UPDATE OF state ON effect_operations
            WHEN NOT (
                NEW.state = OLD.state
                OR (OLD.state = 'PREPARED'
                    AND NEW.state IN ('ACTIVE', 'FENCED', 'UNKNOWN'))
                OR (OLD.state = 'ACTIVE'
                    AND NEW.state IN (
                        'COMPLETED', 'REVOKE_REQUESTED', 'UNKNOWN'
                    ))
                OR (OLD.state = 'REVOKE_REQUESTED'
                    AND NEW.state IN ('FENCED', 'COMPLETED', 'UNKNOWN'))
            )
            BEGIN
                SELECT RAISE(ABORT, 'invalid effect operation state transition');
            END;

            CREATE TRIGGER IF NOT EXISTS effect_historical_outcome_transition
            BEFORE UPDATE OF historical_outcome, historical_outcome_evidence_json
            ON effect_operations
            WHEN NOT (
                (NEW.historical_outcome = OLD.historical_outcome
                 AND NEW.historical_outcome_evidence_json
                     IS OLD.historical_outcome_evidence_json)
                OR (OLD.historical_outcome = 'UNKNOWN'
                    AND NEW.historical_outcome IN ('PARTIAL', 'KNOWN')
                    AND NEW.historical_outcome_evidence_json IS NOT NULL)
                OR (OLD.historical_outcome = 'PARTIAL'
                    AND NEW.historical_outcome = 'KNOWN'
                    AND NEW.historical_outcome_evidence_json IS NOT NULL)
            )
            BEGIN
                SELECT RAISE(ABORT, 'invalid effect historical outcome transition');
            END;

            CREATE TRIGGER IF NOT EXISTS effect_historical_outcome_insert_guard
            BEFORE INSERT ON effect_operations
            WHEN NEW.historical_outcome NOT IN ('UNKNOWN', 'PARTIAL', 'KNOWN')
              OR (NEW.historical_outcome != 'UNKNOWN'
                  AND NEW.historical_outcome_evidence_json IS NULL)
            BEGIN
                SELECT RAISE(ABORT, 'invalid effect historical outcome');
            END;

            CREATE TRIGGER IF NOT EXISTS effect_historical_outcome_update_guard
            BEFORE UPDATE ON effect_operations
            WHEN NEW.historical_outcome NOT IN ('UNKNOWN', 'PARTIAL', 'KNOWN')
              OR (NEW.historical_outcome != 'UNKNOWN'
                  AND NEW.historical_outcome_evidence_json IS NULL)
            BEGIN
                SELECT RAISE(ABORT, 'invalid effect historical outcome');
            END;

            CREATE TRIGGER IF NOT EXISTS effect_active_requires_admission
            BEFORE UPDATE OF state ON effect_operations
            WHEN NEW.state = 'ACTIVE'
             AND NEW.dispatch_admission_ref IS NULL
            BEGIN
                SELECT RAISE(ABORT, 'active effect requires dispatch admission');
            END;
            """
        )
        if migrated_historical_outcome:
            rows = self.connection.execute(
                """
                SELECT operation_ref, state
                FROM effect_operations
                WHERE state IN ('COMPLETED', 'FENCED')
                  AND historical_outcome = 'UNKNOWN'
                  AND historical_outcome_evidence_json IS NULL
                """
            ).fetchall()
            with self.transaction() as connection:
                for row in rows:
                    evidence_json = json.dumps(
                        {
                            "basis": "LEGACY_BOUNDED_EFFECT_TERMINAL_EVIDENCE",
                            "operation_ref": row["operation_ref"],
                            "schema": 1,
                            "terminal_state": row["state"],
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    connection.execute(
                        """
                        UPDATE effect_operations
                        SET historical_outcome = 'KNOWN',
                            historical_outcome_evidence_json = ?
                        WHERE operation_ref = ?
                        """,
                        (evidence_json, row["operation_ref"]),
                    )
        current_refinements = self.connection.execute(
            """
            SELECT operation_ref, historical_outcome,
                   historical_outcome_evidence_json
            FROM effect_operations
            WHERE historical_outcome IN ('PARTIAL', 'KNOWN')
              AND historical_outcome_evidence_json IS NOT NULL
            """
        ).fetchall()
        with self.transaction() as connection:
            for row in current_refinements:
                existing = connection.execute(
                    """
                    SELECT evidence_json
                    FROM effect_historical_outcome_refinements
                    WHERE operation_ref = ? AND historical_outcome = ?
                    """,
                    (row["operation_ref"], row["historical_outcome"]),
                ).fetchone()
                if existing is None:
                    connection.execute(
                        """
                        INSERT INTO effect_historical_outcome_refinements(
                            operation_ref, historical_outcome, evidence_json
                        ) VALUES (?, ?, ?)
                        """,
                        (
                            row["operation_ref"],
                            row["historical_outcome"],
                            row["historical_outcome_evidence_json"],
                        ),
                    )
                elif (
                    existing["evidence_json"]
                    != row["historical_outcome_evidence_json"]
                ):
                    raise sqlite3.IntegrityError(
                        "effect historical refinement projection conflict"
                    )

    def create_budget_schema(self) -> None:
        """Install ARE-GATE-6A BudgetPolicyRevision / BudgetReservation tables."""

        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS budget_policy_revisions (
                budget_policy_revision_ref TEXT PRIMARY KEY,
                accounting_scope_ref TEXT NOT NULL,
                effective_from INTEGER NOT NULL,
                effective_until INTEGER,
                dimensions_json TEXT NOT NULL,
                enforcement_rules_json TEXT NOT NULL,
                created_by_ref TEXT NOT NULL,
                supersedes_ref TEXT,
                CHECK (
                    effective_until IS NULL
                    OR effective_until > effective_from
                ),
                FOREIGN KEY (accounting_scope_ref)
                    REFERENCES accounting_scopes(accounting_scope_ref),
                FOREIGN KEY (supersedes_ref)
                    REFERENCES budget_policy_revisions(budget_policy_revision_ref)
            );

            CREATE TRIGGER IF NOT EXISTS budget_policy_revision_immutable
            BEFORE UPDATE ON budget_policy_revisions
            BEGIN
                SELECT RAISE(ABORT, 'budget policy revision is immutable');
            END;

            CREATE TABLE IF NOT EXISTS budget_reservations (
                reservation_ref TEXT PRIMARY KEY,
                request_ref TEXT NOT NULL UNIQUE,
                activation_ref TEXT NOT NULL,
                run_ref TEXT NOT NULL,
                attempt_seq INTEGER NOT NULL CHECK (attempt_seq > 0),
                accounting_scope_ref TEXT NOT NULL,
                graph_revision_ref TEXT NOT NULL,
                definition_anchor_ref TEXT NOT NULL,
                ancestry_snapshot_json TEXT NOT NULL,
                policy_revision_refs_json TEXT NOT NULL,
                estimate_ref TEXT NOT NULL,
                requested_dimensions_json TEXT NOT NULL,
                reserved_dimensions_json TEXT NOT NULL,
                committed_dimensions_json TEXT NOT NULL,
                released_dimensions_json TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN (
                    'REQUESTED', 'RESERVED', 'DENIED',
                    'RECONCILING', 'COMMITTED', 'RELEASED'
                )),
                deny_reason_code TEXT,
                subject_refs_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                caused_by_ref TEXT NOT NULL,
                CHECK (
                    (state = 'DENIED' AND deny_reason_code IS NOT NULL)
                    OR
                    (state != 'DENIED' AND deny_reason_code IS NULL)
                ),
                FOREIGN KEY (accounting_scope_ref)
                    REFERENCES accounting_scopes(accounting_scope_ref)
            );

            CREATE TRIGGER IF NOT EXISTS budget_reservation_identity_immutable
            BEFORE UPDATE ON budget_reservations
            WHEN NEW.reservation_ref != OLD.reservation_ref
              OR NEW.request_ref != OLD.request_ref
              OR NEW.activation_ref != OLD.activation_ref
              OR NEW.run_ref != OLD.run_ref
              OR NEW.attempt_seq != OLD.attempt_seq
              OR NEW.accounting_scope_ref != OLD.accounting_scope_ref
              OR NEW.graph_revision_ref != OLD.graph_revision_ref
              OR NEW.definition_anchor_ref != OLD.definition_anchor_ref
              OR NEW.ancestry_snapshot_json != OLD.ancestry_snapshot_json
              OR NEW.policy_revision_refs_json != OLD.policy_revision_refs_json
              OR NEW.estimate_ref != OLD.estimate_ref
              OR NEW.requested_dimensions_json != OLD.requested_dimensions_json
              OR NEW.reserved_dimensions_json != OLD.reserved_dimensions_json
              OR NEW.subject_refs_json != OLD.subject_refs_json
              OR NEW.caused_by_ref != OLD.caused_by_ref
              OR NEW.created_at != OLD.created_at
            BEGIN
                SELECT RAISE(ABORT, 'budget reservation identity is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS budget_reservation_state_transition
            BEFORE UPDATE OF state ON budget_reservations
            WHEN NOT (
                NEW.state = OLD.state
                OR (OLD.state = 'REQUESTED'
                    AND NEW.state IN ('RESERVED', 'DENIED'))
                OR (OLD.state = 'RESERVED'
                    AND NEW.state IN ('COMMITTED', 'RELEASED', 'RECONCILING'))
                OR (OLD.state = 'RELEASED' AND NEW.state = 'RECONCILING')
                OR (OLD.state = 'COMMITTED' AND NEW.state = 'RECONCILING')
                OR (OLD.state = 'RECONCILING'
                    AND NEW.state IN ('COMMITTED', 'RELEASED'))
            )
            BEGIN
                SELECT RAISE(ABORT, 'invalid budget reservation state transition');
            END;

            CREATE TABLE IF NOT EXISTS budget_scope_exposure (
                accounting_scope_ref TEXT NOT NULL,
                dimension_ref TEXT NOT NULL,
                reserved_amount INTEGER NOT NULL DEFAULT 0
                    CHECK (reserved_amount >= 0),
                committed_amount INTEGER NOT NULL DEFAULT 0
                    CHECK (committed_amount >= 0),
                PRIMARY KEY (accounting_scope_ref, dimension_ref),
                FOREIGN KEY (accounting_scope_ref)
                    REFERENCES accounting_scopes(accounting_scope_ref)
            );
            """
        )

    def create_usage_ledger_schema(self) -> None:
        """Install the Usage/Ledger foundation tables: immutable UsageFact
        and append-only UsageAdjustmentFact (ARE-GATE-6 Track A)."""

        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS usage_facts (
                usage_fact_ref TEXT PRIMARY KEY,
                accounting_scope_ref TEXT NOT NULL,
                reservation_ref TEXT,
                operation_ref TEXT,
                resource_ref TEXT,
                run_ref TEXT,
                source_authority_ref TEXT NOT NULL,
                source_fact_id TEXT NOT NULL,
                dimension_ref TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                unit TEXT NOT NULL,
                fact_kind TEXT NOT NULL,
                usage_period TEXT,
                external_evidence_ref TEXT NOT NULL,
                observed_at INTEGER,
                ingested_at INTEGER NOT NULL,
                caused_by_ref TEXT NOT NULL,
                UNIQUE (
                    source_authority_ref, source_fact_id, fact_kind, dimension_ref
                ),
                FOREIGN KEY (accounting_scope_ref)
                    REFERENCES accounting_scopes(accounting_scope_ref)
            );

            CREATE TRIGGER IF NOT EXISTS usage_fact_immutable
            BEFORE UPDATE ON usage_facts
            BEGIN
                SELECT RAISE(ABORT, 'usage fact is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS usage_fact_no_delete
            BEFORE DELETE ON usage_facts
            BEGIN
                SELECT RAISE(ABORT, 'usage fact is immutable');
            END;

            CREATE TABLE IF NOT EXISTS usage_adjustment_facts (
                adjustment_fact_ref TEXT PRIMARY KEY,
                adjusts_usage_fact_ref TEXT NOT NULL,
                source_authority_ref TEXT NOT NULL,
                source_fact_id TEXT NOT NULL,
                fact_kind TEXT NOT NULL,
                dimension_ref TEXT NOT NULL,
                delta_quantity INTEGER NOT NULL CHECK (delta_quantity != 0),
                unit TEXT NOT NULL,
                reason TEXT NOT NULL,
                evidence_ref TEXT NOT NULL,
                ingested_at INTEGER NOT NULL,
                caused_by_ref TEXT NOT NULL,
                UNIQUE (
                    source_authority_ref, source_fact_id, fact_kind, dimension_ref
                ),
                FOREIGN KEY (adjusts_usage_fact_ref)
                    REFERENCES usage_facts(usage_fact_ref)
            );

            CREATE TRIGGER IF NOT EXISTS usage_adjustment_fact_immutable
            BEFORE UPDATE ON usage_adjustment_facts
            BEGIN
                SELECT RAISE(ABORT, 'usage adjustment fact is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS usage_adjustment_fact_no_delete
            BEFORE DELETE ON usage_adjustment_facts
            BEGIN
                SELECT RAISE(ABORT, 'usage adjustment fact is immutable');
            END;
            """
        )

    def create_budget_settlement_schema(self) -> None:
        """Install canonical known-actual settlement / overrun facts."""

        self.create_budget_schema()
        self.create_usage_ledger_schema()
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS budget_settlements (
                settlement_ref TEXT PRIMARY KEY,
                request_ref TEXT NOT NULL UNIQUE,
                reservation_ref TEXT NOT NULL UNIQUE,
                fact_set_hash TEXT NOT NULL,
                usage_fact_refs_json TEXT NOT NULL,
                adjustment_fact_refs_json TEXT NOT NULL,
                actual_dimensions_json TEXT NOT NULL,
                released_dimensions_json TEXT NOT NULL,
                overrun_dimensions_json TEXT NOT NULL,
                resulting_state TEXT NOT NULL CHECK (
                    resulting_state IN ('COMMITTED', 'RELEASED')
                ),
                settled_at INTEGER NOT NULL,
                caused_by_ref TEXT NOT NULL,
                FOREIGN KEY (reservation_ref)
                    REFERENCES budget_reservations(reservation_ref)
            );

            CREATE TRIGGER IF NOT EXISTS budget_settlement_immutable
            BEFORE UPDATE ON budget_settlements
            BEGIN
                SELECT RAISE(ABORT, 'budget settlement is immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS budget_settlement_no_delete
            BEFORE DELETE ON budget_settlements
            BEGIN
                SELECT RAISE(ABORT, 'budget settlement is immutable');
            END;
            """
        )

    def create_provider_schema(self) -> None:
        """Install immutable unary Provider identity/profile/evidence records."""

        self.create_effect_schema()
        self.create_budget_schema()
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS provider_profile_revisions (
                profile_revision_ref TEXT PRIMARY KEY,
                profile_ref TEXT NOT NULL,
                adapter_ref TEXT NOT NULL,
                provider_scope_ref TEXT NOT NULL,
                account_scope_ref TEXT NOT NULL,
                endpoint_scope_ref TEXT NOT NULL,
                model_scope_ref TEXT NOT NULL,
                usage_source_namespace TEXT NOT NULL,
                operation_class TEXT NOT NULL CHECK (operation_class = 'MODEL_INVOKE'),
                idempotent_same_key INTEGER NOT NULL CHECK (idempotent_same_key IN (0,1)),
                authoritative_lookup INTEGER NOT NULL CHECK (authoritative_lookup IN (0,1)),
                lookup_not_found_proves_absence INTEGER NOT NULL CHECK (lookup_not_found_proves_absence IN (0,1)),
                cancellation_request INTEGER NOT NULL CHECK (cancellation_request IN (0,1)),
                terminal_cancel_confirmation INTEGER NOT NULL CHECK (terminal_cancel_confirmation IN (0,1)),
                external_identity_recovery INTEGER NOT NULL CHECK (external_identity_recovery IN (0,1)),
                authoritative_usage INTEGER NOT NULL CHECK (authoritative_usage IN (0,1)),
                authoritative_no_usage_no_charge INTEGER NOT NULL CHECK (authoritative_no_usage_no_charge IN (0,1)),
                continuation_resume INTEGER NOT NULL CHECK (continuation_resume = 0),
                streaming INTEGER NOT NULL CHECK (streaming = 0),
                UNIQUE (profile_ref, profile_revision_ref)
            );
            CREATE TRIGGER IF NOT EXISTS provider_profile_revisions_immutable
            BEFORE UPDATE ON provider_profile_revisions BEGIN
                SELECT RAISE(ABORT, 'provider profile revision is immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS provider_profile_revisions_no_delete
            BEFORE DELETE ON provider_profile_revisions BEGIN
                SELECT RAISE(ABORT, 'provider profile revision is immutable');
            END;

            CREATE TABLE IF NOT EXISTS provider_operations (
                operation_ref TEXT PRIMARY KEY,
                semantic_request_hash TEXT NOT NULL,
                profile_revision_ref TEXT NOT NULL,
                idempotency_key TEXT,
                dispatch_admission_ref TEXT NOT NULL,
                run_ref TEXT NOT NULL,
                attempt_seq INTEGER NOT NULL CHECK (attempt_seq > 0),
                capability_grant_ref TEXT NOT NULL,
                resource_lease_ref TEXT NOT NULL,
                reservation_ref TEXT NOT NULL,
                usage_source_namespace TEXT NOT NULL,
                protected_idempotency_scope_ref TEXT NOT NULL,
                external_request_id TEXT,
                created_at INTEGER NOT NULL,
                UNIQUE (protected_idempotency_scope_ref, idempotency_key),
                FOREIGN KEY (profile_revision_ref) REFERENCES provider_profile_revisions(profile_revision_ref),
                FOREIGN KEY (operation_ref) REFERENCES effect_operations(operation_ref),
                FOREIGN KEY (reservation_ref) REFERENCES budget_reservations(reservation_ref)
            );
            CREATE TRIGGER IF NOT EXISTS provider_operations_immutable
            BEFORE UPDATE ON provider_operations
            WHEN NEW.operation_ref != OLD.operation_ref
              OR NEW.semantic_request_hash != OLD.semantic_request_hash
              OR NEW.profile_revision_ref != OLD.profile_revision_ref
              OR NEW.idempotency_key IS NOT OLD.idempotency_key
              OR NEW.dispatch_admission_ref != OLD.dispatch_admission_ref
              OR NEW.run_ref != OLD.run_ref OR NEW.attempt_seq != OLD.attempt_seq
              OR NEW.capability_grant_ref != OLD.capability_grant_ref
              OR NEW.resource_lease_ref != OLD.resource_lease_ref
              OR NEW.reservation_ref != OLD.reservation_ref
              OR NEW.usage_source_namespace != OLD.usage_source_namespace
              OR NEW.protected_idempotency_scope_ref != OLD.protected_idempotency_scope_ref
              OR NEW.created_at != OLD.created_at
              OR (OLD.external_request_id IS NOT NULL AND NEW.external_request_id IS NOT OLD.external_request_id)
            BEGIN SELECT RAISE(ABORT, 'provider operation identity is immutable'); END;
            CREATE TRIGGER IF NOT EXISTS provider_operations_no_delete
            BEFORE DELETE ON provider_operations BEGIN
                SELECT RAISE(ABORT, 'provider operation is immutable');
            END;

            CREATE TABLE IF NOT EXISTS provider_evidence (
                evidence_ref TEXT PRIMARY KEY,
                operation_ref TEXT NOT NULL,
                evidence_kind TEXT NOT NULL CHECK (evidence_kind IN (
                    'ACKNOWLEDGEMENT','LOOKUP','CANCEL_REQUEST','CANCEL_CONFIRMATION','USAGE'
                )),
                evidence_semantics TEXT NOT NULL,
                authoritative INTEGER NOT NULL CHECK (authoritative IN (0,1)),
                historical_outcome TEXT NOT NULL CHECK (historical_outcome IN ('UNKNOWN','PARTIAL','KNOWN')),
                recorded_at INTEGER NOT NULL,
                FOREIGN KEY (operation_ref) REFERENCES provider_operations(operation_ref)
            );
            CREATE TRIGGER IF NOT EXISTS provider_evidence_immutable
            BEFORE UPDATE ON provider_evidence BEGIN
                SELECT RAISE(ABORT, 'provider evidence is immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS provider_evidence_no_delete
            BEFORE DELETE ON provider_evidence BEGIN
                SELECT RAISE(ABORT, 'provider evidence is immutable');
            END;

            CREATE TABLE IF NOT EXISTS provider_usage_source_bindings (
                source_authority_ref TEXT NOT NULL,
                source_fact_id TEXT NOT NULL,
                operation_ref TEXT NOT NULL,
                provider_line_item_ref TEXT NOT NULL,
                evidence_ref TEXT NOT NULL UNIQUE,
                evidence_semantics TEXT NOT NULL CHECK (evidence_semantics IN ('ACTUAL_USAGE','NO_USAGE_NO_CHARGE')),
                dimension_ref TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                unit TEXT NOT NULL,
                bound_at INTEGER NOT NULL,
                PRIMARY KEY (source_authority_ref, source_fact_id),
                UNIQUE (operation_ref, provider_line_item_ref),
                FOREIGN KEY (operation_ref) REFERENCES provider_operations(operation_ref),
                FOREIGN KEY (evidence_ref) REFERENCES provider_evidence(evidence_ref)
            );
            CREATE TRIGGER IF NOT EXISTS provider_usage_source_bindings_immutable
            BEFORE UPDATE ON provider_usage_source_bindings BEGIN
                SELECT RAISE(ABORT, 'provider usage source binding is immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS provider_usage_source_bindings_no_delete
            BEFORE DELETE ON provider_usage_source_bindings BEGIN
                SELECT RAISE(ABORT, 'provider usage source binding is immutable');
            END;
            """
        )

    def create_provider_reconciliation_schema(self) -> None:
        """Install Accounting-owned Provider ambiguity and resolution evidence."""

        self.create_provider_schema()
        self.create_budget_settlement_schema()
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS provider_accounting_reconciliations (
                reconciliation_ref TEXT PRIMARY KEY,
                reservation_ref TEXT NOT NULL UNIQUE,
                operation_ref TEXT NOT NULL,
                provider_usage_source_ref TEXT NOT NULL,
                ambiguity_outcome TEXT NOT NULL CHECK (ambiguity_outcome IN ('UNKNOWN','PARTIAL')),
                evidence_ref TEXT NOT NULL,
                caused_by_ref TEXT NOT NULL,
                entered_at INTEGER NOT NULL,
                FOREIGN KEY (reservation_ref) REFERENCES budget_reservations(reservation_ref)
            );
            CREATE TRIGGER IF NOT EXISTS provider_accounting_reconciliations_immutable
            BEFORE UPDATE ON provider_accounting_reconciliations BEGIN
                SELECT RAISE(ABORT, 'provider reconciliation is immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS provider_accounting_reconciliations_no_delete
            BEFORE DELETE ON provider_accounting_reconciliations BEGIN
                SELECT RAISE(ABORT, 'provider reconciliation is immutable');
            END;
            CREATE TABLE IF NOT EXISTS provider_accounting_reconciliation_resolutions (
                reconciliation_ref TEXT PRIMARY KEY,
                settlement_ref TEXT NOT NULL UNIQUE,
                resulting_state TEXT NOT NULL CHECK (resulting_state IN ('COMMITTED','RELEASED')),
                resolved_at INTEGER NOT NULL,
                FOREIGN KEY (reconciliation_ref) REFERENCES provider_accounting_reconciliations(reconciliation_ref),
                FOREIGN KEY (settlement_ref) REFERENCES budget_settlements(settlement_ref)
            );
            CREATE TRIGGER IF NOT EXISTS provider_accounting_reconciliation_resolutions_immutable
            BEFORE UPDATE ON provider_accounting_reconciliation_resolutions BEGIN
                SELECT RAISE(ABORT, 'provider reconciliation resolution is immutable');
            END;
            CREATE TRIGGER IF NOT EXISTS provider_accounting_reconciliation_resolutions_no_delete
            BEFORE DELETE ON provider_accounting_reconciliation_resolutions BEGIN
                SELECT RAISE(ABORT, 'provider reconciliation resolution is immutable');
            END;
            """
        )

    def create_pwp_schema(self) -> None:
        """Install only PWP-owned identity and immutable revision tables."""

        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS pwp_projects (
                project_ref TEXT PRIMARY KEY,
                state TEXT NOT NULL CHECK (state IN ('ACTIVE','DEPRECATED','ARCHIVED')),
                created_at INTEGER NOT NULL,
                archived_at INTEGER,
                current_project_config_revision_ref TEXT,
                current_policy_context_revision_ref TEXT,
                CHECK ((state = 'ARCHIVED') = (archived_at IS NOT NULL)),
                FOREIGN KEY (current_project_config_revision_ref)
                    REFERENCES pwp_project_config_revisions(revision_ref),
                FOREIGN KEY (current_policy_context_revision_ref)
                    REFERENCES pwp_policy_context_revisions(revision_ref)
            );

            CREATE TABLE IF NOT EXISTS pwp_workspaces (
                workspace_ref TEXT PRIMARY KEY,
                project_ref TEXT NOT NULL,
                parent_workspace_ref TEXT,
                state TEXT NOT NULL CHECK (state IN ('ACTIVE','DEPRECATED','ARCHIVED')),
                created_at INTEGER NOT NULL,
                archived_at INTEGER,
                current_workspace_config_revision_ref TEXT,
                current_policy_context_revision_ref TEXT,
                current_environment_binding_revision_ref TEXT,
                CHECK ((state = 'ARCHIVED') = (archived_at IS NOT NULL)),
                CHECK (parent_workspace_ref IS NULL OR parent_workspace_ref != workspace_ref),
                FOREIGN KEY (project_ref) REFERENCES pwp_projects(project_ref),
                FOREIGN KEY (parent_workspace_ref) REFERENCES pwp_workspaces(workspace_ref),
                FOREIGN KEY (current_workspace_config_revision_ref)
                    REFERENCES pwp_workspace_config_revisions(revision_ref),
                FOREIGN KEY (current_policy_context_revision_ref)
                    REFERENCES pwp_policy_context_revisions(revision_ref),
                FOREIGN KEY (current_environment_binding_revision_ref)
                    REFERENCES pwp_environment_binding_revisions(revision_ref)
            );

            CREATE TABLE IF NOT EXISTS pwp_project_config_revisions (
                revision_ref TEXT PRIMARY KEY,
                subject_ref TEXT NOT NULL,
                revision_seq INTEGER NOT NULL CHECK (revision_seq > 0),
                previous_revision_ref TEXT UNIQUE,
                payload_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                caused_by_ref TEXT NOT NULL,
                UNIQUE(subject_ref, revision_seq),
                FOREIGN KEY (subject_ref) REFERENCES pwp_projects(project_ref),
                FOREIGN KEY (previous_revision_ref)
                    REFERENCES pwp_project_config_revisions(revision_ref)
            );

            CREATE TABLE IF NOT EXISTS pwp_workspace_config_revisions (
                revision_ref TEXT PRIMARY KEY,
                subject_ref TEXT NOT NULL,
                revision_seq INTEGER NOT NULL CHECK (revision_seq > 0),
                previous_revision_ref TEXT UNIQUE,
                payload_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                caused_by_ref TEXT NOT NULL,
                UNIQUE(subject_ref, revision_seq),
                FOREIGN KEY (subject_ref) REFERENCES pwp_workspaces(workspace_ref),
                FOREIGN KEY (previous_revision_ref)
                    REFERENCES pwp_workspace_config_revisions(revision_ref)
            );

            CREATE TABLE IF NOT EXISTS pwp_policy_context_revisions (
                revision_ref TEXT PRIMARY KEY,
                subject_kind TEXT NOT NULL CHECK (subject_kind IN ('PROJECT','WORKSPACE')),
                subject_ref TEXT NOT NULL,
                revision_seq INTEGER NOT NULL CHECK (revision_seq > 0),
                previous_revision_ref TEXT UNIQUE,
                payload_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                caused_by_ref TEXT NOT NULL,
                UNIQUE(subject_kind, subject_ref, revision_seq),
                FOREIGN KEY (previous_revision_ref)
                    REFERENCES pwp_policy_context_revisions(revision_ref)
            );

            CREATE TABLE IF NOT EXISTS pwp_environment_binding_revisions (
                revision_ref TEXT PRIMARY KEY,
                subject_ref TEXT NOT NULL,
                revision_seq INTEGER NOT NULL CHECK (revision_seq > 0),
                previous_revision_ref TEXT UNIQUE,
                payload_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                caused_by_ref TEXT NOT NULL,
                UNIQUE(subject_ref, revision_seq),
                FOREIGN KEY (subject_ref) REFERENCES pwp_workspaces(workspace_ref),
                FOREIGN KEY (previous_revision_ref)
                    REFERENCES pwp_environment_binding_revisions(revision_ref)
            );

            CREATE TABLE IF NOT EXISTS pwp_ingress_routes (
                ingress_route_ref TEXT PRIMARY KEY,
                project_ref TEXT NOT NULL,
                workspace_ref TEXT,
                state TEXT NOT NULL CHECK (state IN ('ACTIVE','DISABLED','DEPRECATED','ARCHIVED')),
                current_ingress_route_revision_ref TEXT,
                created_at INTEGER NOT NULL,
                archived_at INTEGER,
                CHECK ((state = 'ARCHIVED') = (archived_at IS NOT NULL)),
                FOREIGN KEY (project_ref) REFERENCES pwp_projects(project_ref),
                FOREIGN KEY (workspace_ref) REFERENCES pwp_workspaces(workspace_ref),
                FOREIGN KEY (current_ingress_route_revision_ref)
                    REFERENCES pwp_ingress_route_revisions(revision_ref)
            );

            CREATE TABLE IF NOT EXISTS pwp_ingress_route_revisions (
                revision_ref TEXT PRIMARY KEY,
                subject_ref TEXT NOT NULL,
                revision_seq INTEGER NOT NULL CHECK (revision_seq > 0),
                previous_revision_ref TEXT UNIQUE,
                payload_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                caused_by_ref TEXT NOT NULL,
                UNIQUE(subject_ref, revision_seq),
                FOREIGN KEY (subject_ref) REFERENCES pwp_ingress_routes(ingress_route_ref),
                FOREIGN KEY (previous_revision_ref)
                    REFERENCES pwp_ingress_route_revisions(revision_ref)
            );

            CREATE TRIGGER IF NOT EXISTS pwp_project_identity_immutable
            BEFORE UPDATE OF project_ref, created_at ON pwp_projects
            BEGIN SELECT RAISE(ABORT, 'project identity immutable'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_project_no_delete
            BEFORE DELETE ON pwp_projects
            BEGIN SELECT RAISE(ABORT, 'project history retained'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_project_state_transition
            BEFORE UPDATE OF state ON pwp_projects
            WHEN NOT (
                NEW.state = OLD.state
                OR (OLD.state = 'ACTIVE' AND NEW.state IN ('DEPRECATED','ARCHIVED'))
                OR (OLD.state = 'DEPRECATED' AND NEW.state = 'ARCHIVED')
            )
            BEGIN SELECT RAISE(ABORT, 'invalid project state transition'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_workspace_identity_immutable
            BEFORE UPDATE OF workspace_ref, project_ref, parent_workspace_ref, created_at
            ON pwp_workspaces
            BEGIN SELECT RAISE(ABORT, 'workspace identity immutable'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_workspace_no_delete
            BEFORE DELETE ON pwp_workspaces
            BEGIN SELECT RAISE(ABORT, 'workspace history retained'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_workspace_parent_same_project
            BEFORE INSERT ON pwp_workspaces
            WHEN NEW.parent_workspace_ref IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM pwp_workspaces parent
                WHERE parent.workspace_ref = NEW.parent_workspace_ref
                  AND parent.project_ref = NEW.project_ref
            )
            BEGIN SELECT RAISE(ABORT, 'workspace parent project mismatch'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_workspace_state_transition
            BEFORE UPDATE OF state ON pwp_workspaces
            WHEN NOT (
                NEW.state = OLD.state
                OR (OLD.state = 'ACTIVE' AND NEW.state IN ('DEPRECATED','ARCHIVED'))
                OR (OLD.state = 'DEPRECATED' AND NEW.state = 'ARCHIVED')
            )
            BEGIN SELECT RAISE(ABORT, 'invalid workspace state transition'); END;

            CREATE TRIGGER IF NOT EXISTS pwp_project_config_pointer_advance
            BEFORE UPDATE OF current_project_config_revision_ref ON pwp_projects
            WHEN NEW.current_project_config_revision_ref IS NOT OLD.current_project_config_revision_ref
             AND NOT EXISTS (
                SELECT 1 FROM pwp_project_config_revisions revision
                WHERE revision.revision_ref = NEW.current_project_config_revision_ref
                  AND revision.subject_ref = OLD.project_ref
                  AND revision.previous_revision_ref IS OLD.current_project_config_revision_ref
                  AND revision.revision_seq = CASE
                      WHEN OLD.current_project_config_revision_ref IS NULL THEN 1
                      ELSE (SELECT revision_seq + 1 FROM pwp_project_config_revisions
                            WHERE revision_ref = OLD.current_project_config_revision_ref)
                  END
             )
            BEGIN SELECT RAISE(ABORT, 'invalid project config pointer advance'); END;

            CREATE TRIGGER IF NOT EXISTS pwp_workspace_config_pointer_advance
            BEFORE UPDATE OF current_workspace_config_revision_ref ON pwp_workspaces
            WHEN NEW.current_workspace_config_revision_ref IS NOT OLD.current_workspace_config_revision_ref
             AND NOT EXISTS (
                SELECT 1 FROM pwp_workspace_config_revisions revision
                WHERE revision.revision_ref = NEW.current_workspace_config_revision_ref
                  AND revision.subject_ref = OLD.workspace_ref
                  AND revision.previous_revision_ref IS OLD.current_workspace_config_revision_ref
                  AND revision.revision_seq = CASE
                      WHEN OLD.current_workspace_config_revision_ref IS NULL THEN 1
                      ELSE (SELECT revision_seq + 1 FROM pwp_workspace_config_revisions
                            WHERE revision_ref = OLD.current_workspace_config_revision_ref)
                  END
             )
            BEGIN SELECT RAISE(ABORT, 'invalid workspace config pointer advance'); END;

            CREATE TRIGGER IF NOT EXISTS pwp_project_policy_pointer_advance
            BEFORE UPDATE OF current_policy_context_revision_ref ON pwp_projects
            WHEN NEW.current_policy_context_revision_ref IS NOT OLD.current_policy_context_revision_ref
             AND NOT EXISTS (
                SELECT 1 FROM pwp_policy_context_revisions revision
                WHERE revision.revision_ref = NEW.current_policy_context_revision_ref
                  AND revision.subject_kind = 'PROJECT'
                  AND revision.subject_ref = OLD.project_ref
                  AND revision.previous_revision_ref IS OLD.current_policy_context_revision_ref
                  AND revision.revision_seq = CASE
                      WHEN OLD.current_policy_context_revision_ref IS NULL THEN 1
                      ELSE (SELECT revision_seq + 1 FROM pwp_policy_context_revisions
                            WHERE revision_ref = OLD.current_policy_context_revision_ref)
                  END
             )
            BEGIN SELECT RAISE(ABORT, 'invalid project policy pointer advance'); END;

            CREATE TRIGGER IF NOT EXISTS pwp_workspace_policy_pointer_advance
            BEFORE UPDATE OF current_policy_context_revision_ref ON pwp_workspaces
            WHEN NEW.current_policy_context_revision_ref IS NOT OLD.current_policy_context_revision_ref
             AND NOT EXISTS (
                SELECT 1 FROM pwp_policy_context_revisions revision
                WHERE revision.revision_ref = NEW.current_policy_context_revision_ref
                  AND revision.subject_kind = 'WORKSPACE'
                  AND revision.subject_ref = OLD.workspace_ref
                  AND revision.previous_revision_ref IS OLD.current_policy_context_revision_ref
                  AND revision.revision_seq = CASE
                      WHEN OLD.current_policy_context_revision_ref IS NULL THEN 1
                      ELSE (SELECT revision_seq + 1 FROM pwp_policy_context_revisions
                            WHERE revision_ref = OLD.current_policy_context_revision_ref)
                  END
             )
            BEGIN SELECT RAISE(ABORT, 'invalid workspace policy pointer advance'); END;

            CREATE TRIGGER IF NOT EXISTS pwp_environment_pointer_advance
            BEFORE UPDATE OF current_environment_binding_revision_ref ON pwp_workspaces
            WHEN NEW.current_environment_binding_revision_ref IS NOT OLD.current_environment_binding_revision_ref
             AND NOT EXISTS (
                SELECT 1 FROM pwp_environment_binding_revisions revision
                WHERE revision.revision_ref = NEW.current_environment_binding_revision_ref
                  AND revision.subject_ref = OLD.workspace_ref
                  AND revision.previous_revision_ref IS OLD.current_environment_binding_revision_ref
                  AND revision.revision_seq = CASE
                      WHEN OLD.current_environment_binding_revision_ref IS NULL THEN 1
                      ELSE (SELECT revision_seq + 1 FROM pwp_environment_binding_revisions
                            WHERE revision_ref = OLD.current_environment_binding_revision_ref)
                  END
             )
            BEGIN SELECT RAISE(ABORT, 'invalid environment binding pointer advance'); END;

            CREATE TRIGGER IF NOT EXISTS pwp_ingress_route_identity_immutable
            BEFORE UPDATE OF ingress_route_ref, project_ref, workspace_ref, created_at
            ON pwp_ingress_routes
            BEGIN SELECT RAISE(ABORT, 'ingress route identity immutable'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_ingress_route_no_delete
            BEFORE DELETE ON pwp_ingress_routes
            BEGIN SELECT RAISE(ABORT, 'ingress route history retained'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_ingress_route_workspace_same_project
            BEFORE INSERT ON pwp_ingress_routes
            WHEN NEW.workspace_ref IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM pwp_workspaces workspace
                WHERE workspace.workspace_ref = NEW.workspace_ref
                  AND workspace.project_ref = NEW.project_ref
            )
            BEGIN SELECT RAISE(ABORT, 'ingress route workspace project mismatch'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_ingress_route_state_transition
            BEFORE UPDATE OF state ON pwp_ingress_routes
            WHEN NOT (
                NEW.state = OLD.state
                OR (OLD.state = 'ACTIVE' AND NEW.state IN ('DISABLED','DEPRECATED','ARCHIVED'))
                OR (OLD.state = 'DISABLED' AND NEW.state IN ('ACTIVE','DEPRECATED','ARCHIVED'))
                OR (OLD.state = 'DEPRECATED' AND NEW.state = 'ARCHIVED')
            )
            BEGIN SELECT RAISE(ABORT, 'invalid ingress route state transition'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_ingress_route_pointer_advance
            BEFORE UPDATE OF current_ingress_route_revision_ref ON pwp_ingress_routes
            WHEN NEW.current_ingress_route_revision_ref IS NOT OLD.current_ingress_route_revision_ref
             AND NOT EXISTS (
                SELECT 1 FROM pwp_ingress_route_revisions revision
                WHERE revision.revision_ref = NEW.current_ingress_route_revision_ref
                  AND revision.subject_ref = OLD.ingress_route_ref
                  AND revision.previous_revision_ref IS OLD.current_ingress_route_revision_ref
                  AND revision.revision_seq = CASE
                      WHEN OLD.current_ingress_route_revision_ref IS NULL THEN 1
                      ELSE (SELECT revision_seq + 1 FROM pwp_ingress_route_revisions
                            WHERE revision_ref = OLD.current_ingress_route_revision_ref)
                  END
             )
            BEGIN SELECT RAISE(ABORT, 'invalid ingress route pointer advance'); END;

            CREATE TRIGGER IF NOT EXISTS pwp_project_config_immutable
            BEFORE UPDATE ON pwp_project_config_revisions
            BEGIN SELECT RAISE(ABORT, 'PWP revision immutable'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_project_config_no_delete
            BEFORE DELETE ON pwp_project_config_revisions
            BEGIN SELECT RAISE(ABORT, 'PWP revision retained'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_workspace_config_immutable
            BEFORE UPDATE ON pwp_workspace_config_revisions
            BEGIN SELECT RAISE(ABORT, 'PWP revision immutable'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_workspace_config_no_delete
            BEFORE DELETE ON pwp_workspace_config_revisions
            BEGIN SELECT RAISE(ABORT, 'PWP revision retained'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_policy_context_immutable
            BEFORE UPDATE ON pwp_policy_context_revisions
            BEGIN SELECT RAISE(ABORT, 'PWP revision immutable'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_policy_context_no_delete
            BEFORE DELETE ON pwp_policy_context_revisions
            BEGIN SELECT RAISE(ABORT, 'PWP revision retained'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_environment_binding_immutable
            BEFORE UPDATE ON pwp_environment_binding_revisions
            BEGIN SELECT RAISE(ABORT, 'PWP revision immutable'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_environment_binding_no_delete
            BEFORE DELETE ON pwp_environment_binding_revisions
            BEGIN SELECT RAISE(ABORT, 'PWP revision retained'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_ingress_route_revision_immutable
            BEFORE UPDATE ON pwp_ingress_route_revisions
            BEGIN SELECT RAISE(ABORT, 'PWP revision immutable'); END;
            CREATE TRIGGER IF NOT EXISTS pwp_ingress_route_revision_no_delete
            BEFORE DELETE ON pwp_ingress_route_revisions
            BEGIN SELECT RAISE(ABORT, 'PWP revision retained'); END;
            """
        )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Commit all writes together, or roll the entire transaction back."""

        if self.connection.in_transaction:
            raise RuntimeError("nested transactions are not supported")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield self.connection
        except BaseException:
            self.connection.rollback()
            raise
        else:
            self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> SQLiteStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
