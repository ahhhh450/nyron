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
12. Delegated design tasks must write their complete candidate deliverable to the repository at the path specified in the task brief and return the commit SHA. Printing a candidate only in chat is not task completion. If repository writing is unavailable, the task must explicitly return `REPOSITORY_WRITE_UNAVAILABLE` plus the complete candidate for Lead integration.
13. Every new specialist conversation must receive a self-contained launch message that states at minimum: the repository name and URL, that the task belongs to the Nyron design project, the Task ID, the exact task-brief path to read first, the design-only/no-freeze authority boundary, and the requirement to write the final candidate back to the repository and return the commit SHA. A new window must not be expected to infer repository location or prior conversation context.
14. Specialist conversation names use the Task ID only, for example `NYRON-D-005`. Launch instructions must explicitly ask the new window to rename the conversation to that Task ID.

## Current Tasks

| Task ID | Conversation Name | Topic | Mode | Depends On | Status | Gate / Return Condition |
| --- | --- | --- | --- | --- | --- | --- |
| NYRON-D-001 | NYRON-D-001 | Overall System Architecture v0.1 | Main design thread | Frozen Module baseline + explicit amendments | IN PROGRESS | Integrate subsystem candidates and produce reviewable System Foundation baseline |
| NYRON-D-002 | NYRON-D-002 | Graph / Composite Design Candidate v0.1 | Dedicated parallel design thread | NYRON-D-001 draft + frozen Module baseline | FREEZE READY | Valid targeted DeepSeek re-review passed; Lead Clarification 001 accepted; final Lead consolidation/freeze remains |
| NYRON-D-003 | NYRON-D-003 | Runtime Orchestration Design | Dedicated parallel design thread | NYRON-D-002 execution-facing semantics + Module baseline + Amendment 001 | CANDIDATE RECEIVED / LEAD REVIEW PENDING | Candidate committed at `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`; Lead integration review required |
| NYRON-D-004 | NYRON-D-004 | Capability / Resource / Effect Authority Design | Dedicated parallel design thread | NYRON-D-001 ownership model + Module baseline + Amendment 001 | INDEPENDENT REVIEW READY | Bounded consistency review required before freeze consideration |
| NYRON-D-005 | NYRON-D-005 | Accounting / Recovery Design | Dedicated parallel design thread | NYRON-D-001 + Module baseline + NYRON-D-004 candidate | CANDIDATE RECEIVED / LEAD REVIEW PENDING | Candidate committed at `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`; Lead integration review required |
| NYRON-D-006 | NYRON-D-006 | Product Node Taxonomy / Visual Workflow UX | Product design thread with user | NYRON-D-002 expressive envelope | UNBLOCKED / NOT STARTED | Begin when visible-node/product discussion is useful; must not alter runtime primitives |
| NYRON-D-007 | NYRON-D-007 | Distribution / Module Ecosystem | Dedicated design thread | NYRON-D-002 dependency/import semantics + Module registry semantics | READY / NOT STARTED | Can open later while Graph remains candidate if exact-version/import semantics remain review-pending |
| NYRON-D-008 | NYRON-D-008 | External Interfaces / Workspace Boundary | Dedicated design thread | Kernel ownership + NYRON-D-004 authority/resource foundation | CANDIDATE RECEIVED / LEAD REVIEW PENDING | Candidate committed at `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`; Lead integration review required |

## Active Task Briefs

- `design/coordination/tasks/NYRON-D-003.md`
- `design/coordination/tasks/NYRON-D-005.md`
- `design/coordination/tasks/NYRON-D-008.md`

Each specialist window should read its task brief first and then only the minimum repository context listed there. Each brief contains a mandatory repository deliverable path.

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

Lead integration review: PASS.

Repository candidate:
- `design/Nyron_Graph_Composite_Design_Candidate_v0.1.md`

Lead pre-freeze clarification:
- `design/clarifications/NYRON-D-002_Lead_Integration_Clarification_001.md`

Valid targeted independent review record:
- `design/reviews/NYRON-D-002_DeepSeek_Targeted_ReReview.md`

Accepted clarification set:
1. Composite materialization output — leaf identities and topology — is persisted as authoritative immutable GraphRevision content. Runtime never re-flattens or regenerates these identities.
2. FEEDBACK is an intentional-cycle definition marker only; it does not alter Delivery ordering, activation semantics, attempt identity, or scheduling semantics.
3. `edge_ordinal` and concrete input-port ordinals must have collision-free normative scope sufficient for deterministic Delivery projection; non-canonical row/UI/arrival ordering is forbidden as semantic authority.
4. concrete Port objects are the materialized single source of truth for `ModuleInstanceRevision` input/output port contracts.
5. Composite placement uses stable `composite_instance_ref` identity for binding/provenance.
6. Composite materialization is deterministic for identical immutable materialization inputs; persisted GraphRevision output remains execution authority.
7. Added candidate invariants: `G-INV-20` deterministic Delivery projection inputs and `G-INV-21` deterministic Composite materialization.

D-002 is now **FREEZE READY**. Final freeze requires Lead consolidation of Candidate + Clarification 001 into the frozen Graph / Composite baseline.

D-001 follow-up from review: add `EffectOperation -> Effect Authority` to the Overall Architecture canonical Owner table.

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

## Current Candidate Intake

Received and repository-verified:
- `NYRON-D-003` — `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`
- `NYRON-D-005` — `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`
- `NYRON-D-008` — `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`

Lead review order:
1. D-003 Runtime Orchestration — because it owns Attempt/retry/replacement/cancellation semantics consumed by other runtime-facing design.
2. D-005 Accounting / Recovery — cross-check against D-003 Attempt facts and D-004 Effect/Resource ownership.
3. D-008 External Interfaces / Workspace — cross-check adapter mappings after authority/recovery boundaries are stable enough.

## Current Parallelization Decision

Active now:
- NYRON-D-001 — Overall Architecture integration in main thread.
- NYRON-D-003 — Lead integration review.
- NYRON-D-004 — bounded DeepSeek consistency review.
- NYRON-D-005 — Lead integration review after/alongside D-003.
- NYRON-D-008 — Lead integration review after authority/runtime cross-check.

Freeze-ready / awaiting Lead consolidation:
- NYRON-D-002 — Graph / Composite.

Deferred:
- NYRON-D-006 — Product Node / Visual UX until product discussion is useful.
- NYRON-D-007 — Distribution / Module Ecosystem until current candidate review wave settles.

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
