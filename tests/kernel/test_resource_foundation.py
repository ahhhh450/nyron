"""Executable acceptance coverage for ARE-GATE-2 / Task 037."""

from __future__ import annotations

import inspect
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from nyron_kernel.execution import RunRepository, RuntimeAuthorityResolver
from nyron_kernel.resource import (
    AdvisoryLeaseValidation,
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


class InjectedCrash(RuntimeError):
    pass


class ResourceFoundationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.store = SQLiteStore(self.base / "resource.db")
        self._seed_runtime(self.store)
        self.runtime = RuntimeAuthorityResolver(self.store)
        self.authority = self.runtime.resolve_current(RUN)
        assert self.authority is not None
        self.now = 100
        self.manager = self._manager()

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    @staticmethod
    def _seed_runtime(store: SQLiteStore) -> None:
        store.create_run_attempt_schema()
        with store.transaction() as connection:
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
        RunRepository(store).create_initial(
            run_ref=RUN,
            activation_ref=ACTIVATION,
            execution_ref=EXECUTION,
        )

    def _manager(self, hook=None, root=None) -> ResourceManager:
        return ResourceManager(
            self.store,
            root or self.base / "managed-root",
            self.runtime,
            lambda: self.now,
            hook,
        )

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

    def _lease(self, **changes):
        values = {
            "lease_ref": "lease:resource/1",
            "resource_ref": RESOURCE,
            "lease_holder_ref": "holder:module/1",
            "authority": self.authority,
        }
        values.update(changes)
        return self.manager.issue_lease(**values)

    def test_provisioning_commits_before_create_and_recovers_before_create_crash(self):
        def crash(stage, resource):
            if stage == "AFTER_PROVISIONING_COMMIT":
                self.assertEqual("PROVISIONING", resource.state)
                self.assertFalse(Path(resource.external_ref).exists())
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._manager(crash).provision(self._request())
        intent = self.manager.resolve_resource(RESOURCE)
        assert intent is not None
        self.assertEqual("PROVISIONING", intent.state)
        recovered = self.manager.recover(RESOURCE)
        self.assertEqual("AVAILABLE", recovered.state)
        self.assertTrue(Path(recovered.external_ref).is_dir())

    def test_crash_after_create_recovers_only_exact_provenance(self):
        def crash(stage, resource):
            if stage == "AFTER_DIRECTORY_CREATE":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._manager(crash).provision(self._request())
        before = self.manager.resolve_resource(RESOURCE)
        assert before is not None
        self.assertEqual("PROVISIONING", before.state)
        marker = Path(before.external_ref) / ".nyron-resource.json"
        self.assertEqual(before.provenance, json.loads(marker.read_text()))
        self.assertEqual("AVAILABLE", self.manager.recover(RESOURCE).state)

    def test_exact_replay_is_idempotent_and_conflicting_rebind_fails_closed(self):
        resource = self._provision()
        self.assertEqual(resource, self.manager.provision(self._request()))
        for request in (
            self._request(resource_type="other.resource@1"),
            self._request(resource_owner_ref="resource-manager:other"),
            self._request(scope={"workspace_ref": "workspace:other"}),
        ):
            with self.subTest(request=request), self.assertRaises(ResourceError):
                self.manager.provision(request)
        self.assertEqual(resource, self.manager.resolve_resource(RESOURCE))

    def test_resource_ref_cannot_escape_root_and_unproven_directory_is_unknown(self):
        escape = self.manager.provision(self._request(resource_ref="../../outside"))
        self.assertEqual(Path(escape.external_ref).parent, self.base / "managed-root")
        self.assertFalse((self.base / "outside").exists())

        request = self._request(resource_ref="resource:unproven")
        expected = self.manager._path_for(request.resource_ref)
        expected.mkdir()
        (expected / "foreign.txt").write_text("foreign")
        resource = self.manager.provision(request)
        self.assertEqual("UNKNOWN", resource.state)
        self.assertTrue((expected / "foreign.txt").exists())

    def test_mismatched_marker_is_unknown_and_never_adopted(self):
        def crash(stage, _resource):
            if stage == "AFTER_DIRECTORY_CREATE":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._manager(crash).provision(self._request())
        resource = self.manager.resolve_resource(RESOURCE)
        assert resource is not None
        marker = Path(resource.external_ref) / ".nyron-resource.json"
        marker.write_text('{"manager_id":"foreign"}')
        self.assertEqual("UNKNOWN", self.manager.recover(RESOURCE).state)

    def test_final_component_symlink_is_never_followed_or_adopted(self):
        request = self._request(resource_ref="resource:symlink")
        path = self.manager._path_for(request.resource_ref)
        target = self.base / "foreign-target"
        target.mkdir()
        try:
            path.symlink_to(target, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"directory symlink unavailable on this platform: {error}")
        resource = self.manager.provision(request)
        self.assertEqual("UNKNOWN", resource.state)
        self.assertFalse((target / ".nyron-resource.json").exists())

    @unittest.skipUnless(os.name == "nt", "requires Windows junction semantics")
    def test_final_component_junction_is_never_adopted(self):
        def crash(stage, _resource):
            if stage == "AFTER_PROVISIONING_COMMIT":
                raise InjectedCrash

        with self.assertRaises(InjectedCrash):
            self._manager(crash).provision(self._request())
        resource = self.manager.resolve_resource(RESOURCE)
        assert resource is not None
        target = self.base / "junction-target"
        target.mkdir()
        (target / ".nyron-resource.json").write_text(json.dumps(resource.provenance))
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", resource.external_ref, str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if created.returncode != 0:
            self.skipTest(f"junction creation unavailable: {created.stderr.strip()}")
        self.assertEqual("UNKNOWN", self.manager.recover(RESOURCE).state)

    def test_substitution_between_create_and_marker_never_marks_replacement(self):
        displaced = self.base / "displaced-created-directory"
        replacement_file = "unrelated.txt"

        def substitute(stage, resource):
            if stage == "AFTER_DIRECTORY_OPEN_BEFORE_MARKER":
                path = Path(resource.external_ref)
                path.rename(displaced)
                path.mkdir()
                (path / replacement_file).write_text("unrelated")

        resource = self._manager(substitute).provision(self._request())
        replacement = Path(resource.external_ref)
        self.assertEqual("UNKNOWN", resource.state)
        self.assertFalse((replacement / ".nyron-resource.json").exists())
        self.assertEqual("unrelated", (replacement / replacement_file).read_text())

    @unittest.skipUnless(
        ResourceManager._descriptor_operations_supported(),
        "requires O_DIRECTORY/O_NOFOLLOW and descriptor-relative operations",
    )
    def test_descriptor_marker_is_exclusive_and_bound_to_open_directory(self):
        directory = self.base / "descriptor-marker"
        directory.mkdir()
        fd = os.open(
            directory,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        )
        try:
            ResourceManager._write_exclusive_json_at(fd, "marker.json", {"ok": True})
            with self.assertRaises(FileExistsError):
                ResourceManager._write_exclusive_json_at(fd, "marker.json", {"ok": False})
        finally:
            os.close(fd)
        self.assertEqual({"ok": True}, json.loads((directory / "marker.json").read_text()))

    def test_available_resource_and_lease_survive_file_reopen_exactly(self):
        resource = self._provision()
        lease = self._lease(expires_at=200)
        database = self.base / "resource.db"
        root = self.base / "managed-root"
        self.store.close()
        with SQLiteStore(database) as reopened:
            manager = ResourceManager(
                reopened, root, RuntimeAuthorityResolver(reopened), lambda: 100
            )
            self.assertEqual(resource, manager.resolve_resource(RESOURCE))
            self.assertEqual(lease, manager.resolve_lease(lease.lease_ref))
        self.store = SQLiteStore(database)

    def test_lease_requires_available_resource_and_exact_current_authority(self):
        with self.assertRaises(ResourceError) as unavailable:
            self._lease()
        self.assertEqual("UNRESOLVED_RESOURCE", unavailable.exception.code)
        self._provision()
        stale_values = (
            replace(self.authority, execution_ref="execution:stale"),
            replace(self.authority, activation_ref="activation:stale"),
            replace(self.authority, run_ref="run:stale"),
            replace(self.authority, attempt_seq=2),
            replace(self.authority, fencing_token="fencing:stale"),
            replace(self.authority, fencing_generation=2),
        )
        for index, stale in enumerate(stale_values):
            with self.subTest(stale=stale), self.assertRaises(ResourceError) as raised:
                self._lease(lease_ref=f"lease:stale/{index}", authority=stale)
            self.assertEqual("STALE_ATTEMPT_AUTHORITY", raised.exception.code)
        self.assertEqual("ACTIVE", self._lease().state)

    def test_lease_replay_is_stable_and_rebind_or_transfer_fails_closed(self):
        self._provision()
        first = self._lease(expires_at=200)
        self.assertEqual(first, self._lease(expires_at=200))
        conflicts = (
            {"lease_holder_ref": "holder:other", "expires_at": 200},
            {"resource_ref": "resource:other", "expires_at": 200},
            {"authority": replace(self.authority, fencing_generation=2), "expires_at": 200},
            {"expires_at": 201},
        )
        for changes in conflicts:
            with self.subTest(changes=changes), self.assertRaises(ResourceError) as raised:
                self._lease(**changes)
            self.assertEqual("RESOURCE_LEASE_IDENTITY_CONFLICT", raised.exception.code)
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "UPDATE resource_leases SET lease_holder_ref = 'holder:other' WHERE lease_ref = ?",
                (first.lease_ref,),
            )

    def test_release_and_revoke_are_durable_and_do_not_destroy_resource(self):
        resource = self._provision()
        released = self._lease(lease_ref="lease:released")
        self.assertEqual("RELEASED", self.manager.release_lease(released.lease_ref).state)
        self.assertFalse(self.manager.validate_lease_advisory(
            released.lease_ref, RESOURCE, "holder:module/1", self.authority
        ).valid)
        revoked = self._lease(lease_ref="lease:revoked")
        self.assertEqual("REVOKE_REQUESTED", self.manager.revoke_lease(revoked.lease_ref).state)
        self.assertFalse(self.manager.validate_lease_advisory(
            revoked.lease_ref, RESOURCE, "holder:module/1", self.authority
        ).valid)
        self.assertEqual(resource, self.manager.resolve_resource(RESOURCE))
        self.assertTrue(Path(resource.external_ref).exists())

    def test_expiry_ends_lease_but_resource_remains_available(self):
        resource = self._provision()
        lease = self._lease(expires_at=110)
        self.now = 110
        result = self.manager.validate_lease_advisory(
            lease.lease_ref, RESOURCE, "holder:module/1", self.authority
        )
        self.assertEqual(AdvisoryLeaseValidation(False, "LEASE_EXPIRED"), result)
        self.assertEqual("EXPIRED", self.manager.resolve_lease(lease.lease_ref).state)
        self.assertEqual(resource, self.manager.resolve_resource(RESOURCE))

    def test_validation_rechecks_runtime_and_is_advisory_non_consumptive(self):
        self._provision()
        lease = self._lease()
        cached = self.manager.validate_lease_advisory(
            lease.lease_ref, RESOURCE, "holder:module/1", self.authority
        )
        self.assertTrue(cached.valid)
        self.store.connection.execute(
            "UPDATE runs SET fencing_generation = 2 WHERE run_ref = ?", (RUN,)
        )
        current = self.manager.validate_lease_advisory(
            lease.lease_ref, RESOURCE, "holder:module/1", self.authority
        )
        self.assertEqual(AdvisoryLeaseValidation(False, "STALE_ATTEMPT_AUTHORITY"), current)
        self.assertFalse(hasattr(cached, "consume"))
        self.assertFalse(hasattr(cached, "permit_external_use"))
        source = inspect.getsource(ResourceManager).lower()
        self.assertIn("without admitting or consuming authority", source)
        self.assertNotIn("authority_use_permit", source)

    def test_active_lease_blocks_destroy_and_proven_destroy_is_ordered(self):
        resource = self._provision()
        lease = self._lease()
        with self.assertRaises(ResourceError) as raised:
            self.manager.destroy(RESOURCE)
        self.assertEqual("RESOURCE_HAS_ACTIVE_LEASE", raised.exception.code)
        self.manager.release_lease(lease.lease_ref)

        observed = []
        def observe(stage, current):
            if stage == "AFTER_DESTROYING_COMMIT":
                observed.append((current.state, Path(current.external_ref).exists()))
        self.manager._crash_hook = observe
        destroyed = self.manager.destroy(RESOURCE)
        self.assertEqual([("DESTROYING", True)], observed)
        self.assertEqual("DESTROYED", destroyed.state)
        self.assertFalse(Path(resource.external_ref).exists())

    def test_destroy_crash_recovery_and_ambiguous_destroy_become_unknown(self):
        self._provision()
        def crash(stage, _resource):
            if stage == "AFTER_DESTROYING_COMMIT":
                raise InjectedCrash
        self.manager._crash_hook = crash
        with self.assertRaises(InjectedCrash):
            self.manager.destroy(RESOURCE)
        self.assertEqual("DESTROYING", self.manager.resolve_resource(RESOURCE).state)
        self.manager._crash_hook = lambda *_: None
        resource = self.manager.resolve_resource(RESOURCE)
        assert resource is not None
        (Path(resource.external_ref) / ".nyron-resource.json").write_text("{}")
        self.assertEqual("UNKNOWN", self.manager.recover(RESOURCE).state)
        self.assertTrue(Path(resource.external_ref).exists())

    def test_destroy_detects_real_directory_substitution_and_deletes_neither(self):
        resource = self._provision()
        path = Path(resource.external_ref)
        displaced = self.base / "displaced-proven-directory"

        def substitute(stage, current):
            if stage == "AFTER_DESTROY_IDENTITY_CHECK":
                path.rename(displaced)
                path.mkdir()
                shutil.copy2(
                    displaced / ".nyron-resource.json",
                    path / ".nyron-resource.json",
                )
                (path / "unrelated.txt").write_text("keep")

        self.manager._crash_hook = substitute
        destroyed = self.manager.destroy(resource.resource_ref)
        self.assertEqual("UNKNOWN", destroyed.state)
        self.assertTrue(displaced.exists())
        self.assertEqual("keep", (path / "unrelated.txt").read_text())

    def test_no_effect_command_retry_recovery_or_use_permit_surface(self):
        tables = {
            row["name"] for row in self.store.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        for forbidden in (
            "effect_operations", "canonical_commands", "authority_use_permits",
            "budget_reservations", "reconciliation_cases", "attempt_replacements",
        ):
            self.assertNotIn(forbidden, tables)
        source = inspect.getsource(ResourceManager)
        for forbidden in ("EffectOperation", "PREPARED", "CanonicalCommand"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
