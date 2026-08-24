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

## 4. Frozen Architecture Baselines / Amendments

- Module Architecture — `design/Universal_Runtime_Module_Design_Report_v0.1.md`
- Module Amendment 001 / EffectOperation PREPARED — `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
- Graph / Composite — `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md`
- **Graph / Accounting Amendment 001 / Static AccountingScope Resolution** — `design/amendments/Graph_Accounting_Amendment_001_Static_Accounting_Scope_Resolution.md`
- Runtime Orchestration — `design/Nyron_Runtime_Orchestration_Frozen_Baseline_v0.1.md`
- Capability / Resource / Effect Authority — `design/Nyron_Capability_Resource_Effect_Authority_Frozen_Baseline_v0.1.md`
- Accounting / Recovery — `design/Nyron_Accounting_Recovery_Frozen_Baseline_v0.1.md`
- Distribution / Module Ecosystem — `design/Nyron_Distribution_Module_Ecosystem_Frozen_Baseline_v0.1.md`
- External Interfaces / Workspace Boundary — `design/Nyron_External_Interfaces_Workspace_Frozen_Baseline_v0.1.md`
- External Interfaces Amendment 001 / FENCED retry semantics — `design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`
- Human Interaction / Approval Authority — `design/Nyron_Human_Interaction_Approval_Authority_Frozen_Baseline_v0.1.md`
- Project / Workspace / Policy Context — `design/Nyron_Project_Workspace_Policy_Context_Frozen_Baseline_v0.1.md`
- **PWP Amendment 001 / Historical Revision Retention** — `design/amendments/PWP_Amendment_001_Historical_Revision_Retention.md`

## 5. Integrated Claude Review — first pass

The first complete Claude integrated adversarial review returned **FAIL** with two findings.

Review record:
- `design/reviews/NYRON-D-001_Claude_Integrated_Review_FAIL_2026-08-24.md`

### F01 — valid blocker

Static `ModuleInstanceRevision.static_accounting_scope_ref` lacked one explicit frozen cross-owner execution-eligibility rule.

Correction:
- `design/amendments/Graph_Accounting_Amendment_001_Static_Accounting_Scope_Resolution.md`

Current rule:
- unresolved accounting affiliation may be stored/imported but is non-executable;
- Runtime admission fails closed until Accounting Owner resolves/validates all static scope refs and required ancestry;
- missing scope never means unbounded/no-budget authority.

### F02 — premise overstated, ambiguity removed

Frozen D-010 already required historical resolution and retention of superseded revisions while referenced by canonical history.

Correction-strength Amendment makes the coverage explicit for every PWP revision class:
- `design/amendments/PWP_Amendment_001_Historical_Revision_Retention.md`

Covered explicitly:
- ProjectConfigRevision;
- WorkspaceConfigRevision;
- PolicyContextRevision;
- EnvironmentBindingRevision;
- IngressRouteRevision;
- stable Project/Workspace/IngressRoute identities required to resolve them.

## 6. Current Overall System Candidate

- `design/Nyron_Overall_System_Architecture_v0.1.md`
- Status: **INTEGRATED PRE-FREEZE CANDIDATE — TARGETED CLAUDE R2 READY**

The correctness-critical Owner set remains closed.

## 7. Product Node / Visual UX — D-006

D-006 is deferred and **not a System Foundation freeze blocker** unless later Product work reveals a genuine architecture defect.

## 8. Core Cross-System Rules

Single execution path:

```text
Packet -> Delivery -> Activation -> Run / Attempt
```

Distribution separation:

```text
Import != Resolve != Install != Trust != Enable != CapabilityGrant != Runtime execution
```

Effect retry separation:

```text
FENCED != no prior consequence != safe semantic replay
```

Accounting resolution rule:

```text
unresolved static_accounting_scope_ref
-> definition may remain stored/imported
-> Runtime execution admission denied
```

PWP history rule:

```text
retained canonical history pins PWP revision
-> that exact revision remains semantically resolvable
```

## 9. Conversation / Task Economy

Do not create a new GPT conversation for every task. Reuse an existing appropriate window for bounded follow-ups, clarifications, integration and re-review.

## 10. Current Final Gate

Targeted Claude re-review:
- `design/coordination/tasks/NYRON-D-001-REVIEW-CLAUDE-R2.md`

Current Manifest:
- `design/reviews/NYRON-D-001_Integrated_Adversarial_Review_Manifest_DRAFT.md`

Next sequence:
1. run targeted Claude R2 in the same Claude conversation;
2. validate its premises/result;
3. on valid PASS, record review evidence and Lead-freeze Overall System Architecture v0.1 immediately;
4. only if a correction-induced blocker remains, amend that narrow scope and re-review it.
