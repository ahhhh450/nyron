# Nyron Human Interaction / Approval Authority Design Candidate v0.1

Task ID: `NYRON-D-009`

Status: **CANDIDATE — FOR LEAD REVIEW**

Authority: delegated design candidate only; this document does not freeze architecture.

Depends on:
- `design/Universal_Runtime_Module_Design_Report_v0.1.md` — **FROZEN MODULE ARCHITECTURE BASELINE**
- `design/Nyron_Overall_System_Architecture_v0.1.md` — DRAFT integrated system candidate
- `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md` — Lead-review PASS candidate
- `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md` — Lead-review PASS candidate
- `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md` — Lead-review PASS candidate
- `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md` — Lead-review PASS candidate
- `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`
- `design/clarifications/NYRON-D-008_Lead_Integration_Clarification_001.md`

---

## 1. Purpose

This candidate defines Nyron's canonical Human Interaction domain for durable requests to humans, authenticated human responses, approval evidence, response binding, expiry/cancellation/supersession, multi-responder extension, Runtime waiting/resume integration, external ingress canonicalization and Recovery/manual-review boundaries.

The central architecture rule is:

> Human Interaction owns canonical `HumanRequest` / `HumanResponse` truth. It does not become a Kernel/Runtime primitive taxonomy, does not own human identity authentication infrastructure, does not own Capability policy truth, does not own Recovery disposition, and does not create a second waiting engine.

Human-facing product concepts such as approval dialogs, review cards, forms, inboxes, escalation panels, confirmation modals, reviewer roles or agent personas remain Product/Workspace policy concerns unless represented through the generic canonical contracts defined here.

---

## 2. Hard Boundaries

This design preserves the following boundaries.

1. `Human Approval` is not a Runtime primitive or a new Module type.
2. The frozen execution path remains `Packet -> Delivery -> Activation -> Run / Attempt`.
3. Waiting for human input uses the frozen `Suspended -> Subscription -> EventDelivery -> resume(...)` contract.
4. Human Interaction does not authenticate humans by itself; it consumes authentication/authorization evidence from configured trusted ingress/identity authorities.
5. Capability Authority may require approval evidence, but it does not own `HumanResponse` truth.
6. Recovery may request manual review, but it does not own human identity, request/response truth, or subject-state truth.
7. Creating an internal HumanRequest may be a mediated Canonical Command and does not inherently require an `EffectOperation`.
8. External notification delivery such as email, Slack, push, SMS or another provider dispatch is a separate external operation and uses ordinary Capability / Resource / Effect semantics where applicable.
9. A human response arriving from outside Nyron is untrusted External Input until authenticated, validated, deduplicated, bound and committed by the authoritative Human Interaction Owner.
10. A stale Runtime Attempt cannot regain commit/resume/effect authority merely because a valid human response exists.

---

## 3. Canonical Owner

Nyron defines a logical **Human Interaction Owner**.

Human Interaction Owner owns:
- `HumanRequest` canonical identity and lifecycle;
- `HumanResponse` canonical identity and lifecycle;
- request-response binding;
- response deduplication identity;
- accepted authentication/authorization evidence references associated with a response;
- request expiry/cancellation/supersession truth;
- response acceptance/rejection-as-response-fact decisions;
- aggregate decision state derived under a pinned response policy where that aggregate is required as canonical evidence;
- canonical Human Interaction events.

Human Interaction Owner does **not** own:
- user/account/person identity records;
- credentials, OAuth sessions, SSO truth or directory membership;
- Product UI presentation;
- Workspace/Project role policy truth;
- CapabilityGrant lifecycle;
- Runtime Attempt or Subscription truth;
- ReconciliationCase or Recovery disposition;
- EffectOperation truth;
- notification-provider delivery truth;
- Graph topology or Module semantics.

References to foreign canonical objects never transfer ownership.

---

## 4. HumanRequest

