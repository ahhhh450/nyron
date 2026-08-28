"""Truthful immutable unary Provider profile and operation value models."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderProfileRevision:
    profile_ref: str
    profile_revision_ref: str
    adapter_ref: str
    provider_scope_ref: str
    account_scope_ref: str
    endpoint_scope_ref: str
    model_scope_ref: str
    usage_source_namespace: str
    operation_class: str
    idempotent_same_key: bool
    authoritative_lookup: bool
    lookup_not_found_proves_absence: bool
    cancellation_request: bool
    terminal_cancel_confirmation: bool
    external_identity_recovery: bool
    continuation_resume: bool = False
    streaming: bool = False


@dataclass(frozen=True)
class ProviderOperationRequest:
    operation_ref: str
    semantic_request_hash: str
    profile_revision_ref: str
    idempotency_key: str | None
    dispatch_admission_ref: str
    run_ref: str
    attempt_seq: int
    capability_grant_ref: str
    resource_lease_ref: str
    reservation_ref: str


@dataclass(frozen=True)
class ProviderOperation:
    operation_ref: str
    semantic_request_hash: str
    profile_revision_ref: str
    idempotency_key: str | None
    dispatch_admission_ref: str
    run_ref: str
    attempt_seq: int
    capability_grant_ref: str
    resource_lease_ref: str
    reservation_ref: str
    usage_source_namespace: str
    external_request_id: str | None
    created_at: int


@dataclass(frozen=True)
class ProviderEvidence:
    evidence_ref: str
    operation_ref: str
    evidence_kind: str
    evidence_semantics: str
    authoritative: bool
    historical_outcome: str
    recorded_at: int


@dataclass(frozen=True)
class ProviderDispatchAdmission:
    operation_ref: str
    dispatch_admission_ref: str
    profile_revision_ref: str
    simulated: bool = True
