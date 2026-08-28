"""builtin.text.constant@1 — PURE constant-text source module.

Frozen PURE contract (Universal_Runtime_Module_Design_Report_v0.1.md §28):
identical module_ref@version + identical immutable config + identical
immutable inputs => identical observable outputs; no clock, random,
environment, filesystem, network, or mutable globals.

This module has no meaningful input value: its single input port exists
only so a workflow-start Trigger Packet can activate it through the
ordinary Packet -> Delivery -> Activation path (Runtime ingress may not
bypass to a direct Activation). The emitted text comes entirely from the
immutable pinned ``config``.
"""

from __future__ import annotations

from typing import Any

from nyron_kernel.definitions import ModuleDefinition, PortDefinition

MODULE_REF = "builtin.text.constant"
MODULE_VERSION = "1"
MODULE_REF_VERSION = f"{MODULE_REF}@{MODULE_VERSION}"


def definition() -> ModuleDefinition:
    """Return the immutable ModuleDefinition for the constant-text source."""
    return ModuleDefinition(
        module_ref=MODULE_REF,
        version=MODULE_VERSION,
        input_port_definitions=(
            PortDefinition("start", {"type": "null"}, "TRIGGER", "SINGLE_SOURCE"),
        ),
        output_port_definitions=(
            PortDefinition("text", {"type": "string"}),
        ),
        config_schema={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        effect_classes=("PURE",),
        required_capability_types=(),
        execution_contract={"kind": "execute"},
        metadata={"display_name": "Text Constant"},
    )


def execute(
    inputs: dict[str, Any],
    config: dict[str, Any],
    runtime_context: object,
) -> dict[str, Any]:
    """Deterministic constant emission: ``text = config["text"]``.

    PURE: the returned value depends only on the immutable pinned config;
    ``inputs`` (the trigger pulse) and ``runtime_context`` are accepted for
    the frozen ``execute`` ABI shape and deliberately unused.
    """
    text = config["text"]
    if not isinstance(text, str):
        raise TypeError("constant config 'text' must be a string")
    return {"text": text}