### 4.1 Meaning

A `HumanRequest` is a durable Nyron request for one or more authenticated human responses under an explicit immutable request contract.

It is semantic interaction state, not a UI widget and not an outbound-message delivery record.

### 4.2 Candidate identity

```text
HumanRequest
- human_request_ref
- request_kind
- request_schema_ref
- response_schema_ref
- response_policy_ref
- target_policy_ref?
- subject_refs[]
- requested_by_owner_ref
- requested_by_ref
- caused_by_ref
- execution_ref?
- activation_ref?
- run_ref?
- attempt_seq?
- fencing_context_ref?
- expires_at?
- state
- created_event_ref
- terminal_event_ref?
```

`human_request_ref` is globally stable canonical identity.

`request_kind` is a semantic contract class, not product UX taxonomy. Initial generic classes MAY include:
- `APPROVAL_DECISION`;
- `CHOICE`;
- `STRUCTURED_RESPONSE`;
- `ACKNOWLEDGEMENT`.

The vocabulary is intentionally small and extensible. Product labels such as reviewer, developer, supervisor, red button, wizard, form type or dialog style are forbidden as Kernel/Runtime primitive taxonomy.

### 4.3 Stable creation dedupe

Creation MUST carry a stable caller-supplied or owner-derived deduplication identity.

Candidate command:

```text
CreateHumanRequest
- request_command_ref
- human_request_ref
- request_contract_hash
- payload_ref
- caused_by_ref
```

The same creation identity with the same canonical request contract is idempotent.

Reusing the same identity with different request content, policy, target scope, expiry or response schema MUST fail with an identity conflict rather than silently mutating the existing request.

### 4.4 Lifecycle

Candidate request states:

```text
OPEN
SATISFIED
EXPIRED
CANCELLED
SUPERSEDED
```

State meaning:
- `OPEN` — responses may still be accepted according to policy.
- `SATISFIED` — response policy has produced a terminal accepted aggregate decision/evidence.
- `EXPIRED` — expiry boundary passed before satisfaction and Owner committed expiry.
- `CANCELLED` — authoritative caller/policy cancelled future response acceptance.
- `SUPERSEDED` — another request explicitly replaced this request for the relevant decision scope.

Terminal state does not erase historical responses already committed.

---

## 5. HumanResponse

### 5.1 Meaning

A `HumanResponse` is an immutable canonical fact that a response payload, attributed to an authenticated responder context, was accepted and bound to one exact HumanRequest.

A response is not equivalent to approval. Approval is one possible semantic payload/decision under a request contract.

### 5.2 Candidate identity

```text
HumanResponse
- human_response_ref
- human_request_ref
- responder_principal_ref
- responder_context_ref?
- response_payload_ref
- response_schema_ref
- response_semantic_hash
- external_response_ref?
- ingress_route_ref?
- authentication_evidence_ref
- authorization_evidence_ref?
- received_at?
- committed_at_owner_order
- caused_by_ref
- state
```

Response state is intentionally minimal:

```text
ACCEPTED
REJECTED_AS_INVALID
```

`REJECTED_AS_INVALID` MAY be represented as a separate ingress rejection fact instead of a HumanResponse record. The canonical requirement is that invalid/untrusted transport input never becomes accepted HumanResponse truth.

Accepted HumanResponse records are immutable.

### 5.3 Response vocabulary

The canonical payload schema may express:
- approval: `APPROVE | DENY`;
- choice: one or more values constrained by the pinned response schema;
- acknowledgement: explicit confirmation;
- structured response: typed fields under immutable schema;
- optional human-authored text/comment fields where policy permits.

Nyron does not freeze presentation concepts such as buttons, forms, pages, chat replies or modal dialogs.

---

## 6. Request-Response Binding and Deduplication

Every accepted response MUST bind to exactly one `human_request_ref`.

