"""Pure, fail-closed network-boundary admission foundations.

This module performs no DNS resolution and no network I/O.  It only validates
an already selected peer against immutable requested/effective identities and
the current owner-local authority rows at the simulated dispatch boundary.
"""

from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nyron_kernel.store import SQLiteStore

if TYPE_CHECKING:
    from nyron_kernel.capability import CapabilityTypeDefinition, CapabilityTypeRegistry
    from nyron_kernel.execution import AttemptAuthority


NETWORK_ACCESS_TYPE_REF = "nyron.kernel.network-access"
NETWORK_ACCESS_VERSION = "1"
NETWORK_ACCESS_SCOPE_SCHEMA_REF = "nyron.schema.network-access-scope@1"
_SPECIAL_CLASSES = frozenset(
    {"LOOPBACK", "PRIVATE", "LINK_LOCAL", "RESERVED", "UNSPECIFIED", "MULTICAST"}
)
_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class NetworkBoundaryError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def register_network_access_capability(
    registry: CapabilityTypeRegistry,
) -> CapabilityTypeDefinition:
    """Register only the versioned NETWORK_ACCESS scope vocabulary."""

    from nyron_kernel.capability import CapabilityTypeDefinition

    return registry.register(
        CapabilityTypeDefinition(
            capability_type_ref=NETWORK_ACCESS_TYPE_REF,
            version=NETWORK_ACCESS_VERSION,
            scope_schema_ref=NETWORK_ACCESS_SCOPE_SCHEMA_REF,
            operation_schema_ref=None,
            compatible_effect_classes=(),
            metadata={"authority": "network-boundary", "io": "none"},
        )
    )


def canonicalize_host(value: str, *, allow_wildcard: bool = False) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise NetworkBoundaryError("NETWORK_HOST_INVALID")
    wildcard = allow_wildcard and value.startswith("*.")
    raw = value[2:] if wildcard else value
    if "*" in raw or any(char in raw for char in "/\\?#@"):
        raise NetworkBoundaryError("NETWORK_HOST_INVALID")
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    try:
        address = ipaddress.ip_address(raw)
    except ValueError:
        raw = raw[:-1] if raw.endswith(".") else raw
        try:
            host = raw.encode("idna").decode("ascii").lower()
        except (UnicodeError, ValueError) as error:
            raise NetworkBoundaryError("NETWORK_HOST_INVALID") from error
        labels = host.split(".")
        if (
            len(host) > 253
            or all(label.isdigit() for label in labels)
            or any(not _LABEL.fullmatch(label) for label in labels)
        ):
            raise NetworkBoundaryError("NETWORK_HOST_INVALID")
    else:
        host = canonicalize_ip(address)
        if wildcard:
            raise NetworkBoundaryError("NETWORK_HOST_INVALID")
    return f"*.{host}" if wildcard else host


def canonicalize_ip(value: str | ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    try:
        address = value if isinstance(value, (ipaddress.IPv4Address, ipaddress.IPv6Address)) else ipaddress.ip_address(value)
    except (TypeError, ValueError) as error:
        raise NetworkBoundaryError("NETWORK_PEER_IP_INVALID") from error
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return address.compressed.lower()


def classify_ip(value: str) -> str:
    address = ipaddress.ip_address(canonicalize_ip(value))
    if address.is_unspecified:
        return "UNSPECIFIED"
    if address.is_loopback:
        return "LOOPBACK"
    if address.is_link_local:
        return "LINK_LOCAL"
    if address.is_multicast:
        return "MULTICAST"
    if address.is_reserved:
        return "RESERVED"
    if address.is_private:
        return "PRIVATE"
    if not address.is_global:
        return "RESERVED"
    return "GLOBAL"


def normalize_port(value: int | None, scheme: str) -> int:
    if value is None:
        defaults = {"http": 80, "https": 443}
        if scheme not in defaults:
            raise NetworkBoundaryError("NETWORK_PORT_REQUIRED")
        return defaults[scheme]
    if type(value) is not int or not 1 <= value <= 65535:
        raise NetworkBoundaryError("NETWORK_PORT_INVALID")
    return value


@dataclass(frozen=True)
class RequestedDestination:
    scheme: str
    host: str
    port: int | None
    operation_class: str
    path_restriction_ref: str
    redirect_hop: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.scheme, str):
            raise NetworkBoundaryError("NETWORK_REQUESTED_DESTINATION_INVALID")
        scheme = self.scheme.lower()
        if scheme not in {"http", "https", "tcp"}:
            raise NetworkBoundaryError("NETWORK_SCHEME_UNSUPPORTED")
        for value in (self.operation_class, self.path_restriction_ref):
            if not isinstance(value, str) or not value:
                raise NetworkBoundaryError("NETWORK_REQUESTED_DESTINATION_INVALID")
        if type(self.redirect_hop) is not int or self.redirect_hop < 0:
            raise NetworkBoundaryError("NETWORK_REDIRECT_HOP_INVALID")
        object.__setattr__(self, "scheme", scheme)
        object.__setattr__(self, "host", canonicalize_host(self.host))
        object.__setattr__(self, "port", normalize_port(self.port, scheme))


