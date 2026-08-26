"""Accounting Owner: UsageFact / UsageAdjustmentFact ledger foundation
(ARE-GATE-6 Track A / Task 090).

This slice implements only the immutable actual-usage ledger: durable
UsageFact commit keyed by stable source-dedupe identity
``(source_authority_ref, source_fact_id, fact_kind, dimension_ref)``, and
append-only UsageAdjustmentFact correction records that reference the
UsageFact they adjust. It deliberately does NOT implement BudgetReservation
COMMITTED/RELEASED/RECONCILING settlement transitions, reserved-to-committed
exposure conversion, or any Recovery Owner ReconciliationCase state -- those
remain later Gate-6 slices. A dedupe-identity collision with a conflicting
payload fails closed with a machine-readable reconciliation-required error;
it never opens a Recovery Owner ReconciliationCase directly and never
overwrites or chooses the latest callback by arrival time.
"""

from __future__ import annotations

import json
import hashlib
import sqlite3
from dataclasses import dataclass
from typing import Callable

from nyron_kernel.store import SQLiteStore


class UsageLedgerError(RuntimeError):
    """Fail-closed Accounting-owned error with a stable reason code."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class UsageFactRequest:
    """Caller-supplied usage evidence. Not itself canonical truth until committed."""

    source_authority_ref: str
    source_fact_id: str
    fact_kind: str
    dimension_ref: str
    accounting_scope_ref: str
    quantity: int
    unit: str
    external_evidence_ref: str
    caused_by_ref: str
    reservation_ref: str | None = None
    operation_ref: str | None = None
    resource_ref: str | None = None
    run_ref: str | None = None
    usage_period: str | None = None
    observed_at: int | None = None


@dataclass(frozen=True)
class UsageFact:
    usage_fact_ref: str
    accounting_scope_ref: str
    reservation_ref: str | None
    operation_ref: str | None
    resource_ref: str | None
    run_ref: str | None
    source_authority_ref: str
    source_fact_id: str
    dimension_ref: str
    quantity: int
    unit: str
    fact_kind: str
    usage_period: str | None
    external_evidence_ref: str
    observed_at: int | None
    ingested_at: int
    caused_by_ref: str


@dataclass(frozen=True)
class UsageAdjustmentFactRequest:
    """Caller-supplied correction evidence for an already-committed UsageFact."""

    adjusts_usage_fact_ref: str
    source_authority_ref: str
    source_fact_id: str
    fact_kind: str
    dimension_ref: str
    delta_quantity: int
    unit: str
    reason: str
    evidence_ref: str
    caused_by_ref: str


@dataclass(frozen=True)
class UsageAdjustmentFact:
    adjustment_fact_ref: str
    adjusts_usage_fact_ref: str
    source_authority_ref: str
    source_fact_id: str
    fact_kind: str
    dimension_ref: str
    delta_quantity: int
    unit: str
    reason: str
    evidence_ref: str
    ingested_at: int
    caused_by_ref: str


class UsageLedger:
    """Sole canonical writer for UsageFact and UsageAdjustmentFact."""

    def __init__(self, store: SQLiteStore, clock: Callable[[], int]) -> None:
        self._store = store
        self._clock = clock
        self._store.create_usage_ledger_schema()

    # ------------------------------------------------------------------
    # UsageFact
    # ------------------------------------------------------------------

    def record_usage(self, request: UsageFactRequest) -> UsageFact:
        """Commit one immutable UsageFact, deduplicating by stable source identity.

        Exact duplicate source identity + exact semantic payload is
        idempotent and returns the existing canonical fact. Same source
        identity with a conflicting payload fails closed: the existing fact
        is preserved untouched and a ``USAGE_FACT_RECONCILIATION_REQUIRED``
        error is raised instead of overwriting or choosing the latest
        callback by arrival time.
        """

        self._validate_usage_request(request)
        usage_fact_ref = self._usage_fact_ref(request)

        existing = self._load_usage_fact_by_ref(usage_fact_ref)
        if existing is not None:
            self._require_identical_usage_payload(existing, request)
            return existing

        now = self._now()
        try:
            with self._store.transaction() as connection:
                if (
                    connection.execute(
                        "SELECT 1 FROM accounting_scopes WHERE accounting_scope_ref = ?",
                        (request.accounting_scope_ref,),
                    ).fetchone()
                    is None
                ):
                    raise UsageLedgerError(
                        "USAGE_FACT_ACCOUNTING_SCOPE_UNRESOLVED",
                        accounting_scope_ref=request.accounting_scope_ref,
                    )
                connection.execute(
                    """
                    INSERT INTO usage_facts(
                        usage_fact_ref, accounting_scope_ref, reservation_ref,
                        operation_ref, resource_ref, run_ref,
                        source_authority_ref, source_fact_id, dimension_ref,
                        quantity, unit, fact_kind, usage_period,
                        external_evidence_ref, observed_at, ingested_at,
                        caused_by_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        usage_fact_ref,
                        request.accounting_scope_ref,
                        request.reservation_ref,
                        request.operation_ref,
                        request.resource_ref,
                        request.run_ref,
                        request.source_authority_ref,
                        request.source_fact_id,
                        request.dimension_ref,
                        request.quantity,
                        request.unit,
                        request.fact_kind,
                        request.usage_period,
                        request.external_evidence_ref,
                        request.observed_at,
                        now,
                        request.caused_by_ref,
                    ),
                )
        except sqlite3.IntegrityError as error:
            # A concurrent committer may have won the same dedupe identity
            # race between our pre-check and this transaction; re-resolve
            # rather than assume the raw constraint failure is a conflict.
            existing = self._load_usage_fact_by_ref(usage_fact_ref)
            if existing is None:
                raise UsageLedgerError(
                    "USAGE_FACT_IDENTITY_CONFLICT", usage_fact_ref=usage_fact_ref
                ) from error
            self._require_identical_usage_payload(existing, request)
            return existing

        result = self._load_usage_fact_by_ref(usage_fact_ref)
        assert result is not None
        return result

    def resolve(self, usage_fact_ref: str) -> UsageFact | None:
        return self._load_usage_fact_by_ref(usage_fact_ref)

    # ------------------------------------------------------------------
    # UsageAdjustmentFact
    # ------------------------------------------------------------------

    def record_adjustment(
        self, request: UsageAdjustmentFactRequest
    ) -> UsageAdjustmentFact:
        """Append one immutable UsageAdjustmentFact referencing an existing
        UsageFact, deduplicating by stable source identity.

        Never rewrites the original UsageFact or an existing adjustment.
        Same source identity with a conflicting payload fails closed with
        ``USAGE_ADJUSTMENT_RECONCILIATION_REQUIRED``.
        """

        self._validate_adjustment_request(request)

        original = self._load_usage_fact_by_ref(request.adjusts_usage_fact_ref)
        if original is None:
            raise UsageLedgerError(
                "USAGE_ADJUSTMENT_TARGET_UNRESOLVED",
                adjusts_usage_fact_ref=request.adjusts_usage_fact_ref,
            )

        adjustment_fact_ref = self._adjustment_fact_ref(request)
        existing = self._load_adjustment_by_ref(adjustment_fact_ref)
        if existing is not None:
            self._require_identical_adjustment_payload(existing, request)
            return existing

        now = self._now()
        try:
            with self._store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO usage_adjustment_facts(
                        adjustment_fact_ref, adjusts_usage_fact_ref,
                        source_authority_ref, source_fact_id, fact_kind,
                        dimension_ref, delta_quantity, unit, reason,
                        evidence_ref, ingested_at, caused_by_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        adjustment_fact_ref,
                        request.adjusts_usage_fact_ref,
                        request.source_authority_ref,
                        request.source_fact_id,
                        request.fact_kind,
                        request.dimension_ref,
                        request.delta_quantity,
                        request.unit,
                        request.reason,
                        request.evidence_ref,
                        now,
                        request.caused_by_ref,
                    ),
                )
        except sqlite3.IntegrityError as error:
            existing = self._load_adjustment_by_ref(adjustment_fact_ref)
            if existing is None:
                raise UsageLedgerError(
                    "USAGE_ADJUSTMENT_IDENTITY_CONFLICT",
                    adjustment_fact_ref=adjustment_fact_ref,
                ) from error
            self._require_identical_adjustment_payload(existing, request)
            return existing

        result = self._load_adjustment_by_ref(adjustment_fact_ref)
        assert result is not None
        return result

    def resolve_adjustment(
        self, adjustment_fact_ref: str
    ) -> UsageAdjustmentFact | None:
        return self._load_adjustment_by_ref(adjustment_fact_ref)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_usage_fact_by_ref(self, usage_fact_ref: str) -> UsageFact | None:
        row = self._store.connection.execute(
            "SELECT * FROM usage_facts WHERE usage_fact_ref = ?",
            (usage_fact_ref,),
        ).fetchone()
        return self._usage_fact_from_row(row) if row is not None else None

    @staticmethod
    def _usage_fact_from_row(row: sqlite3.Row) -> UsageFact:
        return UsageFact(
            usage_fact_ref=row["usage_fact_ref"],
            accounting_scope_ref=row["accounting_scope_ref"],
            reservation_ref=row["reservation_ref"],
            operation_ref=row["operation_ref"],
            resource_ref=row["resource_ref"],
            run_ref=row["run_ref"],
            source_authority_ref=row["source_authority_ref"],
            source_fact_id=row["source_fact_id"],
            dimension_ref=row["dimension_ref"],
            quantity=row["quantity"],
            unit=row["unit"],
            fact_kind=row["fact_kind"],
            usage_period=row["usage_period"],
            external_evidence_ref=row["external_evidence_ref"],
            observed_at=row["observed_at"],
            ingested_at=row["ingested_at"],
            caused_by_ref=row["caused_by_ref"],
        )

    def _load_adjustment_by_ref(
        self, adjustment_fact_ref: str
    ) -> UsageAdjustmentFact | None:
        row = self._store.connection.execute(
            "SELECT * FROM usage_adjustment_facts WHERE adjustment_fact_ref = ?",
            (adjustment_fact_ref,),
        ).fetchone()
        return self._adjustment_from_row(row) if row is not None else None

    @staticmethod
    def _adjustment_from_row(row: sqlite3.Row) -> UsageAdjustmentFact:
        return UsageAdjustmentFact(
            adjustment_fact_ref=row["adjustment_fact_ref"],
            adjusts_usage_fact_ref=row["adjusts_usage_fact_ref"],
            source_authority_ref=row["source_authority_ref"],
            source_fact_id=row["source_fact_id"],
            fact_kind=row["fact_kind"],
            dimension_ref=row["dimension_ref"],
            delta_quantity=row["delta_quantity"],
            unit=row["unit"],
            reason=row["reason"],
            evidence_ref=row["evidence_ref"],
            ingested_at=row["ingested_at"],
            caused_by_ref=row["caused_by_ref"],
        )

    @staticmethod
    def _require_identical_usage_payload(
        existing: UsageFact, request: UsageFactRequest
    ) -> None:
        if (
            existing.accounting_scope_ref != request.accounting_scope_ref
            or existing.reservation_ref != request.reservation_ref
            or existing.operation_ref != request.operation_ref
            or existing.resource_ref != request.resource_ref
            or existing.run_ref != request.run_ref
            or existing.quantity != request.quantity
            or existing.unit != request.unit
            or existing.usage_period != request.usage_period
            or existing.external_evidence_ref != request.external_evidence_ref
            or existing.observed_at != request.observed_at
            or existing.caused_by_ref != request.caused_by_ref
        ):
            raise UsageLedgerError(
                "USAGE_FACT_RECONCILIATION_REQUIRED",
                usage_fact_ref=existing.usage_fact_ref,
                source_authority_ref=request.source_authority_ref,
                source_fact_id=request.source_fact_id,
                fact_kind=request.fact_kind,
                dimension_ref=request.dimension_ref,
            )

    @staticmethod
    def _require_identical_adjustment_payload(
        existing: UsageAdjustmentFact, request: UsageAdjustmentFactRequest
    ) -> None:
        if (
            existing.adjusts_usage_fact_ref != request.adjusts_usage_fact_ref
            or existing.delta_quantity != request.delta_quantity
            or existing.unit != request.unit
            or existing.reason != request.reason
            or existing.evidence_ref != request.evidence_ref
            or existing.caused_by_ref != request.caused_by_ref
        ):
            raise UsageLedgerError(
                "USAGE_ADJUSTMENT_RECONCILIATION_REQUIRED",
                adjustment_fact_ref=existing.adjustment_fact_ref,
                source_authority_ref=request.source_authority_ref,
                source_fact_id=request.source_fact_id,
                fact_kind=request.fact_kind,
                dimension_ref=request.dimension_ref,
            )

    @staticmethod
    def _usage_fact_ref(request: UsageFactRequest) -> str:
        digest = hashlib.sha256(
            json.dumps(
                [
                    request.source_authority_ref,
                    request.source_fact_id,
                    request.fact_kind,
                    request.dimension_ref,
                ],
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return f"usage-fact:{digest}"

    @staticmethod
    def _adjustment_fact_ref(request: UsageAdjustmentFactRequest) -> str:
        digest = hashlib.sha256(
            json.dumps(
                [
                    request.source_authority_ref,
                    request.source_fact_id,
                    request.fact_kind,
                    request.dimension_ref,
                ],
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return f"usage-adjustment:{digest}"

    def _now(self) -> int:
        value = self._clock()
        if type(value) is not int:
            raise UsageLedgerError("USAGE_LEDGER_CLOCK_INVALID")
        return value

    @classmethod
    def _validate_usage_request(cls, request: UsageFactRequest) -> None:
        if not isinstance(request, UsageFactRequest):
            raise UsageLedgerError("USAGE_FACT_REQUEST_INVALID")
        identity_values = (
            request.source_authority_ref,
            request.source_fact_id,
            request.fact_kind,
            request.dimension_ref,
            request.accounting_scope_ref,
            request.unit,
            request.external_evidence_ref,
            request.caused_by_ref,
        )
        if any(not cls._is_nonempty(value) for value in identity_values):
            raise UsageLedgerError("USAGE_FACT_REQUEST_INVALID")
        if type(request.quantity) is not int or request.quantity < 0:
            raise UsageLedgerError("USAGE_FACT_REQUEST_INVALID")
        for optional in (
            request.reservation_ref,
            request.operation_ref,
            request.resource_ref,
            request.run_ref,
            request.usage_period,
        ):
            if optional is not None and not cls._is_nonempty(optional):
                raise UsageLedgerError("USAGE_FACT_REQUEST_INVALID")
        if request.observed_at is not None and type(request.observed_at) is not int:
            raise UsageLedgerError("USAGE_FACT_REQUEST_INVALID")

    @classmethod
    def _validate_adjustment_request(
        cls, request: UsageAdjustmentFactRequest
    ) -> None:
        if not isinstance(request, UsageAdjustmentFactRequest):
            raise UsageLedgerError("USAGE_ADJUSTMENT_REQUEST_INVALID")
        identity_values = (
            request.adjusts_usage_fact_ref,
            request.source_authority_ref,
            request.source_fact_id,
            request.fact_kind,
            request.dimension_ref,
            request.unit,
            request.reason,
            request.evidence_ref,
            request.caused_by_ref,
        )
        if any(not cls._is_nonempty(value) for value in identity_values):
            raise UsageLedgerError("USAGE_ADJUSTMENT_REQUEST_INVALID")
        if type(request.delta_quantity) is not int or request.delta_quantity == 0:
            raise UsageLedgerError("USAGE_ADJUSTMENT_REQUEST_INVALID")

    @staticmethod
    def _is_nonempty(value: object) -> bool:
        return isinstance(value, str) and value != ""
