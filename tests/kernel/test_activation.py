"""Acceptance tests for NYRON-T-20260825-025 transactional Activation."""

from __future__ import annotations

import inspect
import sqlite3
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from nyron_kernel.accounting import (
    AccountingScope,
    AccountingScopeResolver,
    compute_ancestry_hash,
)
from nyron_kernel.definitions import (
    ModuleDefinition,
    ModuleRegistry,
    PortDefinition,
)
from nyron_kernel.execution import (
    ActivationError,
    ActivationRepository,
    DeliveryProjector,
    ExecutionAdmissionGate,
    PacketRepository,
)
from nyron_kernel.graph import GraphRepository, ModuleInstanceRevision
from nyron_kernel.store import SQLiteStore


GRAPH_REF = "graph:activation@1"
MODULE_REVISION_REF = "module-instance:activation@1"
EXECUTION_REF = "execution:activation/1"
SCOPE_ROOT = "accounting:activation/root"
SCOPE_MODULE = "accounting:activation/module"


def definition() -> ModuleDefinition:
    return ModuleDefinition(
        module_ref="test.activation.inputs",
        version="1",
        input_port_definitions=(
            PortDefinition("trigger", {"type": "string"}, "TRIGGER"),
            PortDefinition("next", {"type": "string"}, "REQUIRED_NEXT"),
            PortDefinition("latest", {"type": "string"}, "REQUIRED_LATEST"),
            PortDefinition("optional", {"type": "string"}, "OPTIONAL_LATEST"),
        ),
        output_port_definitions=(PortDefinition("out", {"type": "string"}),),
        config_schema={"type": "object"},
        effect_classes=("PURE",),
        required_capability_types=(),
        execution_contract={"kind": "execute"},
    )


def module_instance() -> ModuleInstanceRevision:
    return ModuleInstanceRevision(
        module_instance_revision_ref=MODULE_REVISION_REF,
        graph_revision_ref=GRAPH_REF,
        module_instance_ref="activation-inputs",
        module_ref="test.activation.inputs",
        module_version="1",
        config_ref="config:activation@1",
        config_hash="sha256:activation-config",
        input_port_contract={
            "trigger": "TRIGGER",
            "next": "REQUIRED_NEXT",
            "latest": "REQUIRED_LATEST",
            "optional": "OPTIONAL_LATEST",
        },
        output_port_contract={"out": {"type": "string"}},
        static_composite_path=("root",),
        static_accounting_scope_ref=SCOPE_MODULE,
    )


class ActivationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self._prepare(self.store)
        self.activations = ActivationRepository(
            self.store, ModuleRegistry(self.store)
        )
        self.packets = PacketRepository(self.store)
        self.projector = DeliveryProjector(self.store)

    def tearDown(self) -> None:
        self.store.close()

    @staticmethod
    def _prepare(store: SQLiteStore) -> None:
        registry = ModuleRegistry(store)
        registry.register(definition())
        GraphRepository(store, registry).publish(GRAPH_REF, module_instance())
        accounting = AccountingScopeResolver(store)
        accounting.publish(
            AccountingScope(
                accounting_scope_ref=SCOPE_ROOT,
                graph_revision_ref=GRAPH_REF,
                definition_anchor_ref=GRAPH_REF,
                parent_accounting_scope_ref=None,
                scope_kind="GRAPH",
                ancestry_hash=compute_ancestry_hash((SCOPE_ROOT,)),
                created_from_definition_ref=GRAPH_REF,
                state="ACTIVE",
            )
        )
        accounting.publish(
            AccountingScope(
                accounting_scope_ref=SCOPE_MODULE,
                graph_revision_ref=GRAPH_REF,
                definition_anchor_ref=MODULE_REVISION_REF,
                parent_accounting_scope_ref=SCOPE_ROOT,
                scope_kind="MODULE",
                ancestry_hash=compute_ancestry_hash((SCOPE_ROOT, SCOPE_MODULE)),
                created_from_definition_ref=MODULE_REVISION_REF,
                state="ACTIVE",
            )
        )
        ExecutionAdmissionGate(
            store,
            GraphRepository(store, registry),
            registry,
            accounting,
            lambda ref, digest: (ref, digest)
            == ("config:activation@1", "sha256:activation-config"),
            lambda ref: ref == "runtime-policy:test@1",
        ).admit(
            admission_ref="admission:activation/1",
            execution_ref=EXECUTION_REF,
            graph_revision_ref=GRAPH_REF,
            runtime_policy_ref="runtime-policy:test@1",
        )
        for ordinal, port_ref in enumerate(
            ("trigger", "next", "latest", "optional")
        ):
            with store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO graph_edges(
                        graph_revision_ref, edge_ref, source_ref,
                        source_port_ref, target_module_instance_revision_ref,
                        target_port_ref, edge_ordinal, target_port_ordinal
                    ) VALUES (?, ?, ?, 'out', ?, ?, ?, ?)
                    """,
                    (
                        GRAPH_REF,
                        f"edge:{port_ref}",
                        MODULE_REVISION_REF,
                        MODULE_REVISION_REF,
                        port_ref,
                        ordinal,
                        ordinal,
                    ),
                )

    def _deliver(
        self,
        port_ref: str,
        packet_ref: str,
        *,
        execution_ref: str = EXECUTION_REF,
    ):
        packet = self.packets.commit(
            packet_ref=packet_ref,
            execution_ref=execution_ref,
            graph_revision_ref=GRAPH_REF,
            source_kind="MODULE_OUTPUT",
            source_ref=MODULE_REVISION_REF,
            source_port_ref="out",
            value_ref=f"value:{packet_ref}",
            schema_ref="schema:string@1",
            caused_by_ref=f"cause:{packet_ref}",
            created_event_ref=f"event:{packet_ref}",
        )
        return self.projector.project(packet.packet_ref, [f"edge:{port_ref}"])[0]

    def _ready_inputs(self, *, optional: bool = True) -> dict[str, object]:
        deliveries = {
            "latest_old": self._deliver("latest", "packet:latest-old"),
            "next_old": self._deliver("next", "packet:next-old"),
            "latest_new": self._deliver("latest", "packet:latest-new"),
            "next_new": self._deliver("next", "packet:next-new"),
        }
        if optional:
            deliveries["optional"] = self._deliver(
                "optional", "packet:optional"
            )
        deliveries["trigger"] = self._deliver("trigger", "packet:trigger")
        return deliveries

    def _create(
        self,
        *,
        activation_ref: str = "activation:1",
        execution_ref: str = EXECUTION_REF,
        module_revision_ref: str = MODULE_REVISION_REF,
        event_ref: str = "event:activation:1",
    ):
        return self.activations.create_next(
            activation_ref=activation_ref,
            execution_ref=execution_ref,
            module_instance_revision_ref=module_revision_ref,
            created_event_ref=event_ref,
        )

    @staticmethod
    def _binding(activation: object, port_ref: str):
        return next(
            binding
            for binding in activation.input_bindings  # type: ignore[attr-defined]
            if binding.port_ref == port_ref
        )

    def test_success_pins_exact_refs_bindings_and_created_evidence(self) -> None:
        deliveries = self._ready_inputs()

        activation = self._create()

        self.assertEqual(EXECUTION_REF, activation.execution_ref)
        self.assertEqual(GRAPH_REF, activation.graph_revision_ref)
        self.assertEqual(MODULE_REVISION_REF, activation.module_instance_revision_ref)
        self.assertEqual(SCOPE_MODULE, activation.static_accounting_scope_ref)
        self.assertEqual(
            deliveries["trigger"].delivery_ref, activation.trigger_delivery_ref
        )
        self.assertEqual(
            deliveries["next_old"].delivery_ref,
            self._binding(activation, "next").delivery_ref,
        )
        self.assertEqual(
            deliveries["latest_new"].delivery_ref,
            self._binding(activation, "latest").delivery_ref,
        )
        event = self.store.connection.execute(
            "SELECT * FROM activation_created_events"
        ).fetchone()
        self.assertEqual("event:activation:1", event["created_event_ref"])
        self.assertEqual("ActivationCreated", event["event_kind"])

    def test_unadmitted_execution_and_target_mismatch_fail_closed(self) -> None:
        with self.assertRaises(ActivationError) as unadmitted:
            self._create(execution_ref="execution:missing")
        self.assertEqual("WORKFLOW_EXECUTION_NOT_ADMITTED", unadmitted.exception.code)
        with self.assertRaises(ActivationError) as target:
            self._create(module_revision_ref="module-instance:missing")
        self.assertEqual("ACTIVATION_TARGET_MISMATCH", target.exception.code)
        self.assertEqual(0, self._count("activations"))
        self.assertEqual(0, self._count("delivery_bindings"))

    def test_target_from_another_graph_fails_closed(self) -> None:
        other_graph = "graph:activation-other@1"
        other_revision = "module-instance:activation-other@1"
        registry = ModuleRegistry(self.store)
        GraphRepository(self.store, registry).publish(
            other_graph,
            replace(
                module_instance(),
                graph_revision_ref=other_graph,
                module_instance_revision_ref=other_revision,
            ),
        )

        with self.assertRaises(ActivationError) as raised:
            self._create(module_revision_ref=other_revision)

        self.assertEqual("ACTIVATION_TARGET_MISMATCH", raised.exception.code)
        self.assertEqual(0, self._count("activations"))

    def test_delivery_execution_mismatch_is_not_eligible(self) -> None:
        self._deliver("latest", "packet:latest", execution_ref="execution:other")
        self._deliver("next", "packet:next", execution_ref="execution:other")
        self._deliver("trigger", "packet:trigger", execution_ref="execution:other")

        with self.assertRaises(ActivationError) as raised:
            self._create()

        self.assertEqual("ACTIVATION_TRIGGER_NOT_READY", raised.exception.code)
        self.assertEqual(0, self._count("delivery_bindings"))

    def test_oldest_trigger_is_selected_and_each_trigger_binds_once(self) -> None:
        self._deliver("latest", "packet:latest")
        self._deliver("next", "packet:next-1")
        oldest = self._deliver("trigger", "packet:trigger-old")
        newer = self._deliver("trigger", "packet:trigger-new")

        first = self._create()
        self.assertEqual(oldest.delivery_ref, first.trigger_delivery_ref)
        self._deliver("next", "packet:next-2")
        second = self._create(
            activation_ref="activation:2", event_ref="event:activation:2"
        )
        self.assertEqual(newer.delivery_ref, second.trigger_delivery_ref)
        self.assertEqual(
            "activation:1",
            self.activations.binding_activation_ref(oldest.delivery_ref),
        )
        self.assertEqual(
            "activation:2",
            self.activations.binding_activation_ref(newer.delivery_ref),
        )

    def test_projection_arrival_order_does_not_change_next_selection(self) -> None:
        committed = []
        for port_ref, suffix in (
            ("latest", "latest"),
            ("next", "next-old"),
            ("next", "next-new"),
            ("trigger", "trigger-old"),
            ("trigger", "trigger-new"),
        ):
            packet = self.packets.commit(
                packet_ref=f"packet:{suffix}",
                execution_ref=EXECUTION_REF,
                graph_revision_ref=GRAPH_REF,
                source_kind="MODULE_OUTPUT",
                source_ref=MODULE_REVISION_REF,
                source_port_ref="out",
                value_ref=f"value:{suffix}",
                schema_ref="schema:string@1",
                caused_by_ref=f"cause:{suffix}",
                created_event_ref=f"event:{suffix}",
            )
            committed.append((packet, port_ref))
        projected = {}
        for packet, port_ref in reversed(committed):
            delivery = self.projector.project(
                packet.packet_ref, [f"edge:{port_ref}"]
            )[0]
            projected[packet.packet_ref] = delivery

        activation = self._create()

        self.assertEqual(
            projected["packet:trigger-old"].delivery_ref,
            activation.trigger_delivery_ref,
        )
        self.assertEqual(
            projected["packet:next-old"].delivery_ref,
            self._binding(activation, "next").delivery_ref,
        )

    def test_replay_cannot_double_bind_or_create_second_activation(self) -> None:
        deliveries = self._ready_inputs()
        first = self._create()
        self.assertEqual(first, self._create())
        with self.assertRaises(ActivationError) as replay:
            self._create(
                activation_ref="activation:2", event_ref="event:activation:2"
            )
        self.assertEqual("ACTIVATION_TRIGGER_NOT_READY", replay.exception.code)
        self.assertEqual(1, self._count("activations"))
        self.assertEqual(2, self._count("delivery_bindings"))
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO delivery_bindings(
                        delivery_ref, packet_ref, graph_revision_ref, edge_ref,
                        target_port_ref, activation_ref
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        deliveries["trigger"].delivery_ref,
                        deliveries["trigger"].packet_ref,
                        GRAPH_REF,
                        deliveries["trigger"].edge_ref,
                        "trigger",
                        "activation:other",
                    ),
                )

    def test_activation_identity_conflict_cannot_rewrite_committed_fact(self) -> None:
        self._ready_inputs()
        before = self._create()

        with self.assertRaises(ActivationError) as raised:
            self._create(event_ref="event:activation:changed")

        self.assertEqual("ACTIVATION_IDENTITY_CONFLICT", raised.exception.code)
        self.assertEqual(before, self.activations.resolve("activation:1"))
        self.assertEqual(1, self._count("activations"))

    def test_latest_modes_snapshot_without_consuming_and_optional_can_be_null(
        self,
    ) -> None:
        deliveries = self._ready_inputs(optional=False)
        activation = self._create()

        self.assertEqual(
            deliveries["latest_new"].delivery_ref,
            self._binding(activation, "latest").delivery_ref,
        )
        self.assertIsNone(self._binding(activation, "optional").delivery_ref)
        self.assertIsNone(
            self.activations.binding_activation_ref(
                deliveries["latest_new"].delivery_ref
            )
        )
        optional = self._deliver("optional", "packet:optional-late")
        self.assertIsNone(
            self.activations.binding_activation_ref(optional.delivery_ref)
        )

    def test_optional_latest_present_selects_deterministic_latest(self) -> None:
        self._deliver("latest", "packet:latest")
        self._deliver("next", "packet:next")
        optional_old = self._deliver("optional", "packet:optional-old")
        optional_new = self._deliver("optional", "packet:optional-new")
        self._deliver("trigger", "packet:trigger")

        activation = self._create()

        self.assertEqual(
            optional_new.delivery_ref,
            self._binding(activation, "optional").delivery_ref,
        )
        self.assertIsNone(
            self.activations.binding_activation_ref(optional_old.delivery_ref)
        )
        self.assertIsNone(
            self.activations.binding_activation_ref(optional_new.delivery_ref)
        )

    def test_missing_required_input_leaves_all_deliveries_untouched(self) -> None:
        trigger = self._deliver("trigger", "packet:trigger")
        self._deliver("next", "packet:next")

        with self.assertRaises(ActivationError) as raised:
            self._create()

        self.assertEqual("ACTIVATION_REQUIRED_INPUT_NOT_READY", raised.exception.code)
        self.assertEqual(0, self._count("activations"))
        self.assertEqual(0, self._count("delivery_bindings"))
        self.assertIsNone(self.activations.binding_activation_ref(trigger.delivery_ref))

    def test_missing_required_next_leaves_trigger_unbound(self) -> None:
        self._deliver("latest", "packet:latest")
        trigger = self._deliver("trigger", "packet:trigger")

        with self.assertRaises(ActivationError) as raised:
            self._create()

        self.assertEqual("ACTIVATION_REQUIRED_INPUT_NOT_READY", raised.exception.code)
        self.assertEqual(0, self._count("activations"))
        self.assertEqual(0, self._count("delivery_bindings"))
        self.assertIsNone(self.activations.binding_activation_ref(trigger.delivery_ref))

    def test_input_contract_mismatch_fails_before_binding(self) -> None:
        self._ready_inputs()
        self.store.connection.execute(
            """
            UPDATE module_instance_revisions
            SET input_port_contract_json = '{"trigger":"TRIGGER"}'
            WHERE module_instance_revision_ref = ?
            """,
            (MODULE_REVISION_REF,),
        )

        with self.assertRaises(ActivationError) as raised:
            self._create()

        self.assertEqual("ACTIVATION_INPUT_CONTRACT_MISMATCH", raised.exception.code)
        self.assertEqual(0, self._count("delivery_bindings"))

    def test_failure_after_binding_before_activation_rolls_back_then_retries_once(
        self,
    ) -> None:
        deliveries = self._ready_inputs()
        self.store.connection.executescript(
            """
            CREATE TRIGGER inject_activation_failure
            BEFORE INSERT ON activations
            BEGIN SELECT RAISE(ABORT, 'injected activation failure'); END;
            """
        )

        with self.assertRaises(ActivationError) as raised:
            self._create()
        self.assertEqual("ACTIVATION_TRANSACTION_CONFLICT", raised.exception.code)
        self.assertEqual(0, self._count("delivery_bindings"))
        self.assertEqual(0, self._count("activations"))
        self.assertEqual(0, self._count("activation_created_events"))

        self.store.connection.execute("DROP TRIGGER inject_activation_failure")
        activation = self._create()
        self.assertEqual(
            deliveries["trigger"].delivery_ref,
            activation.trigger_delivery_ref,
        )
        self.assertEqual(1, self._count("activations"))
        self.assertEqual(1, self._count("activation_created_events"))

    def test_reopen_preserves_immutable_activation_and_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "nyron.db"
            with SQLiteStore(database) as initial:
                self._prepare(initial)
                packets = PacketRepository(initial)
                projector = DeliveryProjector(initial)
                for index, port in enumerate(("latest", "next", "trigger")):
                    packet = packets.commit(
                        packet_ref=f"packet:reopen:{index}",
                        execution_ref=EXECUTION_REF,
                        graph_revision_ref=GRAPH_REF,
                        source_kind="MODULE_OUTPUT",
                        source_ref=MODULE_REVISION_REF,
                        source_port_ref="out",
                        value_ref=f"value:{index}",
                        schema_ref="schema:string@1",
                        caused_by_ref=f"cause:{index}",
                        created_event_ref=f"event:{index}",
                    )
                    projector.project(packet.packet_ref, [f"edge:{port}"])
                before = ActivationRepository(
                    initial, ModuleRegistry(initial)
                ).create_next(
                    activation_ref="activation:reopen",
                    execution_ref=EXECUTION_REF,
                    module_instance_revision_ref=MODULE_REVISION_REF,
                    created_event_ref="event:activation:reopen",
                )

            with SQLiteStore(database) as reopened:
                repository = ActivationRepository(
                    reopened, ModuleRegistry(reopened)
                )
                after = repository.resolve("activation:reopen")
                binding_rows = reopened.connection.execute(
                    """
                    SELECT delivery_ref, activation_ref
                    FROM delivery_bindings ORDER BY delivery_ref
                    """
                ).fetchall()

        self.assertEqual(before, after)
        self.assertEqual(2, len(binding_rows))
        with self.assertRaises(FrozenInstanceError):
            before.execution_ref = "execution:changed"  # type: ignore[misc]

    def test_activation_path_has_no_accounting_or_later_execution_authority(
        self,
    ) -> None:
        source = inspect.getsource(ActivationRepository)
        for forbidden in (
            "accounting_scopes",
            "AccountingScopeResolver",
            "compute_ancestry_hash",
            "parent_accounting_scope_ref",
        ):
            self.assertNotIn(forbidden, source)
        tables = self.store.connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name IN ('runs', 'run_attempts')
            """
        ).fetchall()
        self.assertEqual([], tables)

    def _count(self, table: str) -> int:
        return self.store.connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]


if __name__ == "__main__":
    unittest.main()
