# Nyron Accounting / Recovery Design Candidate v0.1

Task ID: `NYRON-D-005`

Status: **CANDIDATE — FOR LEAD REVIEW**

Authority: Delegated design candidate only. This document does not freeze architecture.

Depends on:
- `design/Universal_Runtime_Module_Design_Report_v0.1.md` — **FROZEN MODULE ARCHITECTURE BASELINE**
- `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md` — **FROZEN MODULE ARCHITECTURE AMENDMENT**
- `design/Nyron_Overall_System_Architecture_v0.1.md` — DRAFT system foundation
- `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md` — Lead-integrated candidate

---

## 1. Purpose

This candidate defines Nyron's Accounting and Recovery architecture for:

- `AccountingScope` identity and hierarchy;
- budget / quota / limit policy;
- `BudgetReservation` identity, authorization and settlement lifecycle;
- estimated versus actual usage;
- durable usage and charge facts;
- accounting deduplication and late corrections;
- accounting treatment of `EffectOperation`, `ResourceLease` and other UNKNOWN subjects;
- `ReconciliationCase` mechanics;
- retry, backoff, deadline, escalation and manual-resolution boundaries;
- crash/restart/replay behavior;
- orphan reservations, late provider billing and duplicate usage callbacks;
- cross-owner Commands / Queries / Events with Runtime, Effect Authority, Resource Manager and Human Interaction;
- canonical accounting truth versus derived reporting and projection.

The design preserves the frozen rule that:

> `EffectOperation` and `BudgetReservation` are orthogonal canonical facts and lifecycles.

Accounting answers whether consumption was authorized, reserved, recorded and settled. Effect Authority answers what external effect may actually have happened. Resource Manager answers what managed resource and lease existed. Runtime answers which Attempt is current and how Attempts are replaced. Recovery coordinates bounded investigation of unknown past facts but does not become a second workflow engine or a second owner of subject truth.

---

## 2. Design Boundaries

### 2.1 In scope

- Accounting Owner canonical state.
- Recovery Owner canonical state.
- static AccountingScope ancestry.
- budget policy revisions and enforcement semantics.
- hierarchical reservation atomicity within Accounting Owner.
- settlement and overrun handling.
- actual usage and provider charge facts.
- accounting reconciliation policy.
- generic ReconciliationCase mechanics and evidence handling.
- cross-owner recovery contracts.

### 2.2 Explicitly out of scope

This candidate MUST NOT redefine:

- Runtime Attempt creation, replacement, retry or cancellation lifecycle;
- `EffectOperation` state machine;
- `Resource` or `ResourceLease` state machine;
- Capability policy or capability grants;
- Graph / Composite containment semantics;
- Module execution ABI;
- product-facing UX or human-review presentation;
- provider-specific billing APIs;
- one physical database requirement.

If implementation requires changing any frozen Effect / Resource semantics to make Accounting convenient, implementation must stop and raise an Architecture Finding.

---

## 3. Canonical Owners

Nyron uses two distinct logical Owners in this domain.

### 3.1 Accounting Owner

Accounting Owner owns:

- `AccountingScope` canonical accounting identity and scope metadata;
- `BudgetPolicyRevision`;
- `BudgetReservation`;
- canonical `UsageFact` / `UsageAdjustmentFact`;
- canonical settlement decisions and accounting ledger facts;
- owner-local reservation counters / balances when they are canonical enforcement state.

Accounting Owner does **not** own:

- Runtime Attempt truth;
- `EffectOperation` truth;
- `ResourceLease` truth;
- Capability grants;
- Human Response truth;
- external provider truth before evidence is accepted as accounting fact.

### 3.2 Recovery Owner

Recovery Owner owns:

- `ReconciliationCase`;
- recovery attempt scheduling metadata;
- accepted recovery evidence references;
- bounded retry/backoff/deadline policy execution;
- escalation state;
- recorded recovery resolution/disposition.

Recovery Owner does **not** own the subject object's business truth.

A `ReconciliationCase(subject_ref = EffectOperation/X)` cannot directly change that EffectOperation. It may issue a Command or Proposal to Effect Authority with evidence. Effect Authority decides and commits the EffectOperation transition.

The same rule applies to BudgetReservation, ResourceLease and any future subject type.

### 3.3 No global atomicity assumption

Accounting Owner and Recovery Owner are logically separate authoritative Owners. Cross-owner convergence uses durable Commands, Events, stable identities, idempotency and reconciliation. A shared global database transaction is not assumed.

---

## 4. AccountingScope

### 4.1 Meaning

`AccountingScope` is the canonical accounting identity against which limits, quotas, reservations and actual usage are attributed.

It answers:

> Which statically defined accounting authority chain governs this execution?

It does not answer why the execution happened and does not derive membership from dynamic Packet provenance.

### 4.2 Identity

Candidate object:

```text
AccountingScope
- accounting_scope_ref
- graph_revision_ref
- definition_anchor_ref
- parent_accounting_scope_ref?
- scope_kind
- ancestry_hash
- created_from_definition_ref
- state
```

`definition_anchor_ref` identifies the immutable Graph / Composite placement or other immutable definition anchor from which the scope exists.

`accounting_scope_ref` MUST be stable for that immutable definition anchor. It MUST NOT be regenerated from runtime Packet lineage.

### 4.3 Static ancestry

The ancestry chain is derived from immutable Graph / Composite containment.

For a ModuleInstanceRevision:

```text
ModuleInstanceRevision.static_accounting_scope_ref
→ parent AccountingScope
→ parent AccountingScope
→ ...
→ root AccountingScope
```

The chain used for execution is fixed by the immutable GraphRevision / ModuleInstanceRevision pinned by the Activation.

Dynamic facts that MUST NOT change accounting membership include:

- Packet provenance;
- incoming Edge;
- triggering Module;
- previous Attempt;
- current worker;
- external provider callback source;
- runtime scheduling path.

### 4.4 Scope inheritance

A child scope may be governed by both its own policy and all ancestor policies.

Policy inheritance follows restriction composition:

- child policy may narrow an ancestor allowance;
- child policy may add a stricter hard limit;
- child policy may add additional dimensions;
- child policy may not widen a parent hard restriction;
- absence of a child override does not erase ancestor policy.

A scope hierarchy is authority topology, not an allocation ledger. Reservation accounting is performed explicitly against the complete applicable ancestor chain.

### 4.5 Scope changes

Graph / Composite definition changes that alter static containment produce new immutable definition references and therefore a new accounting affiliation for future Activations.

Historical Activations retain their originally pinned `accounting_scope_ref` and ancestry. Later policy or Graph changes MUST NOT rewrite historical attribution.

---

## 5. Budget Policy Vocabulary

### 5.1 BudgetPolicyRevision

Budget policy must be revisioned separately from immutable Graph topology so policy can evolve without rewriting GraphRevision history.

```text
BudgetPolicyRevision
- budget_policy_revision_ref
- accounting_scope_ref
- effective_from
- effective_until?
- dimensions[]
- enforcement_rules[]
- created_by_ref
- supersedes_ref?
```

A reservation pins the exact policy revision set used for its authorization decision.

### 5.2 Accounting dimension

Nyron does not freeze one universal unit such as USD or tokens.

Candidate dimension vocabulary:

```text
AccountingDimension
- dimension_ref
- unit
- measurement_semantics_ref
```

Examples:

- provider currency amount;
- model input tokens;
- model output tokens;
- compute seconds;
- GPU seconds;
- process runtime;
- API requests;
- storage bytes;
- egress bytes;
- project-specific quota units.

Dimensions are independently enforced unless an explicit conversion policy exists.

### 5.3 Limit / quota rule

```text
BudgetRule
- rule_ref
- dimension_ref
- limit_amount
- limit_kind
- window_spec?
- enforcement
- reserve_required
- overrun_policy
```

`limit_kind` may include:

- `LIFETIME_LIMIT`
- `FIXED_WINDOW_QUOTA`
- `ROLLING_WINDOW_QUOTA`
- `PER_ACTIVATION_LIMIT`
- `PER_RUN_LIMIT`

`enforcement`:

- `HARD` — future reservation must be denied when authorization would exceed the rule;
- `SOFT` — reservation may continue but a durable threshold / warning fact may be emitted.

A hard rule only controls future authorization. It cannot rewrite real usage already incurred.

### 5.4 Pricing and conversion

Pricing lookup, currency conversion and usage-to-charge conversion may be policy-controlled, but every conversion used for canonical settlement must pin the exact pricing / rate revision or external billing fact that justified it.

Derived dashboards may use current exchange rates; canonical historical settlement MUST NOT silently recompute old charges using current rates.

---

## 6. Estimate Versus Actual

Nyron distinguishes authorization estimates from historical usage facts.

### 6.1 UsageEstimate

`UsageEstimate` is the amount requested for authorization / reservation. It is not proof of actual consumption.

```text
UsageEstimate
- estimate_ref
- dimensions[]
- estimation_policy_ref
- based_on_ref[]
```

An estimate may be canonical as part of a reservation decision because it explains why authority was granted. It is still not historical usage truth.

### 6.2 UsageFact

`UsageFact` records durable evidence of actual consumption or charge.

```text
UsageFact
- usage_fact_ref
- accounting_scope_ref
- reservation_ref?
- operation_ref?
- resource_ref?
- run_ref?
- source_authority_ref
- source_fact_id
- dimension_ref
- quantity
- unit
- fact_kind
- usage_period?
- external_evidence_ref
- observed_at?
- ingested_at
- caused_by_ref?
```

Typical `fact_kind` values:

- `METERED_USAGE`
- `PROVIDER_CHARGE`
- `PROVIDER_REFUND`
- `MANUAL_ACCOUNTING_ADJUSTMENT`

The exact provider callback payload is evidence; Accounting commits a UsageFact only after the callback is authenticated, attributable and semantically accepted.

### 6.3 No fact rewriting

Committed UsageFacts are immutable.

If a provider later issues a correction, Nyron appends a `UsageAdjustmentFact` or new compensating UsageFact referencing the earlier fact. It does not edit the original quantity to make the ledger look clean.

```text
UsageAdjustmentFact
- adjustment_fact_ref
- adjusts_usage_fact_ref
- delta_dimensions[]
- reason
- evidence_ref
```

### 6.4 UNKNOWN is not zero

If Nyron cannot determine whether usage occurred, Accounting MUST NOT record usage = 0 merely because no bill is currently visible.

Unknown evidence remains Recovery evidence until a UsageFact can be justified, or until a policy disposition settles accounting exposure while explicitly preserving unknown external history.

---

## 7. BudgetReservation

### 7.1 Meaning

`BudgetReservation` is Accounting Owner's canonical authorization / reservation record for estimated future consumption.

It is not:

- an EffectOperation;
- a CapabilityGrant;
- a ResourceLease;
- proof that an external call happened;
- proof that actual usage equals the estimate.

### 7.2 Identity

```text
BudgetReservation
- reservation_ref
- request_ref
- activation_ref
- run_ref
- attempt_seq
- accounting_scope_ref
- ancestry_snapshot[]
- policy_revision_refs[]
- estimate_ref
- reserved_dimensions[]
- committed_dimensions[]
- released_dimensions[]
- state
- subject_refs[]
- created_at
- updated_at
- caused_by_ref
```

`request_ref` is stable and idempotent. The same request identity with a different estimate, scope or subject binding MUST be rejected as an identity conflict.

### 7.3 Candidate state set

```text
REQUESTED
RESERVED
DENIED
RECONCILING
COMMITTED
RELEASED
```

State meaning:

- `REQUESTED` — durable request exists; no reservation authority yet.
- `RESERVED` — estimated capacity is atomically reserved on the full applicable scope ancestry.
- `DENIED` — this request was denied. It never auto-revives.
- `RECONCILING` — authorization is no longer being treated as ordinary open reservation settlement; past usage / billing remains unresolved or newly disputed.
- `COMMITTED` — current known actual settlement for the reservation has been canonically committed.
- `RELEASED` — unused reserved capacity has been released; this is not a claim that no later billing can ever arrive.

