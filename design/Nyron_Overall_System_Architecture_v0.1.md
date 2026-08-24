# Nyron Overall System Architecture v0.1

**Status:** **DRAFT — CONSOLIDATED INTEGRATED PRE-FREEZE CANDIDATE**  
**Authority:** Nyron Lead Design Authority  
**Scope:** System foundation, first-class subsystem ownership, cross-owner correctness, replay/fencing boundaries, product extension envelope, and implementation dependency gates.

## Authoritative frozen dependencies

- `design/Universal_Runtime_Module_Design_Report_v0.1.md` — **FROZEN MODULE ARCHITECTURE BASELINE**
- `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md` — **FROZEN MODULE ARCHITECTURE AMENDMENT**
- `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md` — **FROZEN GRAPH / COMPOSITE ARCHITECTURE BASELINE**

## Lead-integrated subsystem candidate set

- `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`
- `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`
- `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`
- `design/Nyron_Distribution_Module_Ecosystem_Design_Candidate_v0.1.md`
- `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`
- `design/Nyron_Human_Interaction_Approval_Authority_Design_Candidate_v0.1.md`
- `design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`

## Lead integration clarifications incorporated into this consolidation

- `design/clarifications/NYRON-D-001_Lead_Integration_Clarification_001.md`
- `design/clarifications/NYRON-D-001_Lead_Integration_Clarification_002.md`
- `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`
- `design/clarifications/NYRON-D-007_D-010_Lead_Integration_Clarification_001.md`
- `design/clarifications/NYRON-D-008_Lead_Integration_Clarification_001.md`
- `design/clarifications/NYRON-D-009_Lead_Integration_Clarification_001.md`
- `design/clarifications/NYRON-D-010_D-001_Lead_Integration_Clarification_001.md`

This document does not freeze the review-pending subsystem candidates by reference. It consolidates their Lead-accepted architecture for final subsystem review/freeze and later integrated adversarial review.

Any conflict with a frozen dependency requires an explicit Architecture Finding and, if accepted, an Amendment or superseding frozen baseline. Silent reinterpretation is forbidden.

---

# 0. System Principle

Nyron is a system of explicitly owned canonical facts coordinated through durable mediated contracts.

The central rules are:

1. every correctness-relevant canonical state class has one authoritative Owner;
2. immutable execution definitions are pinned exactly;
3. Runtime execution follows one path only;
4. cross-owner mutation is never implicit/global;
5. crash/timeout/absence never authorizes guessed historical truth;
6. product-visible concepts do not become Kernel primitives merely because users can see them.

---

# 1. Four-Layer Architecture

## 1.1 Product Layer

User-facing concepts and surfaces:
- visual Nodes;
- workflow editor;
- Composite presentation;
- Human approval/review UI;
- Project/Workspace UX;
- diagnostics and explanations;
- CLI/public API;
- product labels such as Agent, Reviewer, Router, Browser, Shell, File, Model or Tool.

Product labels are presentation/application concepts, not Runtime or Kernel primitive taxonomy.

## 1.2 Definition Layer

Immutable or authoring-time definition truth:
- Graph / GraphDraft / GraphRevision;
- Composite / CompositeRevision;
- ModuleDefinition / ModuleInstanceRevision;
- concrete Port and Edge topology;
- immutable config/schema references;
- package/registry metadata required to resolve exact implementations.

Graph defines **what executable definition exists**. Runtime defines **when and how admitted execution progresses**.

## 1.3 Runtime / Domain Owners

First-class logical Owner domains:
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

External adapters and Module Host mediate boundaries but do not become semantic Owners merely because they perform work.

## 1.4 Kernel Foundation

Generic correctness machinery only:
- canonical identity;
- durable record/event persistence;
- owner-local transaction primitives;
- immutable-reference/revision enforcement;
- Owner write-boundary enforcement;
- fencing primitives;
- causal references;
- replay/deduplication foundation.

Kernel does not own domain business state machines.

---

# 2. Canonical Owner Model

