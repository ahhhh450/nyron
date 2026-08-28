# Nyron Project Coordination Status

> Canonical coordination fact source. Execution Agents must not modify this file unless a Task explicitly grants authority.

## Coordination

- Active Orchestrator: `Web GPT — Development Orchestrator`
- Development Director: `ACTIVE — Global Development Coordination Authority`
- Coordination Epoch: `3`
- Coordination Revision: `134`
- Revision CAS Basis: `Expected Epoch 3 / Expected Revision 133 — MATCHED`
- Last Accepted Production Commit: `1a741c5c7370f50f9efbc3087c67359cebdd8b27`
- Canonical Repository Finalization Merge: `8962743bfbc6385bf58ebb31a63f5e5442c5f391`
- Foundation Wave 2 Accepted Downstream Base: `fa12ad2ba51a010786ac307e8efd683bc1be832b`
- Accepted Product Foundation: `NODE FOUNDATION v0.1 @ 1a741c5c7370f50f9efbc3087c67359cebdd8b27`
- Development Gate: `PRODUCT NODE / VISUAL WORKFLOW DEVELOPMENT — OPEN`
- Current Gate: `TRACK E — LLM PRODUCT NODE v0.1 READINESS`
- Current Mode: `TRACK E PRIMARY / TASK 180 ACTIVE / SUPPORT TRACKS PRODUCT-DEMAND DRIVEN`
- Primary Milestone: `USER-FACING PRODUCT NODE VERTICAL SLICES`
- Current Target: `LLM PRODUCT NODE v0.1 — REAL-PROVIDER-CAPABLE READINESS`
- Latest Handoff Pointer: `coordination/handoffs/LATEST.md`
- Agent Availability: `coordination/AGENT_AVAILABILITY.md`
- Parallelism Policy: `DYNAMIC / DEPENDENCY + WRITE-SURFACE + REVIEW + INTEGRATION CAPACITY DRIVEN`

## Repository Truth / Handoff Rule

```text
fetch latest main
→ read STATUS
→ read AGENT_AVAILABILITY
→ inspect current tasks/results/checkpoints
→ compare with Handoff
→ Repository wins on any mismatch
```

## Agent Routing

- `Claude`: AVAILABLE for development/review; multiple isolated sessions permitted.
- `Codex`: AVAILABLE for development/review.
- `DeepSeek`: AVAILABLE for simple/mechanical/low-risk implementation, regression, schema consistency and targeted verification.
- `GPT / Web GPT`: orchestration only by default.

Claude and Codex have no fixed developer/reviewer split. Review independence is session/execution-identity based unless a concrete Task explicitly requires stricter cross-model independence.

## Product Direction

```text
Module
  ↓
ProductNodeDefinition
  ↓
NodeInstance + Input/Output Ports + Connections
  ↓
VisualWorkflowRevision
  ↓ deterministic compile/project
GraphRevision
  ↓
Execution Runtime
```

Product Nodes are user-facing abstractions. Runtime canonical records remain internal unless a concrete Product requirement justifies exposure.

Development ordering remains:

```text
Product requirement
      ↓
Product Node / vertical slice
      ↓
identify exact missing system capability
      ↓
resume/open smallest Track A/B/C/D support slice
      ↓
return to Product Node
```

## Current Track Board

| Track | State | Current Role / Gate |
|---|---|---|
| `Track A — PWP / Context Backbone` | `STABLE / DOWNSTREAM USABLE` | Support Product/Runtime admission context on concrete demand. |
| `Track B — Distribution / Module Ecosystem` | `STABLE / DOWNSTREAM USABLE` | Exact module identity/resolution available; Import/Install/Enable remains Product-demand driven. |
| `Track C — Human Interaction / Approval` | `STABLE CORE / SUPPORT DEFERRED` | Suspension/resume and external HumanResponse ingress deferred until a Human Approval Node requires them. |
| `Track D — External Interfaces / Workspace Boundary` | `BOUNDED NETWORK FOUNDATION ACCEPTED / CONSEQUENTIAL PRODUCTION CLOSED` | Socket-free Network classification/admission foundation usable; real Network/Provider dispatch remains CLOSED. |
| `Track E — Product / Visual Workflow` | `PRIMARY / LLM NODE READINESS` | Node Foundation v0.1 accepted; Task 180 derives the smallest real-provider-capable LLM node slice and exact support gaps. |

## Current Live Task Table

| State | Task | Meaning |
|---|---|---|
| `ACTIVE / READY` | `NYRON-T-20260828-180` | Claude LLM Product Node v0.1 readiness / concrete Product→Provider→Credential→Network→Effect gap analysis. No Production mutation. |
| `COMPLETED / PASS` | `NYRON-T-20260828-179` | Final integrated exact-SHA Review PASS; Findings NONE. |
| `ACCEPTED` | `NYRON-T-20260828-178` | Integrated Node Foundation v0.1 Production SHA `1a741c5c7370f50f9efbc3087c67359cebdd8b27`. |
| `ACCEPTED — BOUNDED DOWNSTREAM USE` | `NYRON-T-20260828-168` | Socket-free Network classification/admission foundation at `276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`. |
| `DEFERRED / NOT STARTED` | `NYRON-T-20260828-169` | Human suspension/resume + response ingress; resume only for concrete Human Approval Node need. |

## NODE FOUNDATION v0.1 — ACCEPTED

Exact accepted Production SHA:

`1a741c5c7370f50f9efbc3087c67359cebdd8b27`

Acceptance evidence:

