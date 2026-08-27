"""Owner-local durable authority for exact Distribution identity truth."""

from __future__ import annotations

import sqlite3

from nyron_kernel.distribution.models import (
    ModuleVersion,
    PackageVersion,
    ResolvedModule,
)
from nyron_kernel.store import SQLiteStore


class DistributionError(RuntimeError):
    """Fail-closed Distribution error with a stable reason code."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


class DistributionAuthority:
    """Sole application-level writer for this Distribution identity slice."""

    _FLOATING_VERSION_WORDS = frozenset({"latest", "current", "next", "stable"})
    _RANGE_CHARACTERS = frozenset("*^~<>=,|")

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._create_schema()

    def record_package_version(self, package: PackageVersion) -> PackageVersion:
        self._validate_package(package)
        existing = self.get_package_version(package.package_ref, package.package_version)
        if existing is not None:
            if existing == package:
                return existing
            raise DistributionError(
                "PACKAGE_IDENTITY_COLLISION",
                package_ref=package.package_ref,
                package_version=package.package_version,
            )
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO distribution_package_versions(
                        package_ref, package_version, package_format_version,
                        publisher_ref, namespace, content_digest, manifest_digest,
                        source_registry_ref, provenance_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    tuple(package.__dict__.values()),
                )
        except sqlite3.IntegrityError as error:
            raise DistributionError(
                "PACKAGE_IDENTITY_COLLISION",
                package_ref=package.package_ref,
                package_version=package.package_version,
            ) from error
        result = self.get_package_version(package.package_ref, package.package_version)
        assert result is not None
        return result

    def get_package_version(
        self, package_ref: str, package_version: str
    ) -> PackageVersion | None:
        row = self._store.connection.execute(
            "SELECT * FROM distribution_package_versions"
            " WHERE package_ref=? AND package_version=?",
            (package_ref, package_version),
        ).fetchone()
        return None if row is None else PackageVersion(**dict(row))

    def record_module_version(self, module: ModuleVersion) -> ModuleVersion:
        self._validate_module(module)
        if self.get_package_version(module.package_ref, module.package_version) is None:
            raise DistributionError(
                "PACKAGE_NOT_FOUND",
                package_ref=module.package_ref,
                package_version=module.package_version,
            )
        existing = self.get_module_version(module.module_ref, module.module_version)
        if existing is not None:
            if existing == module:
                return existing
            raise DistributionError(
                "MODULE_IDENTITY_COLLISION",
                module_ref=module.module_ref,
                module_version=module.module_version,
            )
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO distribution_module_versions(
                        module_ref, module_version, definition_digest,
                        entry_artifact_ref, package_ref, package_version
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    tuple(module.__dict__.values()),
                )
        except sqlite3.IntegrityError as error:
            raise DistributionError(
                "MODULE_IDENTITY_COLLISION",
                module_ref=module.module_ref,
                module_version=module.module_version,
            ) from error
        result = self.get_module_version(module.module_ref, module.module_version)
        assert result is not None
        return result

    def get_module_version(
        self, module_ref: str, module_version: str
    ) -> ModuleVersion | None:
        row = self._store.connection.execute(
            "SELECT * FROM distribution_module_versions"
            " WHERE module_ref=? AND module_version=?",
            (module_ref, module_version),
        ).fetchone()
        return None if row is None else ModuleVersion(**dict(row))

    def resolve_exact_module(self, selector: str) -> ResolvedModule:
        module_ref, separator, module_version = selector.rpartition("@")
        if not separator or not module_ref or not self._is_exact_version(module_version):
            raise DistributionError("NON_EXACT_MODULE_SELECTOR", selector=selector)
        row = self._store.connection.execute(
            """
            SELECT
                module.module_ref, module.module_version,
                module.definition_digest, module.entry_artifact_ref,
                package.package_ref, package.package_version,
                package.package_format_version, package.publisher_ref,
                package.namespace, package.content_digest,
                package.manifest_digest, package.source_registry_ref,
                package.provenance_ref
            FROM distribution_module_versions AS module
            JOIN distribution_package_versions AS package
              ON package.package_ref = module.package_ref
             AND package.package_version = module.package_version
            WHERE module.module_ref=? AND module.module_version=?
            """,
            (module_ref, module_version),
        ).fetchone()
        if row is None:
            raise DistributionError(
                "MODULE_VERSION_NOT_FOUND",
                module_ref=module_ref,
                module_version=module_version,
            )
        return ResolvedModule(**dict(row))

    def _create_schema(self) -> None:
        self._store.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS distribution_package_versions (
                package_ref TEXT NOT NULL,
                package_version TEXT NOT NULL,
                package_format_version TEXT NOT NULL,
                publisher_ref TEXT NOT NULL,
                namespace TEXT NOT NULL,
                content_digest TEXT NOT NULL,
                manifest_digest TEXT NOT NULL,
                source_registry_ref TEXT NOT NULL,
                provenance_ref TEXT NOT NULL,
                PRIMARY KEY (package_ref, package_version)
            );

            CREATE TABLE IF NOT EXISTS distribution_module_versions (
                module_ref TEXT NOT NULL,
                module_version TEXT NOT NULL,
                definition_digest TEXT NOT NULL,
                entry_artifact_ref TEXT NOT NULL,
                package_ref TEXT NOT NULL,
                package_version TEXT NOT NULL,
                PRIMARY KEY (module_ref, module_version),
                FOREIGN KEY (package_ref, package_version)
                    REFERENCES distribution_package_versions(
                        package_ref, package_version
                    )
            );

            CREATE TRIGGER IF NOT EXISTS distribution_package_version_immutable
            BEFORE UPDATE ON distribution_package_versions
            BEGIN SELECT RAISE(ABORT, 'package version immutable'); END;
            CREATE TRIGGER IF NOT EXISTS distribution_package_version_no_delete
            BEFORE DELETE ON distribution_package_versions
            BEGIN SELECT RAISE(ABORT, 'package version retained'); END;
            CREATE TRIGGER IF NOT EXISTS distribution_module_version_immutable
            BEFORE UPDATE ON distribution_module_versions
            BEGIN SELECT RAISE(ABORT, 'module version immutable'); END;
            CREATE TRIGGER IF NOT EXISTS distribution_module_version_no_delete
            BEFORE DELETE ON distribution_module_versions
            BEGIN SELECT RAISE(ABORT, 'module version retained'); END;
            """
        )

    def _validate_package(self, package: PackageVersion) -> None:
        for field, value in package.__dict__.items():
            self._require_text(value, field)
        self._require_exact_version(package.package_version, "package_version")

    def _validate_module(self, module: ModuleVersion) -> None:
        for field, value in module.__dict__.items():
            self._require_text(value, field)
        self._require_exact_version(module.module_version, "module_version")
        self._require_exact_version(module.package_version, "package_version")

    @classmethod
    def _require_exact_version(cls, value: str, field: str) -> None:
        if not cls._is_exact_version(value):
            raise DistributionError("NON_EXACT_VERSION", field=field, value=value)

    @classmethod
    def _is_exact_version(cls, value: str) -> bool:
        return (
            isinstance(value, str)
            and bool(value)
            and value == value.strip()
            and not any(character.isspace() for character in value)
            and value.casefold() not in cls._FLOATING_VERSION_WORDS
            and not any(character in cls._RANGE_CHARACTERS for character in value)
        )

    @staticmethod
    def _require_text(value: str, field: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise DistributionError("INVALID_IDENTITY_FIELD", field=field)
