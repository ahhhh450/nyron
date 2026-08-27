"""Immutable canonical facts owned by Human Interaction."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RequestState(StrEnum):
    OPEN = "OPEN"
    SATISFIED = "SATISFIED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class ResponseDecision(StrEnum):
    APPROVE = "APPROVE"
    DENY = "DENY"


@dataclass(frozen=True)
class ResponsePolicyRevision:
    response_policy_ref: str
    responder_selector_ref: str
    required_approval_count: int
    cardinality_rule: str = "AT_LEAST"
    decision_rule: str = "APPROVAL_THRESHOLD"
    duplicate_principal_rule: str = "COUNT_ONCE"
    conflict_rule: str = "DENY_VETO"
    expiry_behavior: str = "REJECT_AFTER_TERMINAL"
    policy_version: str = "1"


@dataclass(frozen=True)
class HumanRequest:
    human_request_ref: str
    project_ref: str
    workspace_ref: str
    policy_context_revision_ref: str
    response_policy_ref: str
    subject_ref: str
    response_schema_ref: str
    created_at: int
    expires_at: int | None = None
    state: RequestState = RequestState.OPEN
    terminal_ref: str | None = None
    superseded_by_request_ref: str | None = None


@dataclass(frozen=True)
class ResponseCandidate:
    human_response_ref: str
    human_request_ref: str
    response_policy_ref: str
    principal_ref: str
    decision: ResponseDecision
    semantic_payload_ref: str
    ingress_evidence_ref: str
    authentication_evidence_ref: str
    authorization_evidence_ref: str
    schema_validation_evidence_ref: str
    authenticated: bool
    authorized: bool
    schema_valid: bool
    accepted_at: int


@dataclass(frozen=True)
class HumanResponse:
    human_response_ref: str
    human_request_ref: str
    response_policy_ref: str
    principal_ref: str
    decision: ResponseDecision
    semantic_payload_ref: str
    ingress_evidence_ref: str
    authentication_evidence_ref: str
    authorization_evidence_ref: str
    schema_validation_evidence_ref: str
    accepted_at: int


@dataclass(frozen=True)
class HumanDecisionEvidence:
    decision_evidence_ref: str
    human_request_ref: str
    response_policy_ref: str
    outcome: str
    accepted_response_refs: tuple[str, ...]
    created_at: int
