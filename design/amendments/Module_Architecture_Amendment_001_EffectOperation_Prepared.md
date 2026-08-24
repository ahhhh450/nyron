# Module Architecture Amendment 001 — EffectOperation PREPARED

Status: **FROZEN MODULE ARCHITECTURE AMENDMENT**
Authority: Lead Design Authority
Applies to: `Universal_Runtime_Module_Design_Report_v0.1.md` §19 EffectOperation
Reason: Explicit resolution of NYRON-D-004 architecture finding concerning the crash window before external effect dispatch.

## 1. Scope

This amendment makes one narrow semantic extension to the frozen Module baseline: `EffectOperation` gains a `PREPARED` state representing a durable operation identity and dispatch intent that exists before an external effect is dispatched.

No other Module execution, Capability, Resource, Packet, Activation, Run, fencing, Accounting, or Recovery invariant is changed.

## 2. Problem

The original frozen baseline starts the EffectOperation lifecycle at `ACTIVE`.

Two unsafe implementation choices follow if no pre-dispatch durable state exists:

1. Mark the operation `ACTIVE` before dispatch, which can falsely claim an external effect has started when it has not.
2. Dispatch externally before any durable operation identity exists, which creates a crash window where the external effect may have occurred but Nyron has no canonical operation identity with which to deduplicate, query, cancel, or reconcile it.

Neither behavior is acceptable under the existing rule that unknown past facts must not be guessed.

## 3. Amended State Set

The frozen EffectOperation state set is amended from:

```text
ACTIVE
REVOKE_REQUESTED
FENCED
COMPLETED
UNKNOWN
```

to:

```text
PREPARED
ACTIVE
REVOKE_REQUESTED
FENCED
COMPLETED
UNKNOWN
```

## 4. PREPARED Semantics

`PREPARED` means exactly:

> Nyron has durably created the EffectOperation identity and recorded the intent to attempt an external effect, but PREPARED alone is not evidence that the external effect was dispatched, accepted, started, completed, or rejected.

An EffectOperation that may create historical ambiguity after a crash MUST have a durable `operation_ref` before external dispatch.

Immediately before dispatch, the mediated boundary MUST revalidate current Attempt, fencing token, CapabilityGrant, scope, and applicable ResourceLease.

## 5. Dispatch Crash Window

The expected logical sequence is:

```text
validate request shape
→ commit EffectOperation(PREPARED)
→ revalidate effect authority at the actual boundary
→ external dispatch
→ record external acknowledgement/evidence when available
→ ACTIVE or COMPLETED
```

A crash can occur after external dispatch but before Nyron commits `ACTIVE` or `COMPLETED`.

Therefore:

> A recovered PREPARED operation MUST NOT be assumed to mean “not dispatched”.

Recovery must use external idempotency identity, provider lookup, process identity, artifact/hash evidence, or another reliable mechanism to determine history. If history cannot be determined, the EffectOperation becomes `UNKNOWN` and is handed to Reconciliation.

Blindly retrying a non-idempotent PREPARED operation with uncertain dispatch history is forbidden.

## 6. Transition Constraints

Canonical transitions may include:

```text
PREPARED → ACTIVE
PREPARED → COMPLETED
PREPARED → FENCED          # cancelled with evidence before dispatch
PREPARED → UNKNOWN         # dispatch history cannot be determined

ACTIVE → COMPLETED
ACTIVE → REVOKE_REQUESTED
ACTIVE → UNKNOWN

REVOKE_REQUESTED → FENCED
REVOKE_REQUESTED → COMPLETED
REVOKE_REQUESTED → UNKNOWN
```

A subsystem may define additional owner-local rejection metadata, but it MUST NOT fabricate external history.

## 7. Ownership Clarification

The phrase in the original Module baseline that `EffectOperation` is a “Kernel internal object” is clarified as follows:

> EffectOperation is a Kernel-visible internal canonical record required for correctness and fencing. Its domain lifecycle is owned by the Effect Authority subsystem. The Kernel Foundation supplies canonical persistence, owner enforcement, fencing primitives, transaction primitives, and causal/replay foundations; it does not absorb the EffectOperation domain state machine into the generic Kernel primitive taxonomy.

This clarification is compatible with the Overall Architecture rule that subsystem-specific state machines remain subsystem-owned.

## 8. Unchanged Requirements

The following frozen requirements remain unchanged:

- stale Attempts cannot canonical-commit;
- stale Attempts cannot initiate new mediated effects;
- actual effect boundaries revalidate authority;
- already-started external effects do not disappear when an Attempt becomes stale;
- conflicting replacement effects wait until old effects are confirmed fenced/completed or otherwise safely cleared;
- uncertain external history becomes `UNKNOWN` and enters Reconciliation;
- EffectOperation and BudgetReservation remain orthogonal facts and lifecycles;
- Resource existence does not imply permission;
- Capability, Resource, and Packet remain distinct.

## 9. Baseline Effect

This amendment is authoritative wherever it conflicts with the original §19 state list.

`Universal_Runtime_Module_Design_Report_v0.1.md` remains the frozen Module baseline together with this explicit amendment.
