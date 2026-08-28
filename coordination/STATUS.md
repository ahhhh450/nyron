# Nyron Project Coordination Status

> Canonical coordination fact source. Execution Agents must not modify this file unless a Task explicitly grants authority.

## Coordination

- Active Orchestrator: `Web GPT — Development Orchestrator`
- Development Director: `ACTIVE — Global Development Coordination Authority`
- Coordination Epoch: `3`
- Coordination Revision: `130`
- Revision CAS Basis: `Expected Epoch 3 / Expected Revision 129 — MATCHED`; intervening Task/acceptance commits were coordination-only and did not alter the STATUS revision.
- Last Accepted Production Commit: `e47511aef987cd9fa5c171e319971f90ab549bd2`
- Canonical Repository Finalization Merge: `8962743bfbc6385bf58ebb31a63f5e5442c5f391`
- Foundation Wave 2 Accepted Downstream Base: `fa12ad2ba51a010786ac307e8efd683bc1be832b`
- Development Gate: `PRODUCT NODE / VISUAL WORKFLOW DEVELOPMENT — OPEN`
- Current Gate: `TRACK E NODE FOUNDATION — TARGETED RE-REVIEW / CONVERGENCE PENDING`
- Current Mode: `TRACK E RE-REVIEW A + B IN PARALLEL / TRACK D BOUNDED NETWORK FOUNDATION ACCEPTED / CONSEQUENTIAL NETWORK CLOSED`
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
Task 176: Claude targeted exact-SHA Re-Review of Task 174
Task 177: Codex targeted exact-SHA Re-Review of Task 175
```

These are read-only reviews of different exact SHAs and may run concurrently.

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

Product Node remains a Product abstraction, not a visualization or alternate owner of Runtime canonical records.

## Current Track Board

| Track | State | Current Role / Gate |
|---|---|---|
| `Track A — PWP / Context Backbone` | `STABLE / DOWNSTREAM USABLE` | Product/Runtime admission-context support. |
| `Track B — Distribution / Module Ecosystem` | `STABLE / DOWNSTREAM USABLE` | Exact module identity/resolution available; later Import/Install/Enable remains Product-demand driven. |
| `Track C — Human Interaction / Approval` | `STABLE CORE / SUPPORT DEFERRED` | Suspension/resume and external HumanResponse ingress deferred until Human Approval Node requires them. |
| `Track D — External Interfaces / Workspace Boundary` | `BOUNDED NETWORK FOUNDATION ACCEPTED / CONSEQUENTIAL PRODUCTION CLOSED` | Task 168 accepted for downstream dependency use after Task 173 `PASS_WITH_FINDINGS`; no real Network/Provider dispatch. |
| `Track E — Product / Visual Workflow` | `PRIMARY / TARGETED RE-REVIEW ACTIVE` | Tasks 174/175 delivered the blocking fixes; Tasks 176/177 independently re-review them before convergence. |

## Current Live Task Table

| State | Task | Meaning |
|---|---|---|
| `ACTIVE / READY` | `NYRON-T-20260828-176` | Claude targeted Re-Review of Task 174 exact SHA `e07a7bcf853e3091561f64fd7343cf6b30ad6369`. |
| `ACTIVE / READY` | `NYRON-T-20260828-177` | Codex targeted Re-Review of Task 175 exact SHA `80ea8ddc330851f09d405040b7729e447bbe7ace`. |
| `DELIVERED / PENDING TARGETED RE-REVIEW` | `NYRON-T-20260828-174` | Codex Fix A SUCCESS; Graph connection_policy/cardinality + old-SQLite compatibility. |
| `DELIVERED / PENDING TARGETED RE-REVIEW` | `NYRON-T-20260828-175` | Claude Fix B SUCCESS; all-instance Runtime admission validation. |
| `COMPLETED / PASS_WITH_FINDINGS` | `NYRON-T-20260828-173` | Independent review of Task 168 Network foundation. |
| `ACCEPTED — BOUNDED DOWNSTREAM USE` | `NYRON-T-20260828-168` | Socket-free Network classification/admission foundation accepted; real Network remains CLOSED. |
| `COMPLETED / FAIL` | `NYRON-T-20260828-172` | Independent exact-SHA review of Task 171; three blocking findings triggered Tasks 174/175. |
| `DELIVERED / FIXES UNDER RE-REVIEW` | `NYRON-T-20260828-171` | Node Foundation base delivery `30998e73f1471921ab9b1b201fa8ea6227dc71f6`; not accepted until findings close and fixes converge. |
| `COMPLETED / GO` | `NYRON-T-20260828-170` | Product readiness `GO_BOUNDED_IMPLEMENTATION`. |
| `DEFERRED / NOT STARTED` | `NYRON-T-20260828-169` | Human suspension/resume + response ingress; resume only for Human Approval Node need. |

## Track E — Review / Fix State

### Task 172 Review of Task 171

- Reviewed exact SHA: `30998e73f1471921ab9b1b201fa8ea6227dc71f6`.
- Result commit: `d573567da48ebd97c1c2037b777978e8819d5036`.
- Principal Decision: `FAIL`.
- Valid independent reviewer: fresh Claude session/identity separate from Task 171 implementation. The later attempted Codex rebind was a coordination race and did not become the executing reviewer.

Blocking findings:

1. `NYRON-T-20260828-172-F-001` — frozen Graph requires independent `connection_policy`; activation-mode-derived cardinality incorrectly rejected legal `MULTI_SOURCE TRIGGER`.
2. `NYRON-T-20260828-172-F-002` — `graph_edges.role` addition broke reopen/publish on pre-171 SQLite databases.
3. `NYRON-T-20260828-171-F-003` — multi-instance `ExecutionAdmissionGate.admit()` checked only the first instance; reclassified BLOCKING.

### Task 174 — Fix A delivered

- Agent: Codex.
- Exact base: `30998e73f1471921ab9b1b201fa8ea6227dc71f6`.
- Exact delivery SHA: `e07a7bcf853e3091561f64fd7343cf6b30ad6369`.
- Result: `SUCCESS`.
- Reported full suite: `460 passed, 2 skipped, 380 subtests passed`.
- Claimed closure: F-001 + F-002.
- Key changes: independent input-port `connection_policy`; Graph cardinality reads it directly; `MULTI_SOURCE TRIGGER` regression; bounded `PRAGMA table_info(graph_edges)` + additive `ALTER TABLE ... role`; pre-171 reopen/publish regression.
- Independent targeted Re-Review: Task 176.

### Task 175 — Fix B delivered

- Agent: Claude.
- Exact base: `30998e73f1471921ab9b1b201fa8ea6227dc71f6`.
- Exact delivery SHA: `80ea8ddc330851f09d405040b7729e447bbe7ace`.
- Result: `SUCCESS`.
- Reported full suite: `467 passed, 2 skipped, 380 subtests passed`.
- Claimed closure: Task-171 F-003.
- Key change: `ExecutionAdmissionGate.admit()` validates ModuleDefinition/config/accounting-scope for every `ModuleInstanceRevision` before canonical admission.
- Independent targeted Re-Review: Task 177.

### Convergence rule

Tasks 174 and 175 both start from the same Task-171 exact base and are separate fix lineages. Even if Tasks 176 and 177 PASS, **NODE FOUNDATION v0.1 is not yet a single accepted Production lineage**.

After both targeted Re-Reviews close their findings, create one explicit convergence/integration Task that combines both accepted fix SHAs, resolves any interaction, runs the full suite plus Product `Text Input → Mock LLM → Text Output` persisted/restarted E2E, and produces one exact integrated SHA for final Director acceptance.

## Track D — Network Foundation Acceptance

Task 168 delivery:
- Exact SHA: `276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`.
- Implementer: Codex.
- Scope: socket-free requested/effective destination classification + NETWORK_ACCESS admission-only boundary revalidation.
- No DNS/socket/TLS/HTTP/proxy client/Provider SDK/live transport.

Task 173 independent review:
- Result commit: `1b3128fad2a0940080394759f7892a4d83f7a34e`.
- Decision: `PASS_WITH_FINDINGS`.
- Director Acceptance checkpoint: `coordination/checkpoints/NYRON-T-20260828-168-DIRECTOR-ACCEPTANCE.md`.
- Accepted only for bounded downstream dependency use.

Carried finding:
- `NYRON-T-20260828-173-F-001` — ARCHITECTURE / NON_BLOCKING / OPEN: connection-origin reuse guard currently compares caller-supplied identities without durable real-connection origin state. Revalidate when real transport/connection reuse is introduced.

Task-136 status remains truthful:
- F01: OPEN — no non-bypassable real consequential Network path.
- F02: PARTIALLY ADDRESSED — boundary-time revalidation mechanism exists but is not yet wired exclusively to a real adapter.
- real-consequential F03: OPEN.

Real Network Production: `CLOSED`.
Real Provider Network Production: `CLOSED`.

## Accepted / Usable Foundation

Important downstream-usable foundations include:

- PWP core: `f3b6b0d022111dfc854f537c361ca5eb46516584`;
- Distribution identity/exact-resolution: `b2ec8e2e79745fee75a9dfdde7d6ab4cebe5f863`;
- Human Interaction core: `a85507b9b74e0f6b68a65460d9e5a4f19aa79f93`;
- Provider foundation: `fdf6e78061d57039a6e59813b76877ab2d7e2bf6`;
- Credential foundation: `d1fd31b1770871f1b96ec1a76250874c8b69ec11`;
- bounded Network classification/admission foundation: `276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`;
- accepted Module / Graph / Runtime / Capability / Resource / Effect / Recovery / Accounting foundations in their existing lineages.

Accepted for downstream dependency use does not itself mean merged to main, Last Accepted Production, release, or Global Accepted.

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

## External / Consequential Production Gates

- real Network dispatch: `CLOSED`;
- real Provider network dispatch: `CLOSED`;
- Browser consequential dispatch: `CLOSED`;
- general Filesystem mutation / less-trusted namespace mutation: `CLOSED / SECURITY-GATED`;
- concrete external HumanResponse adapters: `CLOSED`;
- Human suspension/resume integration: `DEFERRED` until Approval Node needs it.

## Open Non-Blocking Debt / Standing Interlocks

- `NYRON-T-20260828-173-F-001` — real-connection-origin reuse evidence absent until real transport exists.
- `NYRON-T-20260826-078-F-001` — Accounting canonical policy/reservation has no explicit DELETE immutability guard; no current delete path.
- `NYRON-T-20260826-078-F-002` — reservation dimension replay identity order-sensitive.
- `NYRON-T-20260826-078-F-003` — focused validation branch coverage debt.
- `R-096-03 / NYRON-T-20260826-098-F-004 / NYRON-T-20260826-097-F-001` — historical process/session-name record-only debt.
- `NYRON-T-20260825-038-F-001` — less-trusted filesystem/managed-root mutation activates blocking security review.
- `NYRON-T-20260826-043-F-001` — synchronous SQLite single-writer assumption; real concurrency/distributed authority triggers revalidation.
- `NYRON-T-20260826-048-F-001` — Effect recovery caller ergonomics.
- `NYRON-T-20260826-056-F-001` — general cross-version schema migration/rebuild debt remains; concrete `graph_edges.role` compatibility regression is separately owned by Task 174/176.
- `NYRON-T-20260828-166-F-001` — `ResolvedCredentialHandle` must never cross into low-trust plugin/module/network-facing code.

## Revision Decisions

### Revision 129 / Epoch 3

- Task 172 recorded FAIL against Task 171 with three BLOCKING findings.
- Tasks 174/175 created as disjoint parallel targeted fixes.

### Revision 130 / Epoch 3

- Task 173 completed `PASS_WITH_FINDINGS`; Task 168 is Director-Accepted for bounded downstream dependency use while all real Network/Provider consequential gates remain CLOSED.
- Task 174 delivered SUCCESS at `e07a7bcf853e3091561f64fd7343cf6b30ad6369` and enters targeted Re-Review Task 176.
- Task 175 delivered SUCCESS at `80ea8ddc330851f09d405040b7729e447bbe7ace` and enters targeted Re-Review Task 177.
- Tasks 176/177 are authorized to run in parallel with cross-model independence.
- NODE FOUNDATION v0.1 remains unaccepted until both blocking fix reviews pass and the two fix lineages converge into one integrated exact SHA.
- Last Accepted Production Commit remains unchanged.

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