The Human Interaction Owner must verify:
1. request exists;
2. request is currently eligible to accept the response;
3. response schema/version matches the pinned request contract;
4. responder authentication evidence is valid for the configured ingress policy;
5. responder authorization evidence satisfies the request's target/role policy where required;
6. stable response dedupe identity has not already committed a semantically conflicting response.

Candidate stable dedupe key:

```text
response_dedupe_key =
(
  ingress_route_ref,
  external_response_ref
)
```

where a trustworthy immutable external response/message identity exists.

If no external immutable ID exists, the configured ingress contract MUST define another stable idempotency identity. Wall-clock time, transport delivery sequence, UI request count or payload hash alone MUST NOT be assumed globally unique.

Duplicate delivery of the same response identity is idempotent.

The same stable response identity with a different semantic payload is an identity conflict and MUST fail closed.

---

## 7. Authentication and Authorization Evidence Boundary

Human Interaction Owner accepts evidence; it does not become the identity provider.

### 7.1 Authentication evidence

Authentication may originate from trusted external/interface mechanisms such as:
- SSO/OIDC/OAuth authenticated session;
- signed webhook or provider callback bound to a known principal;
- mTLS/client certificate identity;
- verified provider account identity;
- trusted workspace/product session;
- another configured identity authority.

Architecture-level evidence must be durably referenceable where losing it would change interpretation of the accepted HumanResponse.

Candidate evidence reference:

```text
AuthenticationEvidenceRef
- evidence_ref
- authority_ref
- principal_ref
- auth_context_class
- issued_at?
- verified_at?
- immutable_evidence_hash / canonical evidence pointer
```

This is a conceptual evidence contract, not a claim that Human Interaction owns the identity system.

### 7.2 Authorization evidence

Authentication answers who/what principal was authenticated. Authorization answers whether that principal may respond to this request under pinned policy.

Authorization may depend on Workspace/Project/Product policy such as role, team, ownership or review assignment. Human Interaction consumes a pinned policy/evidence decision from the appropriate policy Owner.

Human Interaction MUST NOT infer role authority merely from display name, email address, UI route possession or knowledge of `human_request_ref`.

### 7.3 Replay

Replay reuses the committed canonical response and its evidence references. It does not re-contact the human or re-authenticate historical responses to reinterpret past truth.

Future policy changes do not retroactively invalidate an already accepted canonical response unless a separate explicit architecture contract defines revocation semantics for that evidence class.

---

## 8. Approval Evidence Model

Capability Authority may evaluate:

```text
GRANTED
DENIED
REQUIRES_APPROVAL
```

`REQUIRES_APPROVAL` is not a HumanRequest and not a CapabilityGrant.

Expected loop:

```text
Capability request
-> Capability Authority evaluates policy
-> REQUIRES_APPROVAL(decision_request_ref / approval_requirement)
-> caller creates HumanRequest through Human Interaction Owner
-> Human Interaction collects authenticated response(s)
-> Human Interaction commits canonical ApprovalEvidence / aggregate decision
-> caller re-requests / re-evaluates Capability with evidence_ref
-> Capability Authority independently verifies evidence applicability/current policy
-> GRANTED or DENIED
```

Human approval is evidence for policy re-evaluation. It does not force grant issuance and cannot override a higher-priority system-security deny.

### 8.1 Canonical approval evidence

Where Capability or another Owner needs a stable machine-checkable aggregate, Human Interaction may own:

```text
HumanDecisionEvidence
- decision_evidence_ref
- human_request_ref
- response_policy_ref
- accepted_response_refs[]
- result
- subject_refs[]
- validity_context
- committed_event_ref
```

For simple approval, `result` may be `APPROVED | DENIED`.

This object is Human Interaction truth about what the configured response contract concluded. It is not Capability truth and not a CapabilityGrant.

### 8.2 Evidence applicability

Consumers MUST validate that evidence applies to the exact protected subject/scope/operation requested. Approval for one path, effect, amount, project, Attempt, operation class or time window MUST NOT be generalized to a broader authority scope.

