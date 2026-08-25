# ARE-GATE-3B Debt Settlement Candidate

Date: 2026-08-26
Related Task / Design: `NYRON-T-20260826-044`; `NYRON-T-20260825-038-F-001`; `NYRON-T-20260826-043-F-001`; `NYRON-D-004` §§10–11, §26
Status: **WORKING / CANDIDATE — FOR ORCHESTRATOR DECISION, NON-NORMATIVE**

## Current Facts

- `ARE-GATE-3A` is `PASS / CLOSED`. The accepted bounded EffectOperation foundation establishes: durable `PREPARED` before dispatch, a real race-safe dispatch-admission linearization against Runtime Attempt/fencing + CapabilityGrant + ResourceLease, one deterministic trusted bounded filesystem mutation, and exact-evidence crash recovery to `COMPLETED`/`UNKNOWN`.
- `ARE-GATE-3B` is not open. No long/async effect, revoke/cancel-of-admitted-effect, retry/replacement, Canonical Command, or generalized conflict/recovery semantics exist yet.
- Two `NON_BLOCKING` findings remain open, both explicitly deferred pending this analysis:
  - `NYRON-T-20260825-038-F-001` (`SECURITY`) — a narrow TOCTOU window in `ResourceManager`'s provisioning path, between managed-directory `mkdir()` and the separate provenance-marker `open(..., "x")` write, exploitable only by a co-resident actor with concurrent write access to the exact managed root.
  - `NYRON-T-20260826-043-F-001` (`ARCHITECTURE`) — the Effect dispatch-admission linearization is real (independently proven, including by a live two-thread/two-independent-connection `BEGIN IMMEDIATE` probe) but is load-bearing on every authority-mutating write in the Kernel continuing to go through `SQLiteStore.transaction()` on a single logical writer.
- Both findings were re-confirmed unchanged and still correctly classified across `NYRON-T-20260825-040` (Resource) and the Task 042/043 EffectOperation work — neither the Effect boundary nor any coordination change so far has expanded either threat surface.
- Note: the Effect target write itself (`EffectAuthority._mutate_and_complete`, using `open(path, "xb")` = `O_CREAT|O_EXCL`) is **not** subject to the same TOCTOU class as `038-F-001` — `O_EXCL` refuses to create through a pre-existing symlink at that name by POSIX definition. `038-F-001` is specific to Resource's own two-step `mkdir()` + separate marker-file write during provisioning; it was not reproduced or worsened by Task 042.

## Part A — Resource Provenance TOCTOU (`038-F-001`)

### A1. Activation conditions (become BLOCKING when true)

Any one of the following makes `038-F-001` a blocking prerequisite:

1. A Module-facing or otherwise less-trusted filesystem read/write API is wired through `resource.external_ref` (i.e., any consumer besides the trusted `ResourceManager`/`EffectAuthority` code itself gets to touch the managed directory).
2. The managed root, or its parent directory, becomes concurrently writable by any actor that is not the single trusted Resource-Manager process — including a sandboxed/hostile Module, a second unrelated service, or a shared/network filesystem location where other principals have write access.
3. `ARE-GATE-5` (Module Host trust boundary) work begins exposing any resource-handle-mediated filesystem access to less-trusted code.
4. The managed root is relocated to a filesystem whose local-syscall atomicity assumptions differ from the currently assumed POSIX semantics (e.g., certain network filesystems), without re-deriving the safety argument for that filesystem.

### A2. Does planned `ARE-GATE-3B` activate it?

**No, provided 3B is scoped as recommended in Part D.** 3B's own subdivision note scopes it as "long/async + crash ambiguity" for the *same* bounded, trusted-adapter effect model already accepted in 3A — it does not by itself introduce a new writer to the managed root, a less-trusted actor, or a change of trust level. The one scenario that *would* brush against this finding — a genuine background thread/process performing dispatch — is addressed in Part D's scope constraint and is more precisely a trigger for `043-F-001` (concurrency) than for `038-F-001` (trust level), since a same-trust-level background worker is not a "less-trusted co-resident actor." If 3B is implemented as recommended (single-writer, no real background execution), `038-F-001`'s activation condition is not crossed.

### A3. Smallest cross-platform hardening strategy

The gap is narrowly located: `ResourceManager._open_root()`'s marker write and `recover()`'s `PROVISIONING` branch each perform a separate `mkdir()`/`path.mkdir()` followed by a *second*, independent `open(path / marker, "x")` call, leaving a pathname-re-resolution window between them.

Recommended minimal fix (POSIX-primary, with a documented, already-safe fallback):

