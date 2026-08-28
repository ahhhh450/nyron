"""Immutable multi-instance GraphRevision publication and resolution.

Extends the original single-instance stub to close NYRON-T-20260828-170
findings F-001/F-002: one ``GraphRevision`` now atomically contains an
ordered set of ``ModuleInstanceRevision``s and an ordered set of ``Edge``s,
with fail-closed publish-time validation of the frozen Graph invariants
(G-INV-04 .. G-INV-09) from ``design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md``.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from nyron_kernel.definitions import ModuleDefinition, ModuleRegistry
from nyron_kernel.store import SQLiteStore

EDGE_ROLES = frozenset({"NORMAL", "FEEDBACK"})

# Cardinality is derived from the frozen input activation-mode set (no new
# Module/Graph field is introduced): a consumptive mode (TRIGGER,
# REQUIRED_NEXT) expects exactly one authored source edge per port so a
# single Activation's consumption is unambiguous; a latest-of-many mode
# (REQUIRED_LATEST, OPTIONAL_LATEST) already tolerates multiple deliveries
# at the ActivationRepository selection layer, so it is MULTI_SOURCE.
_SINGLE_SOURCE_MODES = frozenset({"TRIGGER", "REQUIRED_NEXT"})


class GraphError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class ModuleInstanceRevision:
    module_instance_revision_ref: str
    graph_revision_ref: str
    module_instance_ref: str
    module_ref: str
    module_version: str
    config_ref: str
    config_hash: str
    input_port_contract: dict[str, Any]
    output_port_contract: dict[str, Any]
    static_composite_path: tuple[str, ...]
    static_accounting_scope_ref: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "module_instance_revision_ref": self.module_instance_revision_ref,
            "graph_revision_ref": self.graph_revision_ref,
            "module_instance_ref": self.module_instance_ref,
            "module_ref": self.module_ref,
            "module_version": self.module_version,
            "config_ref": self.config_ref,
            "config_hash": self.config_hash,
            "input_port_contract": self.input_port_contract,
            "output_port_contract": self.output_port_contract,
            "static_composite_path": list(self.static_composite_path),
            "static_accounting_scope_ref": self.static_accounting_scope_ref,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ModuleInstanceRevision:
        return cls(
            module_instance_revision_ref=value["module_instance_revision_ref"],
            graph_revision_ref=value["graph_revision_ref"],
            module_instance_ref=value["module_instance_ref"],
            module_ref=value["module_ref"],
            module_version=value["module_version"],
            config_ref=value["config_ref"],
            config_hash=value["config_hash"],
            input_port_contract=value["input_port_contract"],
            output_port_contract=value["output_port_contract"],
            static_composite_path=tuple(value["static_composite_path"]),
            static_accounting_scope_ref=value["static_accounting_scope_ref"],
        )


@dataclass(frozen=True)
class EdgeRequest:
    """Caller-supplied Edge intent; ``publish`` derives ordinals itself."""

    edge_ref: str
    source_ref: str
    source_port_ref: str
    target_ref: str
    target_port_ref: str
    role: str = "NORMAL"


@dataclass(frozen=True)
class Edge:
    """Resolved, persisted Edge definition fact."""

    edge_ref: str
    graph_revision_ref: str
    source_ref: str
    source_port_ref: str
    target_module_instance_revision_ref: str
    target_port_ref: str
    edge_ordinal: int
    target_port_ordinal: int
    role: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "edge_ref": self.edge_ref,
            "source_ref": self.source_ref,
            "source_port_ref": self.source_port_ref,
            "target_module_instance_revision_ref": (
                self.target_module_instance_revision_ref
            ),
            "target_port_ref": self.target_port_ref,
            "edge_ordinal": self.edge_ordinal,
            "target_port_ordinal": self.target_port_ordinal,
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, graph_revision_ref: str, value: dict[str, Any]) -> Edge:
        return cls(
            edge_ref=value["edge_ref"],
            graph_revision_ref=graph_revision_ref,
            source_ref=value["source_ref"],
            source_port_ref=value["source_port_ref"],
            target_module_instance_revision_ref=value[
                "target_module_instance_revision_ref"
            ],
            target_port_ref=value["target_port_ref"],
            edge_ordinal=value["edge_ordinal"],
            target_port_ordinal=value["target_port_ordinal"],
            role=value["role"],
        )


@dataclass(frozen=True)
class GraphRevision:
    graph_revision_ref: str
    module_instance_revisions: tuple[ModuleInstanceRevision, ...]
    edges: tuple[Edge, ...]
    executable: bool
    reason_code: str | None

    @property
    def module_instance_revision(self) -> ModuleInstanceRevision:
        """Backward-compatible single-instance accessor.

        ``src/nyron_kernel/execution/admission.py`` is outside this Task's
        bounded write surface and performs one eager single-instance
        module/config/accounting-scope pre-check before admission. For a
        multi-instance GraphRevision this returns the first instance in
        stable ``module_instance_ref``-sorted order. Every instance's
        module/config is still independently and fully re-verified per
        Activation by the unmodified ``ActivationRepository`` /
        ``AttemptExecutor``, so this narrows only the eager admission-time
        pre-check, not execution correctness (see Finding
        NYRON-T-20260828-171-F-003 in the Task Result).
        """

        if not self.module_instance_revisions:
            raise GraphError("GRAPH_REVISION_INVALID")
        return self.module_instance_revisions[0]


class GraphRepository:
    def __init__(self, store: SQLiteStore, registry: ModuleRegistry) -> None:
        self._store = store
        self._registry = registry

    def publish(
        self,
        graph_revision_ref: str,
        module_instances: ModuleInstanceRevision
        | tuple[ModuleInstanceRevision, ...]
        | list[ModuleInstanceRevision],
        edges: tuple[EdgeRequest, ...] | list[EdgeRequest] = (),
    ) -> GraphRevision:
        if isinstance(module_instances, ModuleInstanceRevision):
            module_instances = (module_instances,)
        instances = tuple(module_instances)
        edge_requests = tuple(edges)

        if not isinstance(graph_revision_ref, str) or not graph_revision_ref:
            raise GraphError("GRAPH_REVISION_INVALID")
        if not instances:
            raise GraphError("GRAPH_REVISION_INVALID")
        for instance in instances:
            self._validate_instance_identity(graph_revision_ref, instance)

        instance_refs = [instance.module_instance_ref for instance in instances]
        if len(set(instance_refs)) != len(instance_refs):
            raise GraphError("GRAPH_REVISION_INVALID")
        instance_by_ref = {
            instance.module_instance_ref: instance for instance in instances
        }
        revision_refs = [instance.module_instance_revision_ref for instance in instances]
        if len(set(revision_refs)) != len(revision_refs):
            raise GraphError("GRAPH_REVISION_INVALID")

        for edge in edge_requests:
            self._validate_edge_request_shape(edge)

        definitions: dict[str, ModuleDefinition | None] = {
            instance.module_instance_ref: self._registry.resolve(
                instance.module_ref, instance.module_version
            )
            for instance in instances
        }
        all_resolved = all(
            definition is not None for definition in definitions.values()
        )

        if all_resolved:
            resolved_edges = self._validate_and_order_edges(
                graph_revision_ref, instances, instance_by_ref, definitions, edge_requests
            )
            executable = True
            reason_code = None
        else:
            resolved_edges = self._order_edges_without_validation(
                graph_revision_ref, instance_by_ref, edge_requests
            )
            executable = False
            reason_code = "UNRESOLVED_MODULE_REFERENCE"

        contract = self._canonical_contract(instances, resolved_edges, executable, reason_code)
        contract_json = self._canonical_json(contract)

        try:
            with self._store.transaction() as connection:
                existing = connection.execute(
                    """
                    SELECT contract_json, executable, reason_code
                    FROM graph_revisions WHERE graph_revision_ref = ?
                    """,
                    (graph_revision_ref,),
                ).fetchone()
                if existing is not None:
                    if existing["contract_json"] == contract_json:
                        return self._row_to_revision(graph_revision_ref, existing)
                    raise GraphError(
                        "GRAPH_REVISION_IMMUTABLE",
                        graph_revision_ref=graph_revision_ref,
                    )

                connection.execute(
                    """
                    INSERT INTO graph_revisions(
                        graph_revision_ref, contract_json, executable, reason_code
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (graph_revision_ref, contract_json, int(executable), reason_code),
                )
                for instance in instances:
                    connection.execute(
                        """
                        INSERT INTO module_instance_revisions(
                            module_instance_revision_ref,
                            graph_revision_ref,
                            module_instance_ref,
                            module_ref,
                            module_version,
                            config_ref,
                            config_hash,
                            input_port_contract_json,
                            output_port_contract_json,
                            static_composite_path_json,
                            static_accounting_scope_ref
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            instance.module_instance_revision_ref,
                            graph_revision_ref,
                            instance.module_instance_ref,
                            instance.module_ref,
                            instance.module_version,
                            instance.config_ref,
                            instance.config_hash,
                            self._canonical_json(instance.input_port_contract),
                            self._canonical_json(instance.output_port_contract),
                            self._canonical_json(list(instance.static_composite_path)),
                            instance.static_accounting_scope_ref,
                        ),
                    )
                for edge in resolved_edges:
                    connection.execute(
                        """
                        INSERT INTO graph_edges(
                            graph_revision_ref, edge_ref, source_ref,
                            source_port_ref, target_module_instance_revision_ref,
                            target_port_ref, edge_ordinal, target_port_ordinal, role
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            graph_revision_ref,
                            edge.edge_ref,
                            edge.source_ref,
                            edge.source_port_ref,
                            edge.target_module_instance_revision_ref,
                            edge.target_port_ref,
                            edge.edge_ordinal,
                            edge.target_port_ordinal,
                            edge.role,
                        ),
                    )
        except sqlite3.IntegrityError as error:
            raise GraphError(
                "GRAPH_REVISION_IMMUTABLE",
                graph_revision_ref=graph_revision_ref,
            ) from error

        return GraphRevision(
            graph_revision_ref=graph_revision_ref,
            module_instance_revisions=instances,
            edges=tuple(resolved_edges),
            executable=executable,
            reason_code=reason_code,
        )

    def resolve(self, graph_revision_ref: str) -> GraphRevision | None:
        row = self._store.connection.execute(
            """
            SELECT contract_json, executable, reason_code
            FROM graph_revisions WHERE graph_revision_ref = ?
            """,
            (graph_revision_ref,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_revision(graph_revision_ref, row)

    def _row_to_revision(
        self, graph_revision_ref: str, row: sqlite3.Row
    ) -> GraphRevision:
        contract = json.loads(row["contract_json"])
        instances = tuple(
            ModuleInstanceRevision.from_dict(value)
            for value in contract["module_instance_revisions"]
        )
        edges = tuple(
            Edge.from_dict(graph_revision_ref, value) for value in contract["edges"]
        )
        return GraphRevision(
            graph_revision_ref=graph_revision_ref,
            module_instance_revisions=instances,
            edges=edges,
            executable=bool(row["executable"]),
            reason_code=row["reason_code"],
        )

    # -- validation -------------------------------------------------

    def _validate_and_order_edges(
        self,
        graph_revision_ref: str,
        instances: tuple[ModuleInstanceRevision, ...],
        instance_by_ref: dict[str, ModuleInstanceRevision],
        definitions: dict[str, ModuleDefinition | None],
        edge_requests: tuple[EdgeRequest, ...],
    ) -> list[Edge]:
        revision_ref_to_instance_ref = {
            instance.module_instance_revision_ref: instance.module_instance_ref
            for instance in instances
        }
        port_ordinal_cache: dict[str, dict[str, int]] = {}

        def input_ordinals(instance_ref: str) -> dict[str, int]:
            if instance_ref not in port_ordinal_cache:
                definition = definitions[instance_ref]
                assert definition is not None
                port_ordinal_cache[instance_ref] = {
                    port.name: index
                    for index, port in enumerate(definition.input_port_definitions)
                }
            return port_ordinal_cache[instance_ref]

        seen_edge_refs: set[str] = set()
        seen_duplicate_keys: set[tuple[str, str, str, str]] = set()
        resolved: list[Edge] = []

        for index, edge in enumerate(edge_requests):
            if edge.edge_ref in seen_edge_refs:
                raise GraphError("GRAPH_EDGE_INVALID", edge_ref=edge.edge_ref)
            seen_edge_refs.add(edge.edge_ref)

            target_instance = instance_by_ref.get(edge.target_ref)
            if target_instance is None:
                raise GraphError("UNRESOLVED_EDGE_TARGET", edge_ref=edge.edge_ref)
            target_definition = definitions[edge.target_ref]
            assert target_definition is not None
            target_ports = {
                port.name: port for port in target_definition.input_port_definitions
            }
            target_port = target_ports.get(edge.target_port_ref)
            if target_port is None:
                raise GraphError(
                    "UNRESOLVED_EDGE_TARGET_PORT", edge_ref=edge.edge_ref
                )

            source_instance = instance_by_ref.get(edge.source_ref)
            if source_instance is not None:
                source_definition = definitions[edge.source_ref]
                assert source_definition is not None
                source_ports = {
                    port.name: port
                    for port in source_definition.output_port_definitions
                }
                source_port = source_ports.get(edge.source_port_ref)
                if source_port is None:
                    raise GraphError(
                        "UNRESOLVED_EDGE_SOURCE_PORT", edge_ref=edge.edge_ref
                    )
                if source_port.value_schema != target_port.value_schema:
                    raise GraphError(
                        "EDGE_SCHEMA_INCOMPATIBLE", edge_ref=edge.edge_ref
                    )
                resolved_source_ref = source_instance.module_instance_revision_ref
                if (
                    source_instance.module_instance_ref == edge.target_ref
                    and edge.role == "NORMAL"
                ):
                    raise GraphError(
                        "UNDECLARED_GRAPH_CYCLE", edge_ref=edge.edge_ref
                    )
            else:
                resolved_source_ref = edge.source_ref

            target_revision_ref = target_instance.module_instance_revision_ref
            dup_key = (
                resolved_source_ref,
                edge.source_port_ref,
                target_revision_ref,
                edge.target_port_ref,
            )
            if dup_key in seen_duplicate_keys:
                raise GraphError("DUPLICATE_EDGE", edge_ref=edge.edge_ref)
            seen_duplicate_keys.add(dup_key)

            resolved.append(
                Edge(
                    edge_ref=edge.edge_ref,
                    graph_revision_ref=graph_revision_ref,
                    source_ref=resolved_source_ref,
                    source_port_ref=edge.source_port_ref,
                    target_module_instance_revision_ref=target_revision_ref,
                    target_port_ref=edge.target_port_ref,
                    edge_ordinal=index,
                    target_port_ordinal=input_ordinals(edge.target_ref)[
                        edge.target_port_ref
                    ],
                    role=edge.role,
                )
            )

        self._validate_cardinality(resolved, revision_ref_to_instance_ref, definitions)
        self._validate_acyclic(resolved, revision_ref_to_instance_ref, instance_refs=tuple(
            instance.module_instance_ref for instance in instances
        ))
        return resolved

    @staticmethod
    def _validate_cardinality(
        edges: list[Edge],
        revision_ref_to_instance_ref: dict[str, str],
        definitions: dict[str, ModuleDefinition | None],
    ) -> None:
        incoming: dict[tuple[str, str], list[Edge]] = {}
        for edge in edges:
            key = (edge.target_module_instance_revision_ref, edge.target_port_ref)
            incoming.setdefault(key, []).append(edge)

        for (target_revision_ref, target_port_ref), group in incoming.items():
            instance_ref = revision_ref_to_instance_ref[target_revision_ref]
            definition = definitions[instance_ref]
            assert definition is not None
            mode = next(
                port.activation_mode
                for port in definition.input_port_definitions
                if port.name == target_port_ref
            )
            if mode in _SINGLE_SOURCE_MODES and len(group) > 1:
                raise GraphError(
                    "EDGE_CARDINALITY_VIOLATION",
                    target_module_instance_revision_ref=target_revision_ref,
                    target_port_ref=target_port_ref,
                )

    @staticmethod
    def _validate_acyclic(
        edges: list[Edge],
        revision_ref_to_instance_ref: dict[str, str],
        instance_refs: tuple[str, ...],
    ) -> None:
        adjacency: dict[str, list[str]] = {ref: [] for ref in instance_refs}
        for edge in edges:
            if edge.role != "NORMAL":
                continue
            source_instance_ref = revision_ref_to_instance_ref.get(edge.source_ref)
            if source_instance_ref is None:
                continue  # external ingress source: not part of module topology
            target_instance_ref = revision_ref_to_instance_ref[
                edge.target_module_instance_revision_ref
            ]
            adjacency[source_instance_ref].append(target_instance_ref)

        WHITE, GRAY, BLACK = 0, 1, 2
        color = {ref: WHITE for ref in instance_refs}

        def visit(node: str) -> None:
            color[node] = GRAY
            for neighbor in adjacency.get(node, ()):
                if color[neighbor] == GRAY:
                    raise GraphError("UNDECLARED_GRAPH_CYCLE", node=node)
                if color[neighbor] == WHITE:
                    visit(neighbor)
            color[node] = BLACK

        for ref in instance_refs:
            if color[ref] == WHITE:
                visit(ref)

    @staticmethod
    def _order_edges_without_validation(
        graph_revision_ref: str,
        instance_by_ref: dict[str, ModuleInstanceRevision],
        edge_requests: tuple[EdgeRequest, ...],
    ) -> list[Edge]:
        resolved: list[Edge] = []
        seen_edge_refs: set[str] = set()
        seen_duplicate_keys: set[tuple[str, str, str, str]] = set()
        for index, edge in enumerate(edge_requests):
            if edge.edge_ref in seen_edge_refs:
                raise GraphError("GRAPH_EDGE_INVALID", edge_ref=edge.edge_ref)
            seen_edge_refs.add(edge.edge_ref)

            target_instance = instance_by_ref.get(edge.target_ref)
            if target_instance is None:
                raise GraphError("UNRESOLVED_EDGE_TARGET", edge_ref=edge.edge_ref)

            source_instance = instance_by_ref.get(edge.source_ref)
            resolved_source_ref = (
                source_instance.module_instance_revision_ref
                if source_instance is not None
                else edge.source_ref
            )
            target_revision_ref = target_instance.module_instance_revision_ref
            dup_key = (
                resolved_source_ref,
                edge.source_port_ref,
                target_revision_ref,
                edge.target_port_ref,
            )
            if dup_key in seen_duplicate_keys:
                raise GraphError("DUPLICATE_EDGE", edge_ref=edge.edge_ref)
            seen_duplicate_keys.add(dup_key)

            resolved.append(
                Edge(
                    edge_ref=edge.edge_ref,
                    graph_revision_ref=graph_revision_ref,
                    source_ref=resolved_source_ref,
                    source_port_ref=edge.source_port_ref,
                    target_module_instance_revision_ref=target_revision_ref,
                    target_port_ref=edge.target_port_ref,
                    edge_ordinal=index,
                    target_port_ordinal=0,
                    role=edge.role,
                )
            )
        return resolved

    @staticmethod
    def _validate_edge_request_shape(edge: EdgeRequest) -> None:
        values = (
            edge.edge_ref,
            edge.source_ref,
            edge.source_port_ref,
            edge.target_ref,
            edge.target_port_ref,
        )
        if any(not isinstance(value, str) or not value for value in values):
            raise GraphError("GRAPH_EDGE_INVALID", edge_ref=edge.edge_ref)
        if edge.role not in EDGE_ROLES:
            raise GraphError("GRAPH_EDGE_INVALID", edge_ref=edge.edge_ref)

    @staticmethod
    def _validate_instance_identity(
        graph_revision_ref: str, module_instance: ModuleInstanceRevision
    ) -> None:
        values = (
            graph_revision_ref,
            module_instance.module_instance_revision_ref,
            module_instance.graph_revision_ref,
            module_instance.module_instance_ref,
            module_instance.module_ref,
            module_instance.module_version,
            module_instance.config_ref,
            module_instance.config_hash,
            module_instance.static_accounting_scope_ref,
        )
        if any(not isinstance(value, str) or not value for value in values):
            raise GraphError("GRAPH_REVISION_INVALID")
        if module_instance.graph_revision_ref != graph_revision_ref:
            raise GraphError("GRAPH_REVISION_INVALID")
        if not isinstance(module_instance.static_composite_path, tuple) or any(
            not isinstance(item, str) or not item
            for item in module_instance.static_composite_path
        ):
            raise GraphError("GRAPH_REVISION_INVALID")
        if not isinstance(module_instance.input_port_contract, dict) or not isinstance(
            module_instance.output_port_contract, dict
        ):
            raise GraphError("GRAPH_REVISION_INVALID")

    @staticmethod
    def _canonical_contract(
        instances: tuple[ModuleInstanceRevision, ...],
        edges: list[Edge],
        executable: bool,
        reason_code: str | None,
    ) -> dict[str, Any]:
        return {
            "module_instance_revisions": [
                instance.as_dict()
                for instance in sorted(
                    instances, key=lambda instance: instance.module_instance_ref
                )
            ],
            "edges": [edge.as_dict() for edge in edges],
            "executable": executable,
            "reason_code": reason_code,
        }

    @staticmethod
    def _canonical_json(value: object) -> str:
        try:
            return json.dumps(value, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as error:
            raise GraphError("GRAPH_REVISION_INVALID") from error
