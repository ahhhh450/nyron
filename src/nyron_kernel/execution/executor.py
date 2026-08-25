"""Concrete Phase-2 dispatch and terminal canonical commit path."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Callable

from nyron_kernel.definitions import ModuleDefinition, ModuleRegistry
from nyron_kernel.host import Completed, Failed, TrustedModuleHost
from nyron_kernel.store import SQLiteStore

from .activation import Activation, ActivationRepository
from .attempt import AttemptAuthority
from .delivery import Delivery
from .packet import Packet, PacketRepository
from .value import DurableValueError, DurableValueRepository


class AttemptExecutionError(RuntimeError):
    """Fail-closed Runtime execution error with a machine-readable code."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class _Invocation:
    authority: AttemptAuthority
    module_ref_version: str
    definition: ModuleDefinition
    inputs: dict[str, Any]
    config: dict[str, Any]


class AttemptExecutor:
    """Dispatch one current CREATED Attempt through the accepted trusted host."""

    def __init__(
        self,
        store: SQLiteStore,
        registry: ModuleRegistry,
        config_loader: Callable[[str, str], object],
        host: TrustedModuleHost | None = None,
    ) -> None:
        self._store = store
        self._registry = registry
        self._config_loader = config_loader
        self._host = host or TrustedModuleHost(registry)
        self._values = DurableValueRepository(store)
        self._packets = PacketRepository(store)
        self._activations = ActivationRepository(store, registry)

    def execute(
        self, run_ref: str, *, inject_failure: str | None = None
    ) -> tuple[Packet, ...] | Failed:
        """Cross the durable dispatch boundary, invoke, and commit the result."""

        invocation = self._prepare_invocation(run_ref)
        self._mark_active(invocation.authority)
        if inject_failure == "after_active_before_execute":
            raise AttemptExecutionError("INJECTED_AFTER_ACTIVE")

        try:
            result = self._host.execute(
                invocation.module_ref_version,
                invocation.inputs,
                invocation.config,
                runtime_context=None,
            )
        except Exception as error:
            raise AttemptExecutionError("MODULE_INVOCATION_INTERRUPTED") from error

        if isinstance(result, Failed):
            self._commit_failed(invocation.authority)
            return result
        if not isinstance(result, Completed):
            self._commit_failed(invocation.authority)
            raise AttemptExecutionError("MODULE_RESULT_INVALID")

        try:
            self._prepare_durable_outputs(invocation, result.outputs)
        except AttemptExecutionError:
            self._commit_failed(invocation.authority)
            raise

        if inject_failure == "before_canonical_transaction":
            raise AttemptExecutionError("INJECTED_BEFORE_CANONICAL_TRANSACTION")
        return self.commit_prepared_success(
            invocation.authority,
            inject_failure=inject_failure,
        )

    def commit_prepared_success(
        self,
        authority: AttemptAuthority,
        *,
        inject_failure: str | None = None,
    ) -> tuple[Packet, ...]:
        """Commit already-durable outputs without crossing execute again."""

        # Fast fail avoids interpreting prepared values for an authority tuple
        # that is already stale; the same complete check is repeated inside
        # the canonical write transaction below.
        self._verify_authority_with(self._store.connection, authority)
        evidence = self._load_current_evidence(authority.run_ref)
        definition = evidence["definition"]
        output_values: dict[str, tuple[str, str]] = {}
        for port in definition.output_port_definitions:
            value_ref = self.output_value_ref(authority, port.name)
            try:
                value = self._values.resolve(value_ref)
            except DurableValueError as error:
                raise AttemptExecutionError(error.code, **error.context) from error
            if not self._matches_schema(value, port.value_schema):
                raise AttemptExecutionError(
                    "MODULE_OUTPUT_SCHEMA_MISMATCH", port_ref=port.name
                )
            output_values[port.name] = (
                value_ref,
                self._schema_ref(port.value_schema),
            )

        event_ref = self.terminal_event_ref(authority)
        caused_by_ref = f"attempt:{authority.run_ref}:{authority.attempt_seq}"
        packets: list[Packet] = []
        try:
            with self._store.transaction() as connection:
                current = self._verify_authority_with(connection, authority)
                attempt_state = current["attempt_state"]
                run_state = current["run_state"]
                if attempt_state == "SUCCEEDED" and run_state == "SUCCESS":
                    return self._resolve_committed_outputs_with(
                        connection, authority, tuple(output_values), event_ref
                    )
                if attempt_state != "ACTIVE" or run_state != "OPEN":
                    raise AttemptExecutionError("STALE_ATTEMPT_REJECTED")

                for value_ref, _ in output_values.values():
                    if not self._values.exists_with(connection, value_ref):
                        raise AttemptExecutionError(
                            "UNRESOLVED_DURABLE_VALUE", value_ref=value_ref
                        )

                connection.execute(
                    """
                    UPDATE run_attempts SET state = 'SUCCEEDED'
                    WHERE run_ref = ? AND attempt_seq = ?
                    """,
                    (authority.run_ref, authority.attempt_seq),
                )
                connection.execute(
                    """
                    UPDATE runs
                    SET state = 'SUCCESS', terminal_attempt_seq = ?,
                        terminal_event_ref = ?
                    WHERE run_ref = ?
                    """,
                    (authority.attempt_seq, event_ref, authority.run_ref),
                )
                if inject_failure == "inside_after_terminal_writes":
                    raise AttemptExecutionError(
                        "INJECTED_INSIDE_CANONICAL_TRANSACTION"
                    )

                for port_ref, (value_ref, schema_ref) in sorted(
                    output_values.items()
                ):
                    packets.append(
                        self._packets.commit_in_transaction(
                            connection,
                            packet_ref=self.output_packet_ref(authority, port_ref),
                            execution_ref=authority.execution_ref,
                            graph_revision_ref=current["graph_revision_ref"],
                            source_kind="MODULE_OUTPUT",
                            source_ref=current["module_instance_revision_ref"],
                            source_port_ref=port_ref,
                            value_ref=value_ref,
                            schema_ref=schema_ref,
                            caused_by_ref=caused_by_ref,
                            created_event_ref=event_ref,
                        )
                    )
                connection.execute(
                    """
                    INSERT INTO run_terminal_events(
                        event_ref, execution_ref, activation_ref, run_ref,
                        attempt_seq, event_kind
                    ) VALUES (?, ?, ?, ?, ?, 'RunSucceeded')
                    """,
                    (
                        event_ref,
                        authority.execution_ref,
                        authority.activation_ref,
                        authority.run_ref,
                        authority.attempt_seq,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise AttemptExecutionError("TERMINAL_COMMIT_CONFLICT") from error
        return tuple(packets)

    def _prepare_invocation(self, run_ref: str) -> _Invocation:
        row = self._store.connection.execute(
            """
            SELECT r.execution_ref, r.activation_ref, r.run_ref,
                   r.current_attempt_seq, r.fencing_generation,
                   r.state AS run_state, a.fencing_token,
                   a.state AS attempt_state
            FROM runs AS r
            JOIN run_attempts AS a
              ON a.run_ref = r.run_ref
             AND a.attempt_seq = r.current_attempt_seq
            WHERE r.run_ref = ?
            """,
            (run_ref,),
        ).fetchone()
        if row is None:
            raise AttemptExecutionError("UNRESOLVED_RUN_REFERENCE")
        if row["attempt_state"] == "ACTIVE":
            raise AttemptExecutionError("ATTEMPT_DISPATCH_AMBIGUOUS")
        if row["attempt_state"] != "CREATED" or row["run_state"] != "OPEN":
            raise AttemptExecutionError("ATTEMPT_NOT_DISPATCHABLE")

        authority = AttemptAuthority(
            execution_ref=row["execution_ref"],
            activation_ref=row["activation_ref"],
            run_ref=row["run_ref"],
            attempt_seq=row["current_attempt_seq"],
            fencing_token=row["fencing_token"],
            fencing_generation=row["fencing_generation"],
        )
        evidence = self._load_current_evidence(run_ref)
        activation = evidence["activation"]
        definition = evidence["definition"]
        inputs = self._resolve_exact_inputs(activation, definition)

        try:
            loaded = self._config_loader(
                evidence["config_ref"], evidence["config_hash"]
            )
            config = json.loads(
                json.dumps(loaded, sort_keys=True, separators=(",", ":"))
            )
        except Exception as error:
            raise AttemptExecutionError("CONFIG_RESOLUTION_FAILED") from error
        if not isinstance(config, dict) or not self._matches_schema(
            config, definition.config_schema
        ):
            raise AttemptExecutionError("CONFIG_SCHEMA_MISMATCH")

        return _Invocation(
            authority=authority,
            module_ref_version=(
                f"{evidence['module_ref']}@{evidence['module_version']}"
            ),
            definition=definition,
            inputs=inputs,
            config=config,
        )

    def _load_current_evidence(self, run_ref: str) -> dict[str, Any]:
        row = self._store.connection.execute(
            """
            SELECT r.activation_ref, r.execution_ref,
                   a.graph_revision_ref, a.module_instance_revision_ref,
                   m.module_ref, m.module_version, m.config_ref, m.config_hash,
                   m.input_port_contract_json, m.output_port_contract_json
            FROM runs AS r
            JOIN activations AS a ON a.activation_ref = r.activation_ref
            JOIN workflow_executions AS w
              ON w.execution_ref = r.execution_ref
             AND w.graph_revision_ref = a.graph_revision_ref
             AND w.state = 'ADMITTED'
            JOIN module_instance_revisions AS m
              ON m.module_instance_revision_ref =
                 a.module_instance_revision_ref
             AND m.graph_revision_ref = a.graph_revision_ref
            WHERE r.run_ref = ? AND a.execution_ref = r.execution_ref
            """,
            (run_ref,),
        ).fetchone()
        if row is None:
            raise AttemptExecutionError("RUNTIME_IDENTITY_MISMATCH")
        definition = self._registry.resolve(row["module_ref"], row["module_version"])
        if definition is None:
            raise AttemptExecutionError("UNRESOLVED_MODULE_REFERENCE")
        expected_inputs = {
            port.name: port.activation_mode
            for port in definition.input_port_definitions
        }
        expected_outputs = {
            port.name: port.value_schema
            for port in definition.output_port_definitions
        }
        if (
            json.loads(row["input_port_contract_json"]) != expected_inputs
            or json.loads(row["output_port_contract_json"]) != expected_outputs
        ):
            raise AttemptExecutionError("MODULE_INSTANCE_CONTRACT_MISMATCH")
        activation = self._activations.resolve(row["activation_ref"])
        if activation is None:
            raise AttemptExecutionError("UNRESOLVED_ACTIVATION_REFERENCE")
        return {
            **dict(row),
            "activation": activation,
            "definition": definition,
        }

    def _resolve_exact_inputs(
        self, activation: Activation, definition: ModuleDefinition
    ) -> dict[str, Any]:
        expected = {
            port.name: (port.activation_mode, port.value_schema)
            for port in definition.input_port_definitions
        }
        actual = {
            binding.port_ref: (binding.activation_mode, binding.delivery_ref)
            for binding in activation.input_bindings
        }
        if set(actual) != set(expected) or any(
            actual[name][0] != expected[name][0] for name in expected
        ):
            raise AttemptExecutionError("ACTIVATION_INPUT_CONTRACT_MISMATCH")

        inputs: dict[str, Any] = {}
        for port_ref, (_, schema) in expected.items():
            delivery_ref = actual[port_ref][1]
            if delivery_ref is None:
                inputs[port_ref] = None
                continue
            matches: list[sqlite3.Row] = []
            rows = self._store.connection.execute(
                """
                SELECT d.*, p.execution_ref, p.value_ref
                FROM deliveries AS d
                JOIN packets AS p ON p.packet_ref = d.packet_ref
                WHERE d.graph_revision_ref = ?
                  AND d.target_module_instance_revision_ref = ?
                  AND d.target_port_ref = ?
                  AND p.execution_ref = ?
                """,
                (
                    activation.graph_revision_ref,
                    activation.module_instance_revision_ref,
                    port_ref,
                    activation.execution_ref,
                ),
            ).fetchall()
            for row in rows:
                delivery = Delivery(
                    **{
                        name: row[name]
                        for name in (
                            "packet_ref", "graph_revision_ref", "edge_ref",
                            "target_module_instance_revision_ref",
                            "target_port_ref", "source_packet_seq",
                            "edge_ordinal", "target_port_ordinal",
                        )
                    }
                )
                if delivery.delivery_ref == delivery_ref:
                    matches.append(row)
            if len(matches) != 1:
                raise AttemptExecutionError(
                    "ACTIVATION_DELIVERY_REFERENCE_INVALID", port_ref=port_ref
                )
            try:
                value = self._values.resolve(matches[0]["value_ref"])
            except DurableValueError as error:
                raise AttemptExecutionError(error.code, **error.context) from error
            if not self._matches_schema(value, schema):
                raise AttemptExecutionError(
                    "MODULE_INPUT_SCHEMA_MISMATCH", port_ref=port_ref
                )
            inputs[port_ref] = value
        return inputs

    def _mark_active(self, authority: AttemptAuthority) -> None:
        with self._store.transaction() as connection:
            current = self._verify_authority_with(connection, authority)
            if current["run_state"] != "OPEN":
                raise AttemptExecutionError("ATTEMPT_NOT_DISPATCHABLE")
            if current["attempt_state"] == "ACTIVE":
                raise AttemptExecutionError("ATTEMPT_DISPATCH_AMBIGUOUS")
            if current["attempt_state"] != "CREATED":
                raise AttemptExecutionError("ATTEMPT_NOT_DISPATCHABLE")
            connection.execute(
                """
                UPDATE run_attempts SET state = 'ACTIVE'
                WHERE run_ref = ? AND attempt_seq = ? AND state = 'CREATED'
                """,
                (authority.run_ref, authority.attempt_seq),
            )

    def _commit_failed(self, authority: AttemptAuthority) -> None:
        with self._store.transaction() as connection:
            current = self._verify_authority_with(connection, authority)
            if current["attempt_state"] != "ACTIVE":
                raise AttemptExecutionError("STALE_ATTEMPT_REJECTED")
            connection.execute(
                """
                UPDATE run_attempts SET state = 'FAILED'
                WHERE run_ref = ? AND attempt_seq = ?
                """,
                (authority.run_ref, authority.attempt_seq),
            )

    def _prepare_durable_outputs(
        self, invocation: _Invocation, outputs: object
    ) -> None:
        if not isinstance(outputs, dict):
            raise AttemptExecutionError("MODULE_RESULT_INVALID")
        schemas = {
            port.name: port.value_schema
            for port in invocation.definition.output_port_definitions
        }
        if set(outputs) != set(schemas):
            raise AttemptExecutionError("MODULE_OUTPUT_SCHEMA_MISMATCH")
        for port_ref, schema in schemas.items():
            value = outputs[port_ref]
            if not self._matches_schema(value, schema):
                raise AttemptExecutionError(
                    "MODULE_OUTPUT_SCHEMA_MISMATCH", port_ref=port_ref
                )
            self._values.put(
                self.output_value_ref(invocation.authority, port_ref), value
            )

    @staticmethod
    def _verify_authority_with(
        connection: sqlite3.Connection, authority: AttemptAuthority
    ) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT r.execution_ref, r.activation_ref, r.run_ref,
                   r.current_attempt_seq, r.fencing_generation,
                   r.state AS run_state, a.fencing_token,
                   a.state AS attempt_state, x.graph_revision_ref,
                   x.module_instance_revision_ref
            FROM runs AS r
            JOIN run_attempts AS a
              ON a.run_ref = r.run_ref
             AND a.attempt_seq = r.current_attempt_seq
            JOIN activations AS x ON x.activation_ref = r.activation_ref
            JOIN workflow_executions AS w
              ON w.execution_ref = r.execution_ref
             AND w.graph_revision_ref = x.graph_revision_ref
             AND w.state = 'ADMITTED'
            WHERE r.run_ref = ? AND x.execution_ref = r.execution_ref
            """,
            (authority.run_ref,),
        ).fetchone()
        if row is None or (
            row["execution_ref"] != authority.execution_ref
            or row["activation_ref"] != authority.activation_ref
            or row["run_ref"] != authority.run_ref
            or row["current_attempt_seq"] != authority.attempt_seq
            or row["fencing_token"] != authority.fencing_token
            or row["fencing_generation"] != authority.fencing_generation
        ):
            raise AttemptExecutionError("STALE_ATTEMPT_REJECTED")
        return row

    def _resolve_committed_outputs_with(
        self,
        connection: sqlite3.Connection,
        authority: AttemptAuthority,
        port_refs: tuple[str, ...],
        event_ref: str,
    ) -> tuple[Packet, ...]:
        event = connection.execute(
            """
            SELECT 1 FROM run_terminal_events
            WHERE event_ref = ? AND run_ref = ? AND attempt_seq = ?
            """,
            (event_ref, authority.run_ref, authority.attempt_seq),
        ).fetchone()
        if event is None:
            raise AttemptExecutionError("TERMINAL_COMMIT_INCONSISTENT")
        packets = tuple(
            self._packets._resolve_with(  # narrow same-transaction read
                connection, self.output_packet_ref(authority, port_ref)
            )
            for port_ref in sorted(port_refs)
        )
        if any(packet is None for packet in packets):
            raise AttemptExecutionError("TERMINAL_COMMIT_INCONSISTENT")
        return packets  # type: ignore[return-value]

    @staticmethod
    def _matches_schema(value: object, schema: dict[str, Any]) -> bool:
        schema_type = schema.get("type")
        if schema_type == "string":
            return isinstance(value, str)
        if schema_type == "boolean":
            return isinstance(value, bool)
        if schema_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if schema_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if schema_type == "null":
            return value is None
        if schema_type == "array":
            return isinstance(value, list) and all(
                AttemptExecutor._matches_schema(item, schema["items"])
                for item in value
            )
        if schema_type == "object":
            if not isinstance(value, dict) or any(
                not isinstance(key, str) for key in value
            ):
                return False
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            if any(key not in value for key in required):
                return False
            if schema.get("additionalProperties") is False and any(
                key not in properties for key in value
            ):
                return False
            return all(
                key not in value
                or AttemptExecutor._matches_schema(value[key], child)
                for key, child in properties.items()
            )
        return False

    @staticmethod
    def _stable_ref(kind: str, values: tuple[object, ...]) -> str:
        encoded = json.dumps(values, separators=(",", ":")).encode("utf-8")
        return f"{kind}:sha256:{sha256(encoded).hexdigest()}"

    @classmethod
    def output_value_ref(
        cls, authority: AttemptAuthority, port_ref: str
    ) -> str:
        return cls._stable_ref(
            "value",
            (authority.run_ref, authority.attempt_seq, port_ref),
        )

    @classmethod
    def output_packet_ref(
        cls, authority: AttemptAuthority, port_ref: str
    ) -> str:
        return cls._stable_ref(
            "packet",
            (authority.run_ref, authority.attempt_seq, port_ref),
        )

    @classmethod
    def terminal_event_ref(cls, authority: AttemptAuthority) -> str:
        return cls._stable_ref(
            "event", (authority.run_ref, authority.attempt_seq, "RunSucceeded")
        )

    @classmethod
    def _schema_ref(cls, schema: dict[str, Any]) -> str:
        encoded = json.dumps(
            schema, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return f"schema:sha256:{sha256(encoded).hexdigest()}"
