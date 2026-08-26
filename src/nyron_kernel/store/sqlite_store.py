"""Minimal SQLite state store for Nyron's current canonical facts."""

from __future__ import annotations

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
                state TEXT NOT NULL,
                PRIMARY KEY (run_ref, attempt_seq),
                FOREIGN KEY (run_ref) REFERENCES runs(run_ref)
            );
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
                )
            );

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

            CREATE TRIGGER IF NOT EXISTS effect_active_requires_admission
            BEFORE UPDATE OF state ON effect_operations
            WHEN NEW.state = 'ACTIVE'
             AND NEW.dispatch_admission_ref IS NULL
            BEGIN
                SELECT RAISE(ABORT, 'active effect requires dispatch admission');
            END;
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