Every canonical state class required by v0.1 has one named authoritative Owner.

| Canonical state class | Authoritative Owner |
| --- | --- |
| GraphRevision / executable definition topology | Graph subsystem |
| ModuleDefinition registration identity/digest + package publication binding | Module Registry / Distribution Owner |
| Module package / Registry publication / install / trust / enable governance | Module Registry / Distribution Owner |
| Project / Workspace identity | PWP Owner |
| ProjectConfig / WorkspaceConfig / PolicyContext / EnvironmentBinding revisions | PWP Owner |
| IngressRoute identity/revision/configuration | PWP Owner |
| generic workflow `ExecutionIngressFact` | Runtime Orchestration |
| Packet / Delivery / Activation | Runtime Orchestration |
| Run / RunAttempt / current Attempt / fencing generation | Runtime Orchestration |
| Continuation / Subscription / EventDelivery consumption | Runtime Orchestration |
| CapabilityGrant | Capability Authority |
| Resource / ResourceLease | Resource Manager |
| EffectOperation | Effect Authority |
| AccountingScope accounting metadata / BudgetPolicyRevision | Accounting Owner |
| BudgetReservation / UsageFact / settlement / overrun | Accounting Owner |
| ReconciliationCase / Recovery disposition | Recovery Owner |
| HumanRequest / accepted HumanResponse / HumanDecisionEvidence | Human Interaction Owner |

References do not transfer ownership.

Examples:
- Graph may pin `static_accounting_scope_ref`; Accounting still owns accounting truth.
- PWP may provide capability/trust/responder policy context; the target domain Owner still commits the resulting decision.
- EffectOperation may reference ResourceLease, CapabilityGrant and BudgetReservation without owning them.
- IngressRoute may name a canonical target Owner without PWP owning the target fact.

No correctness-critical v0.1 `future owner` placeholder remains in this integrated set.

---

# 3. Kernel Boundary

Kernel MUST provide/enforce:
- stable canonical identities;
- durable records/events;
- owner-local atomic transactions;
- immutable references and revision semantics;
- Owner write enforcement;
- fencing-token primitives;
- causal references;
- replay/dedupe foundations.

Kernel MUST NOT own:
- Graph scheduling semantics;
- Runtime retry/replacement/cancellation policy;
- Capability policy meaning;
- Resource lifecycle meaning;
- EffectOperation domain lifecycle;
- Accounting settlement;
- Recovery policy;
- package marketplace/trust UX;
- Project/Workspace role/product UX;
- provider/browser/process taxonomy;
- Human approval presentation;
- product Node taxonomy.

Subsystem objects may be Kernel-visible canonical records without their domain state machines becoming Kernel-owned.

---

# 4. Canonical Truth

Canonical Truth is durable information Nyron must still interpret correctly after crash, restart, retry, replacement, replay, queue duplication or worker loss.

Nyron uses both:
- **Canonical State** — authoritative current durable truth;
- **Canonical History** — durable facts/evidence explaining committed transitions.

RAM, worker queues, provider sessions, adapter caches, UI caches, private module files and telemetry are not canonical merely because they exist.

If losing/recomputing a fact could change the meaning of committed history, the required fact/evidence must be canonical.

Unknown past facts remain UNKNOWN until reliable evidence or an explicit scoped policy disposition is committed. A disposition must never be represented as evidence that an unknown historical fact became objectively known.

---

# 5. Cross-Owner Interaction and Transaction Rules

## 5.1 Vocabulary

Cross-owner interactions use:
- **Query** — observe without mutation authority;
- **Command** — request the target Owner attempt a transition; not proof of success;
- **Event** — durable evidence that a canonical fact already committed;
- **Proposal** — non-authoritative suggestion/request for consideration.

An Event from Owner A may be evidence for Owner B but never grants A mutation authority over B.

A CapabilityGrant permits a mediated request; it does not bypass the target Owner's final mutation decision.

## 5.2 Owner-local atomicity

