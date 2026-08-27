from pathlib import Path
import sqlite3

import pytest

from nyron_kernel.distribution import (
    DistributionAuthority,
    DistributionError,
    ModuleVersion,
    PackageSourceEvidence,
    PackageVersion,
)
from nyron_kernel.store import SQLiteStore


def package(**changes: str) -> PackageVersion:
    fields = {
        "package_ref": "package.example",
        "package_version": "7.2.1",
        "package_format_version": "1",
        "publisher_ref": "publisher.example",
        "namespace": "example",
        "content_digest": "sha256:package-content",
        "manifest_digest": "sha256:package-manifest",
        "provenance_ref": "provenance:build-42",
    }
    fields.update(changes)
    return PackageVersion(**fields)


def module(**changes: str) -> ModuleVersion:
    fields = {
        "module_ref": "module.example/transform",
        "module_version": "3.4.0",
        "definition_digest": "sha256:module-definition",
        "entry_artifact_ref": "artifact:transform.py",
        "package_ref": "package.example",
        "package_version": "7.2.1",
    }
    fields.update(changes)
    return ModuleVersion(**fields)


def source(**changes: str) -> PackageSourceEvidence:
    fields = {
        "package_ref": "package.example",
        "package_version": "7.2.1",
        "source_registry_ref": "registry.local",
        "source_evidence_ref": "publication:local-42",
    }
    fields.update(changes)
    return PackageSourceEvidence(**fields)


def test_package_identity_is_persistent_idempotent_and_immutable(tmp_path: Path) -> None:
    database = tmp_path / "distribution.sqlite"
    with SQLiteStore(database) as store:
        authority = DistributionAuthority(store)
        assert authority.record_package_version(package()) == package()
        assert authority.record_package_version(package()) == package()
        with pytest.raises(DistributionError, match="PACKAGE_IDENTITY_COLLISION"):
            authority.record_package_version(package(content_digest="sha256:other"))
        with pytest.raises(DistributionError, match="PACKAGE_IDENTITY_COLLISION"):
            authority.record_package_version(package(manifest_digest="sha256:other"))
        assert authority.get_package_version("package.example", "7.2.1") == package()

    with SQLiteStore(database) as reopened:
        assert DistributionAuthority(reopened).get_package_version(
            "package.example", "7.2.1"
        ) == package()


def test_module_identity_resolves_exact_provenance_across_restart(
    tmp_path: Path,
) -> None:
    database = tmp_path / "distribution.sqlite"
    with SQLiteStore(database) as store:
        authority = DistributionAuthority(store)
        authority.record_package_version(package())
        authority.record_package_source(source())
        assert authority.record_module_version(module()) == module()
        assert authority.record_module_version(module()) == module()
        resolved = authority.resolve_exact_module("module.example/transform@3.4.0")
        assert resolved.package_ref == "package.example"
        assert resolved.package_version == "7.2.1"
        assert resolved.content_digest == "sha256:package-content"
        assert resolved.manifest_digest == "sha256:package-manifest"
        assert resolved.provenance_ref == "provenance:build-42"
        assert resolved.source_evidence == (source(),)

    with SQLiteStore(database) as reopened:
        resolved = DistributionAuthority(reopened).resolve_exact_module(
            "module.example/transform@3.4.0"
        )
        assert resolved.module_ref == "module.example/transform"
        assert resolved.definition_digest == "sha256:module-definition"
        assert resolved.entry_artifact_ref == "artifact:transform.py"
        assert resolved.content_digest == "sha256:package-content"
        assert resolved.source_evidence == (source(),)


def test_byte_identical_package_accepts_persistent_mirror_evidence(
    tmp_path: Path,
) -> None:
    database = tmp_path / "distribution.sqlite"
    mirror = source(
        source_registry_ref="registry.mirror",
        source_evidence_ref="publication:mirror-9",
    )
    with SQLiteStore(database) as store:
        authority = DistributionAuthority(store)
        authority.record_package_version(package())
        assert authority.record_package_version(package()) == package()
        assert authority.record_package_source(source()) == source()
        assert authority.record_package_source(mirror) == mirror
        assert authority.get_package_sources("package.example", "7.2.1") == (
            source(),
            mirror,
        )

    with SQLiteStore(database) as reopened:
        authority = DistributionAuthority(reopened)
        assert authority.get_package_sources("package.example", "7.2.1") == (
            source(),
            mirror,
        )