---

## 9. Expiry, Cancellation and Supersession

### 9.1 Expiry

`expires_at` is part of the immutable request contract when expiry is used.

Expiry is committed by Human Interaction Owner. A local UI timer or missing response is not canonical expiry by itself.

Responses arriving after committed expiry are late and MUST NOT satisfy the request.

### 9.2 Cancellation

Authorized foreign Owners may send `CancelHumanRequest` Command. Human Interaction Owner decides whether the cancellation is valid and commits `CANCELLED`.

Cancellation prevents future accepted responses for satisfying that request. It does not delete prior response history.

### 9.3 Supersession

Supersession is explicit, never inferred from "newest request" or wall-clock order.

Candidate command:

```text
SupersedeHumanRequest
- old_human_request_ref
- new_human_request_ref
- supersession_scope
- caused_by_ref
```

The Human Interaction Owner commits the old request `SUPERSEDED` only when policy permits the relationship.

A response to a superseded request remains historical evidence but cannot satisfy the successor request unless the successor's explicit policy allows imported evidence and records that relationship.

---

## 10. Multiple Responders, Quorum and Role Policy Extension

v0.1 must support extension beyond one responder without freezing a product role taxonomy.

Candidate `ResponsePolicyRevision` concepts:

```text
ResponsePolicyRevision
- response_policy_ref
- responder_selector_ref
- cardinality_rule
- decision_rule
- duplicate_principal_rule
- conflict_rule
- expiry_behavior
- policy_version
```

Possible generic cardinality/decision semantics include:
- exactly one accepted response;
- first valid response;
- N-of-M quorum;
- all required selectors;
- threshold approvals with deny veto;
- role/selector-weighted rule;
- structured multi-party collection.

Exact role names remain Workspace/Project/Product policy data.

Human Interaction Owner may evaluate a response policy but must consume authoritative principal/role membership evidence from the policy Owner.

A single principal MUST NOT count multiple times toward quorum unless the pinned policy explicitly permits that behavior.

Concurrent responses are serialized or evaluated under deterministic owner-local ordering. Correctness MUST NOT depend on transport arrival race alone.

---

## 11. Runtime Suspension / Subscription / Resume Mapping

Human Interaction introduces no second wait engine.

A Module that needs to wait for a human uses the frozen Module contract:

```text
execute(...)
-> Suspended(subscription_spec, continuation)
```

The `subscription_spec` targets a canonical Human Interaction event/evidence identity such as:
- `HumanRequestSatisfied(human_request_ref)`;
- `HumanRequestExpired(human_request_ref)`;
- `HumanRequestCancelled(human_request_ref)`;
- another explicitly registered canonical event contract.

Runtime owns:
- Continuation;
- Subscription;
- event cursor / causal watermark;
- EventDelivery;
- current-Attempt resume eligibility;
- resume consumption.

Human Interaction owns only the source canonical request/response/decision events.

A human response does not directly call Module `resume`. It creates canonical Human Interaction evidence/event; Runtime's ordinary durable event matching creates EventDelivery and resumes only the current eligible Attempt.

### 11.1 No inherent suspension

Creating a HumanRequest does not inherently suspend the creating Module.

Valid patterns include:
- create request and complete;
- create request then suspend waiting for it;
- one Module creates the request while another Module later waits/consumes the result;
- Product/UI creates a request through authorized Canonical Command while workflow execution continues independently.

---

## 12. External HumanResponse Ingress Canonicalization

A response arriving from UI, API, webhook, email, Slack, Teams, mobile push callback or another provider begins as untrusted external input.

Required sequence:

```text
receive external payload
-> route resolution
-> authenticate source/principal
-> validate transport/provider identity
-> validate request identity and response schema
-> derive stable dedupe identity
-> authorize responder under pinned target/policy context
-> Human Interaction Owner commits HumanResponse
-> Human Interaction Owner updates request/decision state atomically as required
-> emit durable Human Interaction canonical event
```

