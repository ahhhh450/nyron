"""Capability Authority-owned Grant issuance and lifecycle truth.

Advisory validation here is deliberately non-consumptive. It is not an
authority-use permit and cannot authorize a later external dispatch or foreign
canonical mutation. Frozen Clarification 004 still forbids plain check-then-use.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Callable

from nyron_kernel.execution import AttemptAuthority, RuntimeAuthorityResolver
from nyron_kernel.store import SQLiteStore

from .registry import CapabilityTypeRegistry


class CapabilityError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class CapabilityRequest:
    grant_ref: str
    capability_type_ref: str
    capability_type_version: str
    authority: AttemptAuthority
    scope: dict[str, Any]
    issued_by: str
    policy_context_ref: str | None = None


@dataclass(frozen=True)
class CapabilityDecision:
    status: str
    policy_decision_ref: str | None = None


@dataclass(frozen=True)
class CapabilityGrant:
    grant_ref: str
    capability_type_ref: str
    capability_type_version: str
    execution_ref: str
    activation_ref: str
    run_ref: str
    attempt_seq: int
    fencing_token: str
    fencing_generation: int
    scope: dict[str, Any]
    issued_by: str
    policy_decision_ref: str | None
    issued_at: int
    not_before: int | None
    expires_at: int | None
    state: str


@dataclass(frozen=True)
class AdvisoryCapabilityValidation:
    """Current query evidence only; never an authority-use admission permit."""

    valid: bool
    reason_code: str


class CapabilityAuthority:
    """Sole writer for CapabilityGrant canonical state in this slice."""

    _DECISIONS = frozenset({"GRANTED", "DENIED", "REQUIRES_APPROVAL"})

    def __init__(
        self,
        store: SQLiteStore,
        registry: CapabilityTypeRegistry,
        runtime_authority: RuntimeAuthorityResolver,
        policy_evaluator: Callable[[CapabilityRequest], CapabilityDecision],
        scope_validator: Callable[[str, object], bool],
        clock: Callable[[], int],
    ) -> None:
        self._store = store
        self._registry = registry
        self._runtime_authority = runtime_authority
        self._policy_evaluator = policy_evaluator
        self._scope_validator = scope_validator
        self._clock = clock
        self._store.create_capability_schema()

    def issue(
        self,
        request: CapabilityRequest,
        *,
        not_before: int | None = None,
        expires_at: int | None = None,
    ) -> CapabilityGrant:
        self._validate_request(request)
        definition = self._registry.resolve(
            request.capability_type_ref, request.capability_type_version
        )
        if definition is None:
            raise CapabilityError("UNRESOLVED_CAPABILITY_TYPE")
        scope_json = self._canonical_scope(request.scope)
        scope = json.loads(scope_json)
        try:
            scope_valid = self._scope_validator(
                definition.scope_schema_ref, scope
            )
        except Exception as error:
            raise CapabilityError("CAPABILITY_SCOPE_INVALID") from error
        if scope_valid is not True:
            raise CapabilityError("CAPABILITY_SCOPE_INVALID")
        if not self._runtime_authority.is_current(request.authority):
            raise CapabilityError("STALE_ATTEMPT_AUTHORITY")
        now = self._now()
        self._validate_validity(now, not_before, expires_at)

        existing = self.resolve(request.grant_ref)
        if existing is not None:
            self._require_identical_replay(
                existing, request, scope, not_before, expires_at
            )
            if not self._runtime_authority.is_current(request.authority):
                raise CapabilityError("STALE_ATTEMPT_AUTHORITY")
            return existing

        try:
            decision = self._policy_evaluator(
                CapabilityRequest(
                    grant_ref=request.grant_ref,
                    capability_type_ref=request.capability_type_ref,
                    capability_type_version=request.capability_type_version,
                    authority=request.authority,
                    scope=scope,
                    issued_by=request.issued_by,
                    policy_context_ref=request.policy_context_ref,
                )
            )
        except Exception as error:
            raise CapabilityError("CAPABILITY_POLICY_DECISION_INVALID") from error
        if (
            not isinstance(decision, CapabilityDecision)
            or decision.status not in self._DECISIONS
            or (
                decision.policy_decision_ref is not None
                and (
                    not isinstance(decision.policy_decision_ref, str)
                    or not decision.policy_decision_ref
                )
            )
        ):
            raise CapabilityError("CAPABILITY_POLICY_DECISION_INVALID")
        if decision.status == "DENIED":
            raise CapabilityError("CAPABILITY_DENIED")
        if decision.status == "REQUIRES_APPROVAL":
            raise CapabilityError("CAPABILITY_REQUIRES_APPROVAL")

        try:
            with self._store.transaction() as connection:
                if not self._runtime_authority.is_current_with(
                    connection, request.authority
                ):
                    raise CapabilityError("STALE_ATTEMPT_AUTHORITY")
                connection.execute(
                    """
                    INSERT INTO capability_grants(
                        grant_ref, capability_type_ref,
                        capability_type_version, execution_ref,
                        activation_ref, run_ref, attempt_seq, fencing_token,
                        fencing_generation, scope_json, issued_by,
                        policy_decision_ref, issued_at, not_before,
                        expires_at, state
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                              'ACTIVE')
                    """,
                    (
                        request.grant_ref,
                        request.capability_type_ref,
                        request.capability_type_version,
                        request.authority.execution_ref,
                        request.authority.activation_ref,
                        request.authority.run_ref,
                        request.authority.attempt_seq,
                        request.authority.fencing_token,
                        request.authority.fencing_generation,
                        scope_json,
                        request.issued_by,
                        decision.policy_decision_ref,
                        now,
                        not_before,
                        expires_at,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise CapabilityError(
                "CAPABILITY_GRANT_IDENTITY_CONFLICT"
            ) from error
        grant = self.resolve(request.grant_ref)
        if grant is None:  # pragma: no cover
            raise CapabilityError("CAPABILITY_GRANT_COMMIT_FAILED")
        return grant

    def resolve(self, grant_ref: str) -> CapabilityGrant | None:
        row = self._store.connection.execute(
            """
            SELECT * FROM capability_grants WHERE grant_ref = ?
            """,
            (grant_ref,),
        ).fetchone()
        return self._grant_from_row(row) if row is not None else None

    def _resolve_active_for_attempt(
        self,
        authority: AttemptAuthority,
        effect_classes: tuple[str, ...],
    ) -> tuple[CapabilityGrant, ...]:
        """Return current, time-valid grants compatible with each requested effect."""

        if (
            type(authority) is not AttemptAuthority
            or not effect_classes
            or any(not isinstance(value, str) or not value for value in effect_classes)
        ):
            return ()
        now = self._now()
        with self._store.transaction() as connection:
            if not self._runtime_authority.is_current_with(connection, authority):
                return ()
            rows = connection.execute(
                """
                SELECT g.*, t.contract_json
                FROM capability_grants AS g
                JOIN capability_types AS t
                  ON t.capability_type_ref = g.capability_type_ref
                 AND t.version = g.capability_type_version
                WHERE g.execution_ref = ? AND g.activation_ref = ?
                  AND g.run_ref = ? AND g.attempt_seq = ?
                  AND g.fencing_token = ? AND g.fencing_generation = ?
                  AND g.state = 'ACTIVE'
                  AND (g.not_before IS NULL OR g.not_before <= ?)
                  AND (g.expires_at IS NULL OR g.expires_at > ?)
                ORDER BY g.grant_ref
                """,
                (
                    authority.execution_ref,
                    authority.activation_ref,
                    authority.run_ref,
                    authority.attempt_seq,
                    authority.fencing_token,
                    authority.fencing_generation,
                    now,
                    now,
                ),
            ).fetchall()
        requested = set(effect_classes)
        grants = tuple(
            self._grant_from_row(row)
            for row in rows
            if requested.intersection(
                json.loads(row["contract_json"])["compatible_effect_classes"]
            )
        )
        covered = {
            effect_class
            for row in rows
            for effect_class in json.loads(row["contract_json"])[
                "compatible_effect_classes"
            ]
            if effect_class in requested
        }
        return grants if covered == requested else ()

    def revoke(self, grant_ref: str) -> CapabilityGrant:
        now = self._now()
        with self._store.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM capability_grants WHERE grant_ref = ?",
                (grant_ref,),
            ).fetchone()
            if row is None:
                raise CapabilityError("UNRESOLVED_CAPABILITY_GRANT")
            if row["state"] == "ACTIVE":
                if row["expires_at"] is not None and now >= row["expires_at"]:
                    connection.execute(
                        "UPDATE capability_grants SET state = 'EXPIRED' WHERE grant_ref = ?",
                        (grant_ref,),
                    )
                else:
                    connection.execute(
                        "UPDATE capability_grants SET state = 'REVOKED' WHERE grant_ref = ?",
                        (grant_ref,),
                    )
        grant = self.resolve(grant_ref)
        if grant is None:  # pragma: no cover
            raise CapabilityError("UNRESOLVED_CAPABILITY_GRANT")
        return grant

    def validate_advisory(
        self,
        grant_ref: str,
        authority: AttemptAuthority,
        expected_scope: dict[str, Any],
    ) -> AdvisoryCapabilityValidation:
        """Recheck current truth without admitting or consuming authority."""

        try:
            expected_scope_json = self._canonical_scope(expected_scope)
        except CapabilityError:
            return AdvisoryCapabilityValidation(False, "CAPABILITY_SCOPE_INVALID")
        now = self._now()
        with self._store.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM capability_grants WHERE grant_ref = ?",
                (grant_ref,),
            ).fetchone()
            if row is None:
                return AdvisoryCapabilityValidation(
                    False, "UNRESOLVED_CAPABILITY_GRANT"
                )
            if (
                row["state"] == "ACTIVE"
                and row["expires_at"] is not None
                and now >= row["expires_at"]
            ):
                connection.execute(
                    "UPDATE capability_grants SET state = 'EXPIRED' WHERE grant_ref = ?",
                    (grant_ref,),
                )
                return AdvisoryCapabilityValidation(False, "CAPABILITY_EXPIRED")
            if row["state"] != "ACTIVE":
                return AdvisoryCapabilityValidation(
                    False, f"CAPABILITY_{row['state']}"
                )
            if row["not_before"] is not None and now < row["not_before"]:
                return AdvisoryCapabilityValidation(
                    False, "CAPABILITY_NOT_YET_VALID"
                )
            if row["scope_json"] != expected_scope_json:
                return AdvisoryCapabilityValidation(
                    False, "CAPABILITY_SCOPE_MISMATCH"
                )
            if self._authority_from_row(row) != authority:
                return AdvisoryCapabilityValidation(
                    False, "CAPABILITY_NON_TRANSFERABLE"
                )
            if not self._runtime_authority.is_current_with(connection, authority):
                return AdvisoryCapabilityValidation(
                    False, "STALE_ATTEMPT_AUTHORITY"
                )
        return AdvisoryCapabilityValidation(True, "ADVISORY_VALID")

    @classmethod
    def _is_effect_dispatch_admissible_with(
        cls,
        connection: sqlite3.Connection,
        grant_ref: str,
        authority: AttemptAuthority,
        exact_scope: dict[str, Any],
        now: int,
    ) -> bool:
        """Check this Owner's exact truth inside the dispatch transaction."""

        row = connection.execute(
            "SELECT * FROM capability_grants WHERE grant_ref = ?",
            (grant_ref,),
        ).fetchone()
        if row is None or row["state"] != "ACTIVE":
            return False
        if row["not_before"] is not None and now < row["not_before"]:
            return False
        if row["expires_at"] is not None and now >= row["expires_at"]:
            return False
        try:
            scope_json = cls._canonical_scope(exact_scope)
        except CapabilityError:
            return False
        return (
            row["scope_json"] == scope_json
            and cls._authority_from_row(row) == authority
        )

    @staticmethod
    def _validate_request(request: CapabilityRequest) -> None:
        if not isinstance(request, CapabilityRequest):
            raise CapabilityError("CAPABILITY_REQUEST_INVALID")
        values = (
            request.grant_ref,
            request.capability_type_ref,
            request.capability_type_version,
            request.issued_by,
        )
        if (
            any(not isinstance(value, str) or not value for value in values)
            or not isinstance(request.authority, AttemptAuthority)
            or not isinstance(request.scope, dict)
            or (
                request.policy_context_ref is not None
                and (
                    not isinstance(request.policy_context_ref, str)
                    or not request.policy_context_ref
                )
            )
        ):
            raise CapabilityError("CAPABILITY_REQUEST_INVALID")

    @staticmethod
    def _canonical_scope(scope: object) -> str:
        if not isinstance(scope, dict):
            raise CapabilityError("CAPABILITY_SCOPE_INVALID")
        try:
            return json.dumps(
                scope,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
        except (TypeError, ValueError) as error:
            raise CapabilityError("CAPABILITY_SCOPE_INVALID") from error

    def _now(self) -> int:
        value = self._clock()
        if not isinstance(value, int) or isinstance(value, bool):
            raise CapabilityError("CAPABILITY_CLOCK_INVALID")
        return value

    @staticmethod
    def _validate_validity(
        issued_at: int, not_before: int | None, expires_at: int | None
    ) -> None:
        if (
            (
                not_before is not None
                and (
                    not isinstance(not_before, int)
                    or isinstance(not_before, bool)
                )
            )
            or (
                expires_at is not None
                and (
                    not isinstance(expires_at, int)
                    or isinstance(expires_at, bool)
                )
            )
            or (expires_at is not None and expires_at <= issued_at)
            or (
                not_before is not None
                and expires_at is not None
                and expires_at <= not_before
            )
        ):
            raise CapabilityError("CAPABILITY_VALIDITY_INVALID")

    @staticmethod
    def _authority_from_row(row: sqlite3.Row) -> AttemptAuthority:
        return AttemptAuthority(
            execution_ref=row["execution_ref"],
            activation_ref=row["activation_ref"],
            run_ref=row["run_ref"],
            attempt_seq=row["attempt_seq"],
            fencing_token=row["fencing_token"],
            fencing_generation=row["fencing_generation"],
        )

    @classmethod
    def _grant_from_row(cls, row: sqlite3.Row) -> CapabilityGrant:
        return CapabilityGrant(
            grant_ref=row["grant_ref"],
            capability_type_ref=row["capability_type_ref"],
            capability_type_version=row["capability_type_version"],
            execution_ref=row["execution_ref"],
            activation_ref=row["activation_ref"],
            run_ref=row["run_ref"],
            attempt_seq=row["attempt_seq"],
            fencing_token=row["fencing_token"],
            fencing_generation=row["fencing_generation"],
            scope=json.loads(row["scope_json"]),
            issued_by=row["issued_by"],
            policy_decision_ref=row["policy_decision_ref"],
            issued_at=row["issued_at"],
            not_before=row["not_before"],
            expires_at=row["expires_at"],
            state=row["state"],
        )

    @classmethod
    def _require_identical_replay(
        cls,
        existing: CapabilityGrant,
        request: CapabilityRequest,
        scope: dict[str, Any],
        not_before: int | None,
        expires_at: int | None,
    ) -> None:
        if (
            existing.capability_type_ref != request.capability_type_ref
            or existing.capability_type_version
            != request.capability_type_version
            or cls._authority_from_grant(existing) != request.authority
            or existing.scope != scope
            or existing.issued_by != request.issued_by
            or existing.not_before != not_before
            or existing.expires_at != expires_at
        ):
            raise CapabilityError("CAPABILITY_GRANT_IDENTITY_CONFLICT")

    @staticmethod
    def _authority_from_grant(grant: CapabilityGrant) -> AttemptAuthority:
        return AttemptAuthority(
            execution_ref=grant.execution_ref,
            activation_ref=grant.activation_ref,
            run_ref=grant.run_ref,
            attempt_seq=grant.attempt_seq,
            fencing_token=grant.fencing_token,
            fencing_generation=grant.fencing_generation,
        )
