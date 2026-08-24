# NYRON-D-004 — Lead Integration Clarification 003

**Status:** NORMATIVE INTEGRATED CANDIDATE CLARIFICATION / PRE-FREEZE  
**Applies to:** `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`  
**Authority:** Nyron Lead Design Authority

This clarification resolves two correctness issues found during Lead re-review of D-004. It does not amend the Frozen Module baseline; it makes the D-004 candidate conform strictly to Frozen Amendment 001 and closes the safety-critical portion of `OQ-03`.

---

## 1. No Exception to Nyron PREPARED-before-dispatch

D-004 §20 currently states:

> Dispatch before durable operation identity is forbidden unless an adapter provides an equivalent durable external dedupe/recovery identity protocol.

That exception is **not normative** and is superseded by this clarification.

Frozen Amendment 001 requires that every external effect capable of creating crash ambiguity have a durable Nyron `EffectOperation.operation_ref` before dispatch.

Therefore the normative rule is:

```text
crash-ambiguous external effect
-> durable Nyron EffectOperation(PREPARED, operation_ref)
-> boundary authority revalidation
-> external dispatch
```

An external provider idempotency key, request ID, process identity, remote job ID, artifact identity, or other external recovery identity is useful additional evidence and SHOULD be durably bound to the Nyron EffectOperation where available.

It is **not** a substitute for creating the Nyron EffectOperation before dispatch.

### Added invariant

**ARE-INV-18 — External Recovery Identity Does Not Replace PREPARED**

For any external operation that can create crash-ambiguous history, Nyron MUST commit durable `EffectOperation(PREPARED)` identity before dispatch. Provider/external idempotency or recovery identity may strengthen dedupe/reconciliation but cannot replace the Nyron pre-dispatch canonical operation identity.

---

## 2. PREPARED Revalidation Failure

After `PREPARED` is committed, the actual dispatch boundary revalidates current Attempt, fencing, CapabilityGrant, scope, and applicable ResourceLease.

If that revalidation fails **before any external dispatch occurred**, Effect Authority may transition the PREPARED operation to `FENCED` only when it can establish from authoritative local/adapter evidence that dispatch did not occur.

If dispatch status is ambiguous — including after crash/restart where PREPARED alone cannot establish non-dispatch — the operation MUST NOT be treated as safely cancelled/non-dispatched. It becomes `UNKNOWN` or follows owner-local reconciliation consistent with Amendment 001.

This prevents PREPARED records from becoming dangling pseudo-failures or from being interpreted as proof of non-dispatch.

---

## 3. Deterministic Effect Conflict Scope

D-004 `OQ-03` is closed at the architecture-safety level.

Nyron does **not** require one hardcoded global conflict-domain enum. Instead, every EffectClass / CapabilityType contract that can participate in replacement-conflict safety MUST define or deterministically derive a machine-checkable **EffectConflictScope** sufficient to answer whether two operations are proven disjoint.

The scope may be derived from immutable/current-authoritative inputs such as:
- EffectClass/version;
- exact CapabilityType/version and Grant scope;
- Workspace/project/resource identity where semantically relevant;
- target path/object/endpoint/provider/job/process conflict key;
- Resource / ResourceLease compatibility/conflict domain;
- operation-specific immutable semantic target identity.

Exact schemas may remain EffectClass-specific and versioned.

### Required overlap rule

For two operations/scopes A and B, the relevant authority contract must deterministically classify:

```text
PROVEN_DISJOINT
CONFLICTING
UNKNOWN_OVERLAP
```

Safety rule:

```text
UNKNOWN_OVERLAP -> treat as CONFLICTING
```

A subsystem may allow concurrency only when disjointness is positively proven under the applicable immutable/versioned conflict contract.

Transient worker state, UI labels, hash-map order, wall-clock arrival, adapter guesses, or absence of current observation MUST NOT prove disjointness.

### Added invariant

**ARE-INV-19 — Unproven Disjointness Fails Closed**

Replacement or concurrent authority for externally consequential work may proceed in parallel only when the applicable versioned conflict contract proves the operations disjoint. Unknown or unresolved overlap is treated as conflicting.

---

## 4. Conflict-Clearance Barrier by Effect State

For an old Attempt operation whose conflict scope overlaps new requested work:

- `ACTIVE` -> blocks conflicting new authority;
- `REVOKE_REQUESTED` -> blocks conflicting new authority;
- `UNKNOWN` -> blocks conflicting new authority by default;
- `PREPARED` -> blocks conflicting new authority unless Effect Authority can prove non-dispatch and commit `FENCED`, or otherwise establish an owner-authoritative safe disposition consistent with Amendment 001;
- `FENCED` -> no longer blocks on that operation's active-effect basis;
- `COMPLETED` -> no longer represents an active-effect fence, but semantic duplicate/retry policy remains governed by Runtime/effect idempotency contracts and MUST NOT be inferred merely from completion.

Resource and Capability owner-specific clearance remains independently required where applicable, consistent with `NYRON-D-004_Lead_Integration_Clarification_002.md`.

### Added invariant

**ARE-INV-20 — PREPARED Is Conflict-Relevant Until Non-dispatch Is Proven**

A PREPARED operation cannot be treated as harmless merely because ACTIVE was never committed. Where dispatch history may be ambiguous, overlapping replacement authority remains blocked until Effect Authority establishes a safe owner-authoritative state.

---

## 5. Open Question Disposition

- `OQ-03` generic conflict-domain representation: **RESOLVED at architecture-safety level** by the versioned EffectConflictScope + fail-closed overlap contract above. Concrete EffectClass schemas remain implementation/domain design.
- `OQ-01` CapabilityType version identity syntax remains non-blocking naming/schema detail.
- `OQ-02` policy ownership is resolved by D-010/PWP integration and Clarification 002.
- `OQ-04` initial Browser capability vocabulary remains non-blocking extensibility choice.
- `OQ-05` external Resource adoption remains a later bounded feature and must fail closed if implemented without provenance.
- `OQ-06` Human Interaction ownership is resolved by frozen D-009.
- `OQ-07` Recovery/Accounting behavior is resolved by frozen D-005 within its scope.

---

## 6. Lead Re-review Disposition

Before this clarification, D-004 was **not freeze-clean** because §20 contained a frozen-amendment exception and OQ-03 left the conflict-overlap safety contract under-specified.

With this clarification applied, the Lead re-review finds no remaining blocking conflict with:
- Frozen Module Architecture;
- Frozen Amendment 001;
- Frozen Runtime D-003;
- Frozen Accounting / Recovery D-005;
- Frozen Distribution D-007;
- Frozen External Interfaces D-008;
- Frozen Human Interaction D-009;
- Frozen Project / Workspace / Policy Context D-010.

D-004 is now **LEAD RE-REVIEW PASS / INDEPENDENT REVIEW READY**.
