# Nyron Overall System Architecture v0.1

**Status:** **DRAFT — INTEGRATED SYSTEM ARCHITECTURE CANDIDATE**
**Authority:** Nyron Lead Design Authority
**Scope:** System foundation, subsystem ownership, cross-owner correctness, and implementation dependency map

Depends on:
- `design/Universal_Runtime_Module_Design_Report_v0.1.md` — **FROZEN MODULE ARCHITECTURE BASELINE**
- `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md` — **FROZEN MODULE ARCHITECTURE AMENDMENT**
- `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md` — **FROZEN GRAPH / COMPOSITE ARCHITECTURE BASELINE**

Lead-integrated, independent-review-pending subsystem candidates:
- `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`
- `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`
- `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`
- `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`

This document MUST NOT silently weaken any frozen baseline. Any semantic conflict with a frozen baseline requires an explicit Architecture Finding and, if accepted, an Amendment or superseding baseline.

## 0. Purpose

This document defines Nyron's system architecture above and around the frozen Module and Graph/Composite baselines.

It establishes:
- conceptual system layers;
- first-class subsystem boundaries;
- Kernel Foundation scope;
- canonical truth and Owner model;
- cross-owner interaction and transaction rules;
- Runtime execution ownership;
- Capability / Resource / Effect separation;
- Accounting / Recovery separation;
- External World mediation boundary;
- Product Layer extension envelope;
- system invariants;
- implementation dependency gates.

The central architecture rule is:

> Nyron is a system of explicitly owned canonical facts coordinated through durable mediated contracts. Product concepts do not become Kernel primitives merely because users can see them.

---

# 1. Four-Layer Architecture

Nyron is divided into four conceptual layers.

## 1.1 Product Layer

User-facing concepts and interaction surfaces:
- visual Node presentation;
- graph/workflow editor;
- Composite presentation;
- Human Interaction / Approval UX;
- project/workspace UX;
- diagnostics/reasons;
- CLI / public API;
- product roles such as Developer, Reviewer, Agent, Router.

Product labels are not Runtime or Kernel primitive taxonomy.

## 1.2 Definition Layer

Immutable or authoring-time executable definitions:
- Graph / GraphDraft / GraphRevision;
- Composite / CompositeRevision;
- ModuleDefinition / ModuleInstanceRevision;
- concrete Ports and Edges;
- immutable config/schema references;
- package/registry metadata.

Graph describes **what the executable definition is**. Runtime decides **when execution occurs**.

## 1.3 Runtime Subsystems

Canonical domain state machines that execute or govern execution:
- Runtime Orchestration;
- Capability Authority;
- Resource Manager;
- Effect Authority;
- Accounting Owner;
- Recovery Owner;
- Module Registry and related subsystem authorities;
- future Human Interaction and Workspace/Project Owners.

## 1.4 Kernel Foundation

Generic correctness machinery only:
- canonical identity;
- durable canonical records;
- durable canonical events;
- owner-local transaction primitives;
- revision / immutable-reference enforcement;
- Owner boundary enforcement;
- fencing primitives;
- causal references;
- replay foundations.

Kernel Foundation MUST NOT own product taxonomy or subsystem business state machines.

---

# 2. First-Class Subsystem Map

## 2.1 Graph / Definition Subsystem

Owns executable definition truth:
- GraphRevision;
- ModuleInstanceRevision placement;
- concrete Port contracts;
- Edge topology;
- CompositeRevision and materialized Composite placement provenance;
- definition publication/archive governance facts.

Frozen baseline:
- `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md`

## 2.2 Runtime Orchestration

Owns execution truth:
- WorkflowExecution / admission;
- Packet;
- Delivery;
- Activation;
- Run / RunAttempt;
- current-Attempt authority and fencing generation;
- retry/replacement/cancellation decisions;
- Continuation / Subscription / EventDelivery resume-consumption facts;
- workflow convergence/terminal state.

Runtime does NOT own CapabilityGrant, Resource/ResourceLease, EffectOperation, BudgetReservation or ReconciliationCase.

## 2.3 Capability Authority

Owns:
- CapabilityType authority vocabulary/registry semantics;
- CapabilityGrant;
- scoped grant issuance/revocation/expiry;
- policy evaluation for authority.

Capability answers:

> What operation is this Attempt allowed to request?

Capability is not Resource, Packet, Budget or external-effect history.

## 2.4 Resource Manager

Owns:
- Resource;
- ResourceLease;
- compatibility;
- affinity;
- lifecycle / hydration / loss / revoke / expiry semantics.

