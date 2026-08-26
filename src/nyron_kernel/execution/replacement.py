"""Post-cutover cleanup for one exact replaced RunAttempt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from nyron_kernel.store import SQLiteStore

from .attempt import AttemptAuthority

if TYPE_CHECKING:
    from nyron_kernel.effect import EffectAuthority, EffectOperation
    from nyron_kernel.resource import ResourceLease, ResourceManager


class ReplacementCleanupError(RuntimeError):
    """Fail-closed Gate-4B orchestration error."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class ReplacementCleanupResult:
    effects: tuple[EffectOperation, ...]
    leases: tuple[ResourceLease, ...]


class ReplacementCleanup:
    """Discover exact-R1 work and delegate every transition to its Owner."""

    def __init__(
        self,
        store: SQLiteStore,
        effect_authority: EffectAuthority,
        resource_manager: ResourceManager,
    ) -> None:
        self._store = store
        self._effect_authority = effect_authority
        self._resource_manager = resource_manager

    def cleanup(self, replaced_authority: AttemptAuthority) -> ReplacementCleanupResult:
        if not isinstance(replaced_authority, AttemptAuthority):
            raise ReplacementCleanupError("REPLACED_ATTEMPT_AUTHORITY_INVALID")

        effect_refs, lease_refs = self._discover_exact_replaced_work(
            replaced_authority
        )

        effects: list[EffectOperation] = []
        for operation_ref, state in effect_refs:
            if state in {"PREPARED", "ACTIVE"}:
                operation = self._effect_authority.request_revoke(operation_ref)
            else:
                operation = self._require_effect(operation_ref)
            if operation.state == "REVOKE_REQUESTED":
                operation = self._effect_authority.resolve_revoke(operation_ref)
            effects.append(operation)

        leases = tuple(
            self._resource_manager.revoke_lease(lease_ref)
            for lease_ref in lease_refs
        )
        return ReplacementCleanupResult(tuple(effects), leases)

    def _discover_exact_replaced_work(
        self, authority: AttemptAuthority
    ) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...]]:
        with self._store.transaction() as connection:
            run = connection.execute(
                """
                SELECT run_ref, activation_ref, execution_ref,
                       current_attempt_seq, fencing_generation
                FROM runs WHERE run_ref = ?
                """,
                (authority.run_ref,),
            ).fetchone()
            replaced = connection.execute(
                """
                SELECT run_ref, attempt_seq, fencing_token, state
                FROM run_attempts WHERE run_ref = ? AND attempt_seq = ?
                """,
                (authority.run_ref, authority.attempt_seq),
            ).fetchone()
            if run is None or replaced is None:
                raise ReplacementCleanupError("REPLACED_ATTEMPT_NOT_PROVEN")
            sequence_delta = run["current_attempt_seq"] - authority.attempt_seq
            generation_delta = (
                run["fencing_generation"] - authority.fencing_generation
            )
            if (
                run["run_ref"] != authority.run_ref
                or run["execution_ref"] != authority.execution_ref
                or run["activation_ref"] != authority.activation_ref
                or replaced["run_ref"] != authority.run_ref
                or replaced["attempt_seq"] != authority.attempt_seq
                or replaced["fencing_token"] != authority.fencing_token
                or replaced["state"] != "REPLACED"
                or sequence_delta <= 0
                or generation_delta <= 0
                or sequence_delta != generation_delta
            ):
                raise ReplacementCleanupError("REPLACED_ATTEMPT_NOT_PROVEN")

            current = connection.execute(
                """
                SELECT fencing_token FROM run_attempts
                WHERE run_ref = ? AND attempt_seq = ?
                """,
                (authority.run_ref, run["current_attempt_seq"]),
            ).fetchone()
            if (
                current is None
                or not current["fencing_token"]
                or current["fencing_token"] == authority.fencing_token
            ):
                raise ReplacementCleanupError("REPLACED_ATTEMPT_NOT_PROVEN")

            effect_rows = connection.execute(
                """
                SELECT operation_ref, state, execution_ref, activation_ref,
                       run_ref, attempt_seq, fencing_token, fencing_generation
                FROM effect_operations
                WHERE run_ref = ? AND attempt_seq = ?
                  AND state IN ('PREPARED', 'ACTIVE', 'REVOKE_REQUESTED')
                ORDER BY operation_ref
                """,
                (authority.run_ref, authority.attempt_seq),
            ).fetchall()
            lease_rows = connection.execute(
                """
                SELECT lease_ref, execution_ref, activation_ref, run_ref,
                       attempt_seq, fencing_token, fencing_generation
                FROM resource_leases
                WHERE run_ref = ? AND attempt_seq = ? AND state = 'ACTIVE'
                ORDER BY lease_ref
                """,
                (authority.run_ref, authority.attempt_seq),
            ).fetchall()

            for row in (*effect_rows, *lease_rows):
                if self._authority_from_row(row) != authority:
                    raise ReplacementCleanupError(
                        "REPLACED_ATTEMPT_TUPLE_MISMATCH"
                    )

        return (
            tuple((row["operation_ref"], row["state"]) for row in effect_rows),
            tuple(row["lease_ref"] for row in lease_rows),
        )

    def _require_effect(self, operation_ref: str) -> EffectOperation:
        operation = self._effect_authority.resolve(operation_ref)
        if operation is None:  # pragma: no cover - owner row disappeared
            raise ReplacementCleanupError("EFFECT_OPERATION_DISAPPEARED")
        return operation

    @staticmethod
    def _authority_from_row(row: object) -> AttemptAuthority:
        return AttemptAuthority(
            row["execution_ref"],
            row["activation_ref"],
            row["run_ref"],
            row["attempt_seq"],
            row["fencing_token"],
            row["fencing_generation"],
        )
