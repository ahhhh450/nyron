from __future__ import annotations

import sqlite3

import pytest

from nyron_kernel.pwp import (
    EnvironmentBindingEntry,
    EnvironmentBindingRevision,
    PWPAuthority,
    PWPError,
    PolicyContextRevision,
    ProjectConfigRevision,
    WorkspaceConfigRevision,
    WorkspaceRootDeclaration,
)
from nyron_kernel.store import SQLiteStore


def authority(store: SQLiteStore, now: int = 100) -> PWPAuthority:
    return PWPAuthority(store, clock=lambda: now)


def project_config(ref: str, seq: int, previous: str | None) -> ProjectConfigRevision:
    return ProjectConfigRevision(
        ref, "project:1", seq, previous, "schema:project@1", None, None, None,
        None, ("policy:user",), ("policy:system",), (), 100 + seq, "cause:test",
    )


def workspace_config(ref: str, seq: int, previous: str | None) -> WorkspaceConfigRevision:
    return WorkspaceConfigRevision(
        ref,
        "workspace:1",
        seq,
        previous,
        "schema:workspace@1",
        (WorkspaceRootDeclaration("root", "SOURCE", ".", "MUTABLE", True,
                                  "PORTABLE_LOGICAL", "containment:1"),),
        "portability:1",
        None,
        ("policy:workspace",),
        (),
        ("policy:security",),
        ("secret-ref:1",),
        (),
        100 + seq,
        "cause:test",
    )


def policy(ref: str, seq: int, previous: str | None, *, workspace: bool = False) -> PolicyContextRevision:
    return PolicyContextRevision(
        ref,
        "WORKSPACE" if workspace else "PROJECT",
        "workspace:1" if workspace else "project:1",
        seq,
        previous,
        ("policy:project",),
        ("policy:workspace",) if workspace else (),
        ("policy:security",),
        ("policy:runtime",),
        ("policy:user",),
        ("policy:system",),
        "composition:intersection@1",
        100 + seq,
        "cause:test",
    )


def binding(ref: str, seq: int, previous: str | None) -> EnvironmentBindingRevision:
    return EnvironmentBindingRevision(
        ref,
        "workspace:1",
        seq,
        previous,
        "environment:dev",
        (EnvironmentBindingEntry("root", "LOCAL_ROOT", "requirement:root",
                                 local_root_descriptor="descriptor:local"),),
        ("REBIND_REQUIRED",),
        100 + seq,
        "cause:test",
    )


@pytest.fixture
def pwp() -> tuple[SQLiteStore, PWPAuthority]:
    store = SQLiteStore()
    owner = authority(store)
    owner.create_project("project:1")
    owner.create_workspace("workspace:1", "project:1")
    yield store, owner
    store.close()


def test_project_create_resolve_archive_and_replay(pwp) -> None:
    _, owner = pwp
    assert owner.create_project("project:1") == owner.get_project("project:1")
    archived = owner.archive_project("project:1")
    assert archived.state == "ARCHIVED"
    assert archived.archived_at == 100
    assert owner.archive_project("project:1") == archived


def test_deprecated_lifecycle_is_resolvable_but_rejects_new_governance(pwp) -> None:
    _, owner = pwp
    assert owner.deprecate_workspace("workspace:1").state == "DEPRECATED"
    with pytest.raises(PWPError, match="WORKSPACE_NOT_ACTIVE"):
        owner.publish_workspace_config_revision(workspace_config("workspace-config:1", 1, None))
    assert owner.deprecate_project("project:1").state == "DEPRECATED"
    with pytest.raises(PWPError, match="PROJECT_NOT_ACTIVE"):
        owner.publish_project_config_revision(project_config("project-config:1", 1, None))


def test_workspace_create_resolve_archive_and_identity_binding(pwp) -> None:
    _, owner = pwp
    workspace = owner.create_workspace("workspace:1", "project:1")
    assert workspace.project_ref == "project:1"
    with pytest.raises(PWPError, match="PROJECT_NOT_FOUND"):
        owner.create_workspace("workspace:1", "project:other")
    assert owner.archive_workspace("workspace:1").state == "ARCHIVED"
    assert owner.get_workspace("workspace:1").project_ref == "project:1"


