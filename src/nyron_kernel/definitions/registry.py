"""Immutable ModuleDefinition registry backed by the concrete SQLite store."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from nyron_kernel.definitions.schema import (
    PortDefinition,
    validate_json_schema,
    validate_ports,
)
from nyron_kernel.store import SQLiteStore


EFFECT_CAPABILITY = {
    "MODEL_CALL": "MODEL_INVOKE",
    "WORKSPACE_READ": "WORKSPACE_READ",
    "WORKSPACE_WRITE": "WORKSPACE_WRITE",
    "PROCESS_EXEC": "PROCESS_EXEC",
    "NETWORK_IO": "NETWORK_ACCESS",
    "EVENT_SUBSCRIBE": "EVENT_SUBSCRIBE",
    "HUMAN_INTERACTION": "HUMAN_INTERACT",
    "CANONICAL_MUTATION": "CANONICAL_COMMAND",
}
KNOWN_EFFECT_CLASSES = frozenset({"PURE", *EFFECT_CAPABILITY})
KNOWN_CAPABILITY_TYPES = frozenset(EFFECT_CAPABILITY.values())


class DefinitionError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class ModuleDefinition:
    module_ref: str
    version: str
    input_port_definitions: tuple[PortDefinition, ...]
    output_port_definitions: tuple[PortDefinition, ...]
    config_schema: dict[str, Any]
    effect_classes: tuple[str, ...]
    required_capability_types: tuple[str, ...]
    execution_contract: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        def port_dict(port: PortDefinition) -> dict[str, Any]:
            return {
                "name": port.name,
                "value_schema": port.value_schema,
                "activation_mode": port.activation_mode,
                "connection_policy": port.connection_policy,
            }

        return {
            "module_ref": self.module_ref,
            "version": self.version,
            "input_port_definitions": [
                port_dict(port) for port in self.input_port_definitions
            ],
            "output_port_definitions": [
                port_dict(port) for port in self.output_port_definitions
            ],
            "config_schema": self.config_schema,
            "effect_classes": sorted(self.effect_classes),
            "required_capability_types": sorted(self.required_capability_types),
            "execution_contract": self.execution_contract,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ModuleDefinition:
        def port(value: dict[str, Any]) -> PortDefinition:
            return PortDefinition(
                name=value["name"],
                value_schema=value["value_schema"],
                activation_mode=value["activation_mode"],
                connection_policy=value["connection_policy"],
            )

        return cls(
            module_ref=value["module_ref"],
            version=value["version"],
            input_port_definitions=tuple(
                port(item) for item in value["input_port_definitions"]
            ),
            output_port_definitions=tuple(
                port(item) for item in value["output_port_definitions"]
            ),
            config_schema=value["config_schema"],
            effect_classes=tuple(value["effect_classes"]),
            required_capability_types=tuple(value["required_capability_types"]),
            execution_contract=value["execution_contract"],
            metadata=value["metadata"],
        )


class ModuleRegistry:
    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def register(self, definition: ModuleDefinition) -> ModuleDefinition:
        self._validate_schemas(definition)
        if (
            not isinstance(definition.module_ref, str)
            or not definition.module_ref
            or not isinstance(definition.version, str)
            or not definition.version
        ):
            raise DefinitionError("MODULE_CONTRACT_INVALID")

        try:
            contract_json = json.dumps(
                definition.as_dict(), sort_keys=True, separators=(",", ":")
            )
        except (AttributeError, TypeError, ValueError) as error:
            raise DefinitionError("MODULE_CONTRACT_INVALID") from error

        with self._store.transaction() as connection:
            existing = connection.execute(
                """
                SELECT contract_json FROM module_definitions
                WHERE module_ref = ? AND version = ?
                """,
                (definition.module_ref, definition.version),
            ).fetchone()
            if existing is not None:
                if existing["contract_json"] != contract_json:
                    raise DefinitionError(
                        "MODULE_VERSION_CONFLICT",
                        module_ref=definition.module_ref,
                        version=definition.version,
                    )
                return ModuleDefinition.from_dict(
                    json.loads(existing["contract_json"])
                )

            self._validate_effects_and_capabilities(definition)
            self._validate_execution_contract(definition.execution_contract)
            connection.execute(
                """
                INSERT INTO module_definitions(module_ref, version, contract_json)
                VALUES (?, ?, ?)
                """,
                (definition.module_ref, definition.version, contract_json),
            )
        return ModuleDefinition.from_dict(json.loads(contract_json))

    def resolve(self, module_ref: str, version: str) -> ModuleDefinition | None:
        row = self._store.connection.execute(
            """
            SELECT contract_json FROM module_definitions
            WHERE module_ref = ? AND version = ?
            """,
            (module_ref, version),
        ).fetchone()
        if row is None:
            return None
        return ModuleDefinition.from_dict(json.loads(row["contract_json"]))

    @staticmethod
    def _validate_schemas(definition: ModuleDefinition) -> None:
        try:
            validate_ports(definition.input_port_definitions, inputs=True)
            validate_ports(definition.output_port_definitions, inputs=False)
        except (AttributeError, TypeError, ValueError) as error:
            raise DefinitionError("PORT_SCHEMA_INVALID") from error
        try:
            validate_json_schema(definition.config_schema)
        except (TypeError, ValueError) as error:
            raise DefinitionError("MODULE_CONTRACT_INVALID") from error

    @staticmethod
    def _validate_effects_and_capabilities(definition: ModuleDefinition) -> None:
        if any(not isinstance(effect, str) for effect in definition.effect_classes):
            raise DefinitionError("MODULE_CONTRACT_INVALID")
        if any(
            not isinstance(capability, str)
            for capability in definition.required_capability_types
        ):
            raise DefinitionError("MODULE_CONTRACT_INVALID")
        effects = set(definition.effect_classes)
        capabilities = set(definition.required_capability_types)
        if not effects or len(effects) != len(definition.effect_classes):
            raise DefinitionError("MODULE_CONTRACT_INVALID")
        unknown_effects = effects - KNOWN_EFFECT_CLASSES
        if unknown_effects:
            raise DefinitionError(
                "UNKNOWN_EFFECT_CLASS", effect_class=sorted(unknown_effects)[0]
            )
        if len(capabilities) != len(definition.required_capability_types):
            raise DefinitionError("MODULE_CONTRACT_INVALID")
        unknown_capabilities = capabilities - KNOWN_CAPABILITY_TYPES
        if unknown_capabilities:
            raise DefinitionError(
                "UNKNOWN_CAPABILITY_TYPE",
                capability_type=sorted(unknown_capabilities)[0],
            )
        if "PURE" in effects and (len(effects) != 1 or capabilities):
            raise DefinitionError("CAPABILITY_EFFECT_MISMATCH")
        required = {
            EFFECT_CAPABILITY[effect] for effect in effects if effect != "PURE"
        }
        if not required.issubset(capabilities):
            raise DefinitionError("CAPABILITY_EFFECT_MISMATCH")

    @staticmethod
    def _validate_execution_contract(contract: object) -> None:
        if not isinstance(contract, dict) or contract.get("kind") != "execute":
            raise DefinitionError("MODULE_CONTRACT_INVALID")