The ingress adapter does not own HumanResponse truth.

The route contract must identify Human Interaction Owner as canonical target for response ingress and must preserve D-008's rule that transport reception itself is not canonical authority.

If the accepted response triggers workflow execution rather than resumes an existing Subscription, it still enters Runtime only through:

```text
canonical Human Interaction event/fact
-> admitted immutable GraphRevision ingress binding
-> Runtime Trigger Packet
-> Delivery
-> Activation
```

Direct `HumanResponse -> Activation` is forbidden.

---

## 13. Internal Request vs Outbound Notification

Nyron distinguishes:

```text
HumanRequest != NotificationEffect
```

Creating HumanRequest:
- canonical Human Interaction mutation;
- normally a mediated `CANONICAL_COMMAND` / `HUMAN_INTERACT` authorized operation;
- no external EffectOperation required merely to create the canonical request.

Dispatching a notification externally:
- email/Slack/SMS/push/provider action;
- ordinary Capability check;
- ResourceLease if a managed session is required;
- EffectOperation when consequential/crash-ambiguous under D-004/D-008.

A failed notification dispatch does not automatically cancel the HumanRequest.

A delivered notification does not prove the human saw, understood or responded to the HumanRequest.

Multiple channels may notify about the same `human_request_ref`; this does not create multiple HumanRequests.

---

## 14. Replay, Crash, Duplicate and Late Response Semantics

### 14.1 Crash before HumanRequest commit

No canonical HumanRequest exists. A retry of the same creation identity may safely attempt creation again.

### 14.2 Crash after HumanRequest commit before notification

The request exists. Notification may later be dispatched using independent external-effect identity.

### 14.3 Crash after external response receipt before HumanResponse commit

Transport receipt is not canonical truth. The external ingress mechanism may redeliver. Stable deduplication ensures at most one accepted canonical response for the same external response identity.

### 14.4 Crash after HumanResponse commit before downstream EventDelivery

Replay of durable Human Interaction events repairs downstream event propagation. HumanResponse is not recreated.

### 14.5 Duplicate response

Same stable response identity + same semantic payload = idempotent duplicate.

Same stable response identity + different payload = identity conflict, fail closed.

Different response identities from the same principal are evaluated by the pinned ResponsePolicyRevision.

### 14.6 Late response

A response received after `SATISFIED`, `EXPIRED`, `CANCELLED` or `SUPERSEDED` does not alter the terminal decision unless the pinned policy explicitly defines a post-terminal amendment contract.

Default v0.1 behavior: late responses are rejected from satisfaction and may be retained only as non-authoritative ingress/audit evidence according to data policy.

---

## 15. Stale Attempt and Stale Request Interaction

Attempt freshness and HumanRequest freshness are distinct.

A HumanRequest may outlive the Attempt that caused its creation.

When an Attempt becomes stale/superseded/cancelled:
- Runtime old Attempt immediately loses commit/resume/new-effect authority;
- Human Interaction request does not automatically disappear unless an authorized cancellation/supersession policy commands it;
- a later human response may remain valid Human Interaction history;
- that response cannot resume the stale Attempt because Runtime owns and fences resume authority;
- a replacement Attempt may use the prior HumanDecisionEvidence only if the receiving policy explicitly permits it and validates scope/applicability.

No generic rule says `same Run` or `same workflow` automatically transfers human approval to a replacement Attempt.

Approval evidence should bind to the narrowest semantically relevant subject scope. If the original protected action was Attempt-specific, replacement requires fresh approval unless policy explicitly declares approval reusable across replacement.

---

## 16. Manual Recovery Review Boundary

Recovery Owner may request human review by creating or requesting creation of a HumanRequest.

Example:

```text
ReconciliationCase UNKNOWN subject
-> Recovery decides manual review required
-> CreateHumanRequest(subject_refs = case_ref + subject_ref)
-> authenticated HumanResponse / HumanDecisionEvidence
-> Recovery consumes evidence
-> Recovery commits RecoveryDisposition
-> subject Owner independently consumes evidence/proposal where applicable
```

A human statement such as "treat as resolved" is not automatically evidence that an UNKNOWN external effect objectively completed, stopped or never happened.

The distinction is mandatory:
- **manual response evidence** — owned by Human Interaction;
- **Recovery policy disposition** — owned by Recovery;
- **subject business-state transition / conflict clearance** — owned by the subject Owner.

`ReconciliationCase.RESOLVED` or a manual response may permit administrative closure according to Recovery policy, but cannot by itself create Effect/Resource/Capability conflict-clearance truth.

---

## 17. Sensitive Response, Provenance and Reference Handling

Human responses may contain secrets, personal data, approvals, free text or business-sensitive values.

Architecture rules:
1. canonical state should store only the minimum semantic payload required for correctness;
2. large/sensitive payloads may be placed in protected durable value storage and referenced by `value_ref`/content hash;
3. logs, telemetry and UI projections must not automatically duplicate sensitive response content;
4. authentication/authorization evidence should be referenced rather than copied broadly across subsystems;
5. downstream Events should prefer semantic result + references over full raw response payload;
6. access to response payloads is subject to ordinary Capability/Owner access control;
7. audit provenance must preserve who/which principal responded, under which authority evidence and to which exact request contract, without implying that display metadata is identity authority;
8. retention/redaction policy may restrict stored sensitive payload, but it must not destroy evidence required to correctly interpret durable committed history unless an explicit cryptographic/redaction contract preserves the necessary semantics.

This candidate does not define a full privacy/secret-storage subsystem.

---

## 18. Cross-Owner Contracts

### 18.1 Runtime -> Human Interaction

Commands:
- `CreateHumanRequest`
- `CancelHumanRequest`
- `SupersedeHumanRequest`

Queries:
- `GetHumanRequest`
- `GetHumanResponse`
- `GetHumanDecisionEvidence`

Events consumed by Runtime:
- `HumanRequestCreated`
- `HumanResponseAccepted`
- `HumanRequestSatisfied`
- `HumanRequestExpired`
- `HumanRequestCancelled`
- `HumanRequestSuperseded`

Runtime does not mutate HumanRequest/HumanResponse directly.

### 18.2 Capability Authority <-> Human Interaction

Capability Authority may emit/return:
- `REQUIRES_APPROVAL` with protected subject/scope requirement.

Human Interaction provides:
- `HumanDecisionEvidence` Query/Event evidence.

Capability Authority independently evaluates whether the evidence is valid, sufficiently scoped and still applicable under current pinned policy.

Human Interaction does not issue CapabilityGrant.

### 18.3 Recovery <-> Human Interaction

Recovery may Command/Proposal:
- create manual-review request;
- cancel/supersede obsolete review request.

Human Interaction emits response/decision evidence.

Recovery owns resulting ReconciliationCase scheduling/disposition.

### 18.4 External Interface -> Human Interaction

External ingress supplies:
- authenticated source/principal evidence;
- normalized external payload;
- stable external response identity;
- ingress route identity;
- schema/transport validation evidence.

Human Interaction Owner performs final canonical response acceptance and binding.

### 18.5 Workspace/Project/Product Policy -> Human Interaction

Policy Owner supplies pinned policy references/evidence for:
- who may respond;
- role/selector membership;
- quorum/approval rules where policy-owned;
- request routing/visibility;
- approval reuse/validity scope.

Human Interaction must not silently own mutable project/workspace policy simply because it evaluates a request against it.

---

## 19. Canonical vs Derived Human Interaction State