Within one Owner, correctness invariants requiring atomicity MUST use one owner-local canonical transaction or equivalent no-gap mechanism.

Examples:
- consumptive Delivery binding + Activation creation;
- Attempt replacement + current-attempt pointer/fencing update;
- full-ancestry hard budget reservation;
- HumanResponse acceptance + request aggregate/terminal update where required.

## 5.3 No global cross-owner transaction assumption

Across Owners, Nyron uses:
- durable Commands/Events;
- stable identities;
- idempotency/deduplication;
- replayable propagation;
- reconciliation.

Temporary cross-owner partial convergence is acceptable only if every local committed fact is correct and a bounded deterministic convergence/recovery path exists.

---

# 6. Canonical Events, External Events, Notifications and Ordering

Nyron distinguishes:
1. **Canonical Event** — durable committed system fact;
2. **External Event** — outside input, initially untrusted;
3. **Runtime Notification** — transient wake/scheduling hint;
4. **Telemetry** — logs/traces/metrics, non-canonical by default.

A committed fact required by another Owner must have durable replayable propagation established atomically with the local transition or through equivalent correctness machinery.

Transport exactly-once is not required. Consumers tolerate duplicate delivery through stable identity/idempotency.

Wall-clock arrival time alone is not canonical ordering authority.

Semantic ordering relies on committed identities, owner-local canonical ordering, causal refs and immutable definition ordinals where required.

---

# 7. Definition / Graph Boundary — Frozen

The frozen Graph/Composite baseline is system-wide authority:
- Graph is logical identity; Runtime pins exact immutable GraphRevision;
- Runtime never resolves `latest/current` definitions for an admitted execution;
- ModuleInstanceRevision pins exact ModuleDefinition@version and immutable config;
- concrete Ports/Edges are immutable GraphRevision facts;
- Composite materializes before execution into persisted leaf topology;
- Runtime never re-flattens Composite for correctness;
- FEEDBACK marks intentional cyclic topology only and changes no Runtime semantics;
- Loop/Branch/Join are not hidden Kernel/Runtime primitives;
- unresolved definitions may be preserved but cannot enter execution admission.

Graph/Composite dependency manifest remains derived exact dependency metadata, not Registry or Runtime authority.

---

# 8. Runtime Orchestration Boundary

## 8.1 One execution path

```text
Packet -> Delivery -> Activation -> Run / Attempt
```

There is no second direct-Activation path.

## 8.2 Execution admission

Runtime owns WorkflowExecution admission and pins:
- exact GraphRevision;
- exact immutable Runtime policy reference;
- exact semantic Project/Workspace/PWP context revisions needed for replay;
- exact ingress-route/Graph ingress binding when applicable;
- causal/admission identity.

Mutable deployment defaults cannot reinterpret an already admitted execution.

## 8.3 Retry, replacement and resume

- each Activation has one Run lineage;
- retry creates a new Attempt under the same Run after prior disposition;
- replacement creates a new Attempt while old Attempt may still be active/ambiguous;
- resume stays inside the same current Attempt.

Exactly one Attempt is current for a Run.

Replacement/cancellation atomically removes old future commit/resume/new-effect authority.

Already-dispatched external effects do not disappear merely because an Attempt became stale.

## 8.4 Completion

Execution terminal state is canonical quiescence/directive result, not empty queue or absent workers.

A suspended current Attempt with a valid Subscription remains nonterminal.

---

# 9. Capability / Resource / Effect Authority

These are orthogonal:

```text
CapabilityGrant != Resource/ResourceLease != EffectOperation
```

## 9.1 Capability

Capability = bounded machine-checkable authority to request an operation.

Grant is Attempt/fencing/scope/validity-bound, revocable and non-transferable.

Actual external boundary revalidates authority; stale cached permission cannot authorize post-revocation work.

## 9.2 Resource

Resource = managed opaque stateful handle.

ResourceLease = bounded temporary use authority.

Resource continuity never becomes sole workflow semantic truth.

## 9.3 EffectOperation

EffectOperation = durable external-effect history/tracking truth.

