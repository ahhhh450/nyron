# Nyron Overall System Architecture v0.1

Status: DRAFT
Authority: Lead Design Authority
Scope: System foundation and first-class subsystem boundaries
Depends on: `Universal_Runtime_Module_Design_Report_v0.1.md` (FROZEN)

## 0. Purpose

This document defines the system-level architecture of Nyron above and around the frozen Module subsystem. It establishes the Kernel boundary, canonical truth model, subsystem ownership model, cross-owner interaction rules, first-class subsystem map, and implementation gates.

This document MUST NOT silently weaken or reinterpret the frozen Module baseline. Any conflict with the Module baseline must be raised as an explicit Architecture Finding.

## 1. System Architecture Principle

Nyron is divided into four conceptual layers:

1. Product Layer — user-facing nodes, workflow editing, human interaction, diagnostics, project UX, CLI/API surfaces.
2. Definition Layer — immutable executable definitions such as GraphRevision, Composite, ModuleDefinition and ModuleInstanceRevision.
3. Runtime Subsystems — scheduling, execution, capability, resource, accounting, recovery, registry and related state machines.
4. Kernel Foundation — identity, canonical durability, ownership enforcement, transaction primitives, revision/immutability rules, fencing primitives and causal history foundations.

The Kernel MUST NOT encode product taxonomy. User-facing Node is not a Kernel or Runtime primitive.

## 2. First-Class Subsystem Map

### 2.1 Definition Layer

- Graph / GraphRevision
- Composite
- Module Definition / ModuleInstanceRevision
- Package / Registry metadata

### 2.2 Kernel Foundation

- Canonical Identity
- Canonical Record persistence boundary
- Canonical Event persistence boundary
- Canonical Transaction primitive
- Revision / immutability enforcement
- Ownership enforcement
- Fencing primitive
- Causal reference / replay foundation

### 2.3 Runtime Orchestration

- Packet / Delivery
- Activation
- Run / Attempt
- scheduling / readiness
- retry / replacement / cancellation
- workflow lifecycle

### 2.4 Authority and Effects

- Capability policy and grant authority
- CapabilityGrant
- EffectOperation
- Module Host trust boundary

### 2.5 Resource

- Resource Manager
- Resource
- ResourceLease
- affinity / lifecycle

### 2.6 Accounting and Recovery

- AccountingScope
- BudgetReservation
- usage / quota / cost facts
- ReconciliationCase
- recovery / escalation

### 2.7 External World Boundary

- filesystem / workspace
- process execution
- network
- browser
- model/provider/tool integrations
- external event ingress

### 2.8 Product Layer

- user-facing Node abstraction
- visual graph editor
- Composite presentation
- Human Interaction / Approval
- diagnostics / reasons
- project/workspace UX
- CLI / public API

## 3. Kernel Boundary

The Kernel owns foundational correctness primitives, not subsystem business state machines.

The Kernel MUST provide or enforce:

- stable canonical identities;
- durable canonical records;
- durable canonical event recording;
- atomic transaction primitives within an authoritative owner boundary;
- revision and immutability semantics;
- ownership enforcement;
- fencing primitives;
- causal references and replay foundations.

The Kernel MUST NOT own:

- Graph scheduling semantics;
- Run lifecycle policy;
- retry policy;
- Resource lifecycle policy;
- Accounting settlement policy;
- provider selection;
- Node taxonomy;
- product roles such as Developer, Reviewer, Agent, Router or Human Approval.

Subsystem-specific state machines remain owned by their subsystem.

## 4. Canonical Truth

Canonical Truth is any durable fact Nyron must continue to recognize after crash, restart, retry, replay or worker replacement.

A fact is not canonical merely because it exists in memory, a worker queue, a provider session, a UI cache, a private module file or another transient implementation detail.

If re-deriving a piece of state could change the interpretation of committed history, that state or the facts required to reconstruct it must be canonical.

Nyron uses both:

- Canonical State — authoritative current durable state;
- Canonical History — durable evidence describing committed state transitions and facts.

Canonical State answers "what is true now". Canonical History answers "what committed facts caused the system to become this way".

## 5. Canonical Owner Model

Every class of canonical state must have exactly one authoritative subsystem owner.

Examples:

| Canonical state class | Authoritative owner |
| --- | --- |
| GraphRevision | Graph subsystem |
| Delivery / Activation / Run | Runtime subsystem |
| CapabilityGrant | Capability Authority |
| Resource / ResourceLease | Resource Manager |
| BudgetReservation / accounting facts | Accounting subsystem |
| ReconciliationCase | Recovery subsystem |

Other subsystems may Query, Command, send Proposal, or consume Event evidence, but MUST NOT directly mutate foreign canonical state.

## 6. Cross-Owner Interaction

The canonical cross-owner interaction vocabulary is:

- Query — request information without mutation authority.
- Command — request that the target Owner attempt a state transition. A Command does not prove success.
- Event — durable evidence that a canonical fact has already committed.
- Proposal — non-authoritative suggestion asking an Owner to consider a transition or choice.

An Event produced by Owner A can be evidence for Owner B, but it does not grant Owner A mutation authority over Owner B.

## 7. Transaction Boundary

Nyron defines one logical canonical authority model, but does not require one physical database.

Within one Owner boundary, invariants that require atomicity MUST be committed in one owner-local canonical transaction. Example: consumptive Delivery binding and Activation creation belong to Runtime and must remain atomic as required by the frozen Module baseline.

Across Owner boundaries, Nyron MUST NOT assume a shared global database transaction. Cross-owner convergence uses durable facts, commands, idempotent handling and reconciliation.

Temporary cross-owner partial convergence is valid when each committed transition is correct and a deterministic convergence/recovery path exists.