Canonical:
- HumanRequest identity/contract/state;
- accepted HumanResponse records;
- request-response bindings;
- evidence references required to interpret accepted response;
- terminal request transition;
- canonical aggregate HumanDecisionEvidence when used by other Owners;
- explicit cancellation/supersession relationships.

Derived/reconstructible:
- UI inboxes;
- unread/read markers unless a product contract explicitly makes them canonical;
- pending-request dashboards;
- reviewer display names/avatars cached from identity providers;
- notification delivery summaries;
- human-friendly status strings;
- search indexes;
- reminder schedules unless a separate scheduler/policy makes them canonical;
- counts/progress projections derivable from canonical responses and policy.

A derived view MUST NOT become the sole authority for whether a request is approved, denied, expired or satisfied.

---

## 20. Human Interaction Invariants

### HI-INV-01 — Single Owner
`HumanRequest`, `HumanResponse` and canonical HumanDecisionEvidence have exactly one authoritative Human Interaction Owner.

### HI-INV-02 — Human Approval Is Not Runtime Primitive
No Human Approval/Reviewer/Form/Dialog taxonomy is added to Kernel or Runtime primitive types.

### HI-INV-03 — No Second Wait Engine
Waiting for humans uses ordinary Runtime Suspension / Subscription / EventDelivery / resume semantics.

### HI-INV-04 — Response Is Not Approval By Definition
HumanResponse is a generic authenticated response fact; approval/deny is one response contract vocabulary.

### HI-INV-05 — Authentication Evidence Required
An external response cannot become canonical HumanResponse without trusted authentication evidence according to the ingress policy.

### HI-INV-06 — Authorization Is Distinct From Authentication
Authenticated identity alone does not prove permission to satisfy a request.

### HI-INV-07 — Exact Request Binding
Every accepted HumanResponse binds to exactly one immutable HumanRequest contract.

### HI-INV-08 — Stable Duplicate Handling
Duplicate transport delivery cannot create duplicate canonical response facts or double-count quorum.

### HI-INV-09 — Identity Conflict Fails Closed
Reusing a stable request/response identity with conflicting semantic payload is rejected.

### HI-INV-10 — Terminal Request Is Prospective Authority Boundary
EXPIRED/CANCELLED/SUPERSEDED/SATISFIED prevents default future satisfaction mutation but does not erase prior history.

### HI-INV-11 — Supersession Is Explicit
A newer request does not implicitly supersede an older one.

### HI-INV-12 — Capability Owns Grant Truth
Human approval evidence never directly becomes CapabilityGrant or overrides higher-priority deny policy.

### HI-INV-13 — Runtime Owns Resume Authority
A valid response cannot resume a stale/non-current Attempt.

### HI-INV-14 — External Notification Is Separate Effect
HumanRequest creation and external notification dispatch are distinct canonical/external operations.

### HI-INV-15 — Recovery Does Not Gain Subject Truth
Manual recovery response/evidence does not let Recovery rewrite foreign subject truth or fabricate Effect/Resource clearance.

### HI-INV-16 — Late Response Does Not Rewrite Terminal Decision By Default
Late responses are non-satisfying unless the pinned policy explicitly defines amendment semantics.

### HI-INV-17 — Multi-Responder Counting Is Deterministic
Quorum/role aggregation cannot depend on nondeterministic transport ordering or duplicate delivery.

### HI-INV-18 — Policy References Do Not Transfer Ownership
Human Interaction may consume Workspace/Project/Product policy references without owning those policy state classes.

### HI-INV-19 — Historical Replay Does Not Re-Prompt
Replay consumes committed HumanRequest/HumanResponse history and does not contact humans again merely to reconstruct past canonical truth.

### HI-INV-20 — Sensitive Payload Is Not Telemetry By Default
Human response content must not be copied into logs/telemetry/projections as a correctness shortcut.

---

## 21. Required Implementation Gates

