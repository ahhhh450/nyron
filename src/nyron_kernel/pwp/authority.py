"""Owner-local durable authority for the bounded PWP foundation."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from typing import Callable, TypeVar

from nyron_kernel.pwp.models import (
    EnvironmentBindingEntry,
    EnvironmentBindingRevision,
    IngressRoute,
    IngressRouteRevision,
    PolicyContextRevision,
    Project,
    ProjectConfigRevision,
    Workspace,
    WorkspaceConfigRevision,
    WorkspaceRootDeclaration,
)
from nyron_kernel.store import SQLiteStore

Revision = TypeVar(
    "Revision",
    ProjectConfigRevision,
    WorkspaceConfigRevision,
    PolicyContextRevision,
    EnvironmentBindingRevision,
    IngressRouteRevision,
)


class PWPError(RuntimeError):
    """Fail-closed PWP error with a stable reason code."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


class PWPAuthority:
    """Sole application-level writer for PWP-owned canonical truth."""

    def __init__(self, store: SQLiteStore, clock: Callable[[], int]) -> None:
        self._store = store
        self._clock = clock
        self._store.create_pwp_schema()

    def create_project(self, project_ref: str) -> Project:
        self._require_ref(project_ref, "project_ref")
        existing = self.get_project(project_ref)
        if existing is not None:
            return existing
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    "INSERT INTO pwp_projects(project_ref,state,created_at,archived_at)"
                    " VALUES (?, 'ACTIVE', ?, NULL)",
                    (project_ref, self._now()),
                )
        except sqlite3.IntegrityError as error:
            raise PWPError("PROJECT_IDENTITY_CONFLICT", project_ref=project_ref) from error
        result = self.get_project(project_ref)
        assert result is not None
        return result

    def get_project(self, project_ref: str) -> Project | None:
        row = self._store.connection.execute(
            "SELECT * FROM pwp_projects WHERE project_ref = ?", (project_ref,)
        ).fetchone()
        return None if row is None else Project(**dict(row))

    def archive_project(self, project_ref: str) -> Project:
        project = self._require_project(project_ref)
        if project.state == "ARCHIVED":
            return project
        with self._store.transaction() as connection:
            connection.execute(
                "UPDATE pwp_projects SET state='ARCHIVED', archived_at=?"
                " WHERE project_ref=?",
                (self._now(), project_ref),
            )
        return self._require_project(project_ref)

    def deprecate_project(self, project_ref: str) -> Project:
        project = self._require_project(project_ref)
        if project.state == "DEPRECATED":
            return project
        if project.state != "ACTIVE":
            raise PWPError("PROJECT_NOT_ACTIVE", project_ref=project_ref)
        with self._store.transaction() as connection:
            connection.execute(
                "UPDATE pwp_projects SET state='DEPRECATED' WHERE project_ref=?",
                (project_ref,),
            )
        return self._require_project(project_ref)

    def create_workspace(
        self,
        workspace_ref: str,
        project_ref: str,
        parent_workspace_ref: str | None = None,
    ) -> Workspace:
        self._require_ref(workspace_ref, "workspace_ref")
        project = self._require_project(project_ref)
        if project.state != "ACTIVE":
            raise PWPError("PROJECT_NOT_ACTIVE", project_ref=project_ref)
        existing = self.get_workspace(workspace_ref)
        if existing is not None:
            if (
                existing.project_ref == project_ref
                and existing.parent_workspace_ref == parent_workspace_ref
            ):
                return existing
            raise PWPError("WORKSPACE_IDENTITY_CONFLICT", workspace_ref=workspace_ref)
        if parent_workspace_ref is not None:
            parent = self._require_workspace(parent_workspace_ref)
            if parent.project_ref != project_ref:
                raise PWPError("WORKSPACE_PARENT_PROJECT_MISMATCH")
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    "INSERT INTO pwp_workspaces(workspace_ref,project_ref,"
                    "parent_workspace_ref,state,created_at,archived_at)"
                    " VALUES (?, ?, ?, 'ACTIVE', ?, NULL)",
                    (workspace_ref, project_ref, parent_workspace_ref, self._now()),
                )
        except sqlite3.IntegrityError as error:
            raise PWPError("WORKSPACE_IDENTITY_CONFLICT", workspace_ref=workspace_ref) from error
        result = self.get_workspace(workspace_ref)
        assert result is not None
        return result

    def get_workspace(self, workspace_ref: str) -> Workspace | None:
        row = self._store.connection.execute(
            "SELECT * FROM pwp_workspaces WHERE workspace_ref = ?", (workspace_ref,)
        ).fetchone()
        return None if row is None else Workspace(**dict(row))

    def create_ingress_route(
        self,
        ingress_route_ref: str,
        project_ref: str,
        workspace_ref: str | None = None,
    ) -> IngressRoute:
        self._require_ref(ingress_route_ref, "ingress_route_ref")
        self._require_active_project(project_ref)
        if workspace_ref is not None:
            workspace = self._require_active_workspace(workspace_ref)
            if workspace.project_ref != project_ref:
                raise PWPError("INGRESS_ROUTE_WORKSPACE_PROJECT_MISMATCH")
        existing = self.get_ingress_route(ingress_route_ref)
        if existing is not None:
            if existing.project_ref == project_ref and existing.workspace_ref == workspace_ref:
                return existing
            raise PWPError("INGRESS_ROUTE_IDENTITY_CONFLICT", ingress_route_ref=ingress_route_ref)
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    "INSERT INTO pwp_ingress_routes(ingress_route_ref,project_ref,"
                    "workspace_ref,state,created_at,archived_at)"
                    " VALUES (?, ?, ?, 'ACTIVE', ?, NULL)",
                    (ingress_route_ref, project_ref, workspace_ref, self._now()),
                )
        except sqlite3.IntegrityError as error:
            raise PWPError(
                "INGRESS_ROUTE_IDENTITY_CONFLICT", ingress_route_ref=ingress_route_ref
            ) from error
        result = self.get_ingress_route(ingress_route_ref)
        assert result is not None
        return result

    def get_ingress_route(self, ingress_route_ref: str) -> IngressRoute | None:
        row = self._store.connection.execute(
            "SELECT * FROM pwp_ingress_routes WHERE ingress_route_ref=?",
            (ingress_route_ref,),
        ).fetchone()
        return None if row is None else IngressRoute(**dict(row))

    def archive_ingress_route(self, ingress_route_ref: str) -> IngressRoute:
        route = self._require_ingress_route(ingress_route_ref)
        if route.state == "ARCHIVED":
            return route
        with self._store.transaction() as connection:
            connection.execute(
                "UPDATE pwp_ingress_routes SET state='ARCHIVED', archived_at=?"
                " WHERE ingress_route_ref=?",
                (self._now(), ingress_route_ref),
            )
        return self._require_ingress_route(ingress_route_ref)

    def archive_workspace(self, workspace_ref: str) -> Workspace:
        workspace = self._require_workspace(workspace_ref)
        if workspace.state == "ARCHIVED":
            return workspace
        with self._store.transaction() as connection:
            connection.execute(
                "UPDATE pwp_workspaces SET state='ARCHIVED', archived_at=?"
                " WHERE workspace_ref=?",
                (self._now(), workspace_ref),
            )
        return self._require_workspace(workspace_ref)

    def deprecate_workspace(self, workspace_ref: str) -> Workspace:
        workspace = self._require_workspace(workspace_ref)
        if workspace.state == "DEPRECATED":
            return workspace
        if workspace.state != "ACTIVE":
            raise PWPError("WORKSPACE_NOT_ACTIVE", workspace_ref=workspace_ref)
        with self._store.transaction() as connection:
            connection.execute(
                "UPDATE pwp_workspaces SET state='DEPRECATED' WHERE workspace_ref=?",
                (workspace_ref,),
            )
        return self._require_workspace(workspace_ref)

    def resolve_workspace_ancestry(self, workspace_ref: str) -> tuple[Workspace, ...]:
        chain: list[Workspace] = []
        seen: set[str] = set()
        current = self._require_workspace(workspace_ref)
        while True:
            if current.workspace_ref in seen:
                raise PWPError("WORKSPACE_PARENT_CYCLE", workspace_ref=workspace_ref)
            seen.add(current.workspace_ref)
            chain.append(current)
            if current.parent_workspace_ref is None:
                return tuple(reversed(chain))
            current = self._require_workspace(current.parent_workspace_ref)

    def publish_project_config_revision(
        self, revision: ProjectConfigRevision
    ) -> ProjectConfigRevision:
        self._require_active_project(revision.project_ref)
        return self._publish_revision(
            revision,
            table="pwp_project_config_revisions",
            revision_ref=revision.project_config_revision_ref,
            subject_ref=revision.project_ref,
            pointer_table="pwp_projects",
            subject_column="project_ref",
            pointer_column="current_project_config_revision_ref",
            loader=self.get_project_config_revision,
        )

    def get_project_config_revision(self, revision_ref: str) -> ProjectConfigRevision | None:
        row = self._revision_row("pwp_project_config_revisions", revision_ref)
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        self._tuplify(payload, "user_policy_refs", "system_policy_refs", "extension_refs")
        return ProjectConfigRevision(**payload)

    def publish_workspace_config_revision(
        self, revision: WorkspaceConfigRevision
    ) -> WorkspaceConfigRevision:
        self._require_active_workspace(revision.workspace_ref)
        if revision.environment_binding_revision_ref is not None:
            binding = self.get_environment_binding_revision(
                revision.environment_binding_revision_ref
            )
            if binding is None or binding.workspace_ref != revision.workspace_ref:
                raise PWPError("ENVIRONMENT_BINDING_NOT_RESOLVABLE")
        return self._publish_revision(
            revision,
            table="pwp_workspace_config_revisions",
            revision_ref=revision.workspace_config_revision_ref,
            subject_ref=revision.workspace_ref,
            pointer_table="pwp_workspaces",
            subject_column="workspace_ref",
            pointer_column="current_workspace_config_revision_ref",
            loader=self.get_workspace_config_revision,
        )

    def get_workspace_config_revision(
        self, revision_ref: str
    ) -> WorkspaceConfigRevision | None:
        row = self._revision_row("pwp_workspace_config_revisions", revision_ref)
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        payload["root_declarations"] = tuple(
            WorkspaceRootDeclaration(**item) for item in payload["root_declarations"]
        )
        self._tuplify(
            payload,
            "workspace_policy_refs",
            "runtime_admission_policy_refs",
            "security_policy_refs",
            "secret_refs",
            "extension_refs",
        )
        return WorkspaceConfigRevision(**payload)

    def publish_policy_context_revision(
        self, revision: PolicyContextRevision
    ) -> PolicyContextRevision:
        if revision.subject_kind == "PROJECT":
            self._require_active_project(revision.subject_ref)
            pointer_table, subject_column = "pwp_projects", "project_ref"
        elif revision.subject_kind == "WORKSPACE":
            self._require_active_workspace(revision.subject_ref)
            pointer_table, subject_column = "pwp_workspaces", "workspace_ref"
        else:
            raise PWPError("INVALID_POLICY_SUBJECT_KIND")
        return self._publish_revision(
            revision,
            table="pwp_policy_context_revisions",
            revision_ref=revision.policy_context_revision_ref,
            subject_ref=revision.subject_ref,
            pointer_table=pointer_table,
            subject_column=subject_column,
            pointer_column="current_policy_context_revision_ref",
            loader=self.get_policy_context_revision,
            subject_kind=revision.subject_kind,
        )

    def get_policy_context_revision(self, revision_ref: str) -> PolicyContextRevision | None:
        row = self._revision_row("pwp_policy_context_revisions", revision_ref)
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        self._tuplify(
            payload,
            "project_policy_refs",
            "workspace_policy_refs",
            "security_policy_refs",
            "runtime_admission_policy_refs",
            "user_policy_refs",
            "system_policy_refs",
        )
        return PolicyContextRevision(**payload)

    def publish_environment_binding_revision(
        self, revision: EnvironmentBindingRevision
    ) -> EnvironmentBindingRevision:
        self._require_active_workspace(revision.workspace_ref)
        return self._publish_revision(
            revision,
            table="pwp_environment_binding_revisions",
            revision_ref=revision.environment_binding_revision_ref,
            subject_ref=revision.workspace_ref,
            pointer_table="pwp_workspaces",
            subject_column="workspace_ref",
            pointer_column="current_environment_binding_revision_ref",
            loader=self.get_environment_binding_revision,
        )

    def get_environment_binding_revision(
        self, revision_ref: str
    ) -> EnvironmentBindingRevision | None:
        row = self._revision_row("pwp_environment_binding_revisions", revision_ref)
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        payload["binding_entries"] = tuple(
            EnvironmentBindingEntry(**item) for item in payload["binding_entries"]
        )
        self._tuplify(payload, "portability_constraints")
        return EnvironmentBindingRevision(**payload)

    def publish_ingress_route_revision(
        self, revision: IngressRouteRevision
    ) -> IngressRouteRevision:
        route = self._require_active_ingress_route(revision.ingress_route_ref)
        self._validate_ingress_route_revision(revision, route)
        return self._publish_revision(
            revision,
            table="pwp_ingress_route_revisions",
            revision_ref=revision.ingress_route_revision_ref,
            subject_ref=revision.ingress_route_ref,
            pointer_table="pwp_ingress_routes",
            subject_column="ingress_route_ref",
            pointer_column="current_ingress_route_revision_ref",
            loader=self.get_ingress_route_revision,
        )

    def get_ingress_route_revision(
        self, revision_ref: str
    ) -> IngressRouteRevision | None:
        row = self._revision_row("pwp_ingress_route_revisions", revision_ref)
        if row is None:
            return None
        return IngressRouteRevision(**json.loads(row["payload_json"]))

    def _publish_revision(
        self,
        revision: Revision,
        *,
        table: str,
        revision_ref: str,
        subject_ref: str,
        pointer_table: str,
        subject_column: str,
        pointer_column: str,
        loader: Callable[[str], Revision | None],
        subject_kind: str | None = None,
    ) -> Revision:
        self._validate_revision_common(revision_ref, revision.revision_seq)
        existing = loader(revision_ref)
        if existing is not None:
            if existing == revision:
                return existing
            raise PWPError("REVISION_IDENTITY_CONFLICT", revision_ref=revision_ref)
        payload_json = json.dumps(asdict(revision), sort_keys=True, separators=(",", ":"))
        try:
            with self._store.transaction() as connection:
                pointer = connection.execute(
                    f"SELECT {pointer_column} FROM {pointer_table} WHERE {subject_column}=?",
                    (subject_ref,),
                ).fetchone()[pointer_column]
                if revision.previous_revision_ref != pointer:
                    raise PWPError("REVISION_PREDECESSOR_CONFLICT", revision_ref=revision_ref)
                expected_seq = 1
                if pointer is not None:
                    previous = connection.execute(
                        f"SELECT revision_seq FROM {table} WHERE revision_ref=?",
                        (pointer,),
                    ).fetchone()
                    if previous is None:
                        raise PWPError("REVISION_PREDECESSOR_NOT_RESOLVABLE")
                    expected_seq = previous["revision_seq"] + 1
                if revision.revision_seq != expected_seq:
                    raise PWPError("REVISION_SEQUENCE_CONFLICT", expected=expected_seq)
                columns = "revision_ref,subject_ref,revision_seq,previous_revision_ref,payload_json,created_at,caused_by_ref"
                values: tuple[object, ...] = (
                    revision_ref,
                    subject_ref,
                    revision.revision_seq,
                    revision.previous_revision_ref,
                    payload_json,
                    revision.created_at,
                    revision.caused_by_ref,
                )
                if subject_kind is not None:
                    columns = "revision_ref,subject_kind," + columns[len("revision_ref,"):]
                    values = (revision_ref, subject_kind, *values[1:])
                connection.execute(
                    f"INSERT INTO {table}({columns}) VALUES ({','.join('?' for _ in values)})",
                    values,
                )
                connection.execute(
                    f"UPDATE {pointer_table} SET {pointer_column}=? WHERE {subject_column}=?",
                    (revision_ref, subject_ref),
                )
        except sqlite3.IntegrityError as error:
            raise PWPError("REVISION_BINDING_CONFLICT", revision_ref=revision_ref) from error
        result = loader(revision_ref)
        assert result is not None
        return result

    def _revision_row(self, table: str, revision_ref: str) -> sqlite3.Row | None:
        return self._store.connection.execute(
            f"SELECT * FROM {table} WHERE revision_ref=?", (revision_ref,)
        ).fetchone()

    def _require_project(self, project_ref: str) -> Project:
        project = self.get_project(project_ref)
        if project is None:
            raise PWPError("PROJECT_NOT_FOUND", project_ref=project_ref)
        return project

    def _require_workspace(self, workspace_ref: str) -> Workspace:
        workspace = self.get_workspace(workspace_ref)
        if workspace is None:
            raise PWPError("WORKSPACE_NOT_FOUND", workspace_ref=workspace_ref)
        return workspace

    def _require_ingress_route(self, ingress_route_ref: str) -> IngressRoute:
        route = self.get_ingress_route(ingress_route_ref)
        if route is None:
            raise PWPError("INGRESS_ROUTE_NOT_FOUND", ingress_route_ref=ingress_route_ref)
        return route

    def _require_active_ingress_route(self, ingress_route_ref: str) -> IngressRoute:
        route = self._require_ingress_route(ingress_route_ref)
        if route.state != "ACTIVE":
            raise PWPError("INGRESS_ROUTE_NOT_ACTIVE", ingress_route_ref=ingress_route_ref)
        self._require_active_project(route.project_ref)
        if route.workspace_ref is not None:
            self._require_active_workspace(route.workspace_ref)
        return route

    def _validate_ingress_route_revision(
        self, revision: IngressRouteRevision, route: IngressRoute
    ) -> None:
        for name in (
            "source_adapter_profile_ref",
            "source_auth_policy_ref",
            "input_schema_ref",
            "deduplication_contract_ref",
            "canonical_target_owner_ref",
            "canonical_event_type_ref",
            "canonicalization_contract_ref",
            "project_config_revision_ref",
            "policy_context_revision_ref",
            "caused_by_ref",
        ):
            self._require_ref(getattr(revision, name), name)
        project_config = self.get_project_config_revision(revision.project_config_revision_ref)
        if project_config is None or project_config.project_ref != route.project_ref:
            raise PWPError("PROJECT_CONFIG_NOT_RESOLVABLE")
        policy = self.get_policy_context_revision(revision.policy_context_revision_ref)
        expected_policy_subject = route.workspace_ref or route.project_ref
        expected_policy_kind = "WORKSPACE" if route.workspace_ref is not None else "PROJECT"
        if (
            policy is None
            or policy.subject_kind != expected_policy_kind
            or policy.subject_ref != expected_policy_subject
        ):
            raise PWPError("POLICY_CONTEXT_NOT_RESOLVABLE")
        if route.workspace_ref is None:
            if revision.workspace_config_revision_ref is not None:
                raise PWPError("WORKSPACE_CONFIG_NOT_APPLICABLE")
        else:
            workspace_config = (
                None
                if revision.workspace_config_revision_ref is None
                else self.get_workspace_config_revision(revision.workspace_config_revision_ref)
            )
            if workspace_config is None or workspace_config.workspace_ref != route.workspace_ref:
                raise PWPError("WORKSPACE_CONFIG_NOT_RESOLVABLE")
        if (revision.graph_ingress_binding_ref is None) != (revision.graph_revision_ref is None):
            raise PWPError("GRAPH_INGRESS_BINDING_INCOMPLETE")
        if revision.graph_ingress_binding_ref is not None:
            self._require_ref(
                revision.graph_ingress_binding_ref, "graph_ingress_binding_ref"
            )
            self._require_ref(revision.graph_revision_ref, "graph_revision_ref")
        if revision.enabled_from is not None and revision.enabled_until is not None:
            if revision.enabled_until <= revision.enabled_from:
                raise PWPError("INVALID_INGRESS_ROUTE_ENABLEMENT_WINDOW")

    def _require_active_project(self, project_ref: str) -> Project:
        project = self._require_project(project_ref)
        if project.state != "ACTIVE":
            raise PWPError("PROJECT_NOT_ACTIVE", project_ref=project_ref)
        return project

    def _require_active_workspace(self, workspace_ref: str) -> Workspace:
        workspace = self._require_workspace(workspace_ref)
        if workspace.state != "ACTIVE":
            raise PWPError("WORKSPACE_NOT_ACTIVE", workspace_ref=workspace_ref)
        project = self._require_project(workspace.project_ref)
        if project.state != "ACTIVE":
            raise PWPError("PROJECT_NOT_ACTIVE", project_ref=project.project_ref)
        return workspace

    @staticmethod
    def _tuplify(payload: dict[str, object], *keys: str) -> None:
        for key in keys:
            payload[key] = tuple(payload[key])  # type: ignore[arg-type]

    @staticmethod
    def _require_ref(value: str, name: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise PWPError("INVALID_REFERENCE", field=name)

    def _validate_revision_common(self, revision_ref: str, revision_seq: int) -> None:
        self._require_ref(revision_ref, "revision_ref")
        if not isinstance(revision_seq, int) or isinstance(revision_seq, bool) or revision_seq <= 0:
            raise PWPError("INVALID_REVISION_SEQUENCE")

    def _now(self) -> int:
        value = self._clock()
        if not isinstance(value, int) or isinstance(value, bool):
            raise PWPError("INVALID_CLOCK")
        return value
