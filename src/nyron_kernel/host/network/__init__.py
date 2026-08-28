"""Public network admission foundation surface."""

from .foundation import (
    NETWORK_ACCESS_SCOPE_SCHEMA_REF,
    NETWORK_ACCESS_TYPE_REF,
    NETWORK_ACCESS_VERSION,
    EffectiveDestination,
    NetworkAdmission,
    NetworkAdmissionRequest,
    NetworkBoundaryError,
    ProxyHop,
    RequestedDestination,
    SelectedPeer,
    SimulatedNetworkBoundaryBroker,
    canonicalize_host,
    canonicalize_ip,
    classify_ip,
    normalize_port,
    register_network_access_capability,
)

__all__ = [name for name in globals() if not name.startswith("_")]
