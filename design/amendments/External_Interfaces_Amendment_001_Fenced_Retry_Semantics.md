# External Interfaces Amendment 001 — FENCED Is Not Semantic Retry Clearance

Status: **FROZEN EXTERNAL INTERFACES ARCHITECTURE AMENDMENT**
Authority: Nyron Lead Design Authority
Applies to: `design/Nyron_External_Interfaces_Workspace_Frozen_Baseline_v0.1.md`, specifically the frozen D-008 provider/external retry semantics derived from `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md` §11.7.
Reason: Resolve `NYRON-D-004-GPT-F01` discovered during independent adversarial D-004 review.

## 1. Problem

The frozen D-008 candidate states that safe redispatch may rely on:

```text
proof old operation is FENCED
```

That condition is insufficient for a non-idempotent or otherwise consequence-sensitive operation.

`EffectOperation.FENCED` proves only that the old operation is authoritatively prevented from continuing to create future activity within the relevant effect scope. It does **not** prove that the operation:
- was never dispatched;
- produced no partial external consequence;
- produced no complete external consequence;
- is semantically safe to repeat.

Therefore active/concurrency conflict clearance and semantic retry clearance are distinct facts.

## 2. Amended Retry Rule

For the same semantic external operation, redispatch/retry is safe only when at least one of the following is true:

1. reliable evidence proves the prior operation was never externally dispatched or produced no relevant external consequence;
2. the retry uses the same provider/external idempotency identity under a protocol that reliably deduplicates duplicate dispatch for the protected consequence;
3. the prior operation's historical outcome is sufficiently known and the new operation is explicitly a new distinct semantic operation rather than a retry of the same consequence;
4. an explicit policy intentionally permits duplicate consequences for that operation class/scope.

`FENCED` alone is not sufficient.

## 3. Orthogonal Active-State and Historical-Outcome Semantics

Nyron must be able to represent:

```text
active_state = FENCED
historical_outcome = UNKNOWN | PARTIAL | KNOWN
```

or an equivalent owner-local model preserving the same semantics.

The exact storage schema is not frozen here. What is frozen is the semantic distinction:

```text
FENCED
!= never dispatched
!= no consequence
!= safe semantic replay
```

A provider may confirm that no further activity can occur while remaining unable to prove what already happened before fencing.

## 4. Replacement / Conflict Clearance

FENCED may clear the **active/concurrency conflict** that would otherwise allow R1 to continue interfering with R2.

It does not by itself authorize R2 to repeat the same non-idempotent semantic effect.

Therefore two separate questions must be answered:

1. **Can old work still continue or conflict?** — Effect Authority active/conflict state.
2. **Can the same consequence safely be attempted again?** — retry/idempotency/historical-outcome safety.

The first may be cleared while the second remains unsafe.

## 5. UNKNOWN / PARTIAL Historical Outcome

If an old operation is authoritatively stopped but the historical consequence cannot be determined, the system preserves that uncertainty.

A retry must remain blocked for the same consequence unless idempotency/deduplication or explicit duplicate-acceptance policy makes redispatch safe.

Nyron must not convert `FENCED + historical uncertainty` into `safe retry` by convenience.

## 6. Added Invariant

**EIW-INV-32 — FENCED Is Not Semantic Retry Clearance**

External Interface adapters and provider integrations MUST NOT treat `EffectOperation.FENCED` as proof that an old operation had no prior consequence or that the same non-idempotent semantic operation may be safely redispatched. Retry safety requires independent historical/idempotency/duplicate-consequence justification.

## 7. Baseline Effect

This Amendment is authoritative wherever the frozen D-008 retry-safety wording could be read to make `FENCED` alone sufficient for semantic redispatch.

No change is made to:
- EffectOperation ownership;
- the meaning that FENCED requires authoritative stop/fence evidence;
- Runtime Attempt replacement;
- Capability/Resource ownership;
- Packet -> Delivery -> Activation -> Run execution semantics.