`RECONCILING` never grants authority to spend. It is a settlement/recovery state, not a renewed reservation.

### 7.4 Normal lifecycle

```text
REQUESTED
├─ deny → DENIED
└─ reserve → RESERVED
             ├─ known actual usage finalized → COMMITTED
             ├─ definite no-use / unused remainder → RELEASED
             └─ uncertain usage / charge → RECONCILING
```

Late evidence may reopen settlement:

```text
RELEASED  → RECONCILING → COMMITTED / RELEASED
COMMITTED → RECONCILING → COMMITTED
```

This does not retroactively recreate spend authority. It only reopens settlement because new evidence arrived.

### 7.5 Denial semantics

A denied reservation request remains denied even if a limit later increases.

The caller must issue a new request with a new `request_ref` / `reservation_ref` according to Runtime-owned attempt policy.

Accounting does not retry Runtime work itself.

---

## 8. Hierarchical Atomic Reservation

### 8.1 Complete ancestor chain

Every reservation checks and reserves against the complete static accounting chain in one Accounting Owner-local canonical transaction.

Example:

```text
Root Project Scope
  ↓
Composite Scope
  ↓
Nested Composite Scope
  ↓
Module Instance Scope
```

If the Module Instance requests 100 units, all applicable hard limits on that chain must be evaluated against the same atomic snapshot.

### 8.2 Required atomicity

Within Accounting Owner:

```text
BEGIN ACCOUNTING OWNER TRANSACTION
1. validate reservation request identity
2. load pinned static ancestry
3. resolve applicable BudgetPolicyRevisions
4. compute existing committed + reserved exposure
5. evaluate every HARD rule on every ancestor
6. if any HARD rule denies: commit DENIED with no partial reserve
7. otherwise increment all required reserved counters
8. commit BudgetReservation = RESERVED
9. append durable BudgetReserved event / propagation record
COMMIT
```

Partial ancestor reservation is forbidden.

A child cannot successfully reserve if any governing ancestor cannot reserve.

### 8.3 Partition requirement

An ancestry chain that requires atomic reservation MUST be handled by one logical Accounting Owner transaction domain.

An implementation may physically shard storage, but it must not weaken this semantic into a best-effort cross-owner saga that can leave a child reserved while a parent was denied.

### 8.4 Concurrent reservation

Concurrent requests must serialize or otherwise provide equivalent atomic compare-and-reserve semantics so two reservations cannot both observe the same remaining hard-limit capacity and oversubscribe it.

---

## 9. Reserve / Deny / Commit / Release / Reconcile Semantics

### 9.1 Reserve

Reserve authorizes estimated future consumption only after all governing hard policies pass.

Successful reserve emits durable evidence such as:

```text
BudgetReserved
- reservation_ref
- accounting_scope_ref
- ancestry_snapshot
- policy_revision_refs
- reserved_dimensions
```

### 9.2 Deny

Deny means the specific authorization request is rejected.

Accounting emits `BudgetReservationDenied` with machine-readable reasons such as:

- `HARD_LIMIT_EXCEEDED`
- `ANCESTOR_LIMIT_EXCEEDED`
- `POLICY_NOT_RESOLVABLE`
- `ACCOUNTING_SCOPE_INVALID`
- `RESERVATION_REQUEST_CONFLICT`

Natural-language product explanation is outside this candidate.

### 9.3 Commit

Commit records known actual settlement. Actual may be lower, equal to or greater than estimate.

Commit MUST:

- preserve all actual UsageFacts;
- convert reserved exposure to committed exposure;
- release known unused reserved remainder;
- record overrun when actual > reserved;
- update all governed scope balances consistently within Accounting Owner.

### 9.4 Release

Release returns unused reserved capacity when Accounting has adequate evidence that the reservation no longer needs to hold that capacity.

Release is an accounting authority transition only. It does not prove:

- an EffectOperation never occurred;
- a Resource was destroyed;
- a provider can never submit a late bill.

### 9.5 Reconcile

Reconcile begins when Accounting cannot safely decide final committed versus released exposure, or when later evidence conflicts with previous settlement.

Accounting transitions the reservation to `RECONCILING` and opens / links a `ReconciliationCase`.

Recovery coordinates investigation. Accounting Owner remains the only Owner that can commit the final reservation/accounting transition.

---

## 10. Overrun Handling

### 10.1 Actual usage exceeds estimate

If actual usage exceeds the reservation, Nyron MUST record the full actual usage.

Example:

```text
reserved = 100
actual   = 135
```

Canonical result records 135 actual, not 100.

The extra 35 becomes an overrun fact / settlement delta and immediately affects future budget availability according to policy.

### 10.2 No retroactive invalidation

A hard budget limit is an authorization control for future work. It cannot make already incurred external cost disappear and cannot rewrite a completed EffectOperation as failed.

### 10.3 Future blocking after overrun

An overrun may cause later reservation requests on the same scope or ancestors to be denied until:

- quota window resets;
- policy changes;
- refund / adjustment facts reduce canonical exposure;
- an authorized operator changes budget policy.

### 10.4 Optional overrun policy

Policy may define how much additional conservative hold Accounting keeps when actual usage is not final, but that hold is accounting state only. It must not fabricate a provider charge.

---

## 11. Durable Deduplication

### 11.1 Usage dedupe identity

Provider / adapter callbacks may be delivered more than once.

Accounting MUST deduplicate by stable source identity, not callback arrival time.

Candidate uniqueness key:

```text
(source_authority_ref, source_fact_id, fact_kind, dimension_ref)
```

Equivalent provider-native immutable invoice-line / usage-event identity may be used.

### 11.2 Duplicate identical callback

Same dedupe identity + same semantic payload:

- return the previously committed UsageFact;
- do not add usage twice;
- may record telemetry that transport duplicated delivery.

