# ARE-GATE-4 Replacement Fencing Implementation Plan

**WORKING NOTE — NON-NORMATIVE**

Date: 2026-08-26
Related Task / Design: `NYRON-T-20260826-053`; `NYRON-D-004` §11, §19–20, §23, §26; Clarification 003 §§3–4; Clarification 004 §§7–8
Status: **WORKING / CANDIDATE — FOR ORCHESTRATOR DECISION, NON-NORMATIVE**

This note maps frozen `ARE-GATE-4 — Replacement Fencing` onto the *current accepted repository implementation* (post Gate-3 close, corrected Task 049+051 lineage integrated at merge commit `96698eda3e708945e9e12933ce8fe8793137db7f`). It recommends a minimal, evidence-backed implementation subdivision. It does not modify production code or Frozen Design.

## Current Repository Facts That Drive This Plan

These facts were independently verified by reading the accepted source, not assumed from the design documents:

1. **No Attempt-replacement mechanism exists today at any layer.** `RunRepository` (`src/nyron_kernel/execution/run.py`) implements exactly one method that writes `runs`/`run_attempts`: `create_initial()`. There is no `replace_attempt()`, no method that increments `runs.current_attempt_seq` or `runs.fencing_generation`, and no `run_attempts` state beyond `CREATED → ACTIVE → SUCCEEDED | FAILED`. Gate 4A is not "wiring into an existing replacement signal" — it must create the replacement primitive itself.
2. **The schema already supports it structurally.** `run_attempts` is keyed by the composite `(run_ref, attempt_seq)`, not just `run_ref` — a second row for `attempt_seq = 2` is already representable without a schema redesign. `runs.current_attempt_seq` and `runs.fencing_generation` are plain `INTEGER CHECK (... > 0)` columns with no trigger currently constraining their mutation (unlike `capability_grants`/`resources`/`effect_operations`, which all have `BEFORE UPDATE` immutability triggers on identity fields — `runs`/`run_attempts` currently have none).
3. **`RuntimeAuthorityResolver.resolve_current_with()`'s join is the load-bearing mechanism, and it already does exactly the right thing for free.** Its query (`src/nyron_kernel/execution/authority.py`) joins `run_attempts AS a ON a.attempt_seq = r.current_attempt_seq` and additionally requires `r.state = 'OPEN' AND a.state IN ('CREATED','ACTIVE')`. Every authority-mutating admission boundary already built in Gates 1–3 — `CapabilityAuthority.issue()`/`validate_advisory()`, `ResourceManager.issue_lease()`/`validate_lease_advisory()`, `EffectAuthority._admit_dispatch()` — calls `self._runtime_authority.is_current_with(connection, authority)` freshly, inside its own `BEGIN IMMEDIATE` transaction, before committing new authority. **This means: the instant a new Run-layer operation durably updates `runs.current_attempt_seq` to R2's value, R1's `AttemptAuthority` tuple stops matching this join forever — automatically, with zero changes to Capability, Resource, or Effect admission code.** This is the single most important fact this plan rests on.
4. **`EffectAuthority._admit_dispatch()`'s existing rejection path already produces the correct disposition for a stale-R1 `PREPARED` operation, unmodified.** When `is_current_with()` fails, the existing code (accepted in Gate 3A, unchanged since) sets the operation to `FENCED` (with `fence_evidence` basis `DISPATCH_REJECTED_BEFORE_ACTIVE`) if target evidence is `ABSENT`, or `UNKNOWN` if evidence is ambiguous — this is exactly the frozen disposition Gate 4 requires for an R1 `PREPARED` operation that a caller retries after replacement, and it needs no new code.
5. **`ResourceManager.revoke_lease()` and `EffectAuthority.request_revoke()`/`resolve_revoke()` already exist and are directly reusable** for the "fence R1's outstanding work" step — Gate 3's corrected revoke/fence semantics (Task 049+051) are exactly the primitive Gate 4B needs, not a new one.
6. **No conflict-scope concept exists anywhere in the codebase yet.** There is no table, field, or check that relates two different `EffectOperation` rows to each other. This is the one genuinely new piece of canonical truth Gate 4 must add (Gate 4C).

