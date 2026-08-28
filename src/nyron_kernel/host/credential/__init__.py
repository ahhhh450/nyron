"""Credential reference and trusted-resolution boundary exports."""

from .foundation import (
    CredentialBindingRevision,
    CredentialBoundaryError,
    CredentialRepository,
    CredentialResolutionAuthority,
    CredentialResolutionRecord,
    CredentialResolutionRequest,
    CredentialResolver,
    ResolvedCredentialHandle,
    UnconfiguredCredentialResolver,
)

__all__ = [
    "CredentialBindingRevision",
    "CredentialBoundaryError",
    "CredentialRepository",
    "CredentialResolutionAuthority",
    "CredentialResolutionRecord",
    "CredentialResolutionRequest",
    "CredentialResolver",
    "ResolvedCredentialHandle",
    "UnconfiguredCredentialResolver",
]
