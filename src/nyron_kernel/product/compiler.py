"""Deterministic Product -> Graph compiler.

    VisualWorkflowRevision
            v Product validation + exact node/module resolution
    Product compiler (stateless, deterministic, pure)
            v GraphRepository.publish(...)
    GraphRevision

``GraphRevision`` remains the sole executable Graph authority (binding
guardrail ``VisualWorkflowRevision != GraphRevision``); Product never
writes Graph tables directly except through ``GraphRepository.publish``.
Every identifier the compiler emits (``graph_revision_ref``,
``module_instance_revision_ref``, ``edge_ref``) is a stable hash of the
immutable ``VisualWorkflowRevision`` content, so recompiling the same
workflow revision -- including after a process restart -- always
deterministically reproduces the identical ``GraphRevision`` identity and
content (idempotent re-``publish``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.graph import EdgeRequest, GraphRepository, GraphRevision, ModuleInstanceRevision

from .node_definition import ProductNodeDefinition, ProductNodeRegistry
from .workflow import VisualWorkflowRevision

_INGRESS_SOURCE_PORT = "out"


class ProductCompileError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class CompiledWorkflow:
    graph_revision: GraphRevision
    module_instance_revision_ref_by_node: dict[str, str]
    # (node_instance_ref, product_port_ref) -> (ingress source_ref, source_port_ref)
    ingress_by_entrypoint: dict[tuple[str, str], tuple[str, str]]
    # (output_ref, module_instance_revision_ref, module_output_port_name)
    output_bindings: tuple[tuple[str, str, str], ...]
    # config_ref (== config_hash by construction) -> the immutable config dict
    config_by_ref: dict[str, dict[str, Any]]


class ProductGraphCompiler:
    def __init__(
        self,
        graphs: GraphRepository,
        node_registry: ProductNodeRegistry,
        module_registry: ModuleRegistry,
    ) -> None:
        self._graphs = graphs
        self._nodes = node_registry
        self._modules = module_registry

    def compile(self, workflow: VisualWorkflowRevision) -> CompiledWorkflow:
        resolved = self._resolve_definitions(workflow)
        nodes_by_ref = {
            node.node_instance_ref: node for node in workflow.node_instances
        }

        graph_revision_ref = self._derive_graph_revision_ref(workflow, resolved)
        module_instance_revision_ref_by_node = {
            node_ref: self._stable_ref("module-instance", (graph_revision_ref, node_ref))
            for node_ref in resolved
        }

        module_instances = tuple(
            self._build_module_instance(
                workflow.workflow_revision_ref,
                graph_revision_ref,
                nodes_by_ref[node_ref],
                module_instance_revision_ref_by_node[node_ref],
                resolved,
            )
            for node_ref in module_instance_revision_ref_by_node
        )

        def module_port_name(node_ref: str, product_port_ref: str, *, output: bool) -> str:
            definition = resolved[node_ref][0]
            bindings = (
                definition.output_port_bindings
                if output
                else definition.input_port_bindings
            )
            for binding in bindings:
                if binding.product_port_ref == product_port_ref:
                    return binding.bound_module_port_name
            raise ProductCompileError(
                "PRODUCT_PORT_BINDING_UNRESOLVED",
                node_instance_ref=node_ref,
                product_port_ref=product_port_ref,
            )

        edge_requests: list[EdgeRequest] = []
        for connection in workflow.node_connections:
            edge_requests.append(
                EdgeRequest(
                    edge_ref=self._stable_ref(
                        "edge",
                        (
                            graph_revision_ref,
                            connection.source_node_ref,
                            connection.source_port_ref,
                            connection.target_node_ref,
                            connection.target_port_ref,
                        ),
                    ),
                    source_ref=connection.source_node_ref,
                    source_port_ref=module_port_name(
                        connection.source_node_ref,
                        connection.source_port_ref,
                        output=True,
                    ),
                    target_ref=connection.target_node_ref,
                    target_port_ref=module_port_name(
                        connection.target_node_ref,
                        connection.target_port_ref,
                        output=False,
                    ),
                    role=connection.role,
                )
            )

        ingress_by_entrypoint: dict[tuple[str, str], tuple[str, str]] = {}
        for entry in workflow.entrypoints:
            ingress_source_ref = self._stable_ref(
                "ingress", (graph_revision_ref, entry.node_instance_ref, entry.port_ref)
            )
            ingress_by_entrypoint[(entry.node_instance_ref, entry.port_ref)] = (
                ingress_source_ref,
                _INGRESS_SOURCE_PORT,
            )
            edge_requests.append(
                EdgeRequest(
                    edge_ref=self._stable_ref(
                        "edge:ingress",
                        (graph_revision_ref, entry.node_instance_ref, entry.port_ref),
                    ),
                    source_ref=ingress_source_ref,
                    source_port_ref=_INGRESS_SOURCE_PORT,
                    target_ref=entry.node_instance_ref,
                    target_port_ref=module_port_name(
                        entry.node_instance_ref, entry.port_ref, output=False
                    ),
                    role="NORMAL",
                )
            )

        edge_requests.sort(
            key=lambda edge: (
                edge.source_ref,
                edge.source_port_ref,
                edge.target_ref,
                edge.target_port_ref,
            )
        )

        graph_revision = self._graphs.publish(
            graph_revision_ref, module_instances, tuple(edge_requests)
        )

        output_bindings = tuple(
            (
                output.output_ref,
                module_instance_revision_ref_by_node[output.node_instance_ref],
                module_port_name(output.node_instance_ref, output.port_ref, output=True),
            )
            for output in workflow.product_outputs
        )

        config_by_ref = {
            instance.config_ref: nodes_by_ref[instance.module_instance_ref].config
            for instance in module_instances
        }

        return CompiledWorkflow(
            graph_revision=graph_revision,
            module_instance_revision_ref_by_node=module_instance_revision_ref_by_node,
            ingress_by_entrypoint=ingress_by_entrypoint,
            output_bindings=output_bindings,
            config_by_ref=config_by_ref,
        )

    def _resolve_definitions(
        self, workflow: VisualWorkflowRevision
    ) -> dict[str, tuple[ProductNodeDefinition, Any]]:
        resolved: dict[str, tuple[ProductNodeDefinition, Any]] = {}
        for node in workflow.node_instances:
            definition = self._nodes.resolve(node.node_definition_ref, node.node_version)
            if definition is None:
                raise ProductCompileError(
                    "PRODUCT_NODE_DEFINITION_UNRESOLVED",
                    node_instance_ref=node.node_instance_ref,
                )
            module_definition = self._modules.resolve(
                definition.bound_module_ref, definition.bound_module_version
            )
            if module_definition is None:
                raise ProductCompileError(
                    "MODULE_DEFINITION_UNRESOLVED",
                    node_instance_ref=node.node_instance_ref,
                )
            resolved[node.node_instance_ref] = (definition, module_definition)
        return resolved

    def _derive_graph_revision_ref(
        self,
        workflow: VisualWorkflowRevision,
        resolved: dict[str, tuple[ProductNodeDefinition, Any]],
    ) -> str:
        node_facts = sorted(
            (
                node.node_instance_ref,
                resolved[node.node_instance_ref][0].bound_module_ref,
                resolved[node.node_instance_ref][0].bound_module_version,
                json.dumps(node.config, sort_keys=True, separators=(",", ":")),
            )
            for node in workflow.node_instances
        )
        connection_facts = sorted(
            (
                connection.source_node_ref,
                connection.source_port_ref,
                connection.target_node_ref,
                connection.target_port_ref,
                connection.role,
            )
            for connection in workflow.node_connections
        )
        entrypoint_facts = sorted(
            (entry.node_instance_ref, entry.port_ref) for entry in workflow.entrypoints
        )
        output_facts = sorted(
            (output.output_ref, output.node_instance_ref, output.port_ref)
            for output in workflow.product_outputs
        )
        return self._stable_ref(
            "graph:product",
            (
                workflow.workflow_revision_ref,
                node_facts,
                connection_facts,
                entrypoint_facts,
                output_facts,
            ),
        )

    @staticmethod
    def _build_module_instance(
        workflow_revision_ref: str,
        graph_revision_ref: str,
        node: Any,
        module_instance_revision_ref: str,
        resolved: dict[str, tuple[ProductNodeDefinition, Any]],
    ) -> ModuleInstanceRevision:
        definition, module_definition = resolved[node.node_instance_ref]
        input_port_contract = {
            port.name: port.activation_mode
            for port in module_definition.input_port_definitions
        }
        output_port_contract = {
            port.name: port.value_schema
            for port in module_definition.output_port_definitions
        }
        config_hash = ProductGraphCompiler._stable_ref("config", (node.config,))
        return ModuleInstanceRevision(
            module_instance_revision_ref=module_instance_revision_ref,
            graph_revision_ref=graph_revision_ref,
            module_instance_ref=node.node_instance_ref,
            module_ref=definition.bound_module_ref,
            module_version=definition.bound_module_version,
            config_ref=config_hash,
            config_hash=config_hash,
            input_port_contract=input_port_contract,
            output_port_contract=output_port_contract,
            static_composite_path=(
                f"product:{workflow_revision_ref}",
                node.node_instance_ref,
            ),
            static_accounting_scope_ref=(
                f"accounting:product/{workflow_revision_ref}/{node.node_instance_ref}"
            ),
        )

    @staticmethod
    def _stable_ref(kind: str, values: object) -> str:
        encoded = json.dumps(values, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"{kind}:sha256:{sha256(encoded).hexdigest()}"
