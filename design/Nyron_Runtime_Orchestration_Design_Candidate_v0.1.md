# Nyron Runtime Orchestration Design Candidate v0.1

Task ID: `NYRON-D-003`
Status: **CANDIDATE — FOR LEAD INTEGRATION REVIEW**
Authority: delegated design candidate; not frozen
Depends on:
- `Universal_Runtime_Module_Design_Report_v0.1.md` — FROZEN MODULE ARCHITECTURE BASELINE
- `amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md` — FROZEN MODULE ARCHITECTURE AMENDMENT
- `Nyron_Overall_System_Architecture_v0.1.md` — DRAFT system foundation
- `Nyron_Graph_Composite_Design_Candidate_v0.1.md` — execution-facing Graph/Composite candidate
- `Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md` — consumed only for Attempt replacement/fencing interfaces

## 1. Purpose

This document defines Runtime Orchestration semantics above the frozen Module execution contract.

Runtime owns execution admission, Packet-to-Delivery projection, Delivery readiness/binding, Activation creation, Run/Attempt lifecycle, retry/replacement/cancellation, suspension/resume orchestration, workflow convergence, deterministic Runtime replay, and the Runtime side of cross-owner coordination.

It does not redefine Graph topology, Module semantics, Capability policy, Resource lifecycle, EffectOperation lifecycle, Accounting settlement, Recovery adjudication, or product Node taxonomy.

The execution path remains:

```text
Packet -> Delivery -> Activation -> Run / Attempt
```

No Runtime rule in this candidate grants Module code authority to create Activations, schedule downstream Modules, choose retry policy, decide workflow convergence, directly mutate canonical state, or bypass Commit/Effect Fencing.

## 2. Scope and Hard Boundaries

### 2.1 Runtime-owned scope

Runtime Orchestration owns:
- workflow execution identity and admission;
- admitted immutable GraphRevision pinning;
- Runtime Packet identity and sequence;
- idempotent Packet -> Delivery projection;
- Delivery lifecycle and consumptive binding;
- readiness evaluation;
- immutable Activation creation;
- Run identity and current Attempt authority;
- retry, replacement and cancellation decisions;
- current-attempt fencing facts;
- Suspension/Continuation/Subscription/EventDelivery resume eligibility;
- FEEDBACK-cycle execution as ordinary repeated execution facts;
- Runtime workflow lifecycle and terminal-state determination;
- Runtime-owned crash recovery and replay;
- deterministic Runtime ordering rules;
- Runtime-side cross-owner Commands, Queries, Events and durable coordination facts.

### 2.2 Explicit non-scope

Runtime does not own:
- GraphRevision topology, Port, Edge, Composite or Composite materialization;
- ModuleDefinition or ModuleInstanceRevision semantics;
- CapabilityGrant policy or lifecycle;
- Resource or ResourceLease lifecycle;
- EffectOperation lifecycle or external-effect historical truth;
- BudgetReservation settlement, cost truth or quota accounting;
- ReconciliationCase policy, UNKNOWN adjudication or escalation policy;
- external ingress authentication/trust policy;
- user-facing Node/Loop/Branch/Join taxonomy;
- provider-specific retry rules hidden outside explicit Runtime policy;
- scheduler implementation technology, queue technology or worker topology.

When Runtime needs a foreign Owner to change canonical truth, it sends a Command or Proposal and consumes durable Event evidence. It never mutates that foreign state directly.

## 3. Canonical Ownership Map

| Canonical state class | Authoritative Owner |
| --- | --- |
| WorkflowExecution | Runtime Orchestration |
| ExecutionAdmission | Runtime Orchestration |
| Runtime Packet | Runtime Orchestration |
| Delivery | Runtime Orchestration |
| Activation | Runtime Orchestration |
| Run | Runtime Orchestration |
| RunAttempt / current-attempt pointer / Attempt fencing generation | Runtime Orchestration |
| Runtime CancellationRequest / TerminationDirective | Runtime Orchestration |
| Continuation for a Runtime Run Attempt | Runtime Orchestration |
| workflow-scoped Subscription / EventDelivery / resume-consumption fact | Runtime Orchestration, using Kernel durable event/replay primitives |
| GraphRevision / ModuleInstanceRevision / Port / Edge / CompositeRevision | Graph subsystem |
| ModuleDefinition@version | Module Registry |
| CapabilityGrant | Capability Authority |
| Resource / ResourceLease | Resource Manager |
| EffectOperation | Effect Authority |
| BudgetReservation / accounting facts | Accounting |
| ReconciliationCase / UNKNOWN recovery policy | Recovery |

The Kernel Foundation supplies identity, durable canonical record/event persistence, owner enforcement, owner-local transaction primitives, revision immutability, fencing primitives and causal/replay foundations. It does not absorb Runtime policy state machines merely because those records are Kernel-visible.

## 4. WorkflowExecution and ExecutionAdmission

### 4.1 WorkflowExecution

A `WorkflowExecution` is the stable Runtime identity for one admitted execution of exactly one immutable GraphRevision.

Candidate shape:

```text
WorkflowExecution
- execution_ref
- graph_revision_ref
- admission_ref
- runtime_policy_ref
- state
- created_event_ref
- terminal_event_ref?
- terminal_reason_code?
- caused_by_ref?
```

`execution_ref` never means Graph identity. Two executions of the same GraphRevision have distinct execution identities and distinct Runtime histories.

Runtime never resolves `graph_ref -> latest/current` for an existing execution.

