# NYRON-D-004 — Lead Integration Clarification 005

**Status:** `FROZEN NORMATIVE CLARIFICATION`  
**Authority:** `Nyron Lead Design Authority`  
**Applies to:** `design/Nyron_Capability_Resource_Effect_Authority_Frozen_Baseline_v0.1.md`, `design/Universal_Runtime_Module_Design_Report_v0.1.md`, and Clarification 004  
**Source Candidate:** `design/clarifications/NYRON-D-004_Gate5_Live_Broker_ABI_Clarification_Candidate_v0.3.md` at content commit `3fca2acade5bd46ff93bdeb657b4c01070572fb0`  
**Independent Re-Review:** `NYRON-T-20260826-069` — `PASS_WITH_FINDINGS`  

This clarification freezes the minimum Module-callable live-broker ABI required for `ARE-GATE-5`. It incorporates the reviewed v0.3 semantics, with one Design-Authority wording correction from `NYRON-T-20260826-069-F-001`: **identity conflict is not limited to payload mismatch**. Any immutable EffectRequest identity mismatch under an already-bound deterministic `operation_ref` — including a different payload, CapabilityGrant selection, Resource selection, or ResourceLease selection — must use the same identity-conflict semantics below.

This clarification closes the architectural under-specification tracked by `NYRON-T-20260826-062-F-001` and the later result-classification defect tracked by `NYRON-T-20260826-067-F-001`.

---

## 1. Supported Module Mode

The first live-broker slice remains **TRUSTED MODULE MODE only**.

Same-process Python privacy is convention, not hostile-code isolation. `_private`, name mangling, `__slots__`, closures, descriptors, or similar language conventions do not make Host/Owner objects physically unreachable to malicious code sharing the interpreter.

The supported Module ABI must not expose raw `StateStore`, SQLite connection, canonical Owner object, `AttemptAuthority`, `CapabilityGrant`, `ResourceLease`, credentials, or raw Resource/managed-root path as documented public fields, arguments, or return values.

A malicious same-process Python module may introspect/import internals. Such hostile code is outside the current security claim. Hostile third-party Module support still requires real enforceable isolation later.

---

## 2. RuntimeContext Delivery Model

The Module receives:

1. inert identity handles; and
2. exactly one optional callable broker for the first bounded live effect.

Normative shape:

```text
RuntimeContext
- activation_ref: str                  # descriptive
- run_ref: str                         # descriptive
- attempt_seq: int                     # descriptive only
- fencing_token: str                   # descriptive only
- accounting_scope_ref: str
- capability_handles: tuple[CapabilityHandle, ...]
- resource_handles: tuple[ResourceHandle, ...]
- metadata: tuple[tuple[str, str], ...]
- effect_broker: BoundedWriteEffectBroker | None

CapabilityHandle
- capability_type_ref: str
- capability_type_version: str
- grant_ref: str

ResourceHandle
- resource_ref: str
- lease_ref: str
```

`attempt_seq` and `fencing_token` in public RuntimeContext are introspection/descriptive values only. They MUST NOT be read back from Module-visible RuntimeContext and used to construct a new authority claim.

The live broker uses the original immutable `AttemptAuthority` captured by trusted Host construction for this exact invocation.

`effect_broker` is `None` when the Host cannot safely construct the bounded live broker, including PURE-only invocation, missing matching handles, or missing canonical causal binding.

Handles are selectors/opaque identity values, not cached authority verdicts.

---

## 3. First Bounded Live Effect

The only live effect class covered by this clarification is the already accepted:

```text
nyron.kernel.managed-resource-bounded-write@1
```

No generalized Host/plugin SDK is created.

This clarification does not add workspace, process, network, model, browser, Canonical Command, secrets, async, suspension, worker, or hostile-plugin APIs.

The Module never receives or selects a raw target path. The actual bounded target remains derived inside the accepted Effect Authority implementation from canonical Resource state and the Host-derived operation identity.

---

## 4. Module-Callable Broker ABI

The supported broker type is:

```text
BoundedWriteEffectBroker
```

It has exactly one supported public method:

```text
BoundedWriteEffectBroker.dispatch_bounded_write(
    capability_handle: CapabilityHandle,
    resource_handle: ResourceHandle,
    intent_ref: str,
    payload: str,
) -> BoundedWriteDispatched
   | BoundedWriteRejected
   | BoundedWriteUnknown
   | BoundedWriteIdentityConflict
```

Input rules:

- `capability_handle` MUST equal a value present in the exact current RuntimeContext capability-handle set.
- `resource_handle` MUST equal a value present in the exact current RuntimeContext resource-handle set.
- `intent_ref` MUST be non-empty `str`, at most 128 UTF-8 bytes, matching `[A-Za-z0-9_.:-]+`.
- `payload` MUST be `str`, at most 4096 UTF-8 bytes.

Normal Module-input errors are returned values, not Python exceptions:

```text
BoundedWriteRejected(
    operation_ref=None,
    reason_code=
      "BROKER_HANDLE_NOT_IN_CONTEXT" |
      "BROKER_INTENT_REF_INVALID" |
      "BROKER_PAYLOAD_INVALID"
)
```

Unexpected Host/programmer/storage invariant faults remain outside the normal Module-input result algebra.

---

## 5. Public Result Algebra

### 5.1 Completed

```text
BoundedWriteDispatched
- operation_ref: str
- state: str        # literal "COMPLETED"
```

This result may only describe the exact same request identity whose accepted EffectOperation is canonically COMPLETED.

### 5.2 Ordinary rejection

```text
BoundedWriteRejected
- operation_ref: str | None
- reason_code: str
```

This represents a definite normal request rejection/failed admission or broker input rejection. It MUST NOT represent an UNKNOWN consequence or an identity-conflicting current request.

### 5.3 Uncertain historical outcome

```text
BoundedWriteUnknown
- operation_ref: str
- note: str
```

`UNKNOWN` is structurally distinct from ordinary rejection and success. It provides no semantic retry clearance.

### 5.4 Operation identity conflict

```text
BoundedWriteIdentityConflict
- operation_ref: str
- existing_state: str
- reason_code: str  # literal "EFFECT_OPERATION_IDENTITY_CONFLICT"
```

`existing_state` is truth about the **pre-existing operation that already owns `operation_ref`**, not the outcome of the current conflicting request.

Allowed `existing_state` values in this bounded slice are:

```text
PREPARED
ACTIVE
REVOKE_REQUESTED
FENCED
COMPLETED
UNKNOWN
```

A current identity-conflicting request MUST NEVER be reported as `BoundedWriteDispatched`, `BoundedWriteUnknown`, or ordinary `BoundedWriteRejected` merely because the pre-existing operation is in one of those states.

---

## 6. Operation Identity

The broker owns and deterministically derives operation identity:

```text
operation_ref = "module-effect:" +
    sha256(run_ref + "\x00" + str(attempt_seq) + "\x00" + intent_ref).hexdigest()
```

The broker uses trusted captured `run_ref` and the `attempt_seq` from its privately captured original `AttemptAuthority`, never values reconstructed from public RuntimeContext fields.

The Module supplies `intent_ref` but never supplies `operation_ref`.

The identity deliberately causes repeated calls with the same `(run_ref, attempt_seq, intent_ref)` to address the same durable operation identity.

Same-identity, identical-request durability replay is permitted only under the existing accepted Effect Authority identical-replay contract. This clarification creates no new semantic retry clearance.

An identity conflict may arise whenever the same derived `operation_ref` is presented with any immutable EffectRequest identity mismatch, including but not limited to:

- different `payload` / payload hash;
- different valid CapabilityHandle / CapabilityGrant binding;
- different valid ResourceHandle / Resource binding;
- different valid ResourceLease binding;
- any other immutable request identity field mismatch detected by the accepted Effect Authority.

**Implementation and tests MUST NOT restrict identity-conflict handling to payload mismatches.**

---

## 7. Handle-to-EffectRequest Binding

The Module selects only handles already present in its exact RuntimeContext.

The trusted Host/broker constructs the EffectRequest.

The Module does not directly supply:

- `operation_ref`;
- `effect_class`;
- `AttemptAuthority`;
- currentness/fencing facts;
- raw `capability_grant_ref` except indirectly by selecting an issued CapabilityHandle;
- raw `resource_ref` / `resource_lease_ref` except indirectly by selecting an issued ResourceHandle;
- `caused_by_ref`;
- raw target path.

The broker derives:

- `capability_grant_ref` from the selected CapabilityHandle;
- `resource_ref` and `resource_lease_ref` from the selected ResourceHandle;
- `operation_ref` from §6;
- `AttemptAuthority` from the exact original Host-captured invocation identity;
- `caused_by_ref` from §8.

Handle membership is context/selector hygiene only. It is not authority admission.

---

## 8. Causal Binding

No new causal namespace is introduced.

For this bounded broker, `EffectRequest.caused_by_ref` is the existing canonical:

```text
Activation.trigger_delivery_ref
```

The trusted Host resolves the exact current Activation using the accepted `ActivationRepository.resolve(activation_ref)` read surface and captures that Activation's existing `trigger_delivery_ref` at broker construction.

The Module cannot choose, construct, or override this value.

If the exact Activation or its canonical trigger Delivery reference cannot be resolved, the Host does not construct the live broker; it fails closed rather than fabricating a causal identity.

---

## 9. Real Authority Boundary

The broker performs no authority decision itself.

It passes the original immutable `AttemptAuthority` identity claim captured for the Module invocation into the accepted Effect Authority.

It MUST NOT re-resolve the newest/current Attempt and substitute R2 for a stale R1 invocation.

Every actual effect dispatch continues to cross the accepted Effect Authority dispatch-admission/linearization boundary, which freshly decides, in the canonical transaction:

- current Attempt/fencing validity;
- CapabilityGrant validity/scope/attempt binding;
- ResourceLease validity and Resource resolution;
- Gate-4 same-resource conflict barrier;
- bounded target/resource invariants.

This is not check-then-use. No broker-local cached boolean or RuntimeContext handle value is authority.

The broker/Host never directly writes canonical Capability, Resource, Effect, Run, or Attempt state.

---

## 10. Result Classification Precedence

The required synchronous classification order is:

```text
1. Validate broker request shape and handle membership.
   Failure -> BoundedWriteRejected(operation_ref=None, BROKER_*).

2. Derive operation_ref.

3. Construct trusted EffectRequest and call EffectAuthority.execute(request).

4. If execute returns the exact operation as COMPLETED:
   -> BoundedWriteDispatched(operation_ref, "COMPLETED").

5. If EffectError is raised:

   5a. If error.code == "EFFECT_OPERATION_IDENTITY_CONFLICT":
       -> resolve(operation_ref)
       -> if no row: Host/storage invariant fault; do not fabricate a normal Module result
       -> else ALWAYS return:
          BoundedWriteIdentityConflict(
              operation_ref=operation_ref,
              existing_state=row.state,
              reason_code="EFFECT_OPERATION_IDENTITY_CONFLICT"
          )

   5b. Otherwise:
       -> resolve(operation_ref)
       -> state == COMPLETED:
          BoundedWriteDispatched(operation_ref, "COMPLETED")
       -> state == UNKNOWN:
          BoundedWriteUnknown(operation_ref, fixed uncertainty note)
       -> state in {PREPARED, ACTIVE, REVOKE_REQUESTED, FENCED}:
          BoundedWriteRejected(operation_ref, error.code)
       -> no row:
          BoundedWriteRejected(operation_ref, error.code)
```

Identity-conflict precedence is mandatory. Canonical state of the pre-existing row MUST NOT override truth about the current conflicting request.

For an identity conflict, the pre-existing row must not be mutated by the conflicting request merely to classify the conflict.

---

## 11. UNKNOWN Semantics

When the accepted Effect Authority leaves or already has the exact same request identity in canonical `UNKNOWN`, the broker reports `BoundedWriteUnknown`.

This includes:

- an UNKNOWN reached during the same synchronous call before Effect Authority raises; and
- replay of an already durable same-identity UNKNOWN operation.

The broker MUST NOT map canonical UNKNOWN to ordinary rejection, success, or retry authorization.

