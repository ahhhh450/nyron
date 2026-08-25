"""Immutable versioned CapabilityType authority vocabulary."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from nyron_kernel.store import SQLiteStore


class CapabilityTypeError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class CapabilityTypeDefinition:
    capability_type_ref: str
    version: str
    scope_schema_ref: str
    operation_schema_ref: str | None
    compatible_effect_classes: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "capability_type_ref": self.capability_type_ref,
            "version": self.version,
            "scope_schema_ref": self.scope_schema_ref,
            "operation_schema_ref": self.operation_schema_ref,
            "compatible_effect_classes": sorted(
                self.compatible_effect_classes
            ),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CapabilityTypeDefinition:
        return cls(
            capability_type_ref=value["capability_type_ref"],
            version=value["version"],
            scope_schema_ref=value["scope_schema_ref"],
            operation_schema_ref=value["operation_schema_ref"],
            compatible_effect_classes=tuple(
                value["compatible_effect_classes"]
            ),
            metadata=value["metadata"],
        )


class CapabilityTypeRegistry:
    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._store.create_capability_schema()

    def register(
        self, definition: CapabilityTypeDefinition
    ) -> CapabilityTypeDefinition:
        contract_json = self._canonical_contract(definition)
        with self._store.transaction() as connection:
            existing = connection.execute(
                """
                SELECT contract_json FROM capability_types
                WHERE capability_type_ref = ? AND version = ?
                """,
                (definition.capability_type_ref, definition.version),
            ).fetchone()
            if existing is not None:
                if existing["contract_json"] != contract_json:
                    raise CapabilityTypeError(
                        "CAPABILITY_TYPE_VERSION_CONFLICT",
                        capability_type_ref=definition.capability_type_ref,
                        version=definition.version,
                    )
                return CapabilityTypeDefinition.from_dict(
                    json.loads(existing["contract_json"])
                )
            connection.execute(
                """
                INSERT INTO capability_types(
                    capability_type_ref, version, contract_json
                ) VALUES (?, ?, ?)
                """,
                (
                    definition.capability_type_ref,
                    definition.version,
                    contract_json,
                ),
            )
        return CapabilityTypeDefinition.from_dict(json.loads(contract_json))

    def resolve(
        self, capability_type_ref: str, version: str
    ) -> CapabilityTypeDefinition | None:
        row = self._store.connection.execute(
            """
            SELECT contract_json FROM capability_types
            WHERE capability_type_ref = ? AND version = ?
            """,
            (capability_type_ref, version),
        ).fetchone()
        if row is None:
            return None
        return CapabilityTypeDefinition.from_dict(json.loads(row["contract_json"]))

    @staticmethod
    def _canonical_contract(definition: CapabilityTypeDefinition) -> str:
        values = (
            definition.capability_type_ref,
            definition.version,
            definition.scope_schema_ref,
        )
        if any(not isinstance(value, str) or not value for value in values):
            raise CapabilityTypeError("CAPABILITY_TYPE_INVALID")
        if definition.operation_schema_ref is not None and (
            not isinstance(definition.operation_schema_ref, str)
            or not definition.operation_schema_ref
        ):
            raise CapabilityTypeError("CAPABILITY_TYPE_INVALID")
        effect_classes = definition.compatible_effect_classes
        if (
            not isinstance(effect_classes, tuple)
            or any(not isinstance(value, str) or not value for value in effect_classes)
            or len(effect_classes) != len(set(effect_classes))
            or not isinstance(definition.metadata, dict)
        ):
            raise CapabilityTypeError("CAPABILITY_TYPE_INVALID")
        try:
            return json.dumps(
                definition.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as error:
            raise CapabilityTypeError("CAPABILITY_TYPE_INVALID") from error