### 4.2 ExecutionAdmission

Admission is the canonical boundary at which Runtime accepts an immutable executable definition plus immutable execution policy/configuration references.

Candidate shape:

```text
ExecutionAdmission
- admission_ref
- execution_ref
- graph_revision_ref
- runtime_policy_ref
- requested_inputs_ref?
- requested_by_ref?
- caused_by_ref?
- admitted_at_owner_order
- state
- denial_reason_code?
```

Admission requirements:
1. the exact `graph_revision_ref` resolves;
2. the revision is execution-eligible according to Graph subsystem evidence;
3. all immutable ModuleInstanceRevision/ModuleDefinition/config references required by the revision resolve;
4. Runtime policy reference is immutable/resolvable;
5. admission does not silently upgrade Graph, Module, Composite or config versions;
6. admission does not itself imply Capability, Resource or Budget approval.

Validated-but-unpublished GraphRevision may be admitted when the caller's higher-level policy permits, consistent with the Graph candidate. Runtime does not make publication status a correctness primitive.

Admission rejection creates no partial execution that can later accidentally run.

### 4.3 Execution state

Candidate execution states:

```text
ADMITTED
ACTIVE
WAITING
TERMINATING
COMPLETED
FAILED
CANCELLED
```

`ACTIVE` versus `WAITING` is canonical only if persisted as an execution state; implementations may instead derive it from canonical child facts. The terminal states and any transition into `TERMINATING` are canonical.

`WAITING` never means deadlock by itself. A suspended current Attempt waiting on a valid Subscription keeps the execution nonterminal.

## 5. Runtime Packet Model

Packet remains an immutable data fact.

Candidate Runtime fields:

```text
Packet
- packet_ref
- execution_ref
- graph_revision_ref
- source_kind
- source_ref
- source_port_ref?
- value_ref
- schema_ref
- source_packet_seq
- caused_by_ref
- created_event_ref
```

`source_packet_seq` is a durable Runtime-owner ordering fact allocated as part of the Packet's canonical commit. It is not wall-clock time and is never reconstructed from projector arrival order.

For Module output, Run terminal SUCCESS + output Packet manifests are committed atomically after durable output values exist and current-attempt fencing passes, exactly as required by the frozen Module baseline.

For workflow start, schedule, external event or human action, a Trigger Packet must exist before any Activation. There is no second `explicit activation` entry point.

The precise external/top-level Graph ingress mapping is an integration question with Graph/External Interfaces; Runtime requires that the accepted ingress mapping resolve deterministically to immutable GraphRevision execution endpoints before Delivery creation.

## 6. Packet -> Delivery Projection

Packet projection is an idempotent canonical projection over immutable GraphRevision Edge facts.

For every applicable Edge from the Packet's immutable source endpoint, Runtime creates the target-specific Delivery if and only if the uniqueness key does not already exist.

Frozen uniqueness remains:

```text
Delivery uniqueness =
(
  packet_ref,
  graph_revision_ref,
  edge_ref,
  target_port_ref
)
```

Frozen deterministic ordering remains:

```text
delivery_order_key =
(
  source_packet_seq,
  edge_ordinal,
  target_port_ordinal
)
```

The Graph candidate requires collision-free normative scope for the ordinals used by this key. Runtime treats those persisted ordinals as immutable definition facts and never substitutes UI order, database row order, traversal order or current Graph state.

Projection may execute zero, one or many times. A crash during fan-out is repaired by replay: existing Deliveries deduplicate; missing Deliveries are created.

A projection worker cursor, queue offset or scan watermark may be used as an optimization but is not correctness authority unless it is itself a canonical replay-safe owner fact. Delivery uniqueness is the primary correctness boundary.

## 7. Delivery Lifecycle

Delivery is immutable as a delivery fact except for its Runtime binding/consumption status.

Candidate state model:

```text
PENDING
BOUND
```

Non-consumptive `LATEST` Deliveries remain available as immutable history and need not transition to a consumed state.

For consumptive modes:
- `TRIGGER` consumes exactly once by exactly one Activation;
- `REQUIRED_NEXT` consumes exactly once by exactly one Activation.

A `BOUND` Delivery records the immutable `activation_ref` that consumed it.

A cancellation/termination may leave PENDING Deliveries permanently unbound; Runtime must not invent fake consuming Activations merely to clean them up.

Deletion/archival is storage policy only and must preserve replayable history while referenced.

## 8. Readiness and Atomic Activation Creation

Runtime is the sole Owner of readiness evaluation and Activation creation.

The four frozen input modes are unchanged:
- `TRIGGER`
- `REQUIRED_NEXT`
- `REQUIRED_LATEST`
- `OPTIONAL_LATEST`

All Activations are Trigger-driven.

For each target ModuleInstanceRevision, Runtime repeatedly evaluates the oldest pending Trigger Delivery by `delivery_order_key`.

Activation creation transaction:

```text
BEGIN Runtime owner-local canonical transaction
1. select oldest PENDING TRIGGER Delivery deterministically
2. verify execution is still allowed to create new Activations
3. verify target ModuleInstanceRevision remains pinned to admitted GraphRevision
4. verify REQUIRED_NEXT availability
5. bind deterministic oldest REQUIRED_NEXT Deliveries
6. snapshot REQUIRED_LATEST by deterministic latest delivery_order_key
7. snapshot OPTIONAL_LATEST similarly, or null
8. atomically mark consumptive Deliveries BOUND to one new activation_ref
9. create immutable Activation with exact bindings and trigger_delivery_ref
10. append canonical ActivationCreated event
COMMIT
```