### 11.3 Duplicate identity with conflicting payload

Same dedupe identity + different semantic payload:

- MUST NOT overwrite the old UsageFact;
- MUST NOT choose the latest callback by wall clock;
- open a ReconciliationCase with both evidence records;
- mark affected reservation settlement `RECONCILING` when required.

### 11.4 Internal event dedupe

Cross-owner Commands and Events also use stable message identities. Replaying a `BudgetCommitRequested`, `UsageReported` or `OpenReconciliationCase` command must be idempotent.

---

## 12. EffectOperation ↔ BudgetReservation Orthogonality

### 12.1 Reference model

The objects may cross-reference:

```text
EffectOperation.budget_reservation_ref?
BudgetReservation.subject_refs[] may include operation_ref
UsageFact.operation_ref?
```

These references establish causality / correlation only.

They do not grant mutation authority.

### 12.2 Independent state examples

Valid combinations include:

```text
EffectOperation = COMPLETED
BudgetReservation = RECONCILING
```

External completion is known; final cost is not.

```text
EffectOperation = UNKNOWN
BudgetReservation = RESERVED
```

Provider acceptance is unknown; reserved budget must not be prematurely released.

```text
EffectOperation = FENCED
BudgetReservation = COMMITTED
```

Future external activity is stopped; previously incurred usage remains real.

```text
EffectOperation = COMPLETED
BudgetReservation = RELEASED
```

Possible only when reliable accounting policy/evidence establishes no charge or no reserved capacity is needed. Completion itself is not sufficient proof of zero cost.

### 12.3 No ownership collapse

Effect Authority cannot set reservation state.

Accounting cannot set EffectOperation state.

Recovery cannot set either directly.

---

## 13. ResourceLease ↔ BudgetReservation Orthogonality

ResourceLease existence or expiry does not decide actual usage.

Examples:

```text
ResourceLease = EXPIRED
BudgetReservation = RECONCILING
```

Lease authority ended, but provider-side usage before/after disconnect may still be unresolved.

```text
ResourceLease = UNKNOWN
BudgetReservation = COMMITTED
```

Resource detachment history is uncertain, while a known provider invoice already establishes accounting cost.

Accounting may consume Resource Manager events as evidence but does not infer zero usage from lease release/expiry alone.

---

## 14. UNKNOWN Combination Rules

Unknown past facts remain unknown until reliable evidence or explicit policy disposition resolves the relevant subject.

### 14.1 Effect UNKNOWN + accounting state

If EffectOperation is UNKNOWN and potential billable work may have occurred:

- Accounting SHOULD retain conservative reserved exposure or transition to `RECONCILING` according to policy;
- Accounting MUST NOT record actual usage without evidence;
- Effect conflict blocking remains Effect Authority responsibility;
- Accounting may independently block new budget authorization because reserved / uncertain exposure consumes limit headroom.

### 14.2 ResourceLease UNKNOWN + accounting state

If ResourceLease is UNKNOWN:

- Resource Manager owns lease truth;
- Accounting retains only the exposure required by accounting policy;
- a lease UNKNOWN does not automatically mean provider billing occurred;
- Recovery may correlate Resource evidence and UsageFacts.

### 14.3 Effect known, accounting UNKNOWN

If EffectOperation is COMPLETED but provider cost is pending or disputed:

- EffectOperation remains COMPLETED;
- BudgetReservation may be RECONCILING;
- no effect rollback is invented merely to simplify budget.

### 14.4 Accounting known, effect UNKNOWN

A confirmed charge can exist while effect outcome is UNKNOWN.

Accounting commits the confirmed charge. Effect Authority preserves UNKNOWN until its own evidence resolves external effect history.

Money charged does not prove business success.

### 14.5 Unknown subject can remain unknown after case closure

A ReconciliationCase may be resolved by an explicit accounting disposition such as accepting a conservative charge or releasing an exposure after a contractual provider cutoff, while the underlying EffectOperation remains UNKNOWN.

`ReconciliationCase.RESOLVED` means the recovery case has a durable disposition. It does **not** mean every subject fact became known.

---

## 15. ReconciliationCase

### 15.1 Purpose

`ReconciliationCase` is the canonical record of bounded investigation for a past fact that cannot currently be confirmed.

It is not:

- a Graph;
- a Workflow;
- an Attempt scheduler;
- a second state machine for the subject;
- a place to copy subject truth.

### 15.2 Identity

```text
ReconciliationCase
- reconciliation_case_ref
- subject_owner_ref
- subject_ref
- reason_code
- state
- opened_by_ref
- evidence_refs[]
- attempt_count
- max_attempts
- retry_policy_ref
- next_retry_at?
- deadline
- escalation_policy_ref
- human_request_ref?
- resolution_ref?
- caused_by_ref
- opened_at
- updated_at
```

For one unresolved condition on one subject, case creation must be idempotent. Repeated open requests should return the existing active case rather than create unbounded duplicate cases.

### 15.3 State set

Preserving the frozen Module baseline semantics:

```text
OPEN
RETRYING
RESOLVED
ESCALATED
```

Normal flow:

```text
OPEN
→ RETRYING
   ├─ reliable evidence → RESOLVED
   ├─ retryable uncertainty → RETRYING (bounded)
   └─ attempts/deadline exhausted → ESCALATED
```

`ESCALATED` ends automatic retry authority. It may later accept human / newly arrived machine evidence and transition to `RESOLVED`, or be explicitly reopened according to policy. It MUST NOT hide an infinite automatic polling loop.

### 15.4 Reason codes

Examples:

- `EFFECT_DISPATCH_HISTORY_UNKNOWN`
- `EFFECT_REVOKE_UNCONFIRMED`
- `RESOURCE_DETACHMENT_UNKNOWN`
- `BILLING_USAGE_PENDING`
- `BILLING_CALLBACK_CONFLICT`
- `ORPHAN_RESERVATION`
- `LATE_PROVIDER_BILLING`
- `DUPLICATE_SOURCE_FACT_CONFLICT`
- `ACCOUNTING_SETTLEMENT_INCOMPLETE`

