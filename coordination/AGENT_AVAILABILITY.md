# Agent Availability

Status: `ACTIVE OPERATIONAL COORDINATION STATE`
Authority: `Development Director / Global Development Coordination Authority`
Date: `2026-08-28`

This file records current operational availability and routing only. It does not define permanent model capability and does not amend frozen Product/Runtime architecture.

## Current Availability

| Agent | Availability | Default Use While State Applies |
|---|---|---|
| `Claude` | `AVAILABLE — ACTIVE PRIMARY LANE` | May perform complex/core Production implementation, architecture/readiness, blocking fixes, integration, regression, exact-SHA review and re-review. No fixed "review-only" role. |
| `Codex` | `TEMPORARILY RATE-LIMITED — OPERATOR-REPORTED RESPONSE CAPACITY EXPECTED TO RETURN IN ~1 HOUR` | When available, may perform the same classes of core implementation and independent review work as Claude. Do not hold an immediately executable critical task solely to wait for Codex if Claude is available and suitable. |
| `DeepSeek` | `AVAILABLE` | Preferred for simple/mechanical/low-risk implementation, schema consistency, test/regression work, bounded tracing, localization and targeted verification. May provide supplementary review evidence; use Claude/Codex-class review where the Task/risk requires it. |
| `GPT / Web GPT` | `AVAILABLE FOR ORCHESTRATION` | Development Director / Track coordination; not default Production implementation or substitute final reviewer. |

## Role-Neutral Claude / Codex Rule

Claude and Codex are both development and review agents. Do **not** encode a permanent split such as:

```text
Codex = implementation
Claude = review
```

or the reverse.

Assignment is chosen dynamically from:

- current availability / quota;
- task complexity and model suitability;
- dependency readiness;
- mutable write-surface isolation;
- review independence;
- integration/convergence cost.

A model may implement one Task and review another Task. A separate independent session of the same model may also review another session's delivery when it did not participate in that implementation and the Review Task does not explicitly require cross-model independence.

## Review Independence Identity

For coordination purposes, `Implementation Agent != Independent Reviewer` means the **implementing execution session/identity must differ from the reviewing execution session/identity**. It does not by itself require a different model family.

Allowed examples, subject to the Task's own stricter requirements:

```text
Claude session A implements → Claude session B independently reviews
Claude implements → Codex reviews
Codex implements → Claude reviews
Codex session A implements → Codex session B independently reviews
```

The independent reviewer must not share the implementation session's mutable workspace, hidden implementation context, or self-review role. Review remains exact-SHA/read-only unless the Review Task explicitly authorizes otherwise.

## Controlled Parallelism Rule

Parallel work is allowed and encouraged when useful, but must be dependency- and write-surface-driven rather than quota-filling.

- Claude and Codex may both perform Production implementation concurrently on separate Formal Tasks when dependencies and mutable write surfaces are disjoint or an explicit integration order exists.
- Multiple sessions of the same model may also run concurrently under the same isolation rules.
- Review may run in parallel with unrelated implementation when the exact SHA under review is immutable and the implementation lane cannot mutate it.
- Do not have two tasks concurrently mutate the same high-risk persistence/authority surface without explicit ownership split and convergence plan.
- Do not create speculative tasks merely because an Agent has free capacity.
- DeepSeek should absorb simple/mechanical work where doing so frees Claude/Codex for higher-value work.

## Execution Mode / Capacity Failover

Temporary quota, rate-limit, tool, workspace or mode failure is operational, not automatically a Product blocker.

For a Task that has already materially started:

```text
PAUSE / HANDOFF SAME TASK
→ preserve Task ID + scope + base/fence
→ resume in a capable isolated session when authorized
```

For a Task that is still unstarted, the Development Director may rebind the same Task to another capable Claude/Codex session without creating a duplicate technical Task. Rebinding does not change scope, dependency, Production fence, required Result or Review obligations.

## Current Controlled Priority

1. `NYRON-T-20260828-171` is the P0 Product-mainline Task and is currently assigned to Claude for `NODE FOUNDATION v0.1` bounded Production implementation.
2. Task 171 owns the bounded Graph multi-instance/Edge publish completion, Product Node/Workflow persistence/compiler, and pure/mock `Text Input → Mock LLM → Text Output` proof.
3. Codex is temporarily rate-limited; once capacity returns, it may be assigned to a disjoint implementation Task if a real dependency/product need exists, or to an independent exact-SHA Review after a delivery is available. It is not reserved to either role.
4. `NYRON-T-20260828-168` remains `PAUSED — PRODUCT-VERTICAL-SLICE HOLD`; capacity restoration alone does not resume it.
5. `NYRON-T-20260828-169` remains `DEFERRED / NOT STARTED`; resume only when Human Approval Product Node creates the concrete need.
6. Lower Track A/B/C/D work opens or resumes only when a concrete Product Node requires a missing capability or a true blocker demands it.

## Change Rule

Agent availability and routing are operational state and may be superseded by later explicit Operator / Development Director instruction.