Resource answers:

> Which managed stateful handle exists and may be leased?

Resource existence never grants operation authority.

## 2.5 Effect Authority

Owns `EffectOperation` domain lifecycle.

EffectOperation is Kernel-visible canonical state but is not a generic Kernel primitive/state machine.

Frozen Amendment 001 adds `PREPARED` durable intent before crash-ambiguous external dispatch.

Effect Authority answers:

> What external operation may actually have been dispatched, remain active, have completed, been fenced, or become UNKNOWN?

## 2.6 Accounting Owner

Owns:
- AccountingScope accounting metadata/policy context;
- BudgetPolicyRevision;
- BudgetReservation;
- UsageFact / UsageAdjustmentFact;
- canonical settlement and overrun facts;
- owner-local hard-limit enforcement state.

Accounting answers:

> Was estimated consumption authorized/reserved, and what actual usage/cost has been canonically recorded and settled?

## 2.7 Recovery Owner

Owns:
- ReconciliationCase;
- recovery evidence references;
- bounded retry/backoff/deadline schedule;
- escalation;
- Recovery disposition.

Recovery does NOT own the subject object's business truth.

## 2.8 External Interface / Workspace Boundary

Provides mediated adapters and trust boundaries for:
- filesystem/workspace;
- process;
- network;
- browser;
- model/provider/tool;
- remote worker/job;
- external event ingress.

It consumes generic Capability / Resource / Effect mechanisms and does not become their canonical Owner.

## 2.9 Human Interaction — Required Future Owner

Human Request / authenticated Human Response truth must belong to a designated Human Interaction Owner.

Capability Authority may require approval evidence, but does not own the human response itself.

Exact Human Interaction subsystem design remains pending.

## 2.10 Workspace / Project Configuration — Required Future Owner

A stable `workspace_ref` may be consumed by Capability scope, Resource compatibility and External Interface adapters.

D-008 does NOT claim canonical ownership of Workspace identity metadata.

A future Workspace/Project configuration Owner must own durable workspace/project identity and binding metadata.

---

# 3. Kernel Boundary

Kernel Foundation provides correctness primitives, not semantic domain policy.

Kernel MUST provide/enforce:
- stable canonical identities;
- durable records/events;
- owner-local atomic transactions;
- immutable references and revision rules;
- owner write enforcement;
- fencing-token primitives;
- causal references;
- replay/deduplication foundations.

Kernel MUST NOT directly own:
- Graph scheduling;
- Run/Attempt retry policy;
- Capability policy semantics;
- Resource lifecycle policy;
- EffectOperation domain lifecycle;
- Accounting settlement;
- Recovery retry policy;
- provider/browser/process taxonomy;
- product Node taxonomy;
- Human Approval UX.

Subsystem-specific state machines remain subsystem-owned.

---

# 4. Canonical Truth

Canonical Truth is any fact Nyron must continue to interpret correctly after crash, restart, retry, replacement, replay or worker loss.

Nyron uses both:
- **Canonical State** — what is authoritative now;
- **Canonical History** — what committed facts caused the current interpretation.

A fact is not canonical merely because it exists in RAM, a queue, a provider session, an adapter-local cache, a UI cache, a worker process or a private module file.

If losing or recomputing a fact could change the interpretation of committed history, the required fact/evidence must be canonical.

Unknown historical facts remain UNKNOWN until evidence or an explicit policy disposition addresses the appropriate scope. Policy disposition must never be misrepresented as evidence that an unknown past fact became known.

---

# 5. Canonical Owner Model

Every canonical state class has exactly one authoritative Owner.

| Canonical state class | Authoritative Owner |
| --- | --- |
| GraphRevision / definition topology | Graph subsystem |
| ModuleDefinition | Module Registry domain |
| Packet / Delivery / Activation | Runtime Orchestration |
| Run / RunAttempt / current Attempt | Runtime Orchestration |
| Continuation / Subscription / EventDelivery consumption | Runtime Orchestration |
| CapabilityGrant | Capability Authority |
| Resource / ResourceLease | Resource Manager |
| EffectOperation | Effect Authority |
| AccountingScope accounting metadata / BudgetPolicyRevision | Accounting Owner |
| BudgetReservation / UsageFact / settlement | Accounting Owner |
| ReconciliationCase / Recovery disposition | Recovery Owner |
| Human Request / authenticated Human Response | Human Interaction Owner — future design |
| Workspace/Project identity & binding metadata | Workspace/Project Owner — future design |

