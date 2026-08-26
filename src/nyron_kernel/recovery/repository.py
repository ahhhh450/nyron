"""Recovery Owner canonical case, evidence, retry, and disposition state."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Callable

from nyron_kernel.store import SQLiteStore


class RecoveryError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ReconciliationCase:
    reconciliation_case_ref: str
    open_request_ref: str
    subject_owner_ref: str
    subject_ref: str
    reason_code: str
    state: str
    opened_by_ref: str
    attempt_count: int
    max_attempts: int
    retry_policy_ref: str
    backoff_seconds: int
    next_retry_at: int | None
    deadline: int
    escalation_policy_ref: str
    human_request_ref: str | None
    resolution_ref: str | None
    caused_by_ref: str
    opened_at: int
    updated_at: int


@dataclass(frozen=True)
class RecoveryEvidence:
    evidence_ref: str
    evidence_kind: str
    source_authority_ref: str
    source_identity: str
    subject_ref: str | None
    payload_ref: str
    payload_hash: str
    observed_at: int | None
    ingested_at: int
    authenticity_status: str
    semantics_ref: str
    caused_by_ref: str | None


@dataclass(frozen=True)
class RecoveryAttempt:
    attempt_ref: str
    reconciliation_case_ref: str
    attempt_number: int
    observation_kind: str
    scheduled_at: int
    next_retry_at: int | None


@dataclass(frozen=True)
class RecoveryResolution:
    resolution_ref: str
    reconciliation_case_ref: str
    resolution_kind: str
    evidence_refs: tuple[str, ...]
    disposition: str
    disposition_scope: str
    permits_runtime_closure: bool
    policy_ref: str
    caused_by_ref: str
    authorized_by_ref: str | None
    resolved_at: int


class RecoveryRepository:
    """Sole writer for the bounded Recovery-owned foundation."""

    def __init__(self, store: SQLiteStore, clock: Callable[[], int]) -> None:
        self._store = store
        self._clock = clock
        self._install_schema()

    def open_case(
        self,
        *,
        reconciliation_case_ref: str,
        open_request_ref: str,
        subject_owner_ref: str,
        subject_ref: str,
        reason_code: str,
        opened_by_ref: str,
        max_attempts: int,
        retry_policy_ref: str,
        backoff_seconds: int,
        deadline: int,
        escalation_policy_ref: str,
        caused_by_ref: str,
    ) -> ReconciliationCase:
        """Open one stable case per unresolved condition and subject."""

        now = self._clock()
        if max_attempts <= 0 or backoff_seconds < 0 or deadline <= now:
            raise RecoveryError("INVALID_RECOVERY_BOUNDS")
        identity = (
            reconciliation_case_ref,
            open_request_ref,
            subject_owner_ref,
            subject_ref,
            reason_code,
            opened_by_ref,
            max_attempts,
            retry_policy_ref,
            backoff_seconds,
            deadline,
            escalation_policy_ref,
            caused_by_ref,
        )
        existing = self._case_by_open_request(open_request_ref)
        if existing is not None:
            self._require_open_replay(existing, identity)
            return existing
        active = self._active_case(subject_owner_ref, subject_ref, reason_code)
        if active is not None:
            return active
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO reconciliation_cases(
                        reconciliation_case_ref, open_request_ref,
                        subject_owner_ref, subject_ref, reason_code, state,
                        opened_by_ref, attempt_count, max_attempts,
                        retry_policy_ref, backoff_seconds, next_retry_at,
                        deadline, escalation_policy_ref, human_request_ref,
                        resolution_ref, caused_by_ref, opened_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'OPEN', ?, 0, ?, ?, ?, NULL,
                              ?, ?, NULL, NULL, ?, ?, ?)
                    """,
                    identity[:6]
                    + identity[6:9]
                    + (identity[9], identity[10], identity[11], now, now),
                )
        except sqlite3.IntegrityError as error:
            raise RecoveryError("RECONCILIATION_CASE_IDENTITY_CONFLICT") from error
        return self._require_case(reconciliation_case_ref)

    def append_evidence(
        self,
        case_ref: str,
        evidence: RecoveryEvidence,
    ) -> RecoveryEvidence:
        """Append durable evidence without interpreting it as subject truth."""

        self._require_case(case_ref)
        existing = self.resolve_evidence(evidence.evidence_ref)
        if existing is not None:
            if existing != evidence or not self._case_has_evidence(case_ref, evidence.evidence_ref):
                raise RecoveryError("RECOVERY_EVIDENCE_IDENTITY_CONFLICT")
            return existing
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO recovery_evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence.evidence_ref,
                        evidence.evidence_kind,
                        evidence.source_authority_ref,
                        evidence.source_identity,
                        evidence.subject_ref,
                        evidence.payload_ref,
                        evidence.payload_hash,
                        evidence.observed_at,
                        evidence.ingested_at,
                        evidence.authenticity_status,
                        evidence.semantics_ref,
                        evidence.caused_by_ref,
                    ),
                )
                connection.execute(
                    "INSERT INTO reconciliation_case_evidence VALUES (?, ?)",
                    (case_ref, evidence.evidence_ref),
                )
        except sqlite3.IntegrityError as error:
            raise RecoveryError("RECOVERY_EVIDENCE_IDENTITY_CONFLICT") from error
        return evidence

    def record_retry(
        self,
        *,
        case_ref: str,
        attempt_ref: str,
        observation_kind: str,
    ) -> RecoveryAttempt:
        """Commit a stable, bounded observation attempt; never execute an effect."""

        existing = self.resolve_attempt(attempt_ref)
        if existing is not None:
            if (
                existing.reconciliation_case_ref != case_ref
                or existing.observation_kind != observation_kind
            ):
                raise RecoveryError("RECOVERY_ATTEMPT_IDENTITY_CONFLICT")
            return existing
        case = self._require_case(case_ref)
        if case.state in {"RESOLVED", "ESCALATED"}:
            raise RecoveryError("AUTOMATIC_RETRY_AUTHORITY_ENDED")
        now = self._clock()
        if now >= case.deadline:
            self._escalate(case_ref, now)
            raise RecoveryError("RECOVERY_DEADLINE_EXHAUSTED")
        attempt_number = case.attempt_count + 1
        exhausted = attempt_number >= case.max_attempts
        next_retry_at = None if exhausted else min(
            now + case.backoff_seconds * (2 ** (attempt_number - 1)),
            case.deadline,
        )
        state = "ESCALATED" if exhausted else "RETRYING"
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO recovery_attempts VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        attempt_ref,
                        case_ref,
                        attempt_number,
                        observation_kind,
                        now,
                        next_retry_at,
                    ),
                )
                connection.execute(
                    """
                    UPDATE reconciliation_cases
                    SET state = ?, attempt_count = ?, next_retry_at = ?, updated_at = ?
                    WHERE reconciliation_case_ref = ?
                    """,
                    (state, attempt_number, next_retry_at, now, case_ref),
                )
        except sqlite3.IntegrityError as error:
            raise RecoveryError("RECOVERY_ATTEMPT_IDENTITY_CONFLICT") from error
        return self._require_attempt(attempt_ref)

    def enforce_deadline(self, case_ref: str) -> ReconciliationCase:
        case = self._require_case(case_ref)
        now = self._clock()
        if case.state not in {"RESOLVED", "ESCALATED"} and now >= case.deadline:
            self._escalate(case_ref, now)
        return self._require_case(case_ref)

    def resolve_case(self, resolution: RecoveryResolution) -> ReconciliationCase:
        case = self._require_case(resolution.reconciliation_case_ref)
        existing = self.resolve_resolution(resolution.resolution_ref)
        if existing is not None:
            if existing != resolution or case.resolution_ref != resolution.resolution_ref:
                raise RecoveryError("RECOVERY_RESOLUTION_IDENTITY_CONFLICT")
            return case
        if case.state == "RESOLVED":
            raise RecoveryError("RECONCILIATION_CASE_ALREADY_RESOLVED")
        for evidence_ref in resolution.evidence_refs:
            if not self._case_has_evidence(case.reconciliation_case_ref, evidence_ref):
                raise RecoveryError("UNACCEPTED_RECOVERY_EVIDENCE")
        evidence_json = json.dumps(list(resolution.evidence_refs), separators=(",", ":"))
        with self._store.transaction() as connection:
            connection.execute(
                """
                INSERT INTO recovery_resolutions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resolution.resolution_ref,
                    resolution.reconciliation_case_ref,
                    resolution.resolution_kind,
                    evidence_json,
                    resolution.disposition,
                    resolution.disposition_scope,
                    int(resolution.permits_runtime_closure),
                    resolution.policy_ref,
                    resolution.caused_by_ref,
                    resolution.authorized_by_ref,
                    resolution.resolved_at,
                ),
            )
            connection.execute(
                """
                UPDATE reconciliation_cases
                SET state = 'RESOLVED', resolution_ref = ?, next_retry_at = NULL,
                    updated_at = ? WHERE reconciliation_case_ref = ?
                """,
                (
                    resolution.resolution_ref,
                    resolution.resolved_at,
                    resolution.reconciliation_case_ref,
                ),
            )
        return self._require_case(resolution.reconciliation_case_ref)

    def resolve_case_by_ref(self, case_ref: str) -> ReconciliationCase | None:
        row = self._store.connection.execute(
            "SELECT * FROM reconciliation_cases WHERE reconciliation_case_ref = ?",
            (case_ref,),
        ).fetchone()
        return None if row is None else ReconciliationCase(**dict(row))

    def list_evidence(self, case_ref: str) -> tuple[RecoveryEvidence, ...]:
        rows = self._store.connection.execute(
            """
            SELECT e.* FROM recovery_evidence e
            JOIN reconciliation_case_evidence ce USING (evidence_ref)
            WHERE ce.reconciliation_case_ref = ? ORDER BY e.ingested_at, e.evidence_ref
            """,
            (case_ref,),
        )
        return tuple(RecoveryEvidence(**dict(row)) for row in rows)

    def resolve_evidence(self, evidence_ref: str) -> RecoveryEvidence | None:
        row = self._store.connection.execute(
            "SELECT * FROM recovery_evidence WHERE evidence_ref = ?",
            (evidence_ref,),
        ).fetchone()
        return None if row is None else RecoveryEvidence(**dict(row))

    def resolve_attempt(self, attempt_ref: str) -> RecoveryAttempt | None:
        row = self._store.connection.execute(
            "SELECT * FROM recovery_attempts WHERE attempt_ref = ?",
            (attempt_ref,),
        ).fetchone()
        return None if row is None else RecoveryAttempt(**dict(row))

    def resolve_resolution(self, resolution_ref: str) -> RecoveryResolution | None:
        row = self._store.connection.execute(
            "SELECT * FROM recovery_resolutions WHERE resolution_ref = ?",
            (resolution_ref,),
        ).fetchone()
        if row is None:
            return None
        values = dict(row)
        values["evidence_refs"] = tuple(json.loads(values["evidence_refs"]))
        values["permits_runtime_closure"] = bool(values["permits_runtime_closure"])
        return RecoveryResolution(**values)

    def _install_schema(self) -> None:
        self._store.connection.executescript(_SCHEMA)

    def _require_case(self, case_ref: str) -> ReconciliationCase:
        case = self.resolve_case_by_ref(case_ref)
        if case is None:
            raise RecoveryError("UNRESOLVED_RECONCILIATION_CASE")
        return case

    def _require_attempt(self, attempt_ref: str) -> RecoveryAttempt:
        attempt = self.resolve_attempt(attempt_ref)
        if attempt is None:
            raise RecoveryError("UNRESOLVED_RECOVERY_ATTEMPT")
        return attempt

    def _case_by_open_request(self, request_ref: str) -> ReconciliationCase | None:
        row = self._store.connection.execute(
            "SELECT reconciliation_case_ref FROM reconciliation_cases WHERE open_request_ref = ?",
            (request_ref,),
        ).fetchone()
        return None if row is None else self._require_case(row[0])

    def _active_case(self, owner_ref: str, subject_ref: str, reason: str) -> ReconciliationCase | None:
        row = self._store.connection.execute(
            """
            SELECT reconciliation_case_ref FROM reconciliation_cases
            WHERE subject_owner_ref = ? AND subject_ref = ? AND reason_code = ?
              AND state IN ('OPEN', 'RETRYING', 'ESCALATED')
            """,
            (owner_ref, subject_ref, reason),
        ).fetchone()
        return None if row is None else self._require_case(row[0])

    @staticmethod
    def _require_open_replay(case: ReconciliationCase, identity: tuple[object, ...]) -> None:
        actual = (
            case.reconciliation_case_ref, case.open_request_ref,
            case.subject_owner_ref, case.subject_ref, case.reason_code,
            case.opened_by_ref, case.max_attempts, case.retry_policy_ref,
            case.backoff_seconds, case.deadline, case.escalation_policy_ref,
            case.caused_by_ref,
        )
        if actual != identity:
            raise RecoveryError("RECONCILIATION_CASE_IDENTITY_CONFLICT")

    def _case_has_evidence(self, case_ref: str, evidence_ref: str) -> bool:
        return self._store.connection.execute(
            "SELECT 1 FROM reconciliation_case_evidence WHERE reconciliation_case_ref = ? AND evidence_ref = ?",
            (case_ref, evidence_ref),
        ).fetchone() is not None

    def _escalate(self, case_ref: str, now: int) -> None:
        with self._store.transaction() as connection:
            connection.execute(
                """
                UPDATE reconciliation_cases SET state = 'ESCALATED',
                    next_retry_at = NULL, updated_at = ?
                WHERE reconciliation_case_ref = ?
                  AND state IN ('OPEN', 'RETRYING')
                """,
                (now, case_ref),
            )


_SCHEMA = """
CREATE TABLE IF NOT EXISTS reconciliation_cases (
    reconciliation_case_ref TEXT PRIMARY KEY,
    open_request_ref TEXT NOT NULL UNIQUE,
    subject_owner_ref TEXT NOT NULL,
    subject_ref TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('OPEN','RETRYING','RESOLVED','ESCALATED')),
    opened_by_ref TEXT NOT NULL,
    attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
    max_attempts INTEGER NOT NULL CHECK (max_attempts > 0),
    retry_policy_ref TEXT NOT NULL,
    backoff_seconds INTEGER NOT NULL CHECK (backoff_seconds >= 0),
    next_retry_at INTEGER,
    deadline INTEGER NOT NULL,
    escalation_policy_ref TEXT NOT NULL,
    human_request_ref TEXT,
    resolution_ref TEXT UNIQUE,
    caused_by_ref TEXT NOT NULL,
    opened_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_reconciliation_condition
ON reconciliation_cases(subject_owner_ref, subject_ref, reason_code)
WHERE state IN ('OPEN','RETRYING','ESCALATED');
CREATE TABLE IF NOT EXISTS recovery_evidence (
    evidence_ref TEXT PRIMARY KEY, evidence_kind TEXT NOT NULL,
    source_authority_ref TEXT NOT NULL, source_identity TEXT NOT NULL,
    subject_ref TEXT, payload_ref TEXT NOT NULL, payload_hash TEXT NOT NULL,
    observed_at INTEGER, ingested_at INTEGER NOT NULL,
    authenticity_status TEXT NOT NULL, semantics_ref TEXT NOT NULL,
    caused_by_ref TEXT
);
CREATE TABLE IF NOT EXISTS reconciliation_case_evidence (
    reconciliation_case_ref TEXT NOT NULL, evidence_ref TEXT NOT NULL,
    PRIMARY KEY (reconciliation_case_ref, evidence_ref),
    FOREIGN KEY (reconciliation_case_ref) REFERENCES reconciliation_cases(reconciliation_case_ref),
    FOREIGN KEY (evidence_ref) REFERENCES recovery_evidence(evidence_ref)
);
CREATE TABLE IF NOT EXISTS recovery_attempts (
    attempt_ref TEXT PRIMARY KEY, reconciliation_case_ref TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    observation_kind TEXT NOT NULL, scheduled_at INTEGER NOT NULL,
    next_retry_at INTEGER,
    UNIQUE (reconciliation_case_ref, attempt_number),
    FOREIGN KEY (reconciliation_case_ref) REFERENCES reconciliation_cases(reconciliation_case_ref)
);
CREATE TABLE IF NOT EXISTS recovery_resolutions (
    resolution_ref TEXT PRIMARY KEY, reconciliation_case_ref TEXT NOT NULL UNIQUE,
    resolution_kind TEXT NOT NULL, evidence_refs TEXT NOT NULL,
    disposition TEXT NOT NULL, disposition_scope TEXT NOT NULL,
    permits_runtime_closure INTEGER NOT NULL CHECK (permits_runtime_closure IN (0,1)),
    policy_ref TEXT NOT NULL, caused_by_ref TEXT NOT NULL,
    authorized_by_ref TEXT, resolved_at INTEGER NOT NULL,
    FOREIGN KEY (reconciliation_case_ref) REFERENCES reconciliation_cases(reconciliation_case_ref)
);
CREATE TRIGGER IF NOT EXISTS recovery_evidence_immutable BEFORE UPDATE ON recovery_evidence
BEGIN SELECT RAISE(ABORT, 'recovery evidence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS recovery_attempt_immutable BEFORE UPDATE ON recovery_attempts
BEGIN SELECT RAISE(ABORT, 'recovery attempt is immutable'); END;
CREATE TRIGGER IF NOT EXISTS recovery_resolution_immutable BEFORE UPDATE ON recovery_resolutions
BEGIN SELECT RAISE(ABORT, 'recovery resolution is immutable'); END;
CREATE TRIGGER IF NOT EXISTS reconciliation_case_identity_immutable
BEFORE UPDATE ON reconciliation_cases WHEN
 NEW.reconciliation_case_ref != OLD.reconciliation_case_ref OR
 NEW.open_request_ref != OLD.open_request_ref OR
 NEW.subject_owner_ref != OLD.subject_owner_ref OR NEW.subject_ref != OLD.subject_ref OR
 NEW.reason_code != OLD.reason_code OR NEW.opened_by_ref != OLD.opened_by_ref OR
 NEW.max_attempts != OLD.max_attempts OR NEW.retry_policy_ref != OLD.retry_policy_ref OR
 NEW.backoff_seconds != OLD.backoff_seconds OR NEW.deadline != OLD.deadline OR
 NEW.escalation_policy_ref != OLD.escalation_policy_ref OR
 NEW.caused_by_ref != OLD.caused_by_ref OR NEW.opened_at != OLD.opened_at
BEGIN SELECT RAISE(ABORT, 'reconciliation case identity is immutable'); END;
CREATE TRIGGER IF NOT EXISTS reconciliation_case_state_transition
BEFORE UPDATE OF state ON reconciliation_cases WHEN NOT (
 NEW.state = OLD.state OR
 (OLD.state = 'OPEN' AND NEW.state IN ('RETRYING','RESOLVED','ESCALATED')) OR
 (OLD.state = 'RETRYING' AND NEW.state IN ('RESOLVED','ESCALATED')) OR
 (OLD.state = 'ESCALATED' AND NEW.state = 'RESOLVED'))
BEGIN SELECT RAISE(ABORT, 'invalid reconciliation case state transition'); END;
"""