Any failure rolls back all bindings and Activation creation.

Activation minimally pins:

```text
Activation
- activation_ref
- execution_ref
- graph_revision_ref
- module_instance_revision_ref
- trigger_delivery_ref
- input_bindings[]
- static_accounting_scope_ref
- created_event_ref
```

Activation is immutable. Retry, replacement and resume never rewrite Activation inputs.

## 9. Run and Attempt Identity

### 9.1 Run

A `Run` is the stable Runtime execution lineage for exactly one immutable Activation.

```text
Run
- run_ref
- activation_ref
- execution_ref
- current_attempt_seq
- fencing_generation
- state
- terminal_attempt_seq?
- terminal_event_ref?
```

Exactly one Run belongs to an Activation in v0.1. Multiple Attempts may occur under that Run.

### 9.2 RunAttempt

A `RunAttempt` is uniquely identified by:

```text
(run_ref, attempt_seq)
```

Candidate fields:

```text
RunAttempt
- run_ref
- attempt_seq
- fencing_token
- state
- started_event_ref?
- suspended_continuation_ref?
- failure_reason_code?
- replaced_attempt_seq?
- caused_by_ref
```

Candidate states:

```text
CREATED
ACTIVE
SUSPENDED
SUCCEEDED
FAILED
CANCELLED
SUPERSEDED
```

`SUCCEEDED`, `FAILED`, `CANCELLED` and `SUPERSEDED` are terminal for that Attempt identity.

`SUPERSEDED` means the Attempt has lost Runtime current-attempt authority. It does **not** mean its external effects have stopped, leases are released, accounting is settled, or historical ambiguity is resolved.

### 9.3 Current-attempt authority

Exactly one nonterminal Attempt can be current for a Run.

The authoritative current-attempt check is a Runtime canonical fact combining `run_ref`, `current_attempt_seq` and current fencing generation/token.

Commit Fencing checks this fact at canonical commit.

Effect Fencing additionally requires Capability/Effect/Resource Owners to validate the same current Attempt authority at actual mediated boundaries.

## 10. Retry, Replacement and Resume Are Distinct

### 10.1 Retry

Retry creates a **new Attempt** for the same Run and immutable Activation after the prior Attempt has reached a state from which Runtime policy permits another attempt.

Properties:
- same `run_ref`;
- same immutable `activation_ref` and input bindings;
- `attempt_seq = previous + 1`;
- new fencing token;
- new CapabilityGrants/ResourceLeases as applicable;
- no inheritance of old Continuation;
- no reuse of old Attempt authority.

A retry decision is Runtime-owned policy. Module `Failed(error)` is evidence about one Attempt, not permission to retry.

### 10.2 Replacement

Replacement creates a new Attempt **while the previous Attempt may still be active, suspended, orphaned or externally ambiguous**.

Replacement must commit atomically inside Runtime:

```text
old Attempt -> SUPERSEDED
Run.current_attempt_seq -> new attempt_seq
Run.fencing_generation -> next generation
create new RunAttempt(CREATED)
append AttemptReplaced event
```

At that commit boundary:
- old Attempt canonical-commit authority ends immediately;
- old Attempt authority to initiate new mediated effects ends immediately;
- old Continuation/Subscription resume authority ends immediately;
- existing old external effects do not magically stop.

Runtime then issues idempotent cross-owner revoke/cleanup Commands. D-004 Owners independently consume the durable replacement fact.

A replacement Attempt must not receive conflicting side-effect authority until Effect Authority/Resource Manager/Capability Authority provide the required durable conflict-clearance evidence. An old UNKNOWN effect blocks conflicting new authority by default according to D-004; Runtime does not override that policy.

### 10.3 Resume

Resume is neither retry nor replacement.

Resume:
- keeps the same `run_ref`;
- keeps the same `attempt_seq` and fencing token;
- keeps the original immutable Activation inputs;
- consumes exactly one valid EventDelivery against the current Subscription/Continuation;
- advances `resume_seq` through a new immutable Continuation if the Module suspends again.

`execute -> Suspended C1 -> resume(C1) -> Suspended C2 -> resume(C2)` remains one Attempt.

### 10.4 Scheduler redispatch is not retry

A transient worker claim, queue redelivery or scheduler wake-up does not by itself create a new Attempt.

If Runtime can prove an Attempt never crossed the Module execution boundary, the same `CREATED` Attempt may be dispatched again as an implementation retry of transport/worker acquisition.

Once execution may have begun, crash ambiguity must not be erased by silently re-running the same semantic Attempt. Runtime applies explicit retry/replacement/recovery rules and foreign-owner evidence.

## 11. Retry Policy

Runtime owns retry policy, but policy is pinned as immutable admission context rather than hidden in Module code or worker configuration.

Candidate `runtime_policy_ref` must be able to determine, at minimum:
- whether a Failed Attempt is retryable;
- retry count/limit;
- delay/backoff if semantically relevant;
- replacement eligibility;
- execution-level disposition after retry exhaustion;
- cancellation propagation behavior;
- whether non-conflicting branches may continue after a local terminal failure.

Exact policy schema is an implementation-gate dependency and may be a separate Runtime policy design if complexity grows. Observable retry behavior must not depend on mutable deployment defaults after admission.

Backoff timers are wake-up scheduling facts. Wall-clock wake timing may affect when progress happens, but must not reorder already committed Delivery/Activation semantics.

