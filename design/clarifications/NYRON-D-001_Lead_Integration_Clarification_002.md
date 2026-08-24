# NYRON-D-001 — Lead Integration Clarification 002

**Status:** NORMATIVE INTEGRATED CANDIDATE CLARIFICATION / PRE-FREEZE
**Applies to:** `design/Nyron_Overall_System_Architecture_v0.1.md`
**Authority:** Nyron Lead Design Authority

This clarification integrates the Lead-reviewed D-007, D-009 and D-010 subsystem candidates and closes the remaining v0.1 canonical Owner placeholders identified in D-001 Clarification 001.

---

## 1. Human Interaction Owner Is Now Defined

The v0.1 Overall Architecture no longer uses a `future owner` placeholder for Human Interaction.

**Human Interaction Owner** owns canonical truth for:
- `HumanRequest`;
- accepted immutable `HumanResponse`;
- request-response binding;
- Human Interaction-owned immutable response aggregation contract/revision;
- canonical `HumanDecisionEvidence` when materialized for cross-owner consumption;
- request lifecycle transitions such as OPEN / SATISFIED / EXPIRED / CANCELLED / SUPERSEDED.

Human Interaction does not own:
- principal/account identity;
- Project/Workspace role membership;
- CapabilityGrant;
- Runtime Subscription/EventDelivery/resume truth;
- ReconciliationCase;
- external notification EffectOperation;
- target subsystem business state.

Human approval is evidence for another Owner's policy decision; it is never the grant/mutation itself.

---

## 2. Project / Workspace Context Owner Is Now Defined

The v0.1 Overall Architecture no longer uses a `future owner` placeholder for Project/Workspace identity/configuration.

**Project / Workspace Context Owner (PWP Owner)** owns canonical truth for:
- `Project` identity/lifecycle;
- `Workspace` identity/lifecycle;
- `ProjectConfigRevision`;
- `WorkspaceConfigRevision`;
- `PolicyContextRevision` composition/reference context;
- `EnvironmentBindingRevision` logical environment configuration;
- `IngressRoute` identity;
- `IngressRouteRevision` configuration/governance.

PWP does not own:
- live Workspace Handle Resource/Lease;
- CapabilityGrant;
- Runtime execution state;
- Graph topology;
- raw credentials/secrets;
- PackageTrustDecision;
- HumanRequest/HumanResponse;
- target-domain external facts.

Workspace identity remains logically distinct from host path, mount, Resource and Lease.

---

## 3. Module Registry / Distribution Owner Is Defined

**Module Registry / Distribution Owner** is the single logical Owner domain for v0.1 module/package distribution canonical state, including:
- registered immutable ModuleDefinition identity/digest records required for exact resolution;
- exact ModuleDefinition-to-package publication binding;
- Registry identity/publication records;
- package identity/version/content digest;
- publisher/namespace bindings;
- installation records;
- withdrawal/deprecation governance;
- canonical `PackageTrustDecision` result/evidence;
- package enable/disable state where enablement is modeled canonically.

Distribution cannot mutate the immutable semantic contents of an already registered `ModuleDefinition@version`.

The following remain separate:

```text
Import
!= Resolve
!= Install
!= Trust
!= Enable
!= CapabilityGrant
!= Runtime admission/execution
```

Exact Graph dependency resolution never substitutes latest/current/range-compatible versions.

---

## 4. Policy Context vs Decision Owner Pattern

Nyron freezes a general system pattern:

```text
PWP immutable policy context
-> consumed by domain Owner
-> domain Owner commits its own decision truth
```

Examples:

```text
PWP security/capability policy context
-> Capability Authority
-> CapabilityGrant / denial

PWP package trust policy context
-> Module Registry / Distribution Owner
-> PackageTrustDecision

PWP responder/role policy context
-> Human Interaction Owner
-> response acceptance/authorization evidence binding

PWP runtime admission policy context
-> Runtime Orchestration
-> WorkflowExecution admission/denial
```

PWP owning policy-source composition never grants it mutation authority over the resulting domain decisions.

### Added system invariant

**SYS-INV-25 — Policy Context Owner Is Not Decision Owner By Reference Alone**

Owning the immutable policy/config context that supplies decision inputs does not transfer ownership of the resulting Capability, Runtime, Distribution, Human Interaction, Accounting or other domain decision. The authoritative domain Owner commits the decision under its own contract.

---

## 5. Generic Workflow Ingress Ownership Is Closed

`AF-PWP-001` is resolved.

For an external input whose only canonical Nyron meaning is to request workflow execution, Runtime Orchestration owns the canonical `ExecutionIngressFact` / execution-ingress admission truth.

Flow:

```text
External transport
-> exact IngressRouteRevision
-> adapter authentication/validation/canonicalization
-> Runtime-owned deduplicated ExecutionIngressFact
-> Runtime admission with exact immutable execution context
-> Trigger Packet
-> Delivery
-> Activation
-> Run / Attempt
```

PWP owns route configuration, not the target fact.
Adapter validates/translates, but is not target fact Owner.

