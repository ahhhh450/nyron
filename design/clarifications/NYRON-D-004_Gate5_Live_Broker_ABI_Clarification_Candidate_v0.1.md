# NYRON-D-004 — Gate-5 Live Module Broker ABI Clarification Candidate v0.1

**Status:** `CANDIDATE — NOT FROZEN — NO ARCHITECTURE AUTHORITY`
**Produced by:** `NYRON-T-20260826-064` (Claude Code, DESIGN task)
**Resolves (candidate, not yet closing):** `NYRON-T-20260826-062-F-001`
**Applies to:** `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md` (§9, §10, §11, §15, §19, §26) and `design/Universal_Runtime_Module_Design_Report_v0.1.md` (§11, §18, §29, §38), read together with Frozen Clarification 004.

---

## 0. Non-Normative Status (read this first)

This document is a **candidate only**. It has **no architecture authority**, cannot be implemented against, and cannot itself close `NYRON-T-20260826-062-F-001`. It becomes eligible for implementation only after:

1. an independent Codex design review, and
2. explicit acceptance/freeze by the Design Authority, and
3. a newly and correctly scoped Gate-5 implementation Task is opened against the frozen result.

`src/nyron_kernel/host/runtime_context.py` at content commit `dd6a41bc539d00a09a8a0fcc075b7cc0a0b63225` (Task 061) is consulted below **only as non-normative implementation evidence** of what a narrow handle shape can look like. It is not accepted design and several of its choices are explicitly corrected in §8 below, not silently canonized.

This candidate does not modify, and is not itself, `design/Nyron_Capability_Resource_Effect_Authority_Frozen_Baseline_v0.1.md`.

---

## 1. Module-facing delivery model

**Decision: inert identity handles plus exactly one callable broker, both delivered as additional fields on `RuntimeContext`.**

Rejected alternatives and why:

- *Callable broker only, no handles*: fails Module Report §38, which explicitly lists `capability_handles` / `resource_handles` as RuntimeContext fields. A Module needs to be able to select and reason about which capability/resource it is using, not just call an opaque method.
- *Handles only, no callable*: leaves the "concrete Python invocation ABI" question (this Task's central gap) unanswered; a Module would have no way to actually cross the effect boundary.

Concrete shape (extends, does not replace, the Task-061 `RuntimeContext` fields — see §8 for the exact field-level disposition):

```text
RuntimeContext
- activation_ref            (existing, descriptive only)
- run_ref                   (existing, descriptive only)
- attempt_seq               (existing, descriptive only)
- fencing_token             (existing, descriptive only)
- accounting_scope_ref      (existing, descriptive only)
- capability_handles: tuple[CapabilityHandle, ...]   (existing)
- resource_handles: tuple[ResourceHandle, ...]       (existing)
- metadata: tuple[tuple[str, str], ...]              (existing, unused by the broker)
- effect_broker: BoundedWriteEffectBroker | None     (NEW — see §2)
```

`effect_broker` is `None` whenever the Host has no live-effect capability to offer this Module invocation (e.g. a PURE module, or a module with no matching capability/resource handle) — a Module must always null-check before use, exactly like any other optional field. It is never a generalized multi-effect gateway; it exposes exactly one method for exactly one effect class (§2, §3).

---

## 2. Concrete Python invocation ABI

**Broker object/type identity:** `nyron_kernel.host.BoundedWriteEffectBroker`, a Host-constructed instance with **exactly one public method** and no other public attributes/methods. It privately holds (never exposed, never enumerable from Module code):

- the real `EffectAuthority` instance;
- the real, immutable `AttemptAuthority` object captured once at RuntimeContext/broker construction time (never re-resolved, never mutated — see §5 for why this is still safe);
- the exact `activation_ref` used to derive `caused_by_ref`;
- the exact `run_ref`;
- the exact frozenset of `CapabilityHandle`/`ResourceHandle` values that belong to this RuntimeContext (for the membership check in §4).

**Method:**

```text
BoundedWriteEffectBroker.dispatch_bounded_write(
    capability_handle: CapabilityHandle,
    resource_handle: ResourceHandle,
    intent_ref: str,
    payload: str,
) -> BoundedWriteDispatched | BoundedWriteRejected
```

**Arguments — exactly these four, nothing else:**

- `capability_handle` — must be one of the `CapabilityHandle` values already present in this Module's own `RuntimeContext.capability_handles`. Not a raw grant, not a string.
- `resource_handle` — must be one of the `ResourceHandle` values already present in this Module's own `RuntimeContext.resource_handles`. Not a raw lease, not a string, not a path.
- `intent_ref` — a short Module-chosen label (non-empty `str`, ≤ 128 UTF-8 bytes, `[A-Za-z0-9_.:-]+` only) identifying "this logical write attempt" for replay purposes. It is **not** the operation identity itself (§6).
- `payload` — the bounded write content (`str`, ≤ 4096 UTF-8 bytes — the existing `EffectAuthority._MAX_PAYLOAD_BYTES` bound, unchanged and not widened).

**Return type — exactly one of two frozen dataclasses, never a raw `EffectOperation`, never an exception for a normal admission rejection:**

```text
BoundedWriteDispatched
- operation_ref: str
- state: str            # always the literal "COMPLETED" in this slice

BoundedWriteRejected
- operation_ref: str | None   # None only when rejected before an operation_ref
                               # could be derived (see §7)
- reason_code: str             # see §7 for the exact code taxonomy
```

The method is **synchronous**. It returns exactly one of the two shapes above, or it does not return at all (host process crash mid-call — see §7). It never raises `EffectError` to Module code; every `EffectError` raised by the underlying `EffectAuthority` is caught inside the broker and mapped to `BoundedWriteRejected` (a broker-internal shape error, e.g. a malformed `intent_ref`/`payload`, may still raise a plain `TypeError`/`ValueError` synchronously before any operation identity exists — this is the same "fail before module code observes anything durable" posture `TrustedModuleHost` already uses for `INVALID_MODULE_REFERENCE`).

This is a single fixed method for a single fixed effect class. It is not a generalized plugin SDK: there is no method-name dispatch table, no dynamic capability-to-method mapping, and no extensibility hook in this candidate.

---

## 3. First bounded effect surface

The only live effect class in this candidate is the already-accepted:

```text
nyron.kernel.managed-resource-bounded-write@1
```

(`EffectAuthority.EFFECT_CLASS` in `src/nyron_kernel/effect/authority.py`, unchanged.)

This effect class is sufficient to demonstrate real mediation: it already has a fully accepted Owner-side lifecycle (PREPARED → dispatch admission → ACTIVE → COMPLETED, with FENCED/UNKNOWN and Gate-4 conflict-barrier coverage). No new effect class, no workspace/process/network/model/browser surface, and no change to `EffectRequest`/`EffectOperation`/`EffectAuthority` is introduced or required.

The Module never receives, chooses, or can derive the raw managed-root path. The bounded-write target path is computed entirely inside `EffectAuthority.prepare()` from `resource.external_ref` (Owner-internal) and `operation_ref` (Host-derived, §6); neither ever crosses into Module-visible data. `ResourceHandle` (§8) structurally has no field capable of holding a path.

The existing bounded effect fully supports a safe minimal broker without any change to frozen semantics — no blocking Architecture Finding is raised for this question.

---

## 4. Handle → request binding

Answering each required point exactly:

- **Which handle/ref the Module supplies or selects:** the Module *selects* (does not construct) one `CapabilityHandle` and one `ResourceHandle` from the exact tuples already present in its own `RuntimeContext`. It supplies `intent_ref` and `payload` as genuinely its own data.
- **Who resolves it:** the broker. Before constructing any `EffectRequest`, `dispatch_bounded_write` checks `capability_handle in self._capability_handles` and `resource_handle in self._resource_handles` (identity/equality membership against the exact frozenset captured at broker-construction time — dataclass `__eq__` on the frozen, validated handle types makes this a safe value comparison, not an identity-only comparison, so a `CapabilityHandle` reconstructed by the Module with the same field values as one it was actually given still passes; a value belonging to a **different** RuntimeContext, or a hand-fabricated one with fields that were never issued, does not match and is rejected — see §4a for why a fabricated-but-matching value is still safe).
- **How the broker proves the selected handle belongs to the current RuntimeContext:** the membership check above. This is a **non-authority hygiene check**, not a security boundary by itself — real authority is decided only where §5 says it is decided. Its purpose is solely to prevent cross-context confusion (e.g. a Module holding two RuntimeContexts across two Activations accidentally mixing refs) from ever reaching `EffectAuthority`.
- **Who supplies `operation_ref`:** the broker derives it deterministically; the Module never supplies or chooses it (§6).
- **Who supplies `AttemptAuthority`/current attempt facts:** the broker's privately captured, immutable `AttemptAuthority` object from construction time. The Module never supplies, sees, or can influence this (§5).
- **Who supplies `capability_grant_ref`, `resource_ref`, `resource_lease_ref`:** taken directly from the Module-selected `capability_handle.grant_ref`, `resource_handle.resource_ref`, `resource_handle.lease_ref` — i.e. the Module *indirectly* supplies these by selecting a handle, but never by typing/constructing a ref string itself.
- **Who supplies `caused_by_ref` and payload:** `caused_by_ref` is Host-derived, fixed, deterministic: `f"activation-output:{self._activation_ref}"` (using the broker's privately captured `activation_ref`, never a Module-supplied value). `payload` is genuinely Module-supplied (§2).
- **What the Module is forbidden to supply:** `operation_ref`, `effect_class`, the `AttemptAuthority` object (or any of its fields individually), `caused_by_ref`, and any raw `capability_grant_ref` / `resource_ref` / `resource_lease_ref` string not obtained by selecting a handle already present in its own RuntimeContext.

No raw Owner object (`EffectAuthority`, `CapabilityAuthority`, `ResourceManager`, `RuntimeAuthorityResolver`, `SQLiteStore`, `CapabilityGrant`, `ResourceLease`, `AttemptAuthority`) is ever passed to Module code. The Module receives only `CapabilityHandle` / `ResourceHandle` value objects (§8) and the one-method `BoundedWriteEffectBroker`.

### 4a. Why a hand-fabricated-but-matching handle is still safe

A Module cannot gain anything by constructing its own `CapabilityHandle("real.type", "1", "grant:someone-elses")` even if, by luck or by reading logs, the field values happen to match a real grant that was never part of its own RuntimeContext, because the membership check (§4) rejects anything not `==` to a value in `self._capability_handles`/`self._resource_handles` — and those sets are fixed at broker-construction time from refs the *Host itself* resolved for *this* Module's own real, current grants/leases, never from Module input. This is defense in depth, not the primary authority boundary: even if the membership check were somehow bypassed, §5 shows `EffectAuthority` would still independently re-validate the grant's real scope/state/attempt-binding and reject anything not genuinely authorized.

---

## 5. Real authority boundary

**The broker performs no authority decision of its own.** Every real admission/authority check remains exactly where it already is: inside `EffectAuthority.execute()` → `EffectAuthority._admit_dispatch()`'s existing canonical `SQLiteStore.transaction()` (accepted, Gate-3/Gate-4A/4B/4C, unmodified by this candidate).

This is the central subtlety this candidate must resolve precisely, because it is easy to get backwards:

> The broker does **not** re-resolve "what is the current Attempt" at call time. It always passes through the **same, immutable `AttemptAuthority` object** that was captured once when this RuntimeContext/broker was constructed — the identity the Module's own execution genuinely belongs to.
>
> This is **not** a forbidden "read current authority once, cache the verdict, use it later" pattern (Clarification 004 §3). The broker caches no *verdict* at all — it holds only an identity *claim*. Whether that claim is still *current* is re-decided, atomically, fresh, every single call, entirely inside `EffectAuthority._admit_dispatch()`'s own transaction via `self._runtime_authority.is_current_with(connection, authority)` — exactly the same mechanism Gate-4A/4B/4C already use and that is already independently reviewed and tested to correctly reject a captured-but-now-stale `AttemptAuthority`.
>
> If the broker instead re-resolved "current Attempt" itself and substituted whatever is current *now* into the request, a Module still conceptually executing as stale R1 could have its write silently re-attributed to R2 — which is the actually dangerous version of "authority substitution" this design must avoid. Passing through the *original* captured identity and letting `EffectAuthority` reject it if it is no longer current is the correct behavior; **replacing it with a fresher identity is not.**

Concretely, every `dispatch_bounded_write` call crosses the accepted Effect Authority dispatch-admission boundary and therefore freshly revalidates, inside one atomic transaction, at the moment of real dispatch:

- current Attempt/fencing (`RuntimeAuthorityResolver.is_current_with`);
- `CapabilityGrant` validity/scope/attempt-binding (`CapabilityAuthority._is_effect_dispatch_admissible_with`);
- `ResourceLease` validity and resource directory resolution (`ResourceManager._resolve_effect_directory_with`);
- the Gate-4C same-resource conflict barrier (`conflicting_operation` query in `_admit_dispatch`);
- target/resource invariants (`target.parent == resource_directory`, `target_evidence == "ABSENT"`).

None of this logic is duplicated, cached, or reimplemented by the broker. Plain check-then-use remains impossible by construction: the broker has no code path that decides "this is allowed" and only later, separately, performs the mutation — the single call to `EffectAuthority.execute(request)` is both the decision and, if admitted, the mutation, inside one canonical transaction.

---

## 6. Operation identity ownership

The broker derives `operation_ref` deterministically and is its sole owner:

```text
operation_ref = "module-effect:" +
    sha256(run_ref + "\x00" + str(attempt_seq) + "\x00" + intent_ref).hexdigest()
```

using the broker's own privately captured `run_ref` and the `attempt_seq` field of the same privately captured `AttemptAuthority` object from §5 (never a value read from the Module-visible `RuntimeContext.attempt_seq` field — see the correction in §8).

Consequences, all already true of the existing accepted `EffectAuthority.prepare()` replay contract and therefore not new semantics:

- The same `(run_ref, attempt_seq, intent_ref)` always derives the same `operation_ref`. A Module retrying the same logical write with the same `intent_ref` and the same `payload` after a crash-recovery safely replays (`EffectAuthority.prepare()`'s existing `_require_identical_replay`); if already `COMPLETED`, `EffectAuthority.execute()` returns the existing operation immediately without a new mutation.
- The same `intent_ref` with a **different** `payload` within the same Attempt is rejected by the existing `_require_identical_replay` mismatch check (surfaced to the Module as `BoundedWriteRejected(reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT")`, unchanged existing code) — a Module cannot reuse an operation identity with a different meaning.
- Because `attempt_seq` is baked into the hash from the broker's own captured, immutable Attempt identity, a stale R1 Module and the R2 that replaced it can never collide on `operation_ref` even if they happen to choose the same `intent_ref` string.
- The Module cannot choose or override any part of this derivation; it supplies only `intent_ref`, which is one input to a Host-controlled hash, never the identity itself.

This candidate does not define any semantic-retry-clearance rule beyond what Clarification 004 already freezes (§1–§2 of that document): a successful replay above is a same-identity, same-payload durability replay, not a new semantic redispatch, and this candidate makes no claim about safely retrying with a *different* payload under the same real-world intent — that remains outside this bounded slice.

---

## 7. Return / error mapping

Exactly four Module-visible outcome families for a `dispatch_bounded_write` call, all synchronous:

### a. Accepted and completed

`EffectAuthority.execute()` returns an `EffectOperation` with `state == "COMPLETED"`. Broker returns:

```text
BoundedWriteDispatched(operation_ref=operation_ref, state="COMPLETED")
```

### b. Admission rejected

`EffectAuthority.execute()` raises `EffectError(code, **context)` for any reason already in the accepted implementation — including but not limited to `EFFECT_DISPATCH_AUTHORITY_REJECTED` (stale Attempt, revoked/invalid Grant, invalid Lease, or the Gate-4C conflict barrier — the broker does not and cannot distinguish these from each other; that distinction is `EffectAuthority`'s own internal concern, not exposed further here), `EFFECT_REQUEST_INVALID`, `UNRESOLVED_RESOURCE`, `EFFECT_OPERATION_IDENTITY_CONFLICT`, or `EFFECT_OPERATION_NOT_DISPATCHABLE`. Broker returns:

```text
BoundedWriteRejected(operation_ref=operation_ref, reason_code=error.code)
```

passing the existing `EffectError.code` through **unmodified**. The broker never invents a new taxonomy of rejection reasons for this case; it is a transparent pass-through.

### c. Broker-level shape rejection (before any operation identity exists)

An out-of-context handle, a malformed `intent_ref`, or an oversized/non-`str` `payload` is rejected before any `EffectRequest` is constructed:

```text
BoundedWriteRejected(operation_ref=None, reason_code="BROKER_HANDLE_NOT_IN_CONTEXT" | "BROKER_INTENT_REF_INVALID" | "BROKER_PAYLOAD_INVALID")
```

These three codes are broker-original (prefixed `BROKER_` precisely so they can never be confused with a real `EffectError.code` value) and are the only new error vocabulary this candidate introduces.

### d. UNKNOWN

**This method never returns a value that means "UNKNOWN."** Within one synchronous, non-crashing call, `EffectAuthority.execute()` only ever returns `COMPLETED` or raises — it cannot itself produce or return an `UNKNOWN` `EffectOperation`, by construction of the accepted implementation (`recover()` inside `execute()` either yields `COMPLETED`, `PREPARED`→admitted→`COMPLETED`, or a raised `EFFECT_OPERATION_NOT_DISPATCHABLE` if a *prior* call already drove the same `operation_ref` to `UNKNOWN`).

`UNKNOWN` can only become durable in exactly one circumstance already covered by the accepted crash-hook-tested implementation: the Host process itself crashes strictly between dispatch admission and this synchronous Python call returning. In that circumstance the Module's call to `dispatch_bounded_write` **does not return at all** — there is no value to map, honestly, because the process is gone. No later synchronous call from that dead process can retroactively report anything. Discovering and resolving that `UNKNOWN` state is an out-of-band Kernel-owned reconciliation concern (`EffectAuthority.recover()` / a future `ReconciliationCase` consumer) that this bounded slice does not implement, require, or claim to solve — consistent with the instruction to STOP rather than expand this clarification into `Suspended`/async/background-worker territory. No blocking prerequisite is required for *this* slice because "the call never returns" is already a complete, honest, non-fabricating answer; it only becomes a blocking prerequisite if and when a future Task tries to make Module code *observe* a durable UNKNOWN synchronously produced by someone else's crash, which is out of scope here.

The broker never converts `UNKNOWN`, `FENCED`, or any uncertain historical state into a fabricated `BoundedWriteDispatched`. Only a genuine, freshly observed `state == "COMPLETED"` from `EffectAuthority.execute()`'s own return value produces `BoundedWriteDispatched`.

---

## 8. RuntimeContext / handle field-level contract

Disposition of the Task-061 candidate shapes, per field:

| Type | Field | Disposition |
|---|---|---|
| `CapabilityHandle` | `capability_type_ref`, `capability_type_version`, `grant_ref` | **Accepted as-is.** Matches `CapabilityGrant`'s own identity field names; carries no `scope`/`state`/`expiry` — cannot be read as cached authority truth. |
| `ResourceHandle` | `resource_ref`, `lease_ref` | **Accepted as-is.** Built only from `ResourceLease`, never from `Resource.external_ref` — structurally cannot carry a managed-root path or lifecycle ownership. |
| `RuntimeContext` | `activation_ref`, `run_ref`, `attempt_seq`, `fencing_token`, `accounting_scope_ref`, `capability_handles`, `resource_handles`, `metadata` | **Accepted as-is, with one binding correction below.** |
| `RuntimeContext` | `effect_broker` | **New field**, added by this candidate (§1, §2). Not present in Task 061. |

**Binding correction (not present in Task 061, because Task 061 built no live broker to need it):**

`RuntimeContext.attempt_seq` and `RuntimeContext.fencing_token` are **descriptive/introspection-only**. No code — Host, broker, or otherwise — may ever read these two *public* fields back out of a `RuntimeContext` value and feed them into a *new* `EffectRequest`/`AttemptAuthority`-shaped construction. The only `AttemptAuthority` object that may ever be used for a live dispatch is the one the broker captured **privately** at its own construction time (§5). This distinction did not need to exist in Task 061 (which built no broker and performed no dispatch), and is the one genuinely new normative constraint this candidate adds to the Task-061 shapes.

This candidate deliberately clarifies **only** the fields needed for the first live broker slice. No additional RuntimeContext fields (workspace/network/process/model-shaped handles, suspension/continuation fields, etc.) are introduced.

---

## 9. Trusted-mode threat claim

This candidate changes nothing about the threat model:

- **TRUSTED MODULE MODE only.** The broker, handles, and RuntimeContext exist to give a trusted, known, registry-pinned module implementation a narrow, auditable way to reach one accepted effect boundary — not to make arbitrary code safe to run.
- **In-process Python is not hostile-plugin isolation.** Nothing in this candidate — dataclass immutability, frozen handles, membership checks, or the single-method broker — constitutes a sandbox. A genuinely hostile module implementation, hosted in the same process, could still call arbitrary Python/`os`/`subprocess`/`socket` APIs directly; nothing proposed here claims otherwise or attempts to prevent it.
- **No claim of malicious-code containment.** The narrowness of this ABI reduces what a *cooperating, trusted* module implementation needs to do to reach the effect boundary correctly; it is not a security control against an adversarial implementation.
- **Hostile third-party support requires real enforceable isolation** (process/container/WASM/VM — architecture-supported per §15 IsolationProfile language, not selected or implemented here) **before any such claim can be made.** This candidate neither selects nor implements that mechanism.

---

## 10. Standing interlocks

**`NYRON-T-20260825-038-F-001` — confirmed NOT ACTIVATED by this candidate:**

- No Module filesystem API is introduced; the Module never receives a path, file handle, or `pathlib`/`os` primitive.
- `ResourceHandle` has no field capable of holding `Resource.external_ref` or any other raw path (§3, §8).
- No less-trusted namespace-writer model is introduced; the trusted-module-only threat model (§9) is unchanged, and this candidate does not widen who may write into the managed root — only `EffectAuthority`'s own existing, accepted internal path derivation ever touches the managed root.

**`NYRON-T-20260826-043-F-001` — confirmed NOT ACTIVATED by this candidate:**

- The entire flow (§5, §7) is one synchronous Python call ending in one call to `EffectAuthority.execute()`, which uses the existing, unmodified `SQLiteStore.transaction()` / `BEGIN IMMEDIATE` discipline.
- No thread, worker, process-execution concurrency, async callback, or connection pool is introduced anywhere in this candidate.
- No change to SQLite locking/linearization model is proposed; `EffectAuthority`/`CapabilityAuthority`/`ResourceManager` internals are explicitly unmodified (§3, §5).
- The "process crash mid-call → the call never returns" case in §7d is the existing, already-accepted crash model (same one Gate-3/4's crash-hook tests already exercise) — not a new concurrency primitive.

---

## 11. Machine-reviewable invariants

Restated in this candidate's own terms, mapped to where each is enforced:

1. **Module never receives StateStore/SQLite/Owner objects/raw Resource path authority.** — Enforced by construction: `RuntimeContext`/`CapabilityHandle`/`ResourceHandle`/`BoundedWriteEffectBroker` are the only types ever handed to Module code, and none of them exposes a Store, connection, Owner object, or path (§2, §3, §4, §8).
2. **Module-visible handles are selectors/opaque identities, not authority decisions.** — `CapabilityHandle`/`ResourceHandle` carry only identity refs, never scope/state/expiry (§8); selecting one decides nothing by itself (§5).
3. **A broker call cannot authorize external mutation without fresh accepted Effect Authority admission.** — Every call, unconditionally, ends at `EffectAuthority.execute()`'s existing canonical transaction (§5); there is no other code path to a mutation.
4. **Only handles belonging to the exact current RuntimeContext may be selected.** — Membership check in §4 against the exact set captured at this RuntimeContext's own construction time.
5. **Broker/Host never directly mutates canonical Capability/Resource/Effect/Run state.** — The broker contains no `INSERT`/`UPDATE`/`DELETE` against any canonical table; all mutation happens exclusively inside `EffectAuthority.execute()` (§5).
6. **Module cannot choose current Attempt/fencing facts supplied to Effect Authority.** — The broker's privately captured `AttemptAuthority` object is never Module-visible and never Module-constructible (§5, §8 correction).
7. **Module cannot choose a raw target path for the bounded write.** — Confirmed in §3; the target path is derived entirely inside `EffectAuthority.prepare()` from Owner-internal state and the Host-derived `operation_ref`.
8. **FENCED/COMPLETED active-conflict semantics are not semantic retry authorization.** — This candidate adds no retry-authorization logic of its own; §6 explicitly limits its replay claim to identical-payload durability replay, consistent with Clarification 004 §1–§2.
9. **UNKNOWN remains uncertain and is never converted to success/failure certainty by Host.** — §7d: the broker only ever returns `BoundedWriteDispatched` on a freshly observed `COMPLETED`; UNKNOWN is never synthesized into either outcome.
10. **Trusted Module Mode is not hostile-code isolation.** — §9.

---

## 12. Required sequence diagrams

### a. Successful first brokered effect

```text
Module (execute() body)
  -> RuntimeContext.effect_broker.dispatch_bounded_write(
         capability_handle, resource_handle, intent_ref, payload)

BoundedWriteEffectBroker.dispatch_bounded_write
  -> check capability_handle in self._capability_handles      [membership, §4]
  -> check resource_handle in self._resource_handles          [membership, §4]
  -> check intent_ref shape, payload shape                    [broker-level, §7c]
  -> operation_ref := sha256(run_ref, attempt_seq, intent_ref) [Host-derived, §6]
  -> caused_by_ref := f"activation-output:{activation_ref}"    [Host-derived, §4]
  -> request := EffectRequest(
         operation_ref, EFFECT_CLASS,
         self._attempt_authority,      # captured at construction, never re-resolved
         capability_handle.grant_ref, resource_handle.resource_ref,
         resource_handle.lease_ref, payload, caused_by_ref)
  -> EffectAuthority.execute(request)
       -> prepare(): commit PREPARED (or return existing identical replay)
       -> _admit_dispatch(): ONE canonical transaction —
            is_current_with(attempt)              [fresh, real]
            + capability grant admissibility        [fresh, real]
            + resource/lease directory resolution    [fresh, real]
            + Gate-4C conflict-relevant row check     [fresh, real]
          -> admitted: dispatch_admission_ref committed
       -> _activate(): ACTIVE
       -> _mutate_and_complete(): bounded write performed, COMPLETED committed
  <- EffectOperation(state="COMPLETED", operation_ref=...)
<- BoundedWriteDispatched(operation_ref=operation_ref, state="COMPLETED")

Module receives BoundedWriteDispatched
```

### b. Admission rejected (stale Attempt / revoked Grant / invalid Lease / Gate-4C conflict — any one of these)

```text
Module -> dispatch_bounded_write(capability_handle, resource_handle, intent_ref, payload)
  -> membership + shape checks pass
  -> request constructed exactly as in (a)
  -> EffectAuthority.execute(request)
       -> _admit_dispatch(): the same one canonical transaction determines
          the captured AttemptAuthority is no longer current
          (or the Grant/Lease is no longer valid, or a conflicting
          same-resource operation is present)
       -> current operation's own row transitions to FENCED or UNKNOWN
          per existing _admit_dispatch rejection logic (unchanged)
       raise EffectError("EFFECT_DISPATCH_AUTHORITY_REJECTED")
  <- EffectError raised, caught by broker
<- BoundedWriteRejected(operation_ref=operation_ref,
                         reason_code="EFFECT_DISPATCH_AUTHORITY_REJECTED")

Module receives BoundedWriteRejected; no external mutation occurred.
```

### c. UNKNOWN (crash mid-call)

```text
Module -> dispatch_bounded_write(...)
  -> ... -> EffectAuthority.execute(request)
       -> _admit_dispatch() commits dispatch_admission_ref
       -> _activate() commits ACTIVE
       -> [Host process crashes here, before _mutate_and_complete() commits
           COMPLETED — the exact crash window already covered by the
           existing accepted crash-hook tests]

Module's call to dispatch_bounded_write never returns. No value is
produced, fabricated, or lost — the process is gone.

[separately, after restart, out of scope for this candidate:]
EffectAuthority.recover(operation_ref) inspects target evidence and
durably resolves the operation to COMPLETED or UNKNOWN, per the
existing accepted Gate-3 recovery contract. No change proposed here.
```

---

## 13. Explicit non-goals confirmed unaffected

Nothing in this candidate designs, implements, or requires: a generalized Host/plugin SDK; more than one effect class; a workspace/process/network/model/browser API; Canonical Command; a secrets/credentials system; a hostile-plugin sandbox; a Docker/VM/WASM/process isolation selection; an async/suspension protocol expansion; a background worker; Resource filesystem namespace exposure; Gate-6 Accounting/Recovery semantics; or a schema change. No production or test code is included in or implied by this document as accepted; it is a candidate for review.
