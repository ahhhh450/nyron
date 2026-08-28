# Nyron Project Coordination Status

> Canonical coordination fact source. Execution Agents must not modify this file unless a Task explicitly grants authority.

## Coordination

- Active Orchestrator: `Web GPT — Development Orchestrator`
- Development Director: `ACTIVE — Global Development Coordination Authority`
- Coordination Epoch: `3`
- Coordination Revision: `122`
- Handoff CAS Basis: `Expected Epoch 2 / Expected Revision 121 — MATCHED`
- Last Accepted Production Commit: `e47511aef987cd9fa5c171e319971f90ab549bd2`
- Canonical Repository Finalization Merge: `8962743bfbc6385bf58ebb31a63f5e5442c5f391`
- Foundation Wave 2 Accepted Downstream Base: `fa12ad2ba51a010786ac307e8efd683bc1be832b`
- Development Gate: `PRODUCT NODE / VISUAL WORKFLOW DEVELOPMENT — OPEN`
- Current Gate: `TRACK E — MODULE ASSEMBLY NODE FOUNDATION READINESS`
- Current Mode: `TRACK E PRIMARY / TRACK A+B+C+D SUPPORT ON CONCRETE PRODUCT NEED`
- Primary Milestone: `MODULE ASSEMBLY NODE FOUNDATION`
- Agent Availability: `coordination/AGENT_AVAILABILITY.md`
- Parallelism Policy: `DYNAMIC / DEPENDENCY + WRITE-SURFACE + REVIEW + INTEGRATION CAPACITY DRIVEN`
- Track Coordination Mode Policy: `PRODUCT-VERTICAL-SLICE DRIVEN — SUPPORT TRACKS OPEN ONLY WHEN A CONCRETE PRODUCT NODE REQUIRES A MISSING CAPABILITY`

## Current Agent Availability

Operational availability is authoritative in `coordination/AGENT_AVAILABILITY.md`.

Current repository state records:

- `Claude`: `AVAILABLE — OPERATOR-CONFIRMED RESTORED / HIGH-VALUE PRIORITY`.
- `Codex`: `AVAILABLE — FULL WEEKLY WINDOW / CONTROLLED PARALLELISM`.
- `DeepSeek`: `AVAILABLE` for bounded low-risk/mechanical work.
- `GPT / Web GPT`: `AVAILABLE FOR ORCHESTRATION`; not default Production implementation.

High-risk `Implementation Agent != Independent Reviewer` remains mandatory. Restored capacity does not authorize speculative infrastructure expansion.

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

The user-facing canvas is a module assembly system similar in interaction model to ComfyUI / Langflow / Flowise. Runtime/canonical objects are internal mechanisms and MUST NOT automatically become Product Nodes.

Examples:

```text
LLM Node
→ Provider + Credential + Network + Accounting + Effect

Human Approval Node
→ HumanRequest + HumanResponse + HumanDecisionEvidence + Runtime suspension/resume

Filesystem Node
→ Workspace boundary + Capability + Resource/Lease
```

Development ordering is now Product-driven:

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

Do not return to the old scheduling model of completing every low-level subsystem before Product work begins.

## Current Track Board

| Track | State | Current Role / Gate |
|---|---|---|
| `Track A — PWP / Context Backbone` | `STABLE / DOWNSTREAM USABLE` | Support Product/Runtime admission context when a concrete node needs an extension. |
| `Track B — Distribution / Module Ecosystem` | `STABLE / DOWNSTREAM USABLE` | Exact module identity/resolution foundation is available; later Import/Install/Enable work is Product-demand driven. |
| `Track C — Human Interaction / Approval` | `STABLE CORE / SUPPORT DEFERRED` | Human Interaction core remains valid. Suspension/resume and external HumanResponse ingress are deferred until Human Approval Node requires them. |
| `Track D — External Interfaces / Workspace Boundary` | `BOUNDED SUPPORT / CONSEQUENTIAL PRODUCTION CLOSED` | Provider/Credential and other accepted foundations remain usable where accepted. Network/Filesystem/Browser/etc. resume only for concrete Product Node needs and only under their own gates. |
| `Track E — Product / Visual Workflow` | `PRIMARY / ACTIVE READINESS` | Task `NYRON-T-20260828-170` is the primary next Task: Module Assembly Node / Visual Workflow Core Readiness. |

## Active / Paused / Deferred Tasks

### `NYRON-T-20260828-170` — PRIMARY

- Track: `E — Product / Visual Workflow`.
- Assigned Agent: `Claude — Product Node / Visual Workflow Architecture Readiness Session`.
- State: `ASSIGNED / READY`.
- Priority: `P0`.
- Objective: determine the smallest frozen-authority-compatible Product Node foundation and deterministic `VisualWorkflowRevision -> GraphRevision` projection seam.
- Production mutation: `DENIED`; Result/evidence only.
- Required principal disposition: `GO_BOUNDED_IMPLEMENTATION | BLOCKED_BY_DEPENDENCY | ESCALATION_REQUIRED`.

