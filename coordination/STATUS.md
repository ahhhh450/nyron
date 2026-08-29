# Nyron Project Coordination Status

> Canonical coordination fact source. Execution Agents must not modify this file unless a Task explicitly grants authority.

## Coordination

- Active Orchestrator: `Web GPT — Development Orchestrator`
- Development Director: `ACTIVE — Global Development Coordination Authority`
- Coordination Epoch: `3`
- Coordination Revision: `142`
- Revision CAS Basis: `Expected Epoch 3 / Expected Revision 141 — MATCHED`; Node/Orchestration Product direction was recorded and Task 188 opened as a read-only Product-mainline readiness task.
- Last Accepted Production Commit: `103a47324807f01c76990df7b5bca9d3668cb552`
- Accepted Product-Usable Base: `MODULE-BACKED NODE FOUNDATION v0.1 + TRACK-D FOUNDATIONS + BOUNDED RUNTIME/EFFECT SUPPORT @ 103a47324807f01c76990df7b5bca9d3668cb552`
- Development Gate: `PRODUCT NODE / VISUAL WORKFLOW DEVELOPMENT — OPEN`
- Current Gate: `GENERAL NODE CONTRACT / MULTI-AGENT ORCHESTRATION READINESS`
- Current Mode: `TASK 188 P0 GENERAL NODE READINESS + TASKS 186/187 REAL-PROVIDER SUPPORT READINESS IN PARALLEL / NO NEW PRODUCTION MUTATION YET`
- Primary Milestone: `GENERAL EXTENSIBLE NODE SYSTEM + DURABLE MULTI-AGENT ORCHESTRATION`
- Current Target: `GENERAL NODE DEFINITION / EXECUTION BINDING — MODULE IS OPTIONAL CAPABILITY SOURCE`
- Product Direction Record: `coordination/plans/NODE_VISUAL_WORKFLOW_ORCHESTRATION_DIRECTION_v0.1.md`
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

- `Claude`: AVAILABLE for development/review/security/architecture verification; currently assigned Task 186.
- `Codex`: AVAILABLE for development/review/integration; Task 188 is assigned to an independent Codex readiness session.
- `DeepSeek`: AVAILABLE; currently assigned Task 187 for mechanical Provider/Network inventory.
- `GPT / Web GPT`: orchestration only by default.

Claude and Codex have no fixed developer/reviewer split. Review independence is session/execution-identity based unless a concrete Task explicitly requires stricter cross-model independence.

## Current Track Board

| Track | State | Current Role / Gate |
|---|---|---|
| `Track A — PWP / Context Backbone` | `STABLE / DOWNSTREAM USABLE` | Product/Runtime admission-context support. |
| `Track B — Distribution / Module Ecosystem` | `STABLE / DOWNSTREAM USABLE` | Exact Module identity/resolution available; Module-backed Nodes consume this, but Node identity is no longer treated as equivalent to Module identity. |
| `Track C — Human Interaction / Approval` | `STABLE CORE / SUPPORT DEFERRED` | Human support remains deferred until concrete Node/orchestration demand; Wait/Input/Approval requirements may reactivate the smallest required slice. |
| `Track D — External Interfaces / Workspace Boundary` | `BOUNDED RUNTIME/EFFECT SUPPORT ACCEPTED / REAL CONSEQUENTIAL PRODUCTION CLOSED` | Tasks 186/187 continue as parallel support for future real LLM external I/O; they are not prerequisites for general Node/Orchestration work. |
| `Track E — Product / Visual Workflow` | `PRIMARY / GENERALIZATION READINESS` | Accepted v0.1 is retained as a Module-backed Node subset; Task 188 determines the smallest safe general Node/ExecutionBinding generalization and orchestration Runtime gaps. |

## Current Live Task Table

| State | Task | Meaning |
|---|---|---|
| `ACTIVE / READY` | `NYRON-T-20260829-188` | Codex HIGH-risk read-only General Node Contract / Multi-Agent Orchestration readiness; current Product P0. |
| `ACTIVE / READY` | `NYRON-T-20260828-186` | Claude HIGH-risk read-only real Provider/Network security readiness; parallel Track-D support, not Product-wide gate. |
| `ACTIVE / READY` | `NYRON-T-20260828-187` | DeepSeek read-only Provider/Credential/Network/Effect inventory and adversarial test matrix; parallel Track-D support. |
| `COMPLETED / PASS` | `NYRON-T-20260828-185` | Independent exact-SHA Review PASS of Task-184 delivery; Findings NONE. |
| `ACCEPTED` | `NYRON-T-20260828-184` | Bounded RuntimeContext + MODEL_INVOKE Effect support accepted at `103a47324807f01c76990df7b5bca9d3668cb552`. |
| `ACCEPTED` | `NYRON-T-20260828-181` | Product + Track-D convergence accepted at `a48a7e3005943f6a4e65844faaf6b0aeaad7b431`. |
| `COMPLETED / GO_BOUNDED_MODEL_INVOKE_EFFECT_IMPLEMENTATION` | `NYRON-T-20260828-182` | Frozen Effect-contract verification; Task-180 F-005 CLOSED. |
| `DEFERRED / NOT STARTED` | `NYRON-T-20260828-169` | Human suspension/resume + response ingress; resume only when a concrete orchestration/Human Node requirement needs it. |

