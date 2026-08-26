# Runtime / Accounting Amendment 001 — Cross-Owner Identity / Persistence Boundary

Status: **FROZEN ARCHITECTURE AMENDMENT**
Authority: **Nyron Lead Design Authority**
Finding source: `NYRON-T-20260827-108`
Finding code: `CROSS_OWNER_RUNTIME_ACCOUNTING_STORAGE_BOUNDARY_UNFROZEN`

Applies to:
- `design/Nyron_Runtime_Orchestration_Frozen_Baseline_v0.1.md`
- `design/Nyron_Accounting_Recovery_Frozen_Baseline_v0.1.md`
- their pinned Candidates / Lead clarifications only at the integration point defined here

This Amendment does not redesign Runtime or Accounting. It freezes the minimum cross-owner identity and persistence boundary required to implement the already-frozen contracts safely.

---

## 1. Lead Decision

The Task 108 Architecture Finding is **VALID / BLOCKING**.

The existing frozen architecture already requires all of the following:

- Runtime and Accounting remain distinct logical canonical Owners;
- Accounting does not own Runtime Attempt truth;
- cross-owner convergence uses stable Commands / Queries / Events and idempotency;
- no shared/global transaction is assumed;
- the Accounting candidate explicitly does not require one physical database;
- Accounting owner-local reservation atomicity applies to Accounting-owned state.

However, the frozen bundle did **not** state precisely enough how an Accounting-owned canonical row may persist a reference to a Runtime-owned canonical identity when the Owners use different physical stores.

That omission permitted two incompatible interpretations:

1. Runtime identity is validated through Runtime-owned contracts, while Accounting stores only a stable foreign reference; or
2. Accounting additionally requires a storage-level foreign key to the Runtime canonical row.

Task 108 proved these interpretations are observably different under owner-local SQLite stores: Runtime identity validation can succeed while the Accounting commit still fails because the foreign Runtime row is absent from the Accounting database.

Therefore the prior frozen text is **insufficiently explicit for this persistence boundary**, and this Amendment is required.

---

## 2. Normative Ownership Rule

```text
Runtime canonical identity truth
= Runtime Owner

Accounting canonical reservation truth
= Accounting Owner

Accounting reference to Runtime identity
!= Accounting ownership of Runtime identity
!= required local copy of Runtime canonical row
```

A `BudgetReservation` may persist stable Runtime foreign identity fields such as:

```text
activation_ref
run_ref
attempt_seq
```

Those fields are cross-owner references. Their presence in an Accounting-owned record does not transfer canonical ownership and does not require Runtime canonical tables to exist inside the Accounting owner-local store.

---

## 3. Authoritative Runtime Identity Validation

When an Accounting transition requires proof of a Runtime binding, existence, or currentness condition, that proof MUST come from an authoritative Runtime boundary or previously accepted Runtime-issued evidence whose semantics are sufficient for the exact decision being made.

Valid mechanisms include:

- Runtime-owned Query / resolver over canonical Runtime history;
- a durable Runtime-issued command whose exact identity binding was admitted by Runtime;
- a durable owner-local evidence/projection record created from an authenticated Runtime fact, subject to Section 6.

A physical SQL foreign key is **not** Runtime authority validation.

Normative rule:

```text
storage referential integrity
!= cross-owner authority proof
```

A local FK MUST NOT substitute for Runtime Owner validation of facts that belong to Runtime.

---

## 4. Owner-Local Persistence Independence

Correct Accounting semantics MUST NOT require a Runtime-owned canonical row to be physically present in the Accounting owner-local database.

Therefore, when Runtime and Accounting use separate physical stores:

- Accounting MAY store `run_ref`, `attempt_seq`, `activation_ref`, and other stable Runtime references as ordinary foreign-identity values;
- Accounting MUST NOT declare a local relational FK whose satisfaction requires a Runtime canonical table/row to be duplicated into the Accounting store;
- `create_budget_schema()` or equivalent Accounting schema creation MUST NOT create Runtime canonical tables merely to satisfy an Accounting FK;
- missing local Runtime rows MUST NOT be interpreted as missing Runtime truth.

