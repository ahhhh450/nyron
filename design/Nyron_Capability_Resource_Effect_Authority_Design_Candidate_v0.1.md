# Nyron Capability / Resource / Effect Authority Design Candidate v0.1

Task ID: `NYRON-D-004`
Status: **CANDIDATE — FOR INDEPENDENT REVIEW**
Authority: Lead-integrated delegated design candidate; not frozen
Depends on:
- `Universal_Runtime_Module_Design_Report_v0.1.md` — FROZEN MODULE ARCHITECTURE BASELINE
- `amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md` — FROZEN MODULE ARCHITECTURE AMENDMENT
- `Nyron_Overall_System_Architecture_v0.1.md` — DRAFT

## 1. Purpose

This design defines the canonical ownership, authority, lifecycle, fencing, UNKNOWN semantics and cross-owner contracts among Capability Authority, Resource Manager, Effect Authority / Effect Tracker, and the Module Host mediation boundary.

Core goal: Modules may safely interact with the external world without encoding product-node taxonomy, provider taxonomy, sandbox technology, or external state machines into the Kernel.

## 2. Scope / Non-Scope

In scope:
- CapabilityType / CapabilityGrant
- capability policy and scope
- mediated effect boundary
- EffectOperation and effect fencing
- Resource / ResourceLease / affinity
- Module Host trust boundary
- Canonical Command authority
- Human Interaction authority boundary
- Provider / Browser / Process / Workspace mappings
- Runtime cross-owner contracts
- crash / UNKNOWN semantics
- Accounting interface boundary

Out of scope:
- Runtime scheduling/readiness/retry policy
- Graph/Composite topology
- full Accounting/Budget lifecycle
- full Reconciliation policy
- Product Node taxonomy and Human Approval UX
- concrete Docker/VM/WASM isolation choice
- provider-specific APIs
- full secrets/credential system

## 3. Three Canonical Owners

### Capability Authority
Owns `CapabilityGrant` canonical truth and capability policy decisions. It issues, revokes, expires and narrows grants. It does not own resources, effects, Runtime attempts, budgets or external operations.

### Resource Manager
Owns `Resource` and `ResourceLease` canonical truth. It manages provision/discovery, lifecycle, hydration, affinity, lease allocation/release/revoke/expiry, external resource loss and orphan/UNKNOWN handling. It does not own permission, workflow authority, external-effect truth or budget.

### Effect Authority
Owns `EffectOperation` canonical truth. It manages durable effect intent, dispatch tracking, external identity, cancellation/fencing, completion, UNKNOWN and recovery handoff. It does not own CapabilityGrant, ResourceLease, BudgetReservation or current-attempt selection.

These remain separate because they answer different questions:
- Capability: what are you allowed to do?
- Resource: which managed stateful handle can you use?
- EffectOperation: what may actually have happened in the external world?

## 4. Ownership Map

| Canonical state | Owner |
| --- | --- |
| CapabilityType definition | Capability Registry / Authority domain |
| CapabilityGrant | Capability Authority |
| Resource / ResourceLease | Resource Manager |
| EffectOperation | Effect Authority |
| Activation / Run / current Attempt | Runtime |
| BudgetReservation | Accounting |
| ReconciliationCase | Recovery |
| Human Request / Response | Human Interaction Owner (future design) |
| ModuleDefinition | Module Registry |
| subsystem business state | respective target Owner |

Module Host owns none of these canonical truths. It may hold transient execution state and Kernel-issued proxies but cannot become a durable semantic Owner.

Runtime may request grants, leases, effect creation/revocation and lease release/revocation, but cannot directly mutate their canonical state.

## 5. CapabilityType

`CapabilityType` is authority vocabulary, not a concrete grant.

Candidate definition:

```text
CapabilityTypeDefinition
- capability_type_ref
- version
- scope_schema_ref
- operation_schema_ref?
- compatible_effect_classes[]
- conflict_domain_schema?
- metadata
```

Kernel treats capability identity as opaque. Breaking changes to authority meaning, scope or operation semantics require a new version. CapabilityTypes are registered and validated without adding Kernel primitives.

