# NYRON-D-004 — Gate-5 Live Module Broker ABI Clarification Candidate v0.3

**Status:** `CANDIDATE — NOT FROZEN — NO ARCHITECTURE AUTHORITY`
**Produced by:** `NYRON-T-20260826-068` (Claude Code, DESIGN_CORRECTION task)
**Corrects:** `NYRON-T-20260826-066` v0.2, content commit `3c00ac92e553becae7ce2986799f9c5593b69ade` (REJECTED by `NYRON-T-20260826-067`, FAIL — v0.2 is NOT normative and is superseded, not amended in place)
**Resolves (candidate, not yet closing):** `NYRON-T-20260826-067-F-001`; parent `NYRON-T-20260826-062-F-001`
**Applies to:** `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md` (§9, §15, §19, §26) and `design/Universal_Runtime_Module_Design_Report_v0.1.md` (§11, §18, §29, §38), read together with Frozen Clarification 004.

---

## 0. Non-Normative Status (read this first)

This document is a **candidate only**. It has **no architecture authority**, cannot be implemented against, and cannot itself close `NYRON-T-20260826-062-F-001` or `NYRON-T-20260826-067-F-001`. It becomes eligible for implementation only after an independent Codex targeted re-review, explicit Design Authority acceptance/freeze, and a newly and correctly scoped Gate-5 implementation Task opened against the frozen result.

v0.2 (`3c00ac92e553becae7ce2986799f9c5593b69ade`) is superseded and must not be treated as normative or implemented. `NYRON-T-20260826-067` confirmed v0.2 genuinely closed `065-F-001` through `065-F-004` (preserved unchanged below) but found one new blocking result-classification defect (`067-F-001`, §7 below) in how a different-payload request against an already-bound `operation_ref` was mapped. This v0.3 corrects **only** that defect. Every other v0.2 design decision is carried forward unchanged; sections that changed are marked; sections that did not are marked `(unchanged from v0.2)`.

---

## 1. Module-facing delivery model *(unchanged from v0.2)*

**Decision: inert identity handles plus exactly one callable broker, both delivered as additional fields on `RuntimeContext`.**

```text
RuntimeContext
- activation_ref            (existing, descriptive only)
- run_ref                   (existing, descriptive only)
- attempt_seq               (existing, descriptive only)
- fencing_token              (existing, descriptive only)
- accounting_scope_ref      (existing, descriptive only)
- capability_handles: tuple[CapabilityHandle, ...]
- resource_handles: tuple[ResourceHandle, ...]
- metadata: tuple[tuple[str, str], ...]           (unused by the broker)
- effect_broker: BoundedWriteEffectBroker | None
```

`effect_broker` is `None` whenever the Host has no live-effect capability to offer (a PURE module, no matching handle, or no resolvable causal reference for this Activation — §4a).

---

## 2. Concrete Python invocation ABI *(corrected: §2b return type union extended)*

**Broker object/type identity:** `nyron_kernel.host.BoundedWriteEffectBroker`, a Host-constructed instance with **exactly one public method** and no other public attributes/methods.

### 2a. What the broker privately holds *(unchanged from v0.2)*

- the real `EffectAuthority` instance;
- the real, immutable `AttemptAuthority` object captured once at construction time, never re-resolved (§5);
- the resolved `caused_by_ref` string, captured once at construction from `Activation.trigger_delivery_ref` (§4a);
- the exact frozenset of `CapabilityHandle`/`ResourceHandle` values that belong to this RuntimeContext (§4 membership check).

Same-process Python privacy conventions on these private attributes are API-surface organization only, not a physical-reachability guarantee — see §5a and §9 (unchanged from v0.2, closing `065-F-001`).

### 2b. Method and public return algebra *(corrected: fourth outcome type added)*

```text
BoundedWriteEffectBroker.dispatch_bounded_write(
    capability_handle: CapabilityHandle,
    resource_handle: ResourceHandle,
    intent_ref: str,
    payload: str,
) -> BoundedWriteDispatched
  | BoundedWriteRejected
  | BoundedWriteUnknown
  | BoundedWriteIdentityConflict          # NEW in v0.3 — closes 067-F-001
```