---

## 16. Retry / Backoff / Deadline

### 16.1 Bounded automatic recovery

Every automatically retryable reconciliation path MUST specify:

- `max_attempts`;
- backoff policy;
- absolute or causal deadline;
- retry eligibility predicate;
- escalation action.

No permanent `WAITING_FOR_RECOVERY`, `RECOVERY_BLOCKED` or equivalent endless state is allowed.

### 16.2 Retry semantics

Recovery retry means retrying an observation / reconciliation operation, such as:

- query provider by external idempotency identity;
- query process state;
- fetch invoice / usage record;
- verify artifact/hash evidence;
- query subject Owner canonical history.

Recovery MUST NOT blindly repeat the original external effect merely because the original result is uncertain.

### 16.3 Backoff

Backoff is Recovery scheduling metadata only. It does not create Runtime Attempt semantics.

Policy may use fixed, exponential or provider-specific backoff with jitter, but replay correctness must preserve committed retry schedule decisions and case history.

### 16.4 Deadline

When the deadline is reached without adequate evidence:

- automatic retries stop;
- case transitions to ESCALATED;
- subject UNKNOWN is preserved unless the subject Owner has separate reliable evidence;
- accounting may apply an explicitly configured conservative disposition without pretending historical certainty.

---

## 17. Escalation and Manual Resolution

### 17.1 Human Interaction boundary

Recovery does not own human identity or human-response truth.

If manual review is required:

```text
Recovery Owner
→ Command: CreateHumanReconciliationRequest
→ Human Interaction Owner
→ HumanRequestCommitted
→ human response arrives externally
→ Human Interaction Owner authenticates / canonicalizes response
→ HumanReconciliationResponse Event
→ Recovery Owner evaluates response as evidence / disposition instruction
```

### 17.2 Manual evidence versus manual policy disposition

Two concepts must remain separate:

1. **Manual evidence** — an authorized person supplies reliable evidence about what happened.
2. **Manual policy disposition** — an authorized person chooses how Nyron should settle exposure despite unresolved history.

A policy disposition may settle Accounting while leaving EffectOperation UNKNOWN.

A human clicking “assume failed” is not automatically reliable evidence that a provider request never happened.

### 17.3 Resolution authority

Recovery Owner may commit `ReconciliationCase.RESOLVED` with a resolution record such as:

```text
ReconciliationResolution
- resolution_ref
- resolution_kind
- evidence_refs[]
- disposition
- target_commands[]
- authorized_by_ref?
- resolved_at
```

But any subject transition is then requested through the subject Owner:

- Accounting Owner commits BudgetReservation / settlement changes;
- Effect Authority commits EffectOperation changes;
- Resource Manager commits ResourceLease changes.

---

## 18. Recovery Evidence Model

### 18.1 Evidence object

```text
RecoveryEvidence
- evidence_ref
- evidence_kind
- source_authority_ref
- source_identity
- subject_ref?
- payload_ref / payload_hash
- observed_at?
- ingested_at
- authenticity_status
- semantics_ref
- caused_by_ref?
```

Potential evidence kinds:

- provider idempotency lookup;
- provider invoice line;
- provider usage callback;
- process / job identity lookup;
- filesystem artifact hash / revision;
- Effect Authority event;
- Resource Manager event;
- Runtime Attempt event;
- authenticated human attestation;
- contractual provider billing cutoff evidence.

### 18.2 Evidence is not automatically truth

Recovery Evidence becomes authoritative only for the meaning its source can prove.

Examples:

- provider invoice proves a charge, not necessarily application-level success;
- process-not-found at time T may not prove the process never ran before T;
- ResourceLease expiry proves future lease authority ended, not that provider work ended;
- Runtime Attempt failure proves Runtime attempt state, not external provider rejection.

### 18.3 Conflicting evidence

Conflicting evidence is preserved, not overwritten.

The case remains RETRYING or ESCALATED until the applicable subject Owner / policy can resolve the contradiction.

---

## 19. Crash / Restart / Replay

### 19.1 General rule

A crash never authorizes Nyron to infer a missing past fact.

Correctness depends on canonical state, stable identities and replayable events, not in-memory worker knowledge.

### 19.2 Reservation crash windows

#### Crash before reservation commit

No `RESERVED` canonical fact exists. Caller may replay the same request identity. Accounting either returns the previously committed outcome or processes it once.

#### Crash after `RESERVED` commit but before caller receives response

Replay with the same `request_ref` returns the existing reservation. It MUST NOT reserve ancestor capacity twice.

#### Crash during commit/release

Owner-local atomic transaction ensures counters and BudgetReservation state converge together. No state may show released capacity while reservation still claims the same active reserve, or vice versa.

### 19.3 Usage callback crash

If callback handling crashes after UsageFact commit but before acknowledgement, provider may retry. Stable source dedupe returns the existing fact and avoids double charge.

### 19.4 Reconciliation retry crash

Recovery attempts have stable attempt identities.

If a recovery observation was externally issued before crash, restart must determine whether repeating the observation is idempotent/read-only. Recovery may replay provider queries; it must not replay the original business effect.

### 19.5 Event propagation

A committed Accounting / Recovery fact required by another Owner must have durable replayable propagation established atomically with the local commit or equivalent reliable outbox mechanism.

Transport exactly-once delivery is not required.

---

## 20. Orphan Reservation Handling

### 20.1 Definition

An orphan reservation is a BudgetReservation whose expected Runtime / Effect settlement progression is absent or disconnected after crash, replacement or integration failure.

Orphan detection is a derived scan / watchdog condition, not proof that usage did not occur.

### 20.2 Required procedure

For a stale-looking RESERVED reservation:

1. Query Runtime for durable Activation / Run / Attempt state.
2. Query Effect Authority for related EffectOperations.
3. Query relevant Resource Manager state when Resource usage can affect cost evidence.
4. Inspect committed UsageFacts.
5. If reliable evidence proves no billable effect occurred and no future bill can arise under the adapter contract, release.
6. If actual usage is known, commit actual settlement.
7. If history remains uncertain, transition to RECONCILING and open a ReconciliationCase.