Domain-specific external business facts remain owned by their domain Owners:
- HumanResponse -> Human Interaction;
- billing/usage -> Accounting;
- effect evidence -> Effect Authority;
- resource callback/state -> Resource Manager.

Runtime owns only the generic execution-ingress fact when workflow-start intent is the complete canonical semantic meaning.

---

## 6. Semantic Admission Context Is Now Grounded In D-010

The system-level replay-stable admission requirement from D-001 Clarification 001 is concretely satisfied by exact references supplied through PWP context.

An admitted execution must be able to preserve exact refs such as:
- `project_ref`;
- `project_config_revision_ref`;
- optional `workspace_ref`;
- optional `workspace_config_revision_ref`;
- `policy_context_revision_ref`;
- optional `environment_binding_revision_ref`;
- optional `ingress_route_revision_ref`;
- exact `graph_revision_ref`;
- exact graph ingress binding identity where used;
- immutable Runtime policy reference/version.

Current/latest PWP revision pointers are never re-resolved to reinterpret an already-admitted execution.

Dynamic revocable authority remains dynamic:
- current Attempt/fencing;
- CapabilityGrant;
- ResourceLease;
- Effect conflict clearance;
- budget/reservation authority where applicable.

---

## 7. Human Response / Runtime Resume Boundary

A canonical HumanResponse or HumanDecisionEvidence never directly calls Module resume and never creates Activation.

If an existing current Attempt is suspended waiting for Human Interaction evidence:

```text
Human Interaction canonical event
-> Runtime Subscription matching
-> EventDelivery
-> current-Attempt/fencing validation
-> resume same Attempt
```

If a Human Interaction fact starts a new workflow execution:

```text
Human Interaction canonical fact/event
-> Runtime execution ingress/admission
-> Trigger Packet
-> Delivery
-> Activation
```

A stale Attempt cannot regain authority because a valid human response arrived later.

---

## 8. Distribution / Active Execution Boundary

Package trust/install/enable changes affect loading/admission according to policy, but do not silently rewrite already-pinned GraphRevision or ModuleDefinition identity.

A `PackageTrustDecision` change alone does not directly cancel/fence a running Attempt or external EffectOperation.

If policy requires emergency action against active execution, it must use explicit Runtime/Capability/Effect/Host contracts and produce their canonical transitions.

Historical execution remains tied to exact immutable definition/package/provenance facts even when future loading is denied.

---

## 9. Overall Owner Table — Pre-Freeze Integrated Set

| Canonical state class | Authoritative Owner |
| --- | --- |
| GraphRevision / executable definition topology | Graph subsystem |
| ModuleDefinition registration identity + distribution publication binding | Module Registry / Distribution Owner |
| Module package/install/trust/governance | Module Registry / Distribution Owner |
| Project / Workspace identity and revisioned config/policy/binding context | PWP Owner |
| IngressRoute identity/revision | PWP Owner |
| generic workflow ExecutionIngressFact | Runtime Orchestration |
| Packet / Delivery / Activation / Run / Attempt | Runtime Orchestration |
| Continuation / Subscription / EventDelivery consumption | Runtime Orchestration |
| CapabilityGrant | Capability Authority |
| Resource / ResourceLease | Resource Manager |
| EffectOperation | Effect Authority |
| AccountingScope/BudgetPolicyRevision/BudgetReservation/UsageFact | Accounting Owner |
| ReconciliationCase / Recovery disposition | Recovery Owner |
| HumanRequest / accepted HumanResponse / HumanDecisionEvidence | Human Interaction Owner |

No correctness-critical v0.1 canonical Owner placeholder remains in this integrated set.

### Added system invariant

**SYS-INV-26 — Overall v0.1 Owner Closure**

The pre-freeze integrated v0.1 canonical state set listed above has one explicit authoritative Owner per state class. New canonical classes introduced before freeze must be added explicitly to the Owner table or raise an Architecture Finding.

---

## 10. D-006 Product Node / UX Sequencing

D-006 remains non-blocking for System Foundation freeze.

Detailed Product Node taxonomy / visual UX may proceed after foundation freeze because:
- Node is already constrained to Product Layer;
- Product Extension Envelope remains explicit;
- Browser/Shell/File/HTTP/Provider/Human/etc. can map to generic frozen subsystem mechanisms;
- no unresolved product-only canonical Owner is required for current System Foundation correctness.

If later Product design exposes a genuine inability to express a required user-facing concept using the frozen extension envelope, it must raise a new Architecture Finding rather than locally invent a Kernel/Runtime primitive.

---

## 11. Lead Integration Results

- `NYRON-D-007` — **LEAD REVIEW PASS WITH CLARIFICATION**.
- `NYRON-D-009` — **LEAD REVIEW PASS WITH CLARIFICATION**.
- `NYRON-D-010` — **LEAD REVIEW PASS; AF-PWP-001 RESOLVED BY CLARIFICATION**.

No Frozen Module or Frozen Graph/Composite amendment is required by D-007, D-009 or D-010 integration.

These three subsystems are ready for bounded independent consistency review before freeze consideration.