## A. Exact Replacement Authority Cutover

**The canonical linearization point is a single new Run-owned operation — `RunRepository.replace_attempt()` (name illustrative) — whose entire effect is one `BEGIN IMMEDIATE` transaction that:**

1. re-reads current `runs` row fresh inside the transaction;
2. enforces a CAS precondition: caller must supply the *expected* current `attempt_seq` and `fencing_generation` (exactly mirroring this project's own `Coordination Epoch/Revision` CAS convention — a deliberate, already-familiar pattern, not a new one); mismatch fails closed with a distinct error, no write;
3. verifies the current attempt's state is a legal replacement source (`CREATED` or `ACTIVE` — i.e., still logically the current attempt; already-terminal `SUCCEEDED`/`FAILED` attempts are not replaceable, they are finished);
4. transitions R1's `run_attempts` row to a new terminal state — **`REPLACED`** (a new value, not a reuse of `FAILED`, so a future Recovery/Reconciliation subsystem can distinguish "lost the replacement race" from "genuinely failed execution" — this is bookkeeping/audit value; see below for why it is not the *functional* linearization mechanism);
5. inserts the new `run_attempts` row for R2 (`attempt_seq = old + 1`, fresh state `CREATED`, a freshly-derived unique `fencing_token`);
6. updates `runs.current_attempt_seq` to R2's `attempt_seq` and `runs.fencing_generation` to `old + 1`, in the **same transaction** as steps 4–5.

**The functional cutover moment is step 6's commit**, specifically the `runs.current_attempt_seq` write. Per fact 3 above, this single write is *structurally sufficient* by itself to make every subsequent `is_current_with()` call for R1's tuple return `False` everywhere in the codebase, because the join key changes, not because R1's own row is inspected. Step 4 (marking R1's attempt `REPLACED`) is required for correctness of *direct* queries against `run_attempts` and for honest audit trails, but is not what makes R1 stop being able to canonical-commit or gain new authority — that guarantee comes entirely from the join. This distinction matters because it means Gate 4A's correctness argument does not depend on every future piece of code remembering to check the attempt's own state — it depends on one already-proven, already-reused query shape.

**Explicitly not the linearization point:** revoke propagation (calling `request_revoke()` on R1's `EffectOperation`s, or `revoke_lease()` on R1's `ResourceLease`s) is a *consequence* of replacement, handled by Gate 4B, and happens strictly *after* step 6 commits. It is not itself what stops R1 from gaining new authority — R1 already cannot gain new authority the instant step 6 commits, regardless of whether any revoke has been requested yet. Conflating the two would be exactly the class of error `NYRON-T-20260826-050-F-001` punished in the Effect layer (treating a downstream consequence as if it were the authoritative cutoff); this plan is deliberately structured to avoid repeating that mistake one layer up.

**Required new schema (Gate 4A, additive only):**
- `run_attempts.state` CHECK extended to include `REPLACED`.
- A `BEFORE UPDATE` trigger on `run_attempts` restricting legal transitions to `CREATED → {ACTIVE, REPLACED, FAILED}`, `ACTIVE → {SUCCEEDED, FAILED, REPLACED}` (extending the currently-unconstrained state column with the same discipline already used everywhere else in this schema).
- A `BEFORE UPDATE` trigger on `runs` (currently absent) preventing `current_attempt_seq`/`fencing_generation` from ever decreasing, and preventing any write path outside the CAS-checked replacement operation from touching them — this closes a real gap: today nothing stops a bug from writing `current_attempt_seq` directly.
- No changes to `capability_grants`, `resources`, `resource_leases`, or `effect_operations` schema are required for 4A.

## B. Existing R1 EffectOperations After Replacement

Per Clarification 004 §8 and the fact that admission is where authority is truly consumed (fact 3/4 above), the disposition below requires **no new EffectAuthority code** except where marked; it is a description of what already happens, plus what Gate 4B must actively drive.

