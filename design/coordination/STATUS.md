# Nyron Design Coordination Status

Authority: Lead Design Authority
Purpose: Maintain the single current source of truth for parallel design tasks, dependencies, gates, conversation names, and integration status.

## Rules

1. Every active design thread receives one unique Task ID and one planned conversation name.
2. A delegated design thread may produce a candidate design but may not freeze architecture.
3. The Lead Design Authority owns dependency ordering, integration review, Architecture Findings, and final baseline status.
4. Parallel design is allowed only when tasks do not require simultaneous changes to the same unresolved semantic boundary.
5. Results from delegated threads return to the main design thread for integration before becoming authoritative.
6. If a task discovers a conflict with a frozen baseline, it must stop at that boundary and raise an Architecture Finding.
7. This file must be updated whenever a design task is opened, completed, blocked, superseded, integrated, or moved into independent review.
8. Stable decisions should be written to repository documents before a conversation is intentionally replaced or context is compressed.
9. Bounded subsystem consistency reviews should prefer a lower-cost independent reviewer such as DeepSeek; Claude is reserved for broader adversarial architecture review after multiple subsystem candidates have been integrated, unless a high-risk local finding justifies earlier Claude review.
10. Reviewer conclusions are advisory. A PASS is not accepted when the returned review materially misstates the candidate or frozen baseline; the Lead Design Authority must mark that review invalid and request a corrected review.

## Current Tasks

| Task ID | Conversation Name | Topic | Mode | Depends On | Status | Gate / Return Condition |
| --- | --- | --- | --- | --- | --- | --- |
| NYRON-D-001 | Nyron设计-总设计调度 | Overall System Architecture v0.1 | Main design thread | Frozen Module baseline | IN PROGRESS | Integrate subsystem candidates and produce reviewable System Foundation baseline |
| NYRON-D-002 | Nyron设计-NYRON-D-002-Graph-Composite | Graph / Composite Design Candidate v0.1 | Dedicated parallel design thread | NYRON-D-001 draft + frozen Module baseline | TARGETED RE-REVIEW REQUIRED | First DeepSeek PASS was rejected as review-invalid due to material misreads; corrected bounded re-review required before freeze consideration |
| NYRON-D-003 | Nyron设计-NYRON-D-003-Runtime-Orchestration | Runtime Orchestration Design | Dedicated parallel design thread | NYRON-D-002 execution-facing semantics + Module baseline | READY FOR PARALLELIZATION | May open now; must treat Graph candidate as review-pending and escalate any conflict |
| NYRON-D-004 | Nyron设计-NYRON-D-004-Capability-Resource-Effect | Capability / Resource / Effect Authority Design | Dedicated parallel design thread | NYRON-D-001 ownership model + Module baseline | IN PROGRESS / DELEGATED | Return complete candidate, invariants, open questions, findings |
| NYRON-D-005 | Nyron设计-NYRON-D-005-Accounting-Recovery | Accounting / Recovery Design | Dedicated parallel design thread | NYRON-D-001 + Module baseline + NYRON-D-004 lifecycle inputs | PARTIALLY BLOCKED | Open after NYRON-D-004 candidate stabilizes effect/resource lifecycle boundaries |
| NYRON-D-006 | Nyron设计-NYRON-D-006-Product-Node-UX | Product Node Taxonomy / Visual Workflow UX | Product design thread with user | NYRON-D-002 expressive envelope | UNBLOCKED / NOT STARTED | May begin when user/product discussion is useful; must not alter runtime primitives |
| NYRON-D-007 | Nyron设计-NYRON-D-007-Distribution-Module-Ecosystem | Distribution / Module Ecosystem | Dedicated design thread | NYRON-D-002 dependency/import semantics + Module registry semantics | READY / NOT STARTED | Can open after Graph review or earlier if it treats Graph semantics as candidate |
| NYRON-D-008 | Nyron设计-NYRON-D-008-External-Interfaces-Workspace | External Interfaces / Workspace Boundary | Dedicated design thread | Kernel ownership + NYRON-D-004 authority/resource foundation | BLOCKED | Open after NYRON-D-004 foundation |

## NYRON-D-002 Integration Result

Lead integration review: PASS WITH TWO CLARIFICATIONS INCORPORATED.

Repository candidate:
- `design/Nyron_Graph_Composite_Design_Candidate_v0.1.md`

Clarifications incorporated:
1. Composite materialization output — leaf identities and topology — is persisted as authoritative immutable GraphRevision content. Runtime never re-flattens or regenerates these identities.
2. FEEDBACK is an intentional-cycle definition marker only; it does not alter Delivery ordering, activation semantics, attempt identity, or scheduling semantics.

No blocking Architecture Finding against the frozen Module baseline was identified.

### First DeepSeek Review Result

Returned result: PASS.
Lead acceptance: REJECTED AS REVIEW-INVALID.

Material misreads in the returned review:
1. It treated `GraphComposite` as if it were a formal object in the Candidate; the Candidate defines `Graph`, `GraphRevision`, `Composite`, and `CompositeRevision`, not a `GraphComposite` runtime/history object.
2. It claimed FEEDBACK was a standard control operation in the frozen Module baseline. The Candidate defines FEEDBACK as an Edge role / intentional-cycle declaration and explicitly forbids it from introducing special Runtime semantics.
3. It claimed static validation guarantees a DAG, while the Candidate intentionally allows directed cycles when at least one Edge in the cycle is declared FEEDBACK.

Because these are material misunderstandings of the reviewed design, the PASS does not satisfy the independent-review gate.

Required next action: targeted DeepSeek re-review using explicit corrected premises and a narrower question set. Claude remains deferred to integrated adversarial review unless a high-risk local issue appears.

## Current Parallelization Decision

Safe now:
- NYRON-D-001 — continue in main thread.
- NYRON-D-002 — targeted re-review only; no speculative redesign unless a valid review finds an issue.
- NYRON-D-003 — may now start as a dedicated Runtime Orchestration thread, treating Graph semantics as candidate and review-pending.
- NYRON-D-004 — continue in dedicated authority/resource/effect thread.
- NYRON-D-006 — product discussion is unblocked, but may be deferred until the user wants to define visible nodes.

Do not open yet:
- NYRON-D-005 Accounting / Recovery, until NYRON-D-004 establishes candidate lifecycle boundaries.
- NYRON-D-008 External Interfaces / Workspace, until NYRON-D-004 authority foundation is stable enough.

## Review Strategy

### Subsystem Review
Use a bounded independent reviewer, normally DeepSeek, to check:
- frozen-baseline compatibility;
- internal contradiction;
- ownership/identity ambiguity;
- replay/recovery holes;
- missing invariants;
- unsafe cross-subsystem assumptions.

Reviewer output is evidence, not authority. A superficially positive result must be rejected if it demonstrates material misunderstanding of the design under review.

### Integrated Architecture Review
After major subsystem candidates are integrated into the Overall System Architecture candidate, use Claude for an Independent Adversarial Architecture Review with freedom to challenge assumptions and propose alternatives, while retaining no authority to modify or freeze the baseline directly.

## Main Thread Responsibility While Parallel Tasks Run

The main design thread continues only globally useful work that does not pre-decide delegated subsystem semantics:
- refine Kernel / Canonical Truth / Ownership boundaries;
- maintain global invariant candidates;
- integrate incoming candidate designs;
- resolve Architecture Findings;
- decide independent review / freeze gates;
- keep this STATUS file synchronized;
- periodically update the design operating model with reusable multi-session design practices.

The main thread must not duplicate detailed work already delegated to active specialist threads.