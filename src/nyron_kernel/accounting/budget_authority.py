"""Accounting Owner: BudgetPolicyRevision / BudgetReservation foundation
(ARE-GATE-6A).

This slice implements only reservation authorization: durable
BudgetPolicyRevision publication, static-ancestry-atomic hard-limit
reserve/deny, and stable request-identity idempotency. It deliberately does
NOT implement UsageFact settlement, the COMMITTED/RELEASED transition,
ReconciliationCase/Recovery, or provider billing -- those remain future
Gate-6 slices. ``committed_dimensions``/``released_dimensions`` therefore
stay empty on every reservation this module ever produces.

Only ``LIFETIME_LIMIT`` rules are enforced in this slice (a single
monotonic hard cap with no window/reset machinery). Publishing a rule with
any other ``limit_kind`` is rejected at publish time rather than silently
accepted and left unenforced at reserve time -- an unenforced HARD rule
would be an unsafe silent gap, not a narrower implementation.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from typing import Callable

from nyron_kernel.accounting.scope_resolver import (
    AccountingScopeError,
    AccountingScopeResolver,
)
from nyron_kernel.store import SQLiteStore

_SUPPORTED_LIMIT_KINDS = ("LIFETIME_LIMIT",)
_SUPPORTED_ENFORCEMENTS = ("HARD", "SOFT")
_RESERVATION_STATES = (
    "REQUESTED",
    "RESERVED",
    "DENIED",
    "RECONCILING",
    "COMMITTED",
    "RELEASED",
)


class BudgetAuthorityError(RuntimeError):
    """Fail-closed Accounting-owned error with a stable reason code."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class BudgetDimension:
    dimension_ref: str
    unit: str
    measurement_semantics_ref: str


@dataclass(frozen=True)
class BudgetRule:
    rule_ref: str
    dimension_ref: str
    limit_amount: int
    limit_kind: str
    enforcement: str


@dataclass(frozen=True)
class BudgetPolicyRevision:
    budget_policy_revision_ref: str
    accounting_scope_ref: str
    effective_from: int
    effective_until: int | None
    dimensions: tuple[BudgetDimension, ...]
    enforcement_rules: tuple[BudgetRule, ...]
    created_by_ref: str
    supersedes_ref: str | None


@dataclass(frozen=True)
class BudgetReservationRequest:
    """Caller-supplied reservation intent. Not itself canonical truth."""

    request_ref: str
    activation_ref: str
    run_ref: str
    attempt_seq: int
    accounting_scope_ref: str
    graph_revision_ref: str
    definition_anchor_ref: str
    estimate_ref: str
    reserved_dimensions: tuple[tuple[str, int], ...]
    subject_refs: tuple[str, ...]
    caused_by_ref: str


@dataclass(frozen=True)
class BudgetReservation:
    reservation_ref: str
    request_ref: str
    activation_ref: str
    run_ref: str
    attempt_seq: int
    accounting_scope_ref: str
    ancestry_snapshot: tuple[str, ...]
    policy_revision_refs: tuple[str, ...]
    estimate_ref: str
    requested_dimensions: tuple[tuple[str, int], ...]
    reserved_dimensions: tuple[tuple[str, int], ...]
    committed_dimensions: tuple[tuple[str, int], ...]
    released_dimensions: tuple[tuple[str, int], ...]
    state: str
    deny_reason_code: str | None
    subject_refs: tuple[str, ...]
    created_at: int
    updated_at: int
    caused_by_ref: str