def test_parent_requires_same_project_and_cycle_is_rejected(pwp) -> None:
    store, owner = pwp
    owner.create_project("project:2")
    owner.create_workspace("workspace:2", "project:2")
    with pytest.raises(PWPError, match="WORKSPACE_PARENT_PROJECT_MISMATCH"):
        owner.create_workspace("workspace:bad", "project:1", "workspace:2")
    with pytest.raises(PWPError, match="WORKSPACE_IDENTITY_CONFLICT"):
        owner.create_workspace("workspace:1", "project:1", "workspace:1")
    with pytest.raises(sqlite3.IntegrityError):
        store.connection.execute(
            "UPDATE pwp_workspaces SET parent_workspace_ref='workspace:1'"
            " WHERE workspace_ref='workspace:1'"
        )
    with pytest.raises(sqlite3.IntegrityError):
        store.connection.execute(
            "INSERT INTO pwp_workspaces(workspace_ref,project_ref,"
            "parent_workspace_ref,state,created_at,archived_at)"
            " VALUES ('workspace:self','project:1','workspace:self','ACTIVE',100,NULL)"
        )
    assert owner.resolve_workspace_ancestry("workspace:1")[-1].workspace_ref == "workspace:1"


def test_project_config_history_pointer_and_exact_replay(pwp) -> None:
    _, owner = pwp
    first = project_config("project-config:1", 1, None)
    second = project_config("project-config:2", 2, first.project_config_revision_ref)
    assert owner.publish_project_config_revision(first) == first
    assert owner.publish_project_config_revision(first) == first
    assert owner.publish_project_config_revision(second) == second
    assert owner.get_project_config_revision(first.project_config_revision_ref) == first
    assert owner.get_project("project:1").current_project_config_revision_ref == second.project_config_revision_ref


def test_workspace_config_history_pointer(pwp) -> None:
    _, owner = pwp
    first = workspace_config("workspace-config:1", 1, None)
    second = workspace_config("workspace-config:2", 2, first.workspace_config_revision_ref)
    owner.publish_workspace_config_revision(first)
    owner.publish_workspace_config_revision(second)
    assert owner.get_workspace_config_revision(first.workspace_config_revision_ref) == first
    assert owner.get_workspace("workspace:1").current_workspace_config_revision_ref == second.workspace_config_revision_ref


def test_policy_context_project_and_workspace_histories(pwp) -> None:
    _, owner = pwp
    project_first = policy("policy-context:project:1", 1, None)
    project_second = policy("policy-context:project:2", 2, project_first.policy_context_revision_ref)
    workspace_first = policy("policy-context:workspace:1", 1, None, workspace=True)
    owner.publish_policy_context_revision(project_first)
    owner.publish_policy_context_revision(project_second)
    owner.publish_policy_context_revision(workspace_first)
    assert owner.get_policy_context_revision(project_first.policy_context_revision_ref) == project_first
    assert owner.get_project("project:1").current_policy_context_revision_ref == project_second.policy_context_revision_ref
    assert owner.get_workspace("workspace:1").current_policy_context_revision_ref == workspace_first.policy_context_revision_ref


def test_environment_binding_is_immutable_configuration_only(pwp) -> None:
    _, owner = pwp
    first = binding("environment-binding:1", 1, None)
    second = binding("environment-binding:2", 2, first.environment_binding_revision_ref)
    owner.publish_environment_binding_revision(first)
    owner.publish_environment_binding_revision(second)
    assert owner.get_environment_binding_revision(first.environment_binding_revision_ref) == first
    assert owner.get_workspace("workspace:1").current_environment_binding_revision_ref == second.environment_binding_revision_ref
    assert not hasattr(first, "resource_ref")


def test_conflicting_revision_identity_predecessor_and_sequence_fail_closed(pwp) -> None:
    _, owner = pwp
    first = project_config("project-config:1", 1, None)
    owner.publish_project_config_revision(first)
    conflict = ProjectConfigRevision(**{**first.__dict__, "config_schema_ref": "schema:other"})
    with pytest.raises(PWPError, match="REVISION_IDENTITY_CONFLICT"):
        owner.publish_project_config_revision(conflict)
    with pytest.raises(PWPError, match="REVISION_PREDECESSOR_CONFLICT"):
        owner.publish_project_config_revision(project_config("project-config:bad", 2, None))
    with pytest.raises(PWPError, match="REVISION_SEQUENCE_CONFLICT"):
        owner.publish_project_config_revision(project_config("project-config:bad2", 3, "project-config:1"))


