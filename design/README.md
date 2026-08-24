# Nyron Design

## 1. Purpose

`design/` is the authoritative home for Nyron pre-implementation architecture. GitHub is durable design memory; chat windows are temporary working contexts.

## 2. Authority

Nyron uses one **Lead Design Authority** for system-level integration and freeze decisions.

Specialists/reviewers provide Candidates/evidence only. Frozen semantics change only through explicit Amendment or superseding baseline.

## 3. Read This First

1. `design/coordination/STATUS.md`
2. exact Task brief under `design/coordination/tasks/` when one exists
3. only the minimum baselines/candidates listed by that Task

Lead queue:
- `design/coordination/LEAD_ACTIVE_QUEUE.md`

Process model:
- `design/process/Nyron_Design_Operating_Model_v0.1.md`

## 4. Frozen Architecture Baselines

- Module Architecture — `design/Universal_Runtime_Module_Design_Report_v0.1.md`
- Module Amendment 001 / EffectOperation PREPARED — `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
- Graph / Composite — `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md`
- Runtime Orchestration — `design/Nyron_Runtime_Orchestration_Frozen_Baseline_v0.1.md`
- Accounting / Recovery — `design/Nyron_Accounting_Recovery_Frozen_Baseline_v0.1.md`
- Distribution / Module Ecosystem — `design/Nyron_Distribution_Module_Ecosystem_Frozen_Baseline_v0.1.md`
- External Interfaces / Workspace Boundary — `design/Nyron_External_Interfaces_Workspace_Frozen_Baseline_v0.1.md`
- **External Interfaces Amendment 001 / FENCED retry semantics** — `design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`
- Human Interaction / Approval Authority — `design/Nyron_Human_Interaction_Approval_Authority_Frozen_Baseline_v0.1.md`
- Project / Workspace / Policy Context — `design/Nyron_Project_Workspace_Policy_Context_Frozen_Baseline_v0.1.md`

## 5. Current Overall System Candidate

- `design/Nyron_Overall_System_Architecture_v0.1.md`
- Status: **CONSOLIDATED INTEGRATED PRE-FREEZE CANDIDATE**

The v0.1 canonical Owner set is closed at Lead-integration level.

## 6. Only Remaining Subsystem Gate — D-004

Capability / Resource / Effect Authority is **corrected but not frozen**.

Corrected bundle:
- `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`
- `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
- `design/clarifications/NYRON-D-004_Lead_Integration_Clarification_002.md`
- `design/clarifications/NYRON-D-004_Lead_Integration_Clarification_003.md`
- `design/clarifications/NYRON-D-004_Lead_Integration_Clarification_004.md`
- `design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`

Independent GPT adversarial FAIL record:
- `design/reviews/NYRON-D-004_GPT_Adversarial_Review_FAIL_2026-08-24.md`

Accepted blockers/corrections:

```text
FENCED active/conflict clearance
!= historical outcome certainty
!= semantic retry clearance
```

and:

```text
plain authority check-then-use is forbidden
actual authority consumption must linearize against replacement/revoke
```

Targeted re-review:
- `design/coordination/tasks/NYRON-D-004-REVIEW-GPT-R2.md`
- reuse the same GPT review conversation; do not open another GPT window.

## 7. Product Node / Visual UX — D-006

D-006 is deferred and **not a System Foundation freeze blocker** unless later Product work reveals a genuine architecture defect.

## 8. Core Cross-System Rules

Single execution path:

```text
Packet -> Delivery -> Activation -> Run / Attempt
```

Generic workflow-start ingress:

```text
PWP IngressRouteRevision
-> authentication/validation/canonicalization
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

Effect retry separation:

```text
FENCED
!= no prior consequence
!= safe semantic replay
```

Authority race rule:

```text
revoke/replacement wins admission race -> reject new use
exact use admission wins -> durable pre-revoke in-flight work
cached validation cannot cross that boundary
```

## 9. Conversation / Task Economy

Do not create a new GPT conversation for every task.

Use an existing appropriate window for bounded follow-ups, clarifications, integration and re-review. Open a dedicated window only when substantial independent scope, context pressure, clean independent reasoning or meaningful parallelism justifies it.

## 10. Final Review

Prepared integrated Claude review:
- Manifest: `design/reviews/NYRON-D-001_Integrated_Adversarial_Review_Manifest_DRAFT.md`
- Task: `design/coordination/tasks/NYRON-D-001-REVIEW-CLAUDE.md`

Next gate:
1. targeted GPT re-review of corrected D-004;
2. freeze D-004 on valid PASS;
3. update final Manifest with D-004 + External Interfaces Amendment 001;
4. run integrated Claude adversarial review;
5. resolve findings and Lead-freeze Overall System Architecture v0.1.