**Arguments — exactly these four, nothing else** (unchanged from v0.2): `capability_handle`, `resource_handle` (must each be a value already present in this Module's own `RuntimeContext`); `intent_ref` (non-empty `str`, ≤128 UTF-8 bytes, `[A-Za-z0-9_.:-]+`); `payload` (`str`, ≤4096 UTF-8 bytes).

**Return type — exactly one of four frozen dataclasses. Never a raw `EffectOperation`, never a raw `EffectError`, never an exception for any Module-input-shape or identity condition (§2c, unchanged):**

```text
BoundedWriteDispatched
- operation_ref: str
- state: str                    # always the literal "COMPLETED" in this slice

BoundedWriteRejected
- operation_ref: str | None     # None only for a broker-level shape rejection (§7e)
- reason_code: str              # BROKER_* for shape rejections; otherwise the
                                 # underlying EffectError.code, used only when
                                 # canonical truth is a definite non-UNKNOWN,
                                 # non-COMPLETED, SAME-IDENTITY state

BoundedWriteUnknown
- operation_ref: str
- note: str                     # fixed constant, unchanged from v0.2

BoundedWriteIdentityConflict    # NEW in v0.3
- operation_ref: str            # always present — an identity conflict can only
                                 # occur once an operation_ref has been derived
                                 # and an existing row under that identity was found
- existing_state: str           # the exact canonical state of the PRE-EXISTING
                                 # operation row, one of PREPARED / ACTIVE /
                                 # REVOKE_REQUESTED / FENCED / COMPLETED / UNKNOWN
- reason_code: str               # fixed literal "EFFECT_OPERATION_IDENTITY_CONFLICT"
```

`BoundedWriteIdentityConflict` is a fourth, structurally distinct outcome — not a variant of `BoundedWriteRejected`, not a variant of `BoundedWriteDispatched`, and not a variant of `BoundedWriteUnknown`. Its purpose is to make it structurally impossible for a caller to conflate "the pre-existing operation's own canonical truth" with "the outcome of the current, different, request" by pattern-matching on result shape.

**`existing_state` is truth about the pre-existing operation, never about the current request.** The current request itself never dispatched, never completed, and never became UNKNOWN — it was never admitted as a distinct operation at all, because its identity was already claimed by a different (already-existing) request. See §7 for the exact rule this enforces.

### 2c. Error posture *(unchanged from v0.2, closing 065-F-003)*

The public method never raises for any Module-input condition, including an identity conflict — that is now `BoundedWriteIdentityConflict`, a returned value, not an exception. A genuine Host/programmer fault (§7d) remains explicitly outside this public return algebra, as in v0.2.

---

## 3. First bounded effect surface *(unchanged from v0.2)*

`nyron.kernel.managed-resource-bounded-write@1`. No new effect class; no change to `EffectRequest`/`EffectOperation`/`EffectAuthority`.

---

## 4. Handle → request binding *(unchanged from v0.2, including §4a causal binding — closing 065-F-004)*

Unchanged: Module selects handles already present in its own `RuntimeContext`; the broker derives `operation_ref` (§6) and supplies the captured `AttemptAuthority` (§5) and `caused_by_ref` (§4a, bound to `Activation.trigger_delivery_ref`, resolved once at broker-construction time via the existing `ActivationRepository.resolve()`; if unresolvable, `effect_broker` is `None` rather than fabricating a value — fail closed). No new causal namespace is introduced in v0.3.

---

## 5. Real authority boundary *(unchanged from v0.2, including §5a reachability correction — closing 065-F-001)*

**The broker performs no authority decision of its own.** It always passes through the same, immutable `AttemptAuthority` object captured once at construction — never re-resolving "current" at call time, so a stale-R1 Module invocation is never silently re-attributed to R2. All real currentness/Grant/Lease/Gate-4C-conflict/target checks happen fresh, atomically, inside `EffectAuthority._admit_dispatch()`'s existing canonical transaction. §5a's corrected statement that same-process Python privacy is convention, not physical isolation, is unchanged and is not affected by this correction — v0.3 changes only *result classification after `EffectAuthority.execute()` returns or raises* (§7), not the authority boundary itself.

Canonical `run_ref` uniqueness remains a stated, relied-upon assumption (unchanged).

---

## 6. Operation identity ownership *(unchanged from v0.2)*

```text
operation_ref = "module-effect:" +
    sha256(run_ref + "\x00" + str(attempt_seq) + "\x00" + intent_ref).hexdigest()
```

using the broker's own privately captured `run_ref` and `attempt_seq` (never a value read back from the Module-visible `RuntimeContext` fields — §8).

`067-F-001`'s defect was never in this derivation — a different payload under the same `(run_ref, attempt_seq, intent_ref)` correctly derives the *same* `operation_ref` exactly as designed (this is what makes same-identity replay detection possible at all). The defect was purely in how the broker classified the *result* once `EffectAuthority`'s own existing `_require_identical_replay` check (unmodified, accepted, Gate-3) correctly rejected the mismatch. §7 corrects that classification; this section is unchanged.

---

## 7. Return / error mapping *(corrected: identity-conflict precedence — closes 067-F-001)*

### 7.0 Corrected governing rule

v0.2's governing rule was: *"whenever a call has produced an `operation_ref` and `EffectAuthority.execute()` raises, resolve canonical state and classify from that truth."* That rule is retained but is now **subordinate to a prior, higher-precedence check**:

> **Before** canonical state is used to classify *any* raised `EffectError` as `BoundedWriteUnknown` or ordinary `BoundedWriteRejected`, the broker MUST first check whether `error.code == "EFFECT_OPERATION_IDENTITY_CONFLICT"`. If so, the call is classified as `BoundedWriteIdentityConflict` — a category the v0.2 resolve-and-map rule (§7.2 below) never applies to. Canonical state is still read (via the same `EffectAuthority.resolve(operation_ref)`), but it is placed into `existing_state` as informational truth about the *pre-existing* operation, never used to select between `BoundedWriteDispatched` / `BoundedWriteUnknown` / `BoundedWriteRejected` for the *current* request.

This is the exact correction `067-F-001` required: request-identity-conflict truth ("this request was not accepted as this operation's identity") and pre-existing-operation truth ("that operation's own canonical state is X") are two different facts, and v0.2 conflated them by feeding both into the same single resolve-then-map branch. v0.3 gives identity-conflict its own branch, checked first.

### 7.1 Exact classification order

```text
1. validate broker-level Module input shape / handle context-membership   [§7e]
   -> fail: BoundedWriteRejected(operation_ref=None, reason_code="BROKER_*")

2. derive operation_ref                                                    [§6]

3. call EffectAuthority.execute(request)

4. no exception raised, returns EffectOperation(state="COMPLETED")
   -> BoundedWriteDispatched(operation_ref=operation_ref, state="COMPLETED")  [§7a]

5. EffectError raised:
   5a. error.code == "EFFECT_OPERATION_IDENTITY_CONFLICT"                  [§7b, NEW]
       -> row := EffectAuthority.resolve(operation_ref)
       -> if row is None: Host-fault, no Module-visible result defined      [§7d]
       -> else: BoundedWriteIdentityConflict(
                    operation_ref=operation_ref,
                    existing_state=row.state,
                    reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT")
          # row.state is NEVER used to select Dispatched/Unknown/Rejected here.

   5b. error.code != "EFFECT_OPERATION_IDENTITY_CONFLICT"                  [§7c, unchanged from v0.2]
       -> row := EffectAuthority.resolve(operation_ref)
       -> row is None            -> BoundedWriteRejected(operation_ref, error.code)
       -> row.state == COMPLETED -> BoundedWriteDispatched(operation_ref, "COMPLETED")
       -> row.state == UNKNOWN   -> BoundedWriteUnknown(operation_ref, note="...")
       -> row.state in {PREPARED, ACTIVE, REVOKE_REQUESTED, FENCED}
                                  -> BoundedWriteRejected(operation_ref, error.code)
```

Step 5a and step 5b are mutually exclusive and checked in this exact order — `error.code` is inspected *before* `resolve()`'s result is used for classification, precisely so that an identity conflict can never fall into 5b's same-identity mapping (which is what produced the `067-F-001` defect: a `COMPLETED` pre-existing row being reported as if it were this request's own completion).

### 7.2 Same-identity truth table *(unchanged from v0.2 — retained exactly, closes 065-F-002/F-003)*

This table applies **only** when `error.code != "EFFECT_OPERATION_IDENTITY_CONFLICT"`, i.e. the raised error concerns the *same* request identity that this call itself is attempting (a durable replay of the Module's own earlier identical call, or a same-call internal ambiguity):

| Condition | Result |
|---|---|
| `execute()` returns, `state == COMPLETED` | `BoundedWriteDispatched` |
| `execute()` raises, `resolve()` shows `COMPLETED` | `BoundedWriteDispatched` (safe identical replay, unchanged) |
| `execute()` raises, `resolve()` shows `UNKNOWN` | `BoundedWriteUnknown` |
| `execute()` raises, `resolve()` shows `PREPARED`/`ACTIVE`/`REVOKE_REQUESTED`/`FENCED` | `BoundedWriteRejected(reason_code=error.code)` |
| `execute()` raises, `resolve()` returns `None` | `BoundedWriteRejected(operation_ref, reason_code=error.code)` |
| broker-level shape/membership rejection (pre-identity) | `BoundedWriteRejected(operation_ref=None, reason_code="BROKER_*")` |

### 7.3 Different-identity (identity-conflict) truth table *(NEW — required by Task 068)*

This table applies **only** when `error.code == "EFFECT_OPERATION_IDENTITY_CONFLICT"` — the current request's `(effect_class, authority, capability_grant_ref, resource_ref, resource_lease_ref, payload, payload_hash, caused_by_ref)` tuple differs from the already-existing row bound to the same derived `operation_ref` (i.e. a different `payload`, since `intent_ref`+`run_ref`+`attempt_seq` — and therefore `operation_ref` — are identical by construction, and every other field this broker supplies is itself deterministic per Attempt, so a payload difference is the only way a Module can reach this state through this ABI):

| Existing row `existing_state` | Required result |
|---|---|
| `PREPARED` | `BoundedWriteIdentityConflict(operation_ref, existing_state="PREPARED", reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT")` |
| `ACTIVE` | `BoundedWriteIdentityConflict(operation_ref, existing_state="ACTIVE", reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT")` |
| `REVOKE_REQUESTED` | `BoundedWriteIdentityConflict(operation_ref, existing_state="REVOKE_REQUESTED", reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT")` |
| `FENCED` | `BoundedWriteIdentityConflict(operation_ref, existing_state="FENCED", reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT")` |
| `COMPLETED` | `BoundedWriteIdentityConflict(operation_ref, existing_state="COMPLETED", reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT")` |
| `UNKNOWN` | `BoundedWriteIdentityConflict(operation_ref, existing_state="UNKNOWN", reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT")` |

In every row of this table the result type is identical (`BoundedWriteIdentityConflict`); only `existing_state` varies, because in every one of these cases the *current request's own outcome* is identically "not accepted as this identity" — what varies is only the informational truth about the *pre-existing* operation. This directly satisfies the required prohibitions:

- `existing_state == "COMPLETED"` is carried inside `BoundedWriteIdentityConflict`, never surfaced as `BoundedWriteDispatched` — a different-payload request can never be reported as dispatched merely because an unrelated earlier request with that identity happened to complete.
- `existing_state in {"ACTIVE", "REVOKE_REQUESTED"}` is carried explicitly and visibly in a structurally distinct result, never folded into an ordinary `BoundedWriteRejected` that would look identical to a definite terminal rejection — the caller can see the prior work is still nonterminal.
- `existing_state == "UNKNOWN"` is carried explicitly — the historical uncertainty about the *pre-existing* operation is preserved and visible, not discarded, even though the *current* request's own classification (identity conflict) is itself definite.
- `existing_state == "FENCED"` is state truth only; `BoundedWriteIdentityConflict` defines and grants no retry authorization — a Module cannot use this result to conclude a same-identity retry is now safe (unchanged posture from v0.2 §6/§8 — no semantic retry clearance is introduced anywhere in this document).

### 7a. Accepted and completed *(unchanged from v0.2)*

`EffectAuthority.execute()` returns `state == "COMPLETED"` without raising. Broker returns `BoundedWriteDispatched` directly — no `resolve()` call needed.

### 7b. Identity conflict *(NEW, replaces the defective part of v0.2 §7b/§7c)*

Covered in full in §7.0/§7.1/§7.3 above. Worked examples in §12.

### 7c. Same-identity UNKNOWN — synchronous transition and durable replay *(unchanged from v0.2, closing 065-F-002)*

Both cases (an internal ambiguity arising synchronously within this call, and a replay of an already-durable `UNKNOWN` row under the *same* `intent_ref`/payload) are unchanged from v0.2: `error.code != "EFFECT_OPERATION_IDENTITY_CONFLICT"` in both, `resolve(operation_ref)` shows `UNKNOWN`, broker returns `BoundedWriteUnknown(operation_ref, note="external consequence of this operation is not confirmed; do not treat as success or failure; do not retry this intent_ref without independent reconciliation")`. `error.code` is discarded, not surfaced, exactly as in v0.2.

### 7d. Host-fault: identity conflict with no resolvable row *(NEW, required by Task 068)*

If `error.code == "EFFECT_OPERATION_IDENTITY_CONFLICT"` but `EffectAuthority.resolve(operation_ref)` unexpectedly returns `None`, this indicates a state impossible under the accepted single-writer, no-delete `effect_operations` model (`EFFECT_OPERATION_IDENTITY_CONFLICT` is only ever raised by `_require_identical_replay` after `EffectAuthority.resolve()`/an internal existence check already found a row under that exact identity, and no code path in the accepted implementation ever deletes an `effect_operations` row). This is a **Host/programmer fault**, not a Module-input condition, and — consistent with the §2c carve-out (unchanged from v0.2) — is explicitly outside the normal Module-visible return algebra: the broker does not fabricate an `existing_state`, does not report success, and does not silently degrade to an ordinary `BoundedWriteRejected` masquerading as a normal outcome. No specific Module-visible shape is defined for it in this bounded slice; it is treated the same as any other Host-internal invariant violation.

### 7e. Broker-level shape rejection *(unchanged from v0.2, closing 065-F-003)*

An out-of-context handle, malformed `intent_ref`, or malformed `payload` is rejected before any `EffectRequest` is constructed, before any `operation_ref` is derived, and before any `resolve()` call: `BoundedWriteRejected(operation_ref=None, reason_code="BROKER_HANDLE_NOT_IN_CONTEXT" | "BROKER_INTENT_REF_INVALID" | "BROKER_PAYLOAD_INVALID")`. Returned value, never a raised exception (§2c).

### 7f. Process crash mid-call *(unchanged from v0.2)*

If the Host process crashes strictly between dispatch admission and this synchronous call returning, the call does not return at all. Not a fifth outcome shape; the honest absence of a return.

---

## 8. RuntimeContext / handle field-level contract *(unchanged from v0.2)*

Table and binding correction (Module-visible `attempt_seq`/`fencing_token` are descriptive-only, never re-fed into a live request) unchanged. No new fields added to `RuntimeContext`, `CapabilityHandle`, or `ResourceHandle` in v0.3 — only the broker method's *return* algebra gained a fourth member (§2b).

---

## 9. Trusted-mode threat claim *(unchanged from v0.2, closing 065-F-001)*

TRUSTED MODULE MODE only; same-process Python privacy is convention, not isolation; the supported ABI does not hand raw Owner/Store/DB/`AttemptAuthority`/`Grant`/`Lease`/path objects to Modules; a malicious in-process Python module may introspect/import internals and reach the broker's private state anyway, which is explicitly outside the current supported security claim; hostile third-party support still requires real enforceable isolation later. `067-F-001`'s correction is a result-classification fix and has no bearing on the threat model.

---

## 10. Standing interlocks *(unchanged from v0.2, reconfirmed)*

**`NYRON-T-20260825-038-F-001` — confirmed NOT ACTIVATED:** no Module filesystem API; no raw path exposure anywhere in `BoundedWriteIdentityConflict` or any other result type (`existing_state` is a plain state-name string, never a path).

**`NYRON-T-20260826-043-F-001` — confirmed NOT ACTIVATED:** the added branch in §7.1 is a single additional `if` on `error.code` before the existing `resolve()` call already present in v0.2 — no new transaction, no new connection, no retry loop, no thread/worker/async/pool. The flow remains one synchronous call ending in `EffectAuthority.execute()`'s existing canonical transaction plus at most one existing, unmodified `resolve()` read.

---

## 11. Machine-reviewable invariants *(invariant 9 extended; new invariant 11 added)*

1–8, 10. **Unchanged from v0.2** (supported-ABI-vs-reachability distinction; handles as selectors not authority; broker cannot authorize without fresh Effect Authority admission; membership scoping; no direct canonical mutation; Module cannot supply Attempt facts; no raw target path; no retry authorization from FENCED/COMPLETED; trusted-mode-not-isolation).
9. **Extended.** UNKNOWN remains uncertain and is never converted to success/failure certainty by Host, and is never collapsed into ordinary rejection (v0.2) — **and, new in v0.3, this extends to UNKNOWN discovered as `existing_state` inside an identity conflict: it is preserved and visibly reported, never discarded merely because the current request's own classification is "identity conflict" rather than "unknown."**
11. **New.** A request whose derived `operation_ref` already durably exists under a *different* payload/identity can never be reported as `BoundedWriteDispatched`, and the pre-existing operation's own canonical state can never be misattributed as the outcome of the current, different, request. The two truths — "this request was not accepted as this identity" and "the pre-existing operation's own state is X" — are always represented by structurally distinct fields (`BoundedWriteIdentityConflict.reason_code` vs `.existing_state`) and are never merged into a single ambiguous field or a result type shared with same-identity outcomes. Closes `067-F-001`.

---

## 12. Required sequence diagrams *(v0.2's five diagrams unchanged; five new diagrams below per Task 068)*

v0.2's five sequences (§12 a–e of v0.2: successful completed call; definite same-identity admission rejection; same-call UNKNOWN transition; durable same-identity UNKNOWN replay; broker-level shape rejection) are unchanged and still apply exactly as written there — none of them involve `EFFECT_OPERATION_IDENTITY_CONFLICT`, so §7.0's new precedence check never activates for them, and their outcomes are identical to v0.2.

### f. Different payload vs. existing `COMPLETED` — identity conflict, NOT dispatched

```text
[operation_ref X already exists, state=COMPLETED, from an earlier call with payload P1]

Module -> dispatch_bounded_write(capability_handle, resource_handle,
                                  same intent_ref, payload=P2 != P1)
  -> operation_ref derives to the SAME value X                          [§6]
  -> EffectAuthority.execute(request with payload=P2)
       -> prepare(): existing := resolve(X) -> row with payload=P1, state=COMPLETED
       -> _require_identical_replay(existing, request(P2), hash(P2)):
            existing.payload (P1) != request.payload (P2)
          raise EffectError("EFFECT_OPERATION_IDENTITY_CONFLICT")
       # existing row X is NOT mutated by this check
  -> broker: error.code == "EFFECT_OPERATION_IDENTITY_CONFLICT"          [§7.1 step 5a]
       -> row := EffectAuthority.resolve(X)  =>  row.state == "COMPLETED"
<- BoundedWriteIdentityConflict(operation_ref=X, existing_state="COMPLETED",
                                 reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT")

# NOT BoundedWriteDispatched — the P2 request never ran; COMPLETED describes
# the unrelated P1 operation that already owns identity X.
```

### g. Different payload vs. existing `ACTIVE` — identity conflict carrying ACTIVE, not hidden

```text
[operation_ref X already exists, state=ACTIVE, from an earlier call still
 mid-flight (crash-hook-tested scenario, or a legitimately long-running
 admitted operation not yet completed)]

Module -> dispatch_bounded_write(..., same intent_ref, payload=P2 != P1)
  -> operation_ref derives to X
  -> EffectAuthority.execute(request with payload=P2)
       -> prepare(): existing := resolve(X) -> row with payload=P1, state=ACTIVE
       -> _require_identical_replay(...): payload mismatch
       raise EffectError("EFFECT_OPERATION_IDENTITY_CONFLICT")
  -> broker: identity-conflict branch -> row := resolve(X) => state == "ACTIVE"
<- BoundedWriteIdentityConflict(operation_ref=X, existing_state="ACTIVE",
                                 reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT")

# NOT an ordinary BoundedWriteRejected(reason_code="EFFECT_DISPATCH_AUTHORITY_REJECTED")
# or similar — that shape would look identical to a definite terminal
# rejection and would hide that operation X is still nonterminal/ongoing.
```

### h. Different payload vs. existing `REVOKE_REQUESTED` — identity conflict carrying REVOKE_REQUESTED

```text
[operation_ref X already exists, state=REVOKE_REQUESTED — a prior R1
 operation now being actively fenced after replacement, per accepted
 Gate-4B semantics; unrelated to this call]

Module -> dispatch_bounded_write(..., same intent_ref, payload=P2 != P1)
  -> operation_ref derives to X
  -> EffectAuthority.execute(...) -> prepare() -> _require_identical_replay
     raise EffectError("EFFECT_OPERATION_IDENTITY_CONFLICT")
  -> broker: identity-conflict branch -> row := resolve(X) => state == "REVOKE_REQUESTED"
<- BoundedWriteIdentityConflict(operation_ref=X, existing_state="REVOKE_REQUESTED",
                                 reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT")
```

### i. Different payload vs. existing `UNKNOWN` — identity conflict carrying UNKNOWN; uncertainty preserved

```text
[operation_ref X already durably UNKNOWN from an earlier ambiguous call]

Module -> dispatch_bounded_write(..., same intent_ref, payload=P2 != P1)
  -> operation_ref derives to X
  -> EffectAuthority.execute(...) -> prepare() -> _require_identical_replay
     raise EffectError("EFFECT_OPERATION_IDENTITY_CONFLICT")
     # note: this is NOT the same code path as §7c's UNKNOWN case — that
     # path is entered only when payload matches and execute() itself,
     # not the identity-replay check, is what raises.
  -> broker: identity-conflict branch -> row := resolve(X) => state == "UNKNOWN"
<- BoundedWriteIdentityConflict(operation_ref=X, existing_state="UNKNOWN",
                                 reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT")

# The historical uncertainty about X is preserved and visible via
# existing_state — it is not silently discarded just because the current
# P2 request's own classification (identity conflict) is itself definite.
```

### j. Same payload vs. existing durable `UNKNOWN` — v0.2 behavior confirmed unchanged

```text
[operation_ref X already durably UNKNOWN, from an earlier call with payload P1]

Module -> dispatch_bounded_write(..., same intent_ref, payload=P1  # SAME]
  -> operation_ref derives to X
  -> EffectAuthority.execute(request with payload=P1)
       -> prepare(): existing := resolve(X) -> row payload=P1, state=UNKNOWN
       -> _require_identical_replay(...): all fields match -> returns normally,
          no IDENTITY_CONFLICT raised
       -> execute()'s own state-machine: state != PREPARED and != COMPLETED
       raise EffectError("EFFECT_OPERATION_NOT_DISPATCHABLE")
  -> broker: error.code != "EFFECT_OPERATION_IDENTITY_CONFLICT"    [§7.1 step 5b]
       -> row := resolve(X) => state == "UNKNOWN"
<- BoundedWriteUnknown(operation_ref=X, note="...")

# Unchanged from v0.2 §7d — confirms the identity-conflict correction did
# not alter same-payload UNKNOWN handling.
```

---

## 13. Explicit non-goals confirmed unaffected

Unchanged from v0.2. No new effect classes, no generalized SDK, no new Owner APIs, no schema/production/test changes, no reconciliation/async/worker semantics, no new retry-authorization semantics, no new causal namespace. The only new surface introduced anywhere in v0.3 is the `BoundedWriteIdentityConflict` result type and the `error.code`-first precedence check that selects it (§2b, §7).
