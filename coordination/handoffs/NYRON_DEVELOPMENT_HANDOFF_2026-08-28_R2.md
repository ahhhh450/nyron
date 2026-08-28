# NYRON DEVELOPMENT HANDOFF — 2026-08-28 R2

Status: `HANDOFF / NON-CANONICAL SNAPSHOT`

> This Handoff is a recovery aid, not Repository Truth. If anything here conflicts with current Repository state, current Repository state wins.

## 0. Product Direction

Nyron's current Product goal is a module-assembly visual workflow system:

```text
Module
  ↓
ProductNodeDefinition
  ↓
NodeInstance + Ports + Connections
  ↓
VisualWorkflowRevision
  ↓ deterministic compile/project
GraphRevision
  ↓
Execution Runtime
```

The target interaction model is closer to ComfyUI / Langflow / Flowise than to an internal Runtime-object inspector.

The key scheduling correction is:

```text
Track E Product / Visual Workflow = PRIMARY
Track A/B/C/D = SUPPORT, pulled only by concrete Product Node needs
```

Do not return to the old pattern of finishing every low-level subsystem before Product work begins.

---

# 1. Startup Rule — Handoff Is Not Repository Truth

A new Development Director must begin with:

```text
fetch latest main
→ read coordination/STATUS.md
→ read coordination/AGENT_AVAILABILITY.md
→ inspect current tasks/results/checkpoints
→ compare Repository state with this Handoff
→ Repository wins on any mismatch
```

Minimum startup reading:

1. `README.md`
2. `AGENTS.md`
3. `ORCHESTRATOR.md`
4. `coordination/STATUS.md`
5. `coordination/AGENT_AVAILABILITY.md`
6. `coordination/TASK_PROTOCOL.md`
7. `coordination/OUTPUT_FORMAT.md`
8. `coordination/REVIEW_PROTOCOL.md`
9. `coordination/WORKFLOW.md`
10. current active / paused / deferred Task files
11. only the Results / Checkpoints needed to verify those states
12. Task Required Reading

Do not infer current state from chat history or from this Handoff alone.

---

# 2. Current Live Snapshot

Snapshot basis:

```text
Coordination Epoch: 3
Coordination Revision: 122
Primary Gate: TRACK E — MODULE ASSEMBLY NODE FOUNDATION READINESS
Foundation Wave 2 accepted downstream base:
fa12ad2ba51a010786ac307e8efd683bc1be832b
```

Current Repository availability:

- Claude: `AVAILABLE — HIGH-VALUE PRIORITY`
- Codex: `AVAILABLE — FULL WEEKLY WINDOW / CONTROLLED PARALLELISM`
- DeepSeek: `AVAILABLE`
- GPT / Web GPT: `DEVELOPMENT DIRECTOR / ORCHESTRATION`

An older Handoff snapshot said Codex quota was exhausted. That statement is stale and must not override current `coordination/AGENT_AVAILABILITY.md`.

## Current Task Table

| State | Task | Role | Current disposition |
|---|---|---|---|
| `ACTIVE / READY` | `NYRON-T-20260828-170` | Track E Product Node / Visual Workflow Readiness | Primary P0 Task. Assigned to Claude. No Production mutation. |
| `PAUSED` | `NYRON-T-20260828-168` | Track D Network foundation | `PAUSED — PRODUCT-VERTICAL-SLICE HOLD / DO NOT DUPLICATE`. Capacity is restored; pause is scheduling/product-priority based, not a current quota blocker. |
| `DEFERRED / NOT STARTED` | `NYRON-T-20260828-169` | Track C suspension/resume + human response ingress readiness | Resume only when Human Approval Node creates a concrete need. Do not run as current mainline. |
| `WAITING REVIEW` | `NONE in the current Product mainline snapshot` | — | Future HIGH-risk Product implementation must receive independent exact-SHA Review before acceptance. |

## Accepted / Downstream-Usable Foundation

The Product scheduling correction does not invalidate prior accepted work.

Important accepted foundations include:

- Foundation Wave 2 downstream base: `fa12ad2ba51a010786ac307e8efd683bc1be832b`
- PWP core: `f3b6b0d022111dfc854f537c361ca5eb46516584`
- Distribution identity/exact-resolution: `b2ec8e2e79745fee75a9dfdde7d6ab4cebe5f863`
- Human Interaction core: `a85507b9b74e0f6b68a65460d9e5a4f19aa79f93`
- Provider foundation: `fdf6e78061d57039a6e59813b76877ab2d7e2bf6`
- Credential foundation: `d1fd31b1770871f1b96ec1a76250874c8b69ec11`

