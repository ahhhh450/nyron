"""Trusted unary MODEL_INVOKE Provider identity/evidence boundary; no network I/O."""
from __future__ import annotations
import hashlib
import sqlite3
from dataclasses import astuple
from typing import Callable

from nyron_kernel.store import SQLiteStore
from .models import (
    ProviderDispatchAdmission, ProviderEvidence, ProviderOperation,
    ProviderOperationRequest, ProviderProfileRevision,
)


class ProviderFoundationError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code); self.code = code; self.context = context


class ProviderRepository:
    def __init__(self, store: SQLiteStore, clock: Callable[[], int]) -> None:
        self._store = store; self._clock = clock; store.create_provider_schema()

    def register_profile(self, profile: ProviderProfileRevision) -> ProviderProfileRevision:
        self._validate_profile(profile)
        existing = self.resolve_profile(profile.profile_revision_ref)
        if existing is not None:
            if existing == profile: return existing
            raise ProviderFoundationError("PROVIDER_PROFILE_IDENTITY_CONFLICT")
        values = (
            profile.profile_revision_ref, profile.profile_ref, profile.adapter_ref,
            profile.provider_scope_ref, profile.account_scope_ref,
            profile.endpoint_scope_ref, profile.model_scope_ref,
            profile.usage_source_namespace, profile.operation_class,
            int(profile.idempotent_same_key),
            int(profile.authoritative_lookup),
            int(profile.lookup_not_found_proves_absence),
            int(profile.cancellation_request),
            int(profile.terminal_cancel_confirmation),
            int(profile.external_identity_recovery),
            int(profile.continuation_resume), int(profile.streaming),
        )
        try:
            with self._store.transaction() as connection:
                connection.execute("INSERT INTO provider_profile_revisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
        except sqlite3.IntegrityError as error:
            raise ProviderFoundationError("PROVIDER_PROFILE_IDENTITY_CONFLICT") from error
        return profile

    def prepare(self, request: ProviderOperationRequest) -> ProviderOperation:
        self._validate_request(request)
        existing = self.resolve(request.operation_ref)
        if existing is not None:
            expected = astuple(existing)[:11]
            profile = self._require_profile(request.profile_revision_ref)
            supplied = astuple(request) + (profile.usage_source_namespace,)
            if expected == supplied: return existing
            raise ProviderFoundationError("PROVIDER_OPERATION_IDENTITY_CONFLICT")
        profile = self._require_profile(request.profile_revision_ref)
        if profile.idempotent_same_key and request.idempotency_key is None:
            raise ProviderFoundationError("PROVIDER_IDEMPOTENCY_KEY_REQUIRED")
        now = self._now()
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    "INSERT INTO provider_operations VALUES (?,?,?,?,?,?,?,?,?,?,?,NULL,?)",
                    astuple(request) + (profile.usage_source_namespace, now),
                )
        except sqlite3.IntegrityError as error:
            raise ProviderFoundationError("PROVIDER_OPERATION_IDENTITY_CONFLICT") from error
        result = self.resolve(request.operation_ref); assert result is not None; return result

    def bind_external_request_id(self, operation_ref: str, external_request_id: str) -> ProviderOperation:
        self._require_nonempty(external_request_id)
        operation = self._require_operation(operation_ref)
        if operation.external_request_id is not None:
            if operation.external_request_id == external_request_id: return operation
            raise ProviderFoundationError("PROVIDER_EXTERNAL_IDENTITY_CONFLICT")
        try:
            with self._store.transaction() as connection:
                connection.execute("UPDATE provider_operations SET external_request_id=? WHERE operation_ref=? AND external_request_id IS NULL", (external_request_id, operation_ref))
        except sqlite3.IntegrityError as error:
            raise ProviderFoundationError("PROVIDER_EXTERNAL_IDENTITY_CONFLICT") from error
        return self._require_operation(operation_ref)

    def record_evidence(self, *, evidence_ref: str, operation_ref: str, evidence_kind: str,
                        evidence_semantics: str, authoritative: bool,
                        historical_outcome: str) -> ProviderEvidence:
        for value in (evidence_ref, operation_ref, evidence_kind, evidence_semantics, historical_outcome): self._require_nonempty(value)
        if evidence_kind not in {"ACKNOWLEDGEMENT","LOOKUP","CANCEL_REQUEST","CANCEL_CONFIRMATION"} or historical_outcome not in {"UNKNOWN","PARTIAL","KNOWN"} or type(authoritative) is not bool:
            raise ProviderFoundationError("PROVIDER_EVIDENCE_INVALID")
        operation = self._require_operation(operation_ref); profile = self._require_profile(operation.profile_revision_ref)
        if evidence_kind == "LOOKUP" and not profile.authoritative_lookup:
            if authoritative: raise ProviderFoundationError("PROVIDER_LOOKUP_CLAIM_UNSUPPORTED")
            historical_outcome = "UNKNOWN"
        if (
            evidence_kind == "LOOKUP"
            and evidence_semantics == "NOT_FOUND"
            and not profile.lookup_not_found_proves_absence
        ):
            historical_outcome = "UNKNOWN"
        if evidence_kind == "CANCEL_REQUEST" and not profile.cancellation_request:
            raise ProviderFoundationError("PROVIDER_CANCEL_CLAIM_UNSUPPORTED")
        if evidence_kind == "CANCEL_REQUEST":
            historical_outcome = "UNKNOWN"
        if evidence_kind == "CANCEL_CONFIRMATION":
            if not profile.terminal_cancel_confirmation or not authoritative:
                raise ProviderFoundationError("PROVIDER_CANCEL_CONFIRMATION_UNSUPPORTED")
        existing = self.resolve_evidence(evidence_ref)
        if existing is not None:
            candidate = ProviderEvidence(evidence_ref, operation_ref, evidence_kind, evidence_semantics, authoritative, historical_outcome, existing.recorded_at)
            if existing == candidate: return existing
            raise ProviderFoundationError("PROVIDER_EVIDENCE_IDENTITY_CONFLICT")
        now = self._now()
        try:
            with self._store.transaction() as connection:
                connection.execute("INSERT INTO provider_evidence VALUES (?,?,?,?,?,?,?)", (evidence_ref, operation_ref, evidence_kind, evidence_semantics, int(authoritative), historical_outcome, now))
        except sqlite3.IntegrityError as error:
            raise ProviderFoundationError("PROVIDER_EVIDENCE_IDENTITY_CONFLICT") from error
        result = self.resolve_evidence(evidence_ref); assert result is not None; return result

    def usage_source_identity(self, operation_ref: str, provider_line_item_ref: str) -> tuple[str, str]:
        operation = self._require_operation(operation_ref); self._require_nonempty(provider_line_item_ref)
        digest = hashlib.sha256(f"{operation.usage_source_namespace}\\0{operation_ref}\\0{provider_line_item_ref}".encode()).hexdigest()
        return operation.usage_source_namespace, f"provider-usage:{digest}"

    def resolve_profile(self, ref: str) -> ProviderProfileRevision | None:
        row = self._store.connection.execute("SELECT * FROM provider_profile_revisions WHERE profile_revision_ref=?", (ref,)).fetchone()
        return ProviderProfileRevision(**{**dict(row), **{k: bool(row[k]) for k in ('idempotent_same_key','authoritative_lookup','lookup_not_found_proves_absence','cancellation_request','terminal_cancel_confirmation','external_identity_recovery','continuation_resume','streaming')}}) if row else None
    def resolve(self, ref: str) -> ProviderOperation | None:
        row = self._store.connection.execute("SELECT * FROM provider_operations WHERE operation_ref=?", (ref,)).fetchone()
        return ProviderOperation(**dict(row)) if row else None
    def resolve_evidence(self, ref: str) -> ProviderEvidence | None:
        row = self._store.connection.execute("SELECT * FROM provider_evidence WHERE evidence_ref=?", (ref,)).fetchone()
        if not row: return None
        data=dict(row); data['authoritative']=bool(data['authoritative']); return ProviderEvidence(**data)
    def _require_profile(self, ref: str) -> ProviderProfileRevision:
        value=self.resolve_profile(ref)
        if value is None: raise ProviderFoundationError("PROVIDER_PROFILE_UNRESOLVED")
        return value
    def _require_operation(self, ref: str) -> ProviderOperation:
        value=self.resolve(ref)
        if value is None: raise ProviderFoundationError("PROVIDER_OPERATION_UNRESOLVED")
        return value
    def _now(self) -> int:
        value=self._clock()
        if type(value) is not int: raise ProviderFoundationError("PROVIDER_CLOCK_INVALID")
        return value
    @classmethod
    def _validate_profile(cls, p: ProviderProfileRevision) -> None:
        if not isinstance(p, ProviderProfileRevision): raise ProviderFoundationError("PROVIDER_PROFILE_INVALID")
        for value in astuple(p)[:9]: cls._require_nonempty(value)
        if p.operation_class != "MODEL_INVOKE": raise ProviderFoundationError("PROVIDER_PROFILE_OPERATION_UNSUPPORTED")
        if any(type(value) is not bool for value in astuple(p)[9:]): raise ProviderFoundationError("PROVIDER_PROFILE_INVALID")
        if p.streaming or p.continuation_resume: raise ProviderFoundationError("PROVIDER_PROFILE_FEATURE_UNSUPPORTED")
        if p.lookup_not_found_proves_absence and not p.authoritative_lookup: raise ProviderFoundationError("PROVIDER_PROFILE_CLAIM_INVALID")
        if p.terminal_cancel_confirmation and not p.cancellation_request: raise ProviderFoundationError("PROVIDER_PROFILE_CLAIM_INVALID")
    @classmethod
    def _validate_request(cls, r: ProviderOperationRequest) -> None:
        if not isinstance(r, ProviderOperationRequest) or type(r.attempt_seq) is not int or r.attempt_seq <= 0: raise ProviderFoundationError("PROVIDER_OPERATION_INVALID")
        for value in astuple(r):
            if value is not None and not isinstance(value, int): cls._require_nonempty(value)
    @staticmethod
    def _require_nonempty(value: object) -> None:
        if not isinstance(value, str) or not value: raise ProviderFoundationError("PROVIDER_VALUE_INVALID")