def test_module_rebinding_fails_closed_and_preserves_original() -> None:
    with SQLiteStore() as store:
        authority = DistributionAuthority(store)
        authority.record_package_version(package())
        authority.record_module_version(module())
        with pytest.raises(DistributionError, match="MODULE_IDENTITY_COLLISION"):
            authority.record_module_version(
                module(entry_artifact_ref="artifact:different.py")
            )
        assert authority.get_module_version(
            "module.example/transform", "3.4.0"
        ) == module()


def test_module_requires_existing_exact_package_provenance() -> None:
    with SQLiteStore() as store:
        authority = DistributionAuthority(store)
        with pytest.raises(DistributionError, match="PACKAGE_NOT_FOUND"):
            authority.record_module_version(module())


@pytest.mark.parametrize(
    "selector",
    [
        "module.example/transform",
        "module.example/transform@latest",
        "module.example/transform@current",
        "module.example/transform@^3.4",
        "module.example/transform@>=3",
        "module.example/transform@3.*",
        "module.example/transform@",
        "@3.4.0",
        "module.example@transform@3.4.0",
    ],
)
def test_resolver_rejects_non_exact_selectors(selector: str) -> None:
    with SQLiteStore() as store:
        authority = DistributionAuthority(store)
        with pytest.raises(DistributionError, match="NON_EXACT_MODULE_SELECTOR"):
            authority.resolve_exact_module(selector)


def test_unknown_exact_module_fails_closed() -> None:
    with SQLiteStore() as store:
        authority = DistributionAuthority(store)
        with pytest.raises(DistributionError, match="MODULE_VERSION_NOT_FOUND"):
            authority.resolve_exact_module("module.example/missing@1.0.0")


@pytest.mark.parametrize(
    ("record", "error"),
    [
        (lambda: package(package_ref="package@example"), "INVALID_IDENTITY_FIELD"),
        (lambda: package(package_version="7@2"), "NON_EXACT_VERSION"),
        (lambda: module(module_ref="module@example"), "INVALID_IDENTITY_FIELD"),
        (lambda: module(module_version="3@4"), "NON_EXACT_VERSION"),
        (lambda: module(module_ref=""), "INVALID_IDENTITY_FIELD"),
        (lambda: module(module_version=""), "INVALID_IDENTITY_FIELD"),
    ],
)
def test_record_apis_reject_ambiguous_identity_components(record, error: str) -> None:
    with SQLiteStore() as store:
        authority = DistributionAuthority(store)
        candidate = record()
        with pytest.raises(DistributionError, match=error):
            if isinstance(candidate, PackageVersion):
                authority.record_package_version(candidate)
            else:
                authority.record_module_version(candidate)


def test_opaque_structurally_exact_version_is_accepted() -> None:
    with SQLiteStore() as store:
        authority = DistributionAuthority(store)
        exact_package = package(package_version="release/2026.08-build_7")
        exact_module = module(
            module_version="release/2026.08-build_7",
            package_version=exact_package.package_version,
        )
        authority.record_package_version(exact_package)
        authority.record_module_version(exact_module)
        assert authority.resolve_exact_module(
            "module.example/transform@release/2026.08-build_7"
        ).module_version == "release/2026.08-build_7"


def test_raw_sqlite_identity_rows_are_immutable() -> None:
    with SQLiteStore() as store:
        authority = DistributionAuthority(store)
        authority.record_package_version(package())
        authority.record_package_source(source())
        authority.record_module_version(module())
        for table in (
            "distribution_package_versions",
            "distribution_package_sources",
            "distribution_module_versions",
        ):
            with pytest.raises(sqlite3.IntegrityError, match="immutable"):
                store.connection.execute(f"UPDATE {table} SET rowid=rowid")
            with pytest.raises(sqlite3.IntegrityError, match="retained"):
                store.connection.execute(f"DELETE FROM {table}")


def test_distribution_schema_contains_no_authority_side_effect_state() -> None:
    with SQLiteStore() as store:
        DistributionAuthority(store)
        tables = {
            row["name"]
            for row in store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
                " AND name LIKE 'distribution_%'"
            )
        }
        assert tables == {
            "distribution_package_versions",
            "distribution_package_sources",
            "distribution_module_versions",
        }
