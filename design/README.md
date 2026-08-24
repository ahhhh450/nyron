# Nyron Design

## 1. Purpose

`design/` is the authoritative home for Nyron pre-implementation architecture.

Design documents define canonical ownership, contracts, invariants, state/lifecycle semantics, cross-owner boundaries, replay/fencing rules, implementation gates, review evidence, Architecture Findings and frozen baselines before code is allowed to establish those semantics implicitly.

GitHub is durable design memory. Chat windows are temporary working contexts.

---

## 2. Design Authority

Nyron uses one **Lead Design Authority** for system-level consistency and freeze decisions.

Lead owns:
- Overall architecture;
- subsystem decomposition;
- canonical Owner assignment;
- cross-subsystem integration;
- task/review sequencing;
- Architecture Finding disposition;
- Amendment/superseding-baseline decisions;
- final freeze.

Dedicated specialist windows produce Candidates only.
Independent reviewers provide advisory evidence only.

A reviewer PASS is invalid if it materially misreads the actual design/frozen premises.

---

## 3. Design Baseline Rules

1. **FROZEN** design is an implementation contract.
2. Frozen semantic change requires explicit Amendment or superseding frozen baseline.
3. Silent reinterpretation is forbidden.
4. Cross-owner state has exactly one authoritative Owner.
5. Product-visible Node concepts do not automatically become Runtime/Kernel primitives.
6. Unknown past facts are never guessed into convenient success/failure/non-dispatch/clearance.
7. Cross-owner global atomic transactions are not assumed unless an explicit frozen contract says otherwise.
8. Exact immutable execution definitions are never silently upgraded to latest/current versions.
9. Implementation detail is free only where it does not alter frozen observable/canonical semantics.

---

## 4. Read This First

For current project state:

1. `design/coordination/STATUS.md`
2. the exact Task brief under `design/coordination/tasks/` if working on a delegated task
3. only the minimum baseline/candidate documents listed by that Task

For Lead main-window immediate work:
- `design/coordination/LEAD_ACTIVE_QUEUE.md`

For reusable design-process rules:
- `design/process/Nyron_Design_Operating_Model_v0.1.md`

Do not scan all historical task/review material unless a concrete integration issue requires it.

---

## 5. Current Frozen Architecture

### 5.1 Module Architecture — FROZEN

- `design/Universal_Runtime_Module_Design_Report_v0.1.md`

Core frozen rules include:
- Module is Runtime primitive; Product Node is not;
- immutable ModuleDefinition@version;
- Packet -> Delivery -> Activation -> Run;
- explicit Suspension/Continuation/Resume;
- Commit Fencing / Effect Fencing;
- Capability / Resource / Packet separation;
- ResourceLease lifecycle;
- BudgetReservation / Accounting separation;
- ReconciliationCase / UNKNOWN handling;
- Module Host mediation/trust boundary.

### 5.2 Module Amendment 001 — FROZEN

- `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`

Adds/clarifies:
- `EffectOperation.PREPARED` before crash-ambiguous dispatch;
- PREPARED does not prove dispatch happened;
- uncertain recovered PREPARED cannot blind-retry;
- EffectOperation is Kernel-visible canonical record whose domain lifecycle is Effect Authority-owned.

### 5.3 Graph / Composite v0.1 — FROZEN

- `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md`

Core frozen rules include:
- Graph logical identity / immutable GraphRevision execution identity;
- exact Module/config/Port/Edge pinning;
- Composite definition-time deterministic materialization;
- persisted leaf topology is Runtime authority;
- FEEDBACK is intentional-cycle marker only;
- no hidden Loop/Branch/Join Runtime primitive;
- exact dependency/import semantics;
- broken definitions may be preserved but cannot execute.

---

## 6. Current Consolidated Overall Candidate

- `design/Nyron_Overall_System_Architecture_v0.1.md`
- Status: **DRAFT — CONSOLIDATED INTEGRATED PRE-FREEZE CANDIDATE**

The current Overall candidate has closed the v0.1 canonical Owner gaps at Lead-integration level.

Integrated Owner domains:
- Graph subsystem;
- Module Registry / Distribution Owner;
- Project / Workspace Context Owner (PWP Owner);
- Runtime Orchestration;
- Capability Authority;
- Resource Manager;
- Effect Authority;
- Accounting Owner;
- Recovery Owner;
- Human Interaction Owner.

Key Lead clarifications:
- `design/clarifications/NYRON-D-001_Lead_Integration_Clarification_001.md`
- `design/clarifications/NYRON-D-001_Lead_Integration_Clarification_002.md`

Final Overall freeze is still gated by subsystem independent reviews/freeze consolidation and integrated Claude adversarial review.

---

## 7. Lead-Integrated Subsystem Candidates

### Runtime Orchestration — D-003

- Candidate: `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`
- Lead result: PASS
- Independent review: active
- Important clarifications:
  - `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`
  - `design/clarifications/NYRON-D-003_D-010_Lead_Integration_Clarification_002.md`

### Capability / Resource / Effect — D-004

- Candidate: `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`
- Lead result: PASS with Frozen Amendment 001
- Independent review: active
- Integration clarification:
  - `design/clarifications/NYRON-D-004_Lead_Integration_Clarification_002.md`

