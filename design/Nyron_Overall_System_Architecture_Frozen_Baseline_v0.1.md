# Nyron Overall System Architecture Frozen Baseline v0.1

**Status:** **FROZEN OVERALL SYSTEM ARCHITECTURE BASELINE**  
**Authority:** Nyron Lead Design Authority  
**Freeze date:** 2026-08-24  
**Scope:** Nyron v0.1 System Foundation architecture

## 1. Final Freeze Decision

Nyron Overall System Architecture v0.1 is hereby **FROZEN** for implementation.

This freeze follows:
- subsystem Lead integration and individual freeze closure;
- explicit frozen amendments for discovered correctness defects;
- independent GPT adversarial review and targeted re-review of D-004;
- integrated Claude adversarial review;
- targeted Claude re-review validating closure of the two final integrated findings.

Only an explicit Lead-approved Architecture Amendment or superseding frozen baseline may change the semantics frozen here.

## 2. Primary Overall Architecture Content

The primary integrated Overall architecture is the exact content of:

1. `design/Nyron_Overall_System_Architecture_v0.1.md`
   - blob SHA: `8acaf5385a2e89977a2fca5e42a953dccd6d2430`
2. `design/clarifications/NYRON-D-001_Lead_Integration_Clarification_001.md`
   - blob SHA: `e7ec38e40aa3bcf17c2ba9a968f74e85cdbe46c6`
3. `design/clarifications/NYRON-D-001_Lead_Integration_Clarification_002.md`
   - blob SHA: `4765ae2835873103fea07bab4e1663b8c3ec84da`

The source Overall document may still contain a pre-freeze status header. This manifest is the authoritative freeze declaration for the exact content above plus the frozen subsystem/amendment set below.

## 3. Frozen System Foundation Constituents

The Overall baseline incorporates and is constrained by these frozen baselines:

- Module Architecture — `design/Universal_Runtime_Module_Design_Report_v0.1.md`
- Graph / Composite — `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md`
- Runtime Orchestration — `design/Nyron_Runtime_Orchestration_Frozen_Baseline_v0.1.md`
  - freeze commit: `6ac6cb3f031dff0f87b2d50890da37ef198c462d`
- Capability / Resource / Effect Authority — `design/Nyron_Capability_Resource_Effect_Authority_Frozen_Baseline_v0.1.md`
  - freeze commit: `041d868c7d021d5610494c8e3cab50811837b45d`
- Accounting / Recovery — `design/Nyron_Accounting_Recovery_Frozen_Baseline_v0.1.md`
  - freeze commit: `add48655af5e5f371daa4c271b813309eeddacbd`
- Distribution / Module Ecosystem — `design/Nyron_Distribution_Module_Ecosystem_Frozen_Baseline_v0.1.md`
  - freeze commit: `3210da0f30a6c8015b5dec322d22412600f0b081`
- External Interfaces / Workspace Boundary — `design/Nyron_External_Interfaces_Workspace_Frozen_Baseline_v0.1.md`
  - freeze commit: `b0ecf012b286758a44891dff8ce7929abab552e1`
- Human Interaction / Approval Authority — `design/Nyron_Human_Interaction_Approval_Authority_Frozen_Baseline_v0.1.md`
  - freeze commit: `c4f709e88bb1cfa284069958b4992cf4f61d91c5`
- Project / Workspace / Policy Context — `design/Nyron_Project_Workspace_Policy_Context_Frozen_Baseline_v0.1.md`
  - freeze commit: `bc70f744ec93d877332264d89cdc76354df77146`

D-006 Product Node / Visual Workflow UX remains intentionally outside the System Foundation freeze and is not a blocker unless later Product work exposes a real architecture defect.

## 4. Frozen Amendments Included

### Module Amendment 001 — EffectOperation PREPARED