@dataclass(frozen=True)
class SelectedPeer:
    ip: str
    port: int
    connection_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.connection_ref, str) or not self.connection_ref:
            raise NetworkBoundaryError("NETWORK_CONNECTION_IDENTITY_INVALID")
        object.__setattr__(self, "ip", canonicalize_ip(self.ip))
        object.__setattr__(self, "port", normalize_port(self.port, "tcp"))


@dataclass(frozen=True)
class ProxyHop:
    proxy_ref: str
    requested: RequestedDestination
    selected_peer: SelectedPeer

    def __post_init__(self) -> None:
        if (
            not isinstance(self.proxy_ref, str)
            or not self.proxy_ref
            or type(self.requested) is not RequestedDestination
            or type(self.selected_peer) is not SelectedPeer
        ):
            raise NetworkBoundaryError("NETWORK_PROXY_IDENTITY_INVALID")


@dataclass(frozen=True)
class EffectiveDestination:
    requested: RequestedDestination
    selected_peer: SelectedPeer
    connection_origin: RequestedDestination
    reused_connection: bool = False
    proxy_hop: ProxyHop | None = None

    def __post_init__(self) -> None:
        if (
            type(self.requested) is not RequestedDestination
            or type(self.selected_peer) is not SelectedPeer
            or type(self.connection_origin) is not RequestedDestination
            or type(self.reused_connection) is not bool
            or (self.proxy_hop is not None and type(self.proxy_hop) is not ProxyHop)
        ):
            raise NetworkBoundaryError("NETWORK_EFFECTIVE_DESTINATION_INVALID")


@dataclass(frozen=True)
class NetworkAdmissionRequest:
    operation_ref: str
    dispatch_admission_ref: str
    authority: Any
    capability_grant_ref: str
    resource_lease_ref: str
    effective_destination: EffectiveDestination

    def __post_init__(self) -> None:
        from nyron_kernel.execution import AttemptAuthority

        values = (
            self.operation_ref,
            self.dispatch_admission_ref,
            self.capability_grant_ref,
            self.resource_lease_ref,
        )
        if (
            any(not isinstance(value, str) or not value for value in values)
            or type(self.authority) is not AttemptAuthority
            or type(self.effective_destination) is not EffectiveDestination
        ):
            raise NetworkBoundaryError("NETWORK_ADMISSION_REQUEST_INVALID")


@dataclass(frozen=True)
class NetworkAdmission:
    operation_ref: str
    dispatch_admission_ref: str
    requested_destination: RequestedDestination
    selected_peer: SelectedPeer
    simulated: bool = True


