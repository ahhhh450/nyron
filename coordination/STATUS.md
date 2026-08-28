# Nyron Project Coordination Status

> Canonical coordination fact source. Execution Agents must not modify this file unless a Task explicitly grants authority.

## Coordination

- Active Orchestrator: `Web GPT — Development Orchestrator`
- Development Director: `ACTIVE — Global Development Coordination Authority`
- Coordination Epoch: `3`
- Coordination Revision: `123`
- Revision CAS Basis: `Expected Epoch 3 / Expected Revision 122 — MATCHED`
- Last Accepted Production Commit: `e47511aef987cd9fa5c171e319971f90ab549bd2`
- Canonical Repository Finalization Merge: `8962743bfbc6385bf58ebb31a63f5e5442c5f391`
- Foundation Wave 2 Accepted Downstream Base: `fa12ad2ba51a010786ac307e8efd683bc1be832b`
- Development Gate: `PRODUCT NODE / VISUAL WORKFLOW DEVELOPMENT — OPEN`
- Current Gate: `TRACK E — MODULE ASSEMBLY NODE FOUNDATION READINESS`
- Current Mode: `TRACK E PRIMARY / TRACK A+B+C+D SUPPORT ON CONCRETE PRODUCT NEED`
- Primary Milestone: `MODULE ASSEMBLY NODE FOUNDATION`
- Target Acceptance Milestone: `NODE FOUNDATION v0.1`
- Latest Handoff Pointer: `coordination/handoffs/LATEST.md`
- Agent Availability: `coordination/AGENT_AVAILABILITY.md`
- Parallelism Policy: `DYNAMIC / DEPENDENCY + WRITE-SURFACE + REVIEW + INTEGRATION CAPACITY DRIVEN`
- Track Coordination Mode Policy: `PRODUCT-VERTICAL-SLICE DRIVEN — SUPPORT TRACKS OPEN ONLY WHEN A CONCRETE PRODUCT NODE REQUIRES A MISSING CAPABILITY`

## Repository Truth / Handoff Rule

A Handoff is a recovery aid, not canonical state.

New Director startup order:

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

## Current Agent Availability

Operational availability is authoritative in `coordination/AGENT_AVAILABILITY.md`.

- `Claude`: `AVAILABLE — OPERATOR-CONFIRMED RESTORED / HIGH-VALUE PRIORITY`.
- `Codex`: `AVAILABLE — FULL WEEKLY WINDOW / CONTROLLED PARALLELISM`.
- `DeepSeek`: `AVAILABLE` for bounded low-risk/mechanical work.
- `GPT / Web GPT`: `AVAILABLE FOR ORCHESTRATION`; not default Production implementation.

High-risk `Implementation Agent != Independent Reviewer` remains mandatory. Available capacity does not authorize speculative infrastructure expansion.

## Product Direction — Current Scheduling Authority

Nyron's Product target is:

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

The user-facing canvas is a module assembly system similar in interaction model to ComfyUI / Langflow / Flowise.

**Product Node is not Runtime-object visualization.** Runtime/canonical objects such as `Attempt`, `EffectOperation`, `HumanResponse`, `CapabilityGrant`, `BudgetReservation`, `CredentialBinding` and similar authority/evidence records remain internal mechanisms unless a future Product requirement explicitly justifies a user-facing abstraction.

Development ordering:

