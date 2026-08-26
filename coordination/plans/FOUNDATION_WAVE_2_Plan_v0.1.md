# Nyron System Foundation Wave 2 Plan v0.1

Status: `ACTIVE ORCHESTRATION PLAN / NOT ARCHITECTURE`
Owner: `Web GPT — Development Orchestrator`
Date: `2026-08-27`

## Purpose

Continue System Foundation implementation after ARE-GATE-6 closure using the already-frozen architecture for:

1. Project / Workspace / Policy Context (PWP)
2. Distribution / Module Ecosystem
3. Human Interaction / Approval Authority
4. External Interfaces / Workspace Boundary

Product Node / Visual Workflow UX remains downstream and must consume the Foundation rather than redefine Kernel semantics.

## Canonical Starting Point

- Canonical repository main at planning start: `b6c62fd339a5ca51b68e275b32afda84d45cbfc9`
- Last Accepted Production: `e47511aef987cd9fa5c171e319971f90ab549bd2`
- ARE-GATE-6: `PASS / CLOSED`
- Repository convergence: `COMPLETE`
- Full kernel with Track C regressions: `416 passed, 2 skipped, 380 subtests passed`

## Wave Shape

### Phase 1 — PWP Backbone

Implement the smallest durable PWP core first:

- Project identity/lifecycle
- Workspace identity/lifecycle and same-Project parent relation
- immutable ProjectConfigRevision
- immutable WorkspaceConfigRevision
- immutable PolicyContextRevision
- immutable EnvironmentBindingRevision
- owner-local persistence
- historical exact-revision resolution
- fail-closed validation

Do not include Runtime admission wiring or IngressRoute in the first slice unless the frozen contract makes it unavoidable. The goal is to establish the stable PWP truth surface consumed by later modules.

PWP Core is HIGH risk and requires independent exact-SHA review before it becomes the Wave-2 backbone.

### Phase 2 — Bounded Parallel Modules

After PWP Core is independently accepted, open at most two write-disjoint implementation tracks:

- Distribution / Module Ecosystem
- Human Interaction / Approval Authority

They may proceed in parallel only while no unsettled Contract dependency and no overlapping production write surface exists.

### Phase 3 — External Interfaces / Workspace

Implement external boundary behavior only after the PWP context surface needed by workspace/external bindings is stable.

This phase is security-sensitive. Filesystem containment, symlink/mount/TOCTOU, process descendants, network effective destination, PREPARED-before-dispatch, credential non-authority and related frozen constraints require independent high-risk review.

### Phase 4 — Foundation Integration

Integrate PWP + Distribution + Human Interaction + External Interfaces with the accepted Graph / Runtime / Capability / Resource / Effect / Accounting / Recovery foundation.

Require:

- exact-SHA integration
- owner-boundary verification
- replay/idempotency/crash tests
- security boundary tests
- full kernel validation
- independent integrated review

### Phase 5 — Product Layer

Only after the System Foundation is sufficiently complete, proceed to D-006 Product Node / Visual Workflow UX. Product consumes frozen Kernel behavior; it does not introduce new Kernel primitives by convenience.

## Parallelism

Default maximum active production tracks: `2`.

PWP Backbone starts alone. Additional production tracks do not open until its first stable reviewed surface exists.

## Safety Rules

- Repository truth over chat memory.
- Frozen semantics change only by Architecture Finding + Lead Amendment.
- No Owner may mutate another Owner's canonical truth.
- Do not invent second execution paths, weakened UNKNOWN/fencing/retry semantics, mutable-current substitution, or cross-owner transaction assumptions.
- High-risk production candidates require independent exact-SHA review.
- Use bounded checkpoints; do not accumulate multiple unreviewed foundational surfaces before integration.

## Initial Route

First production Task: `NYRON-T-20260827-116 — PWP Core Identity / Revision Foundation`.