1. Immediately after a successful `mkdir()`, open the freshly created directory itself with `O_DIRECTORY | O_NOFOLLOW` to obtain a directory file descriptor *before* any other operation touches that path by name. If this open fails, treat it exactly as today's "MISMATCH" case (fail closed to `UNKNOWN`) — do not retry by pathname.
2. Write the provenance marker using that directory file descriptor (`dir_fd`-relative `os.open(dir_fd=fd, marker_name, O_CREAT | O_EXCL | O_WRONLY)`) rather than a second pathname-based open. Because the marker write is now bound to the *file descriptor* obtained at step 1, no subsequent pathname substitution of the parent entry can redirect it.
3. Feature-detect `os.supports_dir_fd`/`O_NOFOLLOW` availability at import time. Where unavailable (this includes the current Windows review/test environment, where creating a symlink at all requires an elevated privilege the attacker in this threat model would not incidentally have), fall back to the current sequential check-then-write behavior, which is not a regression on that platform — Windows's own privilege model already makes the specific attack impractical there today, and this was independently confirmed during the Task 038 review (`os.symlink` on the review host required `SeCreateSymbolicLinkPrivilege` and failed for an unprivileged process).
4. Apply the identical pattern to the `DESTROYING` recovery branch's pre-`shutil.rmtree` evidence check for defense-in-depth consistency, even though `shutil.rmtree` already independently refuses a top-level symlink argument (verified during the Task 038 review via `inspect.getsource(shutil.rmtree)`), so that branch is not itself blocking — only doing it for uniformity, not because it is currently unsafe.

This stays within "smallest hardening": one localized change to two existing methods in `resource/manager.py`, no new module, no generalized filesystem/provider/adoption framework, no change to the Resource canonical schema.

### A4. Required tests / adversarial validation

1. A POSIX-only test (skipped or `unittest.skipUnless` on symlink-privilege detection) that plants a symlink at the exact resource path in the window the fix closes, and asserts the outcome is `UNKNOWN` with no write occurring through the symlink target — the deterministic-injection technique already used for `crash_hook` testing throughout this codebase is directly reusable here (a testing seam, not a new framework) to force the interleaving without needing real threads.
2. A test proving the fallback path (no `dir_fd` support) still correctly classifies a pre-existing symlink as `MISMATCH`/`UNKNOWN` on the current behavior, so the fallback platform is not silently unguarded.
3. Re-run of the existing `test_resource_ref_cannot_escape_root_and_unproven_directory_is_unknown` and `test_mismatched_marker_is_unknown_and_never_adopted` tests to confirm no regression to the already-accepted provenance behavior.

### A5. Timing recommendation

**A small, dedicated pre-3B hardening implementation task — not bundled into 3B, and not deferred to Host/ARE-GATE-5 work.**

Reasoning: the fix is fully diagnosed, small, localized, and does not require any Host/Module trust-boundary design that doesn't already exist. It has now been re-confirmed as still-open, still-correctly-non-blocking debt across three independent review cycles (`038`, `040`, and implicitly re-checked in `043`/this Task) — every additional cycle that re-confirms rather than closes it is pure repeated overhead with no compounding benefit, since the underlying facts are not expected to change. Deferring it to Host/ARE-GATE-5 would also mean it competes for review attention with a substantially larger, higher-risk trust-boundary design at exactly the point where filesystem hardening matters most — closing it now, while the blast radius is still small and the fix is cheap, is strictly better sequencing than deferring it into a larger, riskier gate later.

## Part B — SQLite Writer / Linearization Debt (`043-F-001`)

### B1. Exact invariant future code must preserve

> Every write that can create, revoke, release, expire, or otherwise change canonical Capability/Resource/Lease/EffectOperation authority state must execute inside `SQLiteStore.transaction()` (i.e., under `BEGIN IMMEDIATE`), and any authority re-check that gates a durable admission/consumption write must be performed on the *same* open transaction as that write, with no intervening commit point.

This is a two-part invariant: (a) single logical writer discipline via `BEGIN IMMEDIATE` across all subsystems, and (b) admission-time re-validation and the durable admission write are atomic (same transaction), never split across two commits.

### B2. Changes that must trigger mandatory revalidation

- Introduction of any raw `sqlite3.connect()` write path that bypasses `SQLiteStore.transaction()`.
- Connection pooling, or any abstraction that gives more than one connection concurrent write intent against the same database without funneling through the same `BEGIN IMMEDIATE` discipline.
- A genuinely multi-threaded or worker-pool Runtime where more than one OS thread can be inside authority-mutating code concurrently (this also requires revisiting `check_same_thread`, which is currently left at its default `True`).
- Any transaction-mode/locking/`PRAGMA` change (e.g., WAL with relaxed `synchronous`, or moving off `BEGIN IMMEDIATE`) that changes the locking guarantee the current proof relies on.
- Long/async Effect execution where dispatch or completion happens from a separate thread, process, or callback rather than a synchronous call on the same writer.
- Any move of authority state off a single SQLite file (distributed/process-separated storage) without an independently re-derived ordering proof.