```text
Product requirement
      ↓
Product Node abstraction / vertical slice
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
| `Track A — PWP / Context Backbone` | `STABLE / DOWNSTREAM USABLE` | Support Product/Runtime admission context when a concrete node needs an extension. |
| `Track B — Distribution / Module Ecosystem` | `STABLE / DOWNSTREAM USABLE` | Exact module identity/resolution foundation is available; later Import/Install/Enable work is Product-demand driven. |
| `Track C — Human Interaction / Approval` | `STABLE CORE / SUPPORT DEFERRED` | Human Interaction core remains valid. Suspension/resume and external HumanResponse ingress are deferred until Human Approval Node requires them. |
| `Track D — External Interfaces / Workspace Boundary` | `BOUNDED SUPPORT / CONSEQUENTIAL PRODUCTION CLOSED` | Provider/Credential and accepted foundations remain usable where accepted. Network/Filesystem/Browser/etc. resume only for concrete Product Node needs and under their own gates. |
| `Track E — Product / Visual Workflow` | `PRIMARY / ACTIVE READINESS` | Task `NYRON-T-20260828-170` is the P0 Module Assembly Node / Visual Workflow Core Readiness Task. |

## Current Live Task Table

| State | Task | Meaning |
|---|---|---|
| `ACTIVE / READY` | `NYRON-T-20260828-170` | Claude Track-E readiness. Primary Product mainline. |
| `PAUSED` | `NYRON-T-20260828-168` | Network foundation paused by Product scheduling hold; do not duplicate. Current pause is not a quota blocker. |
| `DEFERRED / NOT STARTED` | `NYRON-T-20260828-169` | Human suspension/resume + response ingress readiness; resume only for Human Approval Node need. |
| `WAITING REVIEW` | `NONE in current Product-mainline snapshot` | A HIGH-risk Product implementation will require independent exact-SHA Review after delivery. |

### Task 170

- Assigned Agent: `Claude — Product Node / Visual Workflow Architecture Readiness Session`.
- State: `ASSIGNED / READY`.
- Priority: `P0`.
- Production mutation: `DENIED`.
- Principal disposition: `GO_BOUNDED_IMPLEMENTATION | BLOCKED_BY_DEPENDENCY | ESCALATION_REQUIRED`.

### Task 168

- State: `PAUSED — PRODUCT-VERTICAL-SLICE HOLD / DO NOT DUPLICATE`.
- Resume the same Task ID only when a concrete Product Node needs bounded Network foundation or the Development Director explicitly reopens it.
- Real Network/Provider consequential Production remains closed.

### Task 169

- State: `DEFERRED / NOT STARTED`.
- No Result / task-scoped checkpoint existed at defer time.
- Resume the same Task only when Human Approval Product Node needs this Track-C slice.

## Accepted / Usable Foundation

The Product scheduling correction does not invalidate prior accepted work.

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

Parallel accepted SHAs converge only through an explicit Integration Task when convergence is required.

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

## NODE FOUNDATION v0.1 Acceptance Intent

If Task 170 returns `GO_BOUNDED_IMPLEMENTATION`, the next Product implementation should be scoped so that `NODE FOUNDATION v0.1` proves at least:

- Module → ProductNodeDefinition exact binding;
- stable input/output ports;
- persistent/restart-restorable NodeInstance;
- fail-closed Edge validation;
- immutable VisualWorkflowRevision;
- exact node/module version pinning;
- deterministic workflow compile/project;
- compile output enters existing Graph abstraction;
- restart reproduces the exact workflow;
- Product layer does not re-own Runtime canonical truth;
- one complete pure/mock Runtime execution path.

Preferred first end-to-end Product proof:

```text
Text Input
   ↓
Mock LLM
   ↓