| R1 EffectOperation state at replacement | What happens | New code needed? |
|---|---|---|
| `PREPARED`, no admission yet | Nothing happens automatically. If anyone later calls `execute()`/`prepare()` for it again, `_admit_dispatch()`'s existing `is_current_with()` check fails, and the existing rejection path commits `FENCED` (target `ABSENT`) or `UNKNOWN` (target ambiguous) — unchanged Gate-3A code. | No — already correct. Gate 4B should *actively* revoke it (via `request_revoke()`, which already handles the `PREPARED` case) rather than leaving it to be discovered lazily on next access, so R1's debt does not linger silently. |
| `ACTIVE` (admission already linearized before replacement) | This is genuinely pre-replacement in-flight work per Clarification 004 §8. It is **not** touched by replacement itself — it continues via normal Gate-3C mechanisms. Gate 4B actively calls the existing `request_revoke()` → `ACTIVE → REVOKE_REQUESTED`, then (synchronously, in this single-writer model) `resolve_revoke()` to resolve it to `COMPLETED` (exact evidence), or — per the Task 051 correction — the *executor itself*, if it is still the one driving that call stack, observes `REVOKE_REQUESTED` on its own fresh pre-mutation read and stops with truthful `EXECUTOR_STOPPED_BEFORE_FIRST_MUTATION` evidence, or `UNKNOWN` if cessation cannot be proven. | No new EffectAuthority method — reuses `request_revoke`/`resolve_revoke` exactly as accepted in Gate 3C. Gate 4B's new code is the *orchestration* that finds R1's `ACTIVE` operations and calls these existing methods; it does not add new EffectOperation-internal logic. |
| `REVOKE_REQUESTED` already | Already mid-resolution under Gate 3C rules; replacement adds nothing. Gate 4B may call `resolve_revoke()` again (idempotent — re-reading current state, re-checking evidence) to attempt to drive it to a terminal state, but must not assume it can force an outcome. | No. |
| `FENCED`, `COMPLETED`, `UNKNOWN` | Already terminal. Untouched. Frozen rule preserved explicitly: replacement never claims these prove or disprove anything beyond what Gate 3C already established — `FENCED` still does not mean "no historical consequence," `COMPLETED` still means exact proven consequence, `UNKNOWN` still means unresolved. | No. |

**Explicitly not permitted:** any Gate-4 code path that marks an R1 `ACTIVE`/`REVOKE_REQUESTED` operation `FENCED`/`COMPLETED` *merely because replacement occurred*, without going through the existing, already-corrected `resolve_revoke()`/executor-fresh-read evidence discipline. This would silently reopen exactly the class of bug fixed in Task 051.

## C. Existing R1 ResourceLeases After Replacement

| R1 ResourceLease state at replacement | Disposition | New code needed? |
|---|---|---|
| `ACTIVE` | Gate 4B calls the existing `ResourceManager.revoke_lease()` → `ACTIVE → REVOKE_REQUESTED`. Any subsequent `validate_lease_advisory()` (already existing, unchanged) correctly reports invalid the instant state leaves `ACTIVE`, independent of replacement. | No — reuses accepted Gate-2 method. |
| `REVOKE_REQUESTED` | Already non-`ACTIVE`; `validate_lease_advisory()` already rejects it. No further action required by replacement. | No. |
| `RELEASED`, `EXPIRED`, `UNKNOWN` | Already terminal/inactive. Untouched. | No. |