Use Repository acceptance/checkpoint evidence when exact downstream acceptance must be proved.

---

# 3. Product Node Is Not Runtime Object Visualization

**Product Node is a user-facing module composition abstraction, not a visual wrapper around every Runtime/canonical object.**

Do not create these as default Product Nodes merely because they exist internally:

- `Attempt`
- `EffectOperation`
- `HumanResponse`
- `CapabilityGrant`
- `BudgetReservation`
- `CredentialBinding`
- `HumanDecisionEvidence`
- `ResourceLease`
- internal ingress/effect/accounting facts

These belong inside Product Nodes when required by execution semantics.

Examples:

```text
LLM Node
→ Provider + Credential + Network + Accounting + Effect

Human Approval Node
→ HumanRequest + HumanResponse + HumanDecisionEvidence + Runtime suspension/resume

Filesystem Node
→ Workspace boundary + Capability + Resource/Lease
```

Core guardrails:

```text
ModuleDefinition != ProductNodeDefinition
ProductNodeDefinition != NodeInstance
VisualWorkflowRevision != GraphRevision
Product Port != Packet/Delivery canonical truth
Product config != CapabilityGrant
Product declaration != execution authority
Product layout/UI metadata != Runtime canonical truth
```

---

# 4. Track Model

## Track A — PWP / Context Backbone

State: `STABLE / DOWNSTREAM USABLE`

Use only when a concrete Product/Runtime admission requirement exposes a missing PWP capability.

## Track B — Distribution / Module Ecosystem

State: `STABLE / DOWNSTREAM USABLE`

Existing exact module identity/resolution remains valid. Later Import / Install / Trust / Enable work should be pulled by Product requirements such as installable custom nodes.

## Track C — Human Interaction / Approval

State: `STABLE CORE / SUPPORT DEFERRED`

Human Interaction core is accepted. Suspension/resume and external HumanResponse ingress are not the current mainline.

## Track D — External Interfaces / Workspace Boundary

State: `BOUNDED SUPPORT / CONSEQUENTIAL PRODUCTION CLOSED`

Provider/Credential and accepted lower-level foundations remain usable within their accepted gates. Network, Browser, Filesystem, Process and other consequential boundaries reopen only when a concrete Product Node needs them.

## Track E — Product / Visual Workflow

State: `PRIMARY`

Current milestone:

`MODULE ASSEMBLY NODE FOUNDATION`

---

# 5. Task / Branch / Worktree Naming

Formal Task IDs:

```text
NYRON-T-YYYYMMDD-NNN
```

Unless a Task explicitly specifies another remote branch, use these conventions:

```text
implementation:
task/<TASK_ID>-<slug>

readiness/design review:
readiness/<TASK_ID>-<slug>

independent review:
review/<TASK_ID>

targeted fix:
fix/<TASK_ID>-<slug>

re-review:
rereview/<TASK_ID>
```

Worktree rule:

```text
One mutable Task execution
=
one isolated worktree / clone / sandbox
```

Never let concurrent Agents share a mutable checkout.

One Formal Task has one Executor by default. Review is a separate Task/session.

---

# 6. Acceptance != Integration

Always preserve this distinction:

```text
Implementation Result SUCCESS
!= Review PASS
!= Director Acceptance
!= Integration
!= Global Accepted
```

Also:

```text
Accepted for downstream dependency use
!= merged to main
!= Last Accepted Production
!= Release / Global Accepted
```

An implementation SHA may be accepted as a bounded dependency without becoming global Production truth.

Parallel accepted SHAs converge only through an explicit Integration Task when convergence is required.

---

# 7. Standard Finding / Review Decision Tree

```text
Implementation SUCCESS
        ↓
Independent Review
        ├─ PASS
        │    → Director Acceptance decision
        │
        ├─ PASS_WITH_FINDINGS
        │    → classify blocking vs non-blocking
        │    → blocking: targeted Fix
        │    → non-blocking: Director may accept with recorded debt/finding
        │
        ├─ FAIL
        │    → Targeted Fix
        │       ↓
        │    Targeted Re-Review
        │
        └─ ESCALATION_REQUIRED
             → Lead Design Authority
```

Rules:

- Implementation Agent != Independent Reviewer for HIGH-risk work.
- Reviewer does not silently fix Production.
- Targeted Fix closes only named Findings.
- Targeted Re-Review verifies closure + new blocking regressions; it does not automatically become a full architecture re-review.
- Architecture uncertainty is not solved locally by inventing semantics.

---

# 8. Pause / Resume Rule

Temporary execution failures:

```text
quota
or auth
or workspace
or temporary tooling/mode failure
        ↓
PAUSE SAME TASK
        ↓
keep same Task ID
keep same scope
keep required base/dependencies
record HANDOFF checkpoint when required
        ↓
resume same Task later
```

Do not create a replacement technical Task merely because an Agent quota or local tool failed.

Create a new Task only when there is a real new unit of work, changed dependency, explicit Fix/Review stage, or architecture/technical blocker requiring separate resolution.

Task 168 demonstrates the rule: it remains the same Task and must not be duplicated.

---

# 9. Pull Rule for Lower-Level Tracks

Before opening more infrastructure, ask:

> Does a concrete Product Node currently require this capability?

If NO: defer unless it is a true architecture blocker.

If YES: open/resume the smallest supporting slice.

Examples:

```text
Real LLM Node
→ pull Track D Network

Human Approval Node
→ pull Track C suspension/resume

Filesystem Node
→ pull Workspace READ boundary

Browser Node
→ pull Browser boundary

Installable Custom Node
→ pull Track B Import/Install/Enable
```

After the support slice is accepted, return to the Product Node.

---

# 10. NODE FOUNDATION v0.1 — Milestone Acceptance Standard

`NODE FOUNDATION v0.1` is not complete merely because data classes exist.

The first Product foundation must prove at least:

1. an exact Module can expose a `ProductNodeDefinition` without duplicating Module identity;
2. Product Nodes have stable input/output port definitions;
3. `NodeInstance` can be durably persisted/restored;
4. `NodeConnection`/Edge validation fails closed on invalid node/port/type/cardinality references;
5. `VisualWorkflowRevision` is immutable revision truth with stable predecessor/replay/conflict semantics;
6. exact node/module versions are pinned so saved workflows remain reproducible;
7. workflow compile/projection is deterministic;
8. compile output enters the existing Graph abstraction rather than creating a second executable truth;
9. restart restores the exact workflow and its pinned dependencies;
10. mock/pure nodes can execute a complete workflow through the existing Runtime path;
11. Product code cannot mutate/replace Runtime canonical authority merely through Product metadata/config;
12. HIGH-risk implementation receives independent exact-SHA Review before Director Acceptance.

Target relationship:

```text
VisualWorkflowRevision
        ↓ deterministic compile/project
GraphRevision
        ↓
Runtime
```

Never:

```text
VisualWorkflowRevision == GraphRevision
```

---

# 11. First End-to-End Vertical Slice

After Task 170 returns `GO_BOUNDED_IMPLEMENTATION`, the first Product implementation should prove one complete external-effect-free path:

```text
[Text Input]
     ↓
[Mock LLM]
     ↓
[Text Output]
```

The test must exercise the whole chain:

```text
Module
→ ProductNodeDefinition
→ NodeInstance / Ports / Connections
→ VisualWorkflowRevision
→ deterministic compile
→ GraphRevision
→ Runtime execution
→ Result
```

`Mock LLM` must remain non-consequential: no real Network, Provider SDK, Credential value, Browser or external effect.

This vertical slice is the point where Nyron demonstrably becomes a node product rather than only a foundation project.

---

# 12. First Node Set

Start small:

- Text / Constant Input Node
- Text Output Node
- Pure Transform / Pass-through Node if useful to validate ports
- Mock LLM Node
- Conditional Node only if current Graph semantics already support the required branch model

Do not begin the first foundation by implementing:

- Browser Node
- real HTTP / Network Node
- Filesystem write Node
- Human Approval Node
- real Provider/Credential dispatch
- TTS
- Avatar
- streaming
- distributed execution

Those are later vertical slices.

---

# 13. Current Primary Task

`NYRON-T-20260828-170`

Type:

`HIGH-RISK BOUNDED ARCHITECTURE / CONTRACT / PRODUCT-TO-RUNTIME READINESS REVIEW`

Agent:

`Claude`

Purpose:

Determine whether the current frozen Module / Graph / Runtime authority is sufficient for the smallest Product Node foundation, and define the exact bounded implementation slice without inventing new architecture.

Required disposition:

```text
GO_BOUNDED_IMPLEMENTATION
or
BLOCKED_BY_DEPENDENCY
or
ESCALATION_REQUIRED
```

If GO, the next Director-created implementation Task should explicitly target `NODE FOUNDATION v0.1` and the Text Input → Mock LLM → Text Output vertical slice above.

---

# 14. Agent Allocation

## GPT / Web GPT

`Development Director / Global Development Coordination Authority`

Owns roadmap, sequencing, Task creation, dependencies, review assignment, Acceptance and integration decisions.

## Claude

Prefer for:

- architecture/readiness
- Product semantics
- cross-owner contracts
- complex security/correctness review
- HIGH-risk adversarial Review/Re-Review

## Codex

Prefer for:

- Production implementation
- tests
- Git/worktree execution
- exact-SHA engineering review
- replay/restart/persistence probes
- targeted fixes

Current availability is restored. Do not nevertheless resume Task 168 merely to keep Codex busy.

## DeepSeek

Use for low-risk/mechanical/document consistency/targeted verification. Do not use as Development Director or sole HIGH-risk final reviewer.

---

# 15. Parallelism Rules

Safe parallelism requires all of:

- independent scope;
- satisfied dependencies;
- isolated mutable worktree/branch;
- non-overlapping write surface;
- clear owner;
- explicit review/acceptance path.

Do not create speculative Tasks just to occupy available Agent lanes.

Parallel development does not mean parallel merge. Convergence uses an explicit Integration Task when necessary.

---

# 16. External / Consequential Gates

Product-mainline activation does not open consequential external execution.

Until their own accepted gates say otherwise:

- real Network dispatch: `CLOSED`;
- real Provider network dispatch: `CLOSED`;
- Browser consequential dispatch: `CLOSED`;
- general Filesystem mutation / less-trusted namespace mutation: `CLOSED / SECURITY-GATED`;
- concrete external HumanResponse adapters: `CLOSED`;
- Human suspension/resume integration: `DEFERRED` until Approval Node needs it.

Initial Product Nodes should use truthful pure/mock behavior.

Standing credential security invariant:

`ResolvedCredentialHandle` itself must never cross into low-trust plugin/module/network-facing code.

---

# 17. Director Dispatch Style to User

Before every Task dispatch, give only two short sentences:

1. state whether this is `开发 / 审查 / Readiness / Fix / Re-Review`;
2. state what it is meant to prove, fix or unblock.

Then provide the copyable dispatch. Do not add a long explanation unless the user asks.

Example:

```text
这是 Readiness 审查，不写 Production。
目的是确认现有 Module/Graph/Runtime 是否足够支撑第一版 Product Node，并给出下一条实现边界。
```

---

# 18. New Director — First 10 Actions

A new window should do these in order:

1. fetch/read latest `main` Repository state;
2. read `coordination/STATUS.md` and record current Epoch/Revision;
3. read `coordination/AGENT_AVAILABILITY.md`;
4. read `AGENTS.md`, `ORCHESTRATOR.md`, `TASK_PROTOCOL.md`, `REVIEW_PROTOCOL.md`, `WORKFLOW.md`, `OUTPUT_FORMAT.md`;
5. inspect current Task files `168`, `169`, `170` plus any newer Task IDs that now exist;
6. inspect corresponding Results/Checkpoints; never assume a Task has or has not started from this Handoff alone;
7. compare Repository state with this Handoff and discard stale Handoff claims;
8. identify active Agent sessions/lanes and do not duplicate an already-running Task;
9. if Task 170 still has no Result and remains eligible, dispatch/continue Task 170 to Claude; if a Result exists, process that Result instead;
10. follow the standard decision tree: GO → create bounded Product implementation; BLOCKED → create only the required dependency work; ESCALATION → Lead Design Authority.

Do not start by redesigning the entire system.

---

# 19. Immediate Next Objective

Primary milestone:

`MODULE ASSEMBLY NODE FOUNDATION`

Current sequence:

```text
Task 170 Readiness
        ↓
if GO
        ↓
NODE FOUNDATION v0.1 implementation
        ↓
Independent exact-SHA Review
        ↓
Director Acceptance
        ↓
Text Input → Mock LLM → Text Output end-to-end proof
        ↓
next concrete Product Node
        ↓
pull only the missing support Track capability
```

The core principle is:

> Product requirements pull infrastructure. Infrastructure no longer delays Product indefinitely.