Initial vocabulary includes MODEL_INVOKE, WORKSPACE_READ, WORKSPACE_WRITE, PROCESS_EXEC, NETWORK_ACCESS, EVENT_SUBSCRIBE, HUMAN_INTERACT and CANONICAL_COMMAND. Future types such as BROWSER_CONTROL, TOOL_INVOKE and REMOTE_EXEC may be registered without Kernel taxonomy changes.

## 6. CapabilityGrant

```text
CapabilityGrant
- grant_ref
- capability_type
- activation_ref
- run_ref
- attempt_seq
- fencing_token
- scope
- issued_by
- policy_decision_ref?
- issued_at
- not_before?
- expires_at?
- state
- revocation_authority[]
```

Grant properties:
- Activation-bound
- Run-bound
- Attempt-bound
- fencing-bound
- scope-bound
- validity-bound
- revocable
- non-transferable

A Grant being recorded ACTIVE is not sufficient to permit an effect. The actual mediated boundary revalidates current Attempt, current fencing token, Grant state, scope and any applicable ResourceLease.

Stale Attempt authority fails immediately at the boundary even if asynchronous revoke propagation is not yet processed.

Replacement Attempts receive new Grants; they never inherit the old Attempt's Grant.

Scope is immutable per Grant. Narrowing is performed by revoking the old Grant and issuing a new narrower one. Scope widening requires a new authorization decision.

Grant transfer is forbidden. Delegation, where allowed, requires an Authority-issued new scoped Grant.

## 7. Policy / Grant Flow

```text
ModuleDefinition declares required capability types
→ Runtime derives concrete request
→ Capability Authority evaluates applicable policy intersection
→ GRANTED / DENIED / REQUIRES_APPROVAL
→ CapabilityGrant if granted
```

Module requirements are declarations, not authorization.

Applicable policy may include immutable execution context, workflow policy, project/workspace policy, system security policy, user approval evidence, Runtime request and dynamic restrictions.

Final scope is the legal intersection of applicable policies; lower-level policy cannot widen higher-level restrictions. Human approval does not override system-security deny.

If approval is required, the Authority returns a machine-readable decision. Human approval becomes evidence for a later re-evaluation; it is not fabricated by the Capability Authority.

## 8. Scope Model

All scope must be explicit, bounded, machine-checkable, default-deny, auditable and support narrowing/subset checks. Scope must not rely on hidden Module state or Module-controlled expansion.

Examples:
- Workspace: workspace_ref, path containment, READ/WRITE, symlink policy
- Network: protocol, destination/domain class, optional ports
- Model: provider/model/endpoint restrictions
- Canonical Command: target_owner_ref, allowed_command_types, target scope

Budget and monetary/token quota authority remain Accounting concerns, not Capability authority.

## 9. Mediated Effect Boundary

A mediated effect boundary is where pure internal execution is about to cross into a controlled operation that may change, trigger, consume, observe or depend on external/foreign canonical state.

Each operation independently answers:
1. Does it require Capability?
2. Does it require a Resource?
3. Does it require an EffectOperation?

These are not a fixed bundle.

Typical mapping:
- pure calculation: none
- workspace read: Capability; Resource optional; usually no EffectOperation
- workspace write: Capability; usually Resource; EffectOperation
- process start: Capability + EffectOperation
- model invoke: Capability; provider-session Resource optional; EffectOperation
- safe stateless observation: Capability; usually no EffectOperation
- non-idempotent network mutation: Capability + EffectOperation
- browser DOM read: browser authority + Browser Session; usually no EffectOperation
- consequential browser action: Capability + Browser Session + EffectOperation
- canonical command: Capability + target command record; usually no extra EffectOperation
- internal Human Request creation: Capability + canonical Human Request; external notification dispatch additionally uses EffectOperation

## 10. EffectOperation

Effect Authority owns the lifecycle. Kernel Foundation provides canonical persistence, owner enforcement, transaction/fencing primitives and causal/replay foundations.

```text
EffectOperation
- operation_ref
- activation_ref
- run_ref
- attempt_seq
- fencing_token
- effect_class
- state
- capability_grant_ref?
- additional_capability_grant_refs[]?
- resource_ref?
- resource_lease_ref?
- external_operation_ref?
- external_idempotency_key?
- caused_by_ref
- external_ack_ref?
- completion_evidence_ref?
- observed_started_at?
- observed_completed_at?
- outcome?
```

