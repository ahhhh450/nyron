"""Narrow, opaque RuntimeContext shape (Module Design Report §38) and its
Host-side construction from already-accepted Owner objects.

This is the ARE-GATE-5 minimal trust-boundary slice for RuntimeContext.
It deliberately implements only the RuntimeContext *data* shape and a
one-way, narrowing conversion from real canonical Owner objects into it.
It does NOT implement any callable/broker object reachable from inside a
Module's own ``execute()`` body — no live invocation ABI is defined here.

Why the live invocation ABI is out of scope for this slice: the frozen
Capability/Resource/Effect Authority baseline and the Module Design Report
specify the RuntimeContext *field* shape (§38) and the general mediation
principle (Design Candidate §15) but do not specify a concrete Python-level
calling convention for a Module to trigger a mediated effect mid-execution.
Every named effect surface that could motivate such a call
(``workspace.write``, ``process.start``, ``model.invoke``,
``network.request``) is explicit Strict-Out-Of-Scope for this Task.
Inventing a calling convention now would mean inventing a generalized Host
SDK shape not determined by current frozen contracts or repository facts,
which this Task is explicitly required to avoid. That piece is left for a
future Gate-5 sub-task once a concrete brokered effect surface is in scope.

Given that constraint, everything produced by this module carries zero
actionable authority: a handle is nothing but an inert identity reference
(a ref string, or a ref/type pair) that a Module could echo back but that
no code path anywhere in this repository reads to authorize or perform a
real mutation. Building a RuntimeContext from real Owner objects, or from
fabricated strings, produces observably identical downstream behavior,
because nothing consumes handle contents yet. This is a deliberate,
narrower property than "the broker rejects a bad handle" — there is no
broker to bypass.

Design choices that follow directly from the frozen trust boundary:

- ``CapabilityHandle`` copies only ``capability_type_ref``,
  ``capability_type_version`` and ``grant_ref`` from a real
  ``CapabilityGrant``. It never copies ``scope``, ``state``,
  ``expires_at`` or any other validity-relevant field, so a
  ``RuntimeContext`` can never be read later as a cached validity
  signal — real validity is only ever decided by the accepted Capability
  Authority at the moment of real use, never here.
- ``ResourceHandle`` copies only ``resource_ref`` and ``lease_ref`` from a
  real ``ResourceLease``. It is built exclusively from the *lease*, never
  from the ``Resource`` record itself, so it structurally cannot carry
  ``Resource.external_ref`` (the raw managed-root filesystem path) or any
  other lifecycle-ownership field. There is no field on ``ResourceHandle``
  that could ever hold a filesystem path.
- ``build_runtime_context`` performs no validity check of any kind (no
  state/expiry/fencing comparison). It is pure narrow field projection,
  not a cached authority decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type-checking only: nyron_kernel.execution already imports this host
    # package (the existing executor binds Completed/Failed/TrustedModuleHost
    # to invoke modules), so importing these Owner types at module load time
    # would be a real circular import, not merely an ordering inconvenience.
    # Nothing here needs the real classes at runtime — every use below is
    # plain duck-typed attribute access, never isinstance/construction.
    from nyron_kernel.capability import CapabilityGrant
    from nyron_kernel.execution import AttemptAuthority
    from nyron_kernel.resource import ResourceLease

_STR_METADATA_LIMIT = 64


def _require_nonempty_str(value: object, field: str) -> None:
    if type(value) is not str or not value:
        raise TypeError(f"{field} must be a non-empty str, got {value!r}")


@dataclass(frozen=True)
class CapabilityHandle:
    """Opaque capability identity reference. Not a reusable permission token.

    Carries no scope, state, or expiry — nothing that could be mistaken
    for a cached authorization decision.
    """

    capability_type_ref: str
    capability_type_version: str
    grant_ref: str

    def __post_init__(self) -> None:
        _require_nonempty_str(self.capability_type_ref, "capability_type_ref")
        _require_nonempty_str(self.capability_type_version, "capability_type_version")
        _require_nonempty_str(self.grant_ref, "grant_ref")


@dataclass(frozen=True)
class ResourceHandle:
    """Opaque resource identity reference. Carries no lifecycle ownership
    and no filesystem path — there is no field capable of holding one."""

    resource_ref: str
    lease_ref: str

    def __post_init__(self) -> None:
        _require_nonempty_str(self.resource_ref, "resource_ref")
        _require_nonempty_str(self.lease_ref, "lease_ref")


@dataclass(frozen=True)
class RuntimeContext:
    """Frozen §38 RuntimeContext shape: immutable, opaque, non-actionable
    identity data only. Never holds a Store, connection, Owner object, or
    raw filesystem authority — every field is a validated primitive, a
    validated handle, or a tuple of either."""

    activation_ref: str
    run_ref: str
    attempt_seq: int
    fencing_token: str
    accounting_scope_ref: str
    capability_handles: tuple[CapabilityHandle, ...] = ()
    resource_handles: tuple[ResourceHandle, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require_nonempty_str(self.activation_ref, "activation_ref")
        _require_nonempty_str(self.run_ref, "run_ref")
        _require_nonempty_str(self.fencing_token, "fencing_token")
        _require_nonempty_str(self.accounting_scope_ref, "accounting_scope_ref")
        if type(self.attempt_seq) is not int or self.attempt_seq <= 0:
            raise TypeError(f"attempt_seq must be a positive int, got {self.attempt_seq!r}")
        if type(self.capability_handles) is not tuple or not all(
            type(item) is CapabilityHandle for item in self.capability_handles
        ):
            raise TypeError("capability_handles must be a tuple[CapabilityHandle, ...]")
        if type(self.resource_handles) is not tuple or not all(
            type(item) is ResourceHandle for item in self.resource_handles
        ):
            raise TypeError("resource_handles must be a tuple[ResourceHandle, ...]")
        if type(self.metadata) is not tuple:
            raise TypeError("metadata must be a tuple[tuple[str, str], ...]")
        seen_keys: set[str] = set()
        for entry in self.metadata:
            if (
                type(entry) is not tuple
                or len(entry) != 2
                or type(entry[0]) is not str
                or not entry[0]
                or type(entry[1]) is not str
                or len(entry[1]) > _STR_METADATA_LIMIT
            ):
                raise TypeError(
                    "metadata entries must be (non-empty str key, "
                    f"str value of at most {_STR_METADATA_LIMIT} chars)"
                )
            if entry[0] in seen_keys:
                raise TypeError(f"duplicate metadata key: {entry[0]!r}")
            seen_keys.add(entry[0])


def build_runtime_context(
    attempt: AttemptAuthority,
    accounting_scope_ref: str,
    capability_grants: tuple[CapabilityGrant, ...] = (),
    resource_leases: tuple[ResourceLease, ...] = (),
    metadata: tuple[tuple[str, str], ...] = (),
) -> RuntimeContext:
    """Host-only narrowing conversion: real Owner objects in, opaque
    non-actionable RuntimeContext out.

    Performs no validity/authority decision of any kind. Any real
    admission/authority use must still separately go through the accepted
    Capability / Resource / Effect Authority boundary at the point of use;
    nothing this function returns may ever substitute for that.
    """
    capability_handles = tuple(
        CapabilityHandle(
            capability_type_ref=grant.capability_type_ref,
            capability_type_version=grant.capability_type_version,
            grant_ref=grant.grant_ref,
        )
        for grant in capability_grants
    )
    resource_handles = tuple(
        ResourceHandle(resource_ref=lease.resource_ref, lease_ref=lease.lease_ref)
        for lease in resource_leases
    )
    return RuntimeContext(
        activation_ref=attempt.activation_ref,
        run_ref=attempt.run_ref,
        attempt_seq=attempt.attempt_seq,
        fencing_token=attempt.fencing_token,
        accounting_scope_ref=accounting_scope_ref,
        capability_handles=capability_handles,
        resource_handles=resource_handles,
        metadata=metadata,
    )