### HI-G1 — Canonical identity and lifecycle
Before implementation can claim Human Interaction support:
- stable HumanRequest/HumanResponse identities exist;
- creation/response dedupe conflict rules are tested;
- request terminal transitions are owner-local canonical facts.

### HI-G2 — External response ingress
Before external human responses can be accepted:
- ingress route identifies Human Interaction as target Owner;
- authentication policy exists;
- authorization/policy decision path exists;
- schema validation exists;
- stable dedupe identity exists;
- conflicting duplicate identity fails closed.

### HI-G3 — Runtime wait/resume
Before Modules may wait on humans:
- Human Interaction canonical events integrate with frozen Subscription/EventDelivery;
- lost-event race is prevented by Runtime cursor/watermark semantics;
- duplicate event propagation is safe;
- stale Attempt response cannot resume old Continuation.

### HI-G4 — Capability approval loop
Before `REQUIRES_APPROVAL` can authorize protected operations:
- protected subject/scope binding is machine-checkable;
- HumanDecisionEvidence is canonical and referenceable;
- Capability re-evaluation validates evidence scope/applicability;
- approval cannot override higher-priority deny;
- reuse across replacement/Attempt boundaries is explicitly policy-defined.

### HI-G5 — Multi-responder policy
Before quorum/role approval is advertised:
- immutable ResponsePolicyRevision exists;
- principal uniqueness/counting semantics are deterministic;
- role/selector evidence comes from authoritative policy Owner;
- concurrent responses are replay-safe.

### HI-G6 — Recovery manual review
Before manual reconciliation workflows are advertised:
- manual response evidence is separate from RecoveryDisposition;
- subject Owner retains final subject-state authority;
- administrative Runtime closure and effect/resource conflict clearance remain distinct.

### HI-G7 — Sensitive data handling
Before production use with sensitive responses:
- protected payload storage/reference policy exists;
- telemetry/log redaction rules exist;
- authorization to retrieve response content is enforced;
- retention semantics preserve required canonical evidence.

---

## 22. Open Questions

These are implementation/design-followup questions and do not currently require changing frozen Module/Runtime/authority semantics.

1. Which future Workspace/Project/Identity subsystem owns principal, role and responder-selector policy references consumed by Human Interaction?
2. What exact common schema should represent authentication/authorization evidence across UI sessions, OAuth providers, signed webhooks and enterprise SSO?
3. Which approval-validity dimensions must be standardized in v0.1: subject hash, operation class, scope, amount/budget, Attempt, execution, expiry, policy revision?
4. Should HumanDecisionEvidence always be materialized canonically, or only when another Owner requires an aggregate machine-checkable result?
5. Which late-response audit facts are retained when a request is already terminal, especially for sensitive payloads?
6. Are reminder/escalation schedules owned by Human Interaction, Product policy or a generic timer/scheduler subsystem when they affect only notification timing rather than request truth?
7. What first-release responder policy envelope is required beyond single-responder approval: first-valid, N-of-M, unanimous or role-weighted quorum?
8. What exact contract permits approval reuse across Runtime replacement Attempts without accidentally transferring stale authority?

---

## 23. Architecture Finding Review

This candidate does **not** require modification of the Frozen Module Architecture Baseline, Runtime execution path, Capability/Resource/Effect ownership, Accounting/Recovery ownership, or D-008 ingress boundary.

No Architecture Finding is raised by this design.

---

## 24. Candidate Result

This candidate closes the NYRON-D-009 design scope by assigning Human Interaction canonical ownership, defining HumanRequest/HumanResponse lifecycle and evidence semantics, preserving external authentication boundaries, integrating approval with Capability re-evaluation, reusing frozen Runtime suspension/resume machinery, separating internal request truth from notification effects, and preserving Recovery/foreign-owner authority boundaries.

Status remains **CANDIDATE — FOR LEAD REVIEW**. Only the Nyron Lead Design Authority may integrate or freeze it.