Text Output
```

Exercise:

```text
Module → Node → Workflow → Graph → Runtime → Result
```

No real Network/Provider/Credential value/Browser/external effect in this first slice.

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

## Pause / Resume Rule

Temporary quota/auth/workspace/tooling failure:

```text
PAUSE SAME TASK
→ same Task ID
→ same scope
→ HANDOFF checkpoint where required
→ resume same Task later
```

Do not create a replacement technical Task merely because an Agent/tool temporarily failed.

## External / Consequential Production Gates

Until their own accepted implementation/review gates say otherwise:

- real Network dispatch: `CLOSED`;
- Browser consequential dispatch: `CLOSED`;
- general Filesystem mutation / less-trusted namespace mutation: `CLOSED / SECURITY-GATED`;
- real Provider network dispatch: `CLOSED`;
- concrete external HumanResponse adapters: `CLOSED`;
- Human suspension/resume integration: `DEFERRED` until Approval Node needs it.

Product Nodes may initially use pure/mock behavior that truthfully avoids these consequential boundaries.

## Open Non-Blocking Findings / Debt

### `NYRON-T-20260826-078-F-001`
- Type: `IMPLEMENTATION`
- Severity: `NON_BLOCKING`
- State: `OPEN / DEFERRED`
- Summary: no explicit DELETE immutability guard for canonical Accounting policy/reservation rows; current production exposes no delete path.

### `NYRON-T-20260826-078-F-002`
- Type: `IMPLEMENTATION / CONTRACT PRECISION`
- Severity: `NON_BLOCKING`
- State: `OPEN / DEFERRED`
- Summary: reservation dimension replay identity is order-sensitive, causing fail-closed false conflicts for reordered equivalent tuples.

### `NYRON-T-20260826-078-F-003`
- Type: `TEST`
- Severity: `NON_BLOCKING`
- State: `OPEN / DEFERRED`
- Summary: focused validation branch coverage debt retained for later bounded cleanup.

### `R-096-03 / NYRON-T-20260826-098-F-004 / NYRON-T-20260826-097-F-001`
- Type: `PROCESS`
- Severity: `NON_BLOCKING`
- State: `OPEN / RECORD-ONLY`
- Summary: historical Task-092 Result used the older session-name convention; no production correctness impact.

## Standing Interlocks

- `NYRON-T-20260825-038-F-001` — SECURITY / NARROWED / OPEN; less-trusted filesystem/managed-root namespace mutation activates blocking review.
- `NYRON-T-20260826-043-F-001` — ARCHITECTURE / NON_BLOCKING / OPEN; synchronous SQLite single-writer assumption remains mandatory. Genuine concurrency/pools/raw writers/process-distributed authority trigger revalidation.
- `NYRON-T-20260826-048-F-001` — IMPLEMENTATION / NON_BLOCKING / OPEN; Effect recovery caller ergonomics, out of current scope.
- `NYRON-T-20260826-056-F-001` — IMPLEMENTATION / NON_BLOCKING / OPEN; cross-version schema migration/rebuild debt, unaffected.
- `NYRON-T-20260828-166-F-001` — SECURITY / NON_BLOCKING / STANDING; `ResolvedCredentialHandle` itself must never cross into low-trust plugin/module/network-facing code.

## Revision Decisions

### Revision 122 / Epoch 3

- Development Director handoff CAS advanced the Coordination Epoch from 2 to 3 and Revision from 121 to 122.
- Track E became the primary Product development track.
- Task 168 moved to Product-demand pause; Task 169 moved to deferred/not-started; Task 170 was created for Track-E readiness.
- Claude/Codex restored availability superseded the older quota snapshot.

### Revision 123 / Epoch 3

- CAS against `Epoch 3 / Revision 122` succeeded; Revision advances to `123` without changing Epoch.
- Robust recovery Handoff is added at `coordination/handoffs/NYRON_DEVELOPMENT_HANDOFF_2026-08-28_R2.md`; `handoffs/LATEST.md` provides a stable pointer.
- Handoff is explicitly non-canonical and must be checked against current Repository state on every new Director startup.
- `coordination/AGENT_AVAILABILITY.md` is aligned with the Product-mainline priority and no longer points new work at the historical Provider closeout chain.
- Current live task classification is made explicit: 170 active/ready, 168 paused, 169 deferred, no current Product-mainline waiting-review Task.
- `NODE FOUNDATION v0.1` acceptance intent and the first Text Input → Mock LLM → Text Output vertical slice are recorded as the next implementation target if Task 170 returns GO.
- Pause/resume, Acceptance-vs-Integration, Product non-goals, and lower-level Track Pull Rule are preserved in the Handoff.
- `Last Accepted Production Commit` remains unchanged; Revision 123 is coordination-only and does not declare Product implementation accepted.

Historical Revision 108–121 decisions remain available in Git history and are not invalidated by this compact current-state snapshot.

## Repository-Result Protocol

Formal Agent handoff remains file-based:

- Task instruction: `coordination/tasks/<TaskID>.md`
- Agent result: `coordination/results/<TaskID>.md`
- Review / Re-Review result follows `coordination/OUTPUT_FORMAT.md`
- Checkpoint: `coordination/checkpoints/<TaskID>-<CheckpointID>.md`
- Development Director reads Repository evidence directly; chat/session is trigger/status only.
- Agents must not update this STATUS file unless a Task explicitly grants authority.

## State Update Rule

Any key coordination change must be based on current Epoch/Revision, decided by the Active Orchestrator, increment Revision exactly once, preserve unresolved findings, and keep production delivery identity separate from later Result/coordination commits.
