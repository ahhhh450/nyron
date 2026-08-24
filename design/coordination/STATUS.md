# Nyron Design Coordination Status

Authority: Lead Design Authority
Purpose: Single current source of truth for design tasks, frozen baselines, review gates, dependencies, and integration state.

## 1. Operating Rules

1. Every design thread has one unique Task ID.
2. Specialist conversation name = Task ID only, e.g. `NYRON-D-005`.
3. Every new specialist launch message must state: Nyron project, repository URL, Task ID, exact task brief path, design-only/no-freeze boundary, mandatory repository write-back path, commit SHA return requirement, and instruction to rename the conversation to the Task ID.
4. Delegated specialists produce Candidates only; only Lead Design Authority may freeze architecture.
5. Delegated Candidates must be written to the repository. Chat-only output is not completion. If write access is unavailable, return `REPOSITORY_WRITE_UNAVAILABLE` plus the full Candidate.
6. Frozen architecture may change only through an explicit Amendment or superseding frozen baseline. Silent reinterpretation is forbidden.
7. Cross-task conflicts are returned to Lead as explicit `ARCHITECTURE FINDING`; one specialist must not rewrite another Owner's contract.
8. Reviewer output is evidence, not authority. A PASS that materially misreads the design is invalid.
9. Bounded subsystem reviews normally use DeepSeek. Claude is reserved for integrated adversarial architecture review unless a high-risk local finding justifies earlier use.
10. Repository design truth should be written before context compaction or conversation replacement.

## 2. Current Tasks

| Task ID | Topic | Status | Current Gate |
| --- | --- | --- | --- |
| `NYRON-D-001` | Overall System Architecture v0.1 | **IN PROGRESS — LEAD INTEGRATION** | Integrate frozen/reviewed subsystem boundaries, then prepare integrated Claude adversarial review |
| `NYRON-D-002` | Graph / Composite | **FROZEN** | Frozen baseline manifest committed; implementation remains gated by overall design program |
| `NYRON-D-003` | Runtime Orchestration | **LEAD REVIEW PASS / INDEPENDENT REVIEW READY** | DeepSeek bounded consistency review |
| `NYRON-D-004` | Capability / Resource / Effect Authority | **LEAD REVIEW PASS / INDEPENDENT REVIEW IN PROGRESS** | DeepSeek bounded consistency review; Amendment 001 already frozen |
| `NYRON-D-005` | Accounting / Recovery | **LEAD REVIEW PASS / INDEPENDENT REVIEW READY** | DeepSeek bounded consistency review |
| `NYRON-D-006` | Product Node / Visual Workflow UX | **UNBLOCKED / NOT STARTED** | Start when product-node design becomes useful; may not alter frozen primitives |
| `NYRON-D-007` | Distribution / Module Ecosystem | **READY / NOT STARTED** | May start after current review wave or when distribution work is prioritized |
| `NYRON-D-008` | External Interfaces / Workspace | **LEAD REVIEW PASS / INDEPENDENT REVIEW READY** | DeepSeek bounded consistency review |

## 3. Frozen Architecture Baselines

### Module Architecture

- `design/Universal_Runtime_Module_Design_Report_v0.1.md`
- Status: **FROZEN MODULE ARCHITECTURE BASELINE**

### Module Amendment 001 — EffectOperation PREPARED

