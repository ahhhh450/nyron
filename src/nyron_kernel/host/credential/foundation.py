"""Reference-only credential boundary; no secret backend or external I/O."""
from __future__ import annotations

import sqlite3
from dataclasses import astuple, dataclass
from typing import Callable, Protocol, TypeVar

from nyron_kernel.store import SQLiteStore


class CredentialBoundaryError(RuntimeError):
    """Redacted fail-closed error carrying only a stable machine code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

    def __repr__(self) -> str:
        return f"CredentialBoundaryError({self.code!r})"


@dataclass(frozen=True)
class CredentialBindingRevision:
    credential_binding_ref: str
    workspace_secret_ref: str
    profile_ref: str
    profile_revision_ref: str
    binding_class: str
    revision_seq: int
    predecessor_binding_ref: str | None
    creation_evidence_ref: str
    created_at: int


@dataclass(frozen=True)
class CredentialResolutionRequest:
    resolution_request_ref: str
    credential_binding_ref: str
    operation_ref: str
    run_ref: str
    attempt_seq: int
    capability_grant_ref: str
    resource_lease_ref: str
    profile_revision_ref: str


@dataclass(frozen=True)
class CredentialResolutionRecord:
    resolution_request_ref: str
    credential_binding_ref: str
    operation_ref: str
    run_ref: str
    attempt_seq: int
    capability_grant_ref: str
    resource_lease_ref: str
    profile_revision_ref: str
    requested_at: int


class ResolvedCredentialHandle:
    """Opaque, one-use, in-process handle. It is deliberately not serializable."""

    __slots__ = ("__material", "__active")
    _MARKER = "<resolved-credential:redacted>"

    def __init__(self, material: str, issuer: object) -> None:
        if issuer is not _HANDLE_ISSUER or not isinstance(material, str) or not material:
            raise CredentialBoundaryError("CREDENTIAL_HANDLE_CREATION_DENIED")
        self.__material = material
        self.__active = True

    def __repr__(self) -> str:
        return self._MARKER

    __str__ = __repr__

    def __reduce__(self) -> object:
        raise CredentialBoundaryError("CREDENTIAL_HANDLE_NOT_SERIALIZABLE")

    def _use_once(self, consumer: Callable[[str], object], token: object) -> object:
        if token is not _HANDLE_CONSUMER or not self.__active:
            raise CredentialBoundaryError("CREDENTIAL_HANDLE_NOT_ACTIVE")
        try:
            return consumer(self.__material)
        finally:
            self.__material = ""
            self.__active = False


_HANDLE_ISSUER = object()
_HANDLE_CONSUMER = object()


def _issue_resolved_credential(material: str) -> ResolvedCredentialHandle:
    """Private TCB seam used only by explicitly injected trusted resolvers."""
    return ResolvedCredentialHandle(material, _HANDLE_ISSUER)


class CredentialResolver(Protocol):
    def resolve(
        self, binding: CredentialBindingRevision, request: CredentialResolutionRecord
    ) -> ResolvedCredentialHandle: ...


class UnconfiguredCredentialResolver:
    """Production default: no environment/config/keychain/backend fallback."""

    def resolve(
        self, binding: CredentialBindingRevision, request: CredentialResolutionRecord
    ) -> ResolvedCredentialHandle:
        raise CredentialBoundaryError("CREDENTIAL_RESOLVER_NOT_CONFIGURED")


class CredentialRepository:
    def __init__(self, store: SQLiteStore, clock: Callable[[], int]) -> None:
        self._store = store
        self._clock = clock
        store.create_credential_schema()

    def register_binding(
        self, *, credential_binding_ref: str, workspace_secret_ref: str,
        profile_ref: str, profile_revision_ref: str, binding_class: str,
        revision_seq: int, predecessor_binding_ref: str | None,
        creation_evidence_ref: str,
    ) -> CredentialBindingRevision:
        strings = (credential_binding_ref, workspace_secret_ref, profile_ref,
                   profile_revision_ref, binding_class, creation_evidence_ref)
        if any(not isinstance(value, str) or not value for value in strings):
            raise CredentialBoundaryError("CREDENTIAL_BINDING_INVALID")
        if type(revision_seq) is not int or revision_seq <= 0:
            raise CredentialBoundaryError("CREDENTIAL_BINDING_INVALID")
        if predecessor_binding_ref is not None and (
            not isinstance(predecessor_binding_ref, str) or not predecessor_binding_ref
        ):
            raise CredentialBoundaryError("CREDENTIAL_BINDING_INVALID")
        existing = self.resolve_binding(credential_binding_ref)
        now = self._now()
        candidate = CredentialBindingRevision(
            credential_binding_ref, workspace_secret_ref, profile_ref,
            profile_revision_ref, binding_class, revision_seq,
            predecessor_binding_ref, creation_evidence_ref,
            existing.created_at if existing is not None else now,
        )
        if existing is not None:
            if existing == candidate:
                return existing
            raise CredentialBoundaryError("CREDENTIAL_BINDING_IDENTITY_CONFLICT")
        profile = self._store.connection.execute(
            "SELECT profile_ref FROM provider_profile_revisions WHERE profile_revision_ref=?",
            (profile_revision_ref,),
        ).fetchone()
        if profile is None or profile["profile_ref"] != profile_ref:
            raise CredentialBoundaryError("CREDENTIAL_PROFILE_BINDING_INVALID")
        if revision_seq == 1:
            if predecessor_binding_ref is not None:
                raise CredentialBoundaryError("CREDENTIAL_ROTATION_INVALID")
        else:
            predecessor = self.resolve_binding(predecessor_binding_ref or "")
            if predecessor is None or predecessor.revision_seq + 1 != revision_seq or (
                predecessor.profile_ref, predecessor.binding_class
            ) != (profile_ref, binding_class):
                raise CredentialBoundaryError("CREDENTIAL_ROTATION_INVALID")
        insert_failed = False
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    "INSERT INTO credential_binding_revisions VALUES (?,?,?,?,?,?,?,?,?)",
                    astuple(candidate),
                )
        except sqlite3.IntegrityError:
            insert_failed = True
        if insert_failed:
            raise CredentialBoundaryError("CREDENTIAL_BINDING_IDENTITY_CONFLICT")
        return candidate

    def revoke(self, credential_binding_ref: str, evidence_ref: str) -> None:
        self._require_ref(credential_binding_ref); self._require_ref(evidence_ref)
        if self.resolve_binding(credential_binding_ref) is None:
            raise CredentialBoundaryError("CREDENTIAL_BINDING_UNRESOLVED")
        existing = self._store.connection.execute(
            "SELECT evidence_ref FROM credential_binding_revocations WHERE credential_binding_ref=?",
            (credential_binding_ref,),
        ).fetchone()
        if existing is not None:
            if existing["evidence_ref"] == evidence_ref:
                return
            raise CredentialBoundaryError("CREDENTIAL_REVOCATION_CONFLICT")
        insert_failed = False
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    "INSERT INTO credential_binding_revocations VALUES (?,?,?)",
                    (credential_binding_ref, evidence_ref, self._now()),
                )
        except sqlite3.IntegrityError:
            insert_failed = True
        if insert_failed:
            raise CredentialBoundaryError("CREDENTIAL_REVOCATION_CONFLICT")

    def prepare_resolution(
        self, request: CredentialResolutionRequest
    ) -> CredentialResolutionRecord:
        self._validate_resolution_request(request)
        existing = self.resolve_resolution(request.resolution_request_ref)
        now = self._now()
        candidate = CredentialResolutionRecord(
            *astuple(request), existing.requested_at if existing is not None else now
        )
        if existing is not None:
            if existing == candidate:
                return existing
            raise CredentialBoundaryError("CREDENTIAL_RESOLUTION_IDENTITY_CONFLICT")
        binding = self.resolve_binding(request.credential_binding_ref)
        if binding is None:
            raise CredentialBoundaryError("CREDENTIAL_BINDING_UNRESOLVED")
        operation = self._store.connection.execute(
            "SELECT profile_revision_ref, run_ref, attempt_seq, capability_grant_ref, "
            "resource_lease_ref FROM provider_operations WHERE operation_ref=?",
            (request.operation_ref,),
        ).fetchone()
        expected = (request.profile_revision_ref, request.run_ref, request.attempt_seq,
                    request.capability_grant_ref, request.resource_lease_ref)
        if operation is None or tuple(operation) != expected or (
            binding.profile_revision_ref != request.profile_revision_ref
        ):
            raise CredentialBoundaryError("CREDENTIAL_RESOLUTION_CONTEXT_INVALID")
        insert_failed = False
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    "INSERT INTO credential_resolution_requests VALUES (?,?,?,?,?,?,?,?,?)",
                    astuple(candidate),
                )
        except sqlite3.IntegrityError:
            insert_failed = True
        if insert_failed:
            raise CredentialBoundaryError("CREDENTIAL_RESOLUTION_IDENTITY_CONFLICT")
        return candidate

    def resolve_binding(self, ref: str) -> CredentialBindingRevision | None:
        row = self._store.connection.execute(
            "SELECT * FROM credential_binding_revisions WHERE credential_binding_ref=?", (ref,)
        ).fetchone()
        return CredentialBindingRevision(**dict(row)) if row else None

    def resolve_resolution(self, ref: str) -> CredentialResolutionRecord | None:
        row = self._store.connection.execute(
            "SELECT * FROM credential_resolution_requests WHERE resolution_request_ref=?", (ref,)
        ).fetchone()
        return CredentialResolutionRecord(**dict(row)) if row else None

    def is_revoked(self, ref: str) -> bool:
        return self._store.connection.execute(
            "SELECT 1 FROM credential_binding_revocations WHERE credential_binding_ref=?", (ref,)
        ).fetchone() is not None

    def _now(self) -> int:
        value = self._clock()
        if type(value) is not int:
            raise CredentialBoundaryError("CREDENTIAL_CLOCK_INVALID")
        return value

    @staticmethod
    def _require_ref(value: object) -> None:
        if not isinstance(value, str) or not value:
            raise CredentialBoundaryError("CREDENTIAL_REFERENCE_INVALID")

    @classmethod
    def _validate_resolution_request(cls, request: CredentialResolutionRequest) -> None:
        if not isinstance(request, CredentialResolutionRequest):
            raise CredentialBoundaryError("CREDENTIAL_RESOLUTION_REQUEST_INVALID")
        if type(request.attempt_seq) is not int or request.attempt_seq <= 0:
            raise CredentialBoundaryError("CREDENTIAL_RESOLUTION_REQUEST_INVALID")
        for value in astuple(request):
            if not isinstance(value, int):
                cls._require_ref(value)


T = TypeVar("T")


class CredentialResolutionAuthority:
    """Resolves one scoped request without creating or caching dispatch authority."""

    def __init__(self, repository: CredentialRepository) -> None:
        self._repository = repository

    def use_resolved(
        self, request: CredentialResolutionRequest, consumer: Callable[[str], T],
        resolver: CredentialResolver | None = None,
    ) -> T:
        record = self._repository.prepare_resolution(request)
        binding = self._repository.resolve_binding(record.credential_binding_ref)
        assert binding is not None
        if self._repository.is_revoked(binding.credential_binding_ref):
            raise CredentialBoundaryError("CREDENTIAL_BINDING_REVOKED")
        selected = resolver or UnconfiguredCredentialResolver()
        failed = False
        failure_code = "CREDENTIAL_RESOLUTION_FAILED"
        handle: ResolvedCredentialHandle | None = None
        try:
            handle = selected.resolve(binding, record)
            if not isinstance(handle, ResolvedCredentialHandle):
                failed = True
        except CredentialBoundaryError as error:
            failure_code = error.code
            failed = True
        except Exception:
            failed = True
        if failed or handle is None:
            raise CredentialBoundaryError(failure_code)
        consumer_failed = False
        result: object = None
        try:
            result = handle._use_once(consumer, _HANDLE_CONSUMER)
        except Exception:
            consumer_failed = True
        if consumer_failed:
            raise CredentialBoundaryError("CREDENTIAL_CONSUMER_FAILED")
        if result is not None and type(result) not in (bool, int):
            result = None
            raise CredentialBoundaryError("CREDENTIAL_CONSUMER_RESULT_UNSAFE")
        return result  # type: ignore[return-value]