References do not transfer ownership.

Examples:
- GraphRevision may pin `static_accounting_scope_ref` but cannot mutate Accounting state.
- Capability scope may reference `workspace_ref` but Capability Authority does not thereby own workspace identity.
- EffectOperation may reference BudgetReservation, ResourceLease and CapabilityGrant without owning them.

---

# 6. Cross-Owner Interaction Vocabulary

Canonical cross-owner interaction is limited to:

- **Query** — inspect without mutation authority.
- **Command** — request target Owner to attempt a transition; not proof of success.
- **Event** — durable evidence that a canonical fact already committed.
- **Proposal** — non-authoritative suggestion/request for consideration.

An Event from Owner A may become evidence for Owner B, but does not grant A authority to mutate B.

A CapabilityGrant authorizes a mediated request; it does not bypass the target Owner's final mutation decision.

---

# 7. Transaction Boundary

Nyron defines one logical canonical authority model but does not require one physical database.

## 7.1 Owner-local atomicity

Within one Owner, invariants requiring atomicity MUST use one owner-local canonical transaction or equivalent correctness mechanism.

Examples:
- Runtime consumptive Delivery binding + Activation creation;
- Attempt replacement + current-attempt pointer/fencing update;
- Accounting reservation across the full applicable ancestor chain.

## 7.2 Cross-owner convergence

Across Owners, Nyron MUST NOT assume one global transaction.

Cross-owner convergence uses:
- durable Commands/Events;
- stable identities;
- idempotency/deduplication;
- durable replayable propagation;
- explicit reconciliation.

Temporary cross-owner partial convergence is acceptable only when every committed local transition is correct and there is a deterministic bounded convergence/recovery path.

---

# 8. Canonical Event, External Event, Notification and Telemetry

Nyron distinguishes:

1. **Canonical Event** — durable committed system fact.
2. **External Event** — outside input, initially untrusted as internal truth.
3. **Runtime Notification** — transient wake-up/scheduling hint; correctness must not depend on it.
4. **Telemetry** — log/trace/metric, non-canonical by default.

A committed fact required by another Owner must have durable replayable propagation established atomically with the source transition or through an equivalent correctness mechanism.

Transport exactly-once is not required. Canonical consumers must tolerate duplicate delivery.

External ingress becomes internal canonical truth only after the authoritative ingress/target Owner authenticates, validates, canonicalizes, binds stable identity and commits the fact.

---

# 9. Causality and Ordering

Wall-clock arrival time alone is never correctness authority.

Correct replay/order relies on:
- stable canonical identities;
- deterministic owner-local ordering where required;
- explicit causal references;
- immutable Graph definition ordinals where execution ordering needs them.

For Runtime Delivery projection, semantic ordering is derived from committed Packet sequence plus frozen Graph ordinals/Port ordinals, never DB row order, UI coordinates, projector scan order, worker pickup order or hash iteration.

Concurrent owner-local commits may establish a canonical historical order. Replay preserves the committed history rather than pretending all physical interleavings are identical.

---

# 10. Canonical vs Derived State

Derived state is reconstructible projection/cache and is never sole correctness authority.

Examples:
- ready queues;
- pending Delivery counts;
- scheduler candidates;
- dependency manifests;
- validation diagnostics;
- workflow progress percentages;
- Composite progress;
- accounting dashboards/rollups;
- indexes/materialized views;
- UI layout/search caches.

A persisted optimization may become canonical enforcement state only when its owner-local correctness semantics are explicitly defined and it no longer depends on best-effort reconstruction.

---

# 11. Definition and Execution Boundary

Frozen Graph/Composite rules apply system-wide:

- Graph is logical identity; GraphRevision is immutable execution definition.
- Runtime pins exact GraphRevision and exact immutable Module/config references.
- Runtime never resolves `latest/current` definitions for an existing execution.
- Composite is Definition-layer only and is materialized before execution.
- persisted GraphRevision leaf ModuleInstanceRevision/Port/Edge topology is execution authority.
- Runtime never re-flattens Composite for correctness.
- FEEDBACK is only an intentional-cycle Edge role and changes no Runtime execution semantics.
- Loop/Branch/Join are not hidden Runtime/Kernel primitives.
- unresolved/broken definitions may be preserved but cannot enter execution admission.

---

# 12. Runtime Orchestration Boundary

Lead-integrated Runtime semantics are:

## 12.1 Single execution path

```text
Packet -> Delivery -> Activation -> Run / Attempt
```