class TrustedUnaryProviderBroker:
    """Admission-only simulated boundary. It never performs provider I/O."""
    def __init__(self, store: SQLiteStore, repository: ProviderRepository) -> None:
        self._store=store; self._repository=repository
    def admit_simulated_dispatch(self, operation_ref: str) -> ProviderDispatchAdmission:
        operation=self._repository._require_operation(operation_ref)
        effect=self._store.connection.execute("SELECT * FROM effect_operations WHERE operation_ref=?", (operation_ref,)).fetchone()
        reservation=self._store.connection.execute("SELECT state FROM budget_reservations WHERE reservation_ref=?", (operation.reservation_ref,)).fetchone()
        if effect is None or effect['state'] != 'PREPARED' or effect['dispatch_admission_ref'] != operation.dispatch_admission_ref:
            raise ProviderFoundationError("PROVIDER_EFFECT_ADMISSION_INVALID")
        if effect['effect_class'] != "MODEL_INVOKE":
            raise ProviderFoundationError("PROVIDER_EFFECT_CLASS_INVALID")
        if effect['payload_hash'] != operation.semantic_request_hash:
            raise ProviderFoundationError("PROVIDER_SEMANTIC_REQUEST_BINDING_INVALID")
        if (effect['run_ref'], effect['attempt_seq'], effect['capability_grant_ref'], effect['resource_lease_ref']) != (operation.run_ref, operation.attempt_seq, operation.capability_grant_ref, operation.resource_lease_ref):
            raise ProviderFoundationError("PROVIDER_AUTHORITY_BINDING_INVALID")
        if reservation is None or reservation['state'] != 'RESERVED': raise ProviderFoundationError("PROVIDER_RESERVATION_NOT_RESERVED")
        current = self._store.connection.execute(
            "SELECT attempt.state, attempt.fencing_token, run.fencing_generation "
            "FROM runs AS run JOIN run_attempts AS attempt ON attempt.run_ref=run.run_ref "
            "AND attempt.attempt_seq=run.current_attempt_seq WHERE run.run_ref=?",
            (operation.run_ref,),
        ).fetchone()
        grant = self._store.connection.execute(
            "SELECT state, run_ref, attempt_seq FROM capability_grants WHERE grant_ref=?",
            (operation.capability_grant_ref,),
        ).fetchone()
        lease = self._store.connection.execute(
            "SELECT state, run_ref, attempt_seq FROM resource_leases WHERE lease_ref=?",
            (operation.resource_lease_ref,),
        ).fetchone()
        if current is None or current['state'] != 'ACTIVE' or current['fencing_token'] != effect['fencing_token'] or current['fencing_generation'] != effect['fencing_generation']:
            raise ProviderFoundationError("PROVIDER_ATTEMPT_NOT_CURRENT")
        if grant is None or (grant['state'], grant['run_ref'], grant['attempt_seq']) != ('ACTIVE', operation.run_ref, operation.attempt_seq):
            raise ProviderFoundationError("PROVIDER_GRANT_NOT_ACTIVE")
        if lease is None or (lease['state'], lease['run_ref'], lease['attempt_seq']) != ('ACTIVE', operation.run_ref, operation.attempt_seq):
            raise ProviderFoundationError("PROVIDER_LEASE_NOT_ACTIVE")
        profile=self._repository._require_profile(operation.profile_revision_ref)
        if profile.idempotent_same_key and operation.idempotency_key is None: raise ProviderFoundationError("PROVIDER_IDEMPOTENCY_KEY_REQUIRED")
        return ProviderDispatchAdmission(operation_ref, operation.dispatch_admission_ref, operation.profile_revision_ref)
