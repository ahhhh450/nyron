# Nyron Project Coordination Status

> Canonical coordination fact source. Execution Agents must not modify this file unless a Task explicitly grants authority.

## Coordination

- Active Orchestrator: `Web GPT — Development Orchestrator`
- Development Director: `ACTIVE — Global Development Coordination Authority`
- Coordination Epoch: `3`
- Coordination Revision: `128`
- Revision CAS Basis: `Expected Epoch 3 / Expected Revision 127 — MATCHED`
- Last Accepted Production Commit: `e47511aef987cd9fa5c171e319971f90ab549bd2`
- Canonical Repository Finalization Merge: `8962743bfbc6385bf58ebb31a63f5e5442c5f391`
- Foundation Wave 2 Accepted Downstream Base: `fa12ad2ba51a010786ac307e8efd683bc1be832b`
- Development Gate: `PRODUCT NODE / VISUAL WORKFLOW DEVELOPMENT — OPEN`
- Current Gate: `TRACK E NODE FOUNDATION REVIEW + PARALLEL TRACK D NETWORK FOUNDATION REVIEW`
- Current Mode: `TRACK E PRIMARY / TRACK D REVIEW SUPPORT IN PARALLEL / OTHER SUPPORT ON CONCRETE PRODUCT NEED`
- Primary Milestone: `MODULE ASSEMBLY NODE FOUNDATION`
- Target Acceptance Milestone: `NODE FOUNDATION v0.1`
- Latest Handoff Pointer: `coordination/handoffs/LATEST.md`
- Agent Availability: `coordination/AGENT_AVAILABILITY.md`
- Parallelism Policy: `DYNAMIC / DEPENDENCY + WRITE-SURFACE + REVIEW + INTEGRATION CAPACITY DRIVEN`
- Track Coordination Mode Policy: `PRODUCT-VERTICAL-SLICE DRIVEN — SUPPORT TRACKS OPEN ONLY WHEN A CONCRETE PRODUCT NODE REQUIRES A MISSING CAPABILITY OR OPERATOR/DIRECTOR EXPLICITLY RESUMES AN EXISTING TASK`

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

Current handoff:
`coordination/handoffs/NYRON_DEVELOPMENT_HANDOFF_2026-08-28_R2.md`

## Agent Routing

- `Claude`: `AVAILABLE — ACTIVE DEVELOPMENT / REVIEW LANE`.
- `Codex`: `AVAILABLE — OPERATOR-CONFIRMED RESTORED`.
- `DeepSeek`: `AVAILABLE` for simple/mechanical/low-risk implementation, regression, schema consistency and targeted verification.
- `GPT / Web GPT`: orchestration only by default.

Claude and Codex are both eligible for development and independent review. Review independence is session/execution-identity based unless a concrete Task requires stricter cross-model independence.

Current parallel assignment:

```text
Task 172: Codex independent exact-SHA review of Task 171
Task 173: Claude independent exact-SHA review of Task 168
```

The two Review Tasks are read-only Production reviews of different exact SHAs and may run concurrently.

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

The Product canvas is a module assembly system. Runtime/canonical objects such as Attempt, EffectOperation, HumanResponse, CapabilityGrant, BudgetReservation and CredentialBinding remain internal unless a future Product requirement explicitly justifies a Product abstraction.

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
| `Track A — PWP / Context Backbone` | `STABLE / DOWNSTREAM USABLE` | Product/Runtime admission-context support. |
| `Track B — Distribution / Module Ecosystem` | `STABLE / DOWNSTREAM USABLE` | Exact module identity/resolution available; later Import/Install/Enable remains Product-demand driven. |
| `Track C — Human Interaction / Approval` | `STABLE CORE / SUPPORT DEFERRED` | Suspension/resume and external HumanResponse ingress deferred until Human Approval Node requires them. |
| `Track D — External Interfaces / Workspace Boundary` | `NETWORK FOUNDATION DELIVERED / PENDING REVIEW; CONSEQUENTIAL PRODUCTION CLOSED` | Task 168 socket-free Network foundation delivered; Task 173 independently reviews it. Real Network/Provider dispatch remains CLOSED. |
| `Track E — Product / Visual Workflow` | `PRIMARY / REVIEW GATE` | Task 172 independently reviews exact Task-171 Node Foundation delivery. |

## Current Live Task Table

| State | Task | Meaning |
|---|---|---|
| `ACTIVE / READY` | `NYRON-T-20260828-172` | Codex independent HIGH-risk exact-SHA Review of Task 171 delivery `30998e73f1471921ab9b1b201fa8ea6227dc71f6`. |
| `ACTIVE / READY` | `NYRON-T-20260828-173` | Claude independent HIGH-risk exact-SHA Review of Task 168 Network foundation delivery `276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`. |
| `DELIVERED / PENDING INDEPENDENT REVIEW` | `NYRON-T-20260828-171` | Claude Product Node foundation implementation SUCCESS; 458 passed, 2 skipped; not accepted or merged as Production. |
| `DELIVERED / PENDING INDEPENDENT REVIEW` | `NYRON-T-20260828-168` | Codex Network admission/classification foundation SUCCESS; 573 passed, 2 skipped, 393 subtests; real network behavior intentionally absent. |
| `COMPLETED / GO` | `NYRON-T-20260828-170` | Product readiness SUCCESS; `GO_BOUNDED_IMPLEMENTATION`. |
| `DEFERRED / NOT STARTED` | `NYRON-T-20260828-169` | Human suspension/resume + response ingress readiness; resume only for Human Approval Node need. |

