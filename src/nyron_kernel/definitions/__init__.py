"""Immutable ModuleDefinition registration and schema validation."""

from .registry import DefinitionError, ModuleDefinition, ModuleRegistry
from .schema import PortDefinition

__all__ = [
    "DefinitionError",
    "ModuleDefinition",
    "ModuleRegistry",
    "PortDefinition",
]
