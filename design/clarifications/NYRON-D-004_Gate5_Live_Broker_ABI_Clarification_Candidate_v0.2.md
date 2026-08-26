# NYRON-D-004 — Gate-5 Live Module Broker ABI Clarification Candidate v0.2

**Status:** `CANDIDATE — NOT FROZEN — NO ARCHITECTURE AUTHORITY`
**Produced by:** `NYRON-T-20260826-066` (Claude Code, DESIGN_CORRECTION task)
**Corrects:** `NYRON-T-20260826-064` v0.1, content commit `1a8672dea011b7f787238437a0250a778c3ba13c` (REJECTED by `NYRON-T-20260826-065`, FAIL — v0.1 is NOT normative and is superseded, not amended in place)
**Resolves (candidate, not yet closing):** `NYRON-T-20260826-065-F-001`, `F-002`, `F-003`, `F-004`; parent `NYRON-T-20260826-062-F-001`
**Applies to:** `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md` (§9, §15, §19, §26) and `design/Universal_Runtime_Module_Design_Report_v0.1.md` (§11, §18, §29, §38), read together with Frozen Clarification 004.

---

## 0. Non-Normative Status (read this first)

This document is a **candidate only**. It has **no architecture authority**, cannot be implemented against, and cannot itself close `NYRON-T-20260826-062-F-001` or any `065-F-*` finding. It becomes eligible for implementation only after:

1. an independent Codex targeted re-review, and
2. explicit acceptance/freeze by the Design Authority, and
3. a newly and correctly scoped Gate-5 implementation Task is opened against the frozen result.

v0.1 (`1a8672dea011b7f787238437a0250a778c3ba13c`) is superseded and must not be treated as normative or implemented. Its four review findings (`065-F-001..F-004`) are addressed below by targeted correction; every other Task-065 PASS conclusion is preserved unchanged (§1, §3, §4, §5, §6, §8 core content below are the same design decisions as v0.1 unless a correction required wording adjustment).

---

## 1. Module-facing delivery model *(unchanged from v0.1 — PASS)*

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

`effect_broker` is `None` whenever the Host has no live-effect capability to offer (a PURE module, no matching handle, or — new in v0.2, §4a — no resolvable causal reference for this Activation). It exposes exactly one method for exactly one effect class.

---

## 2. Concrete Python invocation ABI *(corrected: §2b return algebra, §2c error posture)*

**Broker object/type identity:** `nyron_kernel.host.BoundedWriteEffectBroker`, a Host-constructed instance with **exactly one public method** and no other public attributes/methods.

### 2a. What the broker privately holds

- the real `EffectAuthority` instance;
- the real, immutable `AttemptAuthority` object captured once at RuntimeContext/broker construction time (never re-resolved — §5);
- the resolved `caused_by_ref` string, captured once at construction (§4, corrected);
- the exact frozenset of `CapabilityHandle`/`ResourceHandle` values that belong to this RuntimeContext (§4 membership check).

**Correction from v0.1 (065-F-001):** the fact that these values are held as non-public/underscore-prefixed Python attributes on the broker instance is an **API-surface convention**, not a claim about what is physically reachable in the process. See §5a for the corrected reachability statement; §11 invariant 1 is restated to match.

### 2b. Method and public return algebra

```text
BoundedWriteEffectBroker.dispatch_bounded_write(
    capability_handle: CapabilityHandle,
    resource_handle: ResourceHandle,
    intent_ref: str,
    payload: str,
) -> BoundedWriteDispatched | BoundedWriteRejected | BoundedWriteUnknown
```

**Arguments — exactly these four, nothing else** (unchanged from v0.1):

- `capability_handle` — must be one of the `CapabilityHandle` values already present in this Module's own `RuntimeContext.capability_handles`.
- `resource_handle` — must be one of the `ResourceHandle` values already present in this Module's own `RuntimeContext.resource_handles`.
- `intent_ref` — a short Module-chosen label (non-empty `str`, ≤ 128 UTF-8 bytes, `[A-Za-z0-9_.:-]+` only) identifying "this logical write attempt" for replay purposes (§6). Not the operation identity itself.
- `payload` — the bounded write content (`str`, ≤ 4096 UTF-8 bytes, unchanged `EffectAuthority._MAX_PAYLOAD_BYTES` bound).

