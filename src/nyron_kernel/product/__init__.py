"""NYRON-T-20260828-171 Product Node Foundation v0.1.

Product-owned Module -> ProductNodeDefinition -> NodeInstance / Ports /
NodeConnection -> VisualWorkflowRevision -> deterministic compiler ->
GraphRevision layer. See ``coordination/tasks/NYRON-T-20260828-171.md``.
"""

from .compiler import CompiledWorkflow, ProductCompileError, ProductGraphCompiler
from .node_definition import (
    ProductDefinitionError,
    ProductNodeDefinition,
    ProductNodeRegistry,
    ProductPortBinding,
)
from .workflow import (
    EntrypointBinding,
    NodeConnection,
    NodeInstance,
    OutputBinding,
    ProductWorkflowError,
    ProductWorkflowRepository,
    VisualWorkflowRevision,
    WorkflowLayoutRecord,
    WorkflowLayoutRepository,
)

__all__ = [
    "CompiledWorkflow",
    "EntrypointBinding",
    "NodeConnection",
    "NodeInstance",
    "OutputBinding",
    "ProductCompileError",
    "ProductDefinitionError",
    "ProductGraphCompiler",
    "ProductNodeDefinition",
    "ProductNodeRegistry",
    "ProductPortBinding",
    "ProductWorkflowError",
    "ProductWorkflowRepository",
    "VisualWorkflowRevision",
    "WorkflowLayoutRecord",
    "WorkflowLayoutRepository",
]