There is no second direct-Activation execution path.

## 12.2 Top-level execution ingress

Workflow start, API invocation, external trigger, human trigger, timer or other top-level execution source MUST be converted into a Runtime-owned Trigger Packet and ordinary Delivery/Activation path against an immutable GraphRevision ingress binding.

Forbidden:

```text
External/Product/API intent -> direct Activation
```

The exact Graph Input/Ingress schema may be refined by its owning definition/interface design, but the execution-path invariant is fixed.

## 12.3 Attempt identity

Each Activation has one Run lineage.

Retry and replacement create a new Attempt under the same Run.

Resume remains within the same current Attempt.

Exactly one Attempt is current for a Run at a time.

## 12.4 Current-attempt fencing

Replacement/cancellation atomically removes the old Attempt's future canonical-commit, resume and new-effect authority.

Already-dispatched external effects do not disappear merely because an Attempt became stale.

## 12.5 Terminal state

Workflow completion/failure/cancellation is a canonical quiescence/directive result, not queue emptiness or worker inactivity.

Suspended current Attempts with live Subscriptions remain nonterminal.

---

# 13. Capability / Resource / Effect Authority Boundary

The following are orthogonal:

```text
CapabilityGrant != Resource/ResourceLease != EffectOperation
```

## 13.1 Capability

Capability = permission to request an operation within bounded machine-checkable scope.

Grant is Attempt-bound, fenced, revocable, non-transferable and revalidated at the actual mediated boundary.

## 13.2 Resource

Resource = managed opaque stateful handle.

ResourceLease = bounded temporary use authority for that handle.

Resource continuity must never become the only carrier of workflow semantic truth.

## 13.3 EffectOperation

EffectOperation = durable tracking of externally consequential/crash-ambiguous operation history.

Frozen Amendment 001 requires durable PREPARED identity before crash-ambiguous dispatch.

PREPARED does not prove dispatch occurred.

Timeout, disconnect or absence of response does not prove failure/non-dispatch.

## 13.4 Attempt replacement

When R2 replaces R1:
- R1 immediately loses future commit/new-effect authority;
- existing R1 effects require explicit completion/fencing/UNKNOWN handling;
- conflicting new external authority waits for authoritative effect/resource/capability clearance;
- non-conflicting work may proceed when policy/scope prove separation.

---

# 14. Accounting / Recovery Boundary

The following remain orthogonal:

```text
EffectOperation != BudgetReservation
ResourceLease != BudgetReservation
CapabilityGrant != Budget authority
```

## 14.1 Static accounting membership

Module execution accounting affiliation is pinned from immutable static Graph/Composite containment through `static_accounting_scope_ref`.

Dynamic Packet provenance, triggering Edge, worker or Attempt does not change membership.

Graph stores the reference; Accounting Owner owns accounting metadata/policies/settlement truth.

## 14.2 Reservation

A successful hierarchical reservation must atomically reserve every applicable hard-limit ancestor inside one logical Accounting Owner transaction domain.

Actual usage is never capped or rewritten to fit the estimate/limit.

## 14.3 UNKNOWN

UNKNOWN is not zero, failure, non-dispatch or release.

Recovery coordinates bounded investigation and evidence handling.

## 14.4 Reconciliation closure vs clearance

`ReconciliationCase.RESOLVED` is not a universal clearance token.

Recovery may issue a scope-specific policy disposition that permits **Runtime administrative closure** while a foreign subject remains UNKNOWN.

That disposition does NOT clear conflicting new Effect/Resource/Capability authority.

Only the authoritative subject Owner can clear its own conflict/safety state.

---

# 15. External World Boundary

External systems are accessed through mediated adapters/brokers mapped onto Capability / Resource / Effect mechanisms.

Browser, Shell, File, HTTP, Provider, Tool, Remote Worker and External Event are not Kernel primitives.

## 15.1 Workspace

`workspace_ref` is logical identity, not raw path/mount/Resource.

Live Workspace Handle may be Resource.

Path access must enforce resolved containment including symlink/junction/mount/TOCTOU considerations according to the declared IsolationProfile.

D-008 does not own workspace identity metadata; future Workspace/Project Owner must be explicit.

## 15.2 Process

Process start is consequential EffectOperation.

A containment claim must control relevant descendants, not only parent PID.

Kill request is not FENCED evidence.

## 15.3 Network

Destination scope is revalidated against effective DNS resolution/redirect destination according to policy.

Raw unrestricted sockets are forbidden in profiles claiming mediation.

