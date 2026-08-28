"""VisualWorkflowRevision / NodeInstance / NodeConnection Product truth.

NYRON-T-20260828-171 Node Foundation v0.1. This module owns the immutable
Product-layer workflow snapshot that the deterministic compiler in
``compiler.py`` projects into exactly one ``GraphRevision``. Layout/UI
placement lives in the separate ``WorkflowLayoutRecord`` table so moving a
node on the canvas never requires or silently causes a new
``VisualWorkflowRevision`` or ``GraphRevision`` (binding guardrail
``Product layout/UI metadata != Runtime canonical truth``).

This bounded slice does not implement a mutable GraphDraft-equivalent
authoring state: ``publish`` always fully validates before persisting.
Task 171 does not require partial/broken draft persistence (no graphical
editor is in scope), so there is no consumer for a "saveable but invalid"
workflow the way GraphDraft exists for hand-authored broken topologies.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.store import SQLiteStore

from .node_definition import ProductNodeDefinition, ProductNodeRegistry

EDGE_ROLES = frozenset({"NORMAL", "FEEDBACK"})


def _matches_schema(value: object, schema: dict[str, Any]) -> bool:
    """Product-owned copy of the frozen JSON-schema-subset value matcher.

    Deliberately duplicated rather than imported from
    ``nyron_kernel.execution.executor`` (a private helper there): Task 171
    forbids modifying or reaching into ``execution/**`` internals, and this
    check is small, pure, and has no other owner to import from publicly.
    """

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
            _matches_schema(item, schema["items"]) for item in value
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
            key not in value or _matches_schema(value[key], child)
            for key, child in properties.items()
        )
    return False


class ProductWorkflowError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class NodeInstance:
    node_instance_ref: str
    node_definition_ref: str
    node_version: str
    config: dict[str, Any] = field(default_factory=dict)
    label: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_instance_ref": self.node_instance_ref,
            "node_definition_ref": self.node_definition_ref,
            "node_version": self.node_version,
            "config": self.config,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> NodeInstance:
        return cls(
            node_instance_ref=value["node_instance_ref"],
            node_definition_ref=value["node_definition_ref"],
            node_version=value["node_version"],
            config=value["config"],
            label=value["label"],
        )


@dataclass(frozen=True)
class NodeConnection:
    connection_ref: str
    source_node_ref: str
    source_port_ref: str
    target_node_ref: str
    target_port_ref: str
    role: str = "NORMAL"

    def as_dict(self) -> dict[str, Any]:
        return {
            "connection_ref": self.connection_ref,
            "source_node_ref": self.source_node_ref,
            "source_port_ref": self.source_port_ref,
            "target_node_ref": self.target_node_ref,
            "target_port_ref": self.target_port_ref,
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> NodeConnection:
        return cls(
            connection_ref=value["connection_ref"],
            source_node_ref=value["source_node_ref"],
            source_port_ref=value["source_port_ref"],
            target_node_ref=value["target_node_ref"],
            target_port_ref=value["target_port_ref"],
            role=value["role"],
        )


@dataclass(frozen=True)
class EntrypointBinding:
    node_instance_ref: str
    port_ref: str

    def as_dict(self) -> dict[str, Any]:
        return {"node_instance_ref": self.node_instance_ref, "port_ref": self.port_ref}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EntrypointBinding:
        return cls(value["node_instance_ref"], value["port_ref"])


@dataclass(frozen=True)
class OutputBinding:
    output_ref: str
    node_instance_ref: str
    port_ref: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "output_ref": self.output_ref,
            "node_instance_ref": self.node_instance_ref,
            "port_ref": self.port_ref,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> OutputBinding:
        return cls(value["output_ref"], value["node_instance_ref"], value["port_ref"])


@dataclass(frozen=True)
class VisualWorkflowRevision:
    workflow_revision_ref: str
    workflow_ref: str
    predecessor_workflow_revision_ref: str | None
    node_instances: tuple[NodeInstance, ...]
    node_connections: tuple[NodeConnection, ...]
    entrypoints: tuple[EntrypointBinding, ...]
    product_outputs: tuple[OutputBinding, ...]
    product_metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "workflow_revision_ref": self.workflow_revision_ref,
            "workflow_ref": self.workflow_ref,
            "predecessor_workflow_revision_ref": (
                self.predecessor_workflow_revision_ref
            ),
            "node_instances": [node.as_dict() for node in self.node_instances],
            "node_connections": [
                connection.as_dict() for connection in self.node_connections
            ],
            "entrypoints": [entry.as_dict() for entry in self.entrypoints],
            "product_outputs": [
                output.as_dict() for output in self.product_outputs
            ],
            "product_metadata": self.product_metadata,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> VisualWorkflowRevision:
        return cls(
            workflow_revision_ref=value["workflow_revision_ref"],
            workflow_ref=value["workflow_ref"],
            predecessor_workflow_revision_ref=value[
                "predecessor_workflow_revision_ref"
            ],
            node_instances=tuple(
                NodeInstance.from_dict(item) for item in value["node_instances"]
            ),
            node_connections=tuple(
                NodeConnection.from_dict(item)
                for item in value["node_connections"]
            ),
            entrypoints=tuple(
                EntrypointBinding.from_dict(item) for item in value["entrypoints"]
            ),
            product_outputs=tuple(
                OutputBinding.from_dict(item) for item in value["product_outputs"]
            ),
            product_metadata=value["product_metadata"],
        )


@dataclass(frozen=True)
class WorkflowLayoutRecord:
    workflow_revision_ref: str
    node_instance_ref: str
    layout: dict[str, Any]


class ProductWorkflowRepository:
    """Validate, publish, and exactly resolve immutable workflow revisions."""

    def __init__(
        self,
        store: SQLiteStore,
        node_registry: ProductNodeRegistry,
        module_registry: ModuleRegistry,
    ) -> None:
        self._store = store
        self._nodes = node_registry
        self._modules = module_registry
        self._store.create_product_schema()

    def publish(self, workflow: VisualWorkflowRevision) -> VisualWorkflowRevision:
        self._validate(workflow)

        try:
            contract_json = json.dumps(
                workflow.as_dict(), sort_keys=True, separators=(",", ":")
            )
        except (TypeError, ValueError) as error:
            raise ProductWorkflowError("PRODUCT_WORKFLOW_CONTRACT_INVALID") from error

        with self._store.transaction() as connection:
            existing = connection.execute(
                """
                SELECT contract_json FROM visual_workflow_revisions
                WHERE workflow_revision_ref = ?
                """,
                (workflow.workflow_revision_ref,),
            ).fetchone()
            if existing is not None:
                if existing["contract_json"] != contract_json:
                    raise ProductWorkflowError(
                        "PRODUCT_WORKFLOW_REVISION_CONFLICT",
                        workflow_revision_ref=workflow.workflow_revision_ref,
                    )
                return VisualWorkflowRevision.from_dict(
                    json.loads(existing["contract_json"])
                )
            connection.execute(
                """
                INSERT INTO visual_workflow_revisions(
                    workflow_revision_ref, workflow_ref,
                    predecessor_workflow_revision_ref, contract_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    workflow.workflow_revision_ref,
                    workflow.workflow_ref,
                    workflow.predecessor_workflow_revision_ref,
                    contract_json,
                ),
            )
        return workflow

    def resolve(self, workflow_revision_ref: str) -> VisualWorkflowRevision | None:
        row = self._store.connection.execute(
            """
            SELECT contract_json FROM visual_workflow_revisions
            WHERE workflow_revision_ref = ?
            """,
            (workflow_revision_ref,),
        ).fetchone()
        if row is None:
            return None
        return VisualWorkflowRevision.from_dict(json.loads(row["contract_json"]))

    def resolve_node_definition(
        self, node: NodeInstance
    ) -> ProductNodeDefinition:
        definition = self._nodes.resolve(node.node_definition_ref, node.node_version)
        if definition is None:
            raise ProductWorkflowError(
                "PRODUCT_NODE_DEFINITION_UNRESOLVED",
                node_definition_ref=node.node_definition_ref,
                node_version=node.node_version,
            )
        return definition

    # -- validation ----------------------------------------------------

    def _validate(self, workflow: VisualWorkflowRevision) -> None:
        identity = (workflow.workflow_revision_ref, workflow.workflow_ref)
        if any(not isinstance(value, str) or not value for value in identity):
            raise ProductWorkflowError("PRODUCT_WORKFLOW_CONTRACT_INVALID")
        if (
            workflow.predecessor_workflow_revision_ref is not None
            and self.resolve(workflow.predecessor_workflow_revision_ref) is None
        ):
            raise ProductWorkflowError(
                "PRODUCT_WORKFLOW_PREDECESSOR_UNRESOLVED",
                predecessor_workflow_revision_ref=(
                    workflow.predecessor_workflow_revision_ref
                ),
            )
        if not workflow.node_instances:
            raise ProductWorkflowError("PRODUCT_WORKFLOW_CONTRACT_INVALID")

        node_refs = [node.node_instance_ref for node in workflow.node_instances]
        if len(set(node_refs)) != len(node_refs):
            raise ProductWorkflowError("PRODUCT_WORKFLOW_CONTRACT_INVALID")
        nodes_by_ref = {node.node_instance_ref: node for node in workflow.node_instances}

        definitions: dict[str, ProductNodeDefinition] = {}
        for node in workflow.node_instances:
            definition = self.resolve_node_definition(node)
            module_definition = self._modules.resolve(
                definition.bound_module_ref, definition.bound_module_version
            )
            if module_definition is None:
                raise ProductWorkflowError(
                    "MODULE_DEFINITION_UNRESOLVED",
                    bound_module_ref=definition.bound_module_ref,
                    bound_module_version=definition.bound_module_version,
                )
            self._validate_config(node, definition, module_definition)
            definitions[node.node_instance_ref] = definition

        self._validate_connections(workflow, nodes_by_ref, definitions)
        self._validate_entrypoints(workflow, nodes_by_ref, definitions)
        self._validate_outputs(workflow, nodes_by_ref, definitions)

    @staticmethod
    def _validate_config(
        node: NodeInstance,
        definition: ProductNodeDefinition,
        module_definition: object,
    ) -> None:
        if not isinstance(node.config, dict) or not _matches_schema(
            node.config, definition.product_config_schema
        ):
            raise ProductWorkflowError(
                "PRODUCT_NODE_CONFIG_INVALID", node_instance_ref=node.node_instance_ref
            )

    @staticmethod
    def _validate_connections(
        workflow: VisualWorkflowRevision,
        nodes_by_ref: dict[str, NodeInstance],
        definitions: dict[str, ProductNodeDefinition],
    ) -> None:
        connection_refs: set[str] = set()
        duplicate_keys: set[tuple[str, str, str, str]] = set()
        incoming_count: dict[tuple[str, str], int] = {}

        for connection in workflow.node_connections:
            if (
                not isinstance(connection.connection_ref, str)
                or not connection.connection_ref
                or connection.connection_ref in connection_refs
            ):
                raise ProductWorkflowError(
                    "PRODUCT_CONNECTION_INVALID",
                    connection_ref=connection.connection_ref,
                )
            connection_refs.add(connection.connection_ref)
            if connection.role not in EDGE_ROLES:
                raise ProductWorkflowError(
                    "PRODUCT_CONNECTION_INVALID",
                    connection_ref=connection.connection_ref,
                )

            source_node = nodes_by_ref.get(connection.source_node_ref)
            target_node = nodes_by_ref.get(connection.target_node_ref)
            if source_node is None or target_node is None:
                raise ProductWorkflowError(
                    "PRODUCT_CONNECTION_UNRESOLVED_ENDPOINT",
                    connection_ref=connection.connection_ref,
                )

            source_definition = definitions[connection.source_node_ref]
            target_definition = definitions[connection.target_node_ref]
            source_ports = {
                binding.product_port_ref: binding.bound_module_port_name
                for binding in source_definition.output_port_bindings
            }
            target_ports = {
                binding.product_port_ref: binding.bound_module_port_name
                for binding in target_definition.input_port_bindings
            }
            if (
                connection.source_port_ref not in source_ports
                or connection.target_port_ref not in target_ports
            ):
                raise ProductWorkflowError(
                    "PRODUCT_CONNECTION_UNRESOLVED_ENDPOINT",
                    connection_ref=connection.connection_ref,
                )

            dup_key = (
                connection.source_node_ref,
                connection.source_port_ref,
                connection.target_node_ref,
                connection.target_port_ref,
            )
            if dup_key in duplicate_keys:
                raise ProductWorkflowError(
                    "PRODUCT_CONNECTION_DUPLICATE",
                    connection_ref=connection.connection_ref,
                )
            duplicate_keys.add(dup_key)

            target_key = (connection.target_node_ref, connection.target_port_ref)
            incoming_count[target_key] = incoming_count.get(target_key, 0) + 1

    @staticmethod
    def _validate_entrypoints(
        workflow: VisualWorkflowRevision,
        nodes_by_ref: dict[str, NodeInstance],
        definitions: dict[str, ProductNodeDefinition],
    ) -> None:
        if not workflow.entrypoints:
            raise ProductWorkflowError("PRODUCT_WORKFLOW_NO_ENTRYPOINT")
        for entry in workflow.entrypoints:
            definition = definitions.get(entry.node_instance_ref)
            if definition is None:
                raise ProductWorkflowError(
                    "PRODUCT_WORKFLOW_ENTRYPOINT_UNRESOLVED",
                    node_instance_ref=entry.node_instance_ref,
                )
            input_ports = {
                binding.product_port_ref for binding in definition.input_port_bindings
            }
            if entry.port_ref not in input_ports:
                raise ProductWorkflowError(
                    "PRODUCT_WORKFLOW_ENTRYPOINT_UNRESOLVED",
                    node_instance_ref=entry.node_instance_ref,
                    port_ref=entry.port_ref,
                )

    @staticmethod
    def _validate_outputs(
        workflow: VisualWorkflowRevision,
        nodes_by_ref: dict[str, NodeInstance],
        definitions: dict[str, ProductNodeDefinition],
    ) -> None:
        if not workflow.product_outputs:
            raise ProductWorkflowError("PRODUCT_WORKFLOW_NO_OUTPUT")
        output_refs: set[str] = set()
        for output in workflow.product_outputs:
            if (
                not isinstance(output.output_ref, str)
                or not output.output_ref
                or output.output_ref in output_refs
            ):
                raise ProductWorkflowError(
                    "PRODUCT_WORKFLOW_OUTPUT_INVALID", output_ref=output.output_ref
                )
            output_refs.add(output.output_ref)
            definition = definitions.get(output.node_instance_ref)
            if definition is None:
                raise ProductWorkflowError(
                    "PRODUCT_WORKFLOW_OUTPUT_UNRESOLVED",
                    node_instance_ref=output.node_instance_ref,
                )
            output_ports = {
                binding.product_port_ref
                for binding in definition.output_port_bindings
            }
            if output.port_ref not in output_ports:
                raise ProductWorkflowError(
                    "PRODUCT_WORKFLOW_OUTPUT_UNRESOLVED",
                    node_instance_ref=output.node_instance_ref,
                    port_ref=output.port_ref,
                )


class WorkflowLayoutRepository:
    """Freely rewritable canvas presentation state, kept out of workflow truth."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._store.create_product_schema()

    def put(self, record: WorkflowLayoutRecord) -> None:
        try:
            layout_json = json.dumps(
                record.layout, sort_keys=True, separators=(",", ":")
            )
        except (TypeError, ValueError) as error:
            raise ProductWorkflowError("PRODUCT_LAYOUT_INVALID") from error
        with self._store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO workflow_layout_records(
                    workflow_revision_ref, node_instance_ref, layout_json
                ) VALUES (?, ?, ?)
                ON CONFLICT(workflow_revision_ref, node_instance_ref)
                DO UPDATE SET layout_json = excluded.layout_json
                """,
                (
                    record.workflow_revision_ref,
                    record.node_instance_ref,
                    layout_json,
                ),
            )

    def resolve(
        self, workflow_revision_ref: str, node_instance_ref: str
    ) -> WorkflowLayoutRecord | None:
        row = self._store.connection.execute(
            """
            SELECT layout_json FROM workflow_layout_records
            WHERE workflow_revision_ref = ? AND node_instance_ref = ?
            """,
            (workflow_revision_ref, node_instance_ref),
        ).fetchone()
        if row is None:
            return None
        return WorkflowLayoutRecord(
            workflow_revision_ref=workflow_revision_ref,
            node_instance_ref=node_instance_ref,
            layout=json.loads(row["layout_json"]),
        )
