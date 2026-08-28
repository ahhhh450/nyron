"""builtin.text.identity@1 — PURE text pass-through/capture module.

Frozen PURE contract (Universal_Runtime_Module_Design_Report_v0.1.md §28):
identical module_ref@version + identical immutable config + identical
immutable inputs => identical observable outputs; no clock, random,
environment, filesystem, network, or mutable globals.

Minimal pass-through used as the ``product.text_output`` first-slice node:
it captures its single input value unchanged as its output, so the final
workflow output can be read as an ordinary Module output Packet without
inventing a separate "workflow output" Runtime primitive.
"""

from __future__ import annotations

from typing import Any

from nyron_kernel.definitions import ModuleDefinition, PortDefinition

MODULE_REF = "builtin.text.identity"
MODULE_VERSION = "1"
MODULE_REF_VERSION = f"{MODULE_REF}@{MODULE_VERSION}"


def definition() -> ModuleDefinition:
    """Return the immutable ModuleDefinition for the text pass-through."""
    return ModuleDefinition(
        module_ref=MODULE_REF,
        version=MODULE_VERSION,
        input_port_definitions=(
            PortDefinition("text", {"type": "string"}, "TRIGGER"),
        ),
        output_port_definitions=(
            PortDefinition("text", {"type": "string"}),
        ),
        config_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        effect_classes=("PURE",),
        required_capability_types=(),
        execution_contract={"kind": "execute"},
        metadata={"display_name": "Text Output"},
    )


def execute(
    inputs: dict[str, Any],
    config: dict[str, Any],
    runtime_context: object,
) -> dict[str, Any]:
    """Deterministic identity: ``text = text``.

    PURE: the returned value depends only on the ``text`` input; ``config``
    and ``runtime_context`` are accepted for the frozen ``execute`` ABI
    shape and deliberately unused.
    """
    text = inputs["text"]
    if not isinstance(text, str):
        raise TypeError("identity input 'text' must be a string")
    return {"text": text}