## 12. Cancellation and Termination

### 12.1 CancellationRequest

Runtime accepts canonical cancellation requests targeting at least:
- a whole `execution_ref`; or
- one `run_ref` / Activation lineage where policy allows scoped cancellation.

Candidate shape:

```text
CancellationRequest
- cancellation_ref
- target_ref
- scope
- reason_code
- caused_by_ref
- accepted_event_ref
```

Cancellation is prospective, not retroactive. Already committed Packets, Deliveries, Activations, Run outcomes and external facts remain history.

### 12.2 Cancellation effect on Runtime authority

When cancellation becomes effective for a current Attempt, Runtime atomically removes its future commit/resume/new-effect authority by transitioning it to `CANCELLED` or by superseding/fencing it under the cancellation transition.

Runtime then requests:
- Capability revocation;
- ResourceLease release/revocation;
- Effect revoke/fencing;
- Accounting handling required by the Accounting Owner;
- Recovery handling if any foreign subject becomes UNKNOWN.

Runtime does not claim those foreign transitions succeeded until their Owners emit durable evidence.

### 12.3 Execution termination drain

An execution enters `TERMINATING` when Runtime has accepted a terminal directive such as cancellation or unrecoverable failure.

While TERMINATING:
- no new ordinary Activations are created for the terminated scope;
- current Attempt commit/new-effect authority is removed as required;
- Runtime-owned pending wake-ups do not resurrect stale Attempts;
- cross-owner cleanup/revocation is driven idempotently;
- foreign UNKNOWN facts are delegated to Recovery rather than guessed.

An execution reaches final `CANCELLED` or `FAILED` only when Runtime's own work is closed and required foreign-owner blocking conditions have either cleared or Recovery has emitted an explicit durable disposition that permits Runtime closure. D-003 does not define that Recovery policy.

## 13. Suspension, Subscription, EventDelivery and Resume

Suspension is explicit durable state for the same Attempt.

On Module result:

```text
Suspended(subscription_spec, continuation)
```

Runtime validates and atomically commits, as one correctness unit:
- immutable Continuation;
- Subscription bound to current `run_ref + attempt_seq + fencing_token`;
- event cursor/causal watermark required by frozen baseline;
- Attempt state -> SUSPENDED;
- canonical suspension event.

Continuation is Attempt-bound and cannot be reused by retry/replacement.

Subscription is also Attempt-bound. When an Attempt becomes stale, cancelled, failed, succeeded or superseded, any remaining Subscription loses resume authority even if later matching events arrive.

Event matching produces canonical `EventDelivery` with stable uniqueness such as:

```text
(subscription_ref, source_event_ref)
```

The exact source Event owner may vary. Runtime consumes a durable canonical event identity/evidence, not a transient notification as truth.

Subscription completion and EventDelivery consumption for one resume must be atomic so duplicate notifications cannot resume twice.

Resume transaction must revalidate:
- Run current Attempt;
- fencing token;
- Subscription current/open status;
- Continuation identity and `resume_seq`;
- EventDelivery unconsumed status.

Then it atomically marks that EventDelivery consumed for the resume and records the resume invocation authority.

Real-time push is only a wake-up optimization. Crash/restart must replay Subscription/EventDelivery matching from durable event facts/cursors.

## 14. FEEDBACK Cycles

Runtime defines no Loop primitive.

A FEEDBACK Edge is treated exactly like any other Edge at execution time.

When an output Packet projects across FEEDBACK:

```text
new Packet
-> new Delivery
-> new Trigger readiness request
-> new Activation
-> same Activation creation rules
-> new Run
-> new Attempt lineage
```

Runtime does not:
- reuse a previous Activation;
- increment a hidden `loop_iteration` primitive;
- give FEEDBACK special ordering priority;
- alter activation modes;
- alter retry semantics;
- infer termination from FEEDBACK count.

Iteration limits, budgets and cancellation are expressed through Runtime/Accounting policy and ordinary canonical facts, not Graph FEEDBACK semantics.

Directed cycles containing FEEDBACK may execute indefinitely if policy permits. That is liveness behavior, not a validation error after Graph admission.

## 15. Branch and Join

Runtime defines no Branch or Join primitive.

Branching is ordinary Packet production plus Graph fan-out. If a Module produces Packets on multiple output Ports, each Packet projects through ordinary Edges.

Join/barrier/snapshot behavior is ordinary readiness over a target Module's input modes:
- TRIGGER requests Activation;
- REQUIRED_NEXT consumes one deterministic next Delivery;
- REQUIRED_LATEST snapshots deterministic latest;
- OPTIONAL_LATEST snapshots latest or null.

MULTI_SOURCE connection policy affects which Edges may target a Port, but Runtime does not perform hidden aggregation. Aggregation/merge semantics belong to an explicit Module.

## 16. Workflow Convergence and Terminal Criteria

Workflow completion is a Runtime fixpoint over canonical execution facts, not a static property of sink Nodes and not a product taxonomy.

### 16.1 Nonterminal conditions

An execution is nonterminal while any of the following can still legally create or change Runtime execution facts:
- a current Attempt is CREATED, ACTIVE or SUSPENDED;
- a valid Subscription can resume a current Attempt;
- a Packet has unprojected deterministic Deliveries;
- a pending Trigger Delivery may become ready because required inputs can still arrive from nonterminal Runtime work;
- a Runtime retry/replacement decision is pending under admitted policy;
- the execution is TERMINATING but required Runtime/foreign clearance has not completed.