Time elapsed alone is not proof of no usage.

### 20.3 Reservation TTL

Accounting may use reservation expiry as a trigger to investigate or stop future spend authority, but expiry MUST NOT automatically erase uncertain historical exposure.

---

## 21. Late Provider Billing

### 21.1 Billing after RELEASED

A provider may submit valid billing after a reservation was released.

Accounting MUST:

- accept and deduplicate the valid UsageFact;
- preserve the previous RELEASED history;
- transition settlement to RECONCILING when necessary;
- commit the actual late charge;
- record resulting overrun / negative headroom;
- apply the charge to all applicable ancestor accounting scopes.

It MUST NOT reject a real bill merely because a reservation was already released.

### 21.2 Billing after COMMITTED

Additional valid billing after COMMITTED reopens settlement:

```text
COMMITTED → RECONCILING → COMMITTED
```

The second COMMITTED settlement reflects the appended usage facts; previous settlement history remains auditable.

### 21.3 Provider correction/refund

Refund or correction is appended as a new Usage/Adjustment fact. Historical facts remain immutable.

---

## 22. Duplicate Usage Callback Cases

### Case A — exact duplicate

Same provider fact identity and same payload:

- idempotent no-op;
- return existing UsageFact.

### Case B — same callback identity, changed amount

- preserve original UsageFact;
- preserve conflicting callback as RecoveryEvidence;
- open `DUPLICATE_SOURCE_FACT_CONFLICT` case;
- do not choose latest arrival as truth.

### Case C — distinct provider line items for same operation

If provider semantics define distinct immutable line-item identities, both may be valid UsageFacts and must be counted.

EffectOperation identity alone is not sufficient as usage dedupe key because one external operation may legitimately produce multiple charge lines.

---

## 23. Cross-Owner Contracts

All contracts use stable command/event identities and idempotent processing.

### 23.1 Runtime → Accounting Owner

Commands:

- `RequestBudgetReservation`
- `ReleaseBudgetReservation`
- `RequestReservationSettlement`
- `ReportAttemptTerminalForAccounting`

Queries:

- `GetBudgetReservation`
- `CheckReservationUsable`
- `GetAccountingExposure`

Events from Accounting:

- `BudgetReservationRequested`
- `BudgetReserved`
- `BudgetReservationDenied`
- `BudgetReservationReconciling`
- `BudgetReservationCommitted`
- `BudgetReservationReleased`
- `BudgetOverrunRecorded`

Runtime consumes these facts but Accounting does not decide Runtime retry/replacement.

### 23.2 Effect Authority ↔ Accounting Owner

Effect / adapter Commands or reports:

- `ReportUsageEvidence`
- `AssociateEffectWithReservation`
- `ReportEffectAccountingTerminalHint`

Accounting Queries:

- `GetEffectOperation`
- `GetEffectEvidence`

Effect Events consumed by Accounting / Recovery:

- `EffectPrepared`
- `EffectActive`
- `EffectCompleted`
- `EffectFenced`
- `EffectUnknown`

Accounting Events consumed by Effect boundary as needed:

- `BudgetReserved`
- `BudgetReservationDenied`
- `BudgetReservationReleased`
- `BudgetReservationReconciling`

The actual effect boundary may require a current usable BudgetReservation according to policy, but Effect Authority never mutates the reservation.

### 23.3 Resource Manager ↔ Accounting / Recovery

Resource Events:

- `LeaseGranted`
- `LeaseReleased`
- `LeaseExpired`
- `LeaseUnknown`
- `ResourceLost`
- `ResourceUnknown`

Queries:

- `GetResource`
- `GetLease`
- `GetResourceEvidence`

Accounting uses them only as evidence / correlation. Resource state does not directly settle usage.

### 23.4 Recovery Owner ↔ subject Owners

Commands:

- `OpenReconciliationCase`
- `SubmitRecoveryEvidence`
- `RequestSubjectEvidence`
- `ProposeSubjectResolution`
- `ApplyAccountingDisposition`

Events:

- `ReconciliationOpened`
- `ReconciliationRetryScheduled`
- `ReconciliationEvidenceAccepted`
- `ReconciliationResolved`
- `ReconciliationEscalated`

Subject Owner Events are the final evidence that a subject transition committed.

### 23.5 Recovery ↔ Human Interaction

Commands:

- `CreateHumanReconciliationRequest`
- `CancelHumanReconciliationRequest`

Events:

- `HumanReconciliationRequestCreated`
- `HumanReconciliationResponseCommitted`
- `HumanReconciliationRequestExpired`

Product UX, wording and role presentation remain outside D-005.

---

## 24. What Blocks New Work

Blocking must be owned by the subsystem whose authority is at risk.

### 24.1 Accounting hard-limit block

New work requiring budget authorization is blocked when:

- required hard-limit headroom is unavailable;
- required ancestry cannot be atomically reserved;
- policy requires conservative hold for an unresolved reservation and that hold consumes remaining capacity;
- reservation state is not usable for the requested effect.

This blocks **new budget authorization**, not arbitrary Runtime scheduling globally.

### 24.2 Effect conflict block

If prior EffectOperation is UNKNOWN or not safely fenced, conflicting new effect authority is blocked by Effect Authority / Capability boundary according to D-004.

Accounting MUST NOT claim to clear an effect conflict merely because a reservation was released or committed.

### 24.3 Resource conflict block

If ResourceLease / Resource ownership is uncertain, Resource Manager decides lease/resource conflict clearance.

### 24.4 Settlement-only conditions

The following normally affect settlement but do not by themselves block non-conflicting work:

- late invoice processing;
- historical reporting projection lag;
- soft budget threshold;
- completed effect with final price pending, provided conservative hard-limit exposure is already held;
- reconciliation on a subject unrelated to the new work's conflict/budget scopes.

### 24.5 ReconciliationCase itself is not a universal lock