## Product Direction Correction — General Node System

The previously accepted Node Foundation remains valid within its tested boundary, but its current Product contract requires every `ProductNodeDefinition` to bind one exact `ModuleDefinition@version`. That is now classified as a **Module-backed Node subset**, not the complete general Node abstraction.

Current intended relationship:

```text
Node System
  ├─ Built-in / Pure Node
  ├─ System-backed Node
  ├─ Module-backed Node
  └─ Composite Node
       ↓
NodeInstance / Connections / VisualWorkflowRevision
       ↓ deterministic compile / projection
Graph / Runtime
```

Binding principles under readiness review:

```text
Node System != Module System
Module is an optional capability source for a Node
NodeDefinition != NodeInstance
VisualWorkflowRevision != GraphRevision
Agent decision != canonical State truth
ordinary new Node should not require Workflow Core modification
```

The Development Director direction record is non-frozen and does not itself amend system architecture. Any required new cross-owner Runtime semantic must go through Architecture Finding -> Lead Design Authority.

## Task 188 — General Node / Orchestration Readiness

- Type: `HIGH-RISK READ-ONLY ARCHITECTURE / CONTRACT / IMPLEMENTATION READINESS`.
- Assigned: `Codex` independent readiness session.
- Exact accepted base: `103a47324807f01c76990df7b5bca9d3668cb552`.
- Reviews reuse/generalization of accepted Product Node foundation and current mandatory Module coupling.
- Must analyze General NodeDefinition, NodeExecutionBinding, Built-in/System/Module/Composite bindings, Graph/Runtime projection, Multi-Agent/child-session orchestration, hidden Runtime mechanisms, Retry/Loop/Concurrency/Cancel/Failure semantics, and the 31-node roadmap classification.
- Must return exactly one of `GO_BOUNDED_GENERAL_NODE_IMPLEMENTATION`, `ESCALATION_REQUIRED_NODE_RUNTIME_CONTRACT`, `BLOCKED_BY_DEPENDENCY`, `NO_GO_DIRECTION_REQUIRES_REDESIGN`.
- No Production mutation and no Frozen Architecture mutation.

## Accepted Product-Usable Runtime/Effect Base

Exact accepted Production SHA:

`103a47324807f01c76990df7b5bca9d3668cb552`

Acceptance evidence:

- Task 184 implementation: `SUCCESS`.
- Task 185 independent exact-SHA Review: `PASS`, Findings `NONE`.
- Full regression independently verified: `632 passed, 2 skipped, 393 subtests passed`.
- Existing persisted Product Node/Workflow/Graph path remains accepted within its tested Module-backed boundary.
- PURE Modules remain on `runtime_context=None`.
- Effect-capable Modules receive bounded RuntimeContext only from canonical current authority.
- Reviewer-originated test revoked a legitimate grant after RuntimeContext construction and proved dispatch revalidation fails closed.
- Reviewer-originated provider/model scope-widening attempt failed closed.
- MODEL_INVOKE PREPARED/ACTIVE/UNKNOWN/FENCED/replay/conflict-scope semantics comply with frozen D-004/D-008.
- Existing filesystem Effect behavior remains green.
- `ResolvedCredentialHandle` remains trusted-host-only.
- No real Provider/Network external I/O exists on this accepted base.
- Director Acceptance: `coordination/checkpoints/NYRON-T-20260828-185-DIRECTOR-ACCEPTANCE.md`.

## Task 180 Finding State

- `NYRON-T-20260828-180-F-001` — `CLOSED` by Task 181 + Task 183 + Director Acceptance.
- `NYRON-T-20260828-180-F-002` — `CLOSED` by Task 184 + Task 185 + Director Acceptance.
- `NYRON-T-20260828-180-F-003` — `OPEN`; carries Task-136 F01 raw-network bypass/isolation risk and must close before real Network Production GO.
- `NYRON-T-20260828-180-F-004` — `OPEN`; bounded Network broker does not yet verify expected Effect class and must close before real dispatch.
- `NYRON-T-20260828-180-F-005` — `CLOSED` by Task 182.

## Real Provider / Network Gate

Real Network Production and real Provider Production remain `CLOSED`.

Task-136 state remains:

- F01: `OPEN` — raw-network bypass/non-bypassable boundary unresolved for real transport.
- F02: `PARTIALLY ADDRESSED` — bounded boundary-time admission exists but is not yet the real consequential dispatch boundary.
- real-consequential F03: `OPEN` — truthful real network Effect/historical-outcome evidence is not yet implemented.

`NYRON-T-20260828-173-F-001` remains open until real connection-origin evidence is necessary. Task 186 must explicitly decide whether first-slice connection reuse can remain disabled so this debt need not be activated.

Standing credential invariant:

`ResolvedCredentialHandle` and secret values must never cross into low-trust plugin/module/Product/network-facing APIs.

## Parallel Track-D Security Preparation

### Task 186 — Real Provider/Network Security Gate Closure Readiness