### 16.2 Successful quiescence

Absent a terminal directive, Runtime may commit `COMPLETED` when it proves a durable quiescent fixpoint:
1. no nonterminal current Attempts exist;
2. no valid current-attempt Subscription can resume;
3. Packet -> Delivery projection is complete for all committed Packets;
4. no ready Activation can be created;
5. no Runtime-owned retry/replacement transition remains authorized/pending;
6. no remaining Runtime fact can legally produce a future Packet without new external ingress that would constitute a separate admitted execution/event path.

PENDING Deliveries that can never be consumed because their execution lineage is closed do not prevent completion; they remain historical facts.

### 16.3 Failure

A terminal Failed Attempt does not itself globally decide workflow failure. Runtime applies the immutable admitted runtime policy.

If policy produces an execution-level terminal failure directive, Runtime enters TERMINATING and later commits `FAILED` after drain/clearance.

This keeps Module failure evidence separate from workflow policy.

### 16.4 Waiting is not completion

A suspended current Attempt with a live Subscription prevents successful completion even if no worker is active and no ready queue entry exists.

### 16.5 Cycles

Cycles require no special convergence algorithm. The same canonical quiescence criteria apply. A FEEDBACK cycle that keeps producing Packets prevents quiescence naturally.

## 17. Crash Recovery and Replay

Runtime correctness must be reconstructible from canonical Runtime state, immutable definitions and durable foreign-owner evidence.

### 17.1 Packet/Delivery recovery

After crash:
- rescan committed Packets;
- project immutable GraphRevision Edges;
- deduplicate by Delivery uniqueness;
- create any missing Deliveries;
- rebuild derived indexes/queues.

Crash after Packet commit but before fan-out cannot lose downstream work.

### 17.2 Activation recovery

Because consumptive binding and Activation creation are one transaction:
- there is no canonical state where Delivery is consumed but Activation is absent;
- there is no valid duplicate consumer for one consumptive Delivery.

Ready queues are rebuilt from canonical PENDING Deliveries and immutable Port contracts.

### 17.3 Attempt recovery

Worker/process death is not automatically Module failure.

For a recovered current Attempt:
- `CREATED` with proven no execution dispatch may be scheduler-redispatched without a semantic retry;
- `SUSPENDED` is resumed only through its durable current Continuation/Subscription path;
- `ACTIVE` without terminal outcome is not guessed successful or failed;
- Runtime consults canonical Effect/Resource/Capability evidence and applies explicit retry/replacement policy;
- if required past facts are UNKNOWN, Runtime delegates to Recovery and does not blind-retry conflicting non-idempotent work.

### 17.4 Output commit crash windows

Frozen sequence remains:

```text
durable output value
-> Runtime canonical transaction:
   verify current Attempt
   commit Attempt/Run success
   create output Packet manifests
   append canonical events
-> Delivery projection
```

Crash before canonical transaction may leave orphan durable values but no output Packet.

Crash after the canonical transaction but before projection is repaired by Packet replay.

Late duplicate `Completed` from a stale/superseded/terminal Attempt is rejected and cannot create another Packet.

### 17.5 Suspension crash windows

Continuation + Subscription + Attempt SUSPENDED state must commit atomically or through an equivalent no-gap protocol. Recovery must not expose a Subscription whose Continuation is missing or a Continuation that can resume without a valid current Subscription path.

### 17.6 Rebuildable scheduler state

The following are derived/rebuildable unless explicitly made canonical for performance:
- ready queues;
- worker claims;
- in-memory priorities;
- pending Delivery counts;
- workflow progress percentages;
- projection cursors that are not required for correctness;
- cache/index state;
- wake-up notifications.

Deleting these must not change canonical interpretation.

## 18. Deterministic Ordering and Non-Semantic Ordering

### 18.1 Semantic deterministic order

Runtime uses:
- Packet `source_packet_seq` as committed owner-local sequence;
- `edge_ordinal` and concrete target input-port ordinal from immutable GraphRevision;
- `delivery_order_key` for Delivery ordering;
- oldest pending Trigger by that key;
- oldest REQUIRED_NEXT by that key;
- latest REQUIRED_LATEST/OPTIONAL_LATEST by that key;
- strictly increasing `attempt_seq` within one Run;
- strictly increasing `resume_seq` within one Attempt;
- stable Event identity/cursor ordering for Subscription matching.

Where two canonical transactions race, whichever owner-local commit order becomes durable is historical fact. Replay preserves that fact; Runtime does not pretend every physically possible concurrent history must be identical.

### 18.2 Explicitly non-semantic order

The following must not determine correctness:
- worker pickup order;
- thread/process scheduling;
- message bus delivery order;
- projector scan order;
- UI node position;
- database row order without a canonical key;
- wall-clock arrival time alone;
- queue implementation order;
- Composite traversal/flattening at Runtime;
- FEEDBACK edge label as execution priority.

Fairness and priority may affect latency. In v0.1 they are not correctness semantics unless a future immutable Runtime policy explicitly promotes them to semantic admission/scheduling facts.

## 19. Current-Attempt Fencing Protocol

Runtime is authoritative for current-attempt identity.

Any operation that can create canonical Run output or initiate mediated effects carries at least:

```text
execution_ref
activation_ref
run_ref
attempt_seq
fencing_token
```

Current-attempt validation must fail closed if the tuple no longer matches Runtime canonical truth.

Replacement/cancellation changes the Runtime fencing generation atomically with current-attempt transition.

