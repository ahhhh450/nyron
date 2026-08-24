# NYRON-D-001 — Lead Integration Clarification 001

**Status:** NORMATIVE INTEGRATED CANDIDATE CLARIFICATION / PRE-FREEZE
**Applies to:** `design/Nyron_Overall_System_Architecture_v0.1.md`
**Authority:** Nyron Lead Design Authority

This clarification fixes system-level integration rules that are already implied by the frozen Module / Graph baselines and the Lead-reviewed D-003 / D-004 / D-005 / D-008 candidates. It deliberately does not pre-decide the detailed internal state machines still delegated to D-007, D-009 or D-010.

---

## 1. Canonical Owner Matrix Is Exhaustive, Not Illustrative

For any canonical state class admitted into the frozen Overall Architecture, the Owner table is normative and exhaustive.

A state class MUST NOT be left with:
- two possible Owners;
- an adapter/host acting as de-facto Owner;
- a product UI surface acting as Owner;
- an implementation database acting as Owner;
- an unspecified `future owner` once that state is required for correctness in the frozen architecture.

Current fixed ownership:

| Canonical state class | Owner |
| --- | --- |
| GraphRevision / immutable executable topology | Graph subsystem |
| ModuleDefinition semantic version | Module Registry domain |
| Packet / Delivery / Activation / Run / Attempt | Runtime Orchestration |
| Continuation / Subscription / EventDelivery consumption | Runtime Orchestration |
| CapabilityGrant | Capability Authority |
| Resource / ResourceLease | Resource Manager |
| EffectOperation | Effect Authority |
| AccountingScope accounting metadata / BudgetPolicyRevision / BudgetReservation / UsageFact | Accounting Owner |
| ReconciliationCase / Recovery disposition | Recovery Owner |

Still-open Owner assignments that MUST close before Overall freeze if their canonical objects remain first-class in v0.1:
- HumanRequest / authenticated HumanResponse / approval evidence record — D-009;
- Project / Workspace identity, policy/config context and ingress-route registration — D-010.

D-007 may define Registry/package/trust canonical state, but MUST preserve the distinction between ModuleDefinition semantic identity, package/install state, trust state and execution authority.

### Added system invariant

**SYS-INV-19 — No Owner Placeholder At Freeze**

Any canonical state class required by the frozen v0.1 architecture MUST have exactly one named authoritative Owner before Overall Architecture freeze. `future owner`, adapter ownership, shared ownership and storage-layer ownership are not acceptable frozen semantics.

---

## 2. Cross-Owner Completion, Disposition and Clearance Are Different Facts

Nyron MUST distinguish three concepts:

1. **Local completion** — an Owner has completed its own state transition.
2. **Administrative disposition** — an Owner such as Recovery has decided how another subsystem may proceed despite unresolved history.
3. **Authority/conflict clearance** — the authoritative subject Owner has established that a specific future action is safe/allowed with respect to that subject.

Examples:
- `ReconciliationCase.RESOLVED` proves only Recovery case disposition.
- `ExecutionCancelled` proves only Runtime cancellation truth.
- `BudgetReservationReleased` proves only Accounting release of budget authority/exposure.
- none of the above proves an UNKNOWN EffectOperation is safely fenced.

A future replacement Run/Attempt that needs conflicting effect authority MUST consume clearance from the authoritative Effect/Resource/Capability owners, not infer it from Runtime or Recovery state.

A clearance fact MUST be scope-specific enough to identify at minimum:
- authoritative Owner;
- subject_ref / conflict domain;
- action/scope being cleared;
- causal basis/evidence refs;
- validity/fencing context where applicable.

It MUST NOT be a universal `SAFE=true` flag spanning unrelated Owners.

### Added system invariant

**SYS-INV-20 — Clearance Is Owner-Scoped Evidence**

No subsystem may infer foreign safety/authority clearance from local completion, cancellation, settlement or reconciliation status. Clearance used to authorize future conflicting work must originate from the authoritative Owner of the conflict-bearing subject and be scoped to the relevant action/domain.

---

## 3. Execution Admission Context Must Pin Semantic Inputs

Nyron distinguishes **semantic admission inputs** from **dynamic execution authority**.

### 3.1 Semantic admission inputs

Any configuration/policy fact whose later mutation would change the meaning of an already-admitted execution MUST be represented by an immutable/revisioned reference pinned into the execution admission context, or by an equivalent immutable snapshot owned by the responsible subsystem.

The v0.1 admission context must be able to bind at least:
- exact `graph_revision_ref`;
- exact immutable Runtime policy reference/version;
- definition/config references already frozen through Graph/ModuleInstanceRevision;
- project/workspace/environment policy context reference(s) once D-010 defines the owning objects;
- ingress binding/context identity when execution is admitted from an external/public route;
- causal/admission identity sufficient for replay and audit.

The exact field names and Owner of Project/Workspace policy context are delegated to D-010. This clarification freezes the requirement that execution semantics cannot depend on mutable deployment defaults that are invisible to canonical history.

### 3.2 Dynamic execution authority is not snapshotted away

The following remain dynamically revalidated canonical authority and MUST NOT be converted into one admission-time snapshot that bypasses revocation/fencing:
- CapabilityGrant validity;
- current Attempt/fencing authority;
- ResourceLease validity;
- Effect conflict clearance;
- budget availability/reservation state where policy requires current authorization.