## Task 171 / 172 — Product Node Foundation

Task 171:
- Implementation Session: `Claude — Product Node Foundation Implementation Session`.
- Branch: `task/NYRON-T-20260828-171-node-foundation-v0-1`.
- Exact Delivery SHA: `30998e73f1471921ab9b1b201fa8ea6227dc71f6`.
- Result: `SUCCESS`.
- Reported validation: `458 passed, 2 skipped, 380 subtests passed`.
- Reported persisted/restarted E2E: `Text Input → Mock LLM → Text Output` through Product → Graph → existing Runtime.
- State: `PENDING_INDEPENDENT_REVIEW`.

Task 172:
- Assigned Reviewer: `Codex — Independent Node Foundation Exact-SHA Review Session`.
- Review Independence: `REQUIRED / CROSS-MODEL`.
- Exact Review Target: `30998e73f1471921ab9b1b201fa8ea6227dc71f6`.
- Production mutation: `DENIED`.
- Mandatory adversarial focus: Graph multi-instance/Edge atomic publish; Task-170 F-001/F-002 closure; cardinality semantics; pre-171 SQLite reopen compatibility; Task-171 F-003 severity; Product/Graph/Runtime ownership; reproducibility; complexity.

## Task 168 / 173 — Network Foundation

Task 168:
- Implementation Session: `Codex — Network Foundation Implementation Session`.
- Required Base: `d1fd31b1770871f1b96ec1a76250874c8b69ec11`.
- Branch: `task/NYRON-T-20260828-168-network-foundation`.
- Exact Delivery SHA: `276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`.
- Result: `SUCCESS`.
- Focused validation reported: `19 passed`.
- Full regression reported: `573 passed, 2 skipped, 393 subtests passed`.
- Delivered scope: socket-free requested/effective-destination normalization/classification, NETWORK_ACCESS scope data, and admission-only boundary revalidation of Attempt/fencing/Grant/Lease/PREPARED Effect.
- Explicit non-goal preserved: no DNS/socket/TLS/HTTP/proxy client/Provider SDK/live transport; no real consequential Network Effect; no Recovery/retry semantics.
- Task-136 `F01` remains open; real-consequential portion of Task-136 `F03` remains open.
- Real Network Production: `CLOSED`.
- Real Provider Production: `CLOSED`.
- State: `PENDING_INDEPENDENT_REVIEW`.

Task 173:
- Assigned Reviewer: `Claude — Independent Network Foundation Exact-SHA Review Session`.
- Original Implementation: `Codex — Task 168`.
- Review Independence: `REQUIRED / CROSS-MODEL`.
- Exact Review Target: `276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`.
- Production mutation: `DENIED`.
- Mandatory focus: effective-destination classification; IPv4/IPv6/mapped IPv6/special ranges; redirect/proxy/reuse; Attempt/fencing/Grant/Lease/PREPARED Effect authority; Credential orthogonality; no live network behavior; replay/restart; Task-136 F01/F03 preservation; complexity.

## Accepted / Usable Foundation

Important accepted/downstream-usable foundation includes:

- PWP core: `f3b6b0d022111dfc854f537c361ca5eb46516584`;
- Distribution identity/exact-resolution: `b2ec8e2e79745fee75a9dfdde7d6ab4cebe5f863`;
- Human Interaction core: `a85507b9b74e0f6b68a65460d9e5a4f19aa79f93`;
- Provider foundation: `fdf6e78061d57039a6e59813b76877ab2d7e2bf6`;
- Credential foundation: `d1fd31b1770871f1b96ec1a76250874c8b69ec11`;
- Module / Graph / Runtime / Capability / Resource / Effect / Recovery / Accounting foundations already accepted in the Foundation lineage;
- IngressRoute / Runtime ingress / IsolationProfile / Effect historical-outcome work where their own independent acceptance evidence applies.

Accepted for downstream dependency use does not itself mean merged to main, Last Accepted Production, release, or Global Accepted.

## Acceptance / Integration Distinction

```text
Implementation Result SUCCESS
!= Review PASS
!= Director Acceptance
!= Integration
!= Global Accepted
```

Parallel accepted SHAs converge only through explicit integration when convergence is required.

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

## Network-Specific Guardrails

```text
requested destination != effective destination authority
host authorization != selected-peer authorization
credential != network authority
PREPARED required before any future consequential dispatch
FENCED != retry clearance
admission evidence != proof of external consequence/no-consequence
```

Real Network/Provider Production gates remain CLOSED until their own consequential implementation + review gates explicitly open them.

## Standard Review / Finding Decision Tree

