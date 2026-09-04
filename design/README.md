# Nyron Design

## 1. Purpose

`design/` is the authoritative home for Nyron architecture. GitHub is durable design memory; chat windows are temporary working contexts.

## 2. Authority

Nyron uses one **Lead Design Authority** for system-level integration and freeze decisions.

Specialists/reviewers provide Candidates/evidence only. Frozen semantics change only through explicit Amendment or superseding baseline.

## 3. Read This First

For implementation/design work:
1. `design/coordination/STATUS.md`
2. `design/Nyron_Overall_System_Architecture_Frozen_Baseline_v0.1.md`
3. the exact subsystem frozen baseline/amendment relevant to the task
4. only then the minimum supporting Candidate/clarification documents needed for detail

### Historical Candidate rule

A historical `Candidate` is **not standalone implementation authority** after a Frozen Baseline or Amendment exists.

Implementation and review MUST resolve semantics in this order:

```text
Overall Frozen Baseline
-> subsystem Frozen Baseline
-> accepted Amendments
-> normative Lead clarifications pinned by the baseline
-> historical Candidate for remaining supporting detail only
```

If historical Candidate wording conflicts with an accepted Amendment, the Amendment controls. Do not reconstruct correctness from the Candidate alone or treat older wording as current merely because it remains visible in the repository.

Known documentation supersession notice:
- D-008 retry safety / `FENCED` wording — `design/errata/NYRON-D-008_Candidate_Supersession_Notice.md`

Process model:
- `design/process/Nyron_Design_Operating_Model_v0.1.md`

## 4. Overall System Architecture — FROZEN

Authoritative implementation baseline:
- `design/Nyron_Overall_System_Architecture_Frozen_Baseline_v0.1.md`
- freeze commit: `28f7f62ac9f269a7a510a037131e938c3b7f44a2`

The frozen manifest pins the exact Overall candidate content, D-001 clarifications, all frozen subsystem baselines and all accepted amendments existing at freeze time. Later Lead-approved frozen Amendments listed in `design/coordination/STATUS.md` extend the implementation authority under the same change-control rule.

**System Foundation implementation gate: OPEN.**

## 5. Frozen Architecture Baselines / Amendments

- Module Architecture — `design/Universal_Runtime_Module_Design_Report_v0.1.md`
- Module Amendment 001 / EffectOperation PREPARED — `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
- Graph / Composite — `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md`
- Graph / Accounting Amendment 001 — `design/amendments/Graph_Accounting_Amendment_001_Static_Accounting_Scope_Resolution.md`
- Runtime Orchestration — `design/Nyron_Runtime_Orchestration_Frozen_Baseline_v0.1.md`
- Runtime / Accounting Amendment 001 / Cross-Owner Identity & Persistence Boundary — `design/amendments/Runtime_Accounting_Amendment_001_Cross_Owner_Identity_Persistence_Boundary.md`
- Capability / Resource / Effect Authority — `design/Nyron_Capability_Resource_Effect_Authority_Frozen_Baseline_v0.1.md`
- Accounting / Recovery — `design/Nyron_Accounting_Recovery_Frozen_Baseline_v0.1.md`
- Distribution / Module Ecosystem — `design/Nyron_Distribution_Module_Ecosystem_Frozen_Baseline_v0.1.md`
- External Interfaces / Workspace Boundary — `design/Nyron_External_Interfaces_Workspace_Frozen_Baseline_v0.1.md`
- External Interfaces Amendment 001 / FENCED retry semantics — `design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`
- Human Interaction / Approval Authority — `design/Nyron_Human_Interaction_Approval_Authority_Frozen_Baseline_v0.1.md`
- Project / Workspace / Policy Context — `design/Nyron_Project_Workspace_Policy_Context_Frozen_Baseline_v0.1.md`
- PWP Amendment 001 / Historical Revision Retention — `design/amendments/PWP_Amendment_001_Historical_Revision_Retention.md`

## 6. Final Review Evidence

D-004 independent adversarial review/re-review:
- `design/reviews/NYRON-D-004_GPT_Adversarial_Review_FAIL_2026-08-24.md`
- `design/reviews/NYRON-D-004_GPT_Targeted_ReReview_PASS_Receipt_2026-08-24.md`

Integrated Claude review:
- first pass FAIL: `design/reviews/NYRON-D-001_Claude_Integrated_Review_FAIL_2026-08-24.md`
- targeted R2 PASS: `design/reviews/NYRON-D-001_Claude_Targeted_ReReview_PASS_2026-08-24.md`

Final R2 result:

```text
F01 closure: PASS
F02 closure: PASS
Additional blocking findings: None
Freeze recommendation: YES
```

Non-blocking documentation hygiene record:
- `design/reviews/NYRON-D-008_Documentation_Hygiene_Observation_2026-08-25.md`

Post-freeze implementation finding closure:
- Task 108 `CROSS_OWNER_RUNTIME_ACCOUNTING_STORAGE_BOUNDARY_UNFROZEN`
- disposition: `VALID BLOCKER / CLOSED BY ARCHITECTURE AMENDMENT`
- authority: `design/amendments/Runtime_Accounting_Amendment_001_Cross_Owner_Identity_Persistence_Boundary.md`

## 7. Core Frozen Cross-System Rules

```text
Packet -> Delivery -> Activation -> Run / Attempt
```

No second direct-Activation execution path.

```text
CapabilityGrant != ResourceLease != EffectOperation != BudgetReservation
```

```text
FENCED != no prior consequence != safe semantic replay
```

```text
unknown overlap -> conflicting
```

```text
revoke/replacement wins authority-consumption race -> reject new use
exact use admission wins -> durable pre-revoke in-flight work
```

```text
unresolved static_accounting_scope_ref -> execution admission denied
```

```text
retained canonical history pins PWP revision -> exact revision remains resolvable
```

```text
logical Owner != physical database placement
cross-owner SQL FK != foreign Owner authority proof
```

```text
Accounting may persist Runtime identity references
!= Accounting owns or must locally duplicate Runtime canonical rows
```

## 8. Product Node / Visual UX — D-006

D-006 remains outside the System Foundation freeze and may now proceed on top of the frozen architecture.

Product work must consume the frozen generic Module / Graph / Runtime / Capability / Resource / Effect / Accounting / Human / PWP mechanisms. If Product design exposes a real expressiveness gap, raise an Architecture Finding instead of inventing a local Kernel primitive.

## 9. Working Product / Collaboration Design

Conversation-confirmed working product/orchestration decisions that do not supersede frozen architecture:

- `design/Nyron_Automated_Visual_MultiAgent_Collaboration_Design_Decisions_v0.1.md`

This record captures the automated visual multi-Agent collaboration direction, Agent lifecycle, plugin/capability model, scoped authority, runtime mutation/event sourcing, Handoff, Director/Subagent communication, Scheduler, Monitor and staged structured-state decisions. Open frontier items remain explicitly marked non-authoritative until decided.

## 10. Change Control

Implementation may refine storage, schemas, APIs, diagnostics and UX where observable frozen semantics do not change.

Any required semantic change must follow:

```text
Architecture Finding
-> Lead review
-> explicit Amendment or superseding baseline
-> targeted review when warranted
-> affected implementation gate re-open
```
