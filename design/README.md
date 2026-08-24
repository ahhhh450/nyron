# Nyron Design

## 1. Purpose

`design/` is the authoritative home for Nyron pre-implementation architecture.

GitHub is durable design memory. Chat windows are temporary working contexts.

Design documents define canonical ownership, contracts, invariants, state/lifecycle semantics, cross-owner boundaries, replay/fencing rules, implementation gates, review evidence, Architecture Findings and frozen baselines before code is allowed to establish those semantics implicitly.

## 2. Authority

Nyron uses one **Lead Design Authority** for system-level integration and freeze decisions.

Specialist design work produces Candidates only. Independent reviewers provide advisory evidence only. A reviewer PASS is invalid if it materially misreads the actual candidate or frozen premises.

## 3. Read This First

For current truth:
1. `design/coordination/STATUS.md`
2. exact Task brief under `design/coordination/tasks/` when one exists
3. only the minimum baselines/candidates listed by that Task

For Lead immediate execution queue:
- `design/coordination/LEAD_ACTIVE_QUEUE.md`

For reusable process rules:
- `design/process/Nyron_Design_Operating_Model_v0.1.md`

Do not scan all historical tasks/reviews unless a concrete integration issue requires it.

## 4. Frozen Architecture Baselines

### Module Architecture
- `design/Universal_Runtime_Module_Design_Report_v0.1.md`
- **FROZEN MODULE ARCHITECTURE BASELINE**

### Amendment 001 — EffectOperation PREPARED
- `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
- **FROZEN MODULE ARCHITECTURE AMENDMENT**

### Graph / Composite
- `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md`
- **FROZEN GRAPH / COMPOSITE ARCHITECTURE BASELINE**

### Runtime Orchestration — D-003
- `design/Nyron_Runtime_Orchestration_Frozen_Baseline_v0.1.md`
- **FROZEN RUNTIME ORCHESTRATION ARCHITECTURE BASELINE**

### Accounting / Recovery — D-005
- `design/Nyron_Accounting_Recovery_Frozen_Baseline_v0.1.md`
- **FROZEN ACCOUNTING / RECOVERY ARCHITECTURE BASELINE**

### External Interfaces / Workspace Boundary — D-008
- `design/Nyron_External_Interfaces_Workspace_Frozen_Baseline_v0.1.md`
- **FROZEN EXTERNAL INTERFACES / WORKSPACE BOUNDARY ARCHITECTURE BASELINE**

The D-003/D-005/D-008 independent review PASS intake is recorded at:
- `design/reviews/NYRON-D-003_D-005_D-008_DeepSeek_PASS_Receipt_2026-08-24.md`

## 5. Current Overall System Candidate

- `design/Nyron_Overall_System_Architecture_v0.1.md`
- Status: **CONSOLIDATED INTEGRATED PRE-FREEZE CANDIDATE**

Lead clarifications:
- `design/clarifications/NYRON-D-001_Lead_Integration_Clarification_001.md`
- `design/clarifications/NYRON-D-001_Lead_Integration_Clarification_002.md`

Current v0.1 canonical Owner set is closed at Lead-integration level. Overall freeze still requires remaining subsystem review/freeze closure and one integrated Claude adversarial review.

## 6. Lead-Integrated Candidates Awaiting Freeze

### D-004 — Capability / Resource / Effect Authority
- `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`
- Lead: PASS with Frozen Amendment 001
- Independent review state: pending Lead closure

### D-007 — Distribution / Module Ecosystem
- `design/Nyron_Distribution_Module_Ecosystem_Design_Candidate_v0.1.md`
- Lead: PASS WITH CLARIFICATION
- DeepSeek review: **IN PROGRESS**

### D-009 — Human Interaction / Approval Authority
- `design/Nyron_Human_Interaction_Approval_Authority_Design_Candidate_v0.1.md`
- Lead: PASS WITH CLARIFICATION
- DeepSeek review: **IN PROGRESS**

### D-010 — Project / Workspace / Policy Context
- `design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`
- Lead: PASS; AF-PWP-001 resolved
- DeepSeek review: **IN PROGRESS**

## 7. Product Node / Visual UX — D-006

D-006 is deferred and **not a System Foundation freeze blocker**.

Product concepts remain wrappers over generic Module / Graph / Runtime / Capability / Resource / Effect / Human Interaction / Accounting mechanisms. If later Product work exposes a real expressiveness or ownership gap, raise an Architecture Finding instead of inventing a local Kernel/Runtime primitive.

## 8. Core Cross-System Rules

Single execution path:

```text
Packet -> Delivery -> Activation -> Run / Attempt
```

No API, Human, PWP, Adapter, Registry or Product path may create a second direct-Activation execution path.

Generic workflow-start external ingress:

```text
PWP IngressRouteRevision
-> adapter authentication/validation/canonicalization
-> Runtime-owned ExecutionIngressFact
-> Runtime admission
-> Trigger Packet
-> Delivery
-> Activation
```

Package distribution separation:

```text
Import != Resolve != Install != Trust != Enable != CapabilityGrant != Runtime execution
```

Recovery separation:

```text
ReconciliationCase.RESOLVED
!= subject truth known
!= Effect/Resource/Capability conflict clearance
```

## 9. Conversation / Task Economy

A new GPT conversation is **not** created for every task.

Prefer the existing appropriate conversation for:
- small bounded design follow-ups;
- clarifications;
- minor integration work;
- short reviews/checks;
- work that does not materially pollute context.

Open a dedicated GPT conversation only when it provides a real benefit, especially:
- substantial independent subsystem design;
- current context is already large/noisy;
- a clean independent reasoning context is important;
- meaningful parallel work is useful.

When a dedicated specialist conversation is opened, its canonical name is exactly:

```text
NYRON-D-XXX
```

The launch prompt must explicitly provide repository URL, Task ID, exact Task brief path, design-only/no-freeze boundary, repository write-back requirement and commit SHA return requirement.

## 10. Review Index

Bounded DeepSeek review tasks:
- `design/coordination/tasks/NYRON-D-003-REVIEW-DS.md` — completed PASS
- `design/coordination/tasks/NYRON-D-004-REVIEW-DS.md`
- `design/coordination/tasks/NYRON-D-005-REVIEW-DS.md` — completed PASS
- `design/coordination/tasks/NYRON-D-007-REVIEW-DS.md` — issued
- `design/coordination/tasks/NYRON-D-008-REVIEW-DS.md` — completed PASS
- `design/coordination/tasks/NYRON-D-009-REVIEW-DS.md` — issued
- `design/coordination/tasks/NYRON-D-010-REVIEW-DS.md` — issued

Prepared final integrated Claude review:
- Manifest: `design/reviews/NYRON-D-001_Integrated_Adversarial_Review_Manifest_DRAFT.md`
- Task: `design/coordination/tasks/NYRON-D-001-REVIEW-CLAUDE.md`

## 11. Next Gate

1. Accept/reject D-007/D-009/D-010 DeepSeek results as they arrive and freeze each valid PASS independently.
2. Close D-004 review state and freeze on valid PASS.
3. Update the integrated Claude review Manifest with exact frozen constituent identities.
4. Run one integrated Claude adversarial review.
5. Resolve valid findings/re-review if required.
6. Lead-freeze Overall System Architecture v0.1.