### Accounting / Recovery — D-005

- Candidate: `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`
- Lead result: PASS
- Independent review: active
- Important clarifications:
  - `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`
  - `design/clarifications/NYRON-D-005_D-010_Lead_Integration_Clarification_002.md`

### Distribution / Module Ecosystem — D-007

- Candidate: `design/Nyron_Distribution_Module_Ecosystem_Design_Candidate_v0.1.md`
- Lead result: PASS WITH CLARIFICATION
- Independent review: ready
- Clarification:
  - `design/clarifications/NYRON-D-007_D-010_Lead_Integration_Clarification_001.md`

### External Interfaces / Workspace Boundary — D-008

- Candidate: `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`
- Lead result: PASS
- Independent review: active
- Clarifications:
  - `design/clarifications/NYRON-D-008_Lead_Integration_Clarification_001.md`
  - `design/clarifications/NYRON-D-008_D-010_Lead_Integration_Clarification_002.md`

### Human Interaction / Approval Authority — D-009

- Candidate: `design/Nyron_Human_Interaction_Approval_Authority_Design_Candidate_v0.1.md`
- Lead result: PASS WITH CLARIFICATION
- Independent review: ready
- Clarification:
  - `design/clarifications/NYRON-D-009_Lead_Integration_Clarification_001.md`

### Project / Workspace / Policy Context — D-010

- Candidate: `design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`
- Lead result: PASS; AF-PWP-001 resolved
- Independent review: ready
- Key clarifications:
  - `design/clarifications/NYRON-D-010_D-001_Lead_Integration_Clarification_001.md`
  - `design/clarifications/NYRON-D-007_D-010_Lead_Integration_Clarification_001.md`
  - `design/clarifications/NYRON-D-008_D-010_Lead_Integration_Clarification_002.md`
  - `design/clarifications/NYRON-D-003_D-010_Lead_Integration_Clarification_002.md`
  - `design/clarifications/NYRON-D-005_D-010_Lead_Integration_Clarification_002.md`

---

## 8. Product Node / Visual UX — D-006

D-006 is currently **deferred and non-blocking for System Foundation freeze**.

Reason:
- Node remains Product Layer only;
- Product Extension Envelope is already explicit;
- Browser/Shell/File/HTTP/Provider/Human/etc. map through generic frozen/lead-integrated mechanisms;
- no unresolved Product-only canonical Owner is required for current foundation correctness.

If later Product design exposes a real architecture expressiveness gap, it must raise an Architecture Finding rather than invent a local Kernel/Runtime primitive.

---

## 9. Review Task Index

Bounded DeepSeek review tasks:
- `design/coordination/tasks/NYRON-D-003-REVIEW-DS.md`
- `design/coordination/tasks/NYRON-D-004-REVIEW-DS.md`
- `design/coordination/tasks/NYRON-D-005-REVIEW-DS.md`
- `design/coordination/tasks/NYRON-D-007-REVIEW-DS.md`
- `design/coordination/tasks/NYRON-D-008-REVIEW-DS.md`
- `design/coordination/tasks/NYRON-D-009-REVIEW-DS.md`
- `design/coordination/tasks/NYRON-D-010-REVIEW-DS.md`

Prepared final integrated Claude review:
- Manifest: `design/reviews/NYRON-D-001_Integrated_Adversarial_Review_Manifest_DRAFT.md`
- Task: `design/coordination/tasks/NYRON-D-001-REVIEW-CLAUDE.md`
- Gate: NOT OPEN until subsystem review/freeze closure is sufficient.

---

## 10. Core Cross-System Rules

The current integrated system preserves:

```text
Packet -> Delivery -> Activation -> Run / Attempt
```

No API, Human, PWP, Adapter, Registry or Product path may create a second direct-Activation execution path.

Generic workflow-start external ingress:

```text
PWP IngressRouteRevision
-> adapter auth/validation/canonicalization
-> Runtime-owned ExecutionIngressFact
-> Runtime admission
-> Trigger Packet
-> Delivery
-> Activation
```

Domain-specific external facts remain domain-owned:
- HumanResponse -> Human Interaction;
- billing/usage -> Accounting;
- effect evidence -> Effect Authority;
- Resource/Lease truth -> Resource Manager.

Policy-context pattern:

```text
PWP immutable policy context
-> domain Owner evaluation
-> domain Owner commits decision truth
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

---

## 11. Design Thread / Repository Rules

Canonical specialist conversation name:

```text
NYRON-D-XXX
```

Every new specialist prompt must explicitly provide:
- repository URL;
- Task ID;
- exact Task brief path;
- design-only/no-freeze boundary;
- required Candidate repository path;
- commit SHA return requirement;
- instruction to rename conversation to Task ID.

Specialist Candidate output must normally be committed to repository. Chat-only output is not normal completion when write capability exists.

---

## 12. Current Next Gate

Current work is no longer canonical Owner discovery.

Next sequence:
1. validate bounded independent review outputs;
2. resolve valid findings/clarifications;
3. freeze passing subsystem baselines/manifests;
4. update final integrated review Manifest with exact frozen constituent identities;
5. open Claude integrated adversarial review gate;
6. resolve valid integrated findings;
7. Lead-freeze Overall System Architecture v0.1.