Opening a ReconciliationCase does not automatically block the whole workflow or project.

Blocking derives from the unresolved subject and the applicable authority policy.

---

## 25. Canonical Accounting Truth Versus Derived Projection

### 25.1 Canonical truth

Canonical Accounting truth includes:

- AccountingScope identity / ancestry reference;
- BudgetPolicyRevision used for authorization;
- BudgetReservation decisions and transitions;
- UsageFacts and UsageAdjustmentFacts;
- canonical settlement transitions;
- overrun facts;
- ReconciliationCase and its evidence / resolution history.

### 25.2 Derived state

The following may be projections or caches when reconstructible:

- current spend dashboard;
- remaining budget display;
- per-provider usage dashboard;
- projected end-of-month cost;
- average cost per Module;
- burn-rate graphs;
- anomaly scores;
- UI warning summaries;
- precomputed rollups / indexes.

Deleting a derived projection must not destroy the evidence needed to reconstruct canonical accounting truth.

### 25.3 Projection lag

Derived reporting may temporarily lag canonical events. It MUST NOT be used as the sole hard-limit authority unless the projection is itself maintained as canonical owner-local enforcement state with transactional correctness.

---

## 26. Reason Codes

Candidate machine-readable Accounting / Recovery reason vocabulary:

```text
BUDGET_RESERVATION_DENIED
HARD_LIMIT_EXCEEDED
ANCESTOR_LIMIT_EXCEEDED
ACCOUNTING_SCOPE_INVALID
ACCOUNTING_POLICY_UNRESOLVED
RESERVATION_REQUEST_CONFLICT
RESERVATION_NOT_USABLE
ACCOUNTING_SETTLEMENT_INCOMPLETE
ACCOUNTING_USAGE_UNKNOWN
BUDGET_OVERRUN
USAGE_FACT_DUPLICATE
USAGE_FACT_CONFLICT
LATE_PROVIDER_BILLING
ORPHAN_RESERVATION
RECONCILIATION_DEADLINE_EXCEEDED
RECONCILIATION_ESCALATED
MANUAL_DISPOSITION_REQUIRED
```

Presentation text is not part of canonical control flow.

---

## 27. AR-INV Architecture Invariants

### AR-INV-01 — Static Accounting Membership
Every execution's AccountingScope membership derives from immutable Graph / Composite containment pinned by the Activation. Dynamic provenance never changes accounting membership.

### AR-INV-02 — Single Owner per Accounting Truth
AccountingScope, BudgetReservation, usage facts and settlement truth have exactly one Accounting Owner. ReconciliationCase has exactly one Recovery Owner.

### AR-INV-03 — Effect / Resource / Capability / Budget Orthogonality
`EffectOperation`, `ResourceLease`, `CapabilityGrant` and `BudgetReservation` remain distinct canonical facts, owners and lifecycles even when one external operation requires all of them.

### AR-INV-04 — Full-Ancestry Atomic Reserve
A successful reservation atomically reserves every applicable hard-limit ancestor within one Accounting Owner transaction domain; partial ancestor reservation is forbidden.

### AR-INV-05 — Child Cannot Widen Parent
A child AccountingScope may narrow ancestor policy but cannot widen an ancestor hard restriction.

### AR-INV-06 — Denial Does Not Auto-Revive
A denied reservation never becomes authorized merely because policy or remaining budget later changes. A new request is required.

### AR-INV-07 — Estimate Is Not Actual
Reserved/estimated usage is authorization basis only and must never be presented as actual historical consumption.

### AR-INV-08 — Actual Facts Are Never Capped
Actual usage / charge facts are recorded in full even when they exceed reservation or policy limit.

### AR-INV-09 — No Historical Rewrite
Committed UsageFacts are immutable. Corrections, refunds and disputes append new evidence / adjustment facts.

### AR-INV-10 — UNKNOWN Is Not Zero
Unknown historical usage/effect/resource/accounting facts are never converted to zero, success, failure, release or completion without adequate evidence or an explicitly recorded policy disposition that preserves what remains unknown.

### AR-INV-11 — Recovery Does Not Own Subject Truth
ReconciliationCase may coordinate retry/evidence/escalation but cannot directly mutate the canonical subject owned by Accounting, Effect Authority, Resource Manager or Runtime.

### AR-INV-12 — Bounded Recovery
Every automatic uncertainty-recovery loop has max attempts, backoff and deadline. Infinite recovery waiting is forbidden.

### AR-INV-13 — Reconciliation Is Not Workflow Runtime
Recovery retry scheduling and evidence handling must not duplicate Runtime Attempts, Graph execution or product workflow semantics.

### AR-INV-14 — Duplicate Delivery Is Accounting-Safe
Duplicate cross-owner events and provider usage callbacks cannot create duplicate canonical usage or duplicate reservation transitions.

### AR-INV-15 — Conflicting Duplicate Evidence Is Preserved
The same source fact identity with conflicting payload must not be resolved by overwrite or wall-clock last-write-wins; conflict enters Reconciliation.

### AR-INV-16 — Reservation Release Does Not Erase Late Actuals
A RELEASED reservation does not authorize Accounting to reject later valid usage or billing facts.

### AR-INV-17 — Settlement Cannot Rewrite Effect Truth
Accounting settlement state cannot change or imply EffectOperation completion/failure/fencing, and EffectOperation state cannot by itself determine accounting settlement.

### AR-INV-18 — Lease Expiry Is Not Billing Proof
ResourceLease release/expiry/UNKNOWN may be evidence but does not by itself prove zero or non-zero usage.

### AR-INV-19 — Cross-Owner Atomicity Is Not Assumed
Accounting/Recovery correctness must tolerate temporary cross-owner partial convergence using durable idempotent Commands/Events and reconciliation.

### AR-INV-20 — Reconciliation Closure Does Not Require Fabricated Certainty
A ReconciliationCase may resolve through explicit policy disposition while the underlying historical subject remains UNKNOWN; the disposition must not be represented as evidence that the unknown fact became known.