A stale Attempt:
- cannot commit SUCCESS/FAILED as current Run outcome;
- cannot create output Packets;
- cannot create a new valid Continuation/Subscription;
- cannot resume;
- cannot initiate new mediated effects;
- cannot receive newly issued Attempt-bound Grants/Leases as though still current.

Foreign Owners may cache Runtime fencing evidence for performance only if stale cache cannot authorize an operation after authority is revoked. The actual external effect boundary must revalidate according to D-004/frozen Module rules.

## 20. Cross-Owner Contracts

Names below define required semantic interactions. D-004 names are consumed directly where already specified. Accounting/Recovery exact API names may be aligned by their owning designs without changing the ownership rules here.

### 20.1 Runtime -> Capability Authority

Commands:
- `RequestCapability`
- `RevokeAttemptCapabilities`
- `ReleaseCapability`
- `RequestCapabilityNarrowing`

Queries:
- `GetCapabilityGrant`
- `ValidateCapability`
- `ListAttemptCapabilities`

Events consumed:
- `CapabilityGranted`
- `CapabilityDenied`
- `CapabilityRevoked`
- `CapabilityExpired`

Runtime never writes CapabilityGrant state.

### 20.2 Runtime -> Resource Manager

Commands:
- `AcquireResource`
- `ReleaseResourceLease`
- `RevokeAttemptLeases`
- `DestroyResource`
- `RequestResourceHydration`

Queries:
- `GetResource`
- `GetLease`
- `ValidateLease`
- `FindCompatibleResource`

Events consumed:
- `ResourceAvailable`
- `ResourceLost`
- `ResourceUnknown`
- `LeaseGranted`
- `LeaseReleased`
- `LeaseExpired`
- `LeaseUnknown`

Runtime never marks a Resource/Lease released merely because its Attempt ended.

### 20.3 Runtime / Module Host -> Effect Authority

Commands:
- `PrepareEffect`
- `ReportEffectDispatch`
- `ReportExternalAcknowledgement`
- `CompleteEffect`
- `RequestEffectRevoke`
- `ReportRevokeResult`
- `ReportEffectEvidence`

Queries:
- `GetEffectOperation`
- `ListAttemptEffects`
- `CheckConflictClearance`

Events consumed:
- `EffectPrepared`
- `EffectActive`
- `EffectCompleted`
- `EffectRevokeRequested`
- `EffectFenced`
- `EffectUnknown`
- `EffectScopeCleared`

Runtime does not redefine PREPARED/ACTIVE/etc. lifecycle semantics.

### 20.4 Runtime -> Accounting

Required semantic interactions:
- request any reservation/authorization required before cost-bearing work;
- identify execution/Activation/Run/Attempt/static accounting affiliation precisely;
- report/forward canonical execution facts needed by Accounting;
- request release/cancellation handling where policy requires;
- consume durable grant/deny/limit/settlement/unknown evidence.

Runtime must not:
- settle BudgetReservation itself;
- rewrite actual usage/cost;
- infer budget release from Run termination;
- collapse EffectOperation and BudgetReservation.

Exact Command/Event vocabulary is owned by D-005 Accounting/Recovery design.

### 20.5 Runtime -> Recovery

Required semantic interactions:
- request reconciliation when Runtime progress/closure depends on an UNKNOWN foreign subject;
- provide subject identity, execution/run/attempt causal context and available evidence refs;
- consume durable resolution/escalation/clearance disposition facts;
- keep the affected Runtime transition blocked where safety requires until Recovery produces an admissible disposition.

Runtime must not:
- decide whether an UNKNOWN effect really succeeded or failed;
- invent Reconciliation retry/backoff/deadline policy;
- convert ESCALATED into guessed external truth.

Exact ReconciliationCase lifecycle and policy are D-005-owned.

### 20.6 Runtime-owned events emitted outward

At minimum, durable Runtime facts should be externally observable through stable events such as:
- `ExecutionAdmitted`
- `ExecutionTerminationStarted`
- `ExecutionCompleted`
- `ExecutionFailed`
- `ExecutionCancelled`
- `PacketCommitted`
- `DeliveryCreated`
- `ActivationCreated`
- `AttemptCreated`
- `AttemptStarted`
- `AttemptSuspended`
- `AttemptResumed`
- `AttemptFailed`
- `AttemptSucceeded`
- `AttemptReplaced`
- `AttemptCancelled`

Event names may be refined, but the facts required by foreign Owners must be durable/replayable and atomically linked to the Runtime transition they describe.

## 21. Canonical State vs Derived State

### 21.1 Canonical Runtime state

Canonical because losing or recomputing it could change committed-history meaning:
- execution identity and admitted GraphRevision;
- immutable runtime policy reference;
- Packet identity/value reference/source sequence;
- Delivery identity and consumptive binding;
- Activation exact input bindings;
- Run identity;
- Attempt identities, states, current-attempt pointer and fencing generation;
- retry/replacement/cancellation decisions once committed;
- Continuation/Subscription/EventDelivery resume-consumption facts;
- execution terminal directive and terminal result;
- causal references/events required by foreign Owners.

### 21.2 Derived Runtime state

Rebuildable projections/caches include:
- ready queue;
- list of runnable Module instances;
- pending Delivery counts;
- workflow progress percentage;
- UI branch/loop summaries;
- Composite progress;
- worker occupancy;
- queue backlog;
- indexes/materialized views;
- scheduler hints;
- transient wake-up state.

