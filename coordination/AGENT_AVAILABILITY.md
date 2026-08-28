# Agent Availability

Status: `ACTIVE OPERATIONAL COORDINATION STATE`
Authority: `Development Director / Global Development Coordination Authority`
Date: `2026-08-28`

This file records current operational availability and routing only. It does not define permanent model capability and does not amend frozen Product/Runtime architecture.

## Current Availability

| Agent | Availability | Default Use While State Applies |
|---|---|---|
| `Claude` | `AVAILABLE — DEVELOPMENT / REVIEW` | Complex/core implementation, architecture/readiness, integration, blocking fixes, regression, exact-SHA review and re-review. No fixed role. |
| `Codex` | `AVAILABLE — ACTIVE P0 INTEGRATION LANE` | Current primary assignment: Task 181 cross-track integration. Also eligible for implementation/review generally. No fixed role. |
| `DeepSeek` | `AVAILABLE` | Preferred for simple/mechanical/low-risk implementation, schema consistency, test/regression, bounded tracing and targeted verification. |
| `GPT / Web GPT` | `AVAILABLE FOR ORCHESTRATION` | Development Director / coordination; not default Production implementer or final reviewer. |

## Role-Neutral Claude / Codex Rule

Claude and Codex are both development and review agents. Do not encode a permanent developer/reviewer split.

Assignment is chosen dynamically from availability, task complexity, dependency readiness, write-surface isolation, review independence and convergence cost.

Review independence is execution-session/identity based unless a concrete Task requires stricter cross-model independence.

## Controlled Parallelism Rule

Parallel work is allowed only when dependencies and mutable write surfaces justify it. Do not create speculative tasks merely to occupy capacity.

Two HIGH-risk tasks must not concurrently mutate the same persistence/authority surface unless an explicit ownership split and convergence plan exists.

## Current Controlled Priority

1. `NYRON-T-20260828-181` is P0: converge accepted Product foundation `1a741c5c7370f50f9efbc3087c67359cebdd8b27` with accepted Provider/Credential/Network tip `276432c1706d6f41900ef6d5cebcf5fc1e36cf5f`.
2. Task 181 owns only `NYRON-T-20260828-180-F-001`; real Network/Provider dispatch remains CLOSED.
3. `NYRON-T-20260828-180-F-002` Runtime/Effect seam work waits for Task 181 delivery + independent Review acceptance.
4. Task-180 F-003/F-004/F-005 and Task-136 F01/F02/F03 remain open; no real external-effect gate may be opened by Task 181.
5. No LLM Product Node Production implementation begins until the dependency-ordered support chain reaches the Product step.
6. Claude remains available for the mandatory independent review of Task 181 or other dependency-safe work; do not pre-start downstream high-risk support Tasks before the exact integrated SHA exists.
7. DeepSeek remains available for low-risk mechanical/regression work when explicitly useful.

## Execution Mode / Capacity Failover

For a materially started Task, preserve Task ID/scope/base and use PAUSE/HANDOFF if the assigned session becomes unavailable. For an unstarted Task, the Development Director may rebind it to another capable Claude/Codex session without duplicating the technical Task.

## Change Rule

Agent availability and routing are operational state and may be superseded by later explicit Operator / Development Director instruction.
