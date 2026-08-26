"""One real bounded EffectOperation and its dispatch linearization boundary."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from nyron_kernel.capability import CapabilityAuthority
from nyron_kernel.execution import AttemptAuthority, RuntimeAuthorityResolver
from nyron_kernel.resource import ResourceManager
from nyron_kernel.store import SQLiteStore


class EffectError(RuntimeError):
    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class EffectRequest:
    operation_ref: str
    effect_class: str
    authority: AttemptAuthority
    capability_grant_ref: str
    resource_ref: str
    resource_lease_ref: str
    payload: str
    caused_by_ref: str


@dataclass(frozen=True)
class EffectOperation:
    operation_ref: str
    effect_class: str
    execution_ref: str
    activation_ref: str
    run_ref: str
    attempt_seq: int
    fencing_token: str
    fencing_generation: int
    capability_grant_ref: str
    resource_ref: str
    resource_lease_ref: str
    target_ref: str
    payload: str
    payload_hash: str
    caused_by_ref: str
    state: str
    prepared_at: int
    dispatch_admission_ref: str | None
    dispatch_admitted_at: int | None
    completion_evidence: dict[str, object] | None


class EffectAuthority:
    """Sole canonical writer and trusted adapter for the bounded effect."""

    EFFECT_CLASS = "nyron.kernel.managed-resource-bounded-write@1"
    _MAX_PAYLOAD_BYTES = 4096

    def __init__(
        self,
        store: SQLiteStore,
        runtime_authority: RuntimeAuthorityResolver,
        capability_authority: CapabilityAuthority,
        resource_manager: ResourceManager,
        clock: Callable[[], int],
        crash_hook: Callable[[str, EffectOperation], None] | None = None,
    ) -> None:
        self._store = store
        self._runtime_authority = runtime_authority
        self._capability_authority = capability_authority
        self._resource_manager = resource_manager
        self._clock = clock
        self._crash_hook = crash_hook or (lambda _stage, _operation: None)
        self._store.create_effect_schema()

    def execute(self, request: EffectRequest) -> EffectOperation:
        """Prepare, admit, and perform this one trusted bounded mutation."""

        operation = self.prepare(request)
        if operation.state == "COMPLETED":
            return operation
        if operation.state == "ACTIVE":
            operation = self.recover(request.operation_ref)
        if operation.state != "PREPARED":
            raise EffectError("EFFECT_OPERATION_NOT_DISPATCHABLE")

        recovered = self.recover(request.operation_ref)
        if recovered.state == "COMPLETED":
            return recovered
        if recovered.state != "PREPARED":
            raise EffectError("EFFECT_OPERATION_NOT_DISPATCHABLE")

        if recovered.dispatch_admission_ref is None:
            recovered = self._admit_dispatch(recovered)
        self._crash_hook("AFTER_DISPATCH_ADMISSION", recovered)
        active = self._activate(recovered)
        self._crash_hook("AFTER_ACTIVE_COMMIT", active)
        return self._mutate_and_complete(active)

    def prepare(self, request: EffectRequest) -> EffectOperation:
        """Commit exact PREPARED intent without consuming authority."""

        self._validate_request(request)
        payload_json, payload_hash = self._payload_identity(request.payload)
        existing = self.resolve(request.operation_ref)
        if existing is not None:
            self._require_identical_replay(existing, request, payload_hash)
            return existing

        resource = self._resource_manager.resolve_resource(request.resource_ref)
        if resource is None:
            raise EffectError("UNRESOLVED_RESOURCE")
        directory = Path(resource.external_ref)
        target = directory / self._target_name(request.operation_ref)
        prepared_at = self._now()

        try:
            with self._store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO effect_operations(
                        operation_ref, effect_class, execution_ref,
                        activation_ref, run_ref, attempt_seq, fencing_token,
                        fencing_generation, capability_grant_ref, resource_ref,
                        resource_lease_ref, target_ref, payload_json,
                        payload_hash, caused_by_ref, state, prepared_at,
                        dispatch_admission_ref, dispatch_admitted_at,
                        completion_evidence_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                              'PREPARED', ?, NULL, NULL, NULL)
                    """,
                    (
                        request.operation_ref,
                        request.effect_class,
                        request.authority.execution_ref,
                        request.authority.activation_ref,
                        request.authority.run_ref,
                        request.authority.attempt_seq,
                        request.authority.fencing_token,
                        request.authority.fencing_generation,
                        request.capability_grant_ref,
                        request.resource_ref,
                        request.resource_lease_ref,
                        str(target),
                        payload_json,
                        payload_hash,
                        request.caused_by_ref,
                        prepared_at,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise EffectError("EFFECT_OPERATION_IDENTITY_CONFLICT") from error
        operation = self._require_operation(request.operation_ref)
        self._crash_hook("AFTER_PREPARED_COMMIT", operation)
        return operation

    def recover(self, operation_ref: str) -> EffectOperation:
        """Classify only from exact owner-local and external evidence."""

        operation = self._require_operation(operation_ref)
        if operation.state not in {"PREPARED", "ACTIVE"}:
            return operation
        evidence = self._target_evidence(operation)
        if operation.state == "ACTIVE":
            if evidence == "EXACT":
                self._commit_completed(operation)
            else:
                self._mark_unknown(operation_ref)
        elif operation.dispatch_admission_ref is None:
            if evidence != "ABSENT":
                self._mark_unknown(operation_ref)
        elif evidence == "EXACT":
            self._commit_completed(operation)
        elif evidence == "MISMATCH":
            self._mark_unknown(operation_ref)
        return self._require_operation(operation_ref)

    def resolve(self, operation_ref: str) -> EffectOperation | None:
        row = self._store.connection.execute(
            "SELECT * FROM effect_operations WHERE operation_ref = ?",
            (operation_ref,),
        ).fetchone()
        return self._operation_from_row(row) if row is not None else None

    def _admit_dispatch(self, operation: EffectOperation) -> EffectOperation:
        authority = self._authority_from_operation(operation)
        exact_scope = {
            "effect_class": operation.effect_class,
            "resource_ref": operation.resource_ref,
        }
        rejected = False
        with self._store.transaction() as connection:
            current = connection.execute(
                "SELECT * FROM effect_operations WHERE operation_ref = ?",
                (operation.operation_ref,),
            ).fetchone()
            if current is None or current["state"] != "PREPARED":
                raise EffectError("EFFECT_OPERATION_NOT_DISPATCHABLE")
            if current["dispatch_admission_ref"] is not None:
                return self._operation_from_row(current)

            now = self._now()
            resource_directory = self._resource_manager._resolve_effect_directory_with(
                connection,
                operation.resource_ref,
                operation.resource_lease_ref,
                authority,
                now,
            )
            target = Path(operation.target_ref)
            target_evidence = self._target_evidence(operation)
            valid = (
                self._runtime_authority.is_current_with(connection, authority)
                and self._capability_authority._is_effect_dispatch_admissible_with(
                    connection,
                    operation.capability_grant_ref,
                    authority,
                    exact_scope,
                    now,
                )
                and resource_directory is not None
                and target.parent == resource_directory
                and target.name == self._target_name(operation.operation_ref)
                and target_evidence == "ABSENT"
            )
            if not valid:
                rejected_state = (
                    "UNKNOWN" if target_evidence != "ABSENT" else "FENCED"
                )
                connection.execute(
                    "UPDATE effect_operations SET state = ? WHERE operation_ref = ?",
                    (rejected_state, operation.operation_ref),
                )
                rejected = True
            else:
                admission_ref = self._admission_ref(operation.operation_ref)
                connection.execute(
                    """
                    UPDATE effect_operations
                    SET dispatch_admission_ref = ?, dispatch_admitted_at = ?
                    WHERE operation_ref = ?
                    """,
                    (admission_ref, now, operation.operation_ref),
                )
        if rejected:
            raise EffectError("EFFECT_DISPATCH_AUTHORITY_REJECTED")
        return self._require_operation(operation.operation_ref)

    def _activate(self, operation: EffectOperation) -> EffectOperation:
        with self._store.transaction() as connection:
            row = connection.execute(
                "SELECT state, dispatch_admission_ref FROM effect_operations WHERE operation_ref = ?",
                (operation.operation_ref,),
            ).fetchone()
            if row is None:
                raise EffectError("UNRESOLVED_EFFECT_OPERATION")
            if row["state"] == "ACTIVE":
                return self._operation_from_row(
                    connection.execute(
                        "SELECT * FROM effect_operations WHERE operation_ref = ?",
                        (operation.operation_ref,),
                    ).fetchone()
                )
            if row["state"] != "PREPARED" or row["dispatch_admission_ref"] is None:
                raise EffectError("EFFECT_ACTIVATION_NOT_ALLOWED")
            connection.execute(
                "UPDATE effect_operations SET state = 'ACTIVE' WHERE operation_ref = ?",
                (operation.operation_ref,),
            )
        return self._require_operation(operation.operation_ref)

    def _mutate_and_complete(self, operation: EffectOperation) -> EffectOperation:
        evidence = self._target_evidence(operation)
        if evidence == "ABSENT":
            target = Path(operation.target_ref)
            data = operation.payload.encode("utf-8")
            try:
                with target.open("xb") as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            except FileExistsError:
                pass
            evidence = self._target_evidence(operation)
        if evidence != "EXACT":
            self._mark_unknown(operation.operation_ref)
            raise EffectError("EFFECT_EXTERNAL_EVIDENCE_AMBIGUOUS")
        self._crash_hook("AFTER_EXTERNAL_MUTATION", operation)
        self._commit_completed(operation)
        return self._require_operation(operation.operation_ref)

    def _commit_completed(self, operation: EffectOperation) -> None:
        evidence = {
            "schema": 1,
            "target_ref": operation.target_ref,
            "payload_hash": operation.payload_hash,
        }
        evidence_json = self._canonical_json(evidence)
        with self._store.transaction() as connection:
            row = connection.execute(
                "SELECT state, dispatch_admission_ref FROM effect_operations WHERE operation_ref = ?",
                (operation.operation_ref,),
            ).fetchone()
            if row is None:
                raise EffectError("UNRESOLVED_EFFECT_OPERATION")
            if row["state"] == "COMPLETED":
                return
            if row["state"] != "ACTIVE" or row["dispatch_admission_ref"] is None:
                raise EffectError("EFFECT_COMPLETION_NOT_ALLOWED")
            connection.execute(
                """
                UPDATE effect_operations
                SET state = 'COMPLETED', completion_evidence_json = ?
                WHERE operation_ref = ?
                """,
                (evidence_json, operation.operation_ref),
            )

    def _mark_unknown(self, operation_ref: str) -> None:
        with self._store.transaction() as connection:
            row = connection.execute(
                "SELECT state FROM effect_operations WHERE operation_ref = ?",
                (operation_ref,),
            ).fetchone()
            if row is None:
                raise EffectError("UNRESOLVED_EFFECT_OPERATION")
            if row["state"] in {"PREPARED", "ACTIVE"}:
                connection.execute(
                    "UPDATE effect_operations SET state = 'UNKNOWN' WHERE operation_ref = ?",
                    (operation_ref,),
                )

    def _target_evidence(self, operation: EffectOperation) -> str:
        target = Path(operation.target_ref)
        if not target.exists():
            return "ABSENT"
        if not target.is_file() or target.is_symlink():
            return "MISMATCH"
        try:
            data = target.read_bytes()
        except OSError:
            return "MISMATCH"
        return (
            "EXACT"
            if hashlib.sha256(data).hexdigest() == operation.payload_hash
            and data == operation.payload.encode("utf-8")
            else "MISMATCH"
        )

    @classmethod
    def _validate_request(cls, request: EffectRequest) -> None:
        if not isinstance(request, EffectRequest):
            raise EffectError("EFFECT_REQUEST_INVALID")
        strings = (
            request.operation_ref,
            request.effect_class,
            request.capability_grant_ref,
            request.resource_ref,
            request.resource_lease_ref,
            request.caused_by_ref,
        )
        if (
            any(not isinstance(value, str) or not value for value in strings)
            or request.effect_class != cls.EFFECT_CLASS
            or not isinstance(request.authority, AttemptAuthority)
            or not isinstance(request.payload, str)
            or len(request.payload.encode("utf-8")) > cls._MAX_PAYLOAD_BYTES
        ):
            raise EffectError("EFFECT_REQUEST_INVALID")

    @staticmethod
    def _payload_identity(payload: str) -> tuple[str, str]:
        data = payload.encode("utf-8")
        return (
            json.dumps(payload, ensure_ascii=True, separators=(",", ":")),
            hashlib.sha256(data).hexdigest(),
        )

    @staticmethod
    def _target_name(operation_ref: str) -> str:
        digest = hashlib.sha256(operation_ref.encode("utf-8")).hexdigest()
        return f"effect-{digest}.bounded"

    @staticmethod
    def _admission_ref(operation_ref: str) -> str:
        digest = hashlib.sha256(operation_ref.encode("utf-8")).hexdigest()
        return f"effect-dispatch-admission:{digest}"

    def _now(self) -> int:
        value = self._clock()
        if not isinstance(value, int) or isinstance(value, bool):
            raise EffectError("EFFECT_CLOCK_INVALID")
        return value

    @staticmethod
    def _canonical_json(value: object) -> str:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )

    def _require_operation(self, operation_ref: str) -> EffectOperation:
        operation = self.resolve(operation_ref)
        if operation is None:
            raise EffectError("UNRESOLVED_EFFECT_OPERATION")
        return operation

    @staticmethod
    def _authority_from_operation(operation: EffectOperation) -> AttemptAuthority:
        return AttemptAuthority(
            operation.execution_ref,
            operation.activation_ref,
            operation.run_ref,
            operation.attempt_seq,
            operation.fencing_token,
            operation.fencing_generation,
        )

    @staticmethod
    def _operation_from_row(row: sqlite3.Row) -> EffectOperation:
        return EffectOperation(
            operation_ref=row["operation_ref"],
            effect_class=row["effect_class"],
            execution_ref=row["execution_ref"],
            activation_ref=row["activation_ref"],
            run_ref=row["run_ref"],
            attempt_seq=row["attempt_seq"],
            fencing_token=row["fencing_token"],
            fencing_generation=row["fencing_generation"],
            capability_grant_ref=row["capability_grant_ref"],
            resource_ref=row["resource_ref"],
            resource_lease_ref=row["resource_lease_ref"],
            target_ref=row["target_ref"],
            payload=json.loads(row["payload_json"]),
            payload_hash=row["payload_hash"],
            caused_by_ref=row["caused_by_ref"],
            state=row["state"],
            prepared_at=row["prepared_at"],
            dispatch_admission_ref=row["dispatch_admission_ref"],
            dispatch_admitted_at=row["dispatch_admitted_at"],
            completion_evidence=(
                json.loads(row["completion_evidence_json"])
                if row["completion_evidence_json"] is not None
                else None
            ),
        )

    @classmethod
    def _require_identical_replay(
        cls,
        existing: EffectOperation,
        request: EffectRequest,
        payload_hash: str,
    ) -> None:
        if (
            existing.effect_class != request.effect_class
            or cls._authority_from_operation(existing) != request.authority
            or existing.capability_grant_ref != request.capability_grant_ref
            or existing.resource_ref != request.resource_ref
            or existing.resource_lease_ref != request.resource_lease_ref
            or existing.payload != request.payload
            or existing.payload_hash != payload_hash
            or existing.caused_by_ref != request.caused_by_ref
        ):
            raise EffectError("EFFECT_OPERATION_IDENTITY_CONFLICT")