**Return type — exactly one of three frozen dataclasses. Never a raw `EffectOperation`, never a raw `EffectError`, and — corrected in v0.2 — never an exception for *any* Module-input-shape condition (§2c):**

```text
BoundedWriteDispatched
- operation_ref: str
- state: str                   # always the literal "COMPLETED" in this slice

BoundedWriteRejected
- operation_ref: str | None    # None only for a broker-level shape rejection (§7d)
- reason_code: str             # BROKER_* for shape rejections; otherwise the
                                # underlying EffectError.code, used only when
                                # canonical truth (§7) is a definite non-UNKNOWN,
                                # non-COMPLETED state

BoundedWriteUnknown            # NEW in v0.2 — closes 065-F-002
- operation_ref: str           # always present: UNKNOWN implies a durable row
                                # already exists
- note: str                    # fixed constant, see §7c
```

`BoundedWriteUnknown` is not a variant of `BoundedWriteRejected`. It is a structurally distinct third outcome so that no caller can accidentally treat "uncertain" and "definitely rejected" as the same case by pattern-matching on one shape.

### 2c. Error posture — one unambiguous public contract (corrected: 065-F-003)

**The public method never raises for any Module-input condition.** Every one of the four required outcome families (§7: completed, rejected, unknown, broker-level shape rejection) is a **returned value**, never an exception.

This replaces v0.1's contradictory mixed posture (which described broker-level shape errors as raising `TypeError`/`ValueError` while simultaneously describing `BoundedWriteRejected` as the shape-error result). v0.2 adopts the Task-066-preferred singular rule: **all normal Module request-shape failures — out-of-context handle, malformed `intent_ref`, malformed `payload` — return `BoundedWriteRejected(operation_ref=None, reason_code="BROKER_...")`. There is no code path in the public method where a Module-supplied value, however malformed, causes a Python exception to propagate to Module code.**

A genuine Host/programmer fault — e.g. a Host build that constructs a `BoundedWriteEffectBroker` with an internally inconsistent private state that violates this document's own construction contract — is not a Module-input condition and is explicitly outside this public return algebra; such a fault indicates a broken Host, not a broker rejection, and is not part of the Module-visible ABI this document specifies.

This is a single fixed method for a single fixed effect class. It is not a generalized plugin SDK.

---

## 3. First bounded effect surface *(unchanged from v0.1 — PASS)*

The only live effect class in this candidate is the already-accepted:

```text
nyron.kernel.managed-resource-bounded-write@1
```

No new effect class, no workspace/process/network/model/browser surface, and no change to `EffectRequest`/`EffectOperation`/`EffectAuthority` is introduced or required. The Module never receives, chooses, or can derive the raw managed-root path; `ResourceHandle` structurally has no field capable of holding one.

---

## 4. Handle → request binding *(corrected: caused_by_ref source, 065-F-004)*

Unchanged from v0.1, and preserved as Task-065 PASS:

- **Which handle/ref the Module supplies or selects:** the Module *selects* one `CapabilityHandle` and one `ResourceHandle` already present in its own `RuntimeContext`; supplies `intent_ref` and `payload` as genuinely its own data.
- **Who resolves it / proves membership:** the broker, via value-equality membership against the exact set captured at broker-construction time (§4a of v0.1, unchanged — this is selector/context hygiene, not an authority decision; real authority is decided only in §5).
- **Who supplies `operation_ref`:** the broker, deterministically (§6). The Module never supplies or chooses it.
- **Who supplies `AttemptAuthority`/current attempt facts:** the broker's privately captured, immutable `AttemptAuthority` object from construction time (§5). The Module never supplies, sees, or can influence this.
- **Who supplies `capability_grant_ref`, `resource_ref`, `resource_lease_ref`:** taken directly from the Module-selected handle's own fields.
- **What the Module is forbidden to supply:** `operation_ref`, `effect_class`, the `AttemptAuthority` object or any of its fields individually, `caused_by_ref`, and any raw `capability_grant_ref` / `resource_ref` / `resource_lease_ref` string not obtained by selecting a handle already present in its own RuntimeContext.