```text
Implementation SUCCESS
        ↓
Independent Review
        ├─ PASS → Director Acceptance decision
        ├─ PASS_WITH_FINDINGS → classify blocking/non-blocking
        ├─ FAIL → Targeted Fix → Targeted Re-Review
        └─ ESCALATION_REQUIRED → Lead Design Authority
```

## Open Findings / Debt

### Product / Graph

- `NYRON-T-20260828-170-F-001` — implementer claims CLOSED in Task 171; `PENDING TASK 172 VERIFICATION`.
- `NYRON-T-20260828-170-F-002` — implementer claims CLOSED in Task 171; `PENDING TASK 172 VERIFICATION`.
- `NYRON-T-20260828-171-F-003` — `ARCHITECTURE / NON_BLOCKING` per implementer; severity `PENDING TASK 172 VERIFICATION`.

### Network / External Interfaces

- Task-136 `F01` — OPEN; no non-bypassable real consequential network execution path yet.
- Task-136 real-consequential `F03` — OPEN; no real OS/network enforcement/transport boundary in Task 168.
- `NYRON-T-20260828-166-F-001` — SECURITY / NON_BLOCKING / STANDING; `ResolvedCredentialHandle` must never cross into low-trust plugin/module/network-facing code.

### Pre-existing Non-Blocking Debt

- `NYRON-T-20260826-078-F-001` — Accounting canonical policy/reservation lacks explicit DELETE immutability guard; no current delete path.
- `NYRON-T-20260826-078-F-002` — reservation dimension replay identity is order-sensitive.
- `NYRON-T-20260826-078-F-003` — focused validation branch coverage debt.
- `R-096-03 / NYRON-T-20260826-098-F-004 / NYRON-T-20260826-097-F-001` — historical process/session-name record-only debt.

## Standing Interlocks

- `NYRON-T-20260825-038-F-001` — SECURITY / NARROWED / OPEN; less-trusted filesystem/managed-root namespace mutation activates blocking review.
- `NYRON-T-20260826-043-F-001` — ARCHITECTURE / NON_BLOCKING / OPEN; synchronous SQLite single-writer assumption remains mandatory; genuine concurrency/pools/raw writers/process-distributed authority trigger revalidation.
- `NYRON-T-20260826-048-F-001` — IMPLEMENTATION / NON_BLOCKING / OPEN; Effect recovery caller ergonomics.
- `NYRON-T-20260826-056-F-001` — IMPLEMENTATION / NON_BLOCKING / OPEN; cross-version schema migration/rebuild debt.

## Revision Decisions

### Revision 122 / Epoch 3
- Track E became primary; Task 168 moved to Product-priority pause; Task 169 deferred; Task 170 created.

### Revision 123 / Epoch 3
- Product-phase Handoff and NODE FOUNDATION v0.1 intent recorded.

### Revision 124 / Epoch 3
- Task 170 readiness completed GO; Task 171 opened.

### Revision 125 / Epoch 3
- Claude/Codex role-neutral routing and session-based review independence clarified; Task 171 rebound to Claude before implementation start.

### Revision 126 / Epoch 3
- Task 171 delivered SUCCESS; Task 172 exact-SHA Review created.

### Revision 127 / Epoch 3
- Operator confirmed Codex restored; unstarted Task 172 safely rebound to Codex for cross-model review.

### Revision 128 / Epoch 3

- CAS against `Epoch 3 / Revision 127` succeeded; Revision advances to `128` without changing Epoch.
- Operator reported Task 168 complete; Repository evidence confirmed `SUCCESS` on branch `task/NYRON-T-20260828-168-network-foundation` at exact content delivery SHA `276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`.
- Task 168 is corrected from the stale Product-priority `PAUSED` snapshot to `DELIVERED / PENDING INDEPENDENT REVIEW`.
- The delivered Network slice remains admission/classification-only and socket-free; it does not open real Network or Provider Production and does not close Task-136 F01 or real-consequential F03.
- Task `NYRON-T-20260828-173` is created for mandatory HIGH-risk independent exact-SHA Review, assigned to a fresh Claude session reviewing the Codex delivery.
- Task 172 (Codex reviewing Track E) and Task 173 (Claude reviewing Track D) are authorized to run concurrently because both are read-only exact-SHA reviews of distinct delivery lineages.
- Task 169 remains deferred.
- Last Accepted Production Commit remains unchanged pending Review + Director Acceptance/integration decisions.

Historical Revision 108–121 decisions remain available in Git history and are not invalidated by this compact current-state snapshot.

## Repository-Result Protocol

- Task instruction: `coordination/tasks/<TaskID>.md`
- Agent result: `coordination/results/<TaskID>.md`
- Review / Re-Review result follows `coordination/OUTPUT_FORMAT.md`.
- Checkpoint: `coordination/checkpoints/<TaskID>-<CheckpointID>.md`.
- Development Director reads Repository evidence directly; chat/session is trigger/status only.
- Agents must not update STATUS unless a Task explicitly grants authority.

## State Update Rule

Any key coordination change must be based on current Epoch/Revision, decided by the Active Orchestrator, increment Revision exactly once, preserve unresolved findings, and keep production delivery identity separate from later Result/coordination commits.