- `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
- Status: **FROZEN MODULE ARCHITECTURE AMENDMENT**
- Adds PREPARED durable intent before crash-ambiguous dispatch and clarifies EffectOperation domain lifecycle ownership by Effect Authority while remaining Kernel-visible.

### Graph / Composite v0.1

- `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md`
- Status: **FROZEN GRAPH / COMPOSITE ARCHITECTURE BASELINE**
- Freezes exact Candidate + Lead Clarification blobs.
- Includes deterministic ordinal rules, concrete-Port single source of truth, stable Composite placement identity, deterministic materialization, FEEDBACK semantics, and GraphRevision execution pinning.

## 4. Lead-Integrated Candidates Awaiting Independent Review

### NYRON-D-003 — Runtime Orchestration

Candidate:
- `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`

Lead clarification:
- `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`

Lead result: **PASS**.

Frozen-facing conclusions accepted:
- Packet -> Delivery -> Activation -> Run/Attempt remains the only execution path.
- Retry/replacement create new Attempt; resume stays in same Attempt.
- one current Attempt per Run, canonically fenced.
- stale Attempt cannot commit/resume/start new effects.
- FEEDBACK has no special Runtime semantics.
- terminal state is canonical quiescence/directive result, not queue emptiness.
- top-level execution ingress must become Trigger Packet -> Delivery; direct Activation ingress is forbidden.

Review task:
- `design/coordination/tasks/NYRON-D-003-REVIEW-DS.md`

### NYRON-D-005 — Accounting / Recovery

Candidate:
- `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`

Lead clarification:
- `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`

Lead result: **PASS**.

Accepted conclusions:
- EffectOperation / ResourceLease / CapabilityGrant / BudgetReservation remain orthogonal.
- full static AccountingScope ancestry reservation is atomic within Accounting Owner.
- actual usage is never capped or rewritten to satisfy budget policy.
- UNKNOWN is not zero/success/failure.
- ReconciliationCase coordinates bounded investigation but never owns subject truth.
- `ReconciliationCase.RESOLVED` is not universal Runtime/effect clearance.
- a Recovery administrative disposition may permit Runtime closure while a subject remains UNKNOWN, but only the authoritative Effect/Resource/Capability Owner can clear conflicting new external authority.

Review task:
- `design/coordination/tasks/NYRON-D-005-REVIEW-DS.md`

### NYRON-D-008 — External Interfaces / Workspace

Candidate:
- `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`

Lead clarification:
- `design/clarifications/NYRON-D-008_Lead_Integration_Clarification_001.md`

Lead result: **PASS**.

Accepted conclusions:
- Browser/Shell/File/HTTP/Provider/Tool/Remote Worker/Event are not Kernel primitives.
- Workspace identity != live Workspace Handle Resource.
- D-008 does not claim WorkspaceIdentity canonical ownership before a Workspace/Project Owner is frozen.
- resolved filesystem containment, symlink/mount policy and isolation claims must be enforceable/testable.
- kill/cancel/timeout/disconnect/absence is not proof of fencing or non-dispatch.
- external ingress must be authenticated/validated/canonicalized, then enter Runtime through Trigger Packet -> Delivery -> Activation; adapter cannot create Activation directly.
- observation classification is fail-closed when provider semantics are billable/stateful/crash-ambiguous/consequential.

Review task:
- `design/coordination/tasks/NYRON-D-008-REVIEW-DS.md`

## 5. NYRON-D-004 Current Review State

Candidate:
- `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`

Lead result: **PASS WITH EXPLICIT FROZEN AMENDMENT 001**.

Accepted model:
- Capability Authority owns CapabilityGrant.
- Resource Manager owns Resource/ResourceLease.
- Effect Authority owns EffectOperation domain lifecycle.
- Module Host is mediation/isolation infrastructure, not canonical semantic Owner.
- Attempt replacement immediately removes old future commit/new-effect authority; already-dispatched effects require completion/fencing/UNKNOWN handling.
- EffectOperation and BudgetReservation remain independent.

Current gate: DeepSeek bounded consistency review.

## 6. D-001 Mandatory Integration Items

Before Overall System Architecture can become freeze-ready, Lead must integrate at least:

1. `EffectOperation -> Effect Authority` into the canonical Owner table.
2. Frozen Graph/Composite baseline reference rather than Candidate-only reference.
3. Top-level execution ingress rule: no direct Activation path; all workflow start/external trigger execution enters as Runtime Trigger Packet -> Delivery -> Activation against immutable GraphRevision ingress binding.
4. Runtime current-Attempt/fencing ownership from D-003.
5. Recovery disposition distinction: administrative Runtime closure permission != subject truth resolution != Effect/Resource conflict clearance.
6. Accounting Owner / Recovery Owner split and static accounting membership reference semantics.
7. External ingress canonicalization boundary and explicit route target Owner requirement.
8. Workspace identity ownership remains unresolved until Workspace/Project configuration Owner is selected; D-008 consumes stable `workspace_ref` but does not own it.
9. Kernel Foundation remains generic: identity/durability/transactions/ownership/fencing/causality, not subsystem business state machines.

## 7. Current Review Wave

Run independently, in parallel where available:

- `NYRON-D-004-REVIEW-DS`
- `NYRON-D-003-REVIEW-DS`
- `NYRON-D-005-REVIEW-DS`
- `NYRON-D-008-REVIEW-DS`

Reviewers must use the exact task files under `design/coordination/tasks/` and return only PASS/non-blocking clarifications or true blocking findings.

## 8. Next Lead Sequence

1. Receive/validate D-004, D-003, D-005, D-008 DeepSeek reviews.
2. Apply only valid non-blocking clarifications; reject review results that materially misread contracts.
3. Freeze subsystem baselines that pass.
4. Integrate D-002/003/004/005/008 into D-001 Overall System Architecture.
5. Decide whether D-006 Product Node / Visual UX and D-007 Distribution need design before overall architecture freeze.
6. Produce integrated Overall Architecture Candidate.
7. Send integrated architecture to Claude for Independent Adversarial Architecture Review.
8. Resolve findings / re-review / freeze overall design baseline.