### 4a. `caused_by_ref` — corrected causal-binding rule (065-F-004)

**v0.1's `f"activation-output:{activation_ref}"` is deleted. No replacement invented prefix or new causal-identifier namespace is introduced.**

Instead, `caused_by_ref` is bound to the already-existing, already-frozen causal fact every `Activation` already carries:

```text
Activation.trigger_delivery_ref
```

(`activations.trigger_delivery_ref TEXT NOT NULL UNIQUE` — the accepted, schema-enforced, always-present record of the exact Delivery that caused this Activation to exist; Module Design Report §7–§8: "所有 Activation 必须由 Trigger Delivery 引起.")

**Binding rule:**

1. At broker-construction time (Host-side, never Module-visible), the Host resolves this invocation's `Activation` via the existing accepted `ActivationRepository.resolve(activation_ref)` read surface.
2. If that resolves to a real `Activation`, the Host captures `activation.trigger_delivery_ref` as the broker's private, immutable `caused_by_ref` value. This is the *only* value ever placed in `EffectRequest.caused_by_ref` for any call made through this broker instance.
3. **If no such `Activation` resolves** (defensive case; should not occur for a real invocation but is not assumed away), **the live broker is not constructed.** `RuntimeContext.effect_broker` is `None` for that invocation, and no `dispatch_bounded_write` call is possible. The call fails closed before any Effect preparation, not by fabricating a placeholder causal reference.

This introduces **no new causal-identifier namespace**: `trigger_delivery_ref` is an existing field of an existing, already-accepted canonical record, used here exactly as-is, for exactly the purpose (`caused_by_ref`) that `EffectOperation`'s own already-frozen field list (§10 of the Design Candidate) already expects a causal reference to be supplied. The Module cannot choose, see, or override it; the broker only ever captures and forwards an already-existing value.

---

## 5. Real authority boundary *(unchanged core logic — PASS; owner-reachability wording corrected in §5a)*

**The broker performs no authority decision of its own.** Every real admission/authority check remains exactly where it already is: inside `EffectAuthority.execute()` → `EffectAuthority._admit_dispatch()`'s existing canonical `SQLiteStore.transaction()` (accepted, Gate-3/Gate-4A/4B/4C, unmodified by this candidate).

> The broker does **not** re-resolve "what is the current Attempt" at call time. It always passes through the **same, immutable `AttemptAuthority` object** captured once when this RuntimeContext/broker was constructed — the identity the Module's own execution genuinely belongs to.
>
> This is **not** a forbidden "read current authority once, cache the verdict, use it later" pattern (Clarification 004 §3). The broker caches no *verdict* — it holds only an identity *claim*. Whether that claim is still *current* is re-decided, atomically, fresh, every single call, entirely inside `EffectAuthority._admit_dispatch()`'s own transaction via `self._runtime_authority.is_current_with(connection, authority)`.
>
> If the broker instead re-resolved "current Attempt" itself and substituted whatever is current *now*, a Module still conceptually executing as stale R1 could have its write silently re-attributed to R2. Passing through the *original* captured identity and letting `EffectAuthority` reject it if it is no longer current is correct; **replacing it with a fresher identity is not.**

Every `dispatch_bounded_write` call that reaches `EffectAuthority.execute()` freshly revalidates, inside one atomic transaction, at the moment of real dispatch: current Attempt/fencing; `CapabilityGrant` validity/scope/attempt-binding; `ResourceLease` validity and resource directory resolution; the Gate-4C same-resource conflict barrier; target/resource invariants. None of this is duplicated, cached, or reimplemented by the broker.

This candidate additionally records the assumption it relies on: **canonical `run_ref` values are unique** (an existing, unstated-but-relied-upon property of the accepted Run/Attempt schema — `run_ref` is a primary-key-bearing identity throughout `run_attempts`), which is what makes the deterministic `operation_ref` derivation in §6 collision-free across unrelated Runs.

### 5a. In-process Python reachability — corrected statement (065-F-001)

