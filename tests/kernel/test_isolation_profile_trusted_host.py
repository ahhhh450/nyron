"""Focused validation for NYRON-T-20260827-138 IsolationProfile foundation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import unittest

from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.host import (
    TRUSTED_SAME_PROCESS_ISOLATION_PROFILE,
    BoundaryEnforcementClaim,
    CredentialExposureClaim,
    IsolationProfile,
    ModuleCodeTrustClass,
    ProcessDescendantContainmentClaim,
    RawOSAPIAccessClaim,
    TrustedModuleHost,
)
from nyron_kernel.store import SQLiteStore


class TrustedSameProcessIsolationProfileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.host = TrustedModuleHost(ModuleRegistry(self.store))

    def tearDown(self) -> None:
        self.store.close()

    def test_host_exposes_exact_builtin_profile(self) -> None:
        self.assertIs(
            TRUSTED_SAME_PROCESS_ISOLATION_PROFILE,
            self.host.isolation_profile,
        )

    def test_profile_truthfully_disclaims_unimplemented_isolation(self) -> None:
        profile = self.host.isolation_profile

        self.assertIs(ModuleCodeTrustClass.TRUSTED_BUILTIN, profile.module_code_trust_class)
        self.assertIs(BoundaryEnforcementClaim.UNRESTRICTED, profile.filesystem_enforcement_claim)
        self.assertIs(BoundaryEnforcementClaim.UNRESTRICTED, profile.network_enforcement_claim)
        self.assertIs(
            ProcessDescendantContainmentClaim.NOT_ENFORCED,
            profile.process_descendant_containment_claim,
        )
        self.assertIs(CredentialExposureClaim.NOT_ISOLATED, profile.credential_exposure_claim)
        self.assertIs(RawOSAPIAccessClaim.UNRESTRICTED, profile.raw_os_api_access_claim)
        self.assertFalse(profile.claims_hostile_code_containment)
        self.assertIn("no hostile-code containment", " ".join(profile.host_escape_assumptions))

    def test_profile_value_is_immutable_and_deterministic(self) -> None:
        profile = self.host.isolation_profile
        self.assertEqual(profile, TRUSTED_SAME_PROCESS_ISOLATION_PROFILE)
        self.assertEqual(hash(profile), hash(TRUSTED_SAME_PROCESS_ISOLATION_PROFILE))
        with self.assertRaises(FrozenInstanceError):
            profile.profile_ref = "changed"  # type: ignore[misc]

    def test_malformed_claims_fail_closed(self) -> None:
        valid = TRUSTED_SAME_PROCESS_ISOLATION_PROFILE
        malformed = (
            {"profile_ref": ""},
            {"module_code_trust_class": "TRUSTED_BUILTIN"},
            {"filesystem_enforcement_claim": "UNRESTRICTED"},
            {"host_escape_assumptions": ()},
            {"supported_adapter_boundaries": ("",)},
            {"verification_evidence_ref": "   "},
        )
        for changes in malformed:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    replace(valid, **changes)

    def test_explicit_hostile_profile_requires_all_enforcement_claims(self) -> None:
        hostile = IsolationProfile(
            profile_ref="isolation-profile:test-hostile@1",
            module_code_trust_class=ModuleCodeTrustClass.HOSTILE,
            filesystem_enforcement_claim=BoundaryEnforcementClaim.MEDIATED,
            network_enforcement_claim=BoundaryEnforcementClaim.OS_RESTRICTED,
            process_descendant_containment_claim=ProcessDescendantContainmentClaim.ENFORCED,
            credential_exposure_claim=CredentialExposureClaim.BROKER_MEDIATED,
            raw_os_api_access_claim=RawOSAPIAccessClaim.DENIED,
            host_escape_assumptions=("test-only enforced boundary claims",),
            supported_adapter_boundaries=(),
            verification_evidence_ref="test:test-only",
        )
        self.assertTrue(hostile.claims_hostile_code_containment)
        self.assertFalse(
            replace(
                hostile,
                process_descendant_containment_claim=ProcessDescendantContainmentClaim.NOT_ENFORCED,
            ).claims_hostile_code_containment
        )


if __name__ == "__main__":
    unittest.main()