Frozen Amendment 001 requires:

```text
PREPARED durable identity
-> authority/fencing revalidation
-> crash-ambiguous external dispatch
-> external evidence / ACTIVE / COMPLETED / revoke / FENCED / UNKNOWN
```

PREPARED does not prove dispatch occurred.
Timeout/disconnect/absence does not prove failure or non-dispatch.
Cancellation request is not FENCED evidence.

## 9.4 Replacement conflict clearance

When R2 replaces R1:
- R1 immediately loses new-effect authority;
- existing R1 effects require authoritative completion/fencing/UNKNOWN handling;
- conflicting R2 authority waits for owner-specific clearance;
- non-conflicting work may proceed if scope/policy prove separation.

---

# 10. Accounting / Recovery Boundary

The following remain orthogonal:

```text
EffectOperation != BudgetReservation
ResourceLease != BudgetReservation
CapabilityGrant != Budget authority
```

## 10.1 Static accounting membership

Execution accounting affiliation derives from immutable static Graph/Composite containment through `static_accounting_scope_ref`.

Dynamic Packet provenance, triggering Edge, Attempt or worker does not change membership.

Graph stores the reference; Accounting owns accounting metadata/policy/settlement.

## 10.2 Reservation and actuals

A successful hard hierarchical reservation atomically reserves every applicable ancestor inside one logical Accounting Owner transaction domain.

Actual usage is immutable evidence/history and is never capped/re-written to fit budget estimate or policy.

Late valid billing may reopen settlement without recreating spend authority.

## 10.3 Recovery

Recovery owns ReconciliationCase/evidence retry/escalation/disposition, not the subject's business truth.

`ReconciliationCase.RESOLVED` is not universal clearance.

Recovery may permit scoped administrative Runtime closure while a foreign subject remains UNKNOWN, but only the authoritative subject Owner can clear its own effect/resource/capability conflict state.

---

# 11. Project / Workspace / Policy Context (PWP)

PWP Owner owns:
- Project/Workspace identity/lifecycle;
- immutable ProjectConfig/WorkspaceConfig revisions;
- immutable PolicyContextRevision composition;
- immutable EnvironmentBindingRevision configuration;
- IngressRoute identity/revisions.

PWP does NOT own:
- live Workspace Handle Resource/Lease;
- Capability decisions;
- Runtime execution;
- Graph topology;
- raw secrets;
- PackageTrustDecision;
- HumanRequest/HumanResponse;
- target-domain external facts.

## 11.1 Workspace identity

```text
workspace_ref != raw host path != Resource != ResourceLease != mount/session handle
```

EnvironmentBindingRevision is configuration, not proof that a live resource currently exists.

## 11.2 Policy context pattern

PWP owns immutable policy-source/context composition. The target domain Owner owns the resulting decision.

Examples:

```text
PWP capability-policy context -> Capability Authority -> Grant/deny
PWP trust-policy context -> Distribution Owner -> PackageTrustDecision
PWP responder-policy context -> Human Interaction -> response acceptance/evidence
PWP Runtime admission context -> Runtime -> admission/deny
```

Owning policy inputs does not transfer decision ownership.

## 11.3 Active execution pinning

Executions preserve exact PWP revision refs needed for semantic replay.

Project/Workspace/policy/binding updates affect future admission by default, not the meaning of existing execution.

Dynamic foreign safety revocation remains possible under the foreign Owner contract; immutable context pinning never disables Capability/fencing/Resource/Effect checks.

---

# 12. External Ingress Ownership

## 12.1 Route configuration

PWP owns IngressRoute / IngressRouteRevision configuration including:
- source adapter/auth/schema/dedupe/canonicalization contract refs;
- exact canonical target Owner/event type;
- exact Project/Workspace context refs;
- exact Graph ingress binding refs where applicable.

PWP configures routing; it does not own arbitrary target facts.

## 12.2 Generic workflow-start ingress

