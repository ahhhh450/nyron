# NYRON-D-010 / NYRON-D-001 — Lead Integration Clarification 001

**Status:** NORMATIVE INTEGRATED CANDIDATE CLARIFICATION / PRE-FREEZE
**Applies to:**
- `design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`
- `design/Nyron_Overall_System_Architecture_v0.1.md`

**Authority:** Nyron Lead Design Authority

This clarification resolves `AF-PWP-001` without adding a new generic Ingress subsystem or changing the frozen Packet → Delivery → Activation → Run execution path.

---

## 1. Resolution of AF-PWP-001

For an external event whose only canonical Nyron meaning is:

> request/admit execution of a specific immutable workflow ingress under an exact IngressRouteRevision and execution context

Runtime Orchestration owns a canonical `ExecutionIngressFact` (name normative at concept level; exact implementation field/API names may vary).

`ExecutionIngressFact` is Runtime admission/input truth, not arbitrary external business-domain truth.

Therefore generic workflow-start ingress is:

```text
External transport input
-> adapter validates/authenticates/canonicalizes under exact IngressRouteRevision
-> Command to Runtime: SubmitExecutionIngress(...)
-> Runtime commits/deduplicates ExecutionIngressFact
-> Runtime performs execution admission against exact immutable GraphRevision/context
-> Runtime creates Trigger Packet
-> Delivery
-> Activation
-> Run / Attempt
```

No direct Activation creation exists.

---

## 2. ExecutionIngressFact Ownership Boundary

Runtime Orchestration owns canonical truth for a generic workflow-start `ExecutionIngressFact` because its semantics are limited to execution admission intent/evidence.

Candidate conceptual fields:

```text
ExecutionIngressFact
- execution_ingress_ref
- ingress_route_revision_ref
- external_source_identity_ref / external_event_ref / dedupe_ref
- canonical_payload_ref / payload_hash
- authentication_evidence_ref
- validation_evidence_ref?
- project_ref
- workspace_ref?
- project_config_revision_ref
- workspace_config_revision_ref?
- policy_context_revision_ref
- environment_binding_revision_ref?
- graph_revision_ref
- graph_ingress_binding_ref
- caused_by_ref
- owner_commit_order
```

The exact schema is Runtime/PWP integration detail, but correctness requires:
- stable identity/deduplication;
- exact route revision pinning;
- exact immutable execution context references;
- durable authentication/validation evidence references where needed for historical interpretation;
- no mutable `current/latest` re-resolution after commit.

Runtime may atomically bind an accepted ingress fact to execution admission / Trigger Packet creation when its owner-local transaction model permits it, or may use equivalent durable no-gap transitions. In either case crash/replay must not duplicate execution admission for the same ingress identity unless the route contract explicitly defines repeatable semantics.

---

## 3. Domain External Events Do NOT Move to Runtime

This clarification does not make Runtime the Owner of all external events.

If the external event has canonical business meaning independent of starting a workflow, the corresponding domain Owner remains authoritative.

Examples:

```text
Human response route
-> Human Interaction Owner owns HumanResponse

Provider billing callback
-> Accounting Owner owns accepted UsageFact/accounting truth

Effect/provider operation evidence
-> Effect Authority owns EffectOperation transition/evidence interpretation

Resource callback
-> Resource Manager owns Resource/Lease truth
```

Such domain canonical facts may later trigger workflow execution through a separate Runtime ingress/admission contract, but their business truth is never re-owned by Runtime.

Rule:

```text
business-domain external fact != generic execution ingress fact
```

---

## 4. PWP / Adapter Boundary

PWP Owner owns:
- `IngressRoute` identity;
- immutable `IngressRouteRevision`;
- route source/auth/schema/dedupe/canonicalization configuration;
- exact canonical target Owner/event type;
- exact Graph ingress binding/config references where applicable.

PWP does not commit target-domain facts.

Adapter/transport layer:
- receives bytes/messages;
- authenticates/validates according to route contract;
- canonicalizes source representation;
- supplies stable external identity/evidence;
- sends a Command to the configured canonical target Owner.

Adapter is not canonical Owner merely because it performs authentication/canonicalization.

---

## 5. Generic Workflow Route Target

For a generic route whose sole target semantics are workflow execution admission, `IngressRouteRevision.canonical_target_owner_ref` MUST identify Runtime Orchestration and the canonical event/command contract MUST identify the `ExecutionIngressFact` admission family.

The route must pin or resolve before admission:
- exact `ingress_route_revision_ref`;
- exact `graph_revision_ref`;
- exact `graph_ingress_binding_ref`;
- exact Project/Workspace semantic admission context revisions required by D-010.

A mutable route current pointer, Graph latest pointer or Workspace current config MUST NOT be re-resolved after the canonical ingress/admission fact is committed.

---

## 6. Deduplication / Replay Rule

Generic workflow ingress must have a route-defined stable deduplication identity.

The Runtime-owned ingress/admission path MUST ensure at-least-once transport delivery cannot accidentally create duplicate WorkflowExecutions for one non-repeatable ingress identity.

Same stable ingress identity + same semantic canonical payload/context:
- idempotently return/observe the previously committed ingress/admission result.

Same stable ingress identity + conflicting semantic payload/context:
- fail closed as identity conflict.

If a route intentionally treats repeated source events as distinct workflow starts, the route's dedupe contract must provide distinct canonical identities for those starts.

Wall-clock arrival time alone is not identity.

---

## 7. Rejected Ingress / Admission Failure

Authentication/validation failure before target-Owner canonical acceptance does not create a trusted `ExecutionIngressFact`; it may create security/audit telemetry or a separate rejection fact under the appropriate logging/security contract.

If Runtime accepts the canonical ingress fact but execution admission later fails (for example archived Workspace, non-executable GraphRevision, unresolved required policy context), Runtime may record a durable admission-rejected disposition linked to the ingress identity.

An admission failure does not authorize Adapter/PWP to create Activation by another path.

---

## 8. Added Overall Invariant

**SYS-INV-24 — Generic Workflow Ingress Is Runtime Admission Truth**

An external input whose only canonical Nyron meaning is to request workflow execution is canonicalized into a Runtime-owned, deduplicated execution-ingress/admission fact under an exact IngressRouteRevision and immutable execution context. External inputs with independent business semantics remain owned by their respective domain Owners. Neither PWP nor Adapter owns arbitrary target-domain truth, and no ingress path may bypass Runtime Trigger Packet → Delivery → Activation.

---

## 9. Added PWP Invariant

**PWP-INV-23 — Route Configuration Does Not Own Target Fact**

PWP owns IngressRoute identity/revision/configuration, but never becomes canonical Owner of the target-domain fact merely by configuring/authenticating/routing the input. Generic workflow-start target ownership is Runtime; domain-specific target ownership remains with the corresponding domain Owner.

---

## 10. Lead Disposition

`AF-PWP-001` — **RESOLVED BY LEAD INTEGRATION CLARIFICATION**.

No Frozen Module or Frozen Graph/Composite amendment is required.

D-010 may proceed to Lead Review PASS subject to the remainder of its candidate remaining compatible with this clarification.
