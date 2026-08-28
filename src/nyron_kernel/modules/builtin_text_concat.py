"""builtin.text.concat@1 — the frozen PURE text concatenation module.

Frozen worked example: Universal_Runtime_Module_Design_Report_v0.1.md §32.
PURE contract (§28): identical module_ref@version + identical immutable
config + identical immutable inputs => identical observable outputs; the
implementation must not read clock, random, environment variables,
filesystem, network, or mutable globals.
"""

from __future__ import annotations

from typing import Any

from nyron_kernel.definitions import ModuleDefinition, PortDefinition

MODULE_REF = "builtin.text.concat"
MODULE_VERSION = "1"
MODULE_REF_VERSION = f"{MODULE_REF}@{MODULE_VERSION}"


def definition() -> ModuleDefinition:
    """Return the immutable ModuleDefinition matching frozen §32 exactly."""
    return ModuleDefinition(
        module_ref=MODULE_REF,
        version=MODULE_VERSION,
        input_port_definitions=(
            PortDefinition("a", {"type": "string"}, "REQUIRED_LATEST", "SINGLE_SOURCE"),
            PortDefinition("b", {"type": "string"}, "TRIGGER", "SINGLE_SOURCE"),
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
        metadata={"display_name": "Text Concatenate"},
    )


def execute(
    inputs: dict[str, Any],
    config: dict[str, Any],
    runtime_context: object,
) -> dict[str, Any]:
    """Deterministic concatenation: ``text = a + b`` (frozen §32).

    PURE: the returned value depends only on the two string inputs; no
    clock, randomness, environment, filesystem, network, or mutable
    module-level state is touched.  ``config`` and ``runtime_context``
    are accepted for the frozen ``execute`` ABI shape and deliberately
    unused.
    """
    a = inputs["a"]
    b = inputs["b"]
    if not isinstance(a, str) or not isinstance(b, str):
        raise TypeError("concat inputs 'a' and 'b' must be strings")
    return {"text": a + b}
