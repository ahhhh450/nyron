"""Accounting-owned known-actual BudgetReservation settlement foundation."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from typing import Callable

from nyron_kernel.store import SQLiteStore


class SettlementAuthorityError(RuntimeError):
    """Fail-closed settlement error with a stable machine-readable code."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class SettlementRequest:
    request_ref: str
    reservation_ref: str
    caused_by_ref: str


@dataclass(frozen=True)
class BudgetSettlement:
    settlement_ref: str
    request_ref: str
    reservation_ref: str
    fact_set_hash: str
    usage_fact_refs: tuple[str, ...]
    adjustment_fact_refs: tuple[str, ...]
    actual_dimensions: tuple[tuple[str, int], ...]
    released_dimensions: tuple[tuple[str, int], ...]
    overrun_dimensions: tuple[tuple[str, int], ...]
    resulting_state: str
    settled_at: int
    caused_by_ref: str


class SettlementAuthority:
    """Atomically convert reserved exposure to known committed exposure."""

    def __init__(
        self,
        store: SQLiteStore,
        clock: Callable[[], int],
        crash_hook: Callable[[str], None] | None = None,
    ) -> None:
        self._store = store
        self._clock = clock
        self._crash_hook = crash_hook or (lambda _stage: None)
        self._store.create_budget_settlement_schema()

    def settle(self, request: SettlementRequest) -> BudgetSettlement:
        self._validate_request(request)
        facts = self._load_bound_facts(request.reservation_ref)
        fact_set_hash = self._fact_set_hash(facts[0], facts[1])

        existing = self._load_by_request_ref(request.request_ref)
        if existing is not None:
            self._require_identical_replay(existing, request, fact_set_hash)
            return existing

        now = self._now()
        settlement_ref = self._settlement_ref(request.request_ref)
        try:
            with self._store.transaction() as connection:
                reservation = connection.execute(
                    "SELECT * FROM budget_reservations WHERE reservation_ref = ?",
                    (request.reservation_ref,),
                ).fetchone()
                if reservation is None:
                    raise SettlementAuthorityError(
                        "SETTLEMENT_RESERVATION_UNRESOLVED",
                        reservation_ref=request.reservation_ref,
                    )
                if reservation["state"] != "RESERVED":
                    raise SettlementAuthorityError(
                        "SETTLEMENT_RESERVATION_NOT_RESERVED",
                        reservation_ref=request.reservation_ref,
                        state=reservation["state"],
                    )

                usage_rows, adjustment_rows = self._load_bound_facts(
                    request.reservation_ref, connection
                )
                transaction_hash = self._fact_set_hash(usage_rows, adjustment_rows)
                if transaction_hash != fact_set_hash:
                    raise SettlementAuthorityError(
                        "SETTLEMENT_FACT_SET_CHANGED",
                        reservation_ref=request.reservation_ref,
                    )

                if not usage_rows:
                    raise SettlementAuthorityError(
                        "SETTLEMENT_EVIDENCE_REQUIRED",
                        reservation_ref=request.reservation_ref,
                    )

                actual = self._actual_dimensions(
                    reservation,
                    usage_rows,
                    adjustment_rows,
                    self._canonical_dimensions(connection, reservation),
                )
                reserved = dict(json.loads(reservation["reserved_dimensions_json"]))
                dimensions = sorted(set(reserved) | set(actual))
                released = {
                    dimension: max(reserved.get(dimension, 0) - actual.get(dimension, 0), 0)
                    for dimension in dimensions
                }
                overrun = {
                    dimension: max(actual.get(dimension, 0) - reserved.get(dimension, 0), 0)
                    for dimension in dimensions
                }
                released = {key: value for key, value in released.items() if value}
                overrun = {key: value for key, value in overrun.items() if value}
                actual = {key: value for key, value in actual.items() if value}

                ancestry = tuple(json.loads(reservation["ancestry_snapshot_json"]))
                for scope_ref in ancestry:
                    for dimension in dimensions:
                        reserved_amount = reserved.get(dimension, 0)
                        actual_amount = actual.get(dimension, 0)
                        exposure = connection.execute(
                            """
                            SELECT reserved_amount, committed_amount
                            FROM budget_scope_exposure
                            WHERE accounting_scope_ref = ? AND dimension_ref = ?
                            """,
                            (scope_ref, dimension),
                        ).fetchone()
                        if reserved_amount and (
                            exposure is None
                            or exposure["reserved_amount"] < reserved_amount
                        ):
                            raise SettlementAuthorityError(
                                "SETTLEMENT_EXPOSURE_INVARIANT_VIOLATION",
                                accounting_scope_ref=scope_ref,
                                dimension_ref=dimension,
                            )
                        if exposure is None:
                            connection.execute(
                                """
                                INSERT INTO budget_scope_exposure(
                                    accounting_scope_ref, dimension_ref,
                                    reserved_amount, committed_amount
                                ) VALUES (?, ?, 0, ?)
                                """,
                                (scope_ref, dimension, actual_amount),
                            )
                        else:
                            connection.execute(
                                """
                                UPDATE budget_scope_exposure
                                SET reserved_amount = reserved_amount - ?,
                                    committed_amount = committed_amount + ?
                                WHERE accounting_scope_ref = ? AND dimension_ref = ?
                                """,
                                (reserved_amount, actual_amount, scope_ref, dimension),
                            )

                self._crash_hook("AFTER_EXPOSURE_CONVERSION")
                resulting_state = "COMMITTED" if actual else "RELEASED"
                connection.execute(
                    """
                    UPDATE budget_reservations
                    SET committed_dimensions_json = ?, released_dimensions_json = ?,
                        state = ?, updated_at = ?
                    WHERE reservation_ref = ?
                    """,
                    (
                        self._encode_dimensions(actual),
                        self._encode_dimensions(released),
                        resulting_state,
                        now,
                        request.reservation_ref,
                    ),
                )
                self._crash_hook("AFTER_RESERVATION_UPDATE")
                connection.execute(
                    """
                    INSERT INTO budget_settlements(
                        settlement_ref, request_ref, reservation_ref, fact_set_hash,
                        usage_fact_refs_json, adjustment_fact_refs_json,
                        actual_dimensions_json, released_dimensions_json,
                        overrun_dimensions_json, resulting_state, settled_at,
                        caused_by_ref
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        settlement_ref,
                        request.request_ref,
                        request.reservation_ref,
                        transaction_hash,
                        json.dumps([row["usage_fact_ref"] for row in usage_rows]),
                        json.dumps(
                            [row["adjustment_fact_ref"] for row in adjustment_rows]
                        ),
                        self._encode_dimensions(actual),
                        self._encode_dimensions(released),
                        self._encode_dimensions(overrun),
                        resulting_state,
                        now,
                        request.caused_by_ref,
                    ),
                )
        except sqlite3.IntegrityError as error:
            existing = self._load_by_request_ref(request.request_ref)
            if existing is not None:
                self._require_identical_replay(existing, request, fact_set_hash)
                return existing
            raise SettlementAuthorityError(
                "SETTLEMENT_IDENTITY_CONFLICT", request_ref=request.request_ref
            ) from error

        result = self._load_by_request_ref(request.request_ref)
        assert result is not None
        return result

    def resolve(self, settlement_ref: str) -> BudgetSettlement | None:
        row = self._store.connection.execute(
            "SELECT * FROM budget_settlements WHERE settlement_ref = ?",
            (settlement_ref,),
        ).fetchone()
        return self._from_row(row) if row is not None else None

    def _load_bound_facts(
        self,
        reservation_ref: str,
        connection: sqlite3.Connection | None = None,
    ) -> tuple[tuple[sqlite3.Row, ...], tuple[sqlite3.Row, ...]]:
        connection = connection or self._store.connection
        usage_rows = tuple(
            connection.execute(
                "SELECT * FROM usage_facts WHERE reservation_ref = ? "
                "ORDER BY usage_fact_ref",
                (reservation_ref,),
            ).fetchall()
        )
        adjustment_rows = tuple(
            connection.execute(
                """
                SELECT adjustment.*
                FROM usage_adjustment_facts AS adjustment
                JOIN usage_facts AS usage
                  ON usage.usage_fact_ref = adjustment.adjusts_usage_fact_ref
                WHERE usage.reservation_ref = ?
                ORDER BY adjustment.adjustment_fact_ref
                """,
                (reservation_ref,),
            ).fetchall()
        )
        return usage_rows, adjustment_rows

    @staticmethod
    def _canonical_dimensions(
        connection: sqlite3.Connection,
        reservation: sqlite3.Row,
    ) -> dict[str, tuple[str, str]]:
        canonical: dict[str, tuple[str, str]] = {}
        for revision_ref in json.loads(reservation["policy_revision_refs_json"]):
            revision = connection.execute(
                "SELECT dimensions_json FROM budget_policy_revisions "
                "WHERE budget_policy_revision_ref = ?",
                (revision_ref,),
            ).fetchone()
            if revision is None:
                raise SettlementAuthorityError(
                    "SETTLEMENT_DIMENSION_UNRESOLVED",
                    dimension_ref=None,
                    budget_policy_revision_ref=revision_ref,
                )
            for dimension in json.loads(revision["dimensions_json"]):
                dimension_ref = dimension["dimension_ref"]
                binding = (
                    dimension["unit"],
                    dimension["measurement_semantics_ref"],
                )
                existing = canonical.get(dimension_ref)
                if existing is not None and existing != binding:
                    raise SettlementAuthorityError(
                        "SETTLEMENT_DIMENSION_BINDING_CONFLICT",
                        dimension_ref=dimension_ref,
                    )
                canonical[dimension_ref] = binding
        return canonical

    @staticmethod
    def _actual_dimensions(
        reservation: sqlite3.Row,
        usage_rows: tuple[sqlite3.Row, ...],
        adjustment_rows: tuple[sqlite3.Row, ...],
        canonical_dimensions: dict[str, tuple[str, str]],
    ) -> dict[str, int]:
        actual: dict[str, int] = {}
        usage_by_ref = {row["usage_fact_ref"]: row for row in usage_rows}
        for row in usage_rows:
            if row["accounting_scope_ref"] != reservation["accounting_scope_ref"]:
                raise SettlementAuthorityError("SETTLEMENT_FACT_BINDING_CONFLICT")
            binding = canonical_dimensions.get(row["dimension_ref"])
            if binding is None:
                raise SettlementAuthorityError(
                    "SETTLEMENT_DIMENSION_UNRESOLVED",
                    dimension_ref=row["dimension_ref"],
                )
            if row["unit"] != binding[0]:
                raise SettlementAuthorityError(
                    "SETTLEMENT_FACT_BINDING_CONFLICT",
                    dimension_ref=row["dimension_ref"],
                )
            actual[row["dimension_ref"]] = (
                actual.get(row["dimension_ref"], 0) + row["quantity"]
            )
        for row in adjustment_rows:
            target = usage_by_ref[row["adjusts_usage_fact_ref"]]
            if (
                row["dimension_ref"] != target["dimension_ref"]
                or row["unit"] != target["unit"]
            ):
                raise SettlementAuthorityError("SETTLEMENT_FACT_BINDING_CONFLICT")
            actual[row["dimension_ref"]] = (
                actual.get(row["dimension_ref"], 0) + row["delta_quantity"]
            )
        if any(amount < 0 for amount in actual.values()):
            raise SettlementAuthorityError("SETTLEMENT_ACTUAL_INVALID")
        return actual

    @staticmethod
    def _fact_set_hash(
        usage_rows: tuple[sqlite3.Row, ...],
        adjustment_rows: tuple[sqlite3.Row, ...],
    ) -> str:
        encoded = json.dumps(
            [["usage", row["usage_fact_ref"]] for row in usage_rows]
            + [
                ["adjustment", row["adjustment_fact_ref"]]
                for row in adjustment_rows
            ],
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _load_by_request_ref(self, request_ref: str) -> BudgetSettlement | None:
        row = self._store.connection.execute(
            "SELECT * FROM budget_settlements WHERE request_ref = ?", (request_ref,)
        ).fetchone()
        return self._from_row(row) if row is not None else None

    @staticmethod
    def _require_identical_replay(
        existing: BudgetSettlement,
        request: SettlementRequest,
        fact_set_hash: str,
    ) -> None:
        if (
            existing.reservation_ref != request.reservation_ref
            or existing.caused_by_ref != request.caused_by_ref
            or existing.fact_set_hash != fact_set_hash
        ):
            raise SettlementAuthorityError(
                "SETTLEMENT_REQUEST_CONFLICT", request_ref=request.request_ref
            )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> BudgetSettlement:
        return BudgetSettlement(
            settlement_ref=row["settlement_ref"],
            request_ref=row["request_ref"],
            reservation_ref=row["reservation_ref"],
            fact_set_hash=row["fact_set_hash"],
            usage_fact_refs=tuple(json.loads(row["usage_fact_refs_json"])),
            adjustment_fact_refs=tuple(json.loads(row["adjustment_fact_refs_json"])),
            actual_dimensions=tuple(
                tuple(item) for item in json.loads(row["actual_dimensions_json"])
            ),
            released_dimensions=tuple(
                tuple(item) for item in json.loads(row["released_dimensions_json"])
            ),
            overrun_dimensions=tuple(
                tuple(item) for item in json.loads(row["overrun_dimensions_json"])
            ),
            resulting_state=row["resulting_state"],
            settled_at=row["settled_at"],
            caused_by_ref=row["caused_by_ref"],
        )

    @staticmethod
    def _settlement_ref(request_ref: str) -> str:
        digest = hashlib.sha256(request_ref.encode("utf-8")).hexdigest()
        return f"budget-settlement:{digest}"

    @staticmethod
    def _encode_dimensions(dimensions: dict[str, int]) -> str:
        return json.dumps(sorted(dimensions.items()), separators=(",", ":"))

    def _now(self) -> int:
        value = self._clock()
        if type(value) is not int:
            raise SettlementAuthorityError("SETTLEMENT_CLOCK_INVALID")
        return value

    @staticmethod
    def _validate_request(request: SettlementRequest) -> None:
        if not isinstance(request, SettlementRequest) or any(
            not isinstance(value, str) or value == ""
            for value in (
                request.request_ref,
                request.reservation_ref,
                request.caused_by_ref,
            )
        ):
            raise SettlementAuthorityError("SETTLEMENT_REQUEST_INVALID")