Authoritative states, including frozen Amendment 001:

```text
PREPARED
ACTIVE
REVOKE_REQUESTED
FENCED
COMPLETED
UNKNOWN
```

`PREPARED` means a durable operation identity and dispatch intent exist, but is not evidence that the external effect was dispatched, accepted, started, completed or rejected.

Expected sequence:

```text
validate request shape
→ commit PREPARED EffectOperation
→ revalidate Grant / Attempt / fencing / scope / applicable lease
→ external dispatch
→ record acknowledgement/evidence
→ ACTIVE or COMPLETED
```

If a crash occurs after dispatch but before ACTIVE/COMPLETED is committed, recovered PREPARED does not mean "not dispatched". Recovery must inspect reliable external identity/evidence; otherwise transition to UNKNOWN and Reconciliation. Blind retry of an uncertain non-idempotent PREPARED operation is forbidden.

Provider timeout is not automatic failure. If acceptance cannot be confirmed, history is UNKNOWN.

## 11. Effect Fencing / Attempt Replacement

When Runtime commits `R2 replaces R1`:
- R1 canonical-commit authority immediately ends.
- R1 new-effect authority immediately ends.
- existing R1 external effects do not magically stop.

Effect Authority handles existing R1 effects:

```text
ACTIVE → REVOKE_REQUESTED
→ confirmed stopped → FENCED
→ cannot confirm → UNKNOWN
```

Resource Manager revokes R1 leases; future use is rejected by fencing mismatch even if the external resource still exists.

R2 must not receive a conflicting side-effect Grant until durable conflict-clearance evidence exists. If the old effect is UNKNOWN, conflicting authority is denied by default.

Non-conflicting effects may proceed concurrently when capability scopes, resource leases and conflict-domain policy establish compatibility.

## 12. Resource

Resource is a Nyron-managed opaque stateful handle. It is not authority, Packet, immutable config, Workflow canonical truth, CapabilityGrant, BudgetReservation or arbitrary JSON.

```text
Resource
- resource_ref
- resource_type
- resource_owner_ref
- scope
- affinity
- state
- external_ref?
- hydration_profile?
- durability_semantics
- compatibility_descriptor?
```

Candidate lifecycle:

```text
PROVISIONING → AVAILABLE → DESTROYING → DESTROYED
                    ↘ LOST / ORPHANED / UNKNOWN where applicable
```

`LEASED` is not a Resource state; leasing is a separate ResourceLease lifecycle.

Resource creation should commit PROVISIONING before external creation/hydration, so the record does not falsely claim the external object exists. External loss must be proven; a connection failure alone is not sufficient to claim LOST.

Rehydration/recreation may preserve a logical resource_ref only if ResourceType policy can prove semantic continuity; otherwise a new resource_ref is created.

Typical Resources include Provider Session, Browser Session, Workspace Handle, Remote Job, Tool Session and managed persistent process/worker sessions.

## 13. ResourceLease

```text
ResourceLease
- lease_ref
- resource_ref
- lease_holder_ref
- activation_ref?
- run_ref
- attempt_seq
- fencing_token
- issued_at
- expires_at
- state
```

Frozen lifecycle states:

```text
ACTIVE
EXPIRING
REVOKE_REQUESTED
RELEASED
EXPIRED
UNKNOWN
```

ACTIVE means lease authority to use the handle, not permission to perform effects. Capability is still required.

Run/Workflow terminal state should proactively release outstanding leases. TTL/expiry is a fallback that terminates future lease authority; it is not an oracle that the external session/resource has stopped.

A Resource may remain AVAILABLE while an old Lease becomes EXPIRED. If detachment/ownership history cannot be confirmed, Lease becomes UNKNOWN and hands off to Recovery.

## 14. Resource Affinity

Affinity expresses preference among otherwise compatible Resources. It is distinct from hard compatibility.

Candidate structured concept:

```text
AffinityProfile
- compatibility_constraints
- reuse_preferences[]
- strength / priority
```

It may represent workflow/module/session/provider/project/workspace preferences without freezing an exhaustive enum.

Resource continuity can improve performance and preserve useful external session continuity, but must never be the sole source of Workflow semantic truth.

## 15. Module Host Trust Boundary