- Type: `HIGH-RISK READ-ONLY SECURITY / ARCHITECTURE READINESS`.
- Assigned: `Claude`.
- Exact base: `103a47324807f01c76990df7b5bca9d3668cb552`.
- Owns readiness/disposition for Task-136 F01, remaining F02, real F03, Task-180 F-004 and first-slice Task-173 F-001 handling.
- Must return `GO_BOUNDED_SECURITY_GATE_IMPLEMENTATION`, `ESCALATION_REQUIRED_SECURITY_CONTRACT`, or `NO_GO_REAL_PROVIDER_GATE`.
- No Production/frozen-design mutation and no real external I/O.

### Task 187 — Concrete Adapter / Credential / Network Inventory

- Type: `READ-ONLY IMPLEMENTATION INVENTORY / TEST MATRIX`.
- Assigned: `DeepSeek`.
- Exact base: `103a47324807f01c76990df7b5bca9d3668cb552`.
- Mechanically traces current Provider/Credential/Network/RuntimeContext/Effect code, exact missing write surfaces and adversarial tests.
- Defers security/authority decisions to Task 186.
- No Production mutation and no external I/O.

Tasks 186/187 may continue in parallel with Task 188 because all three are read-only and share no mutable Production write surface.

## Real LLM Support Chain — Parallel Product Capability, Not Global Node Gate

1. Product + Track-D convergence — `ACCEPTED`.
2. Bounded RuntimeContext + MODEL_INVOKE Effect — `ACCEPTED @ 103a4732...`.
3. Task 186 security readiness + Task 187 mechanical inventory — `ACTIVE IN PARALLEL`.
4. If Task 186 permits: smallest bounded security-gate Production implementation.
5. Mandatory independent adversarial exact-SHA security Review.
6. Real Provider/Network consequential dispatch implementation only after explicit authorization.
7. Mandatory independent security Review of real external I/O.
8. Real LLM Node may then consume that capability under the General Node contract available at that time.

This chain does not block pure/control/system-backed Node design unless a specific Node actually requires external I/O.

## Product / Authority Guardrails

```text
Node System != Module System
ModuleDefinition != NodeDefinition
NodeDefinition != NodeInstance
VisualWorkflowRevision != GraphRevision
Product config != CapabilityGrant
Product declaration != execution authority
Agent decision != State truth
EffectOperation owner = Effect Authority
FENCED != retry clearance
```

## External / Consequential Production Gates

Still CLOSED unless separately implemented/reviewed/accepted:

- real Network dispatch;
- real Provider network dispatch;
- Browser consequential dispatch;
- general Filesystem mutation / less-trusted namespace mutation;
- concrete external HumanResponse adapters;
- Human suspension/resume integration.

## Open Non-Blocking Debt / Standing Interlocks

- `NYRON-T-20260828-180-F-003` / Task-136 F01 — raw-network bypass/isolation posture.
- `NYRON-T-20260828-180-F-004` — Network Effect-class validation gap before real dispatch.
- Task-136 remaining F02 and real-consequential F03.
- `NYRON-T-20260828-173-F-001` — durable real connection-origin reuse evidence; avoid activating by disabling reuse in first slice if permitted.
- `NYRON-T-20260826-078-F-001` — Accounting DELETE immutability guard debt.
- `NYRON-T-20260826-078-F-002` — reservation dimension replay identity is order-sensitive.
- `NYRON-T-20260826-078-F-003` — focused validation branch coverage debt.
- `NYRON-T-20260825-038-F-001` — less-trusted filesystem/managed-root mutation activates blocking security review.
- `NYRON-T-20260826-043-F-001` — synchronous SQLite single-writer assumption; real concurrency/distributed authority triggers revalidation.
- `NYRON-T-20260826-048-F-001` — Effect recovery caller ergonomics.
- `NYRON-T-20260826-056-F-001` — general cross-version schema migration/rebuild debt.
- `NYRON-T-20260828-166-F-001` — credential boundary invariant.

## Revision Decisions

### Revision 141 / Epoch 3
- Task 185 completed `PASS` with Findings `NONE` against exact SHA `103a47324807f01c76990df7b5bca9d3668cb552`.
- Development Director accepted that SHA as the Product-usable Runtime/Effect support base and closed Task-180 F-002.
- Tasks 186/187 opened for real Provider/Network readiness/inventory.

### Revision 142 / Epoch 3
- CAS against `Epoch 3 / Revision 141` succeeded.
- Product direction correction recorded at `coordination/plans/NODE_VISUAL_WORKFLOW_ORCHESTRATION_DIRECTION_v0.1.md`.
- Existing accepted Node Foundation is retained but reclassified for roadmap purposes as a **Module-backed Node subset**, because current `ProductNodeDefinition` and compiler mandate exact Module binding.
- Task 188 opened as P0 read-only General Node Contract / Multi-Agent Orchestration readiness.
- Tasks 186/187 continue in parallel as Track-D support for future real LLM external I/O, but no longer act as the global Product/Node gate.
- No Production acceptance was revoked; no Frozen Architecture was amended by this coordination change.

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