If a different request identity conflicts with an already-UNKNOWN operation, the result is `BoundedWriteIdentityConflict(existing_state="UNKNOWN")`: the current request's conflict is definite while the old operation's historical uncertainty remains explicitly visible.

---

## 12. Required Truth Table for Identity Conflict

For every `EFFECT_OPERATION_IDENTITY_CONFLICT`:

```text
existing PREPARED          -> BoundedWriteIdentityConflict(existing_state="PREPARED")
existing ACTIVE            -> BoundedWriteIdentityConflict(existing_state="ACTIVE")
existing REVOKE_REQUESTED  -> BoundedWriteIdentityConflict(existing_state="REVOKE_REQUESTED")
existing FENCED            -> BoundedWriteIdentityConflict(existing_state="FENCED")
existing COMPLETED         -> BoundedWriteIdentityConflict(existing_state="COMPLETED")
existing UNKNOWN           -> BoundedWriteIdentityConflict(existing_state="UNKNOWN")
```

The conflicting current request is never considered dispatched/completed merely because `existing_state == COMPLETED`.

`ACTIVE` / `REVOKE_REQUESTED` remain visibly nonterminal.

`UNKNOWN` remains visibly uncertain.

`FENCED` remains active/conflict state truth only and grants no semantic retry clearance.

---

## 13. Machine-Reviewable Invariants

1. Supported Module ABI returns no raw StateStore/SQLite/Owner/Attempt/Grant/Lease/path authority objects.
2. Same-process Python privacy is not hostile-code isolation.
3. Module-visible handles are selectors/opaque identities, not authority decisions.
4. Only handles belonging to the exact RuntimeContext may be selected.
5. Module cannot choose current Attempt/fencing facts supplied to Effect Authority.
6. Module cannot choose a raw target path.
7. Every real mutation requires fresh accepted Effect Authority dispatch admission.
8. Broker/Host directly writes no canonical Capability/Resource/Effect/Run/Attempt state.
9. Public RuntimeContext `attempt_seq` / `fencing_token` are descriptive-only and cannot be reconstituted into authority.
10. UNKNOWN is never converted to success, ordinary rejection, or semantic retry certainty.
11. `FENCED` / `COMPLETED` state does not itself grant semantic retry clearance.
12. Identity conflict and pre-existing operation state are two separate truths and must remain separately represented.
13. A different request identity under an already-bound `operation_ref` can never be reported as current-request `BoundedWriteDispatched`.
14. Identity-conflict behavior is source-agnostic: payload, Grant, Resource, Lease, or any other immutable request-identity mismatch uses the same conflict branch.
15. No new causal namespace is invented; bounded effect causality uses existing `Activation.trigger_delivery_ref`.
16. TRUSTED MODULE MODE makes no hostile third-party isolation claim.

---

## 14. Standing Interlocks

`NYRON-T-20260825-038-F-001` remains NOT ACTIVATED by this clarification:

- no Module filesystem API;
- no raw managed-root path exposure;
- no less-trusted namespace-writer support claim.

`NYRON-T-20260826-043-F-001` remains NOT ACTIVATED by this clarification:

- synchronous flow only;
- no threads/workers/process concurrency;
- no async callbacks;
- no connection pools/raw writers;
- no SQLite authority-linearization model change.

`NYRON-T-20260826-056-F-001` is unaffected.

`NYRON-T-20260826-048-F-001` is unaffected/out of scope.

---

## 15. Freeze / Finding Disposition

By Lead Design Authority decision after `NYRON-T-20260826-069 PASS_WITH_FINDINGS`:

- `NYRON-T-20260826-067-F-001` — `CLOSED` by this frozen clarification.
- `NYRON-T-20260826-062-F-001` — `CLOSED` by this frozen clarification.
- `NYRON-T-20260826-069-F-001` — `CLOSED` by Design Authority wording correction in §6 and invariant 14; no semantic or operation-identity formula change was required.
- `NYRON-T-20260826-065-F-001..F-004` remain `CLOSED`.

This clarification is now the normative Gate-5 live-broker ABI basis. Implementation must be performed only under a newly scoped Task and independently reviewed before ARE-GATE-5 can close.