Module Host may serve as execution/isolation boundary, effect mediation point, capability adapter boundary, resource-handle broker and external-adapter invocation boundary. It need not be one physical process.

Module must not receive unrestricted filesystem, subprocess, socket/network, raw canonical DB/StateStore, bypass credentials or hidden durable semantic state.

Module-facing APIs such as `workspace.write`, `model.invoke`, `process.start` and `network.request` are broker/proxy surfaces. Host revalidates authority at the real external boundary.

Resource handles are proxies, not raw lifecycle ownership.

Architecture supports IsolationProfile claims without yet selecting Docker/VM/WASM/OS-process technology. Trusted builtin mode may exist, but trusted mode is not evidence of hostile-plugin isolation. Third-party hostile code requires real enforceable isolation before such support can be claimed.

Provider adapters may be trusted TCB components that hold controlled credentials and translate external IDs, but they do not own Runtime Attempt, Budget, or raw canonical mutation authority.

## 16. Canonical Command

Canonical mutation by a Module is mediated:

```text
Module
→ CANONICAL_COMMAND Capability
→ command gateway
→ Target Owner
```

Candidate envelope:

```text
CanonicalCommand
- command_ref
- command_type
- target_owner_ref
- payload_ref / payload_hash
- activation_ref
- run_ref
- attempt_seq
- fencing_token
- capability_grant_ref
- idempotency_key
- caused_by_ref
```

Sending requires current Grant, Attempt/fencing and scope validation. Target Owner retains final mutation authority. Acknowledgement is not proof of commit; the target canonical event is.

Target Owner deduplicates by command_ref. Reusing command_ref with different payload must be rejected.

Internal Canonical Commands normally do not need a separate EffectOperation. If the target Owner then performs an external effect, that external action receives its own EffectOperation.

## 17. Human Interaction Boundary

`HUMAN_INTERACT` grants authority to initiate/perform human-facing interaction; it is not the human response itself.

Human Request is canonical state owned by a future Human Interaction subsystem, not Capability/Resource/Effect/Module.

Creating an internal Human Request can be a mediated Canonical Command without an EffectOperation. External notification dispatch (email/Slack/etc.) is a separate external EffectOperation.

Human interaction does not inherently imply Suspension. A Module can create a request and complete, while a separate waiting Module can Suspended/Resume using the frozen Subscription/Event contract.

A human response begins as External Event, is authenticated/validated/bound by Human Interaction Owner, then becomes canonical response fact/event for Runtime consumption.

## 18. Provider / Browser / Process / Workspace Mapping

### Provider / Model
- Capability: MODEL_INVOKE
- Resource: Provider Session optional
- EffectOperation: each provider invocation by default
- Streaming: one ACTIVE operation over request lifetime; durable semantic chunks use normal output/event paths
- Timeout without external certainty → UNKNOWN
- cancel: ACTIVE → REVOKE_REQUESTED → FENCED if confirmed; otherwise UNKNOWN
- safe retry requires definitive old completion/fencing, provider idempotency, or policy that explicitly allows duplicate invocation

### Browser
- Browser Session is a Resource
- BROWSER_CONTROL may be a distinct registered CapabilityType; NETWORK_ACCESS may simultaneously restrict destinations
- DOM query/screenshot/local lookup usually no EffectOperation
- form submission, uploads, persistent downloads and externally consequential actions usually require EffectOperation
- every action that can independently retry/cancel/become UNKNOWN should have its own operation identity

### Process
- Process start is EffectOperation
- PID/process group is normally external_operation_ref, not automatically a Resource
- a long-lived reusable/leased process session may additionally be modeled as Resource
- Host must identify process groups, revoke/kill and confirm termination; parent-PID kill alone is insufficient
- inability to confirm → UNKNOWN
- PROCESS_EXEC does not implicitly grant filesystem/network authority to child processes

### Workspace
- static workspace_ref is not itself a Resource
- live mounted/mutable Workspace Handle may be a Resource
- reads require WORKSPACE_READ and usually no EffectOperation
- persistent writes require WORKSPACE_WRITE and should normally be tracked as EffectOperation
- file-system atomic rename is not a global transaction with Nyron canonical DB
- crash recovery may use file identity/hash/revision evidence; otherwise history remains UNKNOWN

## 19. Cross-Owner Contracts

