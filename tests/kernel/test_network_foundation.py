"""Adversarial tests for the admission-only network boundary foundation."""

from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from nyron_kernel.capability import CapabilityTypeRegistry
from nyron_kernel.execution import AttemptAuthority
from nyron_kernel.host import (
    EffectiveDestination,
    NetworkAdmissionRequest,
    NetworkBoundaryError,
    ProxyHop,
    RequestedDestination,
    SelectedPeer,
    SimulatedNetworkBoundaryBroker,
    canonicalize_host,
    canonicalize_ip,
    classify_ip,
    register_network_access_capability,
)
from nyron_kernel.store import SQLiteStore


class NetworkFoundationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "network.db"
        self.store = SQLiteStore(self.db)
        self.store.create_effect_schema()
        register_network_access_capability(CapabilityTypeRegistry(self.store))
        self.authority = AttemptAuthority(
            "execution:network", "activation:network", "run:network", 1,
            "fence:network", 1,
        )
        self.scope = self._scope()
        self._seed()
        self.broker = SimulatedNetworkBoundaryBroker(self.store, lambda: 100)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    @staticmethod
    def _requested(**changes):
        values = dict(scheme="HTTPS", host="API.Example.COM.", port=None,
                      operation_class="MODEL_INVOKE",
                      path_restriction_ref="path:invoke")
        values.update(changes)
        return RequestedDestination(**values)

    def _effective(self, requested=None, **changes):
        requested = requested or self._requested()
        values = dict(requested=requested,
                      selected_peer=SelectedPeer("93.184.216.34", 443, "connection:1"),
                      connection_origin=requested)
        values.update(changes)
        return EffectiveDestination(**values)

    def _request(self, effective=None, **changes):
        values = dict(operation_ref="effect:network", dispatch_admission_ref="dispatch:network",
                      authority=self.authority, capability_grant_ref="grant:network",
                      resource_lease_ref="lease:network",
                      effective_destination=effective or self._effective())
        values.update(changes)
        return NetworkAdmissionRequest(**values)

    @staticmethod
    def _scope():
        return {
            "destination": {
                "schemes": ["https"], "hosts": ["api.example.com"], "ports": [443],
                "ip_networks": ["93.184.216.0/24"], "allow_special_ip_classes": [],
                "operation_classes": ["MODEL_INVOKE"],
                "path_restriction_refs": ["path:invoke"],
            }
        }

    def test_canonicalization_idna_ipv4_ipv6_and_mapped_ipv6(self):
        self.assertEqual("xn--bcher-kva.example", canonicalize_host("BÜCHER.Example."))
        self.assertEqual("2001:db8::1", canonicalize_ip("2001:0db8::1"))
        self.assertEqual("127.0.0.1", canonicalize_ip("::ffff:127.0.0.1"))
        self.assertEqual("LOOPBACK", classify_ip("::ffff:127.0.0.1"))
        self.assertEqual(443, self._requested().port)
        for host in (" api.example.com", "api..example.com", "api@example.com", "*.example.com"):
            with self.assertRaises(NetworkBoundaryError):
                RequestedDestination("https", host, 443, "MODEL_INVOKE", "path:invoke")

    def test_wildcard_respects_label_boundary(self):
        scope = self._scope()
        scope["destination"]["hosts"] = ["*.example.com"]
        self._replace_scope(scope)
        self.assertTrue(self.broker.admit(self._request()).simulated)
        for host in ("example.com", "notexample.com"):
            with self.assertRaises(NetworkBoundaryError):
                self.broker.admit(self._request(self._effective(self._requested(host=host))))

    def test_exact_requested_and_effective_identity_is_admitted_without_io(self):
        admitted = self.broker.admit(self._request())
        self.assertTrue(admitted.simulated)
        self.assertEqual("api.example.com", admitted.requested_destination.host)
        self.assertEqual("93.184.216.34", admitted.selected_peer.ip)

    def test_host_authority_does_not_authorize_arbitrary_selected_peer(self):
        effective = self._effective(selected_peer=SelectedPeer("1.1.1.1", 443, "connection:2"))
        with self.assertRaisesRegex(NetworkBoundaryError, "NETWORK_PEER_NOT_AUTHORIZED"):
            self.broker.admit(self._request(effective))

    def test_selected_peer_cannot_rescue_wrong_host_scheme_or_port(self):
        for requested in (
            self._requested(host="other.example.com"),
            self._requested(scheme="http", port=443),
            self._requested(port=8443),
        ):
            effective = self._effective(
                requested,
                selected_peer=SelectedPeer("93.184.216.34", requested.port, "connection:mismatch"),
            )
            with self.assertRaises(NetworkBoundaryError):
                self.broker.admit(self._request(effective))

    def test_same_host_selected_peer_is_rechecked_for_rebinding(self):
        self.assertTrue(self.broker.admit(self._request()).simulated)
        rebound = self._effective(
            selected_peer=SelectedPeer("93.184.217.34", 443, "connection:rebound")
        )
        with self.assertRaisesRegex(NetworkBoundaryError, "NETWORK_PEER_NOT_AUTHORIZED"):
            self.broker.admit(self._request(rebound))

    def test_special_ranges_and_mapped_bypass_fail_closed(self):
        scope = self._scope()
        scope["destination"]["ip_networks"] = ["0.0.0.0/0", "::/0"]
        self._replace_scope(scope)
        for peer in ("127.0.0.1", "10.0.0.1", "169.254.1.1", "::1", "::ffff:10.0.0.1"):
            effective = self._effective(selected_peer=SelectedPeer(peer, 443, "connection:special"))
            with self.assertRaisesRegex(NetworkBoundaryError, "NETWORK_SPECIAL_ADDRESS_DENIED"):
                self.broker.admit(self._request(effective))

    def test_special_range_requires_both_cidr_and_explicit_class(self):
        scope = self._scope()
        scope["destination"]["ip_networks"] = ["10.0.0.0/8"]
        scope["destination"]["allow_special_ip_classes"] = ["PRIVATE"]
        self._replace_scope(scope)
        effective = self._effective(selected_peer=SelectedPeer("10.1.2.3", 443, "connection:private"))
        self.assertTrue(self.broker.admit(self._request(effective)).simulated)

    def test_redirect_is_a_fresh_requested_identity_and_must_be_authorized(self):
        redirected = self._requested(host="redirect.example.net", redirect_hop=1)
        with self.assertRaisesRegex(NetworkBoundaryError, "NETWORK_DESTINATION_NOT_AUTHORIZED"):
            self.broker.admit(self._request(self._effective(redirected)))

    def test_proxy_endpoint_and_ultimate_destination_are_independently_authorized(self):
        proxy_request = RequestedDestination("https", "proxy.example.com", 8443,
                                             "CONNECT", "path:proxy")
        proxy = ProxyHop("proxy:corp", proxy_request,
                         SelectedPeer("198.51.100.2", 8443, "connection:proxy"))
        with self.assertRaisesRegex(NetworkBoundaryError, "NETWORK_PROXY_NOT_AUTHORIZED"):
            self.broker.admit(self._request(self._effective(proxy_hop=proxy)))
        scope = self._scope()
        scope["proxies"] = {"proxy:corp": {
            "schemes": ["https"], "hosts": ["proxy.example.com"], "ports": [8443],
            "ip_networks": ["198.51.100.0/24"], "allow_special_ip_classes": ["PRIVATE"],
            "operation_classes": ["CONNECT"], "path_restriction_refs": ["path:proxy"],
        }}
        self._replace_scope(scope)
        self.assertTrue(self.broker.admit(self._request(self._effective(proxy_hop=proxy))).simulated)

    def test_connection_reuse_cannot_change_logical_origin(self):
        other = self._requested(host="other.example.com")
        effective = self._effective(reused_connection=True, connection_origin=other)
        with self.assertRaisesRegex(NetworkBoundaryError, "NETWORK_CONNECTION_ORIGIN_MISMATCH"):
            self.broker.admit(self._request(effective))

    def test_boundary_revalidates_prepared_effect(self):
        self.broker.admit(self._request())
        self.store.connection.execute(
            "UPDATE effect_operations SET state='FENCED', fence_evidence_json='{}' WHERE operation_ref='effect:network'"
        )
        with self.assertRaisesRegex(NetworkBoundaryError, "NETWORK_EFFECT_NOT_PREPARED"):
            self.broker.admit(self._request())

    def test_boundary_revalidates_grant_lease_and_attempt_fencing(self):
        self.store.connection.execute(
            "UPDATE capability_grants SET state='REVOKED' WHERE grant_ref='grant:network'"
        )
        with self.assertRaisesRegex(NetworkBoundaryError, "NETWORK_GRANT_NOT_ACTIVE"):
            self.broker.admit(self._request())

    def test_boundary_revalidates_lease(self):
        self.store.connection.execute(
            "UPDATE resource_leases SET state='REVOKE_REQUESTED' WHERE lease_ref='lease:network'"
        )
        with self.assertRaisesRegex(NetworkBoundaryError, "NETWORK_LEASE_NOT_ACTIVE"):
            self.broker.admit(self._request())

    def test_boundary_revalidates_attempt_fencing(self):
        self.store.connection.execute(
            "UPDATE run_attempts SET state='REPLACED' WHERE run_ref='run:network' AND attempt_seq=1"
        )
        with self.assertRaisesRegex(NetworkBoundaryError, "NETWORK_ATTEMPT_NOT_CURRENT"):
            self.broker.admit(self._request())

    def test_mismatched_fencing_generation_grant_and_lease_fail(self):
        stale = replace(self.authority, fencing_generation=2)
        with self.assertRaises(NetworkBoundaryError):
            self.broker.admit(self._request(authority=stale))
        with self.assertRaises(NetworkBoundaryError):
            self.broker.admit(self._request(capability_grant_ref="grant:wrong"))
        with self.assertRaises(NetworkBoundaryError):
            self.broker.admit(self._request(resource_lease_ref="lease:wrong"))

    def test_wrong_grant_scope_and_credential_shaped_objects_cannot_authorize(self):
        class ResolvedCredentialHandle:
            pass
        with self.assertRaises(NetworkBoundaryError):
            NetworkAdmissionRequest("effect:network", "dispatch:network", self.authority,
                                    "grant:network", "lease:network", ResolvedCredentialHandle())
        with self.assertRaises(NetworkBoundaryError):
            RequestedDestination("https", ResolvedCredentialHandle(), 443, "MODEL_INVOKE", "path:invoke")
        self._replace_scope({"destination": {}})
        with self.assertRaisesRegex(NetworkBoundaryError, "NETWORK_SCOPE_INVALID"):
            self.broker.admit(self._request())

    def test_restart_replay_conflict_and_fenced_are_fail_closed(self):
        before = self.store.connection.execute(
            "SELECT historical_outcome, historical_outcome_evidence_json FROM effect_operations WHERE operation_ref='effect:network'"
        ).fetchone()
        expected = self.broker.admit(self._request())
        after = self.store.connection.execute(
            "SELECT historical_outcome, historical_outcome_evidence_json FROM effect_operations WHERE operation_ref='effect:network'"
        ).fetchone()
        self.assertEqual(tuple(before), tuple(after))
        self.store.close()
        self.store = SQLiteStore(self.db)
        self.broker = SimulatedNetworkBoundaryBroker(self.store, lambda: 100)
        self.assertEqual(expected, self.broker.admit(self._request()))
        with self.assertRaises(NetworkBoundaryError):
            self.broker.admit(self._request(self._effective(self._requested(host="other.example"))))
        self.store.connection.execute(
            "UPDATE effect_operations SET state='FENCED', fence_evidence_json='{}' WHERE operation_ref='effect:network'"
        )
        with self.assertRaises(NetworkBoundaryError):
            self.broker.admit(self._request())

    def test_raw_scope_mutation_remains_fail_closed(self):
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "UPDATE capability_grants SET scope_json='{}' WHERE grant_ref='grant:network'"
            )

    def _replace_scope(self, scope):
        import json
        self.store.connection.execute("DROP TRIGGER capability_grant_immutable_fields")
        self.store.connection.execute(
            "UPDATE capability_grants SET scope_json=? WHERE grant_ref='grant:network'",
            (json.dumps(scope, sort_keys=True, separators=(",", ":")),),
        )
        self.store.create_capability_schema()

    def _seed(self):
        import json
        c = self.store.connection
        c.execute("INSERT INTO graph_revisions VALUES ('graph:network@1','{}',1,NULL)")
        c.execute("INSERT INTO module_instance_revisions VALUES ('module:network@1','graph:network@1','module:network','test.network','1','config@1','hash','{}','{}','[\"root\"]','accounting:network')")
        c.execute("INSERT INTO execution_admissions VALUES ('admission:network','execution:network','graph:network@1','policy@1',1,'ADMITTED')")
        c.execute("INSERT INTO workflow_executions VALUES ('execution:network','graph:network@1','admission:network','policy@1','ADMITTED')")
        c.execute("INSERT INTO activations VALUES ('activation:network','execution:network','graph:network@1','module:network@1','delivery:network','[]','accounting:network','event:activation:network')")
        c.execute("INSERT INTO activation_created_events VALUES ('event:activation:network','activation:network','ActivationCreated')")
        c.execute("INSERT INTO runs VALUES ('run:network','activation:network','execution:network',1,1,'RUNNING',NULL,NULL)")
        c.execute("INSERT INTO run_attempts VALUES ('run:network',1,'fence:network','ACTIVE')")
        c.execute("INSERT INTO capability_grants VALUES ('grant:network','nyron.kernel.network-access','1','execution:network','activation:network','run:network',1,'fence:network',1,?,'test',NULL,1,NULL,NULL,'ACTIVE')", (json.dumps(self.scope, sort_keys=True, separators=(",", ":")),))
        c.execute("INSERT INTO resources VALUES ('resource:network','NETWORK_ENDPOINT','network-owner','{}','AVAILABLE','network-endpoint:test','{}')")
        c.execute("INSERT INTO resource_leases VALUES ('lease:network','resource:network','network-broker','execution:network','activation:network','run:network',1,'fence:network',1,1,NULL,'ACTIVE')")
        c.execute("INSERT INTO effect_operations(operation_ref,effect_class,execution_ref,activation_ref,run_ref,attempt_seq,fencing_token,fencing_generation,capability_grant_ref,resource_ref,resource_lease_ref,target_ref,payload_json,payload_hash,caused_by_ref,state,prepared_at,dispatch_admission_ref,dispatch_admitted_at,completion_evidence_json,fence_evidence_json,historical_outcome,historical_outcome_evidence_json) VALUES ('effect:network','MODEL_INVOKE','execution:network','activation:network','run:network',1,'fence:network',1,'grant:network','resource:network','lease:network','network:target','{}','sha256:network','event:network','PREPARED',1,'dispatch:network',1,NULL,NULL,'UNKNOWN',NULL)")


if __name__ == "__main__":
    unittest.main()
