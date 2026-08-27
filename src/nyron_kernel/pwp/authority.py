"""Owner-local durable authority for the bounded PWP foundation."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from typing import Callable, TypeVar

from nyron_kernel.pwp.models import (
    EnvironmentBindingEntry,
    EnvironmentBindingRevision,
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