## 15.4 Browser / Provider / Remote Worker

Stateful sessions may be Resources.

Consequential actions are EffectOperations.

Streaming does not replace Continuation.

Timeout/cancellation is not proof of external terminal state.

## 15.5 Credentials

Credential possession is not authority.

Preferred model keeps long-lived credentials inside trusted adapter/broker boundaries and stores durable references, not secret values, in canonical history.

## 15.6 External ingress

External ingress must:
- authenticate/validate/canonicalize/dedupe;
- identify the authoritative canonical target Owner;
- then, if it starts workflow execution, enter Runtime via Trigger Packet -> Delivery -> Activation.

Ingress adapter never creates Activation directly.

---

# 16. Module Host / Adapter Trust Boundary

Module Host and external adapters may be Trusted Computing Base components for the authority they enforce, but they do not own durable semantic truth merely because they mediate it.

Restricted Module code must not receive bypass routes such as:
- raw canonical DB/StateStore;
- unrestricted filesystem;
- unrestricted subprocess;
- unrestricted sockets;
- raw provider/browser/worker handles that bypass mediation;
- hidden durable semantic state.

Isolation must be described by explicit testable `IsolationProfile` claims rather than a vague `sandboxed=true` flag.

Trusted builtin mode may exist, but must not be advertised as hostile third-party isolation.

---

# 17. Kernel Primitive Classification

Generic Kernel primitives:
- Canonical Identity;
- Canonical Record;
- Canonical Event;
- Canonical Transaction;
- Revision / immutable reference;
- Owner identity / enforcement boundary;
- Fencing token / fencing validation primitive;
- Causal reference / replay support.

NOT generic Kernel primitives:
- GraphRevision;
- Packet / Delivery / Activation;
- Run / Attempt;
- Continuation / Subscription;
- CapabilityGrant;
- Resource / ResourceLease;
- EffectOperation;
- AccountingScope / BudgetReservation;
- ReconciliationCase;
- Workspace Handle;
- Browser / Shell / HTTP / Provider / Agent / Human Approval / Router / Reviewer Nodes.

Kernel provides correctness machinery for these domain objects but does not own their business state machines.

---

# 18. System Architecture Invariants

### SYS-INV-01 — Single Canonical Owner
Every canonical state class has exactly one authoritative Owner.

### SYS-INV-02 — Derived State Is Not Authority
Rebuildable projection/cache state cannot become sole correctness authority.

### SYS-INV-03 — History Independent of Transient Scheduling
Canonical history cannot depend on worker/queue/wake-up order unless that order itself became a committed semantic fact.

### SYS-INV-04 — Unknown Past Remains Unknown
Crash, timeout, disconnect or missing response cannot be converted into guessed historical truth.

### SYS-INV-05 — No Implicit Cross-Owner Atomic Mutation
Owners do not directly mutate foreign canonical state or assume one global cross-owner transaction.

### SYS-INV-06 — Event Carries Fact, Not Foreign Authority
Events provide committed evidence, not foreign mutation authority.

### SYS-INV-07 — Causality Over Wall Clock
Wall-clock arrival alone is not canonical causal/order authority.

### SYS-INV-08 — Committed Facts Are Reliably Observable
Cross-owner-required committed facts have durable replayable propagation.

### SYS-INV-09 — Duplicate Delivery Is Safe
Cross-owner transport and external callbacks may duplicate; canonical processing is idempotent/deduplicated.

### SYS-INV-10 — Exact Definition Pinning
Execution pins immutable GraphRevision / Module/config definition facts and never resolves mutable latest/current semantics.

### SYS-INV-11 — No Direct Activation Ingress
All workflow execution starts/resumes through the frozen Runtime path; top-level ingress cannot bypass Packet/Delivery by creating Activation directly.

### SYS-INV-12 — Current Attempt Is Runtime Authority
Runtime is the sole Owner of current Attempt identity/fencing; stale Attempts cannot create new canonical execution truth or mediated effects.

### SYS-INV-13 — Foreign Clearance Is Owner-Specific
Runtime/Recovery cannot fabricate Effect/Resource/Capability clearance from local termination or case status.

### SYS-INV-14 — Recovery Disposition Does Not Rewrite Subject Truth
Administrative policy disposition may permit scoped closure while subject remains UNKNOWN, but cannot be represented as evidence that the unknown became known.

### SYS-INV-15 — Credential / Resource Possession Is Not Authority
Possessing credentials, sessions, handles or Resources does not replace Capability/fencing validation.