class SimulatedNetworkBoundaryBroker:
    """Admission-only broker; success is not evidence that any I/O occurred."""

    def __init__(self, store: SQLiteStore, clock) -> None:
        self._store = store
        self._clock = clock

    def admit(self, request: NetworkAdmissionRequest) -> NetworkAdmission:
        if type(request) is not NetworkAdmissionRequest:
            raise NetworkBoundaryError("NETWORK_ADMISSION_REQUEST_INVALID")
        now = self._clock()
        if type(now) is not int:
            raise NetworkBoundaryError("NETWORK_CLOCK_INVALID")
        effect = self._store.connection.execute(
            "SELECT * FROM effect_operations WHERE operation_ref=?", (request.operation_ref,)
        ).fetchone()
        if effect is None or effect["state"] != "PREPARED":
            raise NetworkBoundaryError("NETWORK_EFFECT_NOT_PREPARED")
        if effect["dispatch_admission_ref"] != request.dispatch_admission_ref:
            raise NetworkBoundaryError("NETWORK_EFFECT_ADMISSION_MISMATCH")
        expected = (
            request.authority.execution_ref,
            request.authority.activation_ref,
            request.authority.run_ref,
            request.authority.attempt_seq,
            request.authority.fencing_token,
            request.authority.fencing_generation,
            request.capability_grant_ref,
            request.resource_lease_ref,
        )
        actual = tuple(effect[key] for key in (
            "execution_ref", "activation_ref", "run_ref", "attempt_seq",
            "fencing_token", "fencing_generation", "capability_grant_ref",
            "resource_lease_ref",
        ))
        if actual != expected:
            raise NetworkBoundaryError("NETWORK_EFFECT_AUTHORITY_MISMATCH")
        self._require_current_authority(request, now)
        scope = self._grant_scope(request.capability_grant_ref)
        effective = request.effective_destination
        if effective.connection_origin != effective.requested:
            raise NetworkBoundaryError("NETWORK_CONNECTION_ORIGIN_MISMATCH")
        self._authorize_destination(effective.requested, effective.selected_peer, scope["destination"])
        if effective.proxy_hop is not None:
            proxy_scopes = scope.get("proxies")
            if not isinstance(proxy_scopes, dict) or effective.proxy_hop.proxy_ref not in proxy_scopes:
                raise NetworkBoundaryError("NETWORK_PROXY_NOT_AUTHORIZED")
            self._authorize_destination(
                effective.proxy_hop.requested,
                effective.proxy_hop.selected_peer,
                proxy_scopes[effective.proxy_hop.proxy_ref],
            )
        return NetworkAdmission(
            request.operation_ref,
            request.dispatch_admission_ref,
            effective.requested,
            effective.selected_peer,
        )

    def _require_current_authority(self, request: NetworkAdmissionRequest, now: int) -> None:
        current = self._store.connection.execute(
            "SELECT attempt.*, run.execution_ref, run.activation_ref, "
            "run.fencing_generation AS current_generation "
            "FROM runs AS run JOIN run_attempts AS attempt "
            "ON attempt.run_ref=run.run_ref AND attempt.attempt_seq=run.current_attempt_seq "
            "WHERE run.run_ref=?", (request.authority.run_ref,),
        ).fetchone()
        if current is None or (
            current["state"], current["execution_ref"], current["activation_ref"],
            current["attempt_seq"], current["fencing_token"], current["current_generation"]
        ) != (
            "ACTIVE", request.authority.execution_ref, request.authority.activation_ref,
            request.authority.attempt_seq, request.authority.fencing_token,
            request.authority.fencing_generation,
        ):
            raise NetworkBoundaryError("NETWORK_ATTEMPT_NOT_CURRENT")
        grant = self._store.connection.execute(
            "SELECT * FROM capability_grants WHERE grant_ref=?", (request.capability_grant_ref,)
        ).fetchone()
        if grant is None or grant["state"] != "ACTIVE" or (
            grant["not_before"] is not None and now < grant["not_before"]
        ) or (grant["expires_at"] is not None and now >= grant["expires_at"]):
            raise NetworkBoundaryError("NETWORK_GRANT_NOT_ACTIVE")
        lease = self._store.connection.execute(
            "SELECT * FROM resource_leases WHERE lease_ref=?", (request.resource_lease_ref,)
        ).fetchone()
        if lease is None or lease["state"] != "ACTIVE" or (
            lease["expires_at"] is not None and now >= lease["expires_at"]
        ):
            raise NetworkBoundaryError("NETWORK_LEASE_NOT_ACTIVE")
        authority_tuple = (
            request.authority.execution_ref, request.authority.activation_ref,
            request.authority.run_ref, request.authority.attempt_seq,
            request.authority.fencing_token, request.authority.fencing_generation,
        )
        for row, keys in ((grant, ("execution_ref", "activation_ref", "run_ref", "attempt_seq", "fencing_token", "fencing_generation")), (lease, ("execution_ref", "activation_ref", "run_ref", "attempt_seq", "fencing_token", "fencing_generation"))):
            if tuple(row[key] for key in keys) != authority_tuple:
                raise NetworkBoundaryError("NETWORK_AUTHORITY_NON_TRANSFERABLE")
        if grant["capability_type_ref"] != NETWORK_ACCESS_TYPE_REF or grant["capability_type_version"] != NETWORK_ACCESS_VERSION:
            raise NetworkBoundaryError("NETWORK_ACCESS_GRANT_REQUIRED")

    def _grant_scope(self, grant_ref: str) -> dict[str, object]:
        row = self._store.connection.execute(
            "SELECT scope_json FROM capability_grants WHERE grant_ref=?", (grant_ref,)
        ).fetchone()
        try:
            scope = json.loads(row["scope_json"])
        except (TypeError, json.JSONDecodeError) as error:
            raise NetworkBoundaryError("NETWORK_SCOPE_INVALID") from error
        if not isinstance(scope, dict) or set(scope) - {"destination", "proxies"} or "destination" not in scope:
            raise NetworkBoundaryError("NETWORK_SCOPE_INVALID")
        return scope

    @staticmethod
    def _authorize_destination(requested: RequestedDestination, peer: SelectedPeer, scope: object) -> None:
        if not isinstance(scope, dict) or set(scope) != {"schemes", "hosts", "ports", "ip_networks", "allow_special_ip_classes", "operation_classes", "path_restriction_refs"}:
            raise NetworkBoundaryError("NETWORK_SCOPE_INVALID")
        values = tuple(scope.values())
        if any(not isinstance(value, list) for value in values):
            raise NetworkBoundaryError("NETWORK_SCOPE_INVALID")
        if (
            any(not isinstance(value, str) or not value for key in (
                "schemes", "hosts", "ip_networks", "allow_special_ip_classes",
                "operation_classes", "path_restriction_refs",
            ) for value in scope[key])
            or any(type(value) is not int for value in scope["ports"])
        ):
            raise NetworkBoundaryError("NETWORK_SCOPE_INVALID")
        try:
            schemes = {value.lower() for value in scope["schemes"] if isinstance(value, str)}
            hosts = [canonicalize_host(value, allow_wildcard=True) for value in scope["hosts"]]
            ports = set(scope["ports"])
            networks = [ipaddress.ip_network(value, strict=True) for value in scope["ip_networks"]]
            special = set(scope["allow_special_ip_classes"])
            operations = set(scope["operation_classes"])
            paths = set(scope["path_restriction_refs"])
        except (TypeError, ValueError, NetworkBoundaryError) as error:
            raise NetworkBoundaryError("NETWORK_SCOPE_INVALID") from error
        if any(type(port) is not int or not 1 <= port <= 65535 for port in ports) or not special <= _SPECIAL_CLASSES:
            raise NetworkBoundaryError("NETWORK_SCOPE_INVALID")
        host_allowed = any(
            requested.host == pattern
            or (pattern.startswith("*.") and requested.host.endswith(pattern[1:]) and requested.host != pattern[2:])
            for pattern in hosts
        )
        if not host_allowed or requested.scheme not in schemes or requested.port not in ports or requested.operation_class not in operations or requested.path_restriction_ref not in paths:
            raise NetworkBoundaryError("NETWORK_DESTINATION_NOT_AUTHORIZED")
        if peer.port != requested.port:
            raise NetworkBoundaryError("NETWORK_EFFECTIVE_PORT_MISMATCH")
        address = ipaddress.ip_address(peer.ip)
        if not any(address.version == network.version and address in network for network in networks):
            raise NetworkBoundaryError("NETWORK_PEER_NOT_AUTHORIZED")
        classification = classify_ip(peer.ip)
        if classification != "GLOBAL" and classification not in special:
            raise NetworkBoundaryError("NETWORK_SPECIAL_ADDRESS_DENIED")
