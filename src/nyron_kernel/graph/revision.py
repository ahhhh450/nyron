"""Immutable one-module GraphRevision publication and resolution."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.store import SQLiteStore


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
class GraphRevision:
    graph_revision_ref: str
    module_instance_revision: ModuleInstanceRevision
    executable: bool
    reason_code: str | None


class GraphRepository:
    def __init__(self, store: SQLiteStore, registry: ModuleRegistry) -> None:
        self._store = store
        self._registry = registry

    def publish(
        self,
        graph_revision_ref: str,
        module_instance: ModuleInstanceRevision,
    ) -> GraphRevision:
        self._validate_identity(graph_revision_ref, module_instance)
        contract_json = self._canonical_json(module_instance.as_dict())

        try:
            with self._store.transaction() as connection:
                existing = connection.execute(
                    """
                    SELECT 1 FROM graph_revisions WHERE graph_revision_ref = ?
                    """,
                    (graph_revision_ref,),
                ).fetchone()
                if existing is not None:
                    raise GraphError(
                        "GRAPH_REVISION_IMMUTABLE",
                        graph_revision_ref=graph_revision_ref,
                    )

                definition = self._registry.resolve(
                    module_instance.module_ref, module_instance.module_version
                )
                executable = definition is not None
                reason_code = (
                    None if executable else "UNRESOLVED_MODULE_REFERENCE"
                )
                connection.execute(
                    """
                    INSERT INTO graph_revisions(
                        graph_revision_ref, contract_json, executable, reason_code
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (graph_revision_ref, contract_json, int(executable), reason_code),
                )
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
                        module_instance.module_instance_revision_ref,
                        graph_revision_ref,
                        module_instance.module_instance_ref,
                        module_instance.module_ref,
                        module_instance.module_version,
                        module_instance.config_ref,
                        module_instance.config_hash,
                        self._canonical_json(module_instance.input_port_contract),
                        self._canonical_json(module_instance.output_port_contract),
                        self._canonical_json(list(module_instance.static_composite_path)),
                        module_instance.static_accounting_scope_ref,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise GraphError(
                "GRAPH_REVISION_IMMUTABLE",
                graph_revision_ref=graph_revision_ref,
            ) from error

        return GraphRevision(
            graph_revision_ref=graph_revision_ref,
            module_instance_revision=ModuleInstanceRevision.from_dict(
                json.loads(contract_json)
            ),
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
        contract = json.loads(row["contract_json"])
        return GraphRevision(
            graph_revision_ref=graph_revision_ref,
            module_instance_revision=ModuleInstanceRevision.from_dict(contract),
            executable=bool(row["executable"]),
            reason_code=row["reason_code"],
        )

    @staticmethod
    def _validate_identity(
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
    def _canonical_json(value: object) -> str:
        try:
            return json.dumps(value, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as error:
            raise GraphError("GRAPH_REVISION_INVALID") from error
