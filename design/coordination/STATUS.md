# Nyron Design Coordination Status

Authority: Lead Design Authority
Purpose: Maintain the single current source of truth for parallel design tasks, dependencies, gates, and integration status.

## Rules

1. Every active design thread receives one unique Task ID.
2. A delegated design thread may produce a candidate design but may not freeze architecture.
3. The Lead Design Authority owns dependency ordering, integration review, Architecture Findings, and final baseline status.
4. Parallel design is allowed only when tasks do not require simultaneous changes to the same unresolved semantic boundary.
5. Results from delegated threads return to the main design thread for integration before becoming authoritative.
6. If a task discovers a conflict with a frozen baseline, it must stop at that boundary and raise an Architecture Finding.
7. This file must be updated whenever a design task is opened, completed, blocked, superseded, or integrated.

## Current Tasks

| Task ID | Topic | Mode | Depends On | Status | Gate / Return Condition |
| --- | --- | --- | --- | --- | --- |
| NYRON-D-001 | Overall System Architecture v0.1 | Main design thread | Frozen Module baseline | IN PROGRESS | Produce reviewable System Foundation candidate and integrate subsystem results |
| NYRON-D-002 | Graph / Composite Design Candidate v0.1 | Dedicated parallel design thread | NYRON-D-001 current draft + frozen Module baseline | READY / DELEGATED | Return complete candidate, invariants, open questions, Architecture Findings if any |
| NYRON-D-003 | Runtime Orchestration Design | Dedicated parallel design thread | Graph execution semantics from NYRON-D-002; Module baseline | BLOCKED | Open only after Graph/Composite execution-facing semantics are stable enough |
| NYRON-D-004 | Capability / Resource / Effect Authority Design | Dedicated parallel design thread | NYRON-D-001 ownership model + Module baseline | READY FOR PARALLELIZATION | Can proceed independently if scoped to authority/resource boundaries and does not redesign Runtime scheduling |
| NYRON-D-005 | Accounting / Recovery Design | Dedicated parallel design thread | NYRON-D-001 ownership model + Module baseline; some effect lifecycle inputs from NYRON-D-004 | PARTIALLY BLOCKED | Start after NYRON-D-004 establishes effect/resource lifecycle boundaries |
| NYRON-D-006 | Product Node Taxonomy / Visual Workflow UX | Product design thread with user | Graph/Composite expressive envelope | BLOCKED | Open after NYRON-D-002 establishes node/composite/topology envelope |
| NYRON-D-007 | Distribution / Module Ecosystem | Dedicated design thread | Graph dependency manifest + Module registry semantics | BLOCKED | Open after NYRON-D-002 |
| NYRON-D-008 | External Interfaces / Workspace Boundary | Dedicated design thread | Kernel ownership + Capability/Resource authority | BLOCKED | Open after NYRON-D-004 foundation |

## Current Parallelization Decision

Safe now:

- NYRON-D-001 — continue in main thread.
- NYRON-D-002 — run in the dedicated Graph / Composite thread.
- NYRON-D-004 — may be opened as a second parallel specialist thread.

Do not open yet:

- NYRON-D-003 Runtime Orchestration, because readiness, joins, loops, and execution pinning depend directly on NYRON-D-002.
- NYRON-D-005 Accounting / Recovery, until the Capability / Resource / Effect lifecycle boundary is clearer.
- NYRON-D-006 Product Node Taxonomy, until Graph / Composite expressive boundaries are stable.

## Main Thread Responsibility While Parallel Tasks Run

The main design thread does not idle while delegated tasks run. It continues only work that is globally useful and does not pre-decide delegated subsystem semantics. Current allowed work:

- refine Kernel / Canonical Truth / Ownership boundaries;
- maintain global invariant candidates;
- define subsystem dependency map and implementation gates;
- review incoming candidate designs;
- raise and resolve Architecture Findings;
- keep this STATUS file synchronized.

The main thread must not independently design the detailed Graph/Composite state machine while NYRON-D-002 is active, and must not pre-design Capability/Resource details if NYRON-D-004 is delegated.
