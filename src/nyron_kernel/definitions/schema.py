"""Small validation primitives for ModuleDefinition contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


INPUT_ACTIVATION_MODES = frozenset(
    {"TRIGGER", "REQUIRED_NEXT", "REQUIRED_LATEST", "OPTIONAL_LATEST"}
)
SCHEMA_TYPES = frozenset(
    {"array", "boolean", "integer", "null", "number", "object", "string"}
)


@dataclass(frozen=True)
class PortDefinition:
    name: str
    value_schema: dict[str, Any]
    activation_mode: str | None = None


def validate_json_schema(schema: object) -> None:
    """Validate the JSON-schema subset used by this implementation slice."""

    if not isinstance(schema, dict) or schema.get("type") not in SCHEMA_TYPES:
        raise ValueError("schema must be an object with a known type")

    schema_type = schema["type"]
    if schema_type == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, dict):
            raise ValueError("object schema properties must be an object")
        if (
            not isinstance(required, list)
            or any(not isinstance(item, str) for item in required)
            or len(required) != len(set(required))
            or any(item not in properties for item in required)
        ):
            raise ValueError("object schema required must name unique properties")
        for child in properties.values():
            validate_json_schema(child)
        if "additionalProperties" in schema and not isinstance(
            schema["additionalProperties"], bool
        ):
            raise ValueError("additionalProperties must be boolean")
    elif schema_type == "array":
        if "items" not in schema:
            raise ValueError("array schema must declare items")
        validate_json_schema(schema["items"])


def validate_ports(ports: tuple[PortDefinition, ...], *, inputs: bool) -> None:
    names: set[str] = set()
    for port in ports:
        if (
            not isinstance(port.name, str)
            or not port.name
            or port.name in names
        ):
            raise ValueError("port names must be non-empty and unique")
        names.add(port.name)
        validate_json_schema(port.value_schema)
        if inputs and port.activation_mode not in INPUT_ACTIVATION_MODES:
            raise ValueError("input port must declare a known activation mode")
        if not inputs and port.activation_mode is not None:
            raise ValueError("output port cannot declare an activation mode")
