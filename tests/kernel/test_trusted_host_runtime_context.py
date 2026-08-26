"""ARE-GATE-5 minimal Module Host trust-boundary slice (NYRON-T-20260826-061).

Covers the Task's Required Negative Proofs for the RuntimeContext data shape
and its Host-side construction. See src/nyron_kernel/host/runtime_context.py
for the scope decision this test file validates: this slice implements only
the opaque RuntimeContext *data* shape (Module Design Report §38) and a
one-way narrowing conversion from real Owner objects into it. It does NOT
implement any live broker/effect-invocation callable reachable from inside a
Module's execute() body, because the concrete calling convention for that is
not uniquely determined by current frozen contracts without inventing a
generalized Host SDK shape (explicitly out of scope for this Task). Tests
below that map to a "brokered Effect path" requirement are instead answered
by proving the RuntimeContext carries zero actionable authority: no code
anywhere reads a handle's contents to authorize or perform a mutation, so a
real handle and a fabricated one are observably indistinguishable.
"""

from __future__ import annotations

import dataclasses
import inspect
import unittest

from nyron_kernel.capability import (
    CapabilityAuthority,
    CapabilityDecision,
    CapabilityRequest,
    CapabilityTypeDefinition,
    CapabilityTypeRegistry,
)
from nyron_kernel.execution import RunRepository, RuntimeAuthorityResolver
from nyron_kernel.host import (
    CapabilityHandle,
    ResourceHandle,
    RuntimeContext,
    TrustedHostError,
    TrustedModuleHost,
    build_runtime_context,
)
from nyron_kernel.host import runtime_context as runtime_context_module
from nyron_kernel.host import trusted_host as trusted_host_module
from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.modules import builtin_text_concat
from nyron_kernel.resource import ResourceManager, ResourceRequest
from nyron_kernel.store import SQLiteStore


GRAPH = "graph:host-context@1"
MODULE = "module-instance:host-context@1"
EXECUTION = "execution:host-context/1"
ACTIVATION = "activation:host-context/1"
RUN = "run:host-context/1"
RESOURCE = "resource:host-context/1"
CAPABILITY_TYPE = "capability.host-context-probe"
CAPABILITY_VERSION = "1"
SCOPE_SCHEMA = "schema:host-context-probe@1"
ACCOUNTING_SCOPE = "accounting:host-context"

_DISTINCTIVE_PATH_MARKER = "MANAGED-ROOT-PATH-MARKER-DO-NOT-LEAK"


class TrustedHostRuntimeContextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self._seed_runtime()
        self.runtime = RuntimeAuthorityResolver(self.store)
        self.attempt = self.runtime.resolve_current(RUN)
        assert self.attempt is not None
        self.now = 100

        self.registry = CapabilityTypeRegistry(self.store)
        self.registry.register(
            CapabilityTypeDefinition(
                CAPABILITY_TYPE,
                CAPABILITY_VERSION,
                SCOPE_SCHEMA,
                None,
                ("PURE",),
                {"description": "host runtime-context probe"},
            )
        )
        self.capability = CapabilityAuthority(
            self.store,
            self.registry,
            self.runtime,
            lambda _request: CapabilityDecision("GRANTED", "decision:host-context/1"),
            lambda schema_ref, scope: schema_ref == SCOPE_SCHEMA,
            lambda: self.now,
        )

        managed_root = f"{self.temp_root()}/{_DISTINCTIVE_PATH_MARKER}"
        self.resource_manager = ResourceManager(
            self.store, managed_root, self.runtime, lambda: self.now
        )
        self.resource_manager.provision(
            ResourceRequest(
                RESOURCE,
                ResourceManager.RESOURCE_TYPE,
                "resource-manager:kernel",
                {"workspace_ref": "workspace:host-context"},
            )
        )

        self.host_registry = ModuleRegistry(SQLiteStore())
        self.host_registry.register(builtin_text_concat.definition())
        self.host = TrustedModuleHost(self.host_registry)

    def tearDown(self) -> None:
        self.store.close()

    @staticmethod
    def temp_root() -> str:
        import tempfile

        return tempfile.mkdtemp()

    def _seed_runtime(self) -> None:
        RunRepository(self.store)
        with self.store.transaction() as connection:
            connection.execute(
                "INSERT INTO graph_revisions VALUES (?, '{}', 1, NULL)", (GRAPH,)
            )
            connection.execute(
                """
                INSERT INTO module_instance_revisions VALUES (
                    ?, ?, 'host-context', 'test.host-context', '1',
                    'config:host-context@1', 'sha256:host-context', '{}', '{}',
                    '["root"]', ?
                )
                """,
                (MODULE, GRAPH, ACCOUNTING_SCOPE),
            )
            connection.execute(
                """
                INSERT INTO execution_admissions VALUES (
                    'admission:host-context/1', ?, ?, 'policy:host-context@1', 1,
                    'ADMITTED'
                )
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO workflow_executions VALUES (
                    ?, ?, 'admission:host-context/1', 'policy:host-context@1',
                    'ADMITTED'
                )
                """,
                (EXECUTION, GRAPH),
            )
            connection.execute(
                """
                INSERT INTO activations VALUES (
                    ?, ?, ?, ?, 'delivery:host-context-trigger', '[]', ?,
                    'event:activation:host-context/1'
                )
                """,
                (ACTIVATION, EXECUTION, GRAPH, MODULE, ACCOUNTING_SCOPE),
            )
            connection.execute(
                "INSERT INTO activation_created_events VALUES "
                "('event:activation:host-context/1', ?, 'ActivationCreated')",
                (ACTIVATION,),
            )
        RunRepository(self.store).create_initial(
            run_ref=RUN, activation_ref=ACTIVATION, execution_ref=EXECUTION
        )

    def _issue_grant(self, grant_ref: str = "grant:host-context/1"):
        return self.capability.issue(
            CapabilityRequest(
                grant_ref,
                CAPABILITY_TYPE,
                CAPABILITY_VERSION,
                self.attempt,
                {},
                "capability-authority:test",
            ),
            expires_at=200,
        )

    def _issue_lease(self, lease_ref: str = "lease:host-context/1"):
        return self.resource_manager.issue_lease(
            lease_ref, RESOURCE, f"holder:{lease_ref}", self.attempt, expires_at=200
        )

    # ------------------------------------------------------------------
    # 1/2. Module cannot receive raw Store/connection/Owner objects, and no
    # arbitrary caller-supplied object (including a real Owner object, or a
    # duck-typed RuntimeContext lookalike) can be smuggled through
    # runtime_context — only an exact RuntimeContext instance is accepted.
    # ------------------------------------------------------------------

    def test_raw_owner_objects_rejected_as_runtime_context(self) -> None:
        grant = self._issue_grant()
        lease = self._issue_lease()

        for label, candidate in (
            ("store", self.store),
            ("connection", self.store.connection),
            ("attempt_authority", self.attempt),
            ("capability_grant", grant),
            ("resource_lease", lease),
            ("capability_authority", self.capability),
            ("resource_manager", self.resource_manager),
            ("registry", self.host_registry),
        ):
            with self.subTest(candidate=label):
                with self.assertRaises(TrustedHostError) as raised:
                    self.host.execute(
                        "builtin.text.concat@1", {"a": "x", "b": "y"}, {}, candidate
                    )
                self.assertEqual(
                    "INVALID_RUNTIME_CONTEXT", raised.exception.code
                )

    def test_duck_typed_lookalike_rejected(self) -> None:
        class FakeRuntimeContext:
            """Same field names as RuntimeContext, but not the real type."""

            activation_ref = ACTIVATION
            run_ref = RUN
            attempt_seq = 1
            fencing_token = "fence:fake"
            accounting_scope_ref = ACCOUNTING_SCOPE
            capability_handles = ()
            resource_handles = ()
            metadata = ()

        with self.assertRaises(TrustedHostError) as raised:
            self.host.execute(
                "builtin.text.concat@1",
                {"a": "x", "b": "y"},
                {},
                FakeRuntimeContext(),
            )
        self.assertEqual("INVALID_RUNTIME_CONTEXT", raised.exception.code)

    def test_dict_shaped_context_rejected(self) -> None:
        fake = {
            "activation_ref": ACTIVATION,
            "run_ref": RUN,
            "attempt_seq": 1,
            "fencing_token": "fence:fake",
            "accounting_scope_ref": ACCOUNTING_SCOPE,
            "capability_handles": (),
            "resource_handles": (),
            "metadata": (),
        }
        with self.assertRaises(TrustedHostError) as raised:
            self.host.execute(
                "builtin.text.concat@1", {"a": "x", "b": "y"}, {}, fake
            )
        self.assertEqual("INVALID_RUNTIME_CONTEXT", raised.exception.code)

    def test_subclass_of_runtime_context_rejected(self) -> None:
        # type(x) is RuntimeContext, not isinstance — a subclass instance is
        # not automatically trusted just because it inherits the fields.
        class SneakyRuntimeContext(RuntimeContext):
            pass

        base = build_runtime_context(self.attempt, ACCOUNTING_SCOPE)
        sneaky = SneakyRuntimeContext(**{
            field.name: getattr(base, field.name)
            for field in dataclasses.fields(RuntimeContext)
        })
        with self.assertRaises(TrustedHostError) as raised:
            self.host.execute(
                "builtin.text.concat@1", {"a": "x", "b": "y"}, {}, sneaky
            )
        self.assertEqual("INVALID_RUNTIME_CONTEXT", raised.exception.code)

    # ------------------------------------------------------------------
    # 3. PURE builtin regression: identical behavior with None and with a
    # real, non-empty RuntimeContext (the builtin ignores it either way).
    # ------------------------------------------------------------------

    def test_none_and_real_context_produce_identical_pure_output(self) -> None:
        grant = self._issue_grant()
        lease = self._issue_lease()
        context = build_runtime_context(
            self.attempt, ACCOUNTING_SCOPE, (grant,), (lease,)
        )

        with_none = self.host.execute(
            "builtin.text.concat@1", {"a": "x", "b": "y"}, {}, None
        )
        with_context = self.host.execute(
            "builtin.text.concat@1", {"a": "x", "b": "y"}, {}, context
        )

        self.assertEqual(with_none, with_context)
        self.assertEqual({"text": "xy"}, with_context.outputs)

    def test_builtin_source_never_reads_runtime_context_fields(self) -> None:
        source = inspect.getsource(builtin_text_concat)
        for token in (
            "runtime_context.",
            "capability_handles",
            "resource_handles",
            "accounting_scope_ref",
        ):
            self.assertNotIn(token, source)

    # ------------------------------------------------------------------
    # 5 (adapted). No brokered Effect path exists in this slice, so there is
    # nothing to bypass: prove a RuntimeContext built from a fabricated
    # grant_ref/lease_ref that corresponds to NO real store row is accepted
    # and behaves identically to one built from genuine Owner objects. This
    # demonstrates handle contents are never dereferenced/authorized by any
    # code path here — the safety property does not depend on the caller
    # supplying genuine refs.
    # ------------------------------------------------------------------

    def test_fabricated_handles_are_inert_and_produce_identical_behavior(
        self,
    ) -> None:
        genuine_grant = self._issue_grant()
        genuine_lease = self._issue_lease()
        genuine_context = build_runtime_context(
            self.attempt, ACCOUNTING_SCOPE, (genuine_grant,), (genuine_lease,)
        )

        fabricated_context = RuntimeContext(
            activation_ref=self.attempt.activation_ref,
            run_ref=self.attempt.run_ref,
            attempt_seq=self.attempt.attempt_seq,
            fencing_token=self.attempt.fencing_token,
            accounting_scope_ref=ACCOUNTING_SCOPE,
            capability_handles=(
                CapabilityHandle(
                    capability_type_ref="nonexistent.capability.type",
                    capability_type_version="999",
                    grant_ref="grant:never-issued",
                ),
            ),
            resource_handles=(
                ResourceHandle(
                    resource_ref="resource:never-provisioned",
                    lease_ref="lease:never-issued",
                ),
            ),
        )

        genuine_result = self.host.execute(
            "builtin.text.concat@1", {"a": "x", "b": "y"}, {}, genuine_context
        )
        fabricated_result = self.host.execute(
            "builtin.text.concat@1", {"a": "x", "b": "y"}, {}, fabricated_context
        )

        self.assertEqual(genuine_result, fabricated_result)
        self.assertIsInstance(genuine_result, type(fabricated_result))

    def test_no_live_broker_object_reachable_from_runtime_context(self) -> None:
        """Structural proof that RuntimeContext exposes no callable/method
        beyond plain dataclass machinery — there is no broker to bypass."""
        context = build_runtime_context(self.attempt, ACCOUNTING_SCOPE)
        for name in dir(context):
            if name.startswith("_"):
                continue
            value = getattr(context, name)
            self.assertFalse(
                callable(value), f"RuntimeContext.{name} is unexpectedly callable"
            )
        for handle_type in (CapabilityHandle, ResourceHandle):
            for field in dataclasses.fields(handle_type):
                self.assertIn(field.type, ("str",), f"{handle_type.__name__}.{field.name}")

    # ------------------------------------------------------------------
    # 6. Resource proxy opacity: ResourceHandle structurally cannot carry a
    # raw managed-root path, and the real Resource.external_ref value never
    # appears anywhere in a built RuntimeContext.
    # ------------------------------------------------------------------

    def test_resource_handle_has_no_path_capable_field(self) -> None:
        field_names = {f.name for f in dataclasses.fields(ResourceHandle)}
        self.assertEqual({"resource_ref", "lease_ref"}, field_names)

    def test_managed_root_path_never_appears_in_built_context(self) -> None:
        resource = self.resource_manager.resolve_resource(RESOURCE)
        assert resource is not None
        self.assertIn(_DISTINCTIVE_PATH_MARKER, resource.external_ref)

        lease = self._issue_lease()
        context = build_runtime_context(
            self.attempt, ACCOUNTING_SCOPE, (), (lease,)
        )

        self.assertNotIn(_DISTINCTIVE_PATH_MARKER, repr(context))
        for handle in context.resource_handles:
            self.assertNotIn(_DISTINCTIVE_PATH_MARKER, repr(handle))
            for field in dataclasses.fields(handle):
                value = getattr(handle, field.name)
                self.assertNotIn(_DISTINCTIVE_PATH_MARKER, str(value))

    # ------------------------------------------------------------------
    # RuntimeContext / CapabilityHandle / ResourceHandle strict shape
    # validation — proves nothing beyond validated primitives/handles can
    # ever be embedded (blocks Store/connection/Owner-object smuggling via
    # direct construction, not just via the Host boundary).
    # ------------------------------------------------------------------

    def test_capability_handle_rejects_non_string_fields(self) -> None:
        with self.assertRaises(TypeError):
            CapabilityHandle(capability_type_ref=1, capability_type_version="1", grant_ref="g")
        with self.assertRaises(TypeError):
            CapabilityHandle(capability_type_ref="t", capability_type_version="1", grant_ref="")

    def test_resource_handle_rejects_non_string_fields(self) -> None:
        with self.assertRaises(TypeError):
            ResourceHandle(resource_ref=object(), lease_ref="l")

    def test_runtime_context_rejects_raw_object_in_capability_handles(self) -> None:
        with self.assertRaises(TypeError):
            RuntimeContext(
                activation_ref="a",
                run_ref="r",
                attempt_seq=1,
                fencing_token="f",
                accounting_scope_ref="s",
                capability_handles=(self.store,),
            )

    def test_runtime_context_rejects_raw_object_in_resource_handles(self) -> None:
        with self.assertRaises(TypeError):
            RuntimeContext(
                activation_ref="a",
                run_ref="r",
                attempt_seq=1,
                fencing_token="f",
                accounting_scope_ref="s",
                resource_handles=(self.store.connection,),
            )

    def test_runtime_context_rejects_non_tuple_handles(self) -> None:
        with self.assertRaises(TypeError):
            RuntimeContext(
                activation_ref="a",
                run_ref="r",
                attempt_seq=1,
                fencing_token="f",
                accounting_scope_ref="s",
                capability_handles=[],
            )

    def test_runtime_context_rejects_non_positive_attempt_seq(self) -> None:
        with self.assertRaises(TypeError):
            RuntimeContext(
                activation_ref="a",
                run_ref="r",
                attempt_seq=0,
                fencing_token="f",
                accounting_scope_ref="s",
            )
        with self.assertRaises(TypeError):
            RuntimeContext(
                activation_ref="a",
                run_ref="r",
                attempt_seq=True,  # bool is an int subclass — must not pass
                fencing_token="f",
                accounting_scope_ref="s",
            )

    def test_runtime_context_rejects_bad_metadata(self) -> None:
        with self.assertRaises(TypeError):
            RuntimeContext(
                activation_ref="a",
                run_ref="r",
                attempt_seq=1,
                fencing_token="f",
                accounting_scope_ref="s",
                metadata=(("k", 1),),
            )
        with self.assertRaises(TypeError):
            RuntimeContext(
                activation_ref="a",
                run_ref="r",
                attempt_seq=1,
                fencing_token="f",
                accounting_scope_ref="s",
                metadata=(("dup", "1"), ("dup", "2")),
            )

    def test_runtime_context_is_frozen(self) -> None:
        context = build_runtime_context(self.attempt, ACCOUNTING_SCOPE)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            context.activation_ref = "changed"  # type: ignore[misc]

    # ------------------------------------------------------------------
    # 7. No direct canonical INSERT/UPDATE/DELETE in Host code.
    # ------------------------------------------------------------------

    def test_host_files_contain_no_direct_canonical_mutation(self) -> None:
        for module in (trusted_host_module, runtime_context_module):
            source = inspect.getsource(module).upper()
            for token in ("INSERT INTO", "UPDATE ", "DELETE FROM"):
                self.assertNotIn(token, source, f"{module.__name__} contains {token!r}")

    # ------------------------------------------------------------------
    # 8. No hostile-plugin isolation claim is introduced.
    # ------------------------------------------------------------------

    def test_no_hostile_isolation_claim_introduced(self) -> None:
        for module in (trusted_host_module, runtime_context_module):
            source = inspect.getsource(module).lower()
            for token in (
                "docker",
                "wasm",
                "vm sandbox",
                "hostile-safe",
                "untrusted plugin support",
                "hostile plugin support",
                "sandboxed module host",
            ):
                self.assertNotIn(token, source, f"{module.__name__} contains {token!r}")

    # ------------------------------------------------------------------
    # 9. 038-F-001 / 043-F-001 activation-condition absence in the new code.
    # ------------------------------------------------------------------

    def test_no_concurrency_or_filesystem_primitives_introduced(self) -> None:
        for module in (trusted_host_module, runtime_context_module):
            source = inspect.getsource(module)
            for token in (
                "import os",
                "import subprocess",
                "import socket",
                "import threading",
                "import multiprocessing",
                "import asyncio",
                "concurrent.futures",
                "pathlib",
                "open(",
                "connection pool",
            ):
                self.assertNotIn(token, source, f"{module.__name__} contains {token!r}")

    def test_trusted_host_module_still_excludes_execution_machinery_tokens(
        self,
    ) -> None:
        """trusted_host.py must stay ignorant of Attempt/Activation/Packet/
        Delivery/Accounting concepts — RuntimeContext crosses that boundary
        as an opaque, already-built value, never as something the host
        itself constructs or interprets."""
        source = inspect.getsource(trusted_host_module)
        self.assertNotIn("nyron_kernel.execution", source)
        lowered = source.lower()
        for token in ("packet", "delivery", "activation", "attempt", "accounting"):
            self.assertNotIn(token, lowered)


if __name__ == "__main__":
    unittest.main()
