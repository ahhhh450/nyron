from __future__ import annotations

from dataclasses import replace

import pytest

from nyron_kernel.human_interaction import (
    HumanInteractionAuthority,
    HumanInteractionConflict,
    HumanInteractionRejected,
    HumanRequest,
    RequestState,
    ResponseCandidate,
    ResponseDecision,
    ResponsePolicyRevision,
    UnsupportedResponsePolicy,
)
from nyron_kernel.store.sqlite_store import SQLiteStore


def policy(ref: str = "policy:1", count: int = 1) -> ResponsePolicyRevision:
    return ResponsePolicyRevision(ref, "selector:external", count)


def request(ref: str = "request:1", policy_ref: str = "policy:1") -> HumanRequest:
    return HumanRequest(
        human_request_ref=ref,
        project_ref="project:1",
        workspace_ref="workspace:1",
        policy_context_revision_ref="policy-context:7",
        response_policy_ref=policy_ref,
        subject_ref="protected-action:9",
        response_schema_ref="schema:approval:1",
        created_at=100,
        expires_at=500,
    )


def candidate(
    ref: str,
    principal: str,
    decision: ResponseDecision = ResponseDecision.APPROVE,
    request_ref: str = "request:1",
    policy_ref: str = "policy:1",
) -> ResponseCandidate:
    return ResponseCandidate(
        human_response_ref=ref,
        human_request_ref=request_ref,
        response_policy_ref=policy_ref,
        principal_ref=principal,
        decision=decision,
        semantic_payload_ref=f"payload:{ref}",
        ingress_evidence_ref=f"ingress:{ref}",
        authentication_evidence_ref=f"authn:{ref}",
        authorization_evidence_ref=f"authz:{ref}",
        schema_validation_evidence_ref=f"schema-ok:{ref}",
        authenticated=True,
        authorized=True,
        schema_valid=True,
        accepted_at=200,
    )


def authority_with_request(store: SQLiteStore, *, count: int = 1) -> HumanInteractionAuthority:
    authority = HumanInteractionAuthority(store)
    authority.register_response_policy(policy(count=count))
    authority.create_request(request())
    return authority


def response_count(store: SQLiteStore) -> int:
    return store.connection.execute("SELECT COUNT(*) FROM human_responses").fetchone()[0]


def test_request_and_policy_exact_replay_and_conflict_are_fail_closed() -> None:
    with SQLiteStore() as store:
        authority = HumanInteractionAuthority(store)
        original_policy = policy()
        original_request = request()
        assert authority.register_response_policy(original_policy) == original_policy
        assert authority.register_response_policy(original_policy) == original_policy
        with pytest.raises(HumanInteractionConflict):
            authority.register_response_policy(replace(original_policy, responder_selector_ref="selector:other"))
        assert authority.create_request(original_request) == original_request
        assert authority.create_request(original_request) == original_request
        with pytest.raises(HumanInteractionConflict):
            authority.create_request(replace(original_request, workspace_ref="workspace:other"))
        assert authority.get_request("request:1") == original_request


def test_unsupported_aggregation_semantics_fail_closed() -> None:
    with SQLiteStore() as store:
        authority = HumanInteractionAuthority(store)
        with pytest.raises(UnsupportedResponsePolicy):
            authority.register_response_policy(replace(policy(), decision_rule="ROLE_WEIGHTED"))


@pytest.mark.parametrize(
    "order",
    [
        (ResponseDecision.APPROVE, ResponseDecision.DENY),
        (ResponseDecision.DENY, ResponseDecision.APPROVE),
    ],
)
def test_threshold_deny_veto_f001_policy_fails_before_any_truth(
    order: tuple[ResponseDecision, ResponseDecision],
) -> None:
    with SQLiteStore() as store:
        authority = HumanInteractionAuthority(store)
        unsafe = replace(
            policy(),
            cardinality_rule="AT_LEAST",
            decision_rule="APPROVAL_THRESHOLD",
            conflict_rule="DENY_VETO",
        )
        with pytest.raises(UnsupportedResponsePolicy):
            authority.register_response_policy(unsafe)
        assert order in (
            (ResponseDecision.APPROVE, ResponseDecision.DENY),
            (ResponseDecision.DENY, ResponseDecision.APPROVE),
        )
        assert store.connection.execute(
            "SELECT COUNT(*) FROM human_response_policy_revisions"
        ).fetchone()[0] == 0
        assert response_count(store) == 0
        assert authority.get_decision_evidence("request:1") is None


@pytest.mark.parametrize(
    "change",
    [
        {"authenticated": False},
        {"authorized": False},
        {"schema_valid": False},
        {"authentication_evidence_ref": ""},
        {"authorization_evidence_ref": ""},
        {"schema_validation_evidence_ref": ""},
        {"ingress_evidence_ref": ""},
        {"human_request_ref": "request:missing"},
        {"response_policy_ref": "policy:wrong"},
    ],
)
def test_invalid_or_unbound_candidates_never_become_human_response(change: dict[str, object]) -> None:
    with SQLiteStore() as store:
        authority = authority_with_request(store)
        with pytest.raises(HumanInteractionRejected):
            authority.accept_response(replace(candidate("response:1", "principal:1"), **change))
        assert response_count(store) == 0