When an external event's only canonical Nyron meaning is "request this workflow execution", Runtime owns a canonical deduplicated `ExecutionIngressFact`.

```text
External transport
-> exact IngressRouteRevision
-> adapter auth/validation/canonicalization
-> Runtime ExecutionIngressFact
-> Runtime admission
-> Trigger Packet
-> Delivery
-> Activation
-> Run / Attempt
```

No direct Activation creation is allowed.

At-least-once transport cannot accidentally duplicate one non-repeatable ingress identity.

Same stable ingress identity + conflicting semantic payload/context fails closed.

## 12.3 Domain-specific external facts

External facts with independent business meaning remain domain-owned:
- HumanResponse -> Human Interaction;
- billing/usage -> Accounting;
- effect evidence -> Effect Authority;
- resource callback/state -> Resource Manager.

Those facts may later cause a new Runtime ingress/admission, but Runtime does not re-own their business truth.

---

# 13. Human Interaction / Approval Authority

Human Interaction Owner owns:
- HumanRequest;
- accepted immutable HumanResponse;
- request-response binding;
- immutable response aggregation semantics;
- HumanDecisionEvidence when materialized;
- request lifecycle.

## 13.1 Authentication vs authorization

External response is untrusted until authenticated, authorized, schema-valid, deduplicated, request-eligible and committed by Human Interaction Owner.

Responder identity/role/membership comes from authoritative identity/PWP policy evidence; Human Interaction does not create role authority.

## 13.2 Aggregation vs responder authority

Human Interaction owns **how valid responses are counted/interpreted** (single, first-valid, quorum, veto, threshold etc.).

PWP/Identity policy owns **who is allowed to respond**.

These are separate policy classes.

## 13.3 Approval is evidence

Human approval never directly becomes CapabilityGrant or foreign mutation authority.

Typical loop:

```text
Capability policy -> REQUIRES_APPROVAL
-> HumanRequest
-> HumanResponse(s)
-> HumanDecisionEvidence
-> Capability re-evaluation
-> Grant or deny by Capability Authority
```

Higher-priority deny policy remains authoritative.

## 13.4 Wait/resume

Human Interaction creates no second wait engine.

A waiting Module uses frozen Runtime suspension:

```text
Human canonical event
-> Runtime Subscription/EventDelivery
-> current Attempt/fencing check
-> resume same Attempt
```

A valid late HumanResponse cannot resume a stale Attempt.

If Human Interaction starts a new workflow, it goes through Runtime execution ingress -> Trigger Packet -> Delivery -> Activation.

## 13.5 Rejected input

Invalid/unauthenticated/unauthorized/late/conflicting external input does not become accepted HumanResponse truth. It may be audit/security evidence elsewhere.

Response acceptance versus expiry/cancel/supersession is owner-local serialized.

---

# 14. Module Registry / Distribution

Distribution identity layers remain distinct:

```text
module_ref@version
package_ref@package_version
registry_ref
publisher_ref
```

## 14.1 Exact resolution

An executable Graph dependency resolves only exact `module_ref@version`.

Never silently substitute:
- latest;
- current;
- semver range-compatible version;
- alternate payload claiming the same identity.

Conflicting semantic payloads under one exact identity fail closed.

## 14.2 Import/install/trust/enable/execution separation

```text
Import Definition
!= Resolve Package
!= Install Package
!= Trust Package
!= Enable Package
!= CapabilityGrant
!= Runtime admission
```

Embedded/offline package bytes change transport availability only.

## 14.3 Package trust ownership

PWP may provide immutable Project/Workspace trust-policy context.

Module Registry / Distribution Owner commits canonical `PackageTrustDecision` for the exact immutable package subject/context/evidence.

Trust does not grant Capability or prove Host isolation.

## 14.4 Historical resolution

Withdrawal/security revocation may block future load/admission, but cannot rewrite historical GraphRevision/ModuleDefinition references or silently bind another payload.

Cache/mirror/Registry outage cannot cause semantic version substitution.

## 14.5 Hostile third-party code