## 8. Canonical Event Semantics

Nyron distinguishes:

1. Canonical Event — committed durable system fact.
2. External Event — input originating outside Nyron and not automatically trusted as canonical internal truth.
3. Runtime Notification — transient wake-up or scheduling hint; correctness must not depend on its delivery.
4. Telemetry — logs, traces and metrics; not canonical authority by default.

A committed canonical fact that must be observed by another Owner MUST have a durable replayable propagation record established atomically with the committing Owner's state transition or through an equivalent correctness mechanism.

Transport-level exactly-once delivery is not required. Consumers MUST tolerate duplicate delivery through stable identity, deduplication and idempotent canonical handling.

## 9. Causality and Ordering

Wall-clock arrival time is not sufficient correctness authority.

Canonical replay and dependency semantics must rely on committed identities, deterministic owner-local ordering where required, and explicit causal references.

A cross-owner event may record `caused_by` / source event identity so that downstream committed facts can be traced without requiring one global monotonically increasing database sequence.

Physical storage may use one event store or multiple owner-local event streams as long as stable identity, owner attribution, durable ordering requirements, causal references and replayability are preserved.

## 10. Canonical vs Derived State

Canonical state is authoritative durable truth.

Derived state is deterministic projection or cache built from canonical facts. Examples may include:

- ready scheduling candidates;
- pending delivery counts;
- dependency manifests;
- workflow progress percentages;
- missing-module diagnostics;
- indexes and caches.

Derived state may be deleted and rebuilt. It MUST NOT become the only authority for correctness.

## 11. Kernel Primitive Classification

The Kernel should understand only generic correctness primitives:

- Canonical Identity
- Canonical Record
- Canonical Event
- Canonical Transaction
- Revision / immutable reference
- Owner identity / authority boundary
- Fencing token / fencing validation primitive
- Causal reference

The following are NOT generic Kernel primitives; they are subsystem canonical objects:

- GraphRevision
- Packet
- Delivery
- Activation
- Run
- CapabilityGrant
- Resource / ResourceLease
- EffectOperation
- AccountingScope / BudgetReservation
- ReconciliationCase
- Continuation / Subscription

The Kernel provides correctness machinery for these objects without owning their domain state machines.

## 12. System Architecture Invariants — Candidate Set

### SYS-INV-01 — Single Canonical Owner
Every canonical state class has exactly one authoritative Owner.

### SYS-INV-02 — Derived State Is Not Authority
Derived state must never become the sole source of correctness when canonical facts can reconstruct it.

### SYS-INV-03 — History Independent of Transient Scheduling
Canonical history must not depend on transient worker scheduling or wake-up order unless that ordering itself became a committed canonical fact.

### SYS-INV-04 — Unknown Past Remains Unknown
Unknown historical facts must never be converted into guessed success, failure, ownership or external-effect outcomes.

### SYS-INV-05 — No Implicit Cross-Owner Atomic Mutation
An Owner must not directly mutate foreign canonical state inside its own canonical transaction. Cross-owner global atomicity is not assumed.

### SYS-INV-06 — Event Carries Fact, Not Foreign Authority
An Event may provide evidence to another Owner but never grants mutation authority over that Owner's canonical state.

### SYS-INV-07 — Causality Over Wall Clock
Canonical dependency and replay semantics must not rely on wall-clock arrival time alone.

### SYS-INV-08 — Committed Facts Are Reliably Observable
A committed canonical fact required by another Owner must have durable replayable propagation and must not be permanently lost after local commit.

### SYS-INV-09 — Duplicate Delivery Is Safe
Cross-owner transport may duplicate messages; canonical consumers must use stable identity and idempotent handling so duplicates cannot create duplicate canonical transitions.

## 13. Product Extension Envelope

The Product Layer may introduce arbitrary user-facing Node concepts without adding new Kernel primitives.

When designing a future user-facing Node, architecture review should check whether it may require any of the following generic extension dimensions:

- Input
- Output
- Configuration
- Capability
- Resource
- State
- Event
- Human Interaction
- Accounting
- Suspension / Resume
- Composite composition

Not every Node uses every dimension. The purpose is to preserve extensibility without hard-coding product Node taxonomies into Kernel or Runtime.

## 14. Relationship to Frozen Module Baseline

This system architecture adopts and preserves the Module baseline rules including:

- Node is not a Runtime primitive; Module is.
- ModuleDefinition semantics are immutable by version.
- Module execution follows Packet → Delivery → Activation → Run.
- Module does not own readiness, Activation creation, downstream scheduling or canonical workflow truth.
- Capability, Resource and Packet remain separate concepts.
- stale attempts cannot canonical-commit or initiate new mediated effects.
- Suspension uses explicit durable Continuation.
- unknown past external effects flow to Reconciliation / Escalation rather than guessed truth.

No system-level rule in this draft supersedes Module invariants M-INV-01 through M-INV-18.

## 15. Open Design Work Before Freeze

The following topics remain open and must be completed or explicitly deferred before this document can become FROZEN:

1. Graph / Composite ownership and immutable definition publication contract.
2. Runtime orchestration ownership boundaries and workflow execution lifecycle.
3. Capability Authority and policy ownership.
4. Resource Manager lifecycle and cross-owner interaction contract.
5. Accounting / Recovery integration boundaries.
6. global identity/reference/revision format requirements versus implementation-local details.
7. external event ingress canonicalization boundary.
8. workspace/project boundary.
9. implementation gates and dependency ordering among design documents.

## 16. Current Design Gate

Status remains DRAFT.

The next design task is to complete enough of the first-class subsystem ownership map and global contract boundaries to produce an independently reviewable System Foundation candidate baseline. The frozen Module baseline remains authoritative throughout this work.