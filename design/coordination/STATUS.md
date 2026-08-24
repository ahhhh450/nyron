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
11. A frozen baseline may only be changed through an explicit amendment or superseding baseline that identifies the exact affected contract. Silent reinterpretation is forbidden.

## Current Tasks

| Task ID | Conversation Name | Topic | Mode | Depends On | Status | Gate / Return Condition |
| --- | --- | --- | --- | --- | --- | --- |
| NYRON-D-001 | Nyron设计-总设计调度 | Overall System Architecture v0.1 | Main design thread | Frozen Module baseline + explicit amendments | IN PROGRESS | Integrate subsystem candidates and produce reviewable System Foundation baseline |
| NYRON-D-002 | Nyron设计-NYRON-D-002-Graph-Composite | Graph / Composite Design Candidate v0.1 | Dedicated parallel design thread | NYRON-D-001 draft + frozen Module baseline | TARGETED RE-REVIEW REQUIRED | Corrected bounded re-review required before freeze consideration |
| NYRON-D-003 | Nyron设计-NYRON-D-003-Runtime-Orchestration | Runtime Orchestration Design | Dedicated parallel design thread | NYRON-D-002 execution-facing semantics + Module baseline + Amendment 001 | DELEGATED / IN PROGRESS | Return Runtime Orchestration candidate; own Attempt/retry/replacement/cancellation semantics only |
| NYRON-D-004 | Nyron设计-NYRON-D-004-Capability-Resource-Effect | Capability / Resource / Effect Authority Design | Dedicated parallel design thread | NYRON-D-001 ownership model + Module baseline + Amendment 001 | INDEPENDENT REVIEW READY | Bounded consistency review required before freeze consideration |
| NYRON-D-005 | Nyron设计-NYRON-D-005-Accounting-Recovery | Accounting / Recovery Design | Dedicated parallel design thread | NYRON-D-001 + Module baseline + NYRON-D-004 candidate | DELEGATED / IN PROGRESS | Return Accounting/Recovery candidate; preserve Effect/Budget orthogonality and leave Attempt lifecycle to D-003 |
| NYRON-D-006 | Nyron设计-NYRON-D-006-Product-Node-UX | Product Node Taxonomy / Visual Workflow UX | Product design thread with user | NYRON-D-002 expressive envelope | UNBLOCKED / NOT STARTED | Begin when visible-node/product discussion is useful; must not alter runtime primitives |
| NYRON-D-007 | Nyron设计-NYRON-D-007-Distribution-Module-Ecosystem | Distribution / Module Ecosystem | Dedicated design thread | NYRON-D-002 dependency/import semantics + Module registry semantics | READY / NOT STARTED | Can open later while Graph remains candidate if exact-version/import semantics remain review-pending |
| NYRON-D-008 | Nyron设计-NYRON-D-008-External-Interfaces-Workspace | External Interfaces / Workspace Boundary | Dedicated design thread | Kernel ownership + NYRON-D-004 authority/resource foundation | DELEGATED / IN PROGRESS | Return external-boundary candidate; consume D-004 contracts without redefining authority ownership |

## Active Task Briefs

- `design/coordination/tasks/NYRON-D-003.md`
- `design/coordination/tasks/NYRON-D-005.md`
- `design/coordination/tasks/NYRON-D-008.md`

Each specialist window should read its task brief first and then only the minimum repository context listed there.

## Frozen Module Amendments

### Amendment 001 — EffectOperation PREPARED

Document:
- `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`

Status: **FROZEN MODULE ARCHITECTURE AMENDMENT**

Resolution:
- adds `PREPARED` to the frozen EffectOperation lifecycle;
- requires durable operation identity before crash-ambiguous external dispatch;
- PREPARED does not prove dispatch occurred;
- recovered PREPARED with uncertain dispatch history must reconcile or become UNKNOWN rather than blind-retry;
- clarifies EffectOperation as Kernel-visible internal canonical record whose domain lifecycle is owned by Effect Authority, while Kernel Foundation owns only generic correctness primitives.

## NYRON-D-002 Integration Result