Byte integrity/signature/trust do not prove sandbox safety.

Hostile-plugin execution may be claimed only under enforceable IsolationProfile guarantees sufficient for the threat model.

---

# 15. External World Boundary

Browser, Shell, File, HTTP, Provider/Model, Tool, Remote Worker and External Event are adapter/product families, not Kernel primitives.

Each external operation independently asks:
1. which CapabilityGrant is required?
2. which Resource/Lease is required?
3. is EffectOperation required?
4. what stable external identity/evidence exists?
5. is replay/idempotent retry safe?

## 15.1 Workspace/filesystem

Path authorization must enforce resolved containment, including symlink/junction/mount/TOCTOU posture under the declared IsolationProfile.

Persistent consequential workspace mutation normally requires EffectOperation.

## 15.2 Process

Process start is consequential EffectOperation.

A containment claim must cover descendants, not only parent PID.
Kill request is not proof of fencing.

## 15.3 Network

Destination policy is revalidated against effective DNS/redirect destination.

Profiles claiming mediation cannot expose raw unrestricted sockets as a bypass.

## 15.4 Browser/provider/remote worker

Stateful sessions may be Resources.
Consequential actions are EffectOperations.
Provider streaming does not replace Runtime Continuation.
Timeout/cancel/disconnect is not proof of external terminal state.

## 15.5 Credentials

Credential possession is not authority.

Preferred architecture keeps long-lived credentials behind trusted broker/adapter boundaries and durable canonical history stores references rather than raw secret values.

---

# 16. Module Host / Adapter Trust Boundary

Module Host and adapters may belong to the Trusted Computing Base for boundaries they enforce, but they do not own semantic truth merely because they mediate it.

Restricted Module code cannot receive bypass routes such as:
- raw canonical StateStore/DB;
- unrestricted filesystem;
- unrestricted subprocess;
- unrestricted sockets;
- raw provider/browser/worker handles bypassing checks;
- hidden durable semantic state.

Isolation is an explicit testable `IsolationProfile`, not `sandboxed=true` marketing.

Trusted builtin mode may exist but is not evidence of hostile third-party isolation.

---

# 17. Canonical vs Derived State

Derived state is reconstructible projection/cache and is never sole correctness authority.

Examples:
- scheduler ready queues;
- pending Delivery counts;
- dependency manifest caches;
- missing-module diagnostics;
- package resolution plans;
- workflow progress;
- accounting dashboards;
- Project/Workspace UI trees;
- Human inbox projections;
- indexes/search caches;
- adapter caches.

A persisted optimization becomes canonical enforcement state only if its Owner and transactional correctness semantics are explicitly defined.

---

# 18. System Architecture Invariants

### SYS-INV-01 — Single Canonical Owner
Every canonical state class has exactly one authoritative Owner.

### SYS-INV-02 — Derived State Is Not Authority
Rebuildable projection/cache cannot be sole correctness authority.

### SYS-INV-03 — Transient Scheduling Is Not History Authority
Worker/queue/wake order cannot determine canonical history unless committed as semantic fact.

### SYS-INV-04 — Unknown Past Remains Unknown
Crash/timeout/disconnect/absence cannot become guessed success, failure, non-dispatch or clearance.

### SYS-INV-05 — No Implicit Cross-Owner Atomic Mutation
No Owner directly mutates foreign canonical state or assumes one global transaction.

### SYS-INV-06 — Event Carries Fact, Not Foreign Authority
Event evidence never grants foreign mutation authority.

### SYS-INV-07 — Causality Over Wall Clock
Wall-clock arrival alone is not causal/order authority.

### SYS-INV-08 — Required Committed Facts Are Replayably Observable
Cross-owner-required facts have durable replayable propagation.

### SYS-INV-09 — Duplicate Delivery Is Safe
Duplicate transport/callback delivery cannot duplicate canonical transitions.

### SYS-INV-10 — Exact Definition Pinning
Admitted execution pins exact immutable Graph/Module/config semantics.

