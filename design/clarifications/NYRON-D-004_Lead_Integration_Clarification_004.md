# NYRON-D-004 — Lead Integration Clarification 004

**Status:** NORMATIVE INTEGRATED CANDIDATE CLARIFICATION / PRE-FREEZE  
**Applies to:** `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md` and Clarification 003  
**Authority:** Nyron Lead Design Authority

This clarification resolves two blocking findings from an independent GPT adversarial review of D-004:
- `NYRON-D-004-GPT-F01` — `FENCED` was incorrectly usable as sufficient semantic retry clearance;
- `NYRON-D-004-GPT-F02` — authority validation and irreversible authority consumption lacked a race-safe linearization contract.

F01 also requires the frozen companion amendment:
- `design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`

---

## 1. Active Conflict Clearance Is Not Semantic Retry Clearance

D-004 §18 and the previously frozen D-008 provider retry text could be read as allowing a same-semantic retry merely because the old EffectOperation is `FENCED`.

That interpretation is forbidden.

`FENCED` proves only that the old operation is authoritatively prevented from continuing future external activity in the relevant scope. It does not prove what consequences already occurred before fencing.

Therefore:

```text
active/concurrency conflict clearance
!= semantic retry clearance
```

A same-semantic non-idempotent redispatch is safe only when at least one of the following is established:

1. reliable evidence proves the old operation was never dispatched or produced no relevant external consequence;
2. the same external/provider idempotency identity is used under a protocol that reliably deduplicates the protected consequence;
3. the old historical outcome is sufficiently known and the new operation is explicitly a new distinct semantic operation rather than a retry;
4. an explicit policy intentionally accepts duplicate consequences for that operation class/scope.

`FENCED` alone is insufficient.

### Added invariant

**ARE-INV-21 — FENCED Is Not Semantic Retry Clearance**

Effect Authority may use `FENCED` to establish that old work cannot continue on the active-effect axis, but no subsystem may infer from `FENCED` alone that prior consequences are absent or that the same non-idempotent semantic effect is safe to redispatch.

---

## 2. Historical Outcome Must Remain Expressible After Fencing

An operation may be definitely stopped while its past consequence remains uncertain or partial.

Nyron must preserve the equivalent semantics of:

```text
active state: FENCED
historical consequence: KNOWN | NONE_PROVEN | PARTIAL | UNKNOWN
```

The exact schema is owner-local implementation detail. It may be represented by outcome/certainty metadata, evidence records, retry-safety disposition, or another Effect Authority-owned canonical representation.

What is normative is that:

```text
FENCED
!= historical outcome known
```

If active work is fenced but historical consequence is UNKNOWN/PARTIAL, overlapping *concurrent* activity may be unblocked when the conflict contract permits, while same-semantic retry remains blocked unless independent idempotency/retry safety exists.

### Added invariant

**ARE-INV-22 — Active State and Historical Consequence Are Orthogonal**

Effect Authority must preserve enough canonical truth to distinguish whether an old operation can still continue from whether its prior external consequence is known and semantically replay-safe.

---

## 3. Plain Check-Then-Use Authority Validation Is Forbidden

D-004 requires revalidation of current Attempt, fencing token, CapabilityGrant, scope and applicable ResourceLease at the actual mediated boundary.

A simple sequence such as:

```text
read current authority -> valid
replacement/revoke commits
use cached valid result -> dispatch/mutate
```

is not compliant.

The boundary must use a **race-safe authority-consumption admission protocol**. A cached validation result is never sufficient across the authority-consumption linearization point.

---

## 4. Authority-Consumption Linearization Contract

For every externally consequential Effect dispatch or mediated Canonical Command that consumes Attempt/Grant/Lease authority, Nyron must establish one unambiguous order between:

```text
authority use admission
vs
Attempt replacement / cancellation / Grant revoke-or-expire / Lease revoke-or-expire
```

The protocol must guarantee:

### Case A — revoke/replacement wins first

If any required authority becomes invalid before the exact use is admitted:
- the operation/command is rejected;
- no external dispatch or target-owner mutation may be newly initiated from that stale authority;
- any partial local admission work must be abortable/releasable without external consequence.

### Case B — authority use admission wins first

If the exact operation/command is race-safely admitted while all required authority is current:
- that admission is durably identifiable as pre-replacement/pre-revoke in-flight work;
- a later replacement/revoke prevents future authority uses but does not retroactively rewrite the already-admitted operation as if it never entered the boundary;
- the admitted work is handled through normal Effect/target-owner completion, fencing, cancellation, UNKNOWN and reconciliation semantics.

This is a linearization rule, not a requirement for one global cross-owner transaction.

Implementations may use Kernel fencing gates, compare-and-swap epochs, operation-specific admission permits, short critical sections, broker serialization or another mechanism only if it provides the same observable correctness guarantee.