If authoritative Runtime proof cannot be obtained when the exact transition requires it, Accounting fails closed instead of guessing.

---

## 5. Shared Physical SQLite Is Allowed, But Is Not an Architecture Requirement

Nyron logical Owner separation does **not** require one database file per Owner.

A deployment MAY colocate Runtime-owned and Accounting-owned tables in the same physical SQLite database or another shared physical persistence service.

Physical colocation does not merge logical ownership:

```text
same physical database
!= same canonical Owner
!= permission for cross-owner mutation
!= global transaction semantics
```

A shared-store implementation MAY use a cross-owner relational FK as an **optional physical integrity optimization** only if all of the following are true:

1. the referenced row is the actual Runtime-owned canonical row, not an Accounting-owned shadow copy pretending to be Runtime truth;
2. the FK is not used as the authoritative proof of Runtime identity/currentness;
3. correctness does not require an atomic transaction that mutates both Runtime-owned and Accounting-owned canonical state;
4. the cross-owner Command / Query / Event contract remains the semantic authority boundary;
5. the same architecture remains expressible without that FK when Owners are placed in separate physical stores.

Therefore **shared physical SQLite is permitted**, but **shared physical SQLite is not required**, and a cross-owner FK must never become the only thing that makes the contract correct.

---

## 6. Owner-Local Runtime Evidence / Projection Is Allowed With Strict Limits

Accounting MAY persist owner-local evidence or a projection of Runtime facts for replay, diagnostics, or avoiding repeated historical lookups.

Such a record is derivative evidence, not canonical Runtime truth.

Conceptual minimum:

```text
RuntimeIdentityEvidence
- evidence_ref
- runtime_source_ref
- source_command_or_fact_ref
- activation_ref
- run_ref
- attempt_seq
- proven_fact_kind
- source_revision_or_fencing_context?
- accepted_at
- payload_hash / identity_hash
```

Rules:

1. the evidence MUST identify the Runtime source and the exact fact it proves;
2. duplicate evidence identity with conflicting payload MUST fail closed;
3. Accounting MUST NOT mutate the projection and thereby create new Runtime truth;
4. immutable historical identity/binding facts may be reused for replay when the original accepted fact is exactly the fact required;
5. mutable/current Runtime conditions MUST NOT be inferred from stale evidence unless Runtime explicitly issued durable admission evidence whose frozen semantics authorize that exact operation after issuance;
6. if fresh Runtime authority is required and unavailable, the transition remains blocked/fail-closed.

This Amendment does **not** require implementation of a generic projection framework.

---

## 7. No Global Transaction Assumption

The cross-owner flow remains:

```text
Runtime-owned fact / durable command
-> cross-owner delivery / authoritative validation
-> Accounting accepts sufficient Runtime evidence
-> Accounting performs one Accounting Owner-local transaction
-> Accounting commits BudgetReservation / accounting facts
-> durable outbox/event propagation
```

Nyron MUST NOT require:

```text
BEGIN GLOBAL TRANSACTION
mutate Runtime canonical row
mutate Accounting canonical row
COMMIT GLOBAL TRANSACTION
```

Physical colocation may make such a transaction technically possible, but the architecture does not depend on it and implementation MUST NOT use it to collapse Owner boundaries.

---

## 8. Replay / Identity / Fail-Closed Rules

For `RequestBudgetReservation` and equivalent cross-owner commands:

1. `request_ref` remains the stable idempotency identity.
2. The request binds exact Runtime foreign identity (`activation_ref`, `run_ref`, `attempt_seq`) plus Accounting scope/estimate/subject inputs required by the frozen D-005 contract.
3. Same `request_ref` + same canonical payload returns the existing Accounting outcome and MUST NOT reserve twice.
4. Same `request_ref` + conflicting Runtime identity or Accounting payload is an identity conflict and MUST be rejected.
5. Before the first authoritative Accounting decision, required Runtime proof must be obtained from Runtime or sufficient accepted Runtime-issued evidence.
6. After an Accounting outcome is canonically committed, replay of the same request returns that owner-local canonical outcome; it does not require reconstructing a physical cross-owner FK.
7. Crash or temporary Runtime unavailability never authorizes guessing a missing identity/currentness fact.