### SYS-INV-11 — No Direct Activation Ingress
No API/Human/External/PWP path may bypass Trigger Packet -> Delivery -> Activation.

### SYS-INV-12 — Current Attempt Is Runtime Authority
Runtime is sole Owner of current Attempt/fencing; stale Attempts cannot create new execution truth/effects.

### SYS-INV-13 — Foreign Clearance Is Owner-Specific
Runtime/Recovery/Accounting cannot fabricate foreign Effect/Resource/Capability clearance.

### SYS-INV-14 — Recovery Disposition Does Not Rewrite Subject Truth
Administrative disposition may permit scoped closure without claiming unknown subject history became known.

### SYS-INV-15 — Credential/Resource Possession Is Not Authority
Credentials/sessions/handles do not replace Capability/fencing checks.

### SYS-INV-16 — External Input Is Untrusted Until Canonicalized
Transport receipt is not internal canonical truth.

### SYS-INV-17 — Live External State Is Not Sole Workflow Truth
Provider/browser/workspace/process/worker live state cannot be the only carrier of committed workflow meaning.

### SYS-INV-18 — Product Taxonomy Is Non-Primitive
User-visible concepts do not automatically become Kernel/Runtime primitives.

### SYS-INV-19 — No Owner Placeholder At Freeze
Every first-class v0.1 canonical class has a named Owner before freeze.

### SYS-INV-20 — Clearance Is Owner-Scoped Evidence
Foreign safety clearance must originate from the conflict-bearing subject Owner and be scoped to relevant action/domain.

### SYS-INV-21 — Semantic Admission Is Replay-Stable
Mutable configuration/policy affecting execution meaning is pinned by immutable/revisioned reference or equivalent snapshot.

### SYS-INV-22 — Admission Snapshot Cannot Bypass Revocation
Pinned context does not replace dynamic Capability/fencing/Resource/Effect/budget authority validation.

### SYS-INV-23 — Ingress Owners Validate; Runtime Executes
Ingress/domain Owners validate/commit facts; Runtime owns execution admission and execution path.

### SYS-INV-24 — Generic Workflow Ingress Is Runtime Admission Truth
A pure workflow-start external trigger becomes Runtime-owned deduplicated ExecutionIngressFact; domain business facts stay domain-owned.

### SYS-INV-25 — Policy Context Owner Is Not Decision Owner By Reference Alone
PWP policy context does not transfer decision ownership to PWP.

### SYS-INV-26 — Overall v0.1 Owner Closure
The canonical state classes listed by this Overall candidate have one explicit Owner; any new pre-freeze class must be added explicitly or raise an Architecture Finding.

---

# 19. Product Extension Envelope

Future user-facing Nodes are checked against generic dimensions:
- Input;
- Output;
- Configuration;
- Capability;
- Resource;
- Effect;
- owned State;
- Event;
- Human Interaction;
- Accounting;
- Suspension/Resume;
- Composite composition.

Browser, Shell, File, HTTP, Claude/Codex/provider, Agent, Reviewer, Router, Human Approval, Loop, Condition and Merge remain product wrappers over generic architecture unless a real expressiveness gap is demonstrated.

Detailed D-006 Product Node / Visual UX is not a System Foundation freeze blocker while this envelope remains sufficient.

---

# 20. System Implementation Dependency Gates

## SYS-GATE-0 — Frozen Definition Foundations
Required:
- Frozen Module baseline + Amendment 001;
- Frozen Graph/Composite baseline.

## SYS-GATE-1 — Runtime Core
Requires D-003 frozen/accepted:
- admission;
- Packet/Delivery/Activation;
- Run/Attempt/fencing;
- suspension/resume;
- crash/replay.

## SYS-GATE-2 — Capability / Resource / Effect
Requires D-004 frozen/accepted:
- scoped grants;
- Resource/Lease;
- PREPARED EffectOperation;
- mediated boundary;
- replacement conflict clearance.

