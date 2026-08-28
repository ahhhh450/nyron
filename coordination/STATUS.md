# Nyron Project Coordination Status

> Canonical coordination fact source. Execution Agents must not modify this file unless a Task explicitly grants authority.

## Coordination

- Active Orchestrator: `Web GPT — Development Orchestrator`
- Development Director: `ACTIVE — Global Development Coordination Authority`
- Coordination Epoch: `3`
- Coordination Revision: `129`
- Revision CAS Basis: `Expected Epoch 3 / Expected Revision 128 — MATCHED`
- Last Accepted Production Commit: `e47511aef987cd9fa5c171e319971f90ab549bd2`
- Canonical Repository Finalization Merge: `8962743bfbc6385bf58ebb31a63f5e5442c5f391`
- Foundation Wave 2 Accepted Downstream Base: `fa12ad2ba51a010786ac307e8efd683bc1be832b`
- Development Gate: `PRODUCT NODE / VISUAL WORKFLOW DEVELOPMENT — OPEN`
- Current Gate: `TRACK E NODE FOUNDATION — BLOCKING TARGETED FIXES + PARALLEL TRACK D NETWORK REVIEW`
- Current Mode: `TRACK E FIX A + FIX B IN PARALLEL / TRACK D REVIEW IN PARALLEL / OTHER SUPPORT ON CONCRETE PRODUCT NEED`
- Primary Milestone: `MODULE ASSEMBLY NODE FOUNDATION`
- Target Acceptance Milestone: `NODE FOUNDATION v0.1`
- Latest Handoff Pointer: `coordination/handoffs/LATEST.md`
- Agent Availability: `coordination/AGENT_AVAILABILITY.md`
- Parallelism Policy: `DYNAMIC / DEPENDENCY + WRITE-SURFACE + REVIEW + INTEGRATION CAPACITY DRIVEN`

## Repository Truth / Handoff Rule

A Handoff is a recovery aid, not canonical state.

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
- `Codex`: AVAILABLE — OPERATOR-CONFIRMED RESTORED; development/review both permitted.
- `DeepSeek`: AVAILABLE for simple/mechanical/low-risk implementation, regression, schema consistency and targeted verification.
- `GPT / Web GPT`: orchestration only by default.

Current parallel lanes:

```text
Task 173: Claude independent exact-SHA review of Task 168 Network foundation
Task 174: Codex targeted Fix A — Graph connection_policy + SQLite compatibility
Task 175: Claude targeted Fix B — multi-instance Runtime admission validation
```

Tasks 174 and 175 start from the same exact Task-171 delivery SHA and have disjoint primary mutable write surfaces. They must not silently absorb each other's findings. Convergence/integration occurs only after both exact delivery SHAs are durable and reviewed as required.

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

Product Node remains a Product abstraction, not a visualization of Runtime canonical records.

## Current Track Board

| Track | State | Current Role / Gate |
|---|---|---|
| `Track A — PWP / Context Backbone` | `STABLE / DOWNSTREAM USABLE` | Product/Runtime admission-context support. |
| `Track B — Distribution / Module Ecosystem` | `STABLE / DOWNSTREAM USABLE` | Exact module identity/resolution available; later Import/Install/Enable remains Product-demand driven. |
| `Track C — Human Interaction / Approval` | `STABLE CORE / SUPPORT DEFERRED` | Suspension/resume and external HumanResponse ingress deferred until Human Approval Node requires them. |
| `Track D — External Interfaces / Workspace Boundary` | `NETWORK FOUNDATION DELIVERED / PENDING REVIEW; CONSEQUENTIAL PRODUCTION CLOSED` | Task 168 delivered socket-free Network foundation; Task 173 independently reviews it. Real Network/Provider dispatch remains CLOSED. |
| `Track E — Product / Visual Workflow` | `PRIMARY / BLOCKING FIXES ACTIVE` | Task 172 review FAILED Task 171; Tasks 174 and 175 are the bounded blocking fixes. |

## Current Live Task Table

