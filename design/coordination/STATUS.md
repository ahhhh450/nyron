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
| NYRON-D-002 | Nyron设计-NYRON-D-002-Graph-Composite | Graph / Composite Design Candidate v0.1 | Dedicated parallel design thread | NYRON-D-001 draft + frozen Module baseline | TARGETED RE-REVIEW REQUIRED | First DeepSeek PASS was rejected as review-invalid due to material misreads; corrected bounded re-review required before freeze consideration |
| NYRON-D-003 | Nyron设计-NYRON-D-003-Runtime-Orchestration | Runtime Orchestration Design | Dedicated parallel design thread | NYRON-D-002 execution-facing semantics + Module baseline | READY FOR PARALLELIZATION | May open now; treat Graph candidate as review-pending and escalate any conflict |
| NYRON-D-004 | Nyron设计-NYRON-D-004-Capability-Resource-Effect | Capability / Resource / Effect Authority Design | Dedicated parallel design thread | NYRON-D-001 ownership model + Module baseline + Amendment 001 | INDEPENDENT REVIEW READY | Lead integration passed after explicit EffectOperation PREPARED amendment; bounded consistency review required before freeze consideration |
| NYRON-D-005 | Nyron设计-NYRON-D-005-Accounting-Recovery | Accounting / Recovery Design | Dedicated parallel design thread | NYRON-D-001 + Module baseline + NYRON-D-004 candidate | READY FOR PARALLELIZATION | May open now; must treat D-004 as review-pending and preserve Effect/Budget orthogonality |
| NYRON-D-006 | Nyron设计-NYRON-D-006-Product-Node-UX | Product Node Taxonomy / Visual Workflow UX | Product design thread with user | NYRON-D-002 expressive envelope | UNBLOCKED / NOT STARTED | May begin when product discussion is useful; must not alter runtime primitives |
| NYRON-D-007 | Nyron设计-NYRON-D-007-Distribution-Module-Ecosystem | Distribution / Module Ecosystem | Dedicated design thread | NYRON-D-002 dependency/import semantics + Module registry semantics | READY / NOT STARTED | Can open while Graph remains candidate if exact-version/import semantics are treated as review-pending |
| NYRON-D-008 | Nyron设计-NYRON-D-008-External-Interfaces-Workspace | External Interfaces / Workspace Boundary | Dedicated design thread | Kernel ownership + NYRON-D-004 authority/resource foundation | READY / NOT STARTED | May open now against D-004 candidate; any authority conflict must return to Lead |

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

No blocking Architecture Finding against the frozen Module baseline was identified.

### First DeepSeek Review Result

Returned result: PASS.
Lead acceptance: REJECTED AS REVIEW-INVALID.

Material misreads:
1. It treated `GraphComposite` as a formal object; the Candidate defines Graph, GraphRevision, Composite and CompositeRevision.
2. It claimed FEEDBACK was a standard control operation in the frozen Module baseline; the Candidate defines it only as an Edge role / intentional-cycle declaration.
3. It claimed validation guarantees a DAG, while the Candidate intentionally permits directed cycles containing FEEDBACK.

Required next action: targeted DeepSeek re-review using corrected premises.

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

Safe now:
- NYRON-D-001 — continue in main thread.
- NYRON-D-002 — targeted re-review only.
- NYRON-D-003 — may start Runtime Orchestration design.
- NYRON-D-004 — bounded independent consistency review only; no speculative redesign unless a valid finding appears.
- NYRON-D-005 — may start Accounting / Recovery design using D-004 as review-pending candidate.
- NYRON-D-006 — product discussion is unblocked and may be deferred until visible-node design is useful.
- NYRON-D-007 — may start if needed, treating Graph semantics as candidate.
- NYRON-D-008 — may start if needed, treating D-004 authority boundaries as candidate.

Parallelism constraint:
- Do not simultaneously let D-003 and D-005 redefine Attempt replacement / UNKNOWN ownership. D-003 owns runtime attempt/retry lifecycle; D-005 owns recovery/reconciliation and accounting response to UNKNOWN.
- Do not let D-008 redefine Capability/Resource/Effect ownership; it consumes D-004 contracts.

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
