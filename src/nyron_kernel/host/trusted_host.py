"""In-process TRUSTED MODULE MODE host boundary (frozen Module report §11, §29).

v0.1 supports TRUSTED MODULE MODE only and explicitly does NOT claim
hostile-plugin sandboxing.  The host exposes the frozen
``execute(inputs, config, runtime_context)`` ABI shape and invokes only
a known, registry-resolved trusted module implementation.  Module code
never receives the StateStore, SQLite connection, filesystem, network,
or capability objects.

``runtime_context`` must be exactly ``None`` or an exact instance of the
opaque, immutable ``RuntimeContext`` value type (see ``runtime_context``
module) and fails closed on any other value before module code runs — it
never forwards an arbitrary Python object (a raw store, a DB connection,
a raw Owner object, or any other handle) to a module. This host never
constructs a ``RuntimeContext`` itself and holds no knowledge of how one
is built; it only accepts an already-opaque value handed to it by the
caller and forwards it unchanged.

Before invocation, the host also requires the registered immutable
``ModuleDefinition`` to compare equal to the canonical contract returned
by the hosted implementation's own ``definition()`` — resolving the
right identity/version is not sufficient; the exact contract must match.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nyron_kernel.definitions import ModuleRegistry
from nyron_kernel.modules import builtin_text_concat

from .runtime_context import RuntimeContext


class TrustedHostError(RuntimeError):
    """Fail-closed host boundary error carrying a machine-readable code."""

    def __init__(self, code: str, **context: object) -> None:
        super().__init__(code)
        self.code = code
        self.context = context


@dataclass(frozen=True)
class Completed:
    """ModuleResult variant: the module produced outputs (frozen §11)."""

    outputs: dict[str, Any]


@dataclass(frozen=True)
class Failed:
    """ModuleResult variant: the module failed (frozen §11).

    ``Suspension`` is intentionally not implemented: this slice hosts a
    single PURE module that never suspends.
    """

    error: str
    reason_code: str = "MODULE_EXECUTION_FAILED"


_TRUSTED_IMPLEMENTATIONS: dict[tuple[str, str], Any] = {
    (
        builtin_text_concat.MODULE_REF,
        builtin_text_concat.MODULE_VERSION,
    ): builtin_text_concat.execute,
}

_TRUSTED_DEFINITIONS: dict[tuple[str, str], Any] = {
    (
        builtin_text_concat.MODULE_REF,
        builtin_text_concat.MODULE_VERSION,
    ): builtin_text_concat.definition,
}


class TrustedModuleHost:
    """Minimal in-process host for the single seeded trusted builtin.

    TRUSTED MODULE MODE: identity/version are validated against the
    registered immutable ``ModuleDefinition`` before invocation, and the
    exact pinned ``module_ref@version`` selects the implementation — no
    name-based / latest-by-name resolution. The registered definition
    must additionally compare equal to the hosted implementation's own
    canonical contract, and ``runtime_context`` must be exactly ``None``
    or an exact ``RuntimeContext`` instance — both checks fail closed
    before any module code runs.
    """

    def __init__(self, registry: ModuleRegistry) -> None:
        self._registry = registry

    def execute(
        self,
        module_ref_version: str,
        inputs: dict[str, Any],
        config: dict[str, Any],
        runtime_context: RuntimeContext | None = None,
    ) -> Completed | Failed:
        """Invoke the exact pinned module through the frozen execute ABI."""
        module_ref, version = self._parse_pinned_ref(module_ref_version)
        definition = self._registry.resolve(module_ref, version)
        if definition is None:
            raise TrustedHostError(
                "UNRESOLVED_MODULE_REFERENCE",
                module_ref=module_ref,
                version=version,
            )
        implementation = _TRUSTED_IMPLEMENTATIONS.get((module_ref, version))
        canonical_definition = _TRUSTED_DEFINITIONS.get((module_ref, version))
        if implementation is None or canonical_definition is None:
            raise TrustedHostError(
                "UNSUPPORTED_MODULE_REFERENCE",
                module_ref=module_ref,
                version=version,
            )
        if definition != canonical_definition():
            raise TrustedHostError(
                "DEFINITION_CONTRACT_MISMATCH",
                module_ref=module_ref,
                version=version,
            )
        if runtime_context is not None and type(runtime_context) is not RuntimeContext:
            raise TrustedHostError(
                "INVALID_RUNTIME_CONTEXT",
                runtime_context_type=type(runtime_context).__name__,
            )
        try:
            outputs = implementation(inputs, config, runtime_context)
        except Exception as error:  # noqa: BLE001 - trusted mode surfaces module failure
            return Failed(error=str(error))
        if not isinstance(outputs, dict):
            return Failed(
                error="module implementation returned a non-dict result",
                reason_code="MODULE_RESULT_INVALID",
            )
        return Completed(outputs=outputs)

    @staticmethod
    def _parse_pinned_ref(module_ref_version: str) -> tuple[str, str]:
        """Split a pinned ``module_ref@version`` into exactly ref and version."""
        if not isinstance(module_ref_version, str):
            raise TrustedHostError(
                "INVALID_MODULE_REFERENCE",
                module_ref_version=module_ref_version,
            )
        parts = module_ref_version.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise TrustedHostError(
                "INVALID_MODULE_REFERENCE",
                module_ref_version=module_ref_version,
            )
        return parts[0], parts[1]