Runtime → Capability Authority:
- Commands: RequestCapability, RevokeAttemptCapabilities, ReleaseCapability, RequestCapabilityNarrowing
- Queries: GetCapabilityGrant, ValidateCapability, ListAttemptCapabilities
- Events: CapabilityGranted/Denied/Revoked/Expired
- Proposal: CapabilityEscalationProposal

Runtime → Resource Manager:
- Commands: AcquireResource, ReleaseResourceLease, RevokeAttemptLeases, DestroyResource, RequestResourceHydration
- Queries: GetResource, GetLease, ValidateLease, FindCompatibleResource
- Events: ResourceAvailable/Lost/Unknown, LeaseGranted/Released/Expired/Unknown
- Proposal: ResourceReusePreference

Runtime/Host → Effect Authority:
- Commands: PrepareEffect, ReportEffectDispatch, ReportExternalAcknowledgement, CompleteEffect, RequestEffectRevoke, ReportRevokeResult, ReportEffectEvidence
- Queries: GetEffectOperation, ListAttemptEffects, CheckConflictClearance
- Events: EffectPrepared/Active/Completed/RevokeRequested/Fenced/Unknown/ScopeCleared

Attempt replacement is a Runtime-owned durable fact consumed independently by the three Owners. No cross-owner global transaction is required; correctness uses current-fencing validation, idempotent processing, replayable events and conflict-clearance barriers.

## 20. Crash / UNKNOWN Semantics

- CapabilityGrant committed before crash remains canonical but usability is revalidated against current Attempt/fencing/validity.
- External Resource created before canonical identity is an abnormal orphan/adoption case; do not silently claim ownership.
- Resource canonical identity may exist as PROVISIONING before external creation; restart retries/looks up/cancels idempotently or marks UNKNOWN.
- PREPARED EffectOperation is the normal durable pre-dispatch state and does not prove dispatch.
- Dispatch before durable operation identity is forbidden unless an adapter provides an equivalent durable external dedupe/recovery identity protocol.
- External completion with lost response → UNKNOWN until reliable evidence resolves it.
- revoke sent but unconfirmed is REVOKE_REQUESTED, not FENCED; unresolved becomes UNKNOWN.
- Host restart never restores old capability handles by memory; authority is revalidated from canonical state.
- Runtime crash does not imply external effects ended.
- provider callbacks are deduped against stable operation/external identities.

## 21. Accounting Boundary

Capability, EffectOperation, ResourceLease and BudgetReservation remain distinct canonical facts and owners.

An effect may require valid Grant, Lease and BudgetReservation simultaneously, but none owns the others.

Effect/adapter may produce durable usage facts consumed by Accounting. EffectOperation may be COMPLETED while BudgetReservation remains RECONCILING; EffectOperation may be UNKNOWN while budget remains RESERVED. NYRON-D-005 defines budget handling and reconciliation policy.

## 22. Product Extension Mapping

Future product nodes remain wrappers over generic mechanisms:
- Claude: MODEL_INVOKE + optional Provider Session + model EffectOperation
- Codex: MODEL_INVOKE + workspace/process/network capabilities + applicable Resources/Effects
- Browser: BROWSER_CONTROL/NETWORK_ACCESS + Browser Session + consequential browser EffectOperations
- Shell: PROCESS_EXEC + delegated workspace/network authority + Process EffectOperation
- File: WORKSPACE_READ/WRITE + optional Workspace Handle + write EffectOperations
- Human Approval: HUMAN_INTERACT + Human Request + optional external notification effect
- Agent: composed Modules/Composite, never AGENT Kernel primitive
- HTTP: NETWORK_ACCESS + optional connection/session Resource + mutating-request EffectOperation
- Tool: TOOL_INVOKE or underlying capabilities + optional Tool Session
- Remote Worker: REMOTE_EXEC/PROCESS/NETWORK + worker/session/remote-job Resources and Effects

## 23. Architecture Invariants

ARE-INV-01 — CapabilityGrant, Resource/ResourceLease and EffectOperation each have exactly one authoritative Owner.

ARE-INV-02 — CapabilityType is authority vocabulary; CapabilityGrant is permission; Module requirement is not authorization.

ARE-INV-03 — Capability, Resource and Packet remain distinct: authority, stateful handle and data respectively.

