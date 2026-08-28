"""Serialized canonical authority for Human Interaction facts."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict

from nyron_kernel.store.sqlite_store import SQLiteStore

from .models import (
    HumanDecisionEvidence,
    HumanRequest,
    HumanResponse,
    RequestState,
    ResponseCandidate,
    ResponseDecision,
    ResponsePolicyRevision,
)


class HumanInteractionConflict(ValueError):
    """A stable canonical identity was reused with different semantics."""


class HumanInteractionRejected(ValueError):
    """A candidate or transition failed the owner acceptance boundary."""


class UnsupportedResponsePolicy(ValueError):
    """The policy asks for aggregation semantics not frozen in this slice."""


class HumanInteractionAuthority:
    """Own requests, accepted responses, lifecycle, and decision evidence."""

    _SUPPORTED_POLICY = (
        "FIRST_VALID",
        "RESPONSE_DECISION",
        "COUNT_ONCE",
        "FIRST_RESPONSE",
        "REJECT_AFTER_TERMINAL",
        "1",
    )

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._create_schema()

    def _create_schema(self) -> None:
        self._store.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS human_response_policy_revisions (
                response_policy_ref TEXT PRIMARY KEY,
                responder_selector_ref TEXT NOT NULL,
                required_approval_count INTEGER NOT NULL CHECK (required_approval_count > 0),
                cardinality_rule TEXT NOT NULL,
                decision_rule TEXT NOT NULL,
                duplicate_principal_rule TEXT NOT NULL,
                conflict_rule TEXT NOT NULL,
                expiry_behavior TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                definition_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS human_requests (
                human_request_ref TEXT PRIMARY KEY,
                project_ref TEXT NOT NULL,
                workspace_ref TEXT NOT NULL,
                policy_context_revision_ref TEXT NOT NULL,
                response_policy_ref TEXT NOT NULL,
                subject_ref TEXT NOT NULL,
                response_schema_ref TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER,
                state TEXT NOT NULL CHECK (state IN ('OPEN','SATISFIED','EXPIRED','CANCELLED','SUPERSEDED')),
                terminal_ref TEXT UNIQUE,
                superseded_by_request_ref TEXT,
                definition_hash TEXT NOT NULL,
                FOREIGN KEY (response_policy_ref) REFERENCES human_response_policy_revisions(response_policy_ref)
            );
            CREATE TABLE IF NOT EXISTS human_responses (
                human_response_ref TEXT PRIMARY KEY,
                human_request_ref TEXT NOT NULL,
                response_policy_ref TEXT NOT NULL,
                principal_ref TEXT NOT NULL,
                decision TEXT NOT NULL CHECK (decision IN ('APPROVE','DENY')),
                semantic_payload_ref TEXT NOT NULL,
                ingress_evidence_ref TEXT NOT NULL,
                authentication_evidence_ref TEXT NOT NULL,
                authorization_evidence_ref TEXT NOT NULL,
                schema_validation_evidence_ref TEXT NOT NULL,
                accepted_at INTEGER NOT NULL,
                definition_hash TEXT NOT NULL,
                FOREIGN KEY (human_request_ref) REFERENCES human_requests(human_request_ref),
                FOREIGN KEY (response_policy_ref) REFERENCES human_response_policy_revisions(response_policy_ref)
            );
            CREATE INDEX IF NOT EXISTS human_responses_request_principal
                ON human_responses(human_request_ref, principal_ref);
            CREATE TABLE IF NOT EXISTS human_decision_evidence (
                decision_evidence_ref TEXT PRIMARY KEY,
                human_request_ref TEXT NOT NULL UNIQUE,
                response_policy_ref TEXT NOT NULL,
                outcome TEXT NOT NULL CHECK (outcome IN ('APPROVED','DENIED')),
                accepted_response_refs_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                definition_hash TEXT NOT NULL,
                FOREIGN KEY (human_request_ref) REFERENCES human_requests(human_request_ref),
                FOREIGN KEY (response_policy_ref) REFERENCES human_response_policy_revisions(response_policy_ref)
            );
            CREATE TRIGGER IF NOT EXISTS human_policy_immutable BEFORE UPDATE ON human_response_policy_revisions
            BEGIN SELECT RAISE(ABORT, 'human response policy immutable'); END;
            CREATE TRIGGER IF NOT EXISTS human_policy_no_delete BEFORE DELETE ON human_response_policy_revisions
            BEGIN SELECT RAISE(ABORT, 'human response policy retained'); END;
            CREATE TRIGGER IF NOT EXISTS human_request_contract_immutable
            BEFORE UPDATE OF human_request_ref, project_ref, workspace_ref, policy_context_revision_ref,
                response_policy_ref, subject_ref, response_schema_ref, created_at, expires_at, definition_hash
            ON human_requests BEGIN SELECT RAISE(ABORT, 'human request contract immutable'); END;
            CREATE TRIGGER IF NOT EXISTS human_request_no_delete BEFORE DELETE ON human_requests
            BEGIN SELECT RAISE(ABORT, 'human request retained'); END;
            CREATE TRIGGER IF NOT EXISTS human_request_lifecycle_transition
            BEFORE UPDATE OF state, terminal_ref, superseded_by_request_ref ON human_requests
            WHEN NOT (
                NEW.state = OLD.state
                AND NEW.terminal_ref IS OLD.terminal_ref
                AND NEW.superseded_by_request_ref IS OLD.superseded_by_request_ref
                OR OLD.state = 'OPEN'
                AND NEW.state IN ('SATISFIED','EXPIRED','CANCELLED','SUPERSEDED')
                AND NEW.terminal_ref IS NOT NULL
                AND (
                    NEW.state = 'SUPERSEDED' AND NEW.superseded_by_request_ref IS NOT NULL
                    OR NEW.state != 'SUPERSEDED' AND NEW.superseded_by_request_ref IS NULL
                )
            )
            BEGIN SELECT RAISE(ABORT, 'invalid human request lifecycle transition'); END;
            CREATE TRIGGER IF NOT EXISTS human_response_immutable BEFORE UPDATE ON human_responses
            BEGIN SELECT RAISE(ABORT, 'human response immutable'); END;
            CREATE TRIGGER IF NOT EXISTS human_response_no_delete BEFORE DELETE ON human_responses
            BEGIN SELECT RAISE(ABORT, 'human response retained'); END;
            CREATE TRIGGER IF NOT EXISTS human_evidence_immutable BEFORE UPDATE ON human_decision_evidence
            BEGIN SELECT RAISE(ABORT, 'human decision evidence immutable'); END;
            CREATE TRIGGER IF NOT EXISTS human_evidence_no_delete BEFORE DELETE ON human_decision_evidence
            BEGIN SELECT RAISE(ABORT, 'human decision evidence retained'); END;
            """
        )

    def register_response_policy(self, policy: ResponsePolicyRevision) -> ResponsePolicyRevision:
        self._validate_policy(policy)
        values = asdict(policy)
        definition_hash = _semantic_hash(values)
        try:
            with self._store.transaction() as connection:
                row = connection.execute(
                    "SELECT definition_hash FROM human_response_policy_revisions WHERE response_policy_ref = ?",
                    (policy.response_policy_ref,),
                ).fetchone()
                if row is not None:
                    if row["definition_hash"] != definition_hash:
                        raise HumanInteractionConflict("response policy identity conflict")
                    return policy
                connection.execute(
                    """INSERT INTO human_response_policy_revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (*values.values(), definition_hash),
                )
        except sqlite3.IntegrityError as error:
            raise HumanInteractionRejected(str(error)) from error
        return policy

    def create_request(self, request: HumanRequest) -> HumanRequest:
        if request.state != RequestState.OPEN or request.terminal_ref is not None or request.superseded_by_request_ref is not None:
            raise HumanInteractionRejected("new request must be OPEN and non-terminal")
        values = asdict(request)
        values["state"] = request.state.value
        definition_hash = _request_contract_hash(request)
        try:
            with self._store.transaction() as connection:
                row = connection.execute(
                    "SELECT definition_hash FROM human_requests WHERE human_request_ref = ?",
                    (request.human_request_ref,),
                ).fetchone()
                if row is not None:
                    if row["definition_hash"] != definition_hash:
                        raise HumanInteractionConflict("human request identity conflict")
                    return self._require_request(connection, request.human_request_ref)
                connection.execute(
                    """INSERT INTO human_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (*values.values(), definition_hash),
                )
        except sqlite3.IntegrityError as error:
            raise HumanInteractionRejected(str(error)) from error
        return request

    def accept_response(self, candidate: ResponseCandidate) -> HumanResponse:
        self._validate_foreign_evidence(candidate)
        response = HumanResponse(**{name: getattr(candidate, name) for name in HumanResponse.__dataclass_fields__})
        definition_hash = _semantic_hash(_enum_values(asdict(response)))
        with self._store.transaction() as connection:
            existing = connection.execute(
                "SELECT definition_hash FROM human_responses WHERE human_response_ref = ?",
                (response.human_response_ref,),
            ).fetchone()
            if existing is not None:
                if existing["definition_hash"] != definition_hash:
                    raise HumanInteractionConflict("human response identity conflict")
                return self._require_response(connection, response.human_response_ref)
            request = self._require_request(connection, response.human_request_ref)
            if request.state != RequestState.OPEN:
                raise HumanInteractionRejected("request is terminal")
            if response.response_policy_ref != request.response_policy_ref:
                raise HumanInteractionRejected("response policy binding mismatch")
            policy = self._require_policy(connection, request.response_policy_ref)
            connection.execute(
                """INSERT INTO human_responses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (*_enum_values(asdict(response)).values(), definition_hash),
            )
            self._aggregate(connection, request, policy, response.accepted_at)
        return response

    def expire_request(self, request_ref: str, terminal_ref: str) -> HumanRequest:
        return self._terminalize(request_ref, RequestState.EXPIRED, terminal_ref)

    def cancel_request(self, request_ref: str, terminal_ref: str) -> HumanRequest:
        return self._terminalize(request_ref, RequestState.CANCELLED, terminal_ref)

    def supersede_request(self, request_ref: str, terminal_ref: str, superseded_by_request_ref: str) -> HumanRequest:
        if not superseded_by_request_ref:
            raise HumanInteractionRejected("supersession target is required")
        return self._terminalize(request_ref, RequestState.SUPERSEDED, terminal_ref, superseded_by_request_ref)

    def _terminalize(self, request_ref: str, state: RequestState, terminal_ref: str, superseded_by: str | None = None) -> HumanRequest:
        if not terminal_ref:
            raise HumanInteractionRejected("terminal identity is required")
        with self._store.transaction() as connection:
            request = self._require_request(connection, request_ref)
            if request.state == state and request.terminal_ref == terminal_ref and request.superseded_by_request_ref == superseded_by:
                return request
            if request.state != RequestState.OPEN:
                raise HumanInteractionConflict("request already terminalized differently")
            connection.execute(
                "UPDATE human_requests SET state = ?, terminal_ref = ?, superseded_by_request_ref = ? WHERE human_request_ref = ? AND state = 'OPEN'",
                (state.value, terminal_ref, superseded_by, request_ref),
            )
            return self._require_request(connection, request_ref)

    def get_request(self, request_ref: str) -> HumanRequest | None:
        row = self._store.connection.execute("SELECT * FROM human_requests WHERE human_request_ref = ?", (request_ref,)).fetchone()
        return None if row is None else _request_from_row(row)

    def get_response_policy(self, policy_ref: str) -> ResponsePolicyRevision | None:
        row = self._store.connection.execute(
            "SELECT * FROM human_response_policy_revisions WHERE response_policy_ref = ?",
            (policy_ref,),
        ).fetchone()
        if row is None:
            return None
        values = dict(row)
        values.pop("definition_hash")
        return ResponsePolicyRevision(**values)

    def get_response(self, response_ref: str) -> HumanResponse | None:
        row = self._store.connection.execute("SELECT * FROM human_responses WHERE human_response_ref = ?", (response_ref,)).fetchone()
        return None if row is None else _response_from_row(row)

    def get_decision_evidence(self, request_ref: str) -> HumanDecisionEvidence | None:
        row = self._store.connection.execute("SELECT * FROM human_decision_evidence WHERE human_request_ref = ?", (request_ref,)).fetchone()
        return None if row is None else _evidence_from_row(row)

    def _aggregate(self, connection: sqlite3.Connection, request: HumanRequest, policy: ResponsePolicyRevision, created_at: int) -> None:
        rows = connection.execute(
            "SELECT human_response_ref, principal_ref, decision FROM human_responses WHERE human_request_ref = ? ORDER BY human_response_ref",
            (request.human_request_ref,),
        ).fetchall()
        if len(rows) != 1:
            raise HumanInteractionConflict("FIRST_VALID policy must have exactly one accepted response")
        outcome = "APPROVED" if rows[0]["decision"] == ResponseDecision.APPROVE.value else "DENIED"
        refs = tuple(row["human_response_ref"] for row in rows)
        evidence_ref = "human-decision:" + _semantic_hash({
            "request": request.human_request_ref,
            "policy": policy.response_policy_ref,
            "outcome": outcome,
            "responses": refs,
        })
        evidence_values = {
            "decision_evidence_ref": evidence_ref,
            "human_request_ref": request.human_request_ref,
            "response_policy_ref": policy.response_policy_ref,
            "outcome": outcome,
            "accepted_response_refs_json": json.dumps(refs, separators=(",", ":")),
            "created_at": created_at,
        }
        connection.execute(
            "INSERT INTO human_decision_evidence VALUES (?, ?, ?, ?, ?, ?, ?)",
            (*evidence_values.values(), _semantic_hash(evidence_values)),
        )
        connection.execute(
            "UPDATE human_requests SET state = 'SATISFIED', terminal_ref = ? WHERE human_request_ref = ? AND state = 'OPEN'",
            (evidence_ref, request.human_request_ref),
        )

    def _validate_policy(self, policy: ResponsePolicyRevision) -> None:
        actual = (
            policy.cardinality_rule, policy.decision_rule, policy.duplicate_principal_rule,
            policy.conflict_rule, policy.expiry_behavior, policy.policy_version,
        )
        if actual != self._SUPPORTED_POLICY or policy.required_approval_count != 1:
            raise UnsupportedResponsePolicy("response policy semantics are unsupported in v0.1")

    @staticmethod
    def _validate_foreign_evidence(candidate: ResponseCandidate) -> None:
        if not candidate.authenticated or not candidate.authentication_evidence_ref:
            raise HumanInteractionRejected("authentication evidence is required")
        if not candidate.authorized or not candidate.authorization_evidence_ref:
            raise HumanInteractionRejected("authorization evidence is required")
        if not candidate.schema_valid or not candidate.schema_validation_evidence_ref:
            raise HumanInteractionRejected("schema validation evidence is required")
        if not candidate.ingress_evidence_ref:
            raise HumanInteractionRejected("ingress evidence is required")

    def _require_request(self, connection: sqlite3.Connection, request_ref: str) -> HumanRequest:
        row = connection.execute("SELECT * FROM human_requests WHERE human_request_ref = ?", (request_ref,)).fetchone()
        if row is None:
            raise HumanInteractionRejected("unknown human request")
        return _request_from_row(row)

    def _require_response(self, connection: sqlite3.Connection, response_ref: str) -> HumanResponse:
        row = connection.execute("SELECT * FROM human_responses WHERE human_response_ref = ?", (response_ref,)).fetchone()
        if row is None:
            raise HumanInteractionRejected("unknown human response")
        return _response_from_row(row)

    def _require_policy(self, connection: sqlite3.Connection, policy_ref: str) -> ResponsePolicyRevision:
        row = connection.execute("SELECT * FROM human_response_policy_revisions WHERE response_policy_ref = ?", (policy_ref,)).fetchone()
        if row is None:
            raise HumanInteractionRejected("unknown response policy")
        values = dict(row)
        values.pop("definition_hash")
        return ResponsePolicyRevision(**values)


def _semantic_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _enum_values(values: dict[str, object]) -> dict[str, object]:
    return {key: value.value if isinstance(value, (RequestState, ResponseDecision)) else value for key, value in values.items()}


def _request_contract_hash(request: HumanRequest) -> str:
    values = asdict(request)
    for key in ("state", "terminal_ref", "superseded_by_request_ref"):
        values.pop(key)
    return _semantic_hash(values)


def _request_from_row(row: sqlite3.Row) -> HumanRequest:
    values = dict(row)
    values.pop("definition_hash")
    values["state"] = RequestState(values["state"])
    return HumanRequest(**values)


def _response_from_row(row: sqlite3.Row) -> HumanResponse:
    values = dict(row)
    values.pop("definition_hash")
    values["decision"] = ResponseDecision(values["decision"])
    return HumanResponse(**values)


def _evidence_from_row(row: sqlite3.Row) -> HumanDecisionEvidence:
    values = dict(row)
    values.pop("definition_hash")
    values["accepted_response_refs"] = tuple(json.loads(values.pop("accepted_response_refs_json")))
    return HumanDecisionEvidence(**values)
