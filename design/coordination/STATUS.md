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
| `NYRON-D-001` | Overall System Architecture v0.1 | **IN PROGRESS — INTEGRATED CANDIDATE** | Await current subsystem reviews + D-007/D-009/D-010 candidates, then integrated Claude review |
| `NYRON-D-002` | Graph / Composite | **FROZEN** | Frozen baseline manifest committed |
| `NYRON-D-003` | Runtime Orchestration | **LEAD REVIEW PASS / INDEPENDENT REVIEW READY** | DeepSeek bounded consistency review |
| `NYRON-D-004` | Capability / Resource / Effect Authority | **LEAD REVIEW PASS / INDEPENDENT REVIEW IN PROGRESS** | DeepSeek bounded consistency review; Amendment 001 frozen |
| `NYRON-D-005` | Accounting / Recovery | **LEAD REVIEW PASS / INDEPENDENT REVIEW READY** | DeepSeek bounded consistency review |
| `NYRON-D-006` | Product Node / Visual Workflow UX | **UNBLOCKED / NOT STARTED** | Product-layer work may be deferred until foundation stabilizes |
| `NYRON-D-007` | Distribution / Module Ecosystem | **READY / TASK BRIEF CREATED** | Open specialist thread; consume frozen Graph dependency/import semantics |
| `NYRON-D-008` | External Interfaces / Workspace | **LEAD REVIEW PASS / INDEPENDENT REVIEW READY** | DeepSeek bounded consistency review |
| `NYRON-D-009` | Human Interaction / Approval Authority | **READY / TASK BRIEF CREATED** | Open specialist thread; define HumanRequest/HumanResponse Owner and approval evidence boundary |
| `NYRON-D-010` | Project / Workspace / Policy Context | **READY / TASK BRIEF CREATED** | Open specialist thread; close Workspace/Project/policy/ingress-route Owner gap |

## 3. Frozen Architecture Baselines

### Module Architecture
- `design/Universal_Runtime_Module_Design_Report_v0.1.md`
- **FROZEN MODULE ARCHITECTURE BASELINE**

### Module Amendment 001 — EffectOperation PREPARED
- `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
- **FROZEN MODULE ARCHITECTURE AMENDMENT**

### Graph / Composite v0.1
- `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md`
- **FROZEN GRAPH / COMPOSITE ARCHITECTURE BASELINE**

## 4. Lead-Integrated Candidates Awaiting Independent Review

### NYRON-D-003 — Runtime Orchestration
Candidate:
- `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`
Clarification:
- `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`
Review task:
- `design/coordination/tasks/NYRON-D-003-REVIEW-DS.md`
Lead result: **PASS**.

### NYRON-D-005 — Accounting / Recovery
Candidate:
- `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`
Clarification:
- `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`
Review task:
- `design/coordination/tasks/NYRON-D-005-REVIEW-DS.md`
Lead result: **PASS**.

### NYRON-D-008 — External Interfaces / Workspace
Candidate:
- `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`
Clarification:
- `design/clarifications/NYRON-D-008_Lead_Integration_Clarification_001.md`
Review task:
- `design/coordination/tasks/NYRON-D-008-REVIEW-DS.md`
Lead result: **PASS**.

## 5. NYRON-D-004 Review State

Candidate:
- `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`

Lead result: **PASS WITH EXPLICIT FROZEN AMENDMENT 001**.

Current gate: DeepSeek bounded consistency review.

## 6. New Parallel Task Briefs

### NYRON-D-007 — Distribution / Module Ecosystem
- Task: `design/coordination/tasks/NYRON-D-007.md`
- Required output: `design/Nyron_Distribution_Module_Ecosystem_Design_Candidate_v0.1.md`
- Purpose: close package/registry/install/trust/signing/distribution semantics while preserving exact dependency and import != trust rules.

### NYRON-D-009 — Human Interaction / Approval Authority
- Task: `design/coordination/tasks/NYRON-D-009.md`
- Required output: `design/Nyron_Human_Interaction_Approval_Authority_Design_Candidate_v0.1.md`
- Purpose: assign HumanRequest/HumanResponse canonical ownership and approval evidence/suspension/recovery boundaries.

### NYRON-D-010 — Project / Workspace / Policy Context
- Task: `design/coordination/tasks/NYRON-D-010.md`
- Required output: `design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`
- Purpose: close Project/Workspace identity, config/policy ownership, environment binding, active-execution pinning and ingress-route registry ownership.

## 7. D-001 Mandatory Integration Items

Already integrated in current D-001 draft:
1. `EffectOperation -> Effect Authority` canonical ownership.
2. frozen Graph/Composite baseline reference.
3. no direct Activation ingress; all workflow start/external trigger execution enters via Runtime Trigger Packet -> Delivery -> Activation.
4. Runtime current-Attempt/fencing ownership.
5. Recovery administrative disposition != subject truth resolution != Effect/Resource conflict clearance.
6. Accounting Owner / Recovery Owner split and static accounting membership semantics.
7. external ingress canonicalization boundary.
8. D-008 does not own Workspace identity metadata.
9. Kernel Foundation remains generic, not subsystem business state machine owner.

Still needing candidate/freeze closure:
10. Human Interaction canonical Owner and request/response semantics — D-009.
11. Workspace/Project identity/config/policy and ingress route Owner — D-010.
12. Module/package distribution/trust ecosystem — D-007 if required before Overall freeze.

## 8. Current Parallel Work

### Independent reviews
- `NYRON-D-004-REVIEW-DS`
- `NYRON-D-003-REVIEW-DS`
- `NYRON-D-005-REVIEW-DS`
- `NYRON-D-008-REVIEW-DS`

### New design threads
- `NYRON-D-007`
- `NYRON-D-009`
- `NYRON-D-010`

Parallelism constraints:
- D-007 cannot grant Capability or redefine Runtime/Graph semantics.
- D-009 owns HumanRequest/HumanResponse truth only; it must consume Runtime Suspension, Capability approval evidence, Recovery and External Ingress contracts.
- D-010 owns Project/Workspace/policy configuration context; it must not own live ResourceLease, CapabilityGrant, Runtime Attempt or Graph topology.

## 9. Next Lead Sequence

1. Validate incoming D-004/D-003/D-005/D-008 reviews.
2. Apply valid clarifications and freeze passing subsystem baselines.
3. Integrate D-007/D-009/D-010 candidates as they return.
4. Decide whether D-006 Product Node / Visual UX is required before overall freeze; current presumption: foundation can freeze before detailed product taxonomy if Product Extension Envelope remains sufficient.
5. Produce final integrated Overall Architecture Candidate.
6. Send integrated candidate + frozen baseline manifests to Claude for Independent Adversarial Architecture Review.
7. Resolve findings / re-review / freeze Overall System Architecture.
