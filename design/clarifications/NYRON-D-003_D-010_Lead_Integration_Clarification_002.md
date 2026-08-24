# NYRON-D-003 / NYRON-D-010 — Lead Integration Clarification 002

**Status:** NORMATIVE INTEGRATED CANDIDATE CLARIFICATION / PRE-FREEZE
**Applies to:**
- `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`
- `design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`

**Authority:** Nyron Lead Design Authority

This clarification resolves D-003 `OQ-RT-01` and tightens `OQ-RT-05` using the integrated Project/Workspace/Ingress ownership model.

---

## 1. OQ-RT-01 — Top-Level Execution Ingress Mapping — RESOLVED

Top-level execution admission uses an immutable ingress contract and never creates Activation directly.

Canonical generic workflow-start flow:

```text
External/Product/API/Timer/Human-trigger intent
-> exact PWP IngressRouteRevision or equivalent internal admission contract
-> authentication/validation/canonicalization where external
-> Runtime-owned ExecutionIngressFact / stable admission identity
-> Runtime validates exact GraphRevision + graph ingress binding + pinned semantic context
-> Runtime commits WorkflowExecution admission
-> Runtime creates Trigger Packet
-> ordinary Edge projection -> Delivery
-> Activation
-> Run / Attempt
```

For internal product/API starts that do not traverse an external network adapter, the same semantic rule applies: the caller provides a stable execution-ingress/admission identity and exact immutable Graph ingress binding/context; Runtime owns the resulting ingress/admission fact and Trigger Packet.

Forbidden:

```text
API/Product/Human/PWP/Adapter -> Activation
API/Product/Human/PWP/Adapter -> Run
```

### Added Runtime invariant

**RT-INV-25 — Top-Level Ingress Produces Runtime Trigger Packet**

Every new workflow execution admission is represented by Runtime-owned ingress/admission truth bound to an exact immutable Graph ingress binding and produces execution through Trigger Packet -> Delivery -> Activation. No top-level caller may create Activation/Run directly.

---

## 2. Graph Ingress Binding

The Graph/Definition layer may expose a formal immutable Graph ingress binding/port contract.

Runtime consumes the exact frozen binding identity from the admitted GraphRevision/context.

The Graph ingress binding determines where the Trigger Packet enters the frozen topology; it does not itself create Packet, Delivery, Activation or Run.

If the Graph ingress binding is unresolved/invalid, execution admission fails closed.

Mutable Graph `current/latest` state is never resolved after the ingress fact/admission is committed.

---

## 3. Generic External Trigger Dedupe

The Runtime-owned execution-ingress path must preserve stable deduplication semantics supplied by the exact route/admission contract.

For a non-repeatable ingress identity:
- same identity + same semantic payload/context -> idempotent existing admission/result;
- same identity + conflicting payload/context -> fail closed;
- transport duplicate/redelivery must not create duplicate WorkflowExecution.

A route that intentionally allows repeated starts must assign distinct canonical ingress identities according to its immutable dedupe contract.

---

## 4. OQ-RT-05 — Event Source Ordering Contract — TIGHTENED

Runtime Subscription/EventDelivery matching consumes canonical source Event identity/evidence, not raw transport arrival order.

Each source Owner/event family used for durable Subscription matching MUST expose enough canonical ordering/cursor semantics for Runtime to prevent lost-event and duplicate-resume races.

This may be:
- owner-local event sequence/cursor;
- stable event identity plus causal watermark contract;
- another source-specific immutable ordering contract.

External adapters may receive messages in arbitrary transport order; that order is non-semantic unless the authoritative target Owner explicitly commits an owner-local canonical order.

Human Interaction events, Accounting callbacks after acceptance, Effect/Resource events and Runtime execution events follow this same rule.

### Added Runtime invariant

**RT-INV-26 — Subscription Ordering Uses Source Canonical Order**

Runtime event matching/resume correctness depends on durable source Owner identity/order/cursor semantics, never raw message-bus, webhook, socket or wall-clock arrival order.

---

## 5. PWP / Runtime Ownership Boundary

PWP owns:
- Project/Workspace semantic context revisions;
- IngressRoute identity/revision/configuration;
- policy/binding references supplied for admission.

Runtime owns:
- ExecutionIngressFact;
- execution admission/denial;
- Trigger Packet;
- all downstream execution facts.

PWP cannot create execution truth; Runtime cannot mutate PWP configuration.

---

## 6. Lead Disposition

- `OQ-RT-01` — **RESOLVED**.
- `OQ-RT-05` — source-ordering contract requirement clarified sufficiently for v0.1 architecture; exact event-store API/schema remains implementation detail.

No Frozen Module or Frozen Graph/Composite amendment is required.