Derived state may be persisted for efficiency but cannot become the only correctness authority.

## 22. Runtime Reason Codes — Candidate

Runtime control flow must use machine-readable reason codes. Candidate additions:

```text
EXECUTION_ADMISSION_REJECTED
EXECUTION_NOT_CURRENT
EXECUTION_TERMINATING
ACTIVATION_NOT_READY
DELIVERY_ALREADY_BOUND
ATTEMPT_NOT_CURRENT
ATTEMPT_SUPERSEDED
ATTEMPT_CANCELLED
ATTEMPT_RETRY_EXHAUSTED
ATTEMPT_REPLACEMENT_BLOCKED
STALE_ATTEMPT_REJECTED
STALE_SUSPENSION
RESUME_EVENT_ALREADY_CONSUMED
SUBSCRIPTION_NOT_CURRENT
RUNTIME_CONVERGENCE_BLOCKED
FOREIGN_CLEARANCE_PENDING
```

Frozen Module reason codes remain authoritative where overlapping.

## 23. Runtime Architecture Invariants

### RT-INV-01 — One immutable definition per execution
Every WorkflowExecution pins exactly one immutable GraphRevision at admission and never resolves `latest/current` during that execution.

### RT-INV-02 — Packet-first execution
Every Activation is caused by a Trigger Delivery derived from a Packet; Runtime has no second explicit-activation execution path.

### RT-INV-03 — Idempotent Delivery projection
Packet -> Delivery projection is replay-safe and unique by `(packet_ref, graph_revision_ref, edge_ref, target_port_ref)`.

### RT-INV-04 — Deterministic Delivery order
Delivery ordering is determined by durable canonical facts and immutable Graph ordinals, never projector/worker/wall-clock order.

### RT-INV-05 — Atomic consumptive binding
Consumptive Delivery binding and Activation creation are one atomic Runtime correctness transition.

### RT-INV-06 — One consumer per consumptive Delivery
A TRIGGER or REQUIRED_NEXT Delivery is bound to at most one Activation.

### RT-INV-07 — Activation immutability
Activation pins exact Graph/Module instance/input bindings and is never rewritten by retry, replacement or resume.

### RT-INV-08 — One Run lineage per Activation
Each Activation has exactly one Runtime Run lineage; every Attempt belongs to exactly that Run and Activation.

### RT-INV-09 — One current Attempt
At most one Attempt is current for a Run; current-attempt authority is canonical and fenced.

### RT-INV-10 — New Attempt on retry/replacement
A semantic retry or replacement always creates a new `attempt_seq`; resume never does.

### RT-INV-11 — Resume preserves Attempt identity
Resume remains within the same current Attempt and requires its current Continuation/Subscription/EventDelivery authority.

### RT-INV-12 — Replacement revokes future old authority immediately
When replacement commits, the old Attempt immediately loses canonical-commit, resume and new-effect authority even though old external effects may still exist.

### RT-INV-13 — Foreign clearance is not fabricated
Runtime never equates Attempt replacement/cancellation/termination with Capability revocation, Resource release, Effect fencing, Accounting settlement or Recovery resolution.

### RT-INV-14 — Stale Attempts cannot create truth
A stale Attempt cannot commit Run terminal truth, output Packets, new Continuations/Subscriptions or new mediated effects.

### RT-INV-15 — Cancellation is prospective
Cancellation never deletes or rewrites already committed canonical history.

### RT-INV-16 — Suspension is durable
A Suspended current Attempt has explicit durable Continuation and Subscription state sufficient for crash-safe resume.

### RT-INV-17 — Event wake-up is replayable
Transient event notification is never correctness authority; resume eligibility is reconstructed from durable event/subscription facts.

### RT-INV-18 — FEEDBACK has no special Runtime semantics
FEEDBACK affects no Runtime ordering, readiness, Attempt identity or scheduling rule; each cycle traversal creates ordinary new execution facts.

### RT-INV-19 — No hidden Branch/Join/Loop primitive
Branch/join/cycle behavior arises from Module outputs, Ports, Edges and activation modes, not hidden Runtime product primitives.

### RT-INV-20 — Terminal state is canonical quiescence/directive result
Workflow terminal state is committed only from Runtime canonical facts plus required foreign-owner evidence; queue emptiness or lack of active workers alone is insufficient.

### RT-INV-21 — Unknown past remains unknown
Runtime never converts an ambiguous active/external past into guessed success/failure merely to enable retry or completion.

### RT-INV-22 — Runtime replay preserves committed history
Given the same canonical Runtime history and immutable definitions, crash/restart/replay reconstructs the same Deliveries, bindings, current Attempts, resumable waits and terminal interpretation.

### RT-INV-23 — Cross-owner mutation is mediated
Runtime changes foreign canonical state only through Command/Proposal to the owning subsystem and consumes durable Event evidence of committed results.

### RT-INV-24 — Scheduler implementation is not semantic authority
Worker claims, queue order, wake-up order and transient scheduling metadata cannot override canonical Runtime ordering or fencing.

## 24. Implementation Gates

### Gate R1 — Execution Identity and Admission
Implement:
- WorkflowExecution / ExecutionAdmission;
- immutable GraphRevision pinning;
- runtime policy reference pinning;
- admission rejection atomicity;
- no `latest/current` resolution.

Acceptance:
- two admissions of same GraphRevision create distinct executions;
- old execution remains resolvable after Graph retirement/archive;
- unresolved/non-executable GraphRevision cannot run.

