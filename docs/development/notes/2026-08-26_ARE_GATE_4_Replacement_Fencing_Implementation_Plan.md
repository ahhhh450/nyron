# ARE-GATE-4 Replacement Fencing Implementation Plan

**WORKING NOTE — NON-NORMATIVE**

Date: 2026-08-26 (corrected)
Related Task / Design: `NYRON-T-20260826-053`; `NYRON-T-20260826-054`; `NYRON-D-004` §11, §19–20, §23, §26; Clarification 003 §§3–4; Clarification 004 §§7–8
Status: **WORKING / CANDIDATE — FOR ORCHESTRATOR DECISION, NON-NORMATIVE**

> **CORRECTION NOTICE (Task `NYRON-T-20260826-054`, closing `NYRON-T-20260826-053-F-001` — `ARCHITECTURE / BLOCKING`):**
> The original (Task 053) version of this note contained a defective illustrative query in the Gate-4C conflict barrier: `AND run_ref != R2.run_ref`. **R1 → R2 replacement is the same `Run`, a new `Attempt`** — `run_ref` is identical for R1 and R2. That predicate would have excluded the exact stale-R1 rows the barrier exists to catch, silently defeating Gate 4's central purpose. The Gate-4B "find R1's outstanding work" language was also imprecise: discovering by `run_ref` alone cannot distinguish R1 from R2 in the same Run. This correction replaces every Run-level targeting statement with exact Attempt-bound targeting derived directly from the current accepted schema (new §A below), rewrites the conflict barrier to drop the `run_ref` predicate entirely (new §E), resolves same-Run/same-Attempt overlap explicitly rather than deferring it (also §E), and tightens the SQLite-trigger claims in §B to state only what storage constraints can structurally prove. All other Task 053 analysis was independently re-checked during this correction and found still valid; it is preserved below with corrected cross-references.

This note maps frozen `ARE-GATE-4 — Replacement Fencing` onto the *current accepted repository implementation* (post Gate-3 close, corrected Task 049+051 lineage integrated at merge commit `96698eda3e708945e9e12933ce8fe8793137db7f`). It recommends a minimal, evidence-backed implementation subdivision. It does not modify production code or Frozen Design.

## Current Repository Facts That Drive This Plan

These facts were independently verified by reading the accepted source, not assumed from the design documents:

1. **No Attempt-replacement mechanism exists today at any layer.** `RunRepository` (`src/nyron_kernel/execution/run.py`) implements exactly one method that writes `runs`/`run_attempts`: `create_initial()`. There is no `replace_attempt()`, no method that increments `runs.current_attempt_seq` or `runs.fencing_generation`, and no `run_attempts` state beyond `CREATED → ACTIVE → SUCCEEDED | FAILED`. Gate 4A is not "wiring into an existing replacement signal" — it must create the replacement primitive itself.
2. **The schema already supports it structurally.** `run_attempts` is keyed by the composite `(run_ref, attempt_seq)` — `PRIMARY KEY (run_ref, attempt_seq)` — not just `run_ref`, so a second row for `attempt_seq = 2` under the *same* `run_ref` is already representable without a schema redesign. `runs.current_attempt_seq` and `runs.fencing_generation` are plain `INTEGER CHECK (... > 0)` columns with no trigger currently constraining their mutation. `runs` and `run_attempts` currently have **zero** triggers of any kind (re-verified directly against `src/nyron_kernel/store/sqlite_store.py`'s `create_run_attempt_schema()`), unlike `capability_grants`/`resources`/`resource_leases`/`effect_operations`, which each have `BEFORE UPDATE` immutability and legal-state-transition triggers.
3. **`RuntimeAuthorityResolver.resolve_current_with()`'s join is the load-bearing mechanism, and it already does exactly the right thing for free.** Its query (`src/nyron_kernel/execution/authority.py`, re-read verbatim for this correction) joins `run_attempts AS a ON a.run_ref = r.run_ref AND a.attempt_seq = r.current_attempt_seq`, additionally requiring `r.state = 'OPEN' AND a.state IN ('CREATED','ACTIVE')`, and `is_current_with()` compares the **full six-field `AttemptAuthority` tuple** for equality (see §A). Every authority-mutating admission boundary already built in Gates 1–3 — `CapabilityAuthority.issue()`/`validate_advisory()`, `ResourceManager.issue_lease()`/`validate_lease_advisory()`, `EffectAuthority._admit_dispatch()` — calls `self._runtime_authority.is_current_with(connection, authority)` freshly, inside its own `BEGIN IMMEDIATE` transaction, before committing new authority. **This means: the instant a new Run-layer operation durably updates `runs.current_attempt_seq` to R2's value, R1's `AttemptAuthority` tuple stops matching this join forever — automatically, with zero changes to Capability, Resource, or Effect admission code.** This is the single most important fact this plan rests on, and it is unaffected by this correction.
4. **`EffectAuthority._admit_dispatch()`'s existing rejection path already produces the correct disposition for a stale-R1 `PREPARED` operation, unmodified.** When `is_current_with()` fails, the existing code (accepted in Gate 3A, unchanged since) sets the operation to `FENCED` (with `fence_evidence` basis `DISPATCH_REJECTED_BEFORE_ACTIVE`) if target evidence is `ABSENT`, or `UNKNOWN` if evidence is ambiguous — this is exactly the frozen disposition Gate 4 requires for an R1 `PREPARED` operation that a caller retries after replacement, and it needs no new code.
5. **`ResourceManager.revoke_lease()` and `EffectAuthority.request_revoke()`/`resolve_revoke()` already exist and are directly reusable** for the "fence R1's outstanding work" step — Gate 3's corrected revoke/fence semantics (Task 049+051) are exactly the primitive Gate 4B needs, not a new one.
6. **No conflict-scope concept exists anywhere in the codebase yet.** There is no table, field, or check that relates two different `EffectOperation` rows to each other. This is the one genuinely new piece of canonical truth Gate 4 must add (Gate 4C, §E below).

## A. Exact Attempt Identity Binding (Correction — Task 054, Mandatory Question A)

This section states, from the accepted source read directly (not inferred from names), the exact immutable field tuple binding each canonical object to a specific Attempt, and then defines R1's and R2's exact identities from those fields. Every later section's queries are stated only in terms of these exact fields.

**`AttemptAuthority`** (`src/nyron_kernel/execution/attempt.py`) — the full current-attempt fencing tuple checked everywhere:
```text
execution_ref: str
activation_ref: str
run_ref: str
attempt_seq: int
fencing_token: str
fencing_generation: int
```

**`RunAttempt`** (same file) — the per-attempt row identity:
```text
run_ref: str
attempt_seq: int
fencing_token: str
state: str
```
Table `run_attempts`: `PRIMARY KEY (run_ref, attempt_seq)`, `fencing_token TEXT UNIQUE`. Note `RunAttempt` itself does **not** carry `execution_ref`/`activation_ref`/`fencing_generation` — those live on the parent `runs` row (`execution_ref`, `activation_ref UNIQUE`, `fencing_generation`) and are joined in by `resolve_current_with()`.

**`CapabilityGrant`** (table `capability_grants`, `src/nyron_kernel/store/sqlite_store.py`) carries, verbatim: `execution_ref, activation_ref, run_ref, attempt_seq, fencing_token, fencing_generation` — the identical six fields as `AttemptAuthority`, plus its own identity (`grant_ref`, `capability_type_ref`/`capability_type_version`, `scope_json`, etc.). `FOREIGN KEY (run_ref, attempt_seq) REFERENCES run_attempts(run_ref, attempt_seq)`.

**`ResourceLease`** (table `resource_leases`) carries, verbatim: `execution_ref, activation_ref, run_ref, attempt_seq, fencing_token, fencing_generation` — the same six fields, plus `lease_ref`, `resource_ref`, `lease_holder_ref`. Same `FOREIGN KEY (run_ref, attempt_seq)`.

**`EffectOperation`** (table `effect_operations`) carries, verbatim: `execution_ref, activation_ref, run_ref, attempt_seq, fencing_token, fencing_generation` — the same six fields, plus `operation_ref`, `effect_class`, `resource_ref`, `resource_lease_ref`, `capability_grant_ref`, `target_ref`, etc. Same `FOREIGN KEY (run_ref, attempt_seq)`.

**Conclusion: every one of `CapabilityGrant`, `ResourceLease`, and `EffectOperation` binds to an Attempt via the identical six-field tuple that defines `AttemptAuthority` itself, not via `run_ref` alone.** `run_ref` is necessary but never sufficient to identify an Attempt, because `run_ref` is shared by every Attempt of that Run, including R1 and R2.

**Canonical R1 identity** (the Attempt being replaced): the exact tuple stored on R1's own row(s) —
```text
(execution_ref = E, activation_ref = A, run_ref = R, attempt_seq = S1, fencing_token = T1, fencing_generation = G1)
```

**Canonical R2 identity** (the Attempt becoming current): the exact tuple `runs`/`run_attempts` will hold once replacement commits —
```text
(execution_ref = E, activation_ref = A, run_ref = R, attempt_seq = S2, fencing_token = T2, fencing_generation = G2)
```
with `S2 = S1 + 1` and (per this plan's §B replacement design) `G2 = G1 + 1`, `T2` a freshly-derived unique value distinct from `T1`.

**`execution_ref`, `activation_ref`, and `run_ref` are identical between R1 and R2** — this is the entire point of "replacement" as opposed to "a new Run." **`attempt_seq`, `fencing_token`, and `fencing_generation` are what differ and are what any query must use to distinguish them.** Because `run_attempts` is keyed by `(run_ref, attempt_seq)` and `attempt_seq` is a monotonically-assigned per-Run integer, **`(run_ref, attempt_seq)` is the minimal sufficient pair to pin an exact Attempt**; `fencing_token`/`fencing_generation` are additional integrity fields available for defense-in-depth cross-checking (e.g., detecting corruption where a row's stored token doesn't match what `run_attempts` records for that `attempt_seq`), not required for the *identification* itself since `attempt_seq` alone (given `run_ref`) is already unique by the primary key.

This is the fact that Task 053's `run_ref != R2.run_ref` predicate violated: it used the one field that is *shared* between R1 and R2 as if it were discriminating.

## B. Exact Replacement Authority Cutover

**The canonical linearization point is a single new Run-owned operation — `RunRepository.replace_attempt()` (name illustrative) — whose entire effect is one `BEGIN IMMEDIATE` transaction that:**

1. re-reads current `runs` row fresh inside the transaction, obtaining the live `(run_ref=R, current_attempt_seq=S1, fencing_generation=G1)`;
2. enforces a CAS precondition: caller must supply the *expected* current `attempt_seq` and `fencing_generation` (exactly mirroring this project's own `Coordination Epoch/Revision` CAS convention — a deliberate, already-familiar pattern, not a new one); mismatch fails closed with a distinct error, no write;
3. verifies the current attempt's state is a legal replacement source (`CREATED` or `ACTIVE` — i.e., still logically the current attempt; already-terminal `SUCCEEDED`/`FAILED` attempts are not replaceable, they are finished);
4. transitions R1's `run_attempts` row — identified exactly by `(run_ref = R, attempt_seq = S1)` — to a new terminal state, **`REPLACED`** (a new value, not a reuse of `FAILED`, so a future Recovery/Reconciliation subsystem can distinguish "lost the replacement race" from "genuinely failed execution" — this is bookkeeping/audit value; see below for why it is not the *functional* linearization mechanism);
5. inserts the new `run_attempts` row for R2 at `(run_ref = R, attempt_seq = S1 + 1)`, fresh state `CREATED`, a freshly-derived unique `fencing_token`;
6. updates `runs.current_attempt_seq` to `S1 + 1` and `runs.fencing_generation` to `G1 + 1`, in the **same transaction** as steps 4–5.

**The functional cutover moment is step 6's commit**, specifically the `runs.current_attempt_seq` write. Per fact 3 above, this single write is *structurally sufficient* by itself to make every subsequent `is_current_with()` call for R1's exact tuple return `False` everywhere in the codebase, because the join key `r.current_attempt_seq` changes — the query will only ever match `run_attempts` rows where `attempt_seq = S1 + 1`, i.e. R2's row — not because R1's own row is separately inspected for staleness. Step 4 (marking R1's attempt `REPLACED`) is required for correctness of *direct* queries against `run_attempts` (exactly the kind of query §D/§E below perform) and for honest audit trails, but is not what makes R1 stop being able to canonical-commit or gain new authority through the `AttemptAuthority`-comparison path — that guarantee comes entirely from the join. This distinction matters because it means Gate 4A's correctness argument does not depend on every future piece of code remembering to check the attempt's own state — it depends on one already-proven, already-reused query shape.

**Explicitly not the linearization point:** revoke propagation (calling `request_revoke()` on R1's `EffectOperation`s, or `revoke_lease()` on R1's `ResourceLease`s) is a *consequence* of replacement, handled by Gate 4B, and happens strictly *after* step 6 commits. It is not itself what stops R1 from gaining new authority — R1 already cannot gain new authority the instant step 6 commits, regardless of whether any revoke has been requested yet. Conflating the two would be exactly the class of error `NYRON-T-20260826-050-F-001` punished in the Effect layer (treating a downstream consequence as if it were the authoritative cutoff); this plan is deliberately structured to avoid repeating that mistake one layer up.

**Required new schema (Gate 4A, additive only) — corrected to state only what SQLite constraints can structurally prove (Task 054, Mandatory Question E):**

A `BEFORE UPDATE`/CHECK-based trigger can enforce a *shape* on the data — it has no concept of "which Python function issued this statement," so it cannot literally guarantee "only `replace_attempt()` can write this." What it *can* structurally prove, and what Gate 4A should add:

- `run_attempts.state` CHECK extended to include `REPLACED`, plus a legal-transition trigger restricting `CREATED → {ACTIVE, REPLACED, FAILED}` and `ACTIVE → {SUCCEEDED, FAILED, REPLACED}` — this is a **legal-transition invariant**: no `UPDATE`, regardless of caller, can move `run_attempts.state` outside this table, and in particular cannot move a `REPLACED`/`SUCCEEDED`/`FAILED` row to any other value (**no reactivation**, matching the same pattern already accepted for `capability_grants`/`resources`/`resource_leases`/`effect_operations`).
- A trigger on `runs` enforcing `NEW.current_attempt_seq >= OLD.current_attempt_seq` and `NEW.fencing_generation >= OLD.fencing_generation`, and — critically — that the two only change *together* and only by the same delta (e.g., `NEW.current_attempt_seq - OLD.current_attempt_seq = NEW.fencing_generation - OLD.fencing_generation`) — this is a **monotonicity invariant** and a **paired-increment invariant**: no `UPDATE`, from any code path, can move either field backward, or advance one without the other, or skip/duplicate a generation.
- These two invariants together mean: *whatever process issues the write*, the resulting data can never represent "R1 became current again," "a generation was silently skipped or duplicated," or "the attempt counter and the fencing generation drifted apart." They do **not** mean "only `replace_attempt()` can write here" — a different, buggy write path that happens to satisfy monotonicity and pairing would still be legal at the storage layer. Preventing *that* is an application-layer discipline (all writes to `runs`/`run_attempts` route through `RunRepository`, exactly as every other subsystem in this codebase already disciplines itself to route writes through its one Owner class), not a database-provable guarantee, and this plan does not claim otherwise.
- No changes to `capability_grants`, `resources`, `resource_leases`, or `effect_operations` schema are required for 4A.

## C. Existing R1 EffectOperations After Replacement

Per Clarification 004 §8 and the fact that admission is where authority is truly consumed (fact 3/4 above), the disposition below requires **no new EffectAuthority code** except where marked; it is a description of what already happens, plus what Gate 4B must actively drive. "R1's EffectOperations" throughout this table means rows matching the exact `(run_ref = R, attempt_seq = S1)` pair — see §D for the precise discovery query.

| R1 EffectOperation state at replacement | What happens | New code needed? |
|---|---|---|
| `PREPARED`, no admission yet | Nothing happens automatically. If anyone later calls `execute()`/`prepare()` for it again, `_admit_dispatch()`'s existing `is_current_with()` check fails (R1's full tuple no longer matches), and the existing rejection path commits `FENCED` (target `ABSENT`) or `UNKNOWN` (target ambiguous) — unchanged Gate-3A code. | No — already correct. Gate 4B should *actively* revoke it (via `request_revoke()`, which already handles the `PREPARED` case) rather than leaving it to be discovered lazily on next access, so R1's debt does not linger silently. |
| `ACTIVE` (admission already linearized before replacement) | This is genuinely pre-replacement in-flight work per Clarification 004 §8. It is **not** touched by replacement itself — it continues via normal Gate-3C mechanisms. Gate 4B actively calls the existing `request_revoke()` → `ACTIVE → REVOKE_REQUESTED`, then (synchronously, in this single-writer model) `resolve_revoke()` to resolve it to `COMPLETED` (exact evidence), or — per the Task 051 correction — the *executor itself*, if it is still the one driving that call stack, observes `REVOKE_REQUESTED` on its own fresh pre-mutation read and stops with truthful `EXECUTOR_STOPPED_BEFORE_FIRST_MUTATION` evidence, or `UNKNOWN` if cessation cannot be proven. | No new EffectAuthority method — reuses `request_revoke`/`resolve_revoke` exactly as accepted in Gate 3C. Gate 4B's new code is the *orchestration* that finds R1's `ACTIVE` operations and calls these existing methods; it does not add new EffectOperation-internal logic. |
| `REVOKE_REQUESTED` already | Already mid-resolution under Gate 3C rules; replacement adds nothing. Gate 4B may call `resolve_revoke()` again (idempotent — re-reading current state, re-checking evidence) to attempt to drive it to a terminal state, but must not assume it can force an outcome. | No. |
| `FENCED`, `COMPLETED`, `UNKNOWN` | Already terminal. Untouched. Frozen rule preserved explicitly: replacement never claims these prove or disprove anything beyond what Gate 3C already established — `FENCED` still does not mean "no historical consequence," `COMPLETED` still means exact proven consequence, `UNKNOWN` still means unresolved. | No. |

**Explicitly not permitted:** any Gate-4 code path that marks an R1 `ACTIVE`/`REVOKE_REQUESTED` operation `FENCED`/`COMPLETED` *merely because replacement occurred*, without going through the existing, already-corrected `resolve_revoke()`/executor-fresh-read evidence discipline. This would silently reopen exactly the class of bug fixed in Task 051.

## D. Correct Gate-4B R1 Discovery (Task 054, Mandatory Question B)

**The exact, corrected discovery predicate** for "R1's outstanding canonical facts that Gate 4B must fence," using only the exact identity established in §A:

```text
SELECT * FROM effect_operations
WHERE run_ref = R                 -- R1's own run_ref (identical to R2's; not discriminating alone)
  AND attempt_seq = S1             -- R1's own exact attempt_seq (the discriminating field)
  AND state IN ('PREPARED', 'ACTIVE', 'REVOKE_REQUESTED')

SELECT * FROM resource_leases
WHERE run_ref = R
  AND attempt_seq = S1
  AND state = 'ACTIVE'
```

Both `R` and `S1` are known exactly by the caller performing the fencing orchestration, because they are precisely the values that were just read and superseded inside `replace_attempt()`'s own transaction (§B step 1) — no separate lookup or inference is required; the fencing step should be handed `(run_ref, attempt_seq)` directly by whatever code just performed the replacement, not rediscover it independently.

**Proof of the four required properties:**

- **Selects R1 rows:** by construction, every row returned has `run_ref = R AND attempt_seq = S1`, which is exactly and only R1's identity per §A.
- **Cannot select R2 rows from the same Run:** R2's rows (once any exist) carry `attempt_seq = S1 + 1 ≠ S1`; the `attempt_seq = S1` predicate excludes them structurally, not by convention. This is the exact fix for `NYRON-T-20260826-053-F-001` — Task 053's defective query used `run_ref != R2.run_ref` (wrong field, wrong polarity); the corrected query uses `run_ref = R AND attempt_seq = S1` (both fields, correct polarity, pinning the exact stale Attempt rather than trying to exclude the current one by a field that doesn't vary).
- **Cannot select rows from another Activation/Run accidentally:** every candidate row is filtered by the *specific* `run_ref = R` value belonging to this one Run; rows belonging to any other Run (which necessarily have a different `run_ref`, since `runs.activation_ref` is `UNIQUE` and each Run has exactly one `run_ref`) cannot satisfy the predicate.
- **Deterministic, machine-checkable, fail closed:** a plain equality-and-set-membership `SELECT` with no ambiguous branch; a row either matches both exact fields and a listed state, or it does not — there is no partial-match or best-effort interpretation.

**Indexing:** SQLite automatically creates an index to support each table's `PRIMARY KEY`/`UNIQUE` constraints, and `effect_operations`/`resource_leases` both already declare `FOREIGN KEY (run_ref, attempt_seq) REFERENCES run_attempts(run_ref, attempt_seq)` — but a foreign key declaration alone does not itself create an index on the *referencing* table's `(run_ref, attempt_seq)` columns in SQLite (only on the referenced table, which already has one via its own primary key). For the bounded scale of this Kernel-foundation slice (a handful of operations per test/scenario), an unindexed linear scan of `effect_operations`/`resource_leases` filtered by `(run_ref, attempt_seq)` is not a correctness concern and does not justify a schema change in Gate 4A/4B. If Gate 4's later production use grows the row counts materially, an additive `CREATE INDEX` on `effect_operations(run_ref, attempt_seq)` and `resource_leases(run_ref, attempt_seq)` would be the narrowest possible performance improvement — noted here for completeness, not recommended as part of this minimal plan; no current evidence requires it.

## E. Correct Gate-4C Conflict Clearance Barrier (Task 054, Mandatory Questions C and D)

**New canonical concept required:** a deterministic, versioned `EffectConflictScope` comparison, and one new check inserted into `EffectAuthority._admit_dispatch()`'s existing admission transaction (alongside, not replacing, the existing Attempt/Grant/Lease checks).

**Smallest sufficient scope for the current bounded effect class** (`nyron.kernel.managed-resource-bounded-write@1` — the only effect class that exists in this codebase): two `EffectOperation` rows conflict **iff they share the same `resource_ref`** (the managed directory is the shared mutable object whose consistency actually matters; `target_ref` is a deterministic per-`operation_ref` hash within that directory, so two distinct operations essentially never collide at that finer grain for *this* effect class — scoping at `resource_ref` is the correct, non-speculative granularity for what exists today). The scope identity is versioned implicitly via the effect class's own `@1` suffix (already the established versioning convention for `RESOURCE_TYPE`/`EFFECT_CLASS`/`CAPABILITY_TYPE` throughout this codebase) — if a future effect class needs a different conflict granularity, it gets a new class version, not a generalized configurable scope engine.

**The corrected barrier, checked inside R2's existing `_admit_dispatch()` transaction, immediately before its admission commits:**

```text
SELECT operation_ref FROM effect_operations
WHERE resource_ref = R2.resource_ref
  AND state IN ('PREPARED', 'ACTIVE', 'REVOKE_REQUESTED', 'UNKNOWN')
  AND operation_ref != R2.operation_ref

if any row found -> CONFLICTING -> admission rejected (fail closed)
else              -> PROVEN_DISJOINT -> admission may proceed
```

**The `run_ref != R2.run_ref` predicate from Task 053 is removed entirely and must not appear anywhere in an eventual implementation.** The only exclusion in the corrected query is `operation_ref != R2.operation_ref` — excluding *the exact row currently being admitted, and only that row* (needed purely so a row does not conflict with itself during its own admission check; it is not a Run- or Attempt-scoped exclusion of any kind).

**Proof / justification that no `run_ref` (or `attempt_seq`) condition is needed** — Task 054 explicitly asked this to be proven or the safest minimal form confirmed, not assumed:

The frozen conflict-scope requirement (Clarification 003 §§3–4, `ARE-INV-19`) is stated in terms of two *operations*' scope overlapping, evaluated against the shared *resource*, not in terms of which Attempt, Run, or Activation issued either operation. Nothing in the frozen text carves out an exemption for operations that happen to share a Run or Attempt with the one being admitted. Given that, the barrier's job is exactly and only: "does any other live operation already claim this resource?" — a question the `resource_ref` equality alone answers completely and correctly for every one of the three scenarios Task 054 requires resolved (Mandatory Question D):

1. **Stale R1 vs. current R2 (same `run_ref`, different `attempt_seq`):** R1's row (if still `PREPARED`/`ACTIVE`/`REVOKE_REQUESTED`/`UNKNOWN`) has the same `resource_ref` as R2's request and a different `operation_ref` — it **is** found by the query and correctly blocks R2, fixing the exact defect `NYRON-T-20260826-053-F-001` identified.
2. **Another operation within R2's own Attempt** (same `run_ref` *and* same `attempt_seq` as R2, but a distinct `operation_ref`, e.g. R2 attempting a second bounded write against the same resource while its first is still outstanding): this row is **also** found and **also** blocks admission, with no special exemption. This is a deliberate decision, not a punt: the frozen model's conflict domain is resource-scoped, and this codebase currently has no requirement — and Gate 4 must not invent one — for a single Attempt to hold two simultaneous outstanding effects against the same Resource. Blocking this case is the conservative, "unproven disjointness fails closed" default applied uniformly, and it forecloses no capability this bounded slice actually needs.
3. **Another Run/Activation entirely, touching the same `resource_ref`** (a Resource is not itself bound to any single Run — only `ResourceLease` rows are Attempt-bound, per §A; the same managed directory can legitimately be leased across unrelated Runs over its lifetime): this row is **also** found and **also** blocks admission. This is correct for the identical reason as case 2 — the conflict domain is the resource, and cross-Run sharing of a Resource is architecturally possible and must be governed by the same disjointness rule as any other overlap.

All three cases resolve to the *same* uniform rule with no case-specific branching required, which is itself evidence this is the minimal correct barrier rather than an accidental simplification: a query that had to special-case "same Attempt is exempt" or "different Run is exempt" would be *adding* an unproven-disjointness carve-out the frozen baseline does not grant. **This resolves Task 054's Mandatory Question D directly — none of the three scenarios is left undefined, and none requires an Architecture Finding, because the frozen text's resource/scope-centric (not Attempt-centric) framing is definitive enough to answer all three uniformly.**

This directly implements the remaining frozen requirements:
- **Unproven disjointness fails closed as conflicting** — the query has no "I don't know" branch; either a conflicting row exists (reject) or it provably does not (proceed).
- **`PREPARED`/`ACTIVE`/`REVOKE_REQUESTED`/`UNKNOWN` remain conflict-relevant** — all four appear in the `state IN (...)` list, matching Clarification 003 §4's barrier table.
- **`FENCED` does not block** — deliberately excluded, because `FENCED` means only "this exact old operation's active continuation is stopped," which is precisely what makes it safe for a *new, distinct* operation on the same resource to proceed — **active-conflict clearance only**.
- **`COMPLETED` does not block either** — a completed operation is not "in flight"; it has a known, proven outcome, and does not block new conflict-scope admission.
- Malformed/unreadable state or scope data cannot silently default to "proceed": the query's `state IN (...)` list is exhaustive over the frozen vocabulary, and any row whose `state` somehow fell outside that set (impossible under the current `CHECK` constraint, but the barrier does not rely on that alone) would simply not match the explicit list and would need its own explicit handling — this plan does not permit a fallback "if unrecognized, treat as clear" path anywhere.

**What R2 may and may not do once R1's conflicting operation is `FENCED`, `COMPLETED`, or `UNKNOWN`** — the orthogonality the frozen baseline (`ARE-INV-21`, `ARE-INV-22`) and this project's own Task 049/050/051/052 history were built to protect, restated precisely:

- Active-conflict clearance (the barrier above) only answers: *"is R2 free to begin dispatching a new, logically distinct effect against this resource right now?"* Once R1's row leaves the conflict-relevant state set, the answer can be yes.
- It **never** answers: *"is it safe for R2 to perform the same semantic effect R1 was attempting, as a retry?"* That is semantic retry clearance, and this Gate-4 minimal barrier deliberately does not implement it, does not infer it, and does not expose any field or API that could be mistaken for it. Clarification 004 §1's four conditions for safe same-semantic redispatch remain **out of scope for Gate 4** and remain future work.
- Concretely: after R1's operation is `FENCED`, R2 may be admitted for a *new* `operation_ref` targeting the same `resource_ref` (the barrier clears). Whether that new operation happens to carry byte-identical payload to R1's is not inspected or specially handled by Gate 4 — it is treated as what it structurally is: a distinct operation with its own identity, its own admission, its own evidence.

## F. Does the Corrected Minimal Gate-4 Plan Activate `NYRON-T-20260826-043-F-001`? (Re-confirmed under correction)

**No — conclusion unchanged by this correction.** The corrected §D discovery query and §E conflict barrier are both still single synchronous `SELECT` statements executed inside the same connection/`BEGIN IMMEDIATE` transaction discipline as every other admission check in this codebase; removing the (incorrect) `run_ref` predicate and adding `attempt_seq`/`operation_ref` predicates changes *which rows* the query matches, not *how* or *when* it executes. "Non-conflicting concurrency" in the frozen sense (§11, `ARE-INV-19/20/21`) refers to two *canonical* facts' lifetimes logically overlapping — e.g., R1's `EffectOperation` being in a non-terminal state at the moment R2 requests admission — not to two pieces of code literally executing at the same wall-clock instant on separate threads. In the current single-process, single-writer, synchronous Kernel, "R1's effect is still `ACTIVE`" and "R2 is being admitted" are simply two facts read sequentially by the same call stack from the same database.

**Implementation restrictions that must hold for this conclusion to remain valid** (unchanged from the original plan, restated):

- `replace_attempt()`, the §D R1-fencing orchestration, and the §E conflict-scope check must all execute as ordinary synchronous method calls within the existing single connection/writer model — no thread, process, worker pool, async callback, or connection pool of any kind.
- No Gate-4 code may hold a `BEGIN IMMEDIATE` transaction open across the Effect layer's external filesystem mutation.
- No Gate-4 code may introduce an in-memory lock table, worker registry, or other ephemeral local-authority object as a substitute for canonical SQLite state.
- If any future requirement needs R1-fencing or conflict resolution to be triggered *asynchronously* rather than synchronously by whatever caller invokes replacement, that crosses `043-F-001`'s activation condition and requires the real-concurrency revalidation Task 043's own note already specifies *before* such a Gate-4 extension may proceed.

`NYRON-T-20260826-043-F-001` correctly remains `OPEN` and is not weakened, narrowed, or closed by this plan.

## G. Does the Corrected Minimal Gate-4 Plan Activate `NYRON-T-20260825-038-F-001`? (Re-confirmed under correction)

**No — conclusion unchanged by this correction.** None of 4A/4B/4C touch `ResourceManager`'s directory provisioning, recovery, or destruction code, introduce any new writer to the managed root, or expose the managed namespace to any actor that does not already have access today. Gate 4B's Lease-fencing step reuses the existing `revoke_lease()` API surface without modification, now correctly scoped by exact `(run_ref, attempt_seq)` (§D) rather than the defective Run-only targeting. The activation condition (a less-trusted/co-resident actor gaining concurrent write access to the managed root) is unrelated to Attempt replacement and remains un-crossed.

## H. Minimal Gate-4 Subdivision

Repository facts support, and this plan recommends, the three-way split the Task suggested considering:

### Sub-gate 4A — Runtime Attempt Replacement + Stale-Authority Cutover

**Objective:** Establish the one new canonical fact this entire Gate depends on: a CAS-guarded, atomically-committed `R1 → R2` current-Attempt cutover (§B), and prove every existing Capability/Resource/Effect admission boundary correctly and immediately rejects R1's exact tuple the instant it commits — *without modifying any of that admission code*.

**Expected production files:**
- `src/nyron_kernel/execution/run.py` — add `replace_attempt()` (or equivalent) to `RunRepository`.
- `src/nyron_kernel/store/sqlite_store.py` — additive only: extend `run_attempts` state CHECK/trigger to include `REPLACED` with the legal-transition set from §B; add the previously-absent monotonicity/paired-increment trigger on `runs.current_attempt_seq`/`fencing_generation` from §B (stated as structural invariants only, per the §B correction).
- No changes to `capability/`, `resource/`, or `effect/` expected.

**Mandatory fault injection/tests:**
1. CAS mismatch (stale expected `attempt_seq`/`fencing_generation`) fails closed, no write, R1 remains current.
2. Successful replacement: R1's row at `(run_ref, S1)` becomes `REPLACED`; R2's row at `(run_ref, S1+1)` is `CREATED`; `runs.current_attempt_seq`/`fencing_generation` both updated in one transaction.
3. Immediately after replacement, independently re-verify that `CapabilityAuthority.issue()`, `ResourceManager.issue_lease()`, and `EffectAuthority._admit_dispatch()` — called with R1's now-stale full `AttemptAuthority` tuple — each fail exactly as they already do for any other staleness case, using the existing test fixtures, with zero changes to those modules.
4. Direct raw-SQL attempts to violate the §B invariants specifically: reactivate a `REPLACED`/`SUCCEEDED`/`FAILED` attempt; move `current_attempt_seq` backward; advance `current_attempt_seq` without `fencing_generation` (or vice versa) — each must fail via the new triggers.
5. Replacing a Run whose current attempt is already `SUCCEEDED`/`FAILED` fails closed.
6. Full existing `tests/kernel` suite remains green.

**Out of scope:** any EffectOperation/ResourceLease fencing (4B); any conflict-scope logic (4C).

**Independent HIGH-risk review required:** Yes.

**Interlocks to recheck:** `043-F-001` (§F); `038-F-001` (§G, trivially satisfied — 4A never touches Resource code).

### Sub-gate 4B — Old Effect / Lease Fencing on Replacement

**Objective:** Given a durable replacement (from 4A), actively drive R1's outstanding `EffectOperation`s and `ResourceLease`s — discovered by the exact `(run_ref, attempt_seq)` predicate in §D, never by `run_ref` alone — toward a terminal disposition using **only already-accepted Gate 2/3C methods** (`revoke_lease()`, `request_revoke()`, `resolve_revoke()`).

**Expected production files:**
- A small new orchestration surface (plausibly a method on `RunRepository` or a thin new module, e.g. `execution/replacement.py`) that, given `(run_ref = R, attempt_seq = S1)` for the just-replaced R1, runs exactly the §D queries and calls the existing revoke methods on each matching row.
- No changes to `capability/authority.py` expected.

**Mandatory fault injection/tests:**
1. R1 `EffectOperation` in `PREPARED` → actively revoked → `FENCED` (target absent) or `UNKNOWN` (ambiguous).
2. R1 `EffectOperation` `ACTIVE` → `request_revoke()` → `REVOKE_REQUESTED` → resolves via existing `resolve_revoke()`/executor-fresh-read rules to `COMPLETED` or `UNKNOWN`/truthful `FENCED` — re-run the Task 049/051/052 evidence-truthfulness regressions against a *replaced* Attempt context specifically.
3. R1 `ResourceLease` `ACTIVE` → `revoke_lease()` → `REVOKE_REQUESTED`.
4. **Explicit discovery-precision regression (direct response to `NYRON-T-20260826-053-F-001`):** seed both an R1 row `(run_ref, S1)` and an R2 row `(run_ref, S1+1)` on the *same* `resource_ref`, both `ACTIVE`; run the §D discovery query; assert it returns *only* the R1 row and never the R2 row. Also seed an unrelated Run/Activation with an `ACTIVE` row on a *different* `resource_ref`; assert discovery never returns it.
5. Already-terminal R1 effects/leases are left untouched (idempotent no-op).
6. Full existing `tests/kernel` suite remains green.

**Out of scope:** conflict-scope admission logic for R2 (4C); any change to what `FENCED`/`UNKNOWN` mean.

**Independent HIGH-risk review required:** Yes.

**Interlocks to recheck:** `043-F-001`; `038-F-001` (§F/§G).

### Sub-gate 4C — Conflicting / Non-Conflicting R2 Effect Admission Barrier

**Objective:** Add `EffectConflictScope` as the minimal `resource_ref`-keyed, `operation_ref`-self-excluding check described in §E, inserted into the existing `_admit_dispatch()` transaction.

**Expected production files:**
- `src/nyron_kernel/effect/authority.py` — add the §E conflict query as one additional `valid = valid and ...` clause inside the existing `_admit_dispatch()` transaction.
- No schema change expected.

**Mandatory fault injection/tests:**
1. **Stale-R1-vs-R2 conflict (the exact defect scenario):** R1 (same `run_ref` as R2, `attempt_seq = S1`) has a `PREPARED`/`ACTIVE`/`REVOKE_REQUESTED`/`UNKNOWN` row on `resource_ref = X`; R2 (`run_ref` identical, `attempt_seq = S1+1`) attempts admission on the same `resource_ref = X` → **rejected**. This is the regression that would have caught `NYRON-T-20260826-053-F-001` before it shipped and must be first in this Task's test list.
2. **Same-Attempt self-overlap:** a second `operation_ref` within R2's own `(run_ref, attempt_seq)` targeting the same `resource_ref` while the first is still conflict-relevant → **rejected**, per §E case 2 (no exemption).
3. **Cross-Run overlap:** an unrelated Run/Activation holds a conflict-relevant row on the same `resource_ref` → **rejected**, per §E case 3 (no exemption).
4. Only `FENCED`/`COMPLETED` rows present on the target `resource_ref` → admission **proceeds**; independently verify R2's own admission/mutation/evidence is entirely unaffected by R1's history.
5. Explicit regression proving `FENCED` clearing the barrier grants no "retry" status — assert no code path reads R1's `fence_evidence`/`completion_evidence` when deciding R2's own outcome.
6. Full existing `tests/kernel` suite remains green, plus the full 4A/4B/4C regressions re-run together end-to-end.

**Out of scope:** any generalized multi-dimension conflict scope beyond `resource_ref`; semantic-retry-safety inference; Canonical Command.

**Independent HIGH-risk review required:** Yes.

**Interlocks to recheck:** `043-F-001` (§F); `038-F-001` (§G).

### Sequencing

4A must land and be independently accepted before 4B. 4C should follow both. Recommend strict sequential Task order 4A → 4B → 4C, each with its own independent HIGH-risk review, mirroring the 3A → 3B → 3C precedent.

## Unresolved Architecture Finding

**NONE.** This correction resolves the one question Task 053 had left open (same-Run/same-Attempt overlap policy, §E) using the frozen baseline's resource/scope-centric framing, which is definitive enough to answer it without ambiguity. No remaining question in this plan requires a Frozen Design amendment or an Architecture Finding.

## Explicitly Rejected Alternatives

- **Building a generalized multi-dimension `EffectConflictScope` engine now** — rejected; only one effect class exists, and Clarification 003 §3 explicitly allows scope schemas to remain effect-class-specific and versioned.
- **Building a semantic-retry-policy subsystem alongside the conflict barrier** — rejected; explicitly out of scope per Clarification 004 §1.
- **Implementing R1-fencing as new EffectAuthority/ResourceManager-internal methods** instead of reusing `request_revoke`/`resolve_revoke`/`revoke_lease` — rejected; duplicating already-hardened evidence-truthfulness logic elsewhere would reopen surface area already twice independently reviewed (Tasks 050, 052).
- **Introducing a background sweep/worker to detect and fence stale Attempts automatically** — rejected for this Gate; would cross `043-F-001` for no proven current requirement.
- **Marking R1's admitted `ACTIVE` effects `FENCED` immediately upon replacement, without going through revoke/resolve** — rejected; would reopen the exact class of bug fixed in Task 051.
- **Excluding same-Attempt or cross-Run operations from the Gate-4C conflict barrier** — rejected in this correction (§E); the frozen baseline grants no such exemption, and inventing one would be adding an unproven-disjointness carve-out precisely where `ARE-INV-19` forbids one.
- **The original Task 053 `run_ref != R2.run_ref` predicate** — rejected and removed; see the Correction Notice at the top of this document and §D/§E above.

## Reusable Insight

**From Task 053, unaffected by this correction:** a correctly-designed admission boundary (fresh authority re-check inside the same transaction as the durable write, repeated identically at every Owner) makes replacement fencing almost free at the admission layer.

**From this correction (Task 054):** when a canonical identity is a multi-field tuple (here, the six-field `AttemptAuthority`), any exclusion/discovery predicate written against only the *shared* subset of that tuple (here, `run_ref` alone, shared by every Attempt of a Run) can silently invert its own intent — excluding what it meant to select, or selecting what it meant to exclude — without raising any error, because the query remains syntactically valid and simply matches the wrong rows. The general lesson: when writing a predicate meant to distinguish "this specific instance" from "everything else that shares part of its identity," always identify and use the *discriminating* fields of the full identity tuple, and treat any predicate built from only the *shared* fields as a name-only decoy worth independently re-deriving from the schema before trusting it — not just for this project, but as a general habit when working with hierarchical identity tuples (execution → activation → run → attempt) anywhere.

## Promote To

- A concrete `NYRON-T-20260826-055`-style Task definition for Sub-gate 4A, if the Orchestrator accepts this corrected plan and opens Gate-4 implementation.
- Future Development Orchestration Guide entry combining both insights above: admission-boundary re-validation makes later fencing Gates additive, *and* discovery/exclusion predicates against hierarchical identity tuples must be derived from the schema's discriminating fields, not assumed from field names.