## SYS-GATE-3 — Accounting / Recovery
Requires D-005 frozen/accepted:
- hierarchical reservation;
- immutable usage facts;
- settlement/overrun;
- bounded reconciliation;
- administrative disposition vs subject clearance.

## SYS-GATE-4 — Project / Workspace Context
Requires D-010 frozen/accepted:
- Project/Workspace identity;
- immutable semantic config/policy/binding revisions;
- IngressRoute configuration;
- replay-stable admission context.

## SYS-GATE-5 — Human Interaction
Requires D-009 frozen/accepted:
- HumanRequest/HumanResponse;
- authenticated/authorized response acceptance;
- deterministic aggregation;
- Runtime wait/resume integration;
- approval evidence boundary.

## SYS-GATE-6 — Distribution / Module Ecosystem
Requires D-007 frozen/accepted:
- exact package/Module resolution;
- install/trust/enable separation;
- trust evidence;
- no latest substitution;
- historical resolution.

## SYS-GATE-7 — External Interface Safety
Requires D-008 frozen/accepted and at least one truthful enforceable IsolationProfile for any claimed restricted/hostile-code execution.

## SYS-GATE-8 — Product Node / Visual Workflow
Requires stable foundation contracts. Product work cannot invent new Kernel/Runtime semantics locally.

## SYS-GATE-9 — Integrated Fault / Replay Validation
Before production-safety claims, fault-inject crashes/duplicates/timeouts/replacements across Owner boundaries and prove:
- no lost/duplicate canonical execution;
- no stale effect authority;
- no guessed UNKNOWN;
- no double accounting;
- no duplicate Human response/quorum consumption;
- no duplicate non-repeatable workflow ingress;
- no silent exact-version substitution;
- no hidden live external state required to interpret committed history.

---

# 21. Overall Freeze Gate

Overall v0.1 may enter final adversarial review only when:

1. frozen Module + Amendment 001 + frozen Graph baseline remain consistent;
2. D-003/D-004/D-005/D-007/D-008/D-009/D-010 have valid independent review or explicit Lead accepted disposition;
3. valid blocking subsystem findings are resolved;
4. no correctness-critical canonical Owner gap remains;
5. cross-subsystem contradiction check passes;
6. safety-critical paths have stable identity, Owner, crash window, duplicate/retry behavior, UNKNOWN handling and durable propagation;
7. implementation choices such as DB/queue/worker/UI technology remain non-semantic unless explicitly frozen;
8. final integrated Claude adversarial review gate is opened by Lead and mandatory attack areas are executed.

Prepared final-review artifacts:
- `design/reviews/NYRON-D-001_Integrated_Adversarial_Review_Manifest_DRAFT.md`
- `design/coordination/tasks/NYRON-D-001-REVIEW-CLAUDE.md`

Reviewer output remains advisory. Lead owns final freeze.

---

# 22. Remaining Open Work

Current open work is review/freeze/implementation-detail closure, not canonical Owner discovery.

Pending before Overall freeze:
- bounded independent reviews and freeze consolidation for D-003/D-004/D-005/D-007/D-008/D-009/D-010;
- incorporation of valid non-blocking clarifications;
- exact constituent identity update in the integrated adversarial review Manifest;
- Claude integrated adversarial review;
- Lead disposition of any valid integrated findings.

Implementation-detail topics may remain outside frozen correctness semantics, including exact physical DB, queue technology, worker process model, UI layouts, concrete identity provider, concrete sandbox technology, detailed package marketplace UX, and detailed D-006 Product Node taxonomy.

---

# 23. Architecture Findings

No open Frozen Module or Frozen Graph/Composite Architecture Finding exists in the current consolidated Overall candidate.

`AF-PWP-001` (generic workflow-trigger canonical ingress ownership) is **RESOLVED**:
- pure workflow-start canonical ingress fact -> Runtime Orchestration;
- PWP owns route configuration;
- domain-specific external facts remain domain-owned;
- no direct Activation path exists.

Any new contradiction discovered during bounded or integrated review must be recorded explicitly and cannot be silently absorbed by reinterpretation.