### B3. Is code/test hardening required now?

**No.** For the current, actually-deployed single-writer Kernel, the existing interlock note (`docs/development/notes/2026-08-26_Effect_Linearization_Concurrency_Interlock.md`) plus the live empirical probe already performed during Task 043's review constitute sufficient current-state evidence. Building concurrency test scaffolding, a locking abstraction, or speculative multi-connection handling *now*, before any real concurrent execution model exists, would itself be the class of premature-generality complexity this project's own review culture (`coordination/REVIEW_PROTOCOL.md` §5) explicitly treats as `OVER_ENGINEERING`. The correct current action is the documentation interlock that already exists, not a code change.

### B4. Minimum real-concurrency validation once a trigger activates

1. Real independent OS threads or processes with independent connections — not only the deterministic `crash_hook`-style injection used so far (which remains valuable for proving *exact ordering semantics* once a race is possible, but cannot by itself prove that real concurrent execution behaves as assumed).
2. A genuine race in which revoke/release/stale-Attempt-replacement is timed to compete with an in-flight dispatch admission, run repeatedly (stress-style, not a single deterministic pass) to surface non-deterministic interleavings.
3. Explicit confirmation that exactly one of Clarification 004's Case A / Case B orderings wins on every trial, with zero observed partial or duplicated admissions.
4. Explicit, tested behavior under lock contention/timeout (`sqlite3.OperationalError: database is locked`) — the current `SQLiteStore` relies on the sqlite3 default 5-second busy timeout with no defined retry/backoff/fail-closed policy; a genuinely concurrent model must decide and test this before relying on the proof.
5. If authority storage ever moves off a single SQLite file, an independently re-derived linearizability argument for the replacement mechanism (e.g., `SELECT ... FOR UPDATE`, application-level fencing/CAS, or an equivalent), not an assumption that the SQLite-specific proof transfers.

### B5. May `ARE-GATE-3B` proceed without closing this finding?

**Yes — conditionally.** `3B` may proceed without closing `043-F-001` if, and only if, `3B`'s Task definition explicitly constrains its "long/async" semantics to remain **logically single-writer**: the effect's `PREPARED`/`ACTIVE`/`COMPLETED`/`UNKNOWN` progression may span multiple separate synchronous calls over simulated elapsed time (mirroring how crash-window recovery already works today), but no real background thread, process, or async I/O callback may perform dispatch or authority-mutating writes concurrently with other Kernel authority operations.

**Required evidence to justify this:** `3B`'s own Task file must state this constraint as an explicit, authorized scope boundary (not leave it implicit), and `3B`'s own HIGH-risk independent review must include a specific mandatory question confirming the delivered diff actually honored it (no new thread/process/connection was introduced) — exactly the same "adversarial verification, not just reading the stated scope" discipline already established for `038-F-001` in Tasks 040 and 043.

## Part C — Debt Accumulation / Gate Eligibility Checklist

A small, practical rule — not a new framework, registry, or tool. It reuses the `STATUS.md` Open Findings table and the existing "Required Reading" convention that later Tasks already follow.

1. Every threat-model-dependent `NON_BLOCKING` finding must carry one explicit, one-sentence **Activation Condition** (already true for both findings here).
2. Any new Task whose Objective plausibly touches a finding's subject area (filesystem trust boundary, concurrency/writer model, etc.) must include that finding's note in its Required Reading, and its Task file or STATUS entry must state, in one line, whether the Task's *actual scope* crosses the Activation Condition.
3. If it crosses: the finding becomes a blocking prerequisite for that Task's acceptance, until either closed by hardening + re-review, or formally reclassified by the Orchestrator on current evidence — never silently waived.
4. If it does not cross: the Task may proceed, but the finding stays open and unchanged in `STATUS.md`, and the *next* Task touching that subject area must ask the same question again — this is a per-Task discipline, not a one-time clearance, because stated scope and actual delivered diff can diverge (which is exactly what independent HIGH-risk review already checks for).
5. This checklist is enforced entirely through mechanisms that already exist in this project (Finding text, Required Reading lists, STATUS Open Findings table, mandatory review questions) — no new debt-tracking subsystem is introduced.

## Part D — Next Bounded Gate Recommendation

**Recommendation: sequence a small, dedicated pre-3B hardening task for `038-F-001` (Part A5), then open a narrowly-scoped `ARE-GATE-3B` that explicitly preserves `043-F-001` as a non-blocking interlock under the single-writer constraint from Part B5.**

