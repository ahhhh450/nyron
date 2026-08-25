"""Runtime-owned transactional Delivery binding and Activation creation."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.store import SQLiteStore

from .delivery import Delivery


class ActivationError(RuntimeError):
    """Fail-closed Activation creation error with a stable reason code."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class InputBinding:
    port_ref: str
    activation_mode: str
    delivery_ref: str | None


@dataclass(frozen=True)
class Activation:
    activation_ref: str
    execution_ref: str
    graph_revision_ref: str
    module_instance_revision_ref: str
    trigger_delivery_ref: str
    input_bindings: tuple[InputBinding, ...]
    static_accounting_scope_ref: str
    created_event_ref: str


class ActivationRepository:
    """Evaluate readiness and atomically persist one immutable Activation."""

    _CONSUMPTIVE_MODES = frozenset({"TRIGGER", "REQUIRED_NEXT"})

    def __init__(self, store: SQLiteStore, registry: ModuleRegistry) -> None:
        self._store = store
        self._registry = registry
        self._store.create_activation_schema()

    def create_next(
        self,
        *,
        activation_ref: str,
        execution_ref: str,
        module_instance_revision_ref: str,
        created_event_ref: str,
    ) -> Activation:
        values = (
            activation_ref,
            execution_ref,
            module_instance_revision_ref,
            created_event_ref,
        )
        if any(not isinstance(value, str) or not value for value in values):
            raise ActivationError("ACTIVATION_INVALID")

        try:
            with self._store.transaction() as connection:
                existing = self._resolve_with(connection, activation_ref)
                if existing is not None:
                    if (
                        existing.execution_ref != execution_ref
                        or existing.module_instance_revision_ref
                        != module_instance_revision_ref
                        or existing.created_event_ref != created_event_ref
                    ):
                        raise ActivationError(
                            "ACTIVATION_IDENTITY_CONFLICT",
                            activation_ref=activation_ref,
                        )
                    return existing

                execution = connection.execute(
                    """
                    SELECT graph_revision_ref, state
                    FROM workflow_executions WHERE execution_ref = ?
                    """,
                    (execution_ref,),
                ).fetchone()
                if execution is None or execution["state"] != "ADMITTED":
                    raise ActivationError(
                        "WORKFLOW_EXECUTION_NOT_ADMITTED",
                        execution_ref=execution_ref,
                    )

                instance = connection.execute(
                    """
                    SELECT module_ref, module_version,
                           input_port_contract_json,
                           static_accounting_scope_ref
                    FROM module_instance_revisions
                    WHERE module_instance_revision_ref = ?
                      AND graph_revision_ref = ?
                    """,
                    (
                        module_instance_revision_ref,
                        execution["graph_revision_ref"],
                    ),
                ).fetchone()
                if instance is None:
                    raise ActivationError(
                        "ACTIVATION_TARGET_MISMATCH",
                        module_instance_revision_ref=module_instance_revision_ref,
                    )

                modes = self._resolve_input_modes(
                    instance["module_ref"],
                    instance["module_version"],
                    instance["input_port_contract_json"],
                )
                trigger = self._select_delivery(
                    connection,
                    execution_ref,
                    execution["graph_revision_ref"],
                    module_instance_revision_ref,
                    tuple(
                        port for port, mode in modes.items() if mode == "TRIGGER"
                    ),
                    oldest=True,
                    pending=True,
                )
                if trigger is None:
                    raise ActivationError("ACTIVATION_TRIGGER_NOT_READY")

                bindings: list[InputBinding] = []
                consumptive: list[Delivery] = []
                for port_ref, mode in sorted(modes.items()):
                    if mode == "TRIGGER":
                        delivery = (
                            trigger
                            if trigger.target_port_ref == port_ref
                            else None
                        )
                    elif mode == "REQUIRED_NEXT":
                        delivery = self._select_delivery(
                            connection,
                            execution_ref,
                            execution["graph_revision_ref"],
                            module_instance_revision_ref,
                            (port_ref,),
                            oldest=True,
                            pending=True,
                        )
                    else:
                        delivery = self._select_delivery(
                            connection,
                            execution_ref,
                            execution["graph_revision_ref"],
                            module_instance_revision_ref,
                            (port_ref,),
                            oldest=False,
                            pending=False,
                        )

                    if delivery is None and mode != "OPTIONAL_LATEST":
                        raise ActivationError(
                            "ACTIVATION_REQUIRED_INPUT_NOT_READY",
                            port_ref=port_ref,
                            activation_mode=mode,
                        )
                    bindings.append(
                        InputBinding(
                            port_ref,
                            mode,
                            delivery.delivery_ref if delivery is not None else None,
                        )
                    )
                    if delivery is not None and mode in self._CONSUMPTIVE_MODES:
                        consumptive.append(delivery)

                for delivery in consumptive:
                    connection.execute(
                        """
                        INSERT INTO delivery_bindings(
                            delivery_ref, packet_ref, graph_revision_ref,
                            edge_ref, target_port_ref, activation_ref
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            delivery.delivery_ref,
                            delivery.packet_ref,
                            delivery.graph_revision_ref,
                            delivery.edge_ref,
                            delivery.target_port_ref,
                            activation_ref,
                        ),
                    )

                serialized = self._serialize_bindings(bindings)
                connection.execute(
                    """
                    INSERT INTO activations(
                        activation_ref, execution_ref, graph_revision_ref,
                        module_instance_revision_ref, trigger_delivery_ref,
                        input_bindings_json, static_accounting_scope_ref,
                        created_event_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        activation_ref,
                        execution_ref,
                        execution["graph_revision_ref"],
                        module_instance_revision_ref,
                        trigger.delivery_ref,
                        serialized,
                        instance["static_accounting_scope_ref"],
                        created_event_ref,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO activation_created_events(
                        created_event_ref, activation_ref, event_kind
                    ) VALUES (?, ?, 'ActivationCreated')
                    """,
                    (created_event_ref, activation_ref),
                )
        except sqlite3.IntegrityError as error:
            raise ActivationError(
                "ACTIVATION_TRANSACTION_CONFLICT",
                activation_ref=activation_ref,
            ) from error

        activation = self.resolve(activation_ref)
        if activation is None:  # pragma: no cover - guards store corruption
            raise ActivationError("ACTIVATION_TRANSACTION_FAILED")
        return activation

    def resolve(self, activation_ref: str) -> Activation | None:
        return self._resolve_with(self._store.connection, activation_ref)

    def binding_activation_ref(self, delivery_ref: str) -> str | None:
        row = self._store.connection.execute(
            "SELECT activation_ref FROM delivery_bindings WHERE delivery_ref = ?",
            (delivery_ref,),
        ).fetchone()
        return row["activation_ref"] if row is not None else None

    def _resolve_input_modes(
        self,
        module_ref: str,
        module_version: str,
        input_port_contract_json: str,
    ) -> dict[str, str]:
        definition = self._registry.resolve(module_ref, module_version)
        if definition is None:
            raise ActivationError(
                "UNRESOLVED_MODULE_REFERENCE",
                module_ref=module_ref,
                module_version=module_version,
            )
        definition_modes = {
            port.name: port.activation_mode
            for port in definition.input_port_definitions
        }
        persisted_modes = json.loads(input_port_contract_json)
        if persisted_modes != definition_modes:
            raise ActivationError("ACTIVATION_INPUT_CONTRACT_MISMATCH")
        return definition_modes  # type: ignore[return-value]

    @staticmethod
    def _select_delivery(
        connection: sqlite3.Connection,
        execution_ref: str,
        graph_revision_ref: str,
        module_instance_revision_ref: str,
        port_refs: tuple[str, ...],
        *,
        oldest: bool,
        pending: bool,
    ) -> Delivery | None:
        if not port_refs:
            return None
        placeholders = ",".join("?" for _ in port_refs)
        pending_clause = "AND b.delivery_ref IS NULL" if pending else ""
        direction = "ASC" if oldest else "DESC"
        row = connection.execute(
            f"""
            SELECT d.packet_ref, d.graph_revision_ref, d.edge_ref,
                   d.target_module_instance_revision_ref, d.target_port_ref,
                   d.source_packet_seq, d.edge_ordinal, d.target_port_ordinal
            FROM deliveries AS d
            JOIN packets AS p ON p.packet_ref = d.packet_ref
            LEFT JOIN delivery_bindings AS b
              ON b.packet_ref = d.packet_ref
             AND b.graph_revision_ref = d.graph_revision_ref
             AND b.edge_ref = d.edge_ref
             AND b.target_port_ref = d.target_port_ref
            WHERE p.execution_ref = ?
              AND p.graph_revision_ref = ?
              AND d.graph_revision_ref = p.graph_revision_ref
              AND d.target_module_instance_revision_ref = ?
              AND d.target_port_ref IN ({placeholders})
              {pending_clause}
            ORDER BY d.source_packet_seq {direction},
                     d.edge_ordinal {direction},
                     d.target_port_ordinal {direction},
                     d.packet_ref {direction}, d.edge_ref {direction},
                     d.target_port_ref {direction}
            LIMIT 1
            """,
            (
                execution_ref,
                graph_revision_ref,
                module_instance_revision_ref,
                *port_refs,
            ),
        ).fetchone()
        if row is None:
            return None
        return Delivery(**dict(row))

    @staticmethod
    def _serialize_bindings(bindings: list[InputBinding]) -> str:
        return json.dumps(
            [
                {
                    "activation_mode": binding.activation_mode,
                    "delivery_ref": binding.delivery_ref,
                    "port_ref": binding.port_ref,
                }
                for binding in bindings
            ],
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _resolve_with(
        connection: sqlite3.Connection, activation_ref: str
    ) -> Activation | None:
        row = connection.execute(
            """
            SELECT activation_ref, execution_ref, graph_revision_ref,
                   module_instance_revision_ref, trigger_delivery_ref,
                   input_bindings_json, static_accounting_scope_ref,
                   created_event_ref
            FROM activations WHERE activation_ref = ?
            """,
            (activation_ref,),
        ).fetchone()
        if row is None:
            return None
        bindings = tuple(
            InputBinding(**value) for value in json.loads(row["input_bindings_json"])
        )
        return Activation(
            activation_ref=row["activation_ref"],
            execution_ref=row["execution_ref"],
            graph_revision_ref=row["graph_revision_ref"],
            module_instance_revision_ref=row["module_instance_revision_ref"],
            trigger_delivery_ref=row["trigger_delivery_ref"],
            input_bindings=bindings,
            static_accounting_scope_ref=row["static_accounting_scope_ref"],
            created_event_ref=row["created_event_ref"],
        )