### Gate R2 — Packet / Delivery / Activation
Implement:
- Packet canonical commit/sequence;
- idempotent fan-out projection;
- deterministic Delivery ordering;
- all four activation modes;
- atomic consumptive binding + Activation creation.

Acceptance:
- crash mid-fan-out repairs missing Deliveries without duplicates;
- two concurrent readiness workers cannot double-consume Delivery;
- LATEST selection is deterministic after replay.

### Gate R3 — Run / Attempt / Commit Fencing
Implement:
- Run lineage;
- attempt_seq/current pointer/fencing generation;
- Completed/Failed commit path;
- stale attempt rejection;
- retry versus replacement transitions.

Acceptance:
- concurrent old/new Attempts cannot both commit;
- late old Completed produces no Packet;
- replacement immediately removes old future authority.

### Gate R4 — D-004 Fencing Integration
Implement Runtime-side Commands/Events for:
- CapabilityGrant issuance/revocation;
- ResourceLease acquisition/revoke/release;
- EffectOperation PREPARED-compatible execution/fencing;
- conflict-clearance barrier.

Acceptance:
- stale Attempt cannot initiate effect;
- replacement does not falsely claim old effect stopped;
- conflicting replacement waits for durable clearance.

### Gate R5 — Suspension / Event Resume
Implement:
- atomic Continuation + Subscription commit;
- durable event cursor/watermark;
- EventDelivery deduplication;
- same-Attempt resume;
- stale suspension rejection.

Acceptance:
- event before/after realtime wake-up cannot be lost;
- duplicate event notification cannot double-resume;
- replacement prevents old continuation resume.

### Gate R6 — Cancellation / Convergence
Implement:
- CancellationRequest;
- TERMINATING drain;
- no-new-Activation closure;
- Runtime quiescence detection;
- workflow COMPLETED/FAILED/CANCELLED canonical terminal commits.

Acceptance:
- empty worker queue alone never completes suspended execution;
- FEEDBACK cycle can continue without hidden loop state;
- cancellation preserves prior history and prevents stale output commit.

### Gate R7 — Crash / Replay / Recovery Integration
Implement:
- rebuild of queues/indexes from canonical state;
- orphan active Attempt handling;
- D-005 Recovery blocking/clearance interface;
- chaos tests across every canonical transaction boundary.

Acceptance:
- restart after each injected crash point yields same canonical interpretation;
- PREPARED/UNKNOWN external ambiguity is never blind-retried by Runtime;
- no permanently lost Packet/Delivery/Subscription wake-up.

## 25. Open Integration Questions

### OQ-RT-01 — Top-level execution ingress mapping
Graph candidate leaves formal top-level Graph input/output Ports open. Runtime requires a deterministic immutable mapping from admitted start/external input to Trigger Packet source endpoints. This must be aligned with Graph/External Interfaces without adding an explicit-Activation bypass.

### OQ-RT-02 — Runtime policy schema/versioning
The exact immutable schema for retry limits, replacement eligibility, execution failure disposition, cancellation propagation and any semantic backoff needs a focused definition before Gate R3/R6 if not covered by D-001 integration.

### OQ-RT-03 — Accounting command/event names
D-003 defines only the Runtime ownership boundary. Exact reservation/settlement/limit/unknown contracts must align with NYRON-D-005 and must not move Accounting authority into Runtime.

### OQ-RT-04 — Recovery clearance contract
Runtime needs a durable Recovery-owned fact indicating when an UNKNOWN subject no longer blocks Runtime replacement/termination. D-005 must define that without fabricating the unknown external history.

### OQ-RT-05 — Event source ordering contract
Subscription matching requires a stable canonical Event identity/cursor/watermark. The generic contract for external-event canonicalization and cross-owner event stream ordering should be finalized with External Interfaces/System Foundation.

### OQ-RT-06 — Fairness / priority
v0.1 treats fairness and priority as non-semantic scheduling optimization. If product requirements later require priority to affect canonical choice among simultaneously ready work, it must become immutable admitted Runtime policy and receive deterministic tie-breaking rules.

## 26. Architecture Findings

**None.**

This candidate does not require reopening the frozen Module baseline, Amendment 001, the execution-facing D-002 Graph candidate, or D-004 ownership boundaries.

The open questions above are integration dependencies rather than contradictions: each can be resolved by the owning design without changing the Runtime invariants defined here.

## 27. Final Candidate Conclusion

Nyron Runtime Orchestration is the sole canonical Owner of execution admission, Packet/Delivery/Activation execution state, Run/Attempt authority, retry/replacement/cancellation, suspension/resume orchestration and workflow convergence.

Its central safety rule is that execution progress is a sequence of durable owner-controlled facts, not queue behavior: immutable GraphRevision admission creates a WorkflowExecution; Packets project idempotently into deterministic Deliveries; consumptive binding atomically creates immutable Activations; each Activation has one Run lineage with exactly one current fenced Attempt; retry/replacement create new Attempts while resume remains in the same Attempt; stale Attempts lose commit/resume/new-effect authority; FEEDBACK produces ordinary new execution facts; workflow terminal state is proven by canonical quiescence or a drained terminal directive rather than by worker inactivity.

Capability, Resource, Effect, Accounting and Recovery remain separate Owners. Runtime coordinates them through durable Commands/Events and never treats its own replacement/cancellation facts as proof that foreign effects, leases, budgets or unknown external history have resolved.

This document is a design candidate only. It does not freeze architecture and contains no implementation code.