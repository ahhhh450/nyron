"""ProductNodeDefinition — Product-owned wrapper around one ModuleDefinition@version.

NYRON-T-20260828-171 Node Foundation v0.1. Binding guardrails (see
``coordination/STATUS.md`` "Product-Specific Guardrails"):

    ModuleDefinition != ProductNodeDefinition
    Product config != CapabilityGrant
    Product declaration != execution authority

A ``ProductNodeDefinition`` never copies, shadows, or re-derives Module
port/effect/capability contracts. It binds exactly one immutable
``module_ref@version`` by reference (never ``latest``/``current``) and
exposes Product-facing ports that alias the bound Module's declared ports
by exact name. Its config schema may only narrow the bound Module's own
``config_schema`` -- it can never accept a property the Module itself does
not already declare, so Product can never grant itself authority the
Module does not have.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.definitions.schema import validate_json_schema
from nyron_kernel.store import SQLiteStore


class ProductDefinitionError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class ProductPortBinding:
    """A stable Product-facing port name bound to one exact Module port."""

    product_port_ref: str
    bound_module_port_name: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "product_port_ref": self.product_port_ref,
            "bound_module_port_name": self.bound_module_port_name,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ProductPortBinding:
        return cls(
            product_port_ref=value["product_port_ref"],
            bound_module_port_name=value["bound_module_port_name"],
        )


@dataclass(frozen=True)
class ProductNodeDefinition:
    product_node_type_ref: str
    product_node_version: str
    bound_module_ref: str
    bound_module_version: str
    input_port_bindings: tuple[ProductPortBinding, ...]
    output_port_bindings: tuple[ProductPortBinding, ...]
    product_config_schema: dict[str, Any]
    display_metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "product_node_type_ref": self.product_node_type_ref,
            "product_node_version": self.product_node_version,
            "bound_module_ref": self.bound_module_ref,
            "bound_module_version": self.bound_module_version,
            "input_port_bindings": [
                binding.as_dict() for binding in self.input_port_bindings
            ],
            "output_port_bindings": [
                binding.as_dict() for binding in self.output_port_bindings
            ],
            "product_config_schema": self.product_config_schema,
            "display_metadata": self.display_metadata,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ProductNodeDefinition:
        return cls(
            product_node_type_ref=value["product_node_type_ref"],
            product_node_version=value["product_node_version"],
            bound_module_ref=value["bound_module_ref"],
            bound_module_version=value["bound_module_version"],
            input_port_bindings=tuple(
                ProductPortBinding.from_dict(item)
                for item in value["input_port_bindings"]
            ),
            output_port_bindings=tuple(
                ProductPortBinding.from_dict(item)
                for item in value["output_port_bindings"]
            ),
            product_config_schema=value["product_config_schema"],
            display_metadata=value["display_metadata"],
        )

    def bound_module_ref_version(self) -> str:
        return f"{self.bound_module_ref}@{self.bound_module_version}"


class ProductNodeRegistry:
    """Register and exactly resolve immutable ``ProductNodeDefinition``s."""

    def __init__(self, store: SQLiteStore, module_registry: ModuleRegistry) -> None:
        self._store = store
        self._modules = module_registry
        self._store.create_product_schema()

    def register(self, definition: ProductNodeDefinition) -> ProductNodeDefinition:
        self._validate_shape(definition)

        module_definition = self._modules.resolve(
            definition.bound_module_ref, definition.bound_module_version
        )
        if module_definition is None:
            raise ProductDefinitionError(
                "UNRESOLVED_MODULE_REFERENCE",
                bound_module_ref=definition.bound_module_ref,
                bound_module_version=definition.bound_module_version,
            )

        module_input_names = {
            port.name for port in module_definition.input_port_definitions
        }
        module_output_names = {
            port.name for port in module_definition.output_port_definitions
        }
        for binding in definition.input_port_bindings:
            if binding.bound_module_port_name not in module_input_names:
                raise ProductDefinitionError(
                    "PRODUCT_PORT_BINDING_UNRESOLVED",
                    bound_module_port_name=binding.bound_module_port_name,
                )
        for binding in definition.output_port_bindings:
            if binding.bound_module_port_name not in module_output_names:
                raise ProductDefinitionError(
                    "PRODUCT_PORT_BINDING_UNRESOLVED",
                    bound_module_port_name=binding.bound_module_port_name,
                )
        if module_input_names != {
            binding.bound_module_port_name
            for binding in definition.input_port_bindings
        }:
            raise ProductDefinitionError("PRODUCT_PORT_BINDING_INCOMPLETE")
        if module_output_names != {
            binding.bound_module_port_name
            for binding in definition.output_port_bindings
        }:
            raise ProductDefinitionError("PRODUCT_PORT_BINDING_INCOMPLETE")

        self._validate_config_narrowing(
            definition.product_config_schema, module_definition.config_schema
        )

        try:
            contract_json = json.dumps(
                definition.as_dict(), sort_keys=True, separators=(",", ":")
            )
        except (TypeError, ValueError) as error:
            raise ProductDefinitionError("PRODUCT_NODE_CONTRACT_INVALID") from error

        with self._store.transaction() as connection:
            existing = connection.execute(
                """
                SELECT contract_json FROM product_node_definitions
                WHERE product_node_type_ref = ? AND product_node_version = ?
                """,
                (definition.product_node_type_ref, definition.product_node_version),
            ).fetchone()
            if existing is not None:
                if existing["contract_json"] != contract_json:
                    raise ProductDefinitionError(
                        "PRODUCT_NODE_VERSION_CONFLICT",
                        product_node_type_ref=definition.product_node_type_ref,
                        product_node_version=definition.product_node_version,
                    )
                return ProductNodeDefinition.from_dict(
                    json.loads(existing["contract_json"])
                )
            connection.execute(
                """
                INSERT INTO product_node_definitions(
                    product_node_type_ref, product_node_version, contract_json
                ) VALUES (?, ?, ?)
                """,
                (
                    definition.product_node_type_ref,
                    definition.product_node_version,
                    contract_json,
                ),
            )
        return ProductNodeDefinition.from_dict(json.loads(contract_json))

    def resolve(
        self, product_node_type_ref: str, product_node_version: str
    ) -> ProductNodeDefinition | None:
        row = self._store.connection.execute(
            """
            SELECT contract_json FROM product_node_definitions
            WHERE product_node_type_ref = ? AND product_node_version = ?
            """,
            (product_node_type_ref, product_node_version),
        ).fetchone()
        if row is None:
            return None
        return ProductNodeDefinition.from_dict(json.loads(row["contract_json"]))

    @staticmethod
    def _validate_shape(definition: ProductNodeDefinition) -> None:
        identity_values = (
            definition.product_node_type_ref,
            definition.product_node_version,
            definition.bound_module_ref,
            definition.bound_module_version,
        )
        if any(
            not isinstance(value, str) or not value for value in identity_values
        ):
            raise ProductDefinitionError("PRODUCT_NODE_CONTRACT_INVALID")
        for bindings in (
            definition.input_port_bindings,
            definition.output_port_bindings,
        ):
            names: set[str] = set()
            for binding in bindings:
                if (
                    not isinstance(binding.product_port_ref, str)
                    or not binding.product_port_ref
                    or not isinstance(binding.bound_module_port_name, str)
                    or not binding.bound_module_port_name
                    or binding.product_port_ref in names
                ):
                    raise ProductDefinitionError("PRODUCT_NODE_CONTRACT_INVALID")
                names.add(binding.product_port_ref)
        try:
            validate_json_schema(definition.product_config_schema)
        except (TypeError, ValueError) as error:
            raise ProductDefinitionError("PRODUCT_NODE_CONTRACT_INVALID") from error
        if not isinstance(definition.display_metadata, dict):
            raise ProductDefinitionError("PRODUCT_NODE_CONTRACT_INVALID")

    @staticmethod
    def _validate_config_narrowing(
        product_schema: dict[str, Any], module_schema: dict[str, Any]
    ) -> None:
        """Product config schema may only narrow, never widen, Module authority."""

        if product_schema.get("type") != module_schema.get("type"):
            raise ProductDefinitionError("PRODUCT_CONFIG_WIDENS_MODULE_AUTHORITY")
        if product_schema.get("type") != "object":
            return
        module_properties = set(module_schema.get("properties", {}))
        product_properties = set(product_schema.get("properties", {}))
        if not product_properties.issubset(module_properties):
            raise ProductDefinitionError("PRODUCT_CONFIG_WIDENS_MODULE_AUTHORITY")
        if product_schema.get("additionalProperties", False) and not module_schema.get(
            "additionalProperties", False
        ):
            raise ProductDefinitionError("PRODUCT_CONFIG_WIDENS_MODULE_AUTHORITY")
        # Every Module-required property that Product chooses to expose at
        # all must remain required at the Product layer too; Product may
        # not make a Module-mandatory field optional (that would let an
        # authoring path skip data the Module's own contract demands).
        module_required = set(module_schema.get("required", []))
        product_required = set(product_schema.get("required", []))
        newly_optional = (module_required & product_properties) - product_required
        if newly_optional:
            raise ProductDefinitionError(
                "PRODUCT_CONFIG_WIDENS_MODULE_AUTHORITY",
                properties=sorted(newly_optional),
            )