### AR-INV-21 — Derived Reporting Is Not Canonical Authority
Dashboards, projections, rollups and cost forecasts cannot become the sole authority for hard-limit correctness unless maintained as owner-local canonical enforcement state.

### AR-INV-22 — Late Evidence Reopens Settlement, Not Spend Authority
Late usage or billing may move RELEASED/COMMITTED settlement into RECONCILING, but it never recreates a previously expired/released reservation authority for new external spend.

---

## 28. Implementation Gates

This candidate does not authorize implementation until Lead review / freeze establishes the relevant baseline.

Recommended gates after freeze:

### AR-GATE-0 — Ownership / schema gate

Must prove:

- Accounting Owner and Recovery Owner separation;
- AccountingScope static ancestry;
- policy revision pinning;
- BudgetReservation identity/idempotency;
- UsageFact immutable identity/dedupe;
- ReconciliationCase cannot mutate subject state directly.

### AR-GATE-1 — Hierarchical reservation gate

Tests:

- child + parent successful reserve commits atomically;
- parent denial leaves no child reserve;
- two concurrent requests cannot oversubscribe hard limit;
- replay same request does not double reserve;
- denied request does not auto-revive.

### AR-GATE-2 — Settlement / overrun gate

Tests:

- actual < reserved releases remainder;
- actual = reserved commits exactly;
- actual > reserved commits full actual and overrun;
- future reservation denied after overrun when hard limit exhausted;
- refund/adjustment appends rather than rewrites.

### AR-GATE-3 — Usage dedupe gate

Tests:

- exact duplicate provider callback counts once;
- same source identity with conflicting amount opens Reconciliation;
- multiple legitimate provider line items for one EffectOperation can all count;
- crash after UsageFact commit / before callback ack remains idempotent.

### AR-GATE-4 — UNKNOWN / orthogonality gate

Fault-inject combinations:

- Effect COMPLETED + Budget RECONCILING;
- Effect UNKNOWN + Budget RESERVED/RECONCILING;
- Effect FENCED + Budget COMMITTED;
- Lease UNKNOWN + known billing;
- known charge + Effect UNKNOWN.

Verify no Owner rewrites another Owner's truth.

### AR-GATE-5 — Recovery gate

Tests:

- OPEN → RETRYING → RESOLVED;
- max-attempts/deadline → ESCALATED;
- no infinite automatic wait;
- provider observation retry is safe;
- original non-idempotent business effect is never blindly replayed;
- manual disposition can settle Accounting while Effect remains UNKNOWN.

### AR-GATE-6 — Crash / orphan / late billing gate

Tests:

- crash before/after reserve commit;
- orphan reservation with definite no-use → release;
- orphan reservation with uncertain effect → RECONCILING;
- late valid billing after RELEASED;
- late valid billing after COMMITTED;
- durable outbox/event replay after owner restart.

### AR-GATE-7 — Cross-owner integration gate

Integrate Runtime, Effect Authority, Resource Manager and Human Interaction boundaries and prove:

- no global transaction assumption;
- stable command/event dedupe;
- correct conflict ownership;
- hard accounting block is scoped to budget authority;
- Effect/Resource conflict barriers remain owned by their respective authorities.

---

## 29. Open Questions for Lead Review

These are not blocking Architecture Findings unless Lead determines they affect another frozen contract.

### AR-OQ-01 — Initial accounting dimension registry

Which accounting dimensions must be standardized in v0.1 versus registered by provider adapters later? Architecture only requires stable unit semantics and versioned conversion rules.

### AR-OQ-02 — Budget policy ownership above project scope

If Workspace / organization / account policy introduces ancestor budget authorities outside a GraphRevision, D-008 / Overall Architecture should define the immutable context reference by which those scopes participate in the reservation ancestry. This candidate does not invent dynamic Packet-based ancestry.

### AR-OQ-03 — Conservative exposure policy

Lead should decide whether v0.1 standardizes one default conservative hold for UNKNOWN billable effects or requires each accounting policy/provider adapter to declare its own maximum exposure rule.

### AR-OQ-04 — Provider contractual cutoff

When a provider contract guarantees that no billing can arrive after a certain authenticated settlement cutoff, that cutoff can be Recovery evidence supporting release. Exact provider contracts remain adapter-specific.

### AR-OQ-05 — Manual accounting roles

Human Interaction / Workspace policy must eventually define which authenticated human roles may submit evidence, approve policy disposition, modify budget policy or accept overrun. D-005 defines authority boundaries but not product role taxonomy.

---

## 30. Architecture Finding

**None identified by NYRON-D-005.**

This candidate can preserve all known frozen constraints without changing EffectOperation, ResourceLease, Capability or Runtime Attempt semantics.

If later implementation discovers that an UNKNOWN Effect/Resource state can only be resolved by changing those frozen subject lifecycles, the affected implementation scope must stop and raise an explicit Architecture Finding rather than absorbing the semantic change into Accounting/Recovery.

---

## 31. Candidate Conclusion

Nyron Accounting is a canonical authorization-and-settlement subsystem whose execution membership is fixed by immutable static Graph/Composite containment. A BudgetReservation atomically reserves estimated exposure across the entire governing AccountingScope ancestry, while actual usage remains independent durable history that is recorded in full even when it exceeds budget.

EffectOperation, ResourceLease, CapabilityGrant and BudgetReservation remain orthogonal. References correlate these facts but never merge their ownership or state machines.

Recovery is a bounded canonical investigation mechanism. ReconciliationCase owns retry/backoff/deadline/evidence/escalation mechanics, but it never becomes a second Workflow engine and never duplicates subject truth. UNKNOWN past facts remain UNKNOWN until evidence resolves them; policy may settle exposure without fabricating historical certainty.

Crash, replay, duplicate callbacks, orphan reservations and late provider billing converge through stable identities, immutable usage facts, idempotent owner-local transactions and cross-owner Commands/Events rather than global atomic mutation or guessed truth.

Status remains **CANDIDATE — FOR LEAD REVIEW**. No architecture is frozen by this document.