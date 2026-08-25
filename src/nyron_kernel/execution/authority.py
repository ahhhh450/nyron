"""Runtime-owned read-only query boundary for current Attempt authority."""

from __future__ import annotations

import sqlite3

from nyron_kernel.store import SQLiteStore

from .attempt import AttemptAuthority


class RuntimeAuthorityResolver:
    """Resolve Runtime current-attempt truth without exposing Runtime tables."""

    def __init__(self, store: SQLiteStore) -> None:
        self._store = store

    def resolve_current(self, run_ref: str) -> AttemptAuthority | None:
        return self.resolve_current_with(self._store.connection, run_ref)

    def is_current(self, authority: AttemptAuthority) -> bool:
        return self.is_current_with(self._store.connection, authority)

    @classmethod
    def resolve_current_with(
        cls, connection: sqlite3.Connection, run_ref: str
    ) -> AttemptAuthority | None:
        if not isinstance(run_ref, str) or not run_ref:
            return None
        row = connection.execute(
            """
            SELECT r.execution_ref, r.activation_ref, r.run_ref,
                   r.current_attempt_seq AS attempt_seq,
                   a.fencing_token, r.fencing_generation
            FROM runs AS r
            JOIN run_attempts AS a
              ON a.run_ref = r.run_ref
             AND a.attempt_seq = r.current_attempt_seq
            JOIN activations AS x
              ON x.activation_ref = r.activation_ref
             AND x.execution_ref = r.execution_ref
            JOIN workflow_executions AS w
              ON w.execution_ref = r.execution_ref
             AND w.graph_revision_ref = x.graph_revision_ref
             AND w.state = 'ADMITTED'
            WHERE r.run_ref = ?
              AND r.state = 'OPEN'
              AND a.state IN ('CREATED', 'ACTIVE')
            """,
            (run_ref,),
        ).fetchone()
        return AttemptAuthority(**dict(row)) if row is not None else None

    @classmethod
    def is_current_with(
        cls,
        connection: sqlite3.Connection,
        authority: AttemptAuthority,
    ) -> bool:
        current = cls.resolve_current_with(connection, authority.run_ref)
        return current == authority
