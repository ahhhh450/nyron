# Nyron Design

## 1. Purpose

This directory is the authoritative home for all pre-implementation design of Nyron.

Design documents define architecture, contracts, invariants, subsystem boundaries, dependency relationships, implementation gates, acceptance criteria, and architecture findings before code is allowed to establish those semantics implicitly.

The design layer is intentionally separated from implementation. Implementation may choose local technical details only where they do not change frozen observable semantics.

## 2. Design Authority

Nyron uses a single Lead Design Authority for system-level consistency.

The Lead Design Authority is responsible for:

- maintaining the overall architecture and subsystem map;
- deciding what must be designed before implementation;
- deciding when a topic belongs in the main design thread or a dedicated design thread;
- defining and freezing contracts, invariants, ownership, state boundaries, and cross-subsystem dependencies;
- reviewing delegated design results before they become baseline;
- preventing local subsystem designs from silently changing global semantics;
- opening an Architecture Finding when implementation discovers a required semantic change;
- maintaining this design index and the current design status.

The Lead Design Authority does **not** own implementation, coding style, framework choice, internal helpers, database indexes, or other local implementation details unless those choices affect architecture or observable contract semantics.

## 3. Design Baseline Rules

1. A design marked **FROZEN** is an implementation contract, not a suggestion.
2. Implementation MUST NOT silently change a frozen Architecture Invariant, ownership rule, state model, authority boundary, failure semantic, or durable-history semantic.
3. If implementation cannot satisfy a frozen design, it MUST stop at that boundary and raise an **Architecture Finding**.
4. A later design document may refine an earlier document but MUST explicitly identify any changed contract or invariant.
5. Cross-document conflicts are resolved by explicit design review; implementation order or code existence does not determine architectural authority.
6. Historical implementation is evidence for migration, not authority over a Greenfield contract.
7. User-facing product concepts do not automatically become Runtime primitives.
8. Unknown past facts are never converted into convenient guessed truth.

## 4. Current Frozen Baseline

### Module Subsystem

- Document: `Universal_Runtime_Module_Design_Report_v0.1.md`
- Status: **FROZEN MODULE ARCHITECTURE BASELINE**
- Frozen scope: Module subsystem contract for **Phase 1–7**
- Initial implementation gate: **Phase 1–2**
- Re-open condition: an Architecture Finding requiring a change to the frozen contract or invariants

The Module baseline defines, among other things:

- ModuleDefinition / ModuleInstanceRevision
- Packet / Delivery / Activation / Run
- Module execution ABI
- Suspension / Continuation / Resume
- Capability and Resource separation
- Commit Fencing / Effect Fencing
- EffectOperation
- Resource Lease lifecycle
- AccountingScope / BudgetReservation
- ReconciliationCase
- Module Host trust boundary
- unresolved Module dependency handling
- Module Architecture Invariants M-INV-01 through M-INV-18

## 5. Planned Design Domains

The following domains require system-level design before Nyron can be considered implementation-ready as a complete product. Their order may change when dependencies become clearer.

### A. System Foundation

- System Architecture / Kernel boundary
- Canonical State and durable event model
- identity / reference / revision model
- global ownership and authority rules
- deterministic history and replay boundary

### B. Graph and Workflow Definition

- GraphRevision
- Edge / Port topology
- Composite
- dependency manifest / package dependency rules
- import / export / workflow sharing semantics
- loops, branching, joins, and convergence semantics

### C. Runtime Orchestration

- scheduling and readiness
- retry / replacement / cancellation
- workflow lifecycle and terminal states
- concurrency and conflict rules
- execution fairness / priority where semantically relevant

### D. Authority, Effects, and Resources

- Capability policy and grant authority
- Resource Manager
- Resource affinity and lifecycle
- EffectOperation control
- Module Host isolation / trust levels
- provider/tool/process/browser integration boundary

### E. Accounting and Recovery

- AccountingScope hierarchy
- BudgetReservation and settlement
- quota / cost / usage facts
- ReconciliationCase
- UNKNOWN / escalation semantics
- crash recovery and repair boundaries

### F. Product-Facing Runtime Model

- user-facing Node abstraction
- Composite presentation
- Human Interaction / Approval
- diagnostics and user-facing reason presentation
- workflow validation and missing-module UX

### G. Distribution and Extensibility

- Module package format
- registry / installation / version resolution
- dependency compatibility
- trust / signing / provenance
- offline bundle and workflow portability

### H. External Interfaces

- public Runtime API
- CLI / automation interface
- event ingress / egress
- workspace/project boundary
- observability / audit interface

## 6. Document Strategy

Do not grow one universal document indefinitely.

Use one focused design document per architectural domain or tightly coupled contract family. A document should be split when any of the following becomes true:

- it develops its own object/state model;
- it has independent Architecture Invariants;
- it can block implementation independently;
- it requires a dedicated review;
- it has enough context that reviewing it together with unrelated domains reduces precision.

Cross-domain rules should be referenced rather than duplicated wherever possible.

## 7. Design Thread Strategy

The main design thread remains the system-level coordination thread.

A dedicated design conversation should be opened when:

- the topic is large enough to require sustained local reasoning;
- the topic has a distinct contract/state machine;
- keeping its details in the main thread would materially pollute context;
- an independent review would benefit from a clean context window.

A delegated design thread does not freeze architecture by itself. It returns a design result to the Lead Design Authority, which performs integration review and decides whether it becomes baseline.

When a new design conversation is required, the Lead Design Authority must provide the user with a complete handoff prompt containing:

- role;
- exact design target;
- minimum required documents;
- frozen constraints that must not be changed;
- expected deliverable;
- stop conditions / questions that must be escalated;
- instruction not to perform implementation.

## 8. Design Status Vocabulary

- **DRAFT** — active design, not implementation authority.
- **IN REVIEW** — candidate contract under review.
- **FROZEN** — approved implementation baseline.
- **ARCHITECTURE FINDING OPEN** — implementation or review discovered a required semantic change; affected scope is blocked.
- **SUPERSEDED** — replaced by a newer explicit baseline.

## 9. Current Design Status

| Domain | Status | Baseline |
| --- | --- | --- |
| Module subsystem | FROZEN | `Universal_Runtime_Module_Design_Report_v0.1.md` |
| Overall system architecture | DRAFT | `Nyron_Overall_System_Architecture_v0.1.md` |
| Graph / Composite | NOT STARTED | — |
| Runtime orchestration | NOT STARTED | — |
| Capability / Resource system | PARTIALLY DEFINED by Module baseline | — |
| Accounting / Recovery | PARTIALLY DEFINED by Module baseline | — |
| Product-facing Node / UX semantics | PARTIALLY DEFINED by Module baseline | — |
| Distribution / Module ecosystem | PARTIALLY DEFINED by Module baseline | — |
| External interfaces | NOT STARTED | — |

## 10. Next Design Gate

The **Nyron Overall System Architecture Baseline** is now in active DRAFT design.

The draft must answer at minimum:

- what the Kernel owns and does not own;
- the complete first-class subsystem map;
- canonical truth ownership;
- how Graph, Module, Runtime, Capability, Resource, Accounting, Recovery, Registry, Workspace, and Product/UI layers relate;
- which contracts are global versus subsystem-local;
- which design documents must be completed before each implementation gate opens.

The existing Module baseline remains frozen while that system-level architecture is designed. Any discovered conflict must be raised explicitly rather than silently rewriting the Module contract.
