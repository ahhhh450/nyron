"""TRACK_C_TASK_003 — fail-closed regression coverage for the frozen Resource module.

Complements tests/kernel/test_resource_foundation.py by exercising the
validation, clock, idempotency, advisory, destroy and raw-schema-constraint
branches that the foundation acceptance suite does not already cover.

This file adds tests only; it must not modify any production source.  The DB is
an in-memory SQLiteStore while the ResourceManager managed root is a real
temporary directory (file-backed SQLite is prohibited in this sandbox).
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path

from nyron_kernel.execution import (
    AttemptAuthority,
    RunRepository,
    RuntimeAuthorityResolver,
)
from nyron_kernel.resource import (
    ResourceError,
    ResourceManager,
    ResourceRequest,
)
from nyron_kernel.store import SQLiteStore


GRAPH = "graph:resource@1"
MODULE = "module-instance-revision:resource@1"
EXECUTION = "execution:resource/1"
ACTIVATION = "activation:resource/1"
RUN = "run:resource/1"
RESOURCE = "resource:workspace/1"


def _fake_authority() -> AttemptAuthority:
    """A structurally valid AttemptAuthority that is not necessarily current."""
    return AttemptAuthority(
        execution_ref="execution:fake",
        activation_ref="activation:fake",
        run_ref="run:fake",
        attempt_seq=1,
        fencing_token="fencing:fake",
        fencing_generation=1,
    )


class TrackC003ResourceRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        # tempfile.TemporaryDirectory()/mkdtemp create the directory with mode
        # 0o700, which this sandbox then enforces as non-traversable for the
        # child process.  Create the base directory with the default mode
        # instead so the managed root stays a normal writable directory.
        self.temp_dir = Path(tempfile.gettempdir()) / f"tct003-{uuid.uuid4().hex}"
        os.mkdir(self.temp_dir)
        self.managed_root = self.temp_dir / "managed-root"
        self.store = SQLiteStore()  # in-memory
        self.runtime = RuntimeAuthorityResolver(self.store)
        self.now = 100
        self.manager = self._manager()

    def tearDown(self) -> None:
        self.store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _manager(self, clock=None, crash_hook=None) -> ResourceManager:
        return ResourceManager(
            self.store,
            self.managed_root,
            self.runtime,
            clock if clock is not None else (lambda: self.now),
            crash_hook,
        )

    def _seed_runtime(self) -> AttemptAuthority:
        """Install a minimal current-attempt Runtime row and return its authority."""
        self.store.create_run_attempt_schema()
        with self.store.transaction() as connection:
            connection.execute(
                "INSERT INTO graph_revisions VALUES (?, '{}', 1, NULL)", (GRAPH,)
            )
            connection.execute(
                """
                INSERT INTO module_instance_revisions VALUES (
                    ?, ?, 'resource-test', 'test.resource', '1',
                    'config:resource@1', 'sha256:resource-config', '{}', '{}',
                    '["root"]', 'accounting:resource'
                )
                """,
                (MODULE, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO execution_admissions VALUES (
                    'admission:resource/1', ?, ?, 'policy:resource@1', 1, 'ADMITTED'
                )
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO workflow_executions VALUES (
                    ?, ?, 'admission:resource/1', 'policy:resource@1', 'ADMITTED'
                )
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO activations VALUES (
                    ?, ?, ?, ?, 'delivery:resource-trigger', '[]',
                    'accounting:resource', 'event:activation:resource/1'
                )
                """,
                (ACTIVATION, EXECUTION, GRAPH, MODULE),
            )
            connection.execute(
                "INSERT INTO activation_created_events VALUES ('event:activation:resource/1', ?, 'ActivationCreated')",
                (ACTIVATION,),
            )
        RunRepository(self.store).create_initial(
            run_ref=RUN,
            activation_ref=ACTIVATION,
            execution_ref=EXECUTION,
        )
        authority = self.runtime.resolve_current(RUN)
        assert authority is not None
        return authority

    @staticmethod
    def _request(**changes) -> ResourceRequest:
        values = {
            "resource_ref": RESOURCE,
            "resource_type": ResourceManager.RESOURCE_TYPE,
            "resource_owner_ref": "resource-manager:kernel",
            "scope": {"workspace_ref": "workspace:resource-test"},
        }
        values.update(changes)
        return ResourceRequest(**values)

    def _provision(self):
        return self.manager.provision(self._request())

    def _insert_resource(self, **overrides) -> None:
        values = {
            "resource_ref": "resource:raw",
            "resource_type": ResourceManager.RESOURCE_TYPE,
            "resource_owner_ref": "owner:raw",
            "scope_json": "{}",
            "state": "AVAILABLE",
            "external_ref": "ext:raw",
            "provenance_json": "{}",
        }
        values.update(overrides)
        self.store.connection.execute(
            """
            INSERT INTO resources(
                resource_ref, resource_type, resource_owner_ref,
                scope_json, state, external_ref, provenance_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                values["resource_ref"], values["resource_type"],
                values["resource_owner_ref"], values["scope_json"],
                values["state"], values["external_ref"], values["provenance_json"],
            ),
        )

    def _insert_lease(self, authority: AttemptAuthority, **overrides) -> None:
        values = {
            "lease_ref": "lease:raw/1",
            "resource_ref": RESOURCE,
            "lease_holder_ref": "holder:raw",
            "execution_ref": authority.execution_ref,
            "activation_ref": authority.activation_ref,
            "run_ref": authority.run_ref,
            "attempt_seq": authority.attempt_seq,
            "fencing_token": authority.fencing_token,
            "fencing_generation": authority.fencing_generation,
            "issued_at": 100,
            "expires_at": None,
            "state": "ACTIVE",
        }
        values.update(overrides)
        self.store.connection.execute(
            """
            INSERT INTO resource_leases(
                lease_ref, resource_ref, lease_holder_ref, execution_ref,
                activation_ref, run_ref, attempt_seq, fencing_token,
                fencing_generation, issued_at, expires_at, state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                values["lease_ref"], values["resource_ref"],
                values["lease_holder_ref"], values["execution_ref"],
                values["activation_ref"], values["run_ref"],
                values["attempt_seq"], values["fencing_token"],
                values["fencing_generation"], values["issued_at"],
                values["expires_at"], values["state"],
            ),
        )

    # --- _validate_resource_request -------------------------------------------------

    def test_validate_resource_request_rejects_non_request_and_empty_fields(self):
        with self.assertRaises(ResourceError) as raised:
            self.manager.provision("not-a-request")  # type: ignore[arg-type]
        self.assertEqual("RESOURCE_REQUEST_INVALID", raised.exception.code)

        for request in (
            self._request(resource_ref=""),
            self._request(resource_type=""),
            self._request(resource_owner_ref=""),
        ):
            with self.subTest(request=request), self.assertRaises(ResourceError) as raised:
                self.manager.provision(request)
            self.assertEqual("RESOURCE_REQUEST_INVALID", raised.exception.code)

    def test_validate_resource_request_rejects_non_dict_scope(self):
        with self.assertRaises(ResourceError) as raised:
            self.manager.provision(self._request(scope="not-a-dict"))  # type: ignore[arg-type]
        self.assertEqual("RESOURCE_REQUEST_INVALID", raised.exception.code)

    def test_validate_resource_request_rejects_unsupported_resource_type(self):
        with self.assertRaises(ResourceError) as raised:
            self.manager.provision(self._request(resource_type="other.resource@1"))
        self.assertEqual("UNSUPPORTED_RESOURCE_TYPE", raised.exception.code)

    def test_provision_rejects_non_serializable_scope(self):
        for scope in ({"bad": {1, 2, 3}}, {"bad": float("nan")}):
            with self.subTest(scope=scope), self.assertRaises(ResourceError) as raised:
                self.manager.provision(self._request(scope=scope))
            self.assertEqual("RESOURCE_SCOPE_INVALID", raised.exception.code)

    # --- _validate_lease_request ----------------------------------------------------

    def test_validate_lease_request_rejects_empty_refs_and_non_authority(self):
        authority = _fake_authority()
        for kwargs in (
            {"lease_ref": "", "resource_ref": RESOURCE, "lease_holder_ref": "holder:x", "authority": authority},
            {"lease_ref": "lease:x", "resource_ref": "", "lease_holder_ref": "holder:x", "authority": authority},
            {"lease_ref": "lease:x", "resource_ref": RESOURCE, "lease_holder_ref": "", "authority": authority},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ResourceError) as raised:
                self.manager.issue_lease(**kwargs)
            self.assertEqual("RESOURCE_LEASE_REQUEST_INVALID", raised.exception.code)

        for bad_authority in (object(), "not-an-authority", None):
            with self.subTest(authority=bad_authority), self.assertRaises(ResourceError) as raised:
                self.manager.issue_lease("lease:x", RESOURCE, "holder:x", bad_authority)
            self.assertEqual("RESOURCE_LEASE_REQUEST_INVALID", raised.exception.code)

    # --- issue_lease expires_at validation ------------------------------------------

    def test_issue_lease_rejects_invalid_expiry(self):
        authority = _fake_authority()
        for expires_at in ("200", 200.5, True, 100, 99):
            with self.subTest(expires_at=expires_at), self.assertRaises(ResourceError) as raised:
                self.manager.issue_lease(
                    "lease:expiry", RESOURCE, "holder:x", authority, expires_at=expires_at
                )
            self.assertEqual("LEASE_VALIDITY_INVALID", raised.exception.code)

    # --- _now clock -----------------------------------------------------------------

    def test_clock_must_return_plain_int(self):
        for bad in (True, "100", 100.5, None):
            manager = self._manager(clock=lambda bad=bad: bad)
            with self.subTest(clock_value=bad), self.assertRaises(ResourceError) as raised:
                manager._now()
            self.assertEqual("RESOURCE_CLOCK_INVALID", raised.exception.code)

    # --- release / revoke idempotency + unknown lease -------------------------------

    def test_release_and_revoke_unknown_lease(self):
        for action in (self.manager.release_lease, self.manager.revoke_lease):
            with self.subTest(action=action.__name__), self.assertRaises(ResourceError) as raised:
                action("lease:missing")
            self.assertEqual("UNRESOLVED_RESOURCE_LEASE", raised.exception.code)

    def test_release_and_revoke_are_idempotent_on_non_active_lease(self):
        authority = self._seed_runtime()
        self._provision()

        released = self.manager.issue_lease(
            "lease:release/1", RESOURCE, "holder:module/1", authority
        )
        self.assertEqual("ACTIVE", released.state)
        self.assertEqual("RELEASED", self.manager.release_lease(released.lease_ref).state)
        # Second release and a later revoke are no-ops on a non-ACTIVE lease.
        self.assertEqual("RELEASED", self.manager.release_lease(released.lease_ref).state)
        self.assertEqual("RELEASED", self.manager.revoke_lease(released.lease_ref).state)

        revoked = self.manager.issue_lease(
            "lease:revoke/1", RESOURCE, "holder:module/1", authority
        )
        self.assertEqual("REVOKE_REQUESTED", self.manager.revoke_lease(revoked.lease_ref).state)
        self.assertEqual("REVOKE_REQUESTED", self.manager.revoke_lease(revoked.lease_ref).state)
        self.assertEqual("REVOKE_REQUESTED", self.manager.release_lease(revoked.lease_ref).state)

    # --- destroy branches -----------------------------------------------------------

    def test_destroy_unknown_resource(self):
        with self.assertRaises(ResourceError) as raised:
            self.manager.destroy("resource:missing")
        self.assertEqual("UNRESOLVED_RESOURCE", raised.exception.code)

    def test_destroy_rejects_non_available_state(self):
        self._provision()
        self.store.connection.execute(
            "UPDATE resources SET state = 'UNKNOWN' WHERE resource_ref = ?", (RESOURCE,)
        )
        with self.assertRaises(ResourceError) as raised:
            self.manager.destroy(RESOURCE)
        self.assertEqual("RESOURCE_NOT_DESTROYABLE", raised.exception.code)

    def test_destroy_is_idempotent_when_already_destroyed(self):
        self._provision()
        destroyed = self.manager.destroy(RESOURCE)
        self.assertEqual("DESTROYED", destroyed.state)
        self.assertEqual(destroyed, self.manager.destroy(RESOURCE))

    # --- validate_lease_advisory non-transferability -------------------------------

    def test_validate_lease_advisory_rejects_non_transferable_binding(self):
        authority = self._seed_runtime()
        self._provision()
        lease = self.manager.issue_lease(
            "lease:advisory/1", RESOURCE, "holder:module/1", authority
        )
        self.assertEqual("ACTIVE", lease.state)

        other_authority = AttemptAuthority(
            execution_ref=authority.execution_ref,
            activation_ref=authority.activation_ref,
            run_ref=authority.run_ref,
            attempt_seq=authority.attempt_seq,
            fencing_token="fencing:other",
            fencing_generation=authority.fencing_generation,
        )
        cases = (
            ("holder", "holder:other", RESOURCE, authority),
            ("resource", "holder:module/1", "resource:other", authority),
            ("authority", "holder:module/1", RESOURCE, other_authority),
        )
        for label, holder, resource_ref, auth in cases:
            with self.subTest(binding=label):
                result = self.manager.validate_lease_advisory(
                    lease.lease_ref, resource_ref, holder, auth
                )
                self.assertFalse(result.valid)
                self.assertEqual("LEASE_NON_TRANSFERABLE", result.reason_code)

    # --- raw schema constraint probes ----------------------------------------------

    def test_resources_table_raw_constraints(self):
        # NOT NULL resource_type.
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_resource(resource_ref="resource:null-type", resource_type=None)

        # CHECK state in canonical set.
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_resource(
                resource_ref="resource:bad-state",
                state="BOGUS",
                external_ref="ext:bad-state",
            )

        # UNIQUE external_ref.
        self._insert_resource(resource_ref="resource:a", external_ref="ext:shared")
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_resource(resource_ref="resource:b", external_ref="ext:shared")

        # PRIMARY KEY resource_ref.
        self._insert_resource(resource_ref="resource:pk", external_ref="ext:pk")
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_resource(resource_ref="resource:pk", external_ref="ext:pk-dup")

    def test_resource_leases_table_raw_constraints(self):
        authority = self._seed_runtime()
        self._provision()

        # NOT NULL lease_holder_ref.
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_lease(authority, lease_ref="lease:raw/null-holder", lease_holder_ref=None)

        # CHECK attempt_seq > 0.
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_lease(authority, lease_ref="lease:raw/attempt", attempt_seq=0)

        # CHECK fencing_generation > 0.
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_lease(authority, lease_ref="lease:raw/generation", fencing_generation=0)

        # CHECK length(fencing_token) > 0.
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_lease(authority, lease_ref="lease:raw/token", fencing_token="")

        # CHECK state in canonical set.
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_lease(authority, lease_ref="lease:raw/state", state="BOGUS")

        # FK resource_ref -> resources.
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_lease(
                authority, lease_ref="lease:raw/fk-resource", resource_ref="resource:missing"
            )

        # FK activation_ref -> activations.
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_lease(
                authority, lease_ref="lease:raw/fk-activation", activation_ref="activation:missing"
            )

        # FK (run_ref, attempt_seq) -> run_attempts.
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_lease(authority, lease_ref="lease:raw/fk-run", run_ref="run:missing")

        # PRIMARY KEY lease_ref.
        self._insert_lease(authority, lease_ref="lease:raw/pk")
        with self.assertRaises(sqlite3.IntegrityError):
            self._insert_lease(authority, lease_ref="lease:raw/pk")


if __name__ == "__main__":
    unittest.main()
