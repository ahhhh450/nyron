"""In-process TRUSTED MODULE MODE host boundary."""

from .isolation_profile import (
    TRUSTED_SAME_PROCESS_ISOLATION_PROFILE,
    BoundaryEnforcementClaim,
    CredentialExposureClaim,
    IsolationProfile,
    ModuleCodeTrustClass,
    ProcessDescendantContainmentClaim,
    RawOSAPIAccessClaim,
)
from .trusted_host import (
    Completed,
    Failed,
    TrustedHostError,
    TrustedModuleHost,
)

_RUNTIME_EXPORTS = frozenset(
    {
        "BoundedWriteDispatched",
        "BoundedWriteEffectBroker",
        "BoundedWriteIdentityConflict",
        "BoundedWriteRejected",
        "BoundedWriteUnknown",
        "CapabilityHandle",
        "ResourceHandle",
        "RuntimeContext",
        "RuntimeContextInvariantError",
        "build_runtime_context",
    }
)


def __getattr__(name: str):
    """Load the live-broker surface without creating execution import cycles."""
    if name in _RUNTIME_EXPORTS:
        from . import runtime_context

        return getattr(runtime_context, name)
    raise AttributeError(name)


__all__ = [
    "BoundaryEnforcementClaim",
    "Completed",
    "CredentialExposureClaim",
    "Failed",
    "IsolationProfile",
    "ModuleCodeTrustClass",
    "ProcessDescendantContainmentClaim",
    "RawOSAPIAccessClaim",
    "TRUSTED_SAME_PROCESS_ISOLATION_PROFILE",
    "TrustedHostError",
    "TrustedModuleHost",
    "BoundedWriteDispatched",
    "BoundedWriteEffectBroker",
    "BoundedWriteIdentityConflict",
    "BoundedWriteRejected",
    "BoundedWriteUnknown",
    "CapabilityHandle",
    "ResourceHandle",
    "RuntimeContext",
    "RuntimeContextInvariantError",
    "build_runtime_context",
]