Therefore:

```text
immutable admission context != permanent execution authority
```

### Added system invariant

**SYS-INV-21 — Semantic Admission Is Replay-Stable**

Any mutable external configuration/policy that can change the semantic interpretation of an admitted execution must be pinned by immutable/revisioned canonical reference or equivalent snapshot. Replay must not reinterpret past executions using current deployment defaults.

### Added system invariant

**SYS-INV-22 — Admission Snapshot Cannot Bypass Revocation**

Admission-time context cannot replace dynamic validation of Capability, current Attempt/fencing, ResourceLease, Effect conflict or other revocable execution authority at the actual boundary where that authority matters.

---

## 4. Top-Level Ingress Contract Shape

The frozen system rule remains:

```text
external/product/API/human/timer intent
-> authoritative validation/canonicalization/admission
-> Runtime Trigger Packet
-> Delivery
-> Activation
-> Run / Attempt
```

No D-009 or D-010 design may introduce:

```text
External input -> direct Activation
Human approval -> direct Module execution
Ingress route -> direct Run creation
```

D-009 may produce authenticated/canonical HumanResponse evidence.
D-010 may own ingress-route/config/binding metadata.
Runtime remains the Owner that admits execution and creates the Trigger Packet / downstream execution facts.

### Added system invariant

**SYS-INV-23 — Ingress Owners Validate; Runtime Executes**

External/Human/Project ingress owners may authenticate, validate, canonicalize and authorize admission context, but they cannot create Activation/Run directly or establish a second execution path around Runtime Packet → Delivery → Activation semantics.

---

## 5. Product Node / Visual UX Is Not an Overall-Freeze Blocker

Detailed D-006 Product Node taxonomy and visual workflow UX are **not required to freeze the System Foundation v0.1**, provided all of the following remain true:

- Product Extension Envelope is retained;
- Node remains a Product-layer abstraction, not Runtime/Kernel primitive;
- no product concept requires a new unresolved canonical Owner to make the foundation correct;
- future product Nodes can be expressed through frozen Module/Graph/Capability/Resource/Effect/Accounting/Human/Workspace contracts.

Therefore D-006 may proceed after System Foundation freeze unless a later Product requirement exposes a genuine architecture gap.

This is a sequencing decision, not a claim that product UX is unimportant.

---

## 6. Overall Architecture Freeze Gate

`Nyron_Overall_System_Architecture_v0.1.md` may enter final Independent Adversarial Architecture Review only when all conditions below are true.

### F1 — Frozen dependency integrity
- Frozen Module baseline remains intact except explicit Amendment 001.
- Frozen Graph/Composite baseline remains intact or changes only through explicit amendment/superseding freeze.

### F2 — Owner closure
- every first-class canonical state required by Overall v0.1 has exactly one named Owner;
- D-009 closes Human Interaction ownership if HumanRequest/HumanResponse remain first-class;
- D-010 closes Project/Workspace/policy/ingress-route ownership if those objects remain first-class.

### F3 — Subsystem local review closure
- D-003 Runtime has valid independent review or an explicitly accepted Lead disposition;
- D-004 Capability/Resource/Effect has valid independent review or accepted disposition;
- D-005 Accounting/Recovery has valid independent review or accepted disposition;
- D-008 External Interfaces has valid independent review or accepted disposition.

### F4 — Cross-subsystem contradiction check
At minimum verify:
- Runtime replacement semantics match D-004 fencing/clearance;
- Runtime termination/Recovery disposition does not fabricate subject clearance;
- Accounting cannot rewrite Effect/Resource truth;
- External adapters cannot own Capability/Resource/Effect state;
- Human approval evidence cannot bypass Capability/target Owner authority;
- Workspace/Project context cannot become live Resource/Capability/Graph truth;
- Registry/install/trust state cannot silently rewrite exact executable definitions.

### F5 — Replay/crash completeness
Every safety-critical path must have an explicit answer for:
- stable identity;
- authoritative Owner;
- crash window;
- duplicate/retry handling;
- UNKNOWN handling;
- durable propagation;
- stale-attempt fencing where relevant.

### F6 — No silent implementation dependency
Any implementation choice that could alter canonical semantics must either:
- already be fixed by a frozen contract; or
- remain explicitly outside v0.1 correctness semantics.

Examples such as physical database choice, queue technology, worker process model or UI layout MUST NOT become hidden semantic dependencies.

### F7 — Integrated adversarial review
Claude (or equivalent broad independent reviewer selected by Lead) reviews the integrated system, frozen dependency manifests and all accepted clarifications with freedom to challenge cross-subsystem assumptions.

Reviewer output remains advisory; Lead accepts/rejects findings and owns final freeze.

---

## 7. Freeze Recommendation State

Current state at issuance of this clarification:

- Module Architecture — FROZEN.
- Amendment 001 — FROZEN.
- Graph/Composite — FROZEN.
- D-003 / D-004 / D-005 / D-008 — Lead-integrated; independent-review wave active.
- D-007 / D-009 / D-010 — delegated in parallel.
- D-006 — explicitly non-blocking for System Foundation freeze unless it later reveals a genuine architecture gap.

No new Frozen Module or Frozen Graph Architecture Finding is introduced by this clarification.