### SYS-INV-16 — External Ingress Is Untrusted Until Canonicalized
Transport reception is never internal canonical truth until authoritative validation/canonicalization/commit.

### SYS-INV-17 — Live External State Is Not Sole Workflow Truth
Provider/browser/workspace/process/remote sessions may aid continuity but cannot be the only source needed to interpret committed workflow history.

### SYS-INV-18 — Product Taxonomy Is Non-Primitive
User-facing Node concepts cannot change Kernel/Runtime primitive taxonomy.

---

# 19. Product Extension Envelope

For every future user-facing Node, architecture review checks the generic dimensions:
- Input;
- Output;
- Configuration;
- Capability;
- Resource;
- external Effect;
- owned State;
- Event;
- Human Interaction;
- Accounting;
- Suspension/Resume;
- Composite composition.

A Node uses only the dimensions it needs.

Examples such as Claude, Codex, Browser, Shell, File, HTTP, Tool, Agent, Reviewer, Human Approval, Router, Loop, Condition and Merge remain product wrappers over generic Module/Graph/authority mechanisms.

---

# 20. Implementation Dependency Gates

These are system-level gates; subsystem baselines may define finer gates.

## SYS-GATE-0 — Frozen Definition Foundations
Required:
- Frozen Module baseline + amendments;
- Frozen Graph/Composite baseline.

No implementation may reinterpret these semantics.

## SYS-GATE-1 — Runtime Core
Requires D-003 frozen/reviewed enough to implement:
- execution admission;
- Packet/Delivery/Activation;
- Run/Attempt;
- fencing;
- suspension/resume;
- crash/replay.

## SYS-GATE-2 — Capability / Resource / Effect Foundation
Requires D-004 frozen/reviewed enough to implement:
- scoped CapabilityGrant;
- Resource/ResourceLease;
- PREPARED EffectOperation;
- mediated effect boundary;
- replacement conflict clearance.

## SYS-GATE-3 — Accounting / Recovery
Requires D-005 frozen/reviewed enough to implement:
- hierarchical reservation;
- immutable usage facts;
- settlement/overrun;
- bounded ReconciliationCase;
- Recovery disposition semantics.

## SYS-GATE-4 — External Interface Safety
Requires D-008 frozen/reviewed enough to implement selected adapters and one truthful IsolationProfile.

Hostile third-party Module support cannot be claimed before enforceable isolation exists.

## SYS-GATE-5 — Product Node / Visual Workflow
Requires stable Graph/Runtime/authority contracts.

Product Node work may package generic primitives but may not invent new Runtime/Kernel semantics locally.

## SYS-GATE-6 — Distribution / Module Ecosystem
Requires exact dependency/import semantics from frozen Graph baseline plus Module Registry/trust/distribution design.

## SYS-GATE-7 — Integrated Fault / Replay Validation
Before production-safety claims, inject crashes/retries/duplicates/timeouts across owner boundaries and prove:
- no lost/duplicate canonical execution;
- no stale effect authority;
- no guessed UNKNOWN history;
- no double budget accounting;
- no hidden external state required to interpret committed history.

---

# 21. Current Open Work Before Overall Freeze

The following remain open or review-pending:

1. Independent DeepSeek consistency reviews for D-003, D-004, D-005 and D-008.
2. Apply only valid review clarifications and freeze those subsystem baselines.
3. Select canonical Owner for Workspace/Project identity/configuration metadata.
4. Freeze Human Interaction canonical Owner/boundary sufficiently for Human Request/Response evidence.
5. Decide whether D-006 Product Node / Visual UX must be designed before Overall Architecture freeze or can remain post-foundation product work.
6. Decide whether D-007 Distribution / Module Ecosystem must be completed before Overall Architecture freeze.
7. Global Schema/Value compatibility contract remains open; frozen Graph baseline uses exact-compatible-only safe interim behavior.
8. Global reference/identity encoding format remains an implementation/spec detail unless cross-system portability requires further architecture constraints.
9. External ingress route registry/config Owner remains to be assigned.
10. After subsystem integration, run Claude Independent Adversarial Architecture Review against the complete integrated architecture.

---

# 22. Current Architecture Finding Status

No unresolved blocking Architecture Finding is open at the time of this integrated draft.

The prior EffectOperation PREPARED conflict was resolved explicitly through Frozen Module Amendment 001.

Any new independent review finding that requires semantic change to a frozen baseline must reopen only through explicit Amendment/superseding baseline control.