### Added invariant

**ARE-INV-23 — Authority Validation and Use Must Linearize Against Revocation**

An actual mediated authority use must participate in a race-safe admission protocol that orders the use against relevant Attempt/Grant/Lease revocation. Plain check-then-use validation is insufficient.

---

## 5. Effect Dispatch Admission

`EffectOperation(PREPARED)` is durable intent and identity; it is **not by itself** proof that dispatch authority has been consumed.

Before external dispatch, the mediated boundary must establish a race-safe dispatch admission for that exact `operation_ref`.

Conceptually:

```text
EffectOperation(PREPARED)
-> race-safe authority-consumption admission
-> durable dispatch-admission evidence/ref for operation_ref
-> external dispatch
-> external acknowledgement/evidence
-> ACTIVE / COMPLETED / UNKNOWN as applicable
```

The durable dispatch-admission evidence proves only that this exact operation won the authority race and became pre-replacement/pre-revoke in-flight work. It does not prove external dispatch actually occurred; Amendment 001 crash ambiguity still applies.

If crash occurs after dispatch admission but before dispatch, recovery must not fabricate dispatch. If crash occurs after dispatch, PREPARED/dispatch-admitted history still requires external evidence/idempotency lookup or UNKNOWN handling.

### Added invariant

**ARE-INV-24 — PREPARED Is Not Authority Consumption**

PREPARED creates durable effect identity/intent. A separate race-safe boundary admission must establish that the exact operation may cross the external boundary. Neither fact alone proves the provider actually received the operation.

---

## 6. Canonical Command Acceptance

Canonical Command uses the same race-safety principle.

Forbidden:

```text
gateway validates Attempt/Grant
-> replacement commits
-> stale command arrives at target Owner
-> target mutates state because the old validation was cached
```

The target-owner command path must establish a durable acceptance/authority-consumption point for the exact `command_ref` that linearizes against relevant Attempt/Grant revocation.

If revocation wins first, the target Owner rejects the command as stale.

If command acceptance wins first, the command is canonical pre-revocation in-flight work and may complete according to the target Owner's idempotent command contract; later replacement does not rewrite the acceptance order.

Command acknowledgement still does not equal mutation commit unless the target contract explicitly makes acceptance+mutation one owner-local canonical transaction. The corresponding target canonical event remains evidence of the committed mutation.

### Added invariant

**ARE-INV-25 — Canonical Command Cannot Cross a Revocation Race on Cached Authority**

Target-owner command acceptance must be race-safely ordered against relevant Attempt/Grant revocation; stale cached gateway validation cannot authorize a late foreign mutation.

---

## 7. Multi-Authority Admission

Where an operation requires multiple authority dimensions, for example:

```text
current Attempt/fencing
+ CapabilityGrant
+ ResourceLease
```

external/foreign consequence may begin only after the admission protocol has established the exact operation as admitted under all required authority dimensions.

If any required owner/gate rejects because revocation linearized first, no new external/foreign consequence may be initiated.

The architecture does not freeze one physical locking protocol, but implementations must not weaken this into best-effort sequential checks whose results can become stale before use.

---

## 8. Interaction With Replacement

After R2 replaces R1:
- R1 cannot obtain a new authority-use admission;
- an R1 operation whose admission linearized before replacement is treated as already in-flight old work;
- Effect Authority may need to revoke/fence/reconcile that admitted effect;
- active conflict clearance and semantic retry clearance remain separate under §§1–2;
- an admitted old effect may complete after replacement without granting R1 any new future authority.

This distinction prevents two incorrect extremes:
1. stale R1 creating brand-new work after replacement;
2. pretending pre-replacement admitted work never existed merely because its external dispatch/commit completed later.

---

## 9. Frozen-Baseline Impact

### F01
`NYRON-D-004-GPT-F01` has **Frozen baseline impact: YES** because frozen D-008 §11.7 made `FENCED` alone a safe-redispatch condition.

The frozen correction is:
- `design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`

No Module Architecture state-set change is required.

### F02
`NYRON-D-004-GPT-F02` has **Frozen baseline impact: NO**.

It tightens the implementation-independent meaning of existing frozen invariants:
- stale Attempts cannot initiate new effects;
- actual effect boundaries revalidate authority;
- replacement removes future authority.

It does not change Runtime ownership/lifecycle or the frozen EffectOperation state set.

---

## 10. Lead Disposition

Both independent GPT findings are accepted as valid blockers against freezing the pre-Clarification-004 D-004 bundle.

With:
- Clarification 003;
- this Clarification 004; and
- External Interfaces Amendment 001

applied, the Lead considers the identified blockers corrected.

D-004 now requires a **targeted independent re-review of the corrected bundle** before final freeze. The same existing independent GPT review conversation should be reused; no new GPT conversation is required.
