"""Minimal immutable JSON value persistence for the Phase-2 Runtime slice."""

from __future__ import annotations

import json
from typing import Any

from nyron_kernel.store import SQLiteStore


class DurableValueError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


class DurableValueRepository:
    """Persist immutable JSON values; SQLite is only the current implementation."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._store.create_attempt_execution_schema()

    def put(self, value_ref: str, value: Any) -> str:
        if not isinstance(value_ref, str) or not value_ref:
            raise DurableValueError("DURABLE_VALUE_INVALID")
        try:
            value_json = json.dumps(
                value, sort_keys=True, separators=(",", ":"),
                ensure_ascii=True, allow_nan=False,
            )
        except (TypeError, ValueError) as error:
            raise DurableValueError("DURABLE_VALUE_INVALID") from error

        with self._store.transaction() as connection:
            row = connection.execute(
                "SELECT value_json FROM durable_values WHERE value_ref = ?",
                (value_ref,),
            ).fetchone()
            if row is not None:
                if row["value_json"] != value_json:
                    raise DurableValueError(
                        "DURABLE_VALUE_IDENTITY_CONFLICT", value_ref=value_ref
                    )
                return value_ref
            connection.execute(
                "INSERT INTO durable_values(value_ref, value_json) VALUES (?, ?)",
                (value_ref, value_json),
            )
        return value_ref

    def resolve(self, value_ref: str) -> Any:
        row = self._store.connection.execute(
            "SELECT value_json FROM durable_values WHERE value_ref = ?",
            (value_ref,),
        ).fetchone()
        if row is None:
            raise DurableValueError(
                "UNRESOLVED_DURABLE_VALUE", value_ref=value_ref
            )
        return json.loads(row["value_json"])

    def exists_with(self, connection: object, value_ref: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM durable_values WHERE value_ref = ?", (value_ref,)
        ).fetchone()
        return row is not None
