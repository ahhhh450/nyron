"""Acceptance tests for NYRON-T-20260825-019 AccountingScope resolution."""

from __future__ import annotations

import inspect
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from nyron_kernel.accounting import (
    AccountingScope,
    AccountingScopeError,
    AccountingScopeResolver,
    compute_ancestry_hash,
)
from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.graph import GraphRepository, ModuleInstanceRevision
from nyron_kernel.modules import builtin_text_concat
from nyron_kernel.store import SQLiteStore


GRAPH_REF = "graph:text-flow@1"
ROOT_REF = "accounting:graph/text-flow@1"
CHILD_REF = "accounting:module/text-concat@1"
LEAF_REF = "accounting:port/text-concat/text@1"


def scope(
    accounting_scope_ref: str,
    definition_anchor_ref: str,
    ancestry: tuple[str, ...],
    *,
    graph_revision_ref: str = GRAPH_REF,
    parent_accounting_scope_ref: str | None = None,
    scope_kind: str = "MODULE",
    created_from_definition_ref: str | None = None,
    state: str = "ACTIVE",
) -> AccountingScope:
    return AccountingScope(
        accounting_scope_ref=accounting_scope_ref,
        graph_revision_ref=graph_revision_ref,
        definition_anchor_ref=definition_anchor_ref,
        parent_accounting_scope_ref=parent_accounting_scope_ref,
        scope_kind=scope_kind,
        ancestry_hash=compute_ancestry_hash(ancestry),
        created_from_definition_ref=(
            created_from_definition_ref or definition_anchor_ref
        ),
        state=state,
    )


def root_scope(*, graph_revision_ref: str = GRAPH_REF) -> AccountingScope:
    return scope(
        ROOT_REF,
        GRAPH_REF,
        (ROOT_REF,),
        graph_revision_ref=graph_revision_ref,
        scope_kind="GRAPH",
    )


def child_scope(*, graph_revision_ref: str = GRAPH_REF) -> AccountingScope:
    return scope(
        CHILD_REF,
        "module-instance:text-concat@1",
        (ROOT_REF, CHILD_REF),
        graph_revision_ref=graph_revision_ref,
        parent_accounting_scope_ref=ROOT_REF,
    )


class AccountingScopeResolutionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.resolver = AccountingScopeResolver(self.store)

    def tearDown(self) -> None:
        self.store.close()

    def assert_scope_error(self, code: str, action: Callable[[], object]) -> None:
        with self.assertRaises(AccountingScopeError) as raised:
            action()
        self.assertEqual(code, raised.exception.code)

    def test_canonical_root_scope_persists_and_resolves(self) -> None:
        root = root_scope()

        self.assertEqual(root, self.resolver.publish(root))
        resolved = self.resolver.resolve(ROOT_REF, GRAPH_REF, GRAPH_REF)

        self.assertEqual(ROOT_REF, resolved.accounting_scope_ref)
        self.assertEqual(GRAPH_REF, resolved.graph_revision_ref)
        self.assertEqual(GRAPH_REF, resolved.definition_anchor_ref)
        self.assertEqual((root,), resolved.ancestry)
        self.assertEqual(root.ancestry_hash, resolved.ancestry_hash)

    def test_child_resolves_complete_deterministic_root_to_leaf_chain(self) -> None:
        root = self.resolver.publish(root_scope())
        child = self.resolver.publish(child_scope())
        leaf = self.resolver.publish(
            scope(
                LEAF_REF,
                "port:text-concat/text@1",
                (ROOT_REF, CHILD_REF, LEAF_REF),
                parent_accounting_scope_ref=CHILD_REF,
                scope_kind="PORT",
            )
        )

        first = self.resolver.resolve(
            LEAF_REF, GRAPH_REF, "port:text-concat/text@1"
        )
        second = self.resolver.resolve(
            LEAF_REF, GRAPH_REF, "port:text-concat/text@1"
        )

        self.assertEqual(first, second)
        self.assertEqual((root, child, leaf), first.ancestry)
        self.assertEqual(
            compute_ancestry_hash((ROOT_REF, CHILD_REF, LEAF_REF)),
            first.ancestry_hash,
        )

    def test_resolves_graph_owned_static_reference_for_exact_definition_anchor(
        self,
    ) -> None:
        registry = ModuleRegistry(self.store)
        registry.register(builtin_text_concat.definition())
        instance = ModuleInstanceRevision(
            module_instance_revision_ref="module-instance:text-concat@1",
            graph_revision_ref=GRAPH_REF,
            module_instance_ref="text-concat",
            module_ref="builtin.text.concat",
            module_version="1",
            config_ref="config:text-concat@1",
            config_hash="sha256:config-1",
            input_port_contract={"a": "REQUIRED_LATEST", "b": "TRIGGER"},
            output_port_contract={"text": {"type": "string"}},
            static_composite_path=("root",),
            static_accounting_scope_ref=CHILD_REF,
        )
        graph = GraphRepository(self.store, registry).publish(GRAPH_REF, instance)
        self.resolver.publish(root_scope())
        self.resolver.publish(child_scope())

        resolved = self.resolver.resolve(
            graph.module_instance_revision.static_accounting_scope_ref,
            graph.graph_revision_ref,
            graph.module_instance_revision.module_instance_revision_ref,
        )

        self.assertEqual(CHILD_REF, resolved.accounting_scope_ref)

    def test_immutable_identity_rejects_conflicting_republication(self) -> None:
        original = child_scope()
        self.resolver.publish(original)

        self.assertEqual(original, self.resolver.publish(original))
        self.assert_scope_error(
            "ACCOUNTING_SCOPE_IDENTITY_CONFLICT",
            lambda: self.resolver.publish(replace(original, state="ARCHIVED")),
        )

    def test_second_scope_for_same_definition_anchor_is_rejected(self) -> None:
        original = child_scope()
        self.resolver.publish(original)

        self.assert_scope_error(
            "ACCOUNTING_SCOPE_IDENTITY_CONFLICT",
            lambda: self.resolver.publish(
                replace(original, accounting_scope_ref="accounting:conflict")
            ),
        )

    def test_unresolved_scope_reference_fails_closed(self) -> None:
        self.assert_scope_error(
            "UNRESOLVED_ACCOUNTING_SCOPE_REFERENCE",
            lambda: self.resolver.resolve(
                "accounting:missing", GRAPH_REF, "module-instance:missing@1"
            ),
        )

    def test_leaf_graph_revision_mismatch_fails_closed(self) -> None:
        self.resolver.publish(root_scope())

        self.assert_scope_error(
            "ACCOUNTING_SCOPE_BINDING_INVALID",
            lambda: self.resolver.resolve(ROOT_REF, "graph:other@1", GRAPH_REF),
        )

    def test_leaf_definition_anchor_mismatch_fails_closed(self) -> None:
        self.resolver.publish(root_scope())

        self.assert_scope_error(
            "ACCOUNTING_SCOPE_BINDING_INVALID",
            lambda: self.resolver.resolve(ROOT_REF, GRAPH_REF, "graph:other@1"),
        )

    def test_missing_parent_fails_closed(self) -> None:
        self.resolver.publish(child_scope())

        self.assert_scope_error(
            "ACCOUNTING_SCOPE_ANCESTRY_INVALID",
            lambda: self.resolver.resolve(
                CHILD_REF, GRAPH_REF, "module-instance:text-concat@1"
            ),
        )

    def test_cycle_fails_closed(self) -> None:
        first_ref = "accounting:cycle/a"
        second_ref = "accounting:cycle/b"
        self.resolver.publish(
            scope(
                first_ref,
                "module-instance:cycle-a@1",
                (first_ref,),
                parent_accounting_scope_ref=second_ref,
            )
        )
        self.resolver.publish(
            scope(
                second_ref,
                "module-instance:cycle-b@1",
                (second_ref,),
                parent_accounting_scope_ref=first_ref,
            )
        )

        self.assert_scope_error(
            "ACCOUNTING_SCOPE_ANCESTRY_INVALID",
            lambda: self.resolver.resolve(
                first_ref, GRAPH_REF, "module-instance:cycle-a@1"
            ),
        )

    def test_malformed_parent_reference_fails_closed(self) -> None:
        self.resolver.publish(root_scope())
        self.store.connection.execute(
            """
            UPDATE accounting_scopes
            SET parent_accounting_scope_ref = '   '
            WHERE accounting_scope_ref = ?
            """,
            (ROOT_REF,),
        )

        self.assert_scope_error(
            "ACCOUNTING_SCOPE_ANCESTRY_INVALID",
            lambda: self.resolver.resolve(ROOT_REF, GRAPH_REF, GRAPH_REF),
        )

    def test_parent_graph_ownership_mismatch_fails_closed(self) -> None:
        self.resolver.publish(root_scope(graph_revision_ref="graph:other@1"))
        self.resolver.publish(child_scope())

        self.assert_scope_error(
            "ACCOUNTING_SCOPE_ANCESTRY_INVALID",
            lambda: self.resolver.resolve(
                CHILD_REF, GRAPH_REF, "module-instance:text-concat@1"
            ),
        )

    def test_ancestry_hash_corruption_fails_closed(self) -> None:
        self.resolver.publish(root_scope())
        self.resolver.publish(child_scope())
        self.store.connection.execute(
            """
            UPDATE accounting_scopes
            SET ancestry_hash = 'sha256:corrupt'
            WHERE accounting_scope_ref = ?
            """,
            (CHILD_REF,),
        )

        self.assert_scope_error(
            "ACCOUNTING_SCOPE_ANCESTRY_INVALID",
            lambda: self.resolver.resolve(
                CHILD_REF, GRAPH_REF, "module-instance:text-concat@1"
            ),
        )

    def test_same_history_resolves_identically_after_database_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "nyron.db"
            with SQLiteStore(database) as initial_store:
                initial = AccountingScopeResolver(initial_store)
                initial.publish(root_scope())
                initial.publish(child_scope())
                before = initial.resolve(
                    CHILD_REF, GRAPH_REF, "module-instance:text-concat@1"
                )

            with SQLiteStore(database) as reopened_store:
                after = AccountingScopeResolver(reopened_store).resolve(
                    CHILD_REF, GRAPH_REF, "module-instance:text-concat@1"
                )

        self.assertEqual(before, after)

    def test_resolution_does_not_consult_dynamic_execution_provenance(self) -> None:
        parameters = inspect.signature(AccountingScopeResolver.resolve).parameters
        self.assertEqual(
            (
                "self",
                "accounting_scope_ref",
                "graph_revision_ref",
                "definition_anchor_ref",
            ),
            tuple(parameters),
        )
        source = inspect.getsource(AccountingScopeResolver.resolve).lower()
        for forbidden in (
            "packet",
            "delivery",
            "edge",
            "worker",
            "attempt",
            "workspace",
            "project",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