Historical Accounting records MUST remain able to identify the Runtime identity they reference. This is a semantic resolution requirement; it does not require the historical Runtime row to reside in the same physical database.

---

## 9. Implementation Direction for Task 108

For the currently blocked ARE-GATE-6 implementation, the Lead selects the minimum implementation-compatible direction:

### Required now

- Preserve the existing logical Runtime / Accounting Owner separation.
- Continue supporting physically separate owner-local SQLite stores.
- Keep Runtime identity proof through the injected Runtime repository / resolver boundary.
- Remove the requirement that Accounting `budget_reservations` has a SQLite FK to Runtime-owned `run_attempts` in the Accounting database.
- Do not create Runtime canonical tables inside the Accounting store merely to satisfy that FK.
- Persist stable Runtime foreign identity fields on the Accounting reservation as ordinary referenced identity data.
- Preserve existing `request_ref` idempotency and payload-conflict checks.
- If first-time reservation admission cannot obtain the Runtime proof required by the current contract, fail closed.

### Not required now

- no shared global database migration;
- no generic cross-owner projection framework;
- no distributed transaction / two-phase commit;
- no new saga/workflow engine;
- no Runtime ownership transfer;
- no Accounting ownership of `RunAttempt`;
- no redesign of BudgetReservation lifecycle.

If a later implementation profile chooses one shared physical SQLite database, Section 5 permits it without changing these semantics.

---

## 10. Frozen Invariants Added by This Amendment

### RA-INV-01 — Logical Owner Is Independent of Physical Colocation
Physical database placement does not define canonical ownership.

### RA-INV-02 — Foreign Reference Is Not Foreign Ownership
Accounting may persist Runtime identity references without owning or duplicating Runtime canonical truth.

### RA-INV-03 — Cross-Owner Authority Is Not a SQL FK
Runtime-owned facts required by Accounting are proven through Runtime authority or sufficient Runtime-issued evidence, not through storage topology alone.

### RA-INV-04 — Separate Stores Must Not Require Foreign Canonical Rows Locally
An Accounting owner-local commit cannot depend on a Runtime canonical row existing in the Accounting database.

### RA-INV-05 — Shared Physical Persistence Is Optional
Shared SQLite or another shared physical store is allowed, but is not required and must not introduce global-transaction semantics.

### RA-INV-06 — Projection Does Not Become Canonical Runtime Truth
Owner-local Runtime evidence/projection is derivative, scope-limited, replay-safe evidence only.

### RA-INV-07 — Mutable Runtime Currentness Cannot Be Guessed
Stale projection/evidence cannot prove currentness unless Runtime explicitly issued durable evidence whose semantics are sufficient for that exact admission decision.

### RA-INV-08 — Accounting Commit Remains Owner-Local Atomic
After sufficient foreign evidence is accepted, BudgetReservation and hierarchy counters commit atomically only within Accounting Owner.

### RA-INV-09 — Replay Does Not Depend on Physical Cross-Owner FK Reconstruction
A previously committed Accounting outcome is replayed by stable request identity and canonical Accounting state.

---

## 11. Finding Closure

`CROSS_OWNER_RUNTIME_ACCOUNTING_STORAGE_BOUNDARY_UNFROZEN` is **CLOSED BY ARCHITECTURE AMENDMENT**.

The implementation blocker is removed at the architecture level. Production implementation still requires a new bounded implementation/review cycle against this Amendment.

System Foundation ownership, no-global-transaction, stable identity, replay, UNKNOWN/fail-closed, and existing Runtime / Accounting lifecycle semantics remain unchanged except for the newly explicit cross-owner persistence boundary defined here.
