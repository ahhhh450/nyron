"""One concrete managed-directory Resource and its canonical leases.

Lease validation is advisory and non-consumptive.  It never admits a later
external effect or foreign canonical mutation; frozen Clarification 004 still
forbids using this query as a check-then-use authority boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from nyron_kernel.execution import AttemptAuthority, RuntimeAuthorityResolver
from nyron_kernel.store import SQLiteStore


class ResourceError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class ResourceRequest:
    resource_ref: str
    resource_type: str
    resource_owner_ref: str
    scope: dict[str, Any]


@dataclass(frozen=True)
class Resource:
    resource_ref: str
    resource_type: str
    resource_owner_ref: str
    scope: dict[str, Any]
    state: str
    external_ref: str
    provenance: dict[str, Any]


@dataclass(frozen=True)
class ResourceLease:
    lease_ref: str
    resource_ref: str
    lease_holder_ref: str
    execution_ref: str
    activation_ref: str
    run_ref: str
    attempt_seq: int
    fencing_token: str
    fencing_generation: int
    issued_at: int
    expires_at: int | None
    state: str


@dataclass(frozen=True)
class AdvisoryLeaseValidation:
    """Current evidence only, never an authority-use admission permit."""

    valid: bool
    reason_code: str


class ResourceManager:
    """Sole canonical writer for the bounded managed-directory resource."""

    RESOURCE_TYPE = "nyron.kernel.managed-workspace-handle@1"
    _ROOT_MARKER = ".nyron-resource-root.json"
    _RESOURCE_MARKER = ".nyron-resource.json"

    def __init__(
        self,
        store: SQLiteStore,
        managed_root: str | Path,
        runtime_authority: RuntimeAuthorityResolver,
        clock: Callable[[], int],
        crash_hook: Callable[[str, Resource], None] | None = None,
    ) -> None:
        self._store = store
        self._runtime_authority = runtime_authority
        self._clock = clock
        self._crash_hook = crash_hook or (lambda _stage, _resource: None)
        self._root = Path(managed_root).absolute()
        self._manager_id = self._open_root()
        self._store.create_resource_schema()

    def provision(self, request: ResourceRequest) -> Resource:
        self._validate_resource_request(request)
        scope_json = self._canonical_json(request.scope, "RESOURCE_SCOPE_INVALID")
        external_path = self._path_for(request.resource_ref)
        provenance = {
            "schema": 1,
            "manager_id": self._manager_id,
            "resource_ref": request.resource_ref,
            "external_ref": str(external_path),
        }
        provenance_json = self._canonical_json(provenance, "RESOURCE_PROVENANCE_INVALID")
        existing = self.resolve_resource(request.resource_ref)
        if existing is not None:
            self._require_resource_replay(existing, request, external_path, provenance)
            if existing.state in {"PROVISIONING", "DESTROYING"}:
                return self.recover(request.resource_ref)
            return existing

        try:
            with self._store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO resources(
                        resource_ref, resource_type, resource_owner_ref,
                        scope_json, state, external_ref, provenance_json
                    ) VALUES (?, ?, ?, ?, 'PROVISIONING', ?, ?)
                    """,
                    (
                        request.resource_ref, request.resource_type,
                        request.resource_owner_ref, scope_json,
                        str(external_path), provenance_json,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ResourceError("RESOURCE_IDENTITY_CONFLICT") from error
        intent = self._require_resource(request.resource_ref)
        self._crash_hook("AFTER_PROVISIONING_COMMIT", intent)
        return self.recover(request.resource_ref)

    def recover(self, resource_ref: str) -> Resource:
        resource = self._require_resource(resource_ref)
        path = self._verified_stored_path(resource)
        if resource.state == "PROVISIONING":
            evidence = self._directory_evidence(path, resource.provenance)
            if evidence == "ABSENT":
                try:
                    path.mkdir()
                    self._write_exclusive_json(path / self._RESOURCE_MARKER, resource.provenance)
                except FileExistsError:
                    pass
                evidence = self._directory_evidence(path, resource.provenance)
            if evidence == "EXACT":
                self._crash_hook("AFTER_DIRECTORY_CREATE", resource)
                self._set_resource_state(resource_ref, "AVAILABLE")
            else:
                self._set_resource_state(resource_ref, "UNKNOWN")
        elif resource.state == "DESTROYING":
            evidence = self._directory_evidence(path, resource.provenance)
            if evidence == "EXACT":
                shutil.rmtree(path)
                self._crash_hook("AFTER_DIRECTORY_REMOVE", resource)
                evidence = self._directory_evidence(path, resource.provenance)
            if evidence == "ABSENT":
                self._set_resource_state(resource_ref, "DESTROYED")
            else:
                self._set_resource_state(resource_ref, "UNKNOWN")
        return self._require_resource(resource_ref)

    def destroy(self, resource_ref: str) -> Resource:
        with self._store.transaction() as connection:
            row = connection.execute(
                "SELECT state FROM resources WHERE resource_ref = ?", (resource_ref,)
            ).fetchone()
            if row is None:
                raise ResourceError("UNRESOLVED_RESOURCE")
            active = connection.execute(
                "SELECT 1 FROM resource_leases WHERE resource_ref = ? AND state = 'ACTIVE'",
                (resource_ref,),
            ).fetchone()
            if active is not None:
                raise ResourceError("RESOURCE_HAS_ACTIVE_LEASE")
            if row["state"] == "DESTROYED":
                return self._require_resource(resource_ref)
            if row["state"] not in {"AVAILABLE", "DESTROYING"}:
                raise ResourceError("RESOURCE_NOT_DESTROYABLE")
            connection.execute(
                "UPDATE resources SET state = 'DESTROYING' WHERE resource_ref = ?",
                (resource_ref,),
            )
        destroying = self._require_resource(resource_ref)
        self._crash_hook("AFTER_DESTROYING_COMMIT", destroying)
        return self.recover(resource_ref)

    def issue_lease(
        self,
        lease_ref: str,
        resource_ref: str,
        lease_holder_ref: str,
        authority: AttemptAuthority,
        *,
        expires_at: int | None = None,
    ) -> ResourceLease:
        self._validate_lease_request(lease_ref, resource_ref, lease_holder_ref, authority)
        now = self._now()
        if expires_at is not None and (
            not isinstance(expires_at, int) or isinstance(expires_at, bool)
            or expires_at <= now
        ):
            raise ResourceError("LEASE_VALIDITY_INVALID")
        existing = self.resolve_lease(lease_ref)
        if existing is not None:
            self._require_lease_replay(
                existing, resource_ref, lease_holder_ref, authority, expires_at
            )
            if not self._runtime_authority.is_current(authority):
                raise ResourceError("STALE_ATTEMPT_AUTHORITY")
            return existing
        try:
            with self._store.transaction() as connection:
                resource = connection.execute(
                    "SELECT state FROM resources WHERE resource_ref = ?", (resource_ref,)
                ).fetchone()
                if resource is None:
                    raise ResourceError("UNRESOLVED_RESOURCE")
                if resource["state"] != "AVAILABLE":
                    raise ResourceError("RESOURCE_NOT_AVAILABLE")
                if not self._runtime_authority.is_current_with(connection, authority):
                    raise ResourceError("STALE_ATTEMPT_AUTHORITY")
                connection.execute(
                    """
                    INSERT INTO resource_leases(
                        lease_ref, resource_ref, lease_holder_ref, execution_ref,
                        activation_ref, run_ref, attempt_seq, fencing_token,
                        fencing_generation, issued_at, expires_at, state
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
                    """,
                    (lease_ref, resource_ref, lease_holder_ref,
                     authority.execution_ref, authority.activation_ref,
                     authority.run_ref, authority.attempt_seq,
                     authority.fencing_token, authority.fencing_generation,
                     now, expires_at),
                )
        except sqlite3.IntegrityError as error:
            raise ResourceError("RESOURCE_LEASE_IDENTITY_CONFLICT") from error
        return self._require_lease(lease_ref)

    def release_lease(self, lease_ref: str) -> ResourceLease:
        return self._end_lease(lease_ref, "RELEASED")

    def revoke_lease(self, lease_ref: str) -> ResourceLease:
        return self._end_lease(lease_ref, "REVOKE_REQUESTED")

    def validate_lease_advisory(
        self,
        lease_ref: str,
        resource_ref: str,
        lease_holder_ref: str,
        authority: AttemptAuthority,
    ) -> AdvisoryLeaseValidation:
        """Recheck current truth without admitting or consuming authority."""

        now = self._now()
        with self._store.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM resource_leases WHERE lease_ref = ?", (lease_ref,)
            ).fetchone()
            if row is None:
                return AdvisoryLeaseValidation(False, "UNRESOLVED_RESOURCE_LEASE")
            if row["state"] == "ACTIVE" and row["expires_at"] is not None and now >= row["expires_at"]:
                connection.execute(
                    "UPDATE resource_leases SET state = 'EXPIRED' WHERE lease_ref = ?",
                    (lease_ref,),
                )
                return AdvisoryLeaseValidation(False, "LEASE_EXPIRED")
            if row["state"] != "ACTIVE":
                return AdvisoryLeaseValidation(False, f"LEASE_{row['state']}")
            if row["resource_ref"] != resource_ref or row["lease_holder_ref"] != lease_holder_ref or self._authority_from_row(row) != authority:
                return AdvisoryLeaseValidation(False, "LEASE_NON_TRANSFERABLE")
            resource = connection.execute(
                "SELECT state FROM resources WHERE resource_ref = ?", (resource_ref,)
            ).fetchone()
            if resource is None or resource["state"] != "AVAILABLE":
                return AdvisoryLeaseValidation(False, "RESOURCE_NOT_AVAILABLE")
            if not self._runtime_authority.is_current_with(connection, authority):
                return AdvisoryLeaseValidation(False, "STALE_ATTEMPT_AUTHORITY")
        return AdvisoryLeaseValidation(True, "ADVISORY_VALID")

    def resolve_resource(self, resource_ref: str) -> Resource | None:
        row = self._store.connection.execute(
            "SELECT * FROM resources WHERE resource_ref = ?", (resource_ref,)
        ).fetchone()
        return self._resource_from_row(row) if row is not None else None

    def resolve_lease(self, lease_ref: str) -> ResourceLease | None:
        row = self._store.connection.execute(
            "SELECT * FROM resource_leases WHERE lease_ref = ?", (lease_ref,)
        ).fetchone()
        return self._lease_from_row(row) if row is not None else None

    def _end_lease(self, lease_ref: str, state: str) -> ResourceLease:
        now = self._now()
        with self._store.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM resource_leases WHERE lease_ref = ?", (lease_ref,)
            ).fetchone()
            if row is None:
                raise ResourceError("UNRESOLVED_RESOURCE_LEASE")
            if row["state"] == "ACTIVE":
                target = "EXPIRED" if row["expires_at"] is not None and now >= row["expires_at"] else state
                connection.execute(
                    "UPDATE resource_leases SET state = ? WHERE lease_ref = ?",
                    (target, lease_ref),
                )
        return self._require_lease(lease_ref)

    def _open_root(self) -> str:
        if self._root.exists() and (not self._root.is_dir() or self._root.is_symlink()):
            raise ResourceError("MANAGED_ROOT_INVALID")
        self._root.mkdir(parents=True, exist_ok=True)
        marker = self._root / self._ROOT_MARKER
        if marker.exists():
            try:
                value = json.loads(marker.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise ResourceError("MANAGED_ROOT_PROVENANCE_INVALID") from error
            if set(value) != {"schema", "manager_id"} or value["schema"] != 1 or not isinstance(value["manager_id"], str) or not value["manager_id"]:
                raise ResourceError("MANAGED_ROOT_PROVENANCE_INVALID")
            return value["manager_id"]
        if any(self._root.iterdir()):
            raise ResourceError("MANAGED_ROOT_UNPROVEN")
        manager_id = str(uuid.uuid4())
        self._write_exclusive_json(marker, {"schema": 1, "manager_id": manager_id})
        return manager_id

    def _path_for(self, resource_ref: str) -> Path:
        digest = hashlib.sha256(resource_ref.encode("utf-8")).hexdigest()
        path = self._root / f"resource-{digest}"
        if path.parent != self._root:
            raise ResourceError("RESOURCE_PATH_ESCAPE")
        return path

    def _verified_stored_path(self, resource: Resource) -> Path:
        expected = self._path_for(resource.resource_ref)
        stored = Path(resource.external_ref)
        if stored != expected or stored.parent != self._root:
            raise ResourceError("RESOURCE_PATH_ESCAPE")
        return stored

    def _directory_evidence(self, path: Path, expected: dict[str, Any]) -> str:
        if not path.exists():
            return "ABSENT"
        if not path.is_dir() or path.is_symlink():
            return "MISMATCH"
        marker = path / self._RESOURCE_MARKER
        try:
            value = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return "MISMATCH"
        return "EXACT" if value == expected else "MISMATCH"

    @staticmethod
    def _write_exclusive_json(path: Path, value: dict[str, Any]) -> None:
        data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())

    def _set_resource_state(self, resource_ref: str, state: str) -> None:
        with self._store.transaction() as connection:
            connection.execute(
                "UPDATE resources SET state = ? WHERE resource_ref = ?",
                (state, resource_ref),
            )

    def _require_resource(self, resource_ref: str) -> Resource:
        resource = self.resolve_resource(resource_ref)
        if resource is None:
            raise ResourceError("UNRESOLVED_RESOURCE")
        return resource

    def _require_lease(self, lease_ref: str) -> ResourceLease:
        lease = self.resolve_lease(lease_ref)
        if lease is None:
            raise ResourceError("UNRESOLVED_RESOURCE_LEASE")
        return lease

    @classmethod
    def _validate_resource_request(cls, request: ResourceRequest) -> None:
        if not isinstance(request, ResourceRequest) or any(
            not isinstance(value, str) or not value
            for value in (request.resource_ref, request.resource_type, request.resource_owner_ref)
        ) or not isinstance(request.scope, dict):
            raise ResourceError("RESOURCE_REQUEST_INVALID")
        if request.resource_type != cls.RESOURCE_TYPE:
            raise ResourceError("UNSUPPORTED_RESOURCE_TYPE")

    @staticmethod
    def _validate_lease_request(lease_ref: str, resource_ref: str, holder: str, authority: AttemptAuthority) -> None:
        if any(not isinstance(value, str) or not value for value in (lease_ref, resource_ref, holder)) or not isinstance(authority, AttemptAuthority):
            raise ResourceError("RESOURCE_LEASE_REQUEST_INVALID")

    def _now(self) -> int:
        value = self._clock()
        if not isinstance(value, int) or isinstance(value, bool):
            raise ResourceError("RESOURCE_CLOCK_INVALID")
        return value

    @staticmethod
    def _canonical_json(value: object, code: str) -> str:
        try:
            return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ResourceError(code) from error

    @staticmethod
    def _resource_from_row(row: sqlite3.Row) -> Resource:
        return Resource(row["resource_ref"], row["resource_type"], row["resource_owner_ref"], json.loads(row["scope_json"]), row["state"], row["external_ref"], json.loads(row["provenance_json"]))

    @classmethod
    def _lease_from_row(cls, row: sqlite3.Row) -> ResourceLease:
        return ResourceLease(row["lease_ref"], row["resource_ref"], row["lease_holder_ref"], row["execution_ref"], row["activation_ref"], row["run_ref"], row["attempt_seq"], row["fencing_token"], row["fencing_generation"], row["issued_at"], row["expires_at"], row["state"])

    @staticmethod
    def _authority_from_row(row: sqlite3.Row) -> AttemptAuthority:
        return AttemptAuthority(row["execution_ref"], row["activation_ref"], row["run_ref"], row["attempt_seq"], row["fencing_token"], row["fencing_generation"])

    @staticmethod
    def _authority_from_lease(lease: ResourceLease) -> AttemptAuthority:
        return AttemptAuthority(lease.execution_ref, lease.activation_ref, lease.run_ref, lease.attempt_seq, lease.fencing_token, lease.fencing_generation)

    @classmethod
    def _require_resource_replay(cls, existing: Resource, request: ResourceRequest, path: Path, provenance: dict[str, Any]) -> None:
        if existing.resource_type != request.resource_type or existing.resource_owner_ref != request.resource_owner_ref or existing.scope != request.scope or existing.external_ref != str(path) or existing.provenance != provenance:
            raise ResourceError("RESOURCE_IDENTITY_CONFLICT")

    @classmethod
    def _require_lease_replay(cls, existing: ResourceLease, resource_ref: str, holder: str, authority: AttemptAuthority, expires_at: int | None) -> None:
        if existing.resource_ref != resource_ref or existing.lease_holder_ref != holder or cls._authority_from_lease(existing) != authority or existing.expires_at != expires_at:
            raise ResourceError("RESOURCE_LEASE_IDENTITY_CONFLICT")
