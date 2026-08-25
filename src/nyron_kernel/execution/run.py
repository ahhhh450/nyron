"""Atomic Run and initial RunAttempt current-authority creation."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from hashlib import sha256

from nyron_kernel.store import SQLiteStore

from .attempt import RunAttempt


class RunError(RuntimeError):
    """Fail-closed Run authority error with a stable reason code."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class Run:
    run_ref: str
    activation_ref: str
    execution_ref: str
    current_attempt_seq: int
    fencing_generation: int
    state: str


class RunRepository:
    """Create and read the one initial current Attempt for an Activation."""

    _INITIAL_ATTEMPT_SEQ = 1
    _INITIAL_FENCING_GENERATION = 1
    _INITIAL_RUN_STATE = "OPEN"
    _INITIAL_ATTEMPT_STATE = "CREATED"

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store
        self._store.create_run_attempt_schema()

    def create_initial(
        self,
        *,
        run_ref: str,
        activation_ref: str,
        execution_ref: str,
    ) -> tuple[Run, RunAttempt]:
        if any(
            not isinstance(value, str) or not value
            for value in (run_ref, activation_ref, execution_ref)
        ):
            raise RunError("RUN_INVALID")

        try:
            with self._store.transaction() as connection:
                existing = self._resolve_run_with(connection, run_ref)
                if existing is not None:
                    if (
                        existing.activation_ref != activation_ref
                        or existing.execution_ref != execution_ref
                    ):
                        raise RunError(
                            "RUN_IDENTITY_CONFLICT", run_ref=run_ref
                        )
                    return self._require_initial_authority(connection, existing)

                activation = connection.execute(
                    """
                    SELECT execution_ref FROM activations
                    WHERE activation_ref = ?
                    """,
                    (activation_ref,),
                ).fetchone()
                if activation is None:
                    raise RunError(
                        "UNRESOLVED_ACTIVATION_REFERENCE",
                        activation_ref=activation_ref,
                    )
                if activation["execution_ref"] != execution_ref:
                    raise RunError(
                        "RUN_ACTIVATION_EXECUTION_MISMATCH",
                        activation_ref=activation_ref,
                        execution_ref=execution_ref,
                    )

                execution = connection.execute(
                    """
                    SELECT state FROM workflow_executions
                    WHERE execution_ref = ?
                    """,
                    (execution_ref,),
                ).fetchone()
                if execution is None or execution["state"] != "ADMITTED":
                    raise RunError(
                        "WORKFLOW_EXECUTION_NOT_ADMITTED",
                        execution_ref=execution_ref,
                    )

                owner = connection.execute(
                    """
                    SELECT run_ref FROM runs WHERE activation_ref = ?
                    """,
                    (activation_ref,),
                ).fetchone()
                if owner is not None:
                    raise RunError(
                        "ACTIVATION_RUN_CONFLICT",
                        activation_ref=activation_ref,
                        existing_run_ref=owner["run_ref"],
                    )

                fencing_token = self._initial_fencing_token(
                    execution_ref, activation_ref, run_ref
                )
                connection.execute(
                    """
                    INSERT INTO runs(
                        run_ref, activation_ref, execution_ref,
                        current_attempt_seq, fencing_generation, state
                    ) VALUES (?, ?, ?, 1, 1, 'OPEN')
                    """,
                    (run_ref, activation_ref, execution_ref),
                )
                connection.execute(
                    """
                    INSERT INTO run_attempts(
                        run_ref, attempt_seq, fencing_token, state
                    ) VALUES (?, 1, ?, 'CREATED')
                    """,
                    (run_ref, fencing_token),
                )
        except sqlite3.IntegrityError as error:
            raise RunError("RUN_CREATION_CONFLICT", run_ref=run_ref) from error

        authority = self.resolve(run_ref)
        if authority is None:  # pragma: no cover - guards store corruption
            raise RunError("RUN_CREATION_FAILED", run_ref=run_ref)
        return authority

    def resolve(self, run_ref: str) -> tuple[Run, RunAttempt] | None:
        run = self._resolve_run_with(self._store.connection, run_ref)
        if run is None:
            return None
        return self._require_initial_authority(self._store.connection, run)

    def _require_initial_authority(
        self, connection: sqlite3.Connection, run: Run
    ) -> tuple[Run, RunAttempt]:
        attempt = self._resolve_attempt_with(
            connection, run.run_ref, run.current_attempt_seq
        )
        expected_token = self._initial_fencing_token(
            run.execution_ref, run.activation_ref, run.run_ref
        )
        if (
            run.current_attempt_seq != self._INITIAL_ATTEMPT_SEQ
            or run.fencing_generation != self._INITIAL_FENCING_GENERATION
            or run.state != self._INITIAL_RUN_STATE
            or attempt is None
            or attempt.state != self._INITIAL_ATTEMPT_STATE
            or attempt.fencing_token != expected_token
        ):
            raise RunError(
                "RUN_CURRENT_AUTHORITY_INCONSISTENT", run_ref=run.run_ref
            )
        return run, attempt

    @staticmethod
    def _resolve_run_with(
        connection: sqlite3.Connection, run_ref: str
    ) -> Run | None:
        row = connection.execute(
            """
            SELECT run_ref, activation_ref, execution_ref,
                   current_attempt_seq, fencing_generation, state
            FROM runs WHERE run_ref = ?
            """,
            (run_ref,),
        ).fetchone()
        return Run(**dict(row)) if row is not None else None

    @staticmethod
    def _resolve_attempt_with(
        connection: sqlite3.Connection, run_ref: str, attempt_seq: int
    ) -> RunAttempt | None:
        row = connection.execute(
            """
            SELECT run_ref, attempt_seq, fencing_token, state
            FROM run_attempts WHERE run_ref = ? AND attempt_seq = ?
            """,
            (run_ref, attempt_seq),
        ).fetchone()
        return RunAttempt(**dict(row)) if row is not None else None

    @classmethod
    def _initial_fencing_token(
        cls, execution_ref: str, activation_ref: str, run_ref: str
    ) -> str:
        canonical_authority = json.dumps(
            (
                execution_ref,
                activation_ref,
                run_ref,
                cls._INITIAL_ATTEMPT_SEQ,
                cls._INITIAL_FENCING_GENERATION,
            ),
            separators=(",", ":"),
        ).encode("utf-8")
        return f"fencing:sha256:{sha256(canonical_authority).hexdigest()}"
