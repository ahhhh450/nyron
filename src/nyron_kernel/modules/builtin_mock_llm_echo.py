"""builtin.mock.llm_echo@1 — PURE, deterministic, non-consequential Mock LLM.

Frozen PURE contract (Universal_Runtime_Module_Design_Report_v0.1.md §28):
identical module_ref@version + identical immutable config + identical
immutable inputs => identical observable outputs; no clock, random,
environment, filesystem, network, or mutable globals.

This module is intentionally fake: it performs no network call, Provider
call, Credential resolution, filesystem access, clock/random behavior,
Browser action, Human interaction, or consequential external Effect. It
exists only to prove the Product Node Foundation "Text Input -> Mock LLM
-> Text Output" vertical slice end to end through the real Runtime.
"""

from __future__ import annotations

from typing import Any

from nyron_kernel.definitions import ModuleDefinition, PortDefinition

MODULE_REF = "builtin.mock.llm_echo"
MODULE_VERSION = "1"
MODULE_REF_VERSION = f"{MODULE_REF}@{MODULE_VERSION}"

_RESPONSE_PREFIX = "[MOCK_LLM_RESPONSE] "


def definition() -> ModuleDefinition:
    """Return the immutable ModuleDefinition for the mock LLM."""
    return ModuleDefinition(
        module_ref=MODULE_REF,
        version=MODULE_VERSION,
        input_port_definitions=(
            PortDefinition("prompt", {"type": "string"}, "TRIGGER"),
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
        metadata={"display_name": "Mock LLM (Echo)"},
    )


def execute(
    inputs: dict[str, Any],
    config: dict[str, Any],
    runtime_context: object,
) -> dict[str, Any]:
    """Deterministic templated transform: ``text = PREFIX + prompt``.

    PURE: the returned value depends only on the ``prompt`` input; no
    network/model call is made. ``config`` and ``runtime_context`` are
    accepted for the frozen ``execute`` ABI shape and deliberately unused.
    """
    prompt = inputs["prompt"]
    if not isinstance(prompt, str):
        raise TypeError("mock LLM input 'prompt' must be a string")
    return {"text": f"{_RESPONSE_PREFIX}{prompt}"}