Lead integration review: PASS WITH TWO CLARIFICATIONS INCORPORATED.

Repository candidate:
- `design/Nyron_Graph_Composite_Design_Candidate_v0.1.md`

Clarifications incorporated:
1. Composite materialization output — leaf identities and topology — is persisted as authoritative immutable GraphRevision content. Runtime never re-flattens or regenerates these identities.
2. FEEDBACK is an intentional-cycle definition marker only; it does not alter Delivery ordering, activation semantics, attempt identity, or scheduling semantics.

First DeepSeek PASS was rejected as review-invalid because it materially misread formal object names, FEEDBACK semantics and the intentional-cycle rule. Targeted corrected re-review remains required.

## NYRON-D-004 Integration Result

Lead integration review: **PASS WITH ONE EXPLICIT FROZEN AMENDMENT**.

Repository candidate:
- `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`

Accepted integration points:
1. Capability Authority, Resource Manager and Effect Authority are separate canonical Owners.
2. CapabilityGrant is authority; Resource is a managed stateful handle; EffectOperation is external-effect history/tracking truth. They remain orthogonal.
3. EffectOperation gains PREPARED through explicit Frozen Amendment 001, not silent reinterpretation.
4. `EffectOperation` is Kernel-visible internal canonical state but its domain lifecycle belongs to Effect Authority; Kernel Foundation remains generic.
5. Attempt replacement immediately removes old commit/new-effect authority, while already-dispatched external effects require explicit completion/fencing/UNKNOWN handling.
6. Conflicting replacement authority waits for durable effect/resource clearance; non-conflicting work may proceed.
7. Module Host is mediation/isolation infrastructure, not a canonical semantic Owner.
8. EffectOperation and BudgetReservation remain separate Owners and lifecycles.

No other blocking Architecture Finding is open.

## Current Parallelization Decision

Active in parallel now:
- NYRON-D-001 — Overall Architecture integration in main thread.
- NYRON-D-002 — targeted corrected re-review only.
- NYRON-D-003 — Runtime Orchestration design.
- NYRON-D-004 — bounded consistency review only.
- NYRON-D-005 — Accounting / Recovery design.
- NYRON-D-008 — External Interfaces / Workspace design.

Deferred:
- NYRON-D-006 — Product Node / Visual UX until product discussion is useful.
- NYRON-D-007 — Distribution / Module Ecosystem until current three-line design wave returns or earlier only if capacity is clearly available.

Parallelism constraints:
- D-003 owns Runtime Attempt/retry/replacement/cancellation lifecycle.
- D-005 owns Accounting settlement, UNKNOWN recovery policy and ReconciliationCase mechanics; it must not redefine Attempt lifecycle or EffectOperation lifecycle.
- D-008 owns external-boundary mappings and trust assumptions; it must consume, not redefine, D-004 Capability/Resource/Effect ownership.
- Cross-task conflicts return to the Lead Design Authority as explicit Architecture Findings rather than being locally resolved by changing another task's contract.

## Review Strategy

### Subsystem Review
Use a bounded independent reviewer, normally DeepSeek, to check frozen-baseline compatibility, contradiction, owner/identity ambiguity, replay/recovery holes, missing invariants and unsafe cross-subsystem assumptions.

Reviewer output is evidence, not authority. A positive result is rejected if it materially misunderstands the design.

### Integrated Architecture Review
After major subsystem candidates are integrated into the Overall System Architecture candidate, use Claude for an Independent Adversarial Architecture Review with freedom to challenge assumptions and propose alternatives, while retaining no authority to modify or freeze the baseline directly.

## Main Thread Responsibility While Parallel Tasks Run

The main design thread continues only globally useful work that does not pre-decide delegated subsystem semantics:
- refine Kernel / Canonical Truth / Ownership boundaries;
- maintain global invariant candidates;
- integrate incoming candidate designs;
- resolve Architecture Findings through explicit amendments or superseding baselines;
- decide independent review / freeze gates;
- keep this STATUS file synchronized;
- periodically update the design operating model with reusable multi-session design practices.

The main thread must not duplicate detailed work already delegated to active specialist threads.
