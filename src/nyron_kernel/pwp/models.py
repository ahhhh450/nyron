"""Immutable value objects for the PWP owner foundation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    project_ref: str
    state: str
    created_at: int
    archived_at: int | None
    current_project_config_revision_ref: str | None
    current_policy_context_revision_ref: str | None


@dataclass(frozen=True)
class Workspace:
    workspace_ref: str
    project_ref: str
    parent_workspace_ref: str | None
    state: str
    created_at: int
    archived_at: int | None
    current_workspace_config_revision_ref: str | None
    current_policy_context_revision_ref: str | None
    current_environment_binding_revision_ref: str | None


@dataclass(frozen=True)
class WorkspaceRootDeclaration:
    root_key: str
    root_role: str
    logical_path: str
    mutability_class: str
    required: bool
    portability_class: str
    containment_policy_ref: str


@dataclass(frozen=True)
class EnvironmentBindingEntry:
    binding_key: str
    binding_class: str
    logical_requirement_ref: str
    provider_profile_ref: str | None = None
    local_root_descriptor: str | None = None
    browser_profile_class_ref: str | None = None
    worker_class_ref: str | None = None
    process_profile_ref: str | None = None
    resource_compatibility_descriptor_ref: str | None = None
    secret_ref: str | None = None


@dataclass(frozen=True)
class ProjectConfigRevision:
    project_config_revision_ref: str
    project_ref: str
    revision_seq: int
    previous_revision_ref: str | None
    config_schema_ref: str
    default_workspace_policy_ref: str | None
    default_runtime_admission_policy_ref: str | None
    default_environment_binding_policy_ref: str | None
    default_ingress_policy_ref: str | None
    user_policy_refs: tuple[str, ...]
    system_policy_refs: tuple[str, ...]
    extension_refs: tuple[str, ...]
    created_at: int
    caused_by_ref: str


@dataclass(frozen=True)
class WorkspaceConfigRevision:
    workspace_config_revision_ref: str
    workspace_ref: str
    revision_seq: int
    previous_revision_ref: str | None
    config_schema_ref: str
    root_declarations: tuple[WorkspaceRootDeclaration, ...]
    portability_descriptor_ref: str | None
    environment_binding_revision_ref: str | None
    workspace_policy_refs: tuple[str, ...]
    runtime_admission_policy_refs: tuple[str, ...]
    security_policy_refs: tuple[str, ...]
    secret_refs: tuple[str, ...]
    extension_refs: tuple[str, ...]
    created_at: int
    caused_by_ref: str


@dataclass(frozen=True)
class PolicyContextRevision:
    policy_context_revision_ref: str
    subject_kind: str
    subject_ref: str
    revision_seq: int
    previous_revision_ref: str | None
    project_policy_refs: tuple[str, ...]
    workspace_policy_refs: tuple[str, ...]
    security_policy_refs: tuple[str, ...]
    runtime_admission_policy_refs: tuple[str, ...]
    user_policy_refs: tuple[str, ...]
    system_policy_refs: tuple[str, ...]
    composition_contract_ref: str
    created_at: int
    caused_by_ref: str


@dataclass(frozen=True)
class EnvironmentBindingRevision:
    environment_binding_revision_ref: str
    workspace_ref: str
    revision_seq: int
    previous_revision_ref: str | None
    environment_ref: str
    binding_entries: tuple[EnvironmentBindingEntry, ...]
    portability_constraints: tuple[str, ...]
    created_at: int
    caused_by_ref: str