**v0.1 incorrectly implied that Python attribute-privacy conventions make the broker's privately held `EffectAuthority`/`AttemptAuthority` objects physically unreachable to other code in the same process. This is false and is withdrawn.**

The corrected, truthful statement:

- This candidate defines a **supported Module ABI**: the documented public fields of `RuntimeContext` and the one documented public method of `BoundedWriteEffectBroker`. A trusted, cooperating module implementation that only uses the documented surface never receives `Store`/`DB`/Owner/`AttemptAuthority`/`Grant`/`Lease`/raw-path objects as a **return value or public attribute** of anything this ABI hands it.
- This is **not** a claim of physical non-reachability. Underscore-prefixed attribute names, Python name mangling, `__slots__`, closures, or any other same-process Python convention do **not** prevent a determined piece of Python code running in the same interpreter from reaching those objects — via `object.__getattribute__`, `__dict__` / `__closure__` inspection, `gc.get_referrers`, frame/stack introspection, monkey-patching, or simply importing the same modules and constructing equivalent calls directly. `NYRON-T-20260826-065`'s reviewer-originated probe already demonstrated this concretely against the v0.1 code shape, and that finding is accepted as correct, not disputed.
- **TRUSTED MODULE MODE does not provide, and this candidate does not claim it provides, a hostile-Python introspection boundary.** The narrowness of this ABI is a contract for what a well-behaved, trusted module implementation is expected to use — a correctness/auditability property — not a security control against an adversarial in-process implementation.
- Whatever trusted-Host dispatcher state (the captured `EffectAuthority`, `AttemptAuthority`, `caused_by_ref`, handle sets) necessarily exists somewhere in the process's object graph for the broker to function is **TCB-internal implementation state**. It is potentially discoverable by malicious in-process Python. That fact is **tolerated only because hostile/untrusted modules are explicitly outside the current threat model** (§9) — it would not be tolerated if this architecture ever claimed hostile-plugin isolation, which it does not.
- If Gate-5 or any later Task required actual physical non-reachability from a hostile co-resident module, that would require real process/container/WASM/VM isolation — a mechanism this candidate neither selects nor implements (§9, §13). This candidate does not need that mechanism, because it makes no claim requiring it.

---

## 6. Operation identity ownership *(unchanged from v0.1 — PASS)*

```text
operation_ref = "module-effect:" +
    sha256(run_ref + "\x00" + str(attempt_seq) + "\x00" + intent_ref).hexdigest()
```

using the broker's own privately captured `run_ref` and `attempt_seq` (the `attempt_seq` field of the same privately captured `AttemptAuthority` object from §5 — never a value read from the Module-visible `RuntimeContext.attempt_seq` field, per the §8 correction).

