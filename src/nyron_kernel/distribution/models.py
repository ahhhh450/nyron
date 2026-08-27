"""Immutable identity records for the bounded Distribution foundation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PackageVersion:
    package_ref: str
    package_version: str
    package_format_version: str
    publisher_ref: str
    namespace: str
    content_digest: str
    manifest_digest: str
    source_registry_ref: str
    provenance_ref: str


@dataclass(frozen=True)
class ModuleVersion:
    module_ref: str
    module_version: str
    definition_digest: str
    entry_artifact_ref: str
    package_ref: str
    package_version: str


@dataclass(frozen=True)
class ResolvedModule:
    module_ref: str
    module_version: str
    definition_digest: str
    entry_artifact_ref: str
    package_ref: str
    package_version: str
    package_format_version: str
    publisher_ref: str
    namespace: str
    content_digest: str
    manifest_digest: str
    source_registry_ref: str
    provenance_ref: str