| State | Task | Meaning |
|---|---|---|
| `ACTIVE / READY` | `NYRON-T-20260828-174` | Codex targeted Graph cardinality/connection-policy + SQLite compatibility Fix from Task-172 F-001/F-002. |
| `ACTIVE / READY` | `NYRON-T-20260828-175` | Claude targeted multi-instance Runtime admission Fix for Task-171 F-003 as reclassified BLOCKING. |
| `ACTIVE / READY` | `NYRON-T-20260828-173` | Claude independent HIGH-risk exact-SHA Review of Task 168 Network foundation delivery `276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`. |
| `COMPLETED / FAIL` | `NYRON-T-20260828-172` | Independent exact-SHA Review of Task 171; three BLOCKING findings. |
| `DELIVERED / FIX REQUIRED` | `NYRON-T-20260828-171` | Claude Node Foundation implementation at `30998e73f1471921ab9b1b201fa8ea6227dc71f6`; not accepted. |
| `DELIVERED / PENDING INDEPENDENT REVIEW` | `NYRON-T-20260828-168` | Codex socket-free Network foundation at `276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`; real network behavior intentionally absent. |
| `COMPLETED / GO` | `NYRON-T-20260828-170` | Product readiness SUCCESS; `GO_BOUNDED_IMPLEMENTATION`. |
| `DEFERRED / NOT STARTED` | `NYRON-T-20260828-169` | Human suspension/resume + response ingress readiness; resume only for Human Approval Node need. |

## Task 171 / 172 — Node Foundation Review Outcome

Task 171 delivery:
- Exact SHA: `30998e73f1471921ab9b1b201fa8ea6227dc71f6`.
- Implementer: Claude Product Node Foundation session.
- Self-reported/full independently reproduced suite: `458 passed, 2 skipped, 380 subtests passed`.
- The pure/mock Product → Graph → existing Runtime E2E path exists, but the delivery is not acceptable until all blocking findings are closed.

Task 172 Review:
- Exact reviewed SHA: `30998e73f1471921ab9b1b201fa8ea6227dc71f6`.
- Review Result commit: `d573567da48ebd97c1c2037b777978e8819d5036` on `review/NYRON-T-20260828-172`.
- Principal Decision: `FAIL`.
- Actual reviewer: fresh independent Claude session/identity, separate from Task 171 implementation; same-model cross-session independence is permitted by `REVIEW_PROTOCOL.md`.

### Coordination race correction for Task 172

Revision 127 attempted to rebind unstarted Task 172 to Codex because no remote review branch/Result was visible. The later durable Result proves an independent Claude review session had already been executing locally and only pushed afterward. Therefore the `no branch/result => not started` inference was incomplete. The substantive Review is accepted as a valid independent session-based Review; the later attempted Codex rebind did not become the executing reviewer. This is a coordination-record correction only and does not alter the reviewed exact SHA or findings.

## Blocking Findings from Task 172

### `NYRON-T-20260828-172-F-001`
- Type: `CONTRACT / ARCHITECTURE`
- Severity: `BLOCKING`
- Owner/Fix: Task 174.
- Summary: Task 171 incorrectly derives `SINGLE_SOURCE | MULTI_SOURCE` from activation mode. Frozen Graph authority treats input `connection_policy` as independent and explicitly allows `MULTI_SOURCE TRIGGER`.
- Required direction: represent/use independent frozen connection policy; do not infer cardinality from activation mode.

### `NYRON-T-20260828-172-F-002`
- Type: `IMPLEMENTATION`
- Severity: `BLOCKING`
- Owner/Fix: Task 174.
- Summary: adding `graph_edges.role` only to `CREATE TABLE IF NOT EXISTS` breaks existing pre-171 SQLite databases; new edge publish fails with `no column named role`.
- Required direction: bounded `PRAGMA table_info` + additive `ALTER TABLE` compatibility path and old-database reopen regression test.

### `NYRON-T-20260828-171-F-003`
- Type: `ARCHITECTURE`
- Severity: `BLOCKING` — reclassified by Task 172 from implementer NON_BLOCKING.
- Owner/Fix: Task 175.
- Summary: `ExecutionAdmissionGate.admit()` validates only the first instance of a multi-instance Graph, contradicting the frozen admission requirement that all ModuleInstance/ModuleDefinition/config references resolve before canonical admission.
- Required direction: eagerly validate every instance before WorkflowExecution admission succeeds.

No Task-171 Production may be accepted/merged as NODE FOUNDATION v0.1 while these findings remain open.

## Task 174 — Fix A

- Agent: `Codex — Independent Targeted Fix Session A`.
- Exact base: `30998e73f1471921ab9b1b201fa8ea6227dc71f6`.
- Findings: Task-172 F-001/F-002.
- Primary write surfaces: Definitions/Graph/SQLite; Product/Module wiring only where mechanically required.
- Must not modify Runtime admission.
- Independent targeted Re-Review required after delivery.

## Task 175 — Fix B

- Agent: `Claude — Independent Targeted Fix Session B`.
- Exact base: `30998e73f1471921ab9b1b201fa8ea6227dc71f6`.
- Finding: Task-171 F-003 as reclassified BLOCKING.
- Primary write surface: `src/nyron_kernel/execution/admission.py` + focused tests.
- Must not modify Graph cardinality/connection-policy or SQLite compatibility.
- Independent targeted Re-Review required after delivery.