def test_revision_and_pointer_commit_atomically_after_interrupted_write(pwp) -> None:
    store, owner = pwp
    store.connection.execute(
        "CREATE TRIGGER test_interrupt_pointer BEFORE UPDATE OF"
        " current_project_config_revision_ref ON pwp_projects"
        " BEGIN SELECT RAISE(ABORT, 'simulated interruption'); END"
    )
    revision = project_config("project-config:interrupted", 1, None)
    with pytest.raises(PWPError, match="REVISION_BINDING_CONFLICT"):
        owner.publish_project_config_revision(revision)
    assert owner.get_project_config_revision(revision.project_config_revision_ref) is None
    assert owner.get_project("project:1").current_project_config_revision_ref is None
    store.connection.execute("DROP TRIGGER test_interrupt_pointer")
    assert owner.publish_project_config_revision(revision) == revision


def test_raw_pointer_rewind_is_blocked(pwp) -> None:
    store, owner = pwp
    first = project_config("project-config:1", 1, None)
    second = project_config("project-config:2", 2, first.project_config_revision_ref)
    owner.publish_project_config_revision(first)
    owner.publish_project_config_revision(second)
    with pytest.raises(sqlite3.IntegrityError):
        store.connection.execute(
            "UPDATE pwp_projects SET current_project_config_revision_ref=?"
            " WHERE project_ref='project:1'",
            (first.project_config_revision_ref,),
        )


@pytest.mark.parametrize(
    "pointer_kind",
    ["project_policy", "workspace_policy", "environment_binding"],
)
def test_raw_context_pointer_sequence_jumps_fail_closed_across_restart(
    tmp_path, pointer_kind: str
) -> None:
    database = tmp_path / f"{pointer_kind}.db"

    def insert_raw(
        connection: sqlite3.Connection,
        revision_ref: str,
        sequence: int,
        previous_ref: str | None,
    ) -> None:
        if pointer_kind == "environment_binding":
            connection.execute(
                "INSERT INTO pwp_environment_binding_revisions("
                "revision_ref,subject_ref,revision_seq,previous_revision_ref,"
                "payload_json,created_at,caused_by_ref) VALUES (?,?,?,?,?,100,'cause:raw')",
                (revision_ref, "workspace:1", sequence, previous_ref, "{}"),
            )
        else:
            connection.execute(
                "INSERT INTO pwp_policy_context_revisions("
                "revision_ref,subject_kind,subject_ref,revision_seq,"
                "previous_revision_ref,payload_json,created_at,caused_by_ref)"
                " VALUES (?,?,?,?,?,?,100,'cause:raw')",
                (
                    revision_ref,
                    "PROJECT" if pointer_kind == "project_policy" else "WORKSPACE",
                    "project:1" if pointer_kind == "project_policy" else "workspace:1",
                    sequence,
                    previous_ref,
                    "{}",
                ),
            )

    def advance_raw(connection: sqlite3.Connection, revision_ref: str) -> None:
        if pointer_kind == "project_policy":
            connection.execute(
                "UPDATE pwp_projects SET current_policy_context_revision_ref=?"
                " WHERE project_ref='project:1'",
                (revision_ref,),
            )
        elif pointer_kind == "workspace_policy":
            connection.execute(
                "UPDATE pwp_workspaces SET current_policy_context_revision_ref=?"
                " WHERE workspace_ref='workspace:1'",
                (revision_ref,),
            )
        else:
            connection.execute(
                "UPDATE pwp_workspaces SET current_environment_binding_revision_ref=?"
                " WHERE workspace_ref='workspace:1'",
                (revision_ref,),
            )

    def current_pointer(owner: PWPAuthority) -> str | None:
        if pointer_kind == "project_policy":
            return owner.get_project("project:1").current_policy_context_revision_ref
        workspace = owner.get_workspace("workspace:1")
        if pointer_kind == "workspace_policy":
            return workspace.current_policy_context_revision_ref
        return workspace.current_environment_binding_revision_ref

    def valid_revision(ref: str, sequence: int, previous_ref: str | None):
        if pointer_kind == "project_policy":
            return policy(ref, sequence, previous_ref)
        if pointer_kind == "workspace_policy":
            return policy(ref, sequence, previous_ref, workspace=True)
        return binding(ref, sequence, previous_ref)

    def publish(owner: PWPAuthority, revision) -> None:
        if pointer_kind == "environment_binding":
            owner.publish_environment_binding_revision(revision)
        else:
            owner.publish_policy_context_revision(revision)

    initial_ref = f"{pointer_kind}:valid:1"
    initial_jump_ref = f"{pointer_kind}:jump:initial"
    successor_ref = f"{pointer_kind}:valid:2"
    successor_jump_ref = f"{pointer_kind}:jump:successor"

    with SQLiteStore(database) as store:
        owner = authority(store)
        owner.create_project("project:1")
        owner.create_workspace("workspace:1", "project:1")
        with pytest.raises(sqlite3.IntegrityError):
            with store.transaction() as connection:
                insert_raw(connection, initial_jump_ref, 99, None)
                advance_raw(connection, initial_jump_ref)

    with SQLiteStore(database) as reopened:
        owner = authority(reopened)
        assert current_pointer(owner) is None
        table = (
            "pwp_environment_binding_revisions"
            if pointer_kind == "environment_binding"
            else "pwp_policy_context_revisions"
        )
        assert reopened.connection.execute(
            f"SELECT 1 FROM {table} WHERE revision_ref=?", (initial_jump_ref,)
        ).fetchone() is None
        publish(owner, valid_revision(initial_ref, 1, None))

    with SQLiteStore(database) as reopened:
        owner = authority(reopened)
        assert current_pointer(owner) == initial_ref
        with pytest.raises(sqlite3.IntegrityError):
            with reopened.transaction() as connection:
                insert_raw(connection, successor_jump_ref, 77, initial_ref)
                advance_raw(connection, successor_jump_ref)
        assert current_pointer(owner) == initial_ref
        publish(owner, valid_revision(successor_ref, 2, initial_ref))

    with SQLiteStore(database) as reopened:
        owner = authority(reopened)
        assert current_pointer(owner) == successor_ref
        assert reopened.connection.execute(
            f"SELECT 1 FROM {table} WHERE revision_ref=?", (successor_jump_ref,)
        ).fetchone() is None


