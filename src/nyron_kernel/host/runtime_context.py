"""TRUSTED MODULE MODE RuntimeContext and its one bounded live broker."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from nyron_kernel.capability import CapabilityGrant
from nyron_kernel.effect import EffectAuthority, EffectError, EffectRequest
from nyron_kernel.execution import ActivationRepository, AttemptAuthority
from nyron_kernel.resource import ResourceLease


_INTENT_PATTERN = re.compile(r"[A-Za-z0-9_.:-]+")
_UNKNOWN_NOTE = "historical external outcome is unknown; no retry clearance"


@dataclass(frozen=True)
class CapabilityHandle:
    capability_type_ref: str
    capability_type_version: str
    grant_ref: str


@dataclass(frozen=True)
class ResourceHandle:
    resource_ref: str
    lease_ref: str


@dataclass(frozen=True)
class BoundedWriteDispatched:
    operation_ref: str
    state: str = "COMPLETED"


@dataclass(frozen=True)
class BoundedWriteRejected:
    operation_ref: str | None
    reason_code: str


@dataclass(frozen=True)
class BoundedWriteUnknown:
    operation_ref: str
    note: str = _UNKNOWN_NOTE


@dataclass(frozen=True)
class BoundedWriteIdentityConflict:
    operation_ref: str
    existing_state: str
    reason_code: str = "EFFECT_OPERATION_IDENTITY_CONFLICT"


@dataclass(frozen=True)
class ModelInvokeDispatched:
    operation_ref: str
    state: str = "COMPLETED"


@dataclass(frozen=True)
class ModelInvokeRejected:
    operation_ref: str | None
    reason_code: str


@dataclass(frozen=True)
class ModelInvokeUnknown:
    operation_ref: str
    note: str = _UNKNOWN_NOTE


@dataclass(frozen=True)
class ModelInvokeIdentityConflict:
    operation_ref: str
    existing_state: str
    reason_code: str = "EFFECT_OPERATION_IDENTITY_CONFLICT"


class RuntimeContextInvariantError(RuntimeError):
    """An impossible trusted Host/storage invariant was violated."""


class BoundedWriteEffectBroker:
    """One supported live-effect method for same-process trusted Modules.

    Private attributes are a supported-ABI convention, not hostile Python
    isolation. Every real request still crosses ``EffectAuthority.execute``.
    """

    def __init__(
        self,
        effect_authority: EffectAuthority,
        authority: AttemptAuthority,
        capability_handles: tuple[CapabilityHandle, ...],
        resource_handles: tuple[ResourceHandle, ...],
        caused_by_ref: str,
    ) -> None:
        self._effect_authority = effect_authority
        self._authority = authority
        self._capability_handles = frozenset(capability_handles)
        self._resource_handles = frozenset(resource_handles)
        self._caused_by_ref = caused_by_ref

    def dispatch_bounded_write(
        self,
        capability_handle: CapabilityHandle,
        resource_handle: ResourceHandle,
        intent_ref: str,
        payload: str,
    ) -> (
        BoundedWriteDispatched
        | BoundedWriteRejected
        | BoundedWriteUnknown
        | BoundedWriteIdentityConflict
    ):
        if (
            type(capability_handle) is not CapabilityHandle
            or capability_handle not in self._capability_handles
            or type(resource_handle) is not ResourceHandle
            or resource_handle not in self._resource_handles
        ):
            return BoundedWriteRejected(None, "BROKER_HANDLE_NOT_IN_CONTEXT")
        if (
            not isinstance(intent_ref, str)
            or not intent_ref
            or len(intent_ref.encode("utf-8")) > 128
            or _INTENT_PATTERN.fullmatch(intent_ref) is None
        ):
            return BoundedWriteRejected(None, "BROKER_INTENT_REF_INVALID")
        if not isinstance(payload, str) or len(payload.encode("utf-8")) > 4096:
            return BoundedWriteRejected(None, "BROKER_PAYLOAD_INVALID")

        operation_ref = self._operation_ref(intent_ref)
        request = EffectRequest(
            operation_ref=operation_ref,
            effect_class=EffectAuthority.EFFECT_CLASS,
            authority=self._authority,
            capability_grant_ref=capability_handle.grant_ref,
            resource_ref=resource_handle.resource_ref,
            resource_lease_ref=resource_handle.lease_ref,
            payload=payload,
            caused_by_ref=self._caused_by_ref,
        )
        try:
            operation = self._effect_authority.execute(request)
        except EffectError as error:
            existing = self._effect_authority.resolve(operation_ref)
            if error.code == "EFFECT_OPERATION_IDENTITY_CONFLICT":
                if existing is None:
                    raise RuntimeContextInvariantError(
                        "identity conflict without durable operation"
                    ) from error
                return BoundedWriteIdentityConflict(
                    operation_ref=operation_ref,
                    existing_state=existing.state,
                )
            if existing is not None and existing.state == "COMPLETED":
                return BoundedWriteDispatched(operation_ref)
            if existing is not None and existing.state == "UNKNOWN":
                return BoundedWriteUnknown(operation_ref)
            return BoundedWriteRejected(operation_ref, error.code)
        if operation.state != "COMPLETED":
            raise RuntimeContextInvariantError(
                "EffectAuthority.execute returned a non-COMPLETED operation"
            )
        return BoundedWriteDispatched(operation_ref)

    def _operation_ref(self, intent_ref: str) -> str:
        identity = (
            self._authority.run_ref
            + "\x00"
            + str(self._authority.attempt_seq)
            + "\x00"
            + intent_ref
        )
        return "module-effect:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()

    def dispatch_model_invoke(
        self,
        capability_handle: CapabilityHandle,
        intent_ref: str,
        *,
        provider_ref: str,
        model_ref: str,
        conflict_scope_ref: str,
        input_text: str,
    ) -> (
        ModelInvokeDispatched
        | ModelInvokeRejected
        | ModelInvokeUnknown
        | ModelInvokeIdentityConflict
    ):
        if (
            type(capability_handle) is not CapabilityHandle
            or capability_handle not in self._capability_handles
        ):
            return ModelInvokeRejected(None, "BROKER_HANDLE_NOT_IN_CONTEXT")
        refs = (intent_ref, provider_ref, model_ref, conflict_scope_ref)
        if any(
            not isinstance(value, str)
            or not value
            or len(value.encode("utf-8")) > 128
            or _INTENT_PATTERN.fullmatch(value) is None
            for value in refs
        ):
            return ModelInvokeRejected(None, "BROKER_MODEL_INVOKE_REF_INVALID")
        if not isinstance(input_text, str) or len(input_text.encode("utf-8")) > 2048:
            return ModelInvokeRejected(None, "BROKER_MODEL_INVOKE_INPUT_INVALID")
        operation_ref = self._operation_ref(intent_ref)
        payload = json.dumps(
            {
                "provider_ref": provider_ref,
                "model_ref": model_ref,
                "conflict_scope_ref": conflict_scope_ref,
                "input": input_text,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        request = EffectRequest(
            operation_ref=operation_ref,
            effect_class=EffectAuthority.MODEL_INVOKE_EFFECT_CLASS,
            authority=self._authority,
            capability_grant_ref=capability_handle.grant_ref,
            resource_ref=None,
            resource_lease_ref=None,
            payload=payload,
            caused_by_ref=self._caused_by_ref,
        )
        try:
            operation = self._effect_authority.execute(request)
        except EffectError as error:
            existing = self._effect_authority.resolve(operation_ref)
            if error.code == "EFFECT_OPERATION_IDENTITY_CONFLICT":
                if existing is None:
                    raise RuntimeContextInvariantError(
                        "identity conflict without durable operation"
                    ) from error
                return ModelInvokeIdentityConflict(operation_ref, existing.state)
            if existing is not None and existing.state == "COMPLETED":
                return ModelInvokeDispatched(operation_ref)
            if existing is not None and existing.state == "UNKNOWN":
                return ModelInvokeUnknown(operation_ref)
            return ModelInvokeRejected(operation_ref, error.code)
        if operation.state != "COMPLETED":
            raise RuntimeContextInvariantError(
                "EffectAuthority.execute returned a non-COMPLETED operation"
            )
        return ModelInvokeDispatched(operation_ref)


@dataclass(frozen=True)
class RuntimeContext:
    activation_ref: str
    run_ref: str
    attempt_seq: int
    fencing_token: str
    accounting_scope_ref: str
    capability_handles: tuple[CapabilityHandle, ...]
    resource_handles: tuple[ResourceHandle, ...]
    metadata: tuple[tuple[str, str], ...]
    effect_broker: BoundedWriteEffectBroker | None


def is_valid_runtime_context(value: object) -> bool:
    """Defensively validate the complete supported Module-visible shape."""

    if type(value) is not RuntimeContext:
        return False
    if (
        type(value.activation_ref) is not str
        or type(value.run_ref) is not str
        or type(value.attempt_seq) is not int
        or value.attempt_seq <= 0
        or type(value.fencing_token) is not str
        or type(value.accounting_scope_ref) is not str
        or type(value.capability_handles) is not tuple
        or type(value.resource_handles) is not tuple
        or type(value.metadata) is not tuple
        or (
            value.effect_broker is not None
            and type(value.effect_broker) is not BoundedWriteEffectBroker
        )
    ):
        return False
    if any(not _valid_capability_handle(handle) for handle in value.capability_handles):
        return False
    if any(not _valid_resource_handle(handle) for handle in value.resource_handles):
        return False
    return all(
        type(pair) is tuple
        and len(pair) == 2
        and type(pair[0]) is str
        and type(pair[1]) is str
        for pair in value.metadata
    )


def _valid_capability_handle(value: object) -> bool:
    return (
        type(value) is CapabilityHandle
        and type(value.capability_type_ref) is str
        and type(value.capability_type_version) is str
        and type(value.grant_ref) is str
    )


def _valid_resource_handle(value: object) -> bool:
    return (
        type(value) is ResourceHandle
        and type(value.resource_ref) is str
        and type(value.lease_ref) is str
    )


def build_runtime_context(
    *,
    authority: AttemptAuthority,
    activation_repository: ActivationRepository,
    accounting_scope_ref: str,
    capability_grants: tuple[CapabilityGrant, ...] = (),
    resource_leases: tuple[ResourceLease, ...] = (),
    effect_authority: EffectAuthority | None = None,
    metadata: tuple[tuple[str, str], ...] = (),
) -> RuntimeContext:
    """Build public values from trusted invocation inputs without re-resolving R2."""

    if type(authority) is not AttemptAuthority:
        raise RuntimeContextInvariantError("invalid original AttemptAuthority")
    capability_handles = tuple(
        CapabilityHandle(
            grant.capability_type_ref,
            grant.capability_type_version,
            grant.grant_ref,
        )
        for grant in capability_grants
        if type(grant) is CapabilityGrant
        and _grant_matches_authority(grant, authority)
    )
    resource_handles = tuple(
        ResourceHandle(lease.resource_ref, lease.lease_ref)
        for lease in resource_leases
        if type(lease) is ResourceLease
        and _lease_matches_authority(lease, authority)
    )
    activation = activation_repository.resolve(authority.activation_ref)
    causal_ref = None
    if (
        activation is not None
        and activation.execution_ref == authority.execution_ref
        and activation.activation_ref == authority.activation_ref
        and activation.trigger_delivery_ref
    ):
        causal_ref = activation.trigger_delivery_ref
    broker = None
    if (
        effect_authority is not None
        and capability_handles
        and causal_ref is not None
    ):
        broker = BoundedWriteEffectBroker(
            effect_authority,
            authority,
            capability_handles,
            resource_handles,
            causal_ref,
        )
    return RuntimeContext(
        activation_ref=authority.activation_ref,
        run_ref=authority.run_ref,
        attempt_seq=authority.attempt_seq,
        fencing_token=authority.fencing_token,
        accounting_scope_ref=accounting_scope_ref,
        capability_handles=capability_handles,
        resource_handles=resource_handles,
        metadata=metadata,
        effect_broker=broker,
    )


def _grant_matches_authority(
    grant: CapabilityGrant, authority: AttemptAuthority
) -> bool:
    return (
        grant.execution_ref,
        grant.activation_ref,
        grant.run_ref,
        grant.attempt_seq,
        grant.fencing_token,
        grant.fencing_generation,
    ) == (
        authority.execution_ref,
        authority.activation_ref,
        authority.run_ref,
        authority.attempt_seq,
        authority.fencing_token,
        authority.fencing_generation,
    )


def _lease_matches_authority(lease: ResourceLease, authority: AttemptAuthority) -> bool:
    return (
        lease.execution_ref,
        lease.activation_ref,
        lease.run_ref,
        lease.attempt_seq,
        lease.fencing_token,
        lease.fencing_generation,
    ) == (
        authority.execution_ref,
        authority.activation_ref,
        authority.run_ref,
        authority.attempt_seq,
        authority.fencing_token,
        authority.fencing_generation,
    )