Frozen rule preserved: expiry/revoke of a Lease **never** implies the underlying `Resource` (the managed directory) is destroyed or that any external consequence did or did not occur — Gate 4 must not add any code that infers Resource disposition from Lease disposition (this exact distinction was independently verified intact throughout Gates 2–3 in this conversation's prior reviews and must not regress).

## D. Minimum Conflict Clearance Barrier (Gate 4C)

**New canonical concept required:** a deterministic, versioned `EffectConflictScope` comparison, and one new check inserted into `EffectAuthority._admit_dispatch()`'s existing admission transaction (alongside, not replacing, the existing Attempt/Grant/Lease checks).

**Smallest sufficient scope for the current bounded effect class** (`nyron.kernel.managed-resource-bounded-write@1` — the only effect class that exists in this codebase): two `EffectOperation` rows conflict **iff they share the same `resource_ref`** (the managed directory is the shared mutable object whose consistency actually matters; `target_ref` is a deterministic per-`operation_ref` hash within that directory, so two distinct operations essentially never collide at that finer grain for *this* effect class — scoping at `resource_ref` is the correct, non-speculative granularity for what exists today, not an arbitrary choice). The scope identity is versioned implicitly via the effect class's own `@1` suffix (already the established versioning convention for `RESOURCE_TYPE`/`EFFECT_CLASS`/`CAPABILITY_TYPE` throughout this codebase) — if a future effect class needs a different conflict granularity, it gets a new class version, not a generalized configurable scope engine.

**The barrier, checked inside R2's existing `_admit_dispatch()` transaction:**

```text
for R2's requested (effect_class, resource_ref):
    query effect_operations WHERE resource_ref = R2.resource_ref
                               AND run_ref != R2.run_ref
                               AND state IN ('PREPARED','ACTIVE','REVOKE_REQUESTED','UNKNOWN')
    if any row found -> CONFLICTING -> admission rejected (fail closed)
    else -> PROVEN_DISJOINT (no same-resource row in a conflict-relevant state exists) -> admission may proceed
```

This directly implements the frozen requirements:
- **Unproven disjointness fails closed as conflicting** — the query has no "I don't know" branch; either a conflicting row exists (reject) or it provably does not (proceed). There is no ambiguous middle state to mishandle.
- **`PREPARED`/`ACTIVE`/`REVOKE_REQUESTED`/`UNKNOWN` remain conflict-relevant** — all four appear in the `state IN (...)` list, exactly matching Clarification 003 §4's barrier table (`PREPARED` blocks unless proven non-dispatch and `FENCED`; `UNKNOWN` blocks by default; `ACTIVE`/`REVOKE_REQUESTED` block as active work).
- **`FENCED` does not block** — deliberately excluded from the `state IN (...)` list, because `FENCED` means only "this exact old operation's active continuation is stopped," which is precisely what makes it safe for a *new, distinct* operation on the same resource to proceed — but this is **active-conflict clearance only**.
- **`COMPLETED` does not block either** — a completed operation is not "in flight"; it has a known, proven outcome. It does not block new conflict-scope admission. (Whether R2's *specific semantic effect* is safe to perform given that history is a completely separate question — see below.)

**What R2 may and may not do once R1's conflicting operation is `FENCED`, `COMPLETED`, or `UNKNOWN`** — this is the exact orthogonality the frozen baseline (ARE-INV-21, ARE-INV-22) and this project's own Task 049/050/051/052 history were built to protect, and Gate 4 must state it explicitly rather than leave it implicit:

- Active-conflict clearance (the barrier above) only answers: *"is R2 free to begin dispatching a new, logically distinct effect against this resource right now?"* Once R1's row leaves the conflict-relevant state set, the answer can be yes.
- It **never** answers: *"is it safe for R2 to perform the same semantic effect R1 was attempting, as a retry?"* That is semantic retry clearance, and this Gate-4 minimal barrier deliberately does not implement it, does not infer it, and does not expose any field or API that could be mistaken for it. Clarification 004 §1's four conditions for safe same-semantic redispatch (proof of non-dispatch, external idempotency, distinct new operation, or explicit policy accepting duplicates) are **out of scope for Gate 4** and remain future work — likely a real semantic-retry-policy subsystem, explicitly listed as OUT OF SCOPE below.
- Concretely: after R1's operation is `FENCED`, R2 may be admitted for a *new* `operation_ref` targeting the same `resource_ref` (the barrier clears). Whether that new operation happens to carry byte-identical payload to R1's is not inspected or specially handled by Gate 4 — it is treated as what it structurally is: a distinct operation with its own identity, its own admission, its own evidence. Gate 4 does not need to (and must not) decide whether that constitutes a "retry" in the human sense; that judgment belongs to whatever future policy layer Clarification 004 anticipates, not to the conflict barrier.

## E. Does the Minimal Gate-4 Plan Activate `NYRON-T-20260826-043-F-001`?

**No.** Reasoning:

Every operation described above — `replace_attempt()`'s CAS transaction, the R1-fencing orchestration in 4B, and the conflict-scope query in 4C — is a synchronous function call executed by whatever single caller is already driving the Kernel in this process, using the *same* `SQLiteStore.transaction()` / `BEGIN IMMEDIATE` discipline every other authority-mutating write in this codebase already uses. "Non-conflicting concurrency" in the frozen sense (§11, ARE-INV-19/20/21) refers to two *canonical* facts' lifetimes logically overlapping — e.g., R1's `EffectOperation` being in a non-terminal state at the moment R2 requests admission — not to two pieces of code literally executing at the same wall-clock instant on separate threads. In the current single-process, single-writer, synchronous Kernel, "R1's effect is still `ACTIVE`" and "R2 is being admitted" are simply two facts read sequentially by the same call stack from the same database; nothing about proving or checking that relationship requires real OS-level parallelism. The conflict query in section D is structurally identical in shape to the Grant/Lease/Attempt checks `_admit_dispatch()` already performs today — same connection, same transaction, same synchronous read-then-decide pattern already accepted as sound (and empirically probed for genuine multi-connection linearization) in Tasks 042/043.

**Implementation restrictions that must hold for this conclusion to remain valid** (these must be stated as explicit constraints in every Gate-4 production Task, exactly as Gate 3's Tasks were constrained):

- `replace_attempt()`, the R1-fencing orchestration, and the conflict-scope check must all execute as ordinary synchronous method calls within the existing single connection/writer model — no thread, process, worker pool, async callback, or connection pool of any kind.
- No Gate-4 code may hold a `BEGIN IMMEDIATE` transaction open across the Effect layer's external filesystem mutation (the same constraint Task 051 was explicitly held to, and independently re-verified in Task 052).
- No Gate-4 code may introduce an in-memory lock table, worker registry, or other ephemeral local-authority object as a substitute for canonical SQLite state (the same constraint Task 051 was explicitly held to).
- If any future requirement needs R1-fencing or conflict resolution to be triggered *asynchronously* (a background sweep, a timer, a message-driven worker checking for stale Attempts) rather than synchronously by whatever caller invokes replacement, that crosses `043-F-001`'s activation condition and requires the real-concurrency revalidation Task 043's own note already specifies (independent connections/processes, a genuine race between revoke and admission, documented lock-timeout/failure-mode behavior) *before* such a Gate-4 extension may proceed.

`NYRON-T-20260826-043-F-001` correctly remains `OPEN` and is not weakened, narrowed, or closed by this plan — it is a standing precondition on any *future* concurrency-model change, not on the synchronous replacement mechanism described here.

## F. Does the Minimal Gate-4 Plan Activate `NYRON-T-20260825-038-F-001`?

**No.** None of 4A/4B/4C touch `ResourceManager`'s directory provisioning, recovery, or destruction code, introduce any new writer to the managed root, or expose the managed namespace to any actor that does not already have access today (the same single trusted Kernel process). Gate 4B's Lease-fencing step reuses the existing `revoke_lease()` API surface without modification. The activation condition (a less-trusted/co-resident actor gaining concurrent write access to the managed root) is unrelated to Attempt replacement and remains un-crossed.

## G. Minimal Gate-4 Subdivision

Repository facts support, and this plan recommends, the three-way split the Task suggested considering, adjusted based on what actually needs new code versus what is pure reuse:

### Sub-gate 4A — Runtime Attempt Replacement + Stale-Authority Cutover

**Objective:** Establish the one new canonical fact this entire Gate depends on: a CAS-guarded, atomically-committed `R1 → R2` current-Attempt cutover, and prove every existing Capability/Resource/Effect admission boundary correctly and immediately rejects R1 the instant it commits — *without modifying any of that admission code*.

**Expected production files:**
- `src/nyron_kernel/execution/run.py` — add `replace_attempt()` (or equivalent) to `RunRepository`.
- `src/nyron_kernel/store/sqlite_store.py` — additive only: extend `run_attempts` state CHECK/trigger to include `REPLACED`; add the previously-absent immutability/legal-transition trigger on `runs.current_attempt_seq`/`fencing_generation`.
- No changes to `capability/`, `resource/`, or `effect/` expected. Any such change requires a Finding before proceeding, exactly as Gate 3's own Tasks required.

**Mandatory fault injection/tests:**
1. CAS mismatch (stale expected `attempt_seq`/`fencing_generation`) fails closed, no write, R1 remains current.
2. Successful replacement: R1's row becomes `REPLACED`; R2's row is `CREATED`; `runs.current_attempt_seq`/`fencing_generation` both updated in one transaction.
3. Immediately after replacement, independently re-verify (not just assert) that `CapabilityAuthority.issue()`, `ResourceManager.issue_lease()`, and `EffectAuthority._admit_dispatch()` — called with R1's now-stale `AttemptAuthority` — each fail with `STALE_ATTEMPT_AUTHORITY`/`EFFECT_DISPATCH_AUTHORITY_REJECTED` exactly as they already do for any other staleness case, using the existing test fixtures, with zero changes to those modules.
4. Direct raw-SQL attempt to reactivate a `REPLACED` attempt or move `current_attempt_seq` backward fails via the new trigger (mirroring the Task 048/052 terminal-reactivation regression pattern already established for Capability/Resource/Effect).
5. Replacing a Run whose current attempt is already `SUCCEEDED`/`FAILED` (terminal, not `CREATED`/`ACTIVE`) fails closed — replacement is only legal against a still-live attempt.
6. Full existing `tests/kernel` suite remains green (regression guard for every prior Gate).

**Out of scope:** any EffectOperation/ResourceLease fencing (4B), any conflict-scope logic (4C), any change to how Modules or Effects consume authority.

**Independent HIGH-risk review required:** Yes — this is the foundational authority-cutover primitive every later Gate depends on; the same standard applied to Gate 1's Grant issuance and Gate 3A's dispatch admission applies here.

**Interlocks to recheck:** `043-F-001` (confirm no concurrency-model change — see §E); `038-F-001` (confirm untouched — see §F, trivially satisfied since 4A never touches Resource code).

### Sub-gate 4B — Old Effect / Lease Fencing on Replacement

**Objective:** Given a durable replacement (from 4A), actively drive R1's outstanding `EffectOperation`s and `ResourceLease`s toward a terminal disposition using **only already-accepted Gate 2/3C methods** (`revoke_lease()`, `request_revoke()`, `resolve_revoke()`) — no new authority-internal logic in Capability/Resource/Effect.

**Expected production files:**
- A small new orchestration surface — plausibly a method on `RunRepository` or a thin new module (e.g., `execution/replacement.py`) that, given a replaced `run_ref`, queries R1's non-terminal `EffectOperation`/`ResourceLease` rows and calls the existing revoke methods on each. Exact placement (Runtime-owned vs. a narrow cross-owner coordinator) should be decided by whichever avoids inventing a new "owner" — Effect Authority remains the Owner of `EffectOperation`, Resource Manager remains the Owner of `ResourceLease`; this orchestration should not claim ownership of either.
- No changes to `capability/authority.py` expected (Grants are already correctly unusable the instant 4A commits; nothing further to fence — Capability has no "in-flight" concept analogous to `ACTIVE`).

**Mandatory fault injection/tests:**
1. R1 `EffectOperation` in `PREPARED` at replacement time → actively revoked → `FENCED` (target absent) or `UNKNOWN` (ambiguous), matching existing Gate-3A/3C rules, never silently left dangling.
2. R1 `EffectOperation` `ACTIVE` at replacement time → `request_revoke()` → `REVOKE_REQUESTED` → resolves via existing `resolve_revoke()`/executor-fresh-read rules to `COMPLETED` (if exact evidence already present) or `UNKNOWN`/truthful `FENCED` — reuse and re-run the exact Task 049/051/052 evidence-truthfulness regressions against a *replaced* Attempt context, not just a same-Attempt revoke, to prove replacement doesn't reintroduce the false-`FENCED` race in a new guise.
3. R1 `ResourceLease` `ACTIVE` at replacement → `revoke_lease()` → `REVOKE_REQUESTED`; `validate_lease_advisory()` correctly reports invalid immediately.
4. Already-terminal R1 effects/leases are left untouched (idempotent no-op), independently verified via direct row inspection before/after.
5. Confirm no new `EffectOperation`/`ResourceLease` state values were invented (reuse of the exact frozen vocabulary only).
6. Full existing `tests/kernel` suite remains green.

**Out of scope:** conflict-scope admission logic for R2 (4C); any change to what `FENCED`/`UNKNOWN` mean; any automatic retry of R1's fenced work.

**Independent HIGH-risk review required:** Yes — this is exactly the "does replacement silently fabricate cessation" surface Task 050/052 already proved is easy to get subtly wrong once, elsewhere in this same codebase.

**Interlocks to recheck:** `043-F-001` (still synchronous orchestration, no new writer model); `038-F-001` (reuses `revoke_lease()` unmodified, no new Resource surface).

### Sub-gate 4C — Conflicting / Non-Conflicting R2 Effect Admission Barrier

**Objective:** Add the one genuinely new canonical concept, `EffectConflictScope`, as the minimal `(effect_class, resource_ref)`-keyed check described in §D, inserted into the existing `_admit_dispatch()` transaction.

**Expected production files:**
- `src/nyron_kernel/effect/authority.py` — add the conflict query as one additional `valid = valid and ...` clause inside the existing `_admit_dispatch()` transaction (same pattern already used for Grant/Lease/Attempt checks); no new public method needed unless a standalone `check_conflict_clearance()` query is independently useful for callers (optional, decide during implementation, not here).
- No schema change expected — the query reads only the already-existing `effect_operations.resource_ref`/`state` columns.

**Mandatory fault injection/tests:**
1. R2 admission against a `resource_ref` with an R1 row in `PREPARED`/`ACTIVE`/`REVOKE_REQUESTED`/`UNKNOWN` → rejected (conflicting), independent of whether R1 was ever formally replaced (the barrier is scope-based, not replacement-specific — it must also correctly block same-Run self-overlap if ever attempted, not only cross-Attempt conflicts, unless deliberately scoped to cross-Run/Attempt only — this exact boundary must be decided and tested explicitly during implementation).
2. R2 admission against a `resource_ref` with only `FENCED`/`COMPLETED` R1 rows (no other conflicting row) → proceeds; independently verify R2's own admission, `ACTIVE` commit, and mutation are otherwise entirely unaffected by R1's history (no evidence bleed-through, no shared state).
3. Explicit regression proving `FENCED` clearing the barrier does **not** grant R2 any special "retry" status: R2's operation is admitted, mutated, and evidenced exactly like any first-time operation — assert no code path reads or depends on R1's `fence_evidence`/`completion_evidence` content when deciding R2's own outcome.
4. Unproven/ambiguous case (e.g., a row whose state cannot be read, or a malformed scope) fails closed as conflicting — there must be no code path that defaults to "proceed" on error.
5. Full existing `tests/kernel` suite remains green, plus the full 4A/4B regressions re-run together (integration-level fault injection: replace R1 mid-flight, fence its effects via 4B, then admit a conflicting and a non-conflicting R2 effect in the same scenario).

**Out of scope:** any generalized multi-dimension conflict scope beyond `(effect_class, resource_ref)`; any semantic-retry-safety inference; Canonical Command; any product-facing conflict-policy configuration surface.

**Independent HIGH-risk review required:** Yes — this is the "unproven disjointness fails closed" property, a named frozen invariant (ARE-INV-19); it deserves the same adversarial scrutiny every other authority-boundary Task in this project has received.

**Interlocks to recheck:** `043-F-001` (confirm the conflict query stays inside the existing single transaction, no new writer path — see §E); `038-F-001` (untouched — 4C never touches filesystem code).

### Sequencing

4A must land and be independently accepted before 4B (4B's fault injections require a real replaced Attempt to act on). 4C is logically independent of 4B's *content* but should follow both, since its regression suite (item 5 above) is most meaningful once real R1 fencing exists to exercise against. Recommend strict sequential Task order 4A → 4B → 4C, each with its own independent HIGH-risk review, mirroring exactly the 3A → 3B → 3C precedent this project already established and that proved effective (each sub-gate review in that chain caught something real).

## Unresolved Architecture Finding

**NONE.** The current accepted Frozen Design bundle and the current accepted Runtime/Capability/Resource/Effect implementation contain enough information to plan Gate 4 without any semantic contradiction requiring a Frozen Design amendment. The one open question genuinely left to implementation-time judgment — whether the Gate-4C conflict barrier should treat same-Run/same-Attempt self-overlap identically to cross-Attempt overlap — is an implementation-scope decision, not an architecture gap, and is flagged explicitly in 4C's test list above rather than resolved here.

## Explicitly Rejected Alternatives

- **Building a generalized multi-dimension `EffectConflictScope` engine now** (configurable per effect class, pluggable comparators) — rejected; only one effect class exists, and Clarification 003 §3 explicitly allows scope schemas to remain "EffectClass-specific and versioned" rather than generalized up front.
- **Building a semantic-retry-policy subsystem alongside the conflict barrier** — rejected; explicitly out of scope per Clarification 004 §1 and the Task's own restrictions; conflating it with active-conflict clearance is precisely the error the frozen baseline's F01 finding (Amendment 001 companion) already corrected once at the design level.
- **Implementing R1-fencing as new EffectAuthority/ResourceManager-internal methods** instead of reusing `request_revoke`/`resolve_revoke`/`revoke_lease` — rejected; those methods were purpose-built and independently re-reviewed twice (Tasks 050, 052) for exactly this evidence-truthfulness property; duplicating that logic elsewhere would both violate DRY for a genuinely identical concern and reopen surface area already hardened.
- **Introducing a background sweep/worker to detect and fence stale Attempts automatically** — rejected for this Gate; it would cross `043-F-001` for no proven current requirement (nothing in this Kernel-foundation slice yet drives replacement from anything other than a synchronous caller decision).
- **Marking R1's admitted `ACTIVE` effects `FENCED` immediately upon replacement, without going through revoke/resolve** — rejected; this is exactly the frozen-invariant violation (`ARE-INV-08`, and the lesson of Task 050) this plan is structured to avoid; already-admitted work must complete via normal evidence-based mechanisms, not be short-circuited by replacement itself.

## Reusable Insight

The single most valuable property this plan surfaces is that **a correctly-designed admission boundary (fresh authority re-check inside the same transaction as the durable write, repeated identically at every Owner) makes replacement fencing almost free at the admission layer** — three separate subsystems (Capability, Resource, Effect), built independently across Gates 1–3 by the same discipline, all correctly reject a replaced Attempt's authority the instant one Runtime fact changes, with no coordination between them required. The real remaining engineering effort is entirely in (a) building the replacement primitive itself (4A) and (b) actively driving already-in-flight work to a truthful terminal state (4B) — not in re-teaching every Owner about replacement.

## Promote To

- A concrete `NYRON-T-20260826-054`-style Task definition for Sub-gate 4A, if the Orchestrator accepts this plan and opens Gate-4 implementation.
- Future Development Orchestration Guide entry: "an admission boundary that re-validates fresh authority inside its own write transaction, applied uniformly across every canonical Owner, turns a later replacement/fencing Gate into an additive change rather than a cross-cutting rewrite" — a pattern worth naming for reuse beyond this project.
