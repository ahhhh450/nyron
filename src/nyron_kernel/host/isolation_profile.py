"""Truthful declarative host-isolation claims for D-008 §16 / EIW-INV-24."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ModuleCodeTrustClass(str, Enum):
    TRUSTED_BUILTIN = "TRUSTED_BUILTIN"
    RESTRICTED = "RESTRICTED"
    HOSTILE = "HOSTILE"


class BoundaryEnforcementClaim(str, Enum):
    MEDIATED = "MEDIATED"
    OS_RESTRICTED = "OS_RESTRICTED"
    UNRESTRICTED = "UNRESTRICTED"


class ProcessDescendantContainmentClaim(str, Enum):
    ENFORCED = "ENFORCED"
    NOT_ENFORCED = "NOT_ENFORCED"


class CredentialExposureClaim(str, Enum):
    ISOLATED = "ISOLATED"
    BROKER_MEDIATED = "BROKER_MEDIATED"
    NOT_ISOLATED = "NOT_ISOLATED"


class RawOSAPIAccessClaim(str, Enum):
    DENIED = "DENIED"
    RESTRICTED = "RESTRICTED"
    UNRESTRICTED = "UNRESTRICTED"


@dataclass(frozen=True)
class IsolationProfile:
    """Immutable explicit isolation claim set.

    Values describe enforcement that exists; they do not themselves grant
    authority or authorize execution under the claimed profile.
    """

    profile_ref: str
    module_code_trust_class: ModuleCodeTrustClass
    filesystem_enforcement_claim: BoundaryEnforcementClaim
    network_enforcement_claim: BoundaryEnforcementClaim
    process_descendant_containment_claim: ProcessDescendantContainmentClaim
    credential_exposure_claim: CredentialExposureClaim
    raw_os_api_access_claim: RawOSAPIAccessClaim
    host_escape_assumptions: tuple[str, ...]
    supported_adapter_boundaries: tuple[str, ...]
    verification_evidence_ref: str

    def __post_init__(self) -> None:
        _require_nonempty("profile_ref", self.profile_ref)
        _require_exact_enum("module_code_trust_class", self.module_code_trust_class, ModuleCodeTrustClass)
        _require_exact_enum("filesystem_enforcement_claim", self.filesystem_enforcement_claim, BoundaryEnforcementClaim)
        _require_exact_enum("network_enforcement_claim", self.network_enforcement_claim, BoundaryEnforcementClaim)
        _require_exact_enum(
            "process_descendant_containment_claim",
            self.process_descendant_containment_claim,
            ProcessDescendantContainmentClaim,
        )
        _require_exact_enum("credential_exposure_claim", self.credential_exposure_claim, CredentialExposureClaim)
        _require_exact_enum("raw_os_api_access_claim", self.raw_os_api_access_claim, RawOSAPIAccessClaim)
        _require_nonempty_tuple("host_escape_assumptions", self.host_escape_assumptions)
        _require_string_tuple("supported_adapter_boundaries", self.supported_adapter_boundaries)
        _require_nonempty("verification_evidence_ref", self.verification_evidence_ref)

    @property
    def claims_hostile_code_containment(self) -> bool:
        """True only for a profile that explicitly claims all hostile boundaries."""
        return (
            self.module_code_trust_class is ModuleCodeTrustClass.HOSTILE
            and self.filesystem_enforcement_claim
            is not BoundaryEnforcementClaim.UNRESTRICTED
            and self.network_enforcement_claim
            is not BoundaryEnforcementClaim.UNRESTRICTED
            and self.process_descendant_containment_claim
            is ProcessDescendantContainmentClaim.ENFORCED
            and self.credential_exposure_claim
            is not CredentialExposureClaim.NOT_ISOLATED
            and self.raw_os_api_access_claim is not RawOSAPIAccessClaim.UNRESTRICTED
        )


def _require_nonempty(field_name: str, value: object) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_exact_enum(field_name: str, value: object, enum_type: type[Enum]) -> None:
    if type(value) is not enum_type:
        raise ValueError(f"{field_name} must be an explicit {enum_type.__name__} value")


def _require_string_tuple(field_name: str, value: object) -> None:
    if type(value) is not tuple:
        raise ValueError(f"{field_name} must be a tuple")
    if any(type(item) is not str or not item.strip() for item in value):
        raise ValueError(f"{field_name} entries must be non-empty strings")


def _require_nonempty_tuple(field_name: str, value: object) -> None:
    _require_string_tuple(field_name, value)
    if not value:
        raise ValueError(f"{field_name} must contain at least one explicit assumption")


TRUSTED_SAME_PROCESS_ISOLATION_PROFILE = IsolationProfile(
    profile_ref="isolation-profile:trusted-same-process@1",
    module_code_trust_class=ModuleCodeTrustClass.TRUSTED_BUILTIN,
    filesystem_enforcement_claim=BoundaryEnforcementClaim.UNRESTRICTED,
    network_enforcement_claim=BoundaryEnforcementClaim.UNRESTRICTED,
    process_descendant_containment_claim=ProcessDescendantContainmentClaim.NOT_ENFORCED,
    credential_exposure_claim=CredentialExposureClaim.NOT_ISOLATED,
    raw_os_api_access_claim=RawOSAPIAccessClaim.UNRESTRICTED,
    host_escape_assumptions=(
        "module code is trusted and executes inside the Nyron host process",
        "no hostile-code containment boundary is enforced by this profile",
    ),
    supported_adapter_boundaries=("TRUSTED_IN_PROCESS_MODULE_HOST",),
    verification_evidence_ref=(
        "tests/kernel/test_isolation_profile_trusted_host.py"
        "::TrustedSameProcessIsolationProfileTest"
    ),
)