class BudgetAuthority:
    """Sole canonical writer for BudgetPolicyRevision and BudgetReservation."""

    def __init__(
        self,
        store: SQLiteStore,
        scope_resolver: AccountingScopeResolver,
        clock: Callable[[], int],
        crash_hook: Callable[[str], None] | None = None,
    ) -> None:
        self._store = store
        self._scope_resolver = scope_resolver
        self._clock = clock
        self._crash_hook = crash_hook or (lambda _stage: None)
        self._store.create_budget_schema()

    # ------------------------------------------------------------------
    # BudgetPolicyRevision publication
    # ------------------------------------------------------------------

    def publish_policy_revision(
        self, revision: BudgetPolicyRevision
    ) -> BudgetPolicyRevision:
        """Persist one immutable policy revision, idempotently for identical facts."""

        self._validate_revision(revision)
        existing = self._load_revision(revision.budget_policy_revision_ref)
        if existing is not None:
            if existing == revision:
                return existing
            raise BudgetAuthorityError(
                "BUDGET_POLICY_REVISION_IDENTITY_CONFLICT",
                budget_policy_revision_ref=revision.budget_policy_revision_ref,
            )
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO budget_policy_revisions(
                        budget_policy_revision_ref, accounting_scope_ref,
                        effective_from, effective_until, dimensions_json,
                        enforcement_rules_json, created_by_ref, supersedes_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        revision.budget_policy_revision_ref,
                        revision.accounting_scope_ref,
                        revision.effective_from,
                        revision.effective_until,
                        self._encode_dimensions(revision.dimensions),
                        self._encode_rules(revision.enforcement_rules),
                        revision.created_by_ref,
                        revision.supersedes_ref,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise BudgetAuthorityError(
                "BUDGET_POLICY_REVISION_IDENTITY_CONFLICT",
                budget_policy_revision_ref=revision.budget_policy_revision_ref,
            ) from error
        return revision

    # ------------------------------------------------------------------
    # BudgetReservation
    # ------------------------------------------------------------------

    def reserve(self, request: BudgetReservationRequest) -> BudgetReservation:
        """Validate identity, then atomically evaluate and commit RESERVED/DENIED."""

        self._validate_request(request)
        existing = self._load_reservation_by_request_ref(request.request_ref)
        if existing is not None:
            self._require_identical_replay(existing, request)
            return existing

        reservation_ref = self._reservation_ref(request.request_ref)
        now = self._now()

        try:
            with self._store.transaction() as connection:
                try:
                    resolution = self._scope_resolver.resolve(
                        request.accounting_scope_ref,
                        request.graph_revision_ref,
                        request.definition_anchor_ref,
                    )
                except AccountingScopeError as error:
                    raise BudgetAuthorityError(
                        "ACCOUNTING_SCOPE_INVALID",
                        accounting_scope_ref=request.accounting_scope_ref,
                    ) from error

                ancestry = resolution.ancestry
                policy_revision_refs: list[str] = []
                deny_reason: str | None = None
                for scope in ancestry:
                    revision_row = self._current_policy_revision(
                        connection, scope.accounting_scope_ref, now
                    )
                    if revision_row is None:
                        continue
                    policy_revision_refs.append(
                        revision_row["budget_policy_revision_ref"]
                    )
                    if deny_reason is not None:
                        continue
                    for rule in json.loads(revision_row["enforcement_rules_json"]):
                        if rule["enforcement"] != "HARD":
                            continue
                        requested_amount = dict(request.reserved_dimensions).get(
                            rule["dimension_ref"], 0
                        )
                        if requested_amount <= 0:
                            continue
                        exposure = self._load_exposure(
                            connection,
                            scope.accounting_scope_ref,
                            rule["dimension_ref"],
                        )
                        projected = (
                            exposure["reserved_amount"]
                            + exposure["committed_amount"]
                            + requested_amount
                        )
                        if projected > rule["limit_amount"]:
                            deny_reason = (
                                "HARD_LIMIT_EXCEEDED"
                                if scope.accounting_scope_ref
                                == request.accounting_scope_ref
                                else "ANCESTOR_LIMIT_EXCEEDED"
                            )
                            break

                ancestry_refs = tuple(
                    scope.accounting_scope_ref for scope in ancestry
                )
                if deny_reason is not None:
                    self._insert_reservation(
                        connection,
                        request=request,
                        reservation_ref=reservation_ref,
                        ancestry_refs=ancestry_refs,
                        policy_revision_refs=tuple(policy_revision_refs),
                        reserved_dimensions=(),
                        state="DENIED",
                        deny_reason_code=deny_reason,
                        now=now,
                    )
                else:
                    for scope in ancestry:
                        for dimension_ref, amount in request.reserved_dimensions:
                            if amount <= 0:
                                continue
                            self._increment_exposure(
                                connection,
                                scope.accounting_scope_ref,
                                dimension_ref,
                                amount,
                            )
                    self._crash_hook("AFTER_EXPOSURE_INCREMENT")
                    self._insert_reservation(
                        connection,
                        request=request,
                        reservation_ref=reservation_ref,
                        ancestry_refs=ancestry_refs,
                        policy_revision_refs=tuple(policy_revision_refs),
                        reserved_dimensions=request.reserved_dimensions,
                        state="RESERVED",
                        deny_reason_code=None,
                        now=now,
                    )
        except sqlite3.IntegrityError as error:
            raise BudgetAuthorityError(
                "RESERVATION_REQUEST_CONFLICT", request_ref=request.request_ref
            ) from error

        result = self._load_reservation_by_ref(reservation_ref)
        assert result is not None
        return result

    def resolve(self, reservation_ref: str) -> BudgetReservation | None:
        return self._load_reservation_by_ref(reservation_ref)

    def resolve_by_request(self, request_ref: str) -> BudgetReservation | None:
        return self._load_reservation_by_request_ref(request_ref)

    def exposure(self, accounting_scope_ref: str, dimension_ref: str) -> tuple[int, int]:
        """Return (reserved_amount, committed_amount) for one (scope, dimension)."""

        row = self._load_exposure(
            self._store.connection, accounting_scope_ref, dimension_ref
        )
        return row["reserved_amount"], row["committed_amount"]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _insert_reservation(
        self,
        connection: sqlite3.Connection,
        *,
        request: BudgetReservationRequest,
        reservation_ref: str,
        ancestry_refs: tuple[str, ...],
        policy_revision_refs: tuple[str, ...],
        reserved_dimensions: tuple[tuple[str, int], ...],
        state: str,
        deny_reason_code: str | None,
        now: int,
    ) -> None:
        connection.execute(
            """
            INSERT INTO budget_reservations(
                reservation_ref, request_ref, activation_ref, run_ref,
                attempt_seq, accounting_scope_ref, graph_revision_ref,
                definition_anchor_ref, ancestry_snapshot_json,
                policy_revision_refs_json, estimate_ref,
                requested_dimensions_json, reserved_dimensions_json,
                committed_dimensions_json, released_dimensions_json,
                state, deny_reason_code,
                subject_refs_json, created_at, updated_at, caused_by_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reservation_ref,
                request.request_ref,
                request.activation_ref,
                request.run_ref,
                request.attempt_seq,
                request.accounting_scope_ref,
                request.graph_revision_ref,
                request.definition_anchor_ref,
                self._encode_str_tuple(ancestry_refs),
                self._encode_str_tuple(policy_revision_refs),
                request.estimate_ref,
                self._encode_dimension_amounts(request.reserved_dimensions),
                self._encode_dimension_amounts(reserved_dimensions),
                self._encode_dimension_amounts(()),
                self._encode_dimension_amounts(()),
                state,
                deny_reason_code,
                self._encode_str_tuple(request.subject_refs),
                now,
                now,
                request.caused_by_ref,
            ),
        )

    def _increment_exposure(
        self,
        connection: sqlite3.Connection,
        accounting_scope_ref: str,
        dimension_ref: str,
        amount: int,
    ) -> None:
        connection.execute(
            """
            INSERT INTO budget_scope_exposure(
                accounting_scope_ref, dimension_ref, reserved_amount, committed_amount
            ) VALUES (?, ?, ?, 0)
            ON CONFLICT(accounting_scope_ref, dimension_ref)
            DO UPDATE SET reserved_amount = reserved_amount + excluded.reserved_amount
            """,
            (accounting_scope_ref, dimension_ref, amount),
        )

    def _load_exposure(
        self,
        connection: sqlite3.Connection,
        accounting_scope_ref: str,
        dimension_ref: str,
    ) -> dict[str, int]:
        row = connection.execute(
            """
            SELECT reserved_amount, committed_amount FROM budget_scope_exposure
            WHERE accounting_scope_ref = ? AND dimension_ref = ?
            """,
            (accounting_scope_ref, dimension_ref),
        ).fetchone()
        if row is None:
            return {"reserved_amount": 0, "committed_amount": 0}
        return {
            "reserved_amount": row["reserved_amount"],
            "committed_amount": row["committed_amount"],
        }

    def _current_policy_revision(
        self, connection: sqlite3.Connection, accounting_scope_ref: str, now: int
    ) -> sqlite3.Row | None:
        return connection.execute(
            """
            SELECT * FROM budget_policy_revisions
            WHERE accounting_scope_ref = ?
              AND effective_from <= ?
              AND (effective_until IS NULL OR effective_until > ?)
            ORDER BY effective_from DESC, budget_policy_revision_ref DESC
            LIMIT 1
            """,
            (accounting_scope_ref, now, now),
        ).fetchone()

    def _load_revision(
        self, budget_policy_revision_ref: str
    ) -> BudgetPolicyRevision | None:
        row = self._store.connection.execute(
            "SELECT * FROM budget_policy_revisions WHERE budget_policy_revision_ref = ?",
            (budget_policy_revision_ref,),
        ).fetchone()
        if row is None:
            return None
        return self._revision_from_row(row)

    def _revision_from_row(self, row: sqlite3.Row) -> BudgetPolicyRevision:
        return BudgetPolicyRevision(
            budget_policy_revision_ref=row["budget_policy_revision_ref"],
            accounting_scope_ref=row["accounting_scope_ref"],
            effective_from=row["effective_from"],
            effective_until=row["effective_until"],
            dimensions=tuple(
                BudgetDimension(**item)
                for item in json.loads(row["dimensions_json"])
            ),
            enforcement_rules=tuple(
                BudgetRule(**item)
                for item in json.loads(row["enforcement_rules_json"])
            ),
            created_by_ref=row["created_by_ref"],
            supersedes_ref=row["supersedes_ref"],
        )

    def _load_reservation_by_ref(
        self, reservation_ref: str
    ) -> BudgetReservation | None:
        row = self._store.connection.execute(
            "SELECT * FROM budget_reservations WHERE reservation_ref = ?",
            (reservation_ref,),
        ).fetchone()
        return self._reservation_from_row(row) if row is not None else None

    def _load_reservation_by_request_ref(
        self, request_ref: str
    ) -> BudgetReservation | None:
        row = self._store.connection.execute(
            "SELECT * FROM budget_reservations WHERE request_ref = ?",
            (request_ref,),
        ).fetchone()
        return self._reservation_from_row(row) if row is not None else None

    @staticmethod
    def _reservation_from_row(row: sqlite3.Row) -> BudgetReservation:
        return BudgetReservation(
            reservation_ref=row["reservation_ref"],
            request_ref=row["request_ref"],
            activation_ref=row["activation_ref"],
            run_ref=row["run_ref"],
            attempt_seq=row["attempt_seq"],
            accounting_scope_ref=row["accounting_scope_ref"],
            ancestry_snapshot=tuple(json.loads(row["ancestry_snapshot_json"])),
            policy_revision_refs=tuple(
                json.loads(row["policy_revision_refs_json"])
            ),
            estimate_ref=row["estimate_ref"],
            requested_dimensions=tuple(
                tuple(item) for item in json.loads(row["requested_dimensions_json"])
            ),
            reserved_dimensions=tuple(
                tuple(item) for item in json.loads(row["reserved_dimensions_json"])
            ),
            committed_dimensions=tuple(
                tuple(item) for item in json.loads(row["committed_dimensions_json"])
            ),
            released_dimensions=tuple(
                tuple(item) for item in json.loads(row["released_dimensions_json"])
            ),
            state=row["state"],
            deny_reason_code=row["deny_reason_code"],
            subject_refs=tuple(json.loads(row["subject_refs_json"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            caused_by_ref=row["caused_by_ref"],
        )

    @staticmethod
    def _require_identical_replay(
        existing: BudgetReservation, request: BudgetReservationRequest
    ) -> None:
        if (
            existing.activation_ref != request.activation_ref
            or existing.run_ref != request.run_ref
            or existing.attempt_seq != request.attempt_seq
            or existing.accounting_scope_ref != request.accounting_scope_ref
            or existing.estimate_ref != request.estimate_ref
            or existing.requested_dimensions != request.reserved_dimensions
            or existing.subject_refs != request.subject_refs
            or existing.caused_by_ref != request.caused_by_ref
        ):
            raise BudgetAuthorityError(
                "RESERVATION_REQUEST_CONFLICT", request_ref=request.request_ref
            )

    @staticmethod
    def _reservation_ref(request_ref: str) -> str:
        digest = hashlib.sha256(request_ref.encode("utf-8")).hexdigest()
        return f"budget-reservation:{digest}"

    def _now(self) -> int:
        value = self._clock()
        if type(value) is not int:
            raise BudgetAuthorityError("BUDGET_CLOCK_INVALID")
        return value

    @staticmethod
    def _encode_str_tuple(values: tuple[str, ...]) -> str:
        return json.dumps(list(values), ensure_ascii=True, separators=(",", ":"))

    @staticmethod
    def _encode_dimension_amounts(pairs: tuple[tuple[str, int], ...]) -> str:
        return json.dumps(
            [list(pair) for pair in pairs],
            ensure_ascii=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _encode_dimensions(dimensions: tuple[BudgetDimension, ...]) -> str:
        return json.dumps(
            [
                {
                    "dimension_ref": dimension.dimension_ref,
                    "unit": dimension.unit,
                    "measurement_semantics_ref": dimension.measurement_semantics_ref,
                }
                for dimension in dimensions
            ],
            ensure_ascii=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _encode_rules(rules: tuple[BudgetRule, ...]) -> str:
        return json.dumps(
            [
                {
                    "rule_ref": rule.rule_ref,
                    "dimension_ref": rule.dimension_ref,
                    "limit_amount": rule.limit_amount,
                    "limit_kind": rule.limit_kind,
                    "enforcement": rule.enforcement,
                }
                for rule in rules
            ],
            ensure_ascii=True,
            separators=(",", ":"),
        )

    @classmethod
    def _validate_revision(cls, revision: BudgetPolicyRevision) -> None:
        if not isinstance(revision, BudgetPolicyRevision):
            raise BudgetAuthorityError("BUDGET_POLICY_REVISION_INVALID")
        identity_values = (
            revision.budget_policy_revision_ref,
            revision.accounting_scope_ref,
            revision.created_by_ref,
        )
        if any(not cls._is_nonempty(value) for value in identity_values):
            raise BudgetAuthorityError("BUDGET_POLICY_REVISION_INVALID")
        if type(revision.effective_from) is not int:
            raise BudgetAuthorityError("BUDGET_POLICY_REVISION_INVALID")
        if revision.effective_until is not None and (
            type(revision.effective_until) is not int
            or revision.effective_until <= revision.effective_from
        ):
            raise BudgetAuthorityError("BUDGET_POLICY_REVISION_INVALID")
        for dimension in revision.dimensions:
            if not isinstance(dimension, BudgetDimension) or any(
                not cls._is_nonempty(value)
                for value in (
                    dimension.dimension_ref,
                    dimension.unit,
                    dimension.measurement_semantics_ref,
                )
            ):
                raise BudgetAuthorityError("BUDGET_POLICY_REVISION_INVALID")
        for rule in revision.enforcement_rules:
            if not isinstance(rule, BudgetRule):
                raise BudgetAuthorityError("BUDGET_POLICY_REVISION_INVALID")
            if not cls._is_nonempty(rule.rule_ref) or not cls._is_nonempty(
                rule.dimension_ref
            ):
                raise BudgetAuthorityError("BUDGET_POLICY_REVISION_INVALID")
            if type(rule.limit_amount) is not int or rule.limit_amount < 0:
                raise BudgetAuthorityError("BUDGET_POLICY_REVISION_INVALID")
            if rule.limit_kind not in _SUPPORTED_LIMIT_KINDS:
                raise BudgetAuthorityError(
                    "BUDGET_RULE_LIMIT_KIND_UNSUPPORTED",
                    limit_kind=rule.limit_kind,
                )
            if rule.enforcement not in _SUPPORTED_ENFORCEMENTS:
                raise BudgetAuthorityError("BUDGET_POLICY_REVISION_INVALID")

    @classmethod
    def _validate_request(cls, request: BudgetReservationRequest) -> None:
        if not isinstance(request, BudgetReservationRequest):
            raise BudgetAuthorityError("RESERVATION_REQUEST_INVALID")
        identity_values = (
            request.request_ref,
            request.activation_ref,
            request.run_ref,
            request.accounting_scope_ref,
            request.graph_revision_ref,
            request.definition_anchor_ref,
            request.estimate_ref,
            request.caused_by_ref,
        )
        if any(not cls._is_nonempty(value) for value in identity_values):
            raise BudgetAuthorityError("RESERVATION_REQUEST_INVALID")
        if type(request.attempt_seq) is not int or request.attempt_seq <= 0:
            raise BudgetAuthorityError("RESERVATION_REQUEST_INVALID")
        if type(request.reserved_dimensions) is not tuple:
            raise BudgetAuthorityError("RESERVATION_REQUEST_INVALID")
        seen_dimensions: set[str] = set()
        for pair in request.reserved_dimensions:
            if (
                type(pair) is not tuple
                or len(pair) != 2
                or not cls._is_nonempty(pair[0])
                or type(pair[1]) is not int
                or pair[1] < 0
            ):
                raise BudgetAuthorityError("RESERVATION_REQUEST_INVALID")
            if pair[0] in seen_dimensions:
                raise BudgetAuthorityError("RESERVATION_REQUEST_INVALID")
            seen_dimensions.add(pair[0])
        if type(request.subject_refs) is not tuple or any(
            not cls._is_nonempty(value) for value in request.subject_refs
        ):
            raise BudgetAuthorityError("RESERVATION_REQUEST_INVALID")

    @staticmethod
    def _is_nonempty(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())
