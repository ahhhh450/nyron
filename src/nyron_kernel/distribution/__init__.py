"""Distribution identity and exact-resolution authority."""

from nyron_kernel.distribution.authority import (
    DistributionAuthority,
    DistributionError,
)
from nyron_kernel.distribution.models import (
    ModuleVersion,
    PackageSourceEvidence,
    PackageVersion,
    ResolvedModule,
)

__all__ = [
    "DistributionAuthority",
    "DistributionError",
    "ModuleVersion",
    "PackageSourceEvidence",
    "PackageVersion",
    "ResolvedModule",
]
