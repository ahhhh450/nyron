# Nyron Design

## 1. Purpose

`design/` is the authoritative home for Nyron pre-implementation architecture. GitHub is durable design memory; chat windows are temporary working contexts.

Design documents define ownership, contracts, invariants, lifecycle semantics, cross-owner boundaries, replay/fencing rules, implementation gates, review evidence, Architecture Findings and frozen baselines before code may establish those semantics implicitly.

## 2. Authority

Nyron uses one **Lead Design Authority** for system-level integration and freeze decisions.

Specialists produce Candidates only. Independent reviewers provide advisory evidence only. A reviewer PASS is invalid if it materially misreads the actual candidate or frozen premises.

## 3. Read This First

For current truth:
1. `design/coordination/STATUS.md`
2. exact Task brief under `design/coordination/tasks/` when one exists
3. only the minimum baselines/candidates listed by that Task

For Lead immediate execution queue:
- `design/coordination/LEAD_ACTIVE_QUEUE.md`

For reusable process rules:
- `design/process/Nyron_Design_Operating_Model_v0.1.md`

## 4. Frozen Architecture Baselines

- Module Architecture — `design/Universal_Runtime_Module_Design_Report_v0.1.md`
- Amendment 001 / EffectOperation PREPARED — `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
- Graph / Composite — `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md`
- Runtime Orchestration — `design/Nyron_Runtime_Orchestration_Frozen_Baseline_v0.1.md`
- Accounting / Recovery — `design/Nyron_Accounting_Recovery_Frozen_Baseline_v0.1.md`
- Distribution / Module Ecosystem — `design/Nyron_Distribution_Module_Ecosystem_Frozen_Baseline_v0.1.md`
- External Interfaces / Workspace Boundary — `design/Nyron_External_Interfaces_Workspace_Frozen_Baseline_v0.1.md`
- Human Interaction / Approval Authority — `design/Nyron_Human_Interaction_Approval_Authority_Frozen_Baseline_v0.1.md`
- Project / Workspace / Policy Context — `design/Nyron_Project_Workspace_Policy_Context_Frozen_Baseline_v0.1.md`

Accepted DeepSeek PASS evidence:
- `design/reviews/NYRON-D-003_D-005_D-008_DeepSeek_PASS_Receipt_2026-08-24.md`
- `design/reviews/NYRON-D-007_D-009_D-010_DeepSeek_Review_PASS_Receipt.md`

## 5. Current Overall System Candidate

- `design/Nyron_Overall_System_Architecture_v0.1.md`
- Status: **CONSOLIDATED INTEGRATED PRE-FREEZE CANDIDATE**

Lead integration audit trail:
- `design/clarifications/NYRON-D-001_Lead_Integration_Clarification_001.md`
- `design/clarifications/NYRON-D-001_Lead_Integration_Clarification_002.md`

The v0.1 canonical Owner set is closed at Lead-integration level.

## 6. Only Remaining Subsystem Gate — D-004

Capability / Resource / Effect Authority:
- Candidate: `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`
- Lead clarification: `design/clarifications/NYRON-D-004_Lead_Integration_Clarification_002.md`
- Frozen dependency: Amendment 001
- Lead result: PASS
- Remaining gate: accept the D-004 bounded DeepSeek review result and freeze on valid PASS.

## 7. Product Node / Visual UX — D-006

D-006 is deferred and **not a System Foundation freeze blocker**.

Product concepts remain wrappers over generic Module / Graph / Runtime / Capability / Resource / Effect / Human Interaction / Accounting mechanisms. If Product work later exposes a real expressiveness or ownership gap, raise an Architecture Finding instead of inventing a local Kernel/Runtime primitive.

## 8. Core Cross-System Rules

Single execution path:

```text
Packet -> Delivery -> Activation -> Run / Attempt
```

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

Distribution separation:

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

Do not create a new GPT conversation for every task.

Use an existing appropriate window for bounded follow-ups, clarifications, integration and short checks. Open a dedicated GPT window only when substantial independent scope, context pressure, clean independent reasoning or meaningful parallelism justifies it.

If opened, canonical specialist conversation name is exactly `NYRON-D-XXX`, and the launch prompt must provide repository URL, Task ID, exact Task brief path, design-only/no-freeze boundary, repository write-back and commit SHA return requirements.

## 10. Final Review

Prepared final integrated Claude review:
- Manifest: `design/reviews/NYRON-D-001_Integrated_Adversarial_Review_Manifest_DRAFT.md`
- Task: `design/coordination/tasks/NYRON-D-001-REVIEW-CLAUDE.md`

Next gate:
1. close/freeze D-004;
2. update Manifest with all exact frozen constituent identities;
3. run one integrated Claude adversarial review;
4. resolve valid findings/re-review if necessary;
5. Lead-freeze Overall System Architecture v0.1.