## Task 168 / 173 — Network Foundation

Task 168:
- Implementer: Codex Network Foundation session.
- Exact SHA: `276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`.
- Result: SUCCESS; focused `19 passed`; full regression `573 passed, 2 skipped, 393 subtests passed`.
- Scope is socket-free requested/effective-destination classification + admission-only foundation.
- No DNS/socket/TLS/HTTP/Provider SDK/live transport.
- Task-136 F01 and real-consequential F03 remain open.
- Real Network Production: CLOSED.
- Real Provider Production: CLOSED.

Task 173:
- Reviewer: independent Claude session.
- Exact target: `276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`.
- Production mutation: DENIED.

## Product-Specific Guardrails

```text
ModuleDefinition != ProductNodeDefinition
ProductNodeDefinition != NodeInstance
VisualWorkflowRevision != GraphRevision
Product Port != Runtime Packet/Delivery canonical truth
Product config != CapabilityGrant
Product declaration != execution authority
Product layout/UI metadata != Runtime canonical truth
```

## Acceptance / Integration Distinction

```text
Implementation Result SUCCESS
!= Review PASS
!= Director Acceptance
!= Integration
!= Global Accepted
```

Parallel fix SHAs are not automatically one accepted lineage. After Tasks 174/175 deliver, the Development Director must explicitly decide integration/convergence and targeted Re-Review order.

## External / Consequential Production Gates

- real Network dispatch: `CLOSED`;
- real Provider network dispatch: `CLOSED`;
- Browser consequential dispatch: `CLOSED`;
- general Filesystem mutation / less-trusted namespace mutation: `CLOSED / SECURITY-GATED`;
- concrete external HumanResponse adapters: `CLOSED`;
- Human suspension/resume integration: `DEFERRED` until Approval Node needs it.

## Pre-existing Non-Blocking Debt / Standing Interlocks

- `NYRON-T-20260826-078-F-001` — Accounting canonical policy/reservation has no explicit DELETE immutability guard; no current delete path.
- `NYRON-T-20260826-078-F-002` — reservation dimension replay identity order-sensitive.
- `NYRON-T-20260826-078-F-003` — focused validation branch coverage debt.
- `R-096-03 / NYRON-T-20260826-098-F-004 / NYRON-T-20260826-097-F-001` — historical process/session-name record-only debt.
- `NYRON-T-20260825-038-F-001` — less-trusted filesystem/managed-root mutation activates blocking security review.
- `NYRON-T-20260826-043-F-001` — synchronous SQLite single-writer assumption; real concurrency/distributed authority triggers revalidation.
- `NYRON-T-20260826-048-F-001` — Effect recovery caller ergonomics.
- `NYRON-T-20260826-056-F-001` — cross-version schema migration/rebuild debt, except the concrete Task-172 F-002 compatibility regression which is now blocking and owned by Task 174.
- `NYRON-T-20260828-166-F-001` — `ResolvedCredentialHandle` must never cross into low-trust plugin/module/network-facing code.

## Revision Decisions

### Revision 129 / Epoch 3

- CAS against `Epoch 3 / Revision 128` succeeded.
- Task 172 durable independent Review Result is recorded as `FAIL` with three blocking findings.
- The actual executing reviewer was an independent Claude session that had started locally before the attempted Codex rebind became observable; the race is corrected here without invalidating session-based review independence.
- Task 171 moves from pending review to `FIX REQUIRED`.
- Task 174 is created for Graph connection-policy/cardinality + SQLite old-database compatibility.
- Task 175 is created for all-instance Runtime admission validation.
- Tasks 174 and 175 are authorized to execute in parallel from exact Task-171 SHA because their primary mutable write surfaces are separate.
- Task 173 continues independently in parallel on Track D Network foundation.
- Last Accepted Production Commit remains unchanged.

Historical Revision 108–128 decisions remain available in Git history.

## Repository-Result Protocol

- Task instruction: `coordination/tasks/<TaskID>.md`
- Agent result: `coordination/results/<TaskID>.md`
- Review / Re-Review result follows `coordination/OUTPUT_FORMAT.md`
- Checkpoint: `coordination/checkpoints/<TaskID>-<CheckpointID>.md`
- Development Director reads Repository evidence directly; chat/session is trigger/status only.

## State Update Rule

Any key coordination change must be based on current Epoch/Revision, increment Revision exactly once, preserve unresolved findings, and keep Production delivery identity separate from later Result/coordination commits.