@pytest.mark.parametrize("table", [
    "pwp_project_config_revisions",
    "pwp_workspace_config_revisions",
    "pwp_policy_context_revisions",
    "pwp_environment_binding_revisions",
])
def test_raw_revision_update_and_delete_are_blocked(pwp, table: str) -> None:
    store, owner = pwp
    revisions = {
        "pwp_project_config_revisions": project_config("pc:raw", 1, None),
        "pwp_workspace_config_revisions": workspace_config("wc:raw", 1, None),
        "pwp_policy_context_revisions": policy("pol:raw", 1, None),
        "pwp_environment_binding_revisions": binding("env:raw", 1, None),
    }
    publishers = {
        "pwp_project_config_revisions": owner.publish_project_config_revision,
        "pwp_workspace_config_revisions": owner.publish_workspace_config_revision,
        "pwp_policy_context_revisions": owner.publish_policy_context_revision,
        "pwp_environment_binding_revisions": owner.publish_environment_binding_revision,
    }
    revision = revisions[table]
    publishers[table](revision)
    ref = next(value for key, value in revision.__dict__.items() if key.endswith("revision_ref") and key != "previous_revision_ref")
    with pytest.raises(sqlite3.IntegrityError):
        store.connection.execute(f"UPDATE {table} SET caused_by_ref='rewrite' WHERE revision_ref=?", (ref,))
    with pytest.raises(sqlite3.IntegrityError):
        store.connection.execute(f"DELETE FROM {table} WHERE revision_ref=?", (ref,))


def test_restart_and_archive_preserve_exact_history(tmp_path) -> None:
    database = tmp_path / "pwp.db"
    with SQLiteStore(database) as store:
        owner = authority(store)
        owner.create_project("project:1")
        owner.create_workspace("workspace:1", "project:1")
        owner.publish_project_config_revision(project_config("project-config:1", 1, None))
        owner.publish_workspace_config_revision(workspace_config("workspace-config:1", 1, None))
        owner.publish_policy_context_revision(policy("policy-context:1", 1, None))
        owner.publish_environment_binding_revision(binding("environment-binding:1", 1, None))
        owner.archive_workspace("workspace:1")
        owner.archive_project("project:1")
    with SQLiteStore(database) as reopened:
        owner = authority(reopened, now=200)
        assert owner.get_project_config_revision("project-config:1") is not None
        assert owner.get_workspace_config_revision("workspace-config:1") is not None
        assert owner.get_policy_context_revision("policy-context:1") is not None
        assert owner.get_environment_binding_revision("environment-binding:1") is not None
        assert owner.get_project("project:1").state == "ARCHIVED"
        assert owner.get_workspace("workspace:1").state == "ARCHIVED"


def test_schema_contains_no_foreign_owner_canonical_tables(pwp) -> None:
    store, _ = pwp
    pwp_tables = {
        row["name"] for row in store.connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'pwp_%'"
        )
    }
    assert pwp_tables == {
        "pwp_projects", "pwp_workspaces", "pwp_project_config_revisions",
        "pwp_workspace_config_revisions", "pwp_policy_context_revisions",
        "pwp_environment_binding_revisions",
    }