ARE-INV-04 — Resource existence, connectivity or caching never grants authority.

ARE-INV-05 — CapabilityGrant is Activation/Run/Attempt/fencing/scope/validity-bound and non-transferable.

ARE-INV-06 — Every actual mediated effect boundary revalidates current Attempt, fencing, Capability state/scope and applicable ResourceLease.

ARE-INV-07 — A stale Attempt cannot initiate new mediated effects or canonical-commit.

ARE-INV-08 — Attempt replacement terminates future authority but does not fabricate termination of already-started external effects; they must be completed, fenced or UNKNOWN.

ARE-INV-09 — Every long/async/non-idempotent/cancellable/crash-ambiguous external effect has durable EffectOperation identity before dispatch; PREPARED does not prove the effect occurred.

ARE-INV-10 — Every ResourceLease has bounded release/revoke/expiry paths; expiry only terminates future lease authority and does not fabricate external resource termination.

ARE-INV-11 — Unknown past external effect/resource/revoke history remains UNKNOWN and enters Reconciliation rather than being guessed.

ARE-INV-12 — Module/Host cannot bypass mediation through hidden durable semantic state, raw canonical DB, unrestricted filesystem, unrestricted subprocess or unrestricted network.

ARE-INV-13 — EffectOperation and BudgetReservation remain orthogonal canonical states, owners and lifecycles.

## 24. Open Questions

OQ-01 — Freeze exact CapabilityType version identity syntax (`capability_type_ref@version` vs identity including version).

OQ-02 — Overall/Workspace design must assign canonical ownership of Project Policy, Workspace Policy, User Security Policy and System Security Policy documents.

OQ-03 — Runtime/Effect integration must define the generic conflict-domain representation used for overlapping effects/grants.

OQ-04 — Decide whether BROWSER_CONTROL enters the initial authority vocabulary now or is registered later by browser integration. Either path requires no Kernel primitive change.

OQ-05 — Resource adoption provenance/security for externally discovered Resources may be detailed later.

OQ-06 — Product/External Interface design must define the Human Interaction Owner.

OQ-07 — NYRON-D-005 defines retry limits, backoff, deadlines, escalation, manual resolution and budget behavior during UNKNOWN.

## 25. Architecture Finding Resolution

The candidate originally surfaced one integration issue: the frozen Module baseline §19 listed EffectOperation states without a pre-dispatch state and called EffectOperation a "Kernel internal object".

Lead Design Authority resolved this through:

`design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`

The amendment explicitly adds PREPARED and clarifies that EffectOperation is Kernel-visible internal canonical state whose domain lifecycle is owned by Effect Authority, while Kernel Foundation provides generic persistence/ownership/fencing/causal primitives.

No other blocking Architecture Finding is currently open for this candidate.

## 26. Recommended Implementation Gates

ARE-GATE-0 — design freeze review: three-owner decomposition, Grant semantics, effect-boundary contract, PREPARED, Resource/Lease separation, R1→R2 fencing and Host boundary.

ARE-GATE-1 — Capability foundation: type registry, grant issuance, scope, attempt binding, non-transferability, revoke/expiry, stale-effect rejection.

ARE-GATE-2 — Resource foundation: at least one real Resource with provision/acquire/lease/release/revoke/expiry/crash recovery.

ARE-GATE-3 — EffectOperation foundation: at least one bounded mutation and one long/async effect; test PREPARED-before-dispatch, crashes on both sides of dispatch, completion, revoke and UNKNOWN.

ARE-GATE-4 — Replacement fencing: fault-inject R1→R2 and prove stale commit/effect rejection, old effect/lease fencing, conflicting R2 clearance barrier and non-conflicting concurrency.

ARE-GATE-5 — Module Host trust boundary: broker-only effects/resources, no raw DB, effect-boundary fencing; hostile third-party support may not be claimed without real physical isolation enforcement.

ARE-GATE-6 — Accounting/Recovery integration: BudgetReservation references, usage facts, Effect/Lease UNKNOWN, ReconciliationCase handoff, deadline/escalation.

## 27. Lead Integration Decision

Lead integration review: **PASS WITH ONE EXPLICIT FROZEN AMENDMENT**.

The candidate is ready for bounded independent consistency review. It is not yet frozen as a subsystem baseline.