### `NYRON-T-20260828-168` — PAUSED SUPPORT

- Track: `D — Network`.
- State: `PAUSED — PRODUCT-VERTICAL-SLICE HOLD / DO NOT DUPLICATE`.
- Current Agent availability is restored; the pause is scheduling/product-priority based, not a current quota blocker.
- Resume the same Task ID only when a concrete Product Node requires the bounded Network foundation or the Development Director explicitly reopens it.
- Real Network/Provider consequential Production remains closed.

### `NYRON-T-20260828-169` — DEFERRED SUPPORT

- Track: `C — Human Interaction / Approval`.
- State: `DEFERRED / NOT STARTED`.
- Repository verification at defer time found no Final Result and no Task-scoped `CP-001` checkpoint.
- Resume the same Task only when Human Approval Product Node creates the concrete need for suspension/resume + external response ingress readiness.
- Do not let this speculative support slice delay Track E.

## Accepted / Usable Foundation

The scheduling correction does not invalidate prior accepted work.

Still valid for downstream Product consumption where their own acceptance/gates permit:

- PWP / Context backbone;
- ModuleDefinition and Module architecture;
- Graph / GraphRevision canonical execution semantics;
- ExecutionAdmission;
- Packet -> Delivery -> Activation -> Run / Attempt lifecycle;
- Capability / Resource / Lease / Effect;
- Recovery and Accounting foundations;
- Distribution exact module identity/resolution;
- Human Interaction core;
- Provider foundation accepted ancestry used by later Credential/Network tasks;
- Credential foundation ancestry used by Task 168;
- IngressRoute / Runtime ingress accepted lineage where already reviewed;
- IsolationProfile / Effect historical-outcome work where already independently accepted.

The current Product milestone does **not** require all consequential external interfaces to be complete first.

## Standing Cross-System Invariants

```text
Packet -> Delivery -> Activation -> Run / Attempt
```

No second direct-Activation execution path.

```text
CapabilityGrant != ResourceLease != EffectOperation != BudgetReservation
```

```text
FENCED != no prior consequence != safe semantic replay
```

```text
unknown overlap -> conflicting
```

```text
revoke/replacement wins authority-consumption race -> reject new use
exact use admission wins -> durable pre-revoke in-flight work
```

```text
unresolved static_accounting_scope_ref -> execution admission denied
```

```text
retained canonical history pins PWP revision -> exact revision remains resolvable
```

```text
logical Owner != physical database placement
cross-owner SQL FK != foreign Owner authority proof
```

Product-specific guardrails now also include:

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

The Product-mainline correction does not open consequential external execution.

Until their own accepted implementation/review gates say otherwise:

- real Network dispatch: `CLOSED`;
- Browser consequential dispatch: `CLOSED`;
- general Filesystem mutation / less-trusted namespace mutation: `CLOSED / SECURITY-GATED`;
- real Provider network dispatch: `CLOSED`;
- concrete external HumanResponse adapters: `CLOSED`;
- speculative suspension/resume integration: `DEFERRED`.

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

- New Development Director session accepted the repository-backed handoff using CAS against `Epoch 2 / Revision 121`; Coordination Epoch advances to `3`, Revision to `122`.
- Repository `AGENT_AVAILABILITY.md` supersedes the older handoff quota snapshot: Claude and Codex are currently available under controlled parallelism.
- Product scheduling correction is adopted: `Track E — Product / Visual Workflow` becomes the primary Product development track.
- Prior accepted Foundation is preserved; this is a development-order correction, not architecture invalidation.
- Task `NYRON-T-20260828-168` is paused behind concrete Product demand and must not be duplicated.
- Task `NYRON-T-20260828-169` is deferred/not started; it will be resumed only when Human Approval Node requires the Track-C slice.
- New primary Task `NYRON-T-20260828-170` is assigned to Claude for Module Assembly Node / Visual Workflow Core Readiness.
- The intended Product/Runtime relationship is tested, not assumed, by Task 170: `VisualWorkflowRevision -> deterministic compile/project -> GraphRevision`, while Graph retains canonical executable ownership.
- First Product implementation, if readiness returns GO, should remain external-effect-free and should prove the Product Node abstraction before HTTP/Browser/Filesystem/Approval/TTS/Avatar or real Provider work.
- Consequential external Production gates remain unchanged/closed unless their own accepted evidence says otherwise.
- `Last Accepted Production Commit` is unchanged by this coordination revision.

Historical Revision 108–121 decisions remain available in Git history and their accepted outcomes/findings are not invalidated by this compact current-state snapshot.

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