def test_response_replay_is_idempotent_and_conflict_preserves_original() -> None:
    with SQLiteStore() as store:
        authority = authority_with_request(store)
        original = candidate("response:1", "principal:1")
        accepted = authority.accept_response(original)
        assert authority.accept_response(original) == accepted
        with pytest.raises(HumanInteractionConflict):
            authority.accept_response(replace(original, semantic_payload_ref="payload:changed"))
        assert response_count(store) == 1
        assert authority.get_response("response:1") == accepted


def test_first_valid_is_explicitly_order_semantic_and_duplicate_principal_is_late() -> None:
    with SQLiteStore() as store:
        authority = authority_with_request(store)
        authority.accept_response(candidate("response:first", "principal:1"))
        with pytest.raises(HumanInteractionRejected):
            authority.accept_response(candidate("response:duplicate-principal", "principal:1"))
        current = authority.get_request("request:1")
        evidence = authority.get_decision_evidence("request:1")
        assert current.state == RequestState.SATISFIED
        assert current.terminal_ref == evidence.decision_evidence_ref
        assert evidence.outcome == "APPROVED"
        assert evidence.accepted_response_refs == ("response:first",)
        assert response_count(store) == 1


def test_first_valid_deny_satisfies_with_denied_evidence() -> None:
    with SQLiteStore() as store:
        authority = authority_with_request(store)
        authority.accept_response(candidate("response:deny", "principal:1", ResponseDecision.DENY))
        evidence = authority.get_decision_evidence("request:1")
        assert evidence.outcome == "DENIED"
        assert authority.get_request("request:1").state == RequestState.SATISFIED


def test_terminalization_wins_without_partial_late_response_write() -> None:
    with SQLiteStore() as store:
        authority = authority_with_request(store)
        expired = authority.expire_request("request:1", "expiry:1")
        assert expired.state == RequestState.EXPIRED
        assert authority.expire_request("request:1", "expiry:1") == expired
        with pytest.raises(HumanInteractionRejected):
            authority.accept_response(candidate("response:late", "principal:1"))
        with pytest.raises(HumanInteractionConflict):
            authority.cancel_request("request:1", "cancel:1")
        assert response_count(store) == 0
        assert authority.get_request("request:1") == expired


def test_response_commit_wins_then_losing_terminalization_has_no_partial_write() -> None:
    with SQLiteStore() as store:
        authority = authority_with_request(store, count=1)
        authority.accept_response(candidate("response:1", "principal:1"))
        satisfied = authority.get_request("request:1")
        with pytest.raises(HumanInteractionConflict):
            authority.cancel_request("request:1", "cancel:1")
        assert authority.get_request("request:1") == satisfied
        assert authority.get_decision_evidence("request:1") is not None
        assert response_count(store) == 1


def test_cancel_and_explicit_supersession_are_terminal_and_idempotent() -> None:
    with SQLiteStore() as store:
        authority = HumanInteractionAuthority(store)
        authority.register_response_policy(policy())
        authority.create_request(request("request:cancel"))
        authority.create_request(request("request:replacement"))
        cancelled = authority.cancel_request("request:cancel", "cancel:1")
        assert cancelled.state == RequestState.CANCELLED
        superseded = authority.supersede_request("request:replacement", "supersede:1", "request:new")
        assert superseded.state == RequestState.SUPERSEDED
        assert superseded.superseded_by_request_ref == "request:new"
        assert authority.supersede_request("request:replacement", "supersede:1", "request:new") == superseded


def test_canonical_facts_survive_restart(tmp_path) -> None:
    database = tmp_path / "human-interaction.sqlite"
    with SQLiteStore(database) as store:
        authority = authority_with_request(store, count=1)
        accepted = authority.accept_response(candidate("response:1", "principal:1"))
        expected_request = authority.get_request("request:1")
        expected_evidence = authority.get_decision_evidence("request:1")
    with SQLiteStore(database) as reopened:
        authority = HumanInteractionAuthority(reopened)
        assert authority.get_response_policy("policy:1") == policy(count=1)
        assert authority.get_request("request:1") == expected_request
        assert authority.get_response("response:1") == accepted
        assert authority.get_decision_evidence("request:1") == expected_evidence
        assert authority.accept_response(candidate("response:1", "principal:1")) == accepted


def test_owner_schema_contains_no_runtime_or_foreign_authority_mutation_path() -> None:
    with SQLiteStore() as store:
        authority_with_request(store)
        human_tables = {
            row[0]
            for row in store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'human_%'"
            )
        }
        assert human_tables == {
            "human_response_policy_revisions",
            "human_requests",
            "human_responses",
            "human_decision_evidence",
        }