The same `(run_ref, attempt_seq, intent_ref)` always derives the same `operation_ref` (safe, existing-contract replay via `EffectAuthority.prepare()`'s `_require_identical_replay`); the same `intent_ref` with a different `payload` is rejected by that same existing mismatch check. Because `attempt_seq` is baked in from the broker's own captured, immutable identity, a stale R1 Module and its R2 replacement can never collide on `operation_ref` even with the same `intent_ref` string. This relies on canonical `run_ref` uniqueness (§5). No semantic-retry-clearance rule beyond Clarification 004 is introduced.

---

## 7. Return / error mapping *(corrected: distinct UNKNOWN, resolve-before-map, no exceptions — 065-F-002, 065-F-003)*

**Governing rule, corrected from v0.1:** whenever a call has produced an `operation_ref` (i.e. execution reached the point of constructing an `EffectRequest`) and `EffectAuthority.execute()` raises `EffectError`, the broker does **not** map the raised `error.code` directly to a result. It first asks accepted Owner truth what the canonical state of that exact `operation_ref` actually is, via `EffectAuthority.resolve(operation_ref)` (a plain read of canonical state — safe to call any number of times, performs no mutation, already exists, unmodified), and classifies from that truth **first**:

```text
resolve(operation_ref) result           -> broker result
--------------------------------------------------------------
row.state == "COMPLETED"                -> BoundedWriteDispatched
row.state == "UNKNOWN"                  -> BoundedWriteUnknown
row.state in {PREPARED, ACTIVE,          -> BoundedWriteRejected(
              REVOKE_REQUESTED, FENCED}       operation_ref=operation_ref,
                                               reason_code=<original error.code>)
resolve(operation_ref) is None          -> BoundedWriteRejected(
  (no durable row was ever committed          operation_ref=operation_ref,
   for this exact operation_ref — only         reason_code=<original error.code>)
   possible for the pre-identity
   validation failures in §7 case b-early)
```

`error.code` (the original `EffectError.code` raised by `EffectAuthority.execute()`) is still reported inside `BoundedWriteRejected.reason_code` when the resolved state is a **definite non-dispatch, non-UNKNOWN** state — it remains informative there, and is not contradicted by resolved truth in that branch. **`error.code` is never used to override resolved `UNKNOWN` truth.** This is the corrected version of v0.1 §7b, which previously mapped every raised `EffectError` — including ones that left the operation durably `UNKNOWN` — directly to an ordinary `BoundedWriteRejected` using only `error.code`, collapsing historical uncertainty into an indistinguishable rejection. That collapse (`065-F-002`) is what this section corrects.

### 7a. Accepted and completed

`EffectAuthority.execute()` returns an `EffectOperation` with `state == "COMPLETED"` **without raising**. Broker returns directly, no `resolve()` call needed (the return value already is canonical truth):

```text
BoundedWriteDispatched(operation_ref=operation_ref, state="COMPLETED")
```

### 7b. Admission rejected (definite, non-UNKNOWN)

Example: stale Attempt, revoked/invalid Grant, invalid Lease, or the Gate-4C conflict barrier — all surfaced by `EffectAuthority` as `EffectError("EFFECT_DISPATCH_AUTHORITY_REJECTED")`, with the operation's own row left in a definite `FENCED` state by `_admit_dispatch`'s existing rejection logic (unmodified). The broker calls `resolve(operation_ref)`, observes a definite non-UNKNOWN state, and returns:

```text
BoundedWriteRejected(operation_ref=operation_ref, reason_code="EFFECT_DISPATCH_AUTHORITY_REJECTED")
```

The broker never itself distinguishes *which* of stale-Attempt / revoked-Grant / invalid-Lease / conflict-barrier caused this — that distinction is `EffectAuthority`'s own internal concern and is not decoded further here, exactly as in v0.1.

### 7c. UNKNOWN — synchronous same-call transition (NEW, closes 065-F-002)

If, within the same synchronous call, `EffectAuthority.execute()`'s own internal `recover()` step determines the operation cannot be classified with certainty (for example: an ambiguous/mismatched target-evidence read during the internal recovery check that `execute()` performs before re-raising `EFFECT_OPERATION_NOT_DISPATCHABLE`), the operation's own row is left durably `UNKNOWN` **before** `EffectError` is raised. The broker's `resolve(operation_ref)` call observes `state == "UNKNOWN"` and returns:

```text
BoundedWriteUnknown(
    operation_ref=operation_ref,
    note="external consequence of this operation is not confirmed; do not treat as success or failure; do not retry this intent_ref without independent reconciliation",
)
```

The Module-visible `error.code` (`EFFECT_OPERATION_NOT_DISPATCHABLE` in this case) is **discarded**, not placed in `BoundedWriteUnknown` — `BoundedWriteUnknown` intentionally carries no `reason_code` field, only the fixed `note`, so that no caller can mistake an opaque, generically-worded code for a specific, actionable failure reason when the actual truth is "unknown," not "known to have failed for reason X."

### 7d. UNKNOWN — replay of a pre-existing durable UNKNOWN (NEW, closes 065-F-002)

If a Module calls `dispatch_bounded_write` with an `intent_ref` whose derived `operation_ref` (§6) already durably exists and was already `UNKNOWN` from an earlier call (in this Attempt or, via the deterministic hash, unreachable from any other Attempt — §6), `EffectAuthority.execute()` again raises (its own internal `recover()`/state-not-`PREPARED` check rejects a non-`PREPARED` existing row). The broker again calls `resolve(operation_ref)`, again observes `state == "UNKNOWN"`, and returns the identical:

```text
BoundedWriteUnknown(operation_ref=operation_ref, note="...")
```

Repeated calls with the same `intent_ref` against an `UNKNOWN` operation therefore repeatedly and honestly report `BoundedWriteUnknown` — never silently degrading to an ordinary rejection, and never fabricating success. Resolving that `UNKNOWN` into a definite outcome is an out-of-band Kernel-owned reconciliation concern this bounded slice does not implement (no `Suspended`, async, workers, callbacks, or Gate-6 reconciliation semantics are introduced — unchanged from v0.1).

### 7e. Broker-level shape rejection (before any operation identity exists)

An out-of-context handle, a malformed `intent_ref`, or an oversized/non-`str` `payload` is rejected before any `EffectRequest` is constructed and before any `operation_ref` is derived — this is the one case where `resolve()` is never called, because there is nothing to resolve:

```text
BoundedWriteRejected(operation_ref=None, reason_code="BROKER_HANDLE_NOT_IN_CONTEXT" | "BROKER_INTENT_REF_INVALID" | "BROKER_PAYLOAD_INVALID")
```

Per §2c, this is a **returned value**, never a raised exception. These three `BROKER_`-prefixed codes are the only new error vocabulary this candidate introduces, kept deliberately distinguishable from any real `EffectError.code`.

### 7f. Process crash mid-call (unchanged from v0.1)

If the Host process itself crashes strictly between dispatch admission and this synchronous call returning, the call **does not return at all** — there is no value to map. This is not a fourth outcome needing a shape; it is the honest absence of a return, already covered by the existing accepted crash-hook-tested implementation. A later, separate call (from a live process, using `EffectAuthority.resolve`/`recover`) against the same durable `operation_ref` is what would surface as §7c/§7d.

---

## 8. RuntimeContext / handle field-level contract *(unchanged from v0.1 — PASS)*

| Type | Field | Disposition |
|---|---|---|
| `CapabilityHandle` | `capability_type_ref`, `capability_type_version`, `grant_ref` | **Accepted as-is.** Matches `CapabilityGrant`'s own identity field names; carries no `scope`/`state`/`expiry`. |
| `ResourceHandle` | `resource_ref`, `lease_ref` | **Accepted as-is.** Built only from `ResourceLease`, never from `Resource.external_ref`. |
| `RuntimeContext` | `activation_ref`, `run_ref`, `attempt_seq`, `fencing_token`, `accounting_scope_ref`, `capability_handles`, `resource_handles`, `metadata` | **Accepted as-is, with the same binding correction as v0.1.** |
| `RuntimeContext` | `effect_broker` | **New field** (v0.1), unchanged in v0.2 except that its construction may now additionally be withheld per §4a step 3. |

**Binding correction (carried over from v0.1, restated):** `RuntimeContext.attempt_seq` and `RuntimeContext.fencing_token` are **descriptive/introspection-only**. No code may ever read these two *public* fields back out of a `RuntimeContext` value and feed them into a *new* `EffectRequest`/`AttemptAuthority`-shaped construction. The only `AttemptAuthority` object ever used for a live dispatch is the one the broker captured **privately** at its own construction time (§5).

This candidate clarifies **only** the fields needed for the first live broker slice. No additional RuntimeContext fields are introduced in v0.2.

---

## 9. Trusted-mode threat claim *(corrected wording — 065-F-001)*

This candidate's threat-model statement, corrected to remove any implied physical-isolation claim:

- **TRUSTED MODULE MODE only.**
- **Same-process Python privacy is convention, not isolation.** Underscore-prefixed attributes, closures, and `__slots__` organize the supported API surface; they do not and cannot make any object unreachable to other Python code sharing the interpreter.
- **The supported ABI does not hand raw Owner/Store/DB/`AttemptAuthority`/`Grant`/`Lease`/path objects to Modules.** This is a contract about documented return values and public attributes, not a reachability guarantee.
- **A malicious in-process Python module may introspect/import internals and reach the broker's private state anyway; this is explicitly outside the current supported security claim.** `NYRON-T-20260826-065`'s reviewer probe is accepted evidence of this, not disputed.
- **Hostile third-party support still requires real, enforceable isolation later** (process/container/WASM/VM — architecture-supported per §15 IsolationProfile language, not selected or implemented here).

Nothing else about the threat model changes from v0.1: this candidate reduces what a *cooperating, trusted* module needs to do to reach the effect boundary correctly; it is not and does not claim to be a security control against an adversarial implementation.

---

## 10. Standing interlocks *(unchanged from v0.1 — PASS, reconfirmed)*

**`NYRON-T-20260825-038-F-001` — confirmed NOT ACTIVATED:** no Module filesystem API; `ResourceHandle` has no field capable of holding a raw path (§3, §8); no less-trusted namespace-writer model is introduced or widened by the §5a reachability correction (that correction is a *truthful disclosure*, not a *new capability* — it grants the Module nothing it did not already have in v0.1).

**`NYRON-T-20260826-043-F-001` — confirmed NOT ACTIVATED:** the entire flow (§5, §7) remains one synchronous Python call ending in one call to `EffectAuthority.execute()`, using the existing, unmodified `SQLiteStore.transaction()` discipline. No thread, worker, process-execution concurrency, async callback, or connection pool is introduced. The additional `resolve(operation_ref)` read in §7 is a single extra synchronous, non-mutating read on the same connection — not a new transaction model, not a retry loop, not a poll.

---

## 11. Machine-reviewable invariants *(invariant 1 corrected — 065-F-001; invariant 9 strengthened — 065-F-002)*

1. **Corrected.** *Within the supported Module ABI, no documented public field or method return value is a `StateStore`/SQLite/Owner object or raw Resource path authority.* This is a claim about the documented contract's return values, not a claim of physical non-reachability in-process — see §5a. Enforced by construction: `RuntimeContext`/`CapabilityHandle`/`ResourceHandle`/`BoundedWriteEffectBroker`'s single public method are the only supported-ABI surfaces, and none of their documented values is a Store/connection/Owner object/path.
2. **Unchanged.** Module-visible handles are selectors/opaque identities, not authority decisions — `CapabilityHandle`/`ResourceHandle` carry only identity refs, never scope/state/expiry (§8).
3. **Unchanged.** A broker call cannot authorize external mutation without fresh accepted Effect Authority admission — every call, unconditionally, ends at `EffectAuthority.execute()`'s existing canonical transaction (§5).
4. **Unchanged.** Only handles belonging to the exact current RuntimeContext may be selected — membership check in §4.
5. **Unchanged.** Broker/Host never directly mutates canonical Capability/Resource/Effect/Run state — the broker contains no `INSERT`/`UPDATE`/`DELETE` against any canonical table; the added `resolve()` call in §7 is a read.
6. **Unchanged.** Module cannot choose current Attempt/fencing facts supplied to Effect Authority — the broker's privately captured `AttemptAuthority` is never Module-visible or Module-constructible (§5, §8).
7. **Unchanged.** Module cannot choose a raw target path for the bounded write — derived entirely inside `EffectAuthority.prepare()` (§3).
8. **Unchanged.** FENCED/COMPLETED active-conflict semantics are not semantic retry authorization — §6 limits its replay claim to identical-payload durability replay, unchanged from v0.1.
9. **Strengthened.** UNKNOWN remains uncertain and is never converted to success/failure certainty by Host — and, new in v0.2, UNKNOWN is never even converted to an *ordinary rejection*: it has its own distinct, structurally separate `BoundedWriteUnknown` result (§7c, §7d), closing `065-F-002`.
10. **Unchanged, restated with corrected wording.** Trusted Module Mode is not hostile-code isolation, and same-process Python privacy conventions do not make it so (§9, §5a).

---

## 12. Required sequence diagrams *(all five cases per Task 066)*

### a. Successful completed call

```text
Module -> RuntimeContext.effect_broker.dispatch_bounded_write(
              capability_handle, resource_handle, intent_ref, payload)
  -> membership + shape checks pass                              [§4, §7e]
  -> operation_ref := sha256(run_ref, attempt_seq, intent_ref)    [§6]
  -> request := EffectRequest(operation_ref, EFFECT_CLASS,
         self._attempt_authority,   # captured at construction, never re-resolved
         capability_handle.grant_ref, resource_handle.resource_ref,
         resource_handle.lease_ref, payload, self._caused_by_ref)  [§4a, §5]
  -> EffectAuthority.execute(request)
       -> prepare(): PREPARED committed (or identical replay)
       -> _admit_dispatch(): ONE canonical transaction — fresh
            currentness + Grant + Lease + Gate-4C conflict checks
       -> _activate(): ACTIVE
       -> _mutate_and_complete(): bounded write performed, COMPLETED committed
  <- EffectOperation(state="COMPLETED", operation_ref=...)          [no raise]
<- BoundedWriteDispatched(operation_ref=operation_ref, state="COMPLETED")
```

### b. Definite admission rejection

```text
Module -> dispatch_bounded_write(...)
  -> membership + shape checks pass; request constructed as in (a)
  -> EffectAuthority.execute(request)
       -> _admit_dispatch(): captured AttemptAuthority no longer current
          (or Grant/Lease invalid, or Gate-4C conflict present)
       -> current operation's own row set to FENCED (existing logic)
       raise EffectError("EFFECT_DISPATCH_AUTHORITY_REJECTED")
  -> broker catches EffectError, calls EffectAuthority.resolve(operation_ref)
  <- row.state == "FENCED"   # definite, non-UNKNOWN
<- BoundedWriteRejected(operation_ref=operation_ref,
                         reason_code="EFFECT_DISPATCH_AUTHORITY_REJECTED")
```

### c. Synchronous same-call transition to UNKNOWN

```text
Module -> dispatch_bounded_write(...)
  -> request constructed as in (a)
  -> EffectAuthority.execute(request)
       -> internal recover()/state check finds target-evidence ambiguity
       -> operation's own row committed to state = "UNKNOWN"
       raise EffectError("EFFECT_OPERATION_NOT_DISPATCHABLE")
  -> broker catches EffectError, calls EffectAuthority.resolve(operation_ref)
  <- row.state == "UNKNOWN"
<- BoundedWriteUnknown(operation_ref=operation_ref, note="...")
   # error.code "EFFECT_OPERATION_NOT_DISPATCHABLE" is discarded, not surfaced
```

### d. Replay of a pre-existing durable UNKNOWN

```text
[operation_ref already durably UNKNOWN from an earlier call, same intent_ref]

Module -> dispatch_bounded_write(same capability_handle, resource_handle,
                                  same intent_ref, same payload)
  -> operation_ref derives to the SAME value as before                [§6]
  -> EffectAuthority.execute(request)
       -> prepare(): existing row found, not COMPLETED -> re-enters
          execute()'s not-PREPARED path
       raise EffectError("EFFECT_OPERATION_NOT_DISPATCHABLE")
  -> broker catches EffectError, calls EffectAuthority.resolve(operation_ref)
  <- row.state == "UNKNOWN"          # unchanged from before
<- BoundedWriteUnknown(operation_ref=operation_ref, note="...")
   # identical outcome on every repeated call — never degrades to Rejected
```

### e. Broker-level malformed input rejection

```text
Module -> dispatch_bounded_write(resource_handle_from_a_different_RuntimeContext,
                                  resource_handle, intent_ref, payload)
  -> membership check: capability_handle not in self._capability_handles
  -> [no EffectRequest constructed; no operation_ref derived; no resolve() call]
<- BoundedWriteRejected(operation_ref=None,
                         reason_code="BROKER_HANDLE_NOT_IN_CONTEXT")
   # returned value, not a raised exception — §2c
```

---

## 13. Explicit non-goals confirmed unaffected

Nothing in this candidate designs, implements, or requires: a generalized Host/plugin SDK; more than one effect class; a workspace/process/network/model/browser API; Canonical Command; a secrets/credentials system; a hostile-plugin sandbox or any actual process/container/WASM/VM isolation mechanism; an async/suspension protocol expansion; a background worker; Resource filesystem namespace exposure; Gate-6 Accounting/Recovery semantics; or a schema change. The additional `EffectAuthority.resolve()` read introduced in §7 is an existing, unmodified read surface — not a new Owner API. No production or test code is included in or implied by this document as accepted; it is a candidate for review.