- Task 178 integration: `SUCCESS`.
- Exact parents:
  - `e07a7bcf853e3091561f64fd7343cf6b30ad6369` — Fix A / Task 176 PASS.
  - `80ea8ddc330851f09d405040b7729e447bbe7ace` — Fix B / Task 177 PASS.
- Task 179 final independent Review: `PASS`, Findings `NONE`.
- Full integrated regression independently reproduced: `469 passed, 2 skipped, 380 subtests passed`.
- Persisted/restarted `Text Input → Mock LLM → Text Output` through Product → Graph → existing Runtime: PASS.
- Combined `MULTI_SOURCE TRIGGER` + later-instance admission adversarial scenario: PASS.
- Director Acceptance: `coordination/checkpoints/NYRON-T-20260828-179-DIRECTOR-ACCEPTANCE.md`.

Closed blockers:

- `NYRON-T-20260828-172-F-001` — CLOSED.
- `NYRON-T-20260828-172-F-002` — CLOSED.
- `NYRON-T-20260828-171-F-003` — CLOSED.

## Task 180 — LLM Product Node v0.1 Readiness

- Type: `READINESS / CROSS-LAYER GAP ANALYSIS`.
- Required Product base: `1a741c5c7370f50f9efbc3087c67359cebdd8b27`.
- Production mutation: `DENIED`.
- Objective: define the smallest truthful single-turn text LLM Product Node and determine exactly which accepted Provider/Credential/Network/Effect/Accounting capabilities can be reused vs which concrete bounded support slices are still missing.
- The Task must not open real Network/Provider gates or invent retry/recovery/credential semantics.
- Expected principal disposition is evidence-driven: `GO_PRODUCT_LLM_NODE_IMPLEMENTATION`, `GO_BOUNDED_SUPPORT_TASKS`, `BLOCKED_ARCHITECTURE`, or `NO_GO_SCOPE_TOO_BROAD`.
- Follow-up technical Tasks are created only after Task 180 identifies concrete Product-required gaps.

## Product Guardrails

```text
ModuleDefinition != ProductNodeDefinition
ProductNodeDefinition != NodeInstance
VisualWorkflowRevision != GraphRevision
Product Port != Runtime Packet/Delivery canonical truth
Product config != CapabilityGrant
Product declaration != execution authority
Product layout/UI metadata != Runtime canonical truth
```

Standing credential invariant:

`ResolvedCredentialHandle` must never cross into low-trust plugin/module/network-facing code.

## External / Consequential Production Gates

Still CLOSED unless separately implemented/reviewed/accepted:

- real Network dispatch;
- real Provider network dispatch;
- Browser consequential dispatch;
- general Filesystem mutation / less-trusted namespace mutation;
- concrete external HumanResponse adapters;
- Human suspension/resume integration.

Track D bounded Network foundation remains accepted at:

`276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`

Task-136 status remains:

- F01: `OPEN`;
- F02: `PARTIALLY ADDRESSED`;
- real-consequential F03: `OPEN`.

## Open Non-Blocking Debt / Standing Interlocks

- `NYRON-T-20260828-173-F-001` — real-connection-origin reuse evidence absent until real transport exists.
- `NYRON-T-20260826-078-F-001` — Accounting canonical policy/reservation has no explicit DELETE immutability guard; no current delete path.
- `NYRON-T-20260826-078-F-002` — reservation dimension replay identity is order-sensitive.
- `NYRON-T-20260826-078-F-003` — focused validation branch coverage debt.
- `R-096-03 / NYRON-T-20260826-098-F-004 / NYRON-T-20260826-097-F-001` — historical process/session-name record-only debt.
- `NYRON-T-20260825-038-F-001` — less-trusted filesystem/managed-root mutation activates blocking security review.
- `NYRON-T-20260826-043-F-001` — synchronous SQLite single-writer assumption; real concurrency/distributed authority triggers revalidation.
- `NYRON-T-20260826-048-F-001` — Effect recovery caller ergonomics.
- `NYRON-T-20260826-056-F-001` — general cross-version schema migration/rebuild debt remains.
- `NYRON-T-20260828-166-F-001` — `ResolvedCredentialHandle` must never cross into low-trust plugin/module/network-facing code.

## Revision Decisions

### Revision 133 / Epoch 3
- Task 179 PASS accepted integrated SHA `1a741c5c7370f50f9efbc3087c67359cebdd8b27` as `NODE FOUNDATION v0.1` and new Last Accepted Production Commit.
- Track E advanced to next Product vertical slice; real external consequential gates remained CLOSED.

### Revision 134 / Epoch 3
- CAS against `Epoch 3 / Revision 133` succeeded.
- Task 180 opened as the Product-mainline readiness task for the first real-provider-capable LLM Product Node.
- Task 180 is read-only against Production and must derive support work from concrete Product needs rather than reopening Track D speculatively.
- No external consequential gate changes in this revision.

Historical decisions remain available in Git history.

## Repository-Result Protocol

- Task instruction: `coordination/tasks/<TaskID>.md`
- Agent result: `coordination/results/<TaskID>.md`
- Review / Re-Review result follows `coordination/OUTPUT_FORMAT.md`
- Checkpoint: `coordination/checkpoints/<TaskID>-<CheckpointID>.md`
- Development Director reads Repository evidence directly; chat/session is trigger/status only.
- Agents must not update STATUS unless a Task explicitly grants authority.

## State Update Rule

Any key coordination change must be based on current Epoch/Revision, increment Revision exactly once, preserve unresolved findings, and keep Production delivery identity separate from later Result/coordination commits.