- `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
- blob SHA: `a179144c7a39f2f991f4ec5001522ddb9af901f8`

Frozen effect rule includes durable `EffectOperation(PREPARED)` identity before crash-ambiguous external dispatch; PREPARED never proves dispatch/non-dispatch.

### External Interfaces Amendment 001 — FENCED Is Not Semantic Retry Clearance

- `design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`
- blob SHA: `9fb007d6e44f869b51022c5fd4ef05482e8cf81c`
- amendment commit: `d54d3088879c82f6869554a141c11221e63e5fdb`

Frozen rule:

```text
FENCED active/conflict clearance
!= historical outcome certainty
!= semantic retry clearance
```

### Graph / Accounting Amendment 001 — Static AccountingScope Reference Resolution

- `design/amendments/Graph_Accounting_Amendment_001_Static_Accounting_Scope_Resolution.md`
- blob SHA: `8111ba48978816be57164b1d7fb02513b606ec87`
- amendment commit: `a9a8ff9566246b57b338f134815888106ea21765`

Frozen rule: an execution may not enter Runtime admission with an unresolved/invalid required `static_accounting_scope_ref` or incomplete Accounting-owned ancestor chain. Graph may preserve broken/unresolved definitions as non-executable artifacts; Accounting retains ownership of scope truth.

### PWP Amendment 001 — Historical Revision Retention and Resolvability

- `design/amendments/PWP_Amendment_001_Historical_Revision_Retention.md`
- blob SHA: `5bb55ebaac097642bdf8b1630399f1eebe5c711a`
- amendment commit: `1c984217a16278bbb107fd5a425ef937b6a0e873`

Frozen rule: PWP revisions pinned by durable execution/canonical history remain resolvable while referenced, including ProjectConfigRevision, WorkspaceConfigRevision, PolicyContextRevision, EnvironmentBindingRevision and IngressRouteRevision.

## 5. Final Review Evidence

### D-004 independent adversarial review

- FAIL evidence: `design/reviews/NYRON-D-004_GPT_Adversarial_Review_FAIL_2026-08-24.md`
- targeted PASS evidence: `design/reviews/NYRON-D-004_GPT_Targeted_ReReview_PASS_Receipt_2026-08-24.md`

The D-004 review established and revalidated:
- no external-ID exception to PREPARED-before-dispatch;
- fail-closed versioned EffectConflictScope;
- FENCED is not semantic retry clearance;
- active state and historical consequence remain orthogonal;
- authority consumption linearizes against Attempt/Grant/Lease revocation/replacement;
- cached validation cannot authorize late dispatch/foreign mutation.

### Integrated Claude adversarial review

First integrated review:
- `design/reviews/NYRON-D-001_Claude_Integrated_Review_FAIL_2026-08-24.md`

The two accepted final findings were corrected by:
- Graph / Accounting Amendment 001;
- PWP Amendment 001.

Targeted Claude re-review:
- `design/reviews/NYRON-D-001_Claude_Targeted_ReReview_PASS_2026-08-24.md`
- result: **PASS**
- F01 closure: PASS
- F02 closure: PASS
- additional blocking findings: None
- freeze recommendation: YES

## 6. Frozen System-Level Invariants

The Overall baseline freezes, among other rules:

1. every correctness-relevant canonical state has exactly one authoritative Owner;
2. references do not transfer mutation authority;
3. Runtime execution has one path: `Packet -> Delivery -> Activation -> Run / Attempt`;
4. immutable definitions and semantic admission context are pinned exactly;
5. historical replay does not re-resolve mutable `current/latest` definitions/context;
6. stale Attempts cannot canonical-commit, resume or initiate new mediated authority use;
7. actual authority use linearizes race-safely against replacement/revocation;
8. CapabilityGrant, Resource/ResourceLease, EffectOperation and BudgetReservation remain separate authorities/facts;
9. crash-ambiguous external effects have durable PREPARED identity before dispatch;
10. unknown past external facts remain UNKNOWN rather than being guessed;
11. active-effect clearance is distinct from semantic retry safety;
12. Effect conflict overlap fails closed unless disjointness is positively proven;
13. Recovery disposition does not fabricate foreign Owner truth/clearance;
14. hierarchical hard budget reservation is Accounting Owner-local and applies to the complete resolvable static ancestry;
15. required static accounting-scope references must resolve before execution admission;
16. PWP pinned historical revision classes remain resolvable while durable history references them;
17. Project/Workspace policy context is input to domain Owners, not the resulting authority/decision;
18. Package trust/install/enable is not Capability or Runtime admission;
19. external ingress cannot bypass Runtime admission or create Activation directly;
20. Product-visible concepts remain above the Kernel/Runtime primitive taxonomy unless a future explicit amendment says otherwise.

## 7. Implementation Gate

**SYSTEM FOUNDATION IMPLEMENTATION GATE: OPEN**

Implementation may now proceed against this frozen architecture.

Implementation MUST stop and raise an Architecture Finding instead of silently changing semantics if it requires:
- a new canonical Owner or Owner collision;
- a second execution/admission path;
- weakening Attempt/authority fencing;
- changing frozen effect/retry/UNKNOWN semantics;
- bypassing static accounting-scope resolution;
- allowing historical PWP context to become unresolvable while referenced;
- changing frozen Graph/Module identity/version behavior;
- introducing product-specific Kernel primitives;
- changing any other frozen invariant in the constituent baselines/amendments.

## 8. Change Control

This is the implementation authority for Nyron v0.1 System Foundation.

Future work may add implementation detail, schemas, storage layout, APIs, diagnostics and product UX only when those additions do not weaken or reinterpret the frozen semantics.

Any required semantic change must follow:

```text
Implementation/Design discovery
-> Architecture Finding
-> Lead review
-> explicit Amendment or superseding baseline
-> targeted re-review where warranted
-> implementation gate re-open for affected scope
```