This is not "stop with an Architecture Finding" — the frozen `D-004` bundle (Module Amendment 001's `PREPARED → ACTIVE → COMPLETED/UNKNOWN` transitions, already present in the accepted schema but unexercised by 3A) contains enough information to scope 3B safely without any new design decision.

### Smallest safe `ARE-GATE-3B` scope

**In scope:**

- Extend the same bounded, trusted managed-resource-write effect class (or one similarly bounded new effect class) to actually exercise the `PREPARED → ACTIVE` transition that 3A left unused: after dispatch admission, durably commit `ACTIVE` *before* attempting the external mutation, representing "dispatch has begun, outcome not yet certain."
- Prove crash recovery correctly resolves `ACTIVE → COMPLETED` (exact evidence match) or `ACTIVE → UNKNOWN` (mismatched/ambiguous/absent evidence) using the same exact-evidence discipline already accepted in 3A — this is the actual "long/async + crash ambiguity" objective named in the Gate-3 subdivision note.
- Represent "long-running" as state persisting across multiple separate synchronous `execute()`/`recover()`-style calls over simulated elapsed time (test-controlled), not as real background execution.

**Explicitly OUT (mirrors 3A's own discipline, plus the new single-writer constraint from B5):**

- Any real background thread, process, or async I/O callback performing dispatch or authority-mutating writes concurrently with other Kernel operations (protects `043-F-001`'s non-blocking status — see B5).
- `REVOKE_REQUESTED`/cancellation handling for an already-admitted effect (still a distinct, separately-bounded increment).
- Retry/replacement, semantic retry clearance, `EffectConflictScope`, Canonical Command, `BudgetReservation`/settlement, Recovery/Reconciliation subsystem, Module filesystem API, `ARE-GATE-5` hostile-plugin sandbox — all remain future, separately-bounded work, unchanged from 3A's own scope restrictions.
- Any connection-pool, multi-writer, or transaction-discipline change (protects `043-F-001`; would immediately require the full B4 real-concurrency validation instead of the lighter B5 path).
- Any change to the managed-root trust model (protects `038-F-001`'s continued non-activation per A2).

### Unresolved Architecture Finding

**NONE.** This candidate does not identify any gap in Frozen Design that blocks a safe decision; both parts of the recommendation are derivable from the already-accepted D-004 bundle and Module Amendment 001.

## Explicitly Rejected Over-Engineered Alternatives

- **Building a generic distributed-lock / connection-pool abstraction now** "to future-proof" concurrency — rejected as premature; no current requirement exists, and it directly contradicts this project's own Simple-Correct-First/YAGNI discipline (`coordination/REVIEW_PROTOCOL.md` §5).
- **Building a generalized Resource-provenance/external-adoption security framework** (e.g., a full capability-based filesystem sandbox) to close `038-F-001` — rejected; the actual gap is two syscalls in one method, and the fix in A3 stays local to that method.
- **Building a generalized Finding/debt-tracking subsystem** (structured ledger, auto-expiry, dashboards) for Part C — rejected per this Task's explicit restriction; the existing `STATUS.md` Open Findings table plus Required Reading convention already covers the need.
- **Implementing real multi-threaded/async dispatch in 3B now**, "to get concurrency over with in one pass" — rejected because it would simultaneously activate both open findings inside one Task, mixing two independent failure-mode proofs (filesystem trust and concurrency linearization) into one review surface, exactly what the Gate-3 subdivision philosophy was adopted to avoid.
- **Deferring `038-F-001` hardening indefinitely until `ARE-GATE-5`** — rejected; the fix is cheap and fully diagnosed today, and further deferral only adds repeated re-confirmation overhead (this is the third review cycle to re-confirm it unchanged) without any offsetting benefit, and stacks filesystem hardening onto what will already be a large, higher-risk Host trust-boundary design.

## Reusable Insight

A `NON_BLOCKING` finding whose safety depends on "the attacker capability this requires doesn't exist yet" is not settled by writing that fact down once — it must be re-askable against every future Task's *actual delivered scope*, not just its stated Objective, using the same Required-Reading-plus-explicit-question mechanism this project already uses for independent review. The cheapest time to close a fully-diagnosed, narrowly-scoped debt item is before it has to compete for review attention with a larger gate that touches the same code area — not after.

## Promote To

- A concrete pre-3B hardening implementation Task, if the Orchestrator accepts this candidate's Part A5 recommendation.
- A concrete `ARE-GATE-3B` Task definition incorporating the Part D scope and the Part B5 single-writer constraint as an explicit authorized boundary, if the Orchestrator accepts opening 3B next.
- Future generic Development Orchestration Guide entry for the Part C checklist pattern (threat-model-dependent debt re-evaluation on every touching Task), alongside the existing Gate-3-subdivision and stale-policy notes.
