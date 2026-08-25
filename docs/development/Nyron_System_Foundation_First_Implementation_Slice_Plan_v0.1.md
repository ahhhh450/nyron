# Nyron System Foundation — First Implementation Slice Plan v0.1

**Task:** `NYRON-T-20260825-003`
**Type:** Implementation Planning (this document proposes no runtime code and changes no frozen semantics)
**Coordination basis:** Epoch `1` / Revision `8` (revised under `NYRON-T-20260825-007`; previously revised under `NYRON-T-20260825-005` at Revision `6`; originally authored under Revision `4`)
**Authoritative sources this plan traces to:**
- `design/Nyron_Overall_System_Architecture_Frozen_Baseline_v0.1.md`
- `design/Universal_Runtime_Module_Design_Report_v0.1.md`
- `design/Nyron_Runtime_Orchestration_Frozen_Baseline_v0.1.md` (frozen manifest) + `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md` §9, §10, §17, §19 (the frozen bundle's normative Run/Attempt/fencing/crash-recovery content — read for the F-001 correction)
- `design/Nyron_Accounting_Recovery_Frozen_Baseline_v0.1.md`
- `design/amendments/Graph_Accounting_Amendment_001_Static_Accounting_Scope_Resolution.md` §4 (mandatory admission validation — read in full for the F-002 correction)
- `design/Nyron_Capability_Resource_Effect_Authority_Frozen_Baseline_v0.1.md` (boundary only; not exercised by this slice)

This plan does not reinterpret, extend, or narrow any frozen semantic. Where it makes an implementation-tooling choice not fixed by the frozen baselines (language/runtime, file layout), that choice is marked explicitly and is not itself a Frozen Architecture decision.

## Revision Note (`NYRON-T-20260825-005`)

This revision targetedly closes all four findings from independent Review `NYRON-T-20260825-004` (`FAIL` against the original `NYRON-T-20260825-003` delivery) without broadening the first slice or changing any frozen semantic:

- **F-001** (Run/Attempt/fencing/crash semantics — CONTRACT/BLOCKING): §3, §4, §5, §6, §7 and §10 now model `Run` and `RunAttempt` as the two distinct frozen entities defined by `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md` §9, use the full frozen current-attempt fencing tuple, and distinguish safe scheduler redispatch from an ambiguous crossed-boundary Attempt per that Candidate's §10.4/§17.3.
- **F-002** (Accounting admission boundary — CONTRACT/BLOCKING): §3 and §7 now enumerate all five mandatory conditions from `Graph_Accounting_Amendment_001` §4 and make explicit that Runtime only consumes the Accounting Owner's authoritative resolution result; it never derives or locally owns Accounting truth. The gate also moves from per-Activation (`activation.py`) to a new `execution/admission.py` implementing `ExecutionAdmission`, matching the Amendment's exact "before Runtime admits a WorkflowExecution" wording.
- **F-003** (missing atomicity/idempotency/determinism tests — TEST/BLOCKING): §6 adds explicit executable tests for Activation rollback, Delivery double-binding prevention, Delivery uniqueness, interrupted fan-out replay idempotency, output/Attempt/Run atomic-commit crash windows, duplicate/late `Completed`, and same-committed-history replay determinism.
- **F-004** (SQLite overclaim — IMPLEMENTATION/NON_BLOCKING): §3's storage recommendation is reworded to an overridable engineering choice justified only on current simplicity/dependency grounds, with no claim that the frozen architecture selected or presupposed SQLite.

Everything not touched by these four findings is unchanged from the original `NYRON-T-20260825-003` delivery.

## Revision Note (`NYRON-T-20260825-007`)

Targeted Re-Review `NYRON-T-20260825-006` (against the `NYRON-T-20260825-005` correction) closed F-001, F-002 and F-004 but kept **F-003 open**: the plan's crash-window test coverage tested the boundaries *around* the §12 canonical transaction (before it opens; after it commits) but did not prove the transaction is all-or-nothing *internally* across all four of its writes. This revision adds exactly that missing test to §6 — a fault injected after the in-transaction Attempt-terminal-state and Run-terminal-state writes but before Output Packet/canonical-event creation, asserting full rollback with no partial state, followed by a clean single retry with no duplication. F-001, F-002 and F-004 are not reopened or re-touched.

---

## 1. Recommended First System Foundation Vertical Slice

**Slice: Module Definition Registry + Execution ABI**, i.e. exactly Phase 1 + Phase 2 of the frozen Module implementation route (`Universal_Runtime_Module_Design_Report_v0.1.md` §40):

- Register one immutable `ModuleDefinition`: the frozen worked example `builtin.text.concat@1` (§32) — `effects: PURE`, no required capabilities, inputs `a: REQUIRED_LATEST`, `b: TRIGGER`, output `text`.
- Publish one immutable `GraphRevision` containing exactly one `ModuleInstanceRevision` that pins `builtin.text.concat@1` and carries a resolvable `static_accounting_scope_ref`.
- Admit the `GraphRevision` for execution (validating the accounting-scope gate below).
- Drive one Trigger `Packet` through `Delivery` projection → transactional `Activation` creation (§10) → `Run`/Attempt execution via the `execute()` ABI (§11) → canonical commit of the terminal outcome and `Output Packet` (§12).

No Capability, Resource, Effect, Suspension, or Recovery machinery is built in this slice.

## 2. Why This Is the Smallest Slice That Proves Frozen Core Semantics

1. It is not an invented staging — it is the exact Phase 1–2 gate the frozen Module baseline itself declares as the first implementation gate (§40: "Phase 1–2 为首个实现 Gate"). No alternative first slice needs to be justified from scratch.
2. It is the minimum surface that exercises the sole execution path required by Overall Invariant #3 (`Packet -> Delivery -> Activation -> Run/Attempt`) and by the Runtime Orchestration frozen baseline's frozen scope (single execution path, one current Attempt per Run, current-attempt fencing).
3. Restricting the seeded module to `PURE` means Capability/Resource/Effect Authority (Phase 3–4), Suspension (Phase 5) and Effect Fencing/Recovery (Phase 6–7) are correctly deferred — there is nothing yet for them to mediate, so building them now would be speculative complexity forbidden by `skills/implementation/SKILL.md`.
4. It still forces genuinely non-trivial, non-deferrable correctness:
   - `Graph_Accounting_Amendment_001` (GA-INV-01/02): a `GraphRevision` cannot be admitted for ordinary execution while any `static_accounting_scope_ref` is unresolved — this applies even to a single-module PURE graph, so a minimal Accounting-Owner-mediated resolution check is unavoidable in slice 1, not optional.
   - M-INV-01/02/03/16: Run→Attempt→Activation ownership and immutable Module/Graph reference resolution.
   - M-INV-07/M-INV-02 and §12's canonical-commit re-validation of current Attempt: Commit Fencing must exist even though there is no Effect Fencing yet, because canonical Run-outcome commit is itself a fencing-sensitive transaction independent of Capability/Effect.
   - §39 Committed-History Determinism: restart must recompute the same pending Deliveries / next Activation from durable facts alone.
5. Everything genuinely deferrable (Capability, Resource, Suspension, Effect, Reconciliation) is deferrable *precisely because* PURE-only admits no effect — this is a real current-scope argument, not a convenience argument.

## 3. Concrete Implementation Modules / Files / Package Boundaries

**Implementation-tooling recommendation (not fixed by any frozen baseline; repository currently has no prior language/runtime decision — verified by targeted search, no hit besides the Module baseline's own text):**

Python 3.11+, stdlib `sqlite3` as the StateStore backing for this first slice. **This is an overridable engineering choice, not a frozen-architecture selection.** No frozen baseline names, requires, or presupposes any specific storage technology — the Module baseline's references to "raw StateStore/SQLite" (§17, §29) are examples of what Module code must never access directly, not a technology mandate. The recommendation here rests only on current engineering-simplicity grounds: an embedded, dependency-free, transactional store is sufficient to implement the two canonical transactions this slice requires (§10, §12) without standing up external infrastructure for a first vertical slice. Any other transactional store satisfying the same durability/atomicity requirements is equally acceptable, and a future Implementation Task or the Orchestrator may replace this choice without triggering an Architecture Finding. Python is likewise chosen only for fast, dependency-light transactional/state-machine code; nothing here blocks the frozen Module Host boundary (§29) from hosting non-Python Modules later — that boundary is already frozen as a protocol boundary, not a language commitment. If the Orchestrator already has a different language/storage decision from context outside this Task's minimal reading, this recommendation should be treated as overridable, not authoritative.

Proposed package layout under a new top-level `src/nyron_kernel/`:

```
src/nyron_kernel/
├── store/
│   └── sqlite_store.py       # canonical StateStore adapter; single connection;
│                              # explicit BEGIN/COMMIT boundaries for the two
│                              # canonical transactions in §10 and §12
├── definitions/
│   ├── registry.py           # ModuleDefinition register/resolve;
│   │                          # MODULE_VERSION_CONFLICT, MODULE_CONTRACT_INVALID,
│   │                          # PORT_SCHEMA_INVALID, UNKNOWN_EFFECT_CLASS,
│   │                          # UNKNOWN_CAPABILITY_TYPE, CAPABILITY_EFFECT_MISMATCH,
│   │                          # INVALID_SUSPENSION_CONTRACT
│   └── schema.py              # input/output/config schema validation primitives
├── graph/
│   └── revision.py           # immutable GraphRevision + ModuleInstanceRevision
│                              # storage; module_ref@version resolution;
│                              # UNRESOLVED_MODULE_REFERENCE
├── accounting/
│   └── scope_resolver.py     # Accounting-Owner-authoritative AccountingScope
│                              # resolution boundary implementing the FULL
│                              # Graph/Accounting Amendment 001 §4 mandatory
│                              # checklist (all 5 conditions — see §4/§7 below),
│                              # returning one authoritative resolve/deny result
│                              # that execution/admission.py MUST consume as-is.
│                              # Explicitly NOT BudgetReservation, NOT
│                              # estimate/actual settlement — those stay out of
│                              # scope for this slice (see §8).
├── execution/
│   ├── admission.py           # ExecutionAdmission (Runtime Orchestration
│   │                          # Candidate §4.2): the ONE gate, before any
│   │                          # WorkflowExecution exists, that validates
│   │                          # graph_revision_ref resolution/eligibility AND
│   │                          # calls accounting/scope_resolver.py for every
│   │                          # static_accounting_scope_ref in the admitted
│   │                          # topology per Amendment 001 §4 ("Before Runtime
│   │                          # admits a WorkflowExecution ... MUST validate").
│   │                          # Fail-closed denial creates no WorkflowExecution
│   │                          # and no partial execution that can later run.
│   ├── packet.py              # immutable Packet facts; every Packet carries
│   │                          # an execution_ref, so packet creation requires
│   │                          # admission.py to have already admitted the
│   │                          # WorkflowExecution
│   ├── delivery.py            # delivery_order_key, idempotent Packet->Delivery
│   │                          # projection, Delivery uniqueness constraint
│   ├── activation.py          # transactional Activation creation per §10.
│   │                          # Does NOT re-derive or re-check accounting
│   │                          # truth — that gate already ran once at
│   │                          # admission.py; Activation only pins the
│   │                          # already-validated static_accounting_scope_ref
│   ├── run.py                 # Run entity only: run_ref, activation_ref,
│   │                          # execution_ref, current_attempt_seq,
│   │                          # fencing_generation, state, terminal_attempt_seq
│   │                          # (Candidate §9.1). Exactly one Run per Activation.
│   └── attempt.py             # RunAttempt entity: (run_ref, attempt_seq),
│                              # fencing_token, state (CREATED/ACTIVE/SUCCEEDED/
│                              # FAILED/SUPERSEDED — the subset this PURE-only
│                              # slice needs; SUSPENDED/CANCELLED left as
│                              # unused-but-not-removed states per Candidate §9.2).
│                              # Hosts execute() ABI invocation, Completed/Failed
│                              # handling, the §12 canonical commit transaction
│                              # re-validating the full current-attempt fencing
│                              # tuple (execution_ref, activation_ref, run_ref,
│                              # attempt_seq, fencing_token — Candidate §19), and
│                              # the CREATED-not-dispatched-yet vs
│                              # ACTIVE-crossed-boundary crash-recovery split
│                              # (Candidate §10.4, §17.3).
├── host/
│   └── trusted_host.py        # in-process TRUSTED MODULE MODE host (§29);
│                              # exposes only execute(inputs, config, runtime_context)
└── modules/
    └── builtin_text_concat.py # the one seeded PURE ModuleDefinition + implementation

tests/
└── kernel/                    # acceptance tests, mapped 1:1 to §6 below
```

`docs/development/` (this document) is the only documentation artifact this Task adds; no other repository restructuring is proposed.

## 4. Required Interfaces / Contracts / Invariants Per Unit

| Unit | Must satisfy |
|---|---|
| `definitions/registry.py` | M-INV-14 (immutable `ModuleDefinition@version`), M-INV-16 (resolves to exactly one registered definition), §16/§30 registration validation order and rejection codes |
| `graph/revision.py` | M-INV-03 (Activation pins immutable definitions), §5 `UNRESOLVED_MODULE_REFERENCE`, §4 immutable `GraphRevision` publish-once semantics |
| `accounting/scope_resolver.py` | GA-INV-01, GA-INV-02, GA-INV-03, and all five mandatory conditions of `Graph_Accounting_Amendment_001` §4 (reference resolves to exactly one canonical `AccountingScope`; scope valid for the pinned definition anchor/GraphRevision affiliation; complete Accounting-owned parent ancestry resolvable and structurally valid; no missing/ambiguous parent reference or ownership mismatch; ancestry identity/hash consistency). Is the sole authoritative source of this result — Runtime consumes it, never re-derives it (Runtime Orchestration Candidate §20.4: "Runtime must not ... settle BudgetReservation itself" / owns admission only). |
| `execution/admission.py` | Candidate §4.1/§4.2 `WorkflowExecution`/`ExecutionAdmission`; Amendment 001 §4 (validates every `static_accounting_scope_ref` in the admitted topology *before* WorkflowExecution exists, per the Amendment's exact "before Runtime admits a WorkflowExecution" gate — not deferred to per-Activation time); GA-INV-01, GA-INV-02; admission rejection creates no partial execution (Candidate §4.2 item 6) |
| `execution/delivery.py` | §9 deterministic `delivery_order_key`, Delivery uniqueness, idempotent replay-safe projection; RT-INV-03, RT-INV-04, RT-INV-05, RT-INV-06 |
| `execution/activation.py` | §10 atomic Activation-creation transaction (no partial consume, no double-bind of a consumptive Delivery); RT-INV-05, RT-INV-06, RT-INV-07; relies on `admission.py` having already validated the static accounting reference — does not re-derive it |
| `execution/run.py` | Runtime Orchestration Candidate §9.1: exactly one `Run` per Activation (RT-INV-08); owns `current_attempt_seq` and `fencing_generation` as the atomically-updated current-attempt pointer (§9.3, RT-INV-09) |
| `execution/attempt.py` | Candidate §9.2, §19: `RunAttempt` identified by `(run_ref, attempt_seq)`; full current-attempt fencing tuple (`execution_ref`, `activation_ref`, `run_ref`, `attempt_seq`, `fencing_token`) re-validated at canonical commit; M-INV-07, RT-INV-09, RT-INV-10, RT-INV-12, RT-INV-14 (stale Attempt cannot canonical-commit, create output Packets, or initiate new mediated effects); §12 canonical commit ordering (durable output → verify current-attempt tuple → Attempt/Run terminal commit → Output Packets → canonical events); Candidate §10.4/§17.3 safe-redispatch-vs-ambiguous-Attempt distinction |
| `host/trusted_host.py` | §11 `execute()` ABI contract exactly; §29 TRUSTED MODULE MODE boundary (v0.1 explicitly does not claim hostile-plugin sandboxing) |
| `modules/builtin_text_concat.py` | §28 PURE contract (no clock/random/env/filesystem/network/mutable-global access) |

## 5. Execution Order and Dependencies

Serial build order (each step's tests need the previous step's durable schema fixed):

1. `store/sqlite_store.py` — schema + transaction boundary primitives.
2. `definitions/registry.py` (+ `schema.py`) — nothing downstream can register/resolve without this.
3. `graph/revision.py` — depends on (2) for `module_ref@version` resolution.
4. `accounting/scope_resolver.py` — depends on (1) only for storage.
5. `execution/admission.py` — depends on (3) for GraphRevision execution-eligibility evidence and (4) for the accounting-scope gate; creates `WorkflowExecution`/`ExecutionAdmission` and validates every static accounting reference in the topology *before* the WorkflowExecution exists (Amendment 001 §4). This must land before step (6), because Packets carry an `execution_ref` that presupposes an admitted execution.
6. `execution/packet.py`, `execution/delivery.py` — depend on (5).
7. `execution/activation.py` — depends on (5) and (6); relies on admission's already-validated accounting reference rather than re-deriving it.
8. `host/trusted_host.py` + `modules/builtin_text_concat.py` — depends on (2)'s contract only; independent of (4)/(5)/(7).
9. `execution/run.py` — depends on (7); creates the one Run per Activation and the current-attempt pointer.
10. `execution/attempt.py` — depends on (8) and (9); this is where the `execute()` ABI call, §12 canonical commit and the full current-attempt fencing tuple validation land.
11. End-to-end acceptance tests (§6) — last, after all of the above.

## 6. Tests Required Before the Slice Can Be Accepted

Restricted to the Phase 1–2-applicable subset of the frozen §42/§43 checklists (Capability/Resource/Suspension items are out of scope and excluded, not silently skipped):

**Registry (§42 subset):**
- Duplicate `module_ref@version` with different contract → rejected (`MODULE_VERSION_CONFLICT`).
- Invalid input/output/config schema → rejected (`PORT_SCHEMA_INVALID` / `MODULE_CONTRACT_INVALID`).
- Unknown effect/capability declared → rejected (`UNKNOWN_EFFECT_CLASS` / `UNKNOWN_CAPABILITY_TYPE`).
- A module declaring `PURE` with a non-empty `required_capability_types` → rejected.
- A `GraphRevision` referencing an unregistered `module_ref@version` → stored as non-executable, `UNRESOLVED_MODULE_REFERENCE`, never admitted.

**Runtime (§43 subset):**
- Run belongs to an existing immutable Activation; Activation's pinned `GraphRevision`/`ModuleInstanceRevision`/`ModuleDefinition` all resolve.
- Execution does not read a mutated "current" graph/config after Activation creation (test: mutate the pointer post-Activation, assert no behavior change).
- Input bindings delivered to `execute()` match exactly what Activation recorded.
- Output schema is validated and durable output confirmed to exist before the canonical transaction commits.

**Run / RunAttempt / fencing / crash-recovery (F-001 — Runtime Orchestration Candidate §9, §10, §17, §19):**
- Exactly one `Run` is created per Activation; a second Activation-creation attempt for the same bindings does not create a second Run (RT-INV-08).
- `Run.current_attempt_seq` and `Run.fencing_generation` are updated atomically together; no state where one advances without the other.
- Canonical commit at Attempt terminal time re-validates the full fencing tuple (`execution_ref`, `activation_ref`, `run_ref`, `attempt_seq`, `fencing_token`) against current Runtime truth, not `attempt_seq` alone.
- A second, injected stale/superseded Attempt for the same Run must be rejected at canonical commit (`ATTEMPT_NOT_CURRENT` / `STALE_ATTEMPT_REJECTED`) and must not produce an Output Packet or Run-terminal truth.
- Attempt terminal state (`SUCCEEDED`/`FAILED`/`SUPERSEDED`) and Run terminal state are asserted as distinct facts: a `SUPERSEDED` Attempt does not itself force the Run to a terminal state, and a successful Attempt's `SUCCEEDED` commit is what drives Run-terminal commit — the two are not collapsed into one flag.
- Simulated replacement (old Attempt superseded while still `ACTIVE`) immediately removes the old Attempt's canonical-commit authority at the replacement commit boundary, independent of whether the old Attempt's in-process work has actually stopped (RT-INV-12).
- Crash-recovery redispatch split: an Attempt left `CREATED` with proof it never reached the Module execution boundary may be safely redispatched as the same Attempt (no new `attempt_seq`); an Attempt left `ACTIVE` with no terminal outcome is never silently redispatched or guessed complete — it must go through explicit retry/replacement Runtime policy, not implicit re-execution (Candidate §10.4, §17.3, RT-INV-21).
- Late/duplicate `Completed` from a stale or superseded Attempt is rejected and creates no Packet (Candidate §17.4).

**Accounting admission (F-002 — Graph/Accounting Amendment 001 §4, all five mandatory conditions):**
- Reference-resolution: admission denied with `UNRESOLVED_ACCOUNTING_SCOPE_REFERENCE` when `static_accounting_scope_ref` does not resolve to exactly one canonical `AccountingScope`.
- Binding validity: admission denied with `ACCOUNTING_SCOPE_BINDING_INVALID` when the resolved scope is not valid for the pinned definition anchor / GraphRevision affiliation.
- Ancestry completeness: admission denied with `ACCOUNTING_SCOPE_ANCESTRY_INVALID` when the required Accounting-owned parent ancestry chain is missing or incomplete.
- Ancestry integrity: admission denied when a parent reference is ambiguous or an ownership mismatch exists in the ancestry chain.
- Ancestry identity consistency: admission denied when a canonical ancestry identity/hash the Accounting contract relies on is inconsistent with the resolved ancestry.
- Admission proceeds only when the Accounting-Owner resolver positively confirms all five conditions (never "absence/silence of scope info ⇒ allow" — GA-INV-02).
- `execution/admission.py` is tested to consume the resolver's result as-is (mock the resolver returning `DENY`; assert `ExecutionAdmission` refuses to create a `WorkflowExecution` regardless of any locally-cached or previously-seen scope state, and that no Packet/Delivery/Activation can subsequently be created for that denied admission) — proving Runtime does not fabricate or independently re-derive Accounting truth.

**Atomicity / idempotency / determinism (F-003):**
- Transactional Activation rollback: inject a failure between steps of the §10 Activation-creation transaction (e.g. after consumptive-Delivery binding, before Activation record write) and assert the entire transaction rolls back — no bound-but-orphaned Delivery, no partially created Activation.
- Consumptive Delivery double-binding prevention: two concurrent Activation-creation attempts racing on the same `TRIGGER`/`REQUIRED_NEXT` Delivery — assert exactly one succeeds and the Delivery is bound to exactly one `activation_ref` (RT-INV-06).
- Delivery uniqueness: replaying the same Packet->Edge projection twice does not create a second Delivery for the same `(packet_ref, graph_revision_ref, edge_ref, target_port_ref)` key.
- Interrupted fan-out / projection replay idempotency: inject a crash mid-fan-out across multiple Edges from one Packet; on replay, assert existing Deliveries are not duplicated and missing Deliveries are created (Candidate §17.1).
- Output/Attempt/Run atomic-commit crash windows: inject a crash (a) before the §12 canonical transaction opens (assert orphan durable output value but no Output Packet, no Attempt/Run terminal commit), (b) **inside** the canonical transaction, after the Attempt-terminal-state write and the Run-terminal-state write have occurred but before Output Packet creation and canonical event creation complete (see the dedicated in-transaction test below), and (c) after the canonical transaction commits but before Delivery projection runs (assert projection replay repairs it without duplicating the Output Packet) (Candidate §17.4).
- **In-transaction all-or-nothing fault injection (closes `NYRON-T-20260825-004-F-003`):** this test exists specifically to prove that Attempt-terminal-state write, Run-terminal-state write, Output Packet creation, and canonical event creation are one single atomic transaction — not four separately-committing steps that merely happen to run in sequence.
  1. Begin the §12 canonical commit transaction (current-attempt fencing tuple already re-verified per §7).
  2. Execute the in-transaction Attempt-terminal-state write (e.g. `RunAttempt.state -> SUCCEEDED`).
  3. Execute the in-transaction Run-terminal-state write (e.g. `Run.terminal_attempt_seq` set).
  4. Inject failure at this exact point — after step 2 and step 3 have executed within the open transaction, but strictly before Output Packet creation and canonical event append complete.
  5. Assert the transaction rolls back as a whole (single `ROLLBACK`, not partial undo of only some writes).
  6. Post-rollback assertions, all against durable state (not in-memory/pre-rollback views): the Attempt's persisted state is unchanged from its pre-transaction value (**no** partial/leaked `SUCCEEDED`/terminal write survives the rollback); the Run's persisted state is likewise unchanged (**no** partial/leaked terminal write survives); no Output Packet exists for this Attempt; no canonical event for this failed transaction exists in the durable event log.
  7. Drive a subsequent retry/recovery pass over the same (now again non-terminal, per step 6) Attempt and assert it completes exactly one canonical commit transaction successfully — Attempt terminal state, Run terminal state, Output Packet, and canonical event all become durable together in that one successful transaction.
  8. Assert no duplication versus the failed attempt: exactly one terminal `RunAttempt` state, exactly one Run-terminal association, exactly one Output Packet, exactly one canonical event for the Activation — the rolled-back transaction from steps 1–5 left no residue for the retry to collide with or duplicate.
  This directly targets the Runtime Orchestration Candidate §17.4 sequence ("verify current Attempt → commit Attempt/Run success → create output Packet manifests → append canonical events" inside one `BEGIN...COMMIT` boundary) and RT-INV-14 (stale/failed transactions cannot leave partial canonical truth); crash windows (a) and (c) above test the boundary *around* this transaction, while this test proves the boundary *inside* it is all-or-nothing.
- Duplicate/late `Completed`: a Module returning `Completed` twice for the same Attempt, and a `Completed` arriving after the Attempt has already been superseded, both produce no additional Output Packet and no error state inconsistency.
- Replay/determinism against the **same committed durable history**: given one fixed sequence of already-committed canonical facts, replaying `delivery_order_key` derivation and next-Activation selection under two different in-process replay/projector orderings yields the identical result every time. This test does not assert determinism *across different concurrent histories* — which commit wins a genuine race is historical fact, not something replay must reproduce differently (Candidate §18.1) — only that replaying one fixed history is deterministic.
- Process restart between the §10 transaction commit and the §12 transaction commit recomputes the same next pending work from durable state alone (§39 Committed-History Determinism); no reliance on in-memory state that a crash would destroy.

## 7. Replay / Fencing / Authority / Accounting / Recovery Checks Applicable to This Slice

- **Run / Attempt model (in scope):** exactly one stable `Run` per Activation with one or more `RunAttempt` records under it (Runtime Orchestration Candidate §9.1/§9.2); `Run` and `RunAttempt` are separate persisted entities, not a merged concept, so that Attempt terminal state (`SUCCEEDED`/`FAILED`/`SUPERSEDED`) and Run terminal state remain distinguishable facts as the frozen contract requires.
- **Commit Fencing (in scope):** the §12 canonical-commit path must re-verify the *full* current-attempt fencing tuple — `execution_ref`, `activation_ref`, `run_ref`, `attempt_seq`, `fencing_token` (Candidate §19) — before commit, not `attempt_seq` alone, and this must be tested with an injected stale-Attempt scenario. This is not left as "nothing to fence yet" reasoning: M-INV-07 and RT-INV-09/RT-INV-14 are Run-level invariants independent of whether any Effect exists.
- **Crash recovery (in scope, corrected):** recovery of a recovered current Attempt must distinguish (a) `CREATED` with proof the Module execution boundary was never crossed — safely redispatchable as the *same* Attempt, no new `attempt_seq` — from (b) `ACTIVE` with no terminal outcome, which is never guessed successful/failed and never silently re-executed; it is handled only through explicit Runtime retry/replacement policy applied to a genuinely new Attempt (Candidate §10.4, §17.3). Retry/replacement *policy execution* itself (choosing to retry, backoff, replacement eligibility) stays deferred per §8, but the crash-recovery classification above — which distinguishes safe redispatch from ambiguous crossed-boundary work — is not deferrable; without it the slice cannot claim RT-INV-21 (unknown past remains unknown).
- **Accounting (in scope, gating admission — not Activation creation):** all five mandatory conditions of `Graph_Accounting_Amendment_001` §4 — reference resolution, definition-anchor/GraphRevision binding validity, ancestry completeness/structural validity, absence of missing/ambiguous parent references or ownership mismatch, and ancestry identity/hash consistency. Per the Amendment's own wording ("Before Runtime admits a WorkflowExecution ... MUST validate"), this gate belongs at `execution/admission.py` (`ExecutionAdmission`, Candidate §4.2), *before* any `WorkflowExecution`/Packet/Delivery/Activation exists — not deferred to per-Activation time. `execution/admission.py` **consumes** the Accounting Owner's authoritative resolve/deny result from `accounting/scope_resolver.py`; it never independently re-derives, caches-and-trusts-stale, or partially re-implements that validation, and `execution/activation.py` does not re-check it either. Full hierarchical `BudgetReservation`, estimate-vs-actual settlement, and Accounting/Recovery Owner separation beyond the resolution check are explicitly **out of scope** — the resolver must still fail closed (GA-INV-02) on any of the five conditions so it cannot later be mistaken for a completed Accounting implementation.
- **Authority / Capability / Resource / Effect (out of scope):** no `CapabilityGrant`, `Resource`/`ResourceLease`, or `EffectOperation` exists in this slice because the only seeded Module is `PURE`.
- **Recovery (out of scope):** no `ReconciliationCase` machinery; nothing in this slice can produce an `UNKNOWN` external fact since there is no external effect. The CREATED-vs-ACTIVE crash-recovery classification above is a Runtime-local fencing fact, not a `ReconciliationCase` — it does not require Recovery machinery to exist.
- **Replay (in scope):** §39 Committed-History Determinism and Candidate §18.1 (deterministic replay of one fixed committed history, not cross-history determinism) must hold for the Packet/Delivery/Activation/Run/RunAttempt facts this slice already creates.

## 8. Explicit Out of Scope for the First Slice

- Runtime retry/replacement *policy* execution (choosing whether/when to retry, backoff, replacement eligibility, `runtime_policy_ref` schema) — Candidate §10.1/§10.2/§11. **Not deferred:** the crash-recovery classification that distinguishes safe `CREATED`-redispatch from ambiguous `ACTIVE`-crossed-boundary Attempts (§7 above) — that classification is required now even though no policy engine decides what to do next with an ambiguous Attempt.
- CapabilityGrant issuance/validation and any mediated effect (Phase 3).
- Resource / ResourceLease (Phase 4).
- Suspension / Continuation / Subscription / Event / `resume()` (Phase 5).
- EffectOperation, Effect Fencing, revoke/kill/confirm lifecycle (Phase 6).
- ReconciliationCase / Recovery escalation (Phase 7).
- Full hierarchical `BudgetReservation` and estimate/actual settlement (only static-scope resolution is in scope).
- Multi-module, branching, or nested Composite graphs (single `ModuleInstanceRevision` only).
- Human Interaction/Approval, External Interfaces/ingress, Distribution/Module Ecosystem, Project/Workspace/Policy Context.
- Any product/UI-facing Node concepts (frozen invariant M-INV-15).
- Changing any Frozen Architecture / Contract / Amendment / Baseline (per this Task's own Out of Scope).

## 9. Parallelism

**Must remain serial** (shared SQLite schema / canonical transaction boundaries — concurrent authors would conflict): `store/` → `definitions/registry.py` → `graph/revision.py` → `execution/{admission,packet,delivery,activation,run,attempt}.py`.

**Safe to run in parallel** once (1) the store schema and (2) the registry's public contract (function signatures + error codes) are fixed:
- `host/trusted_host.py` + `modules/builtin_text_concat.py` (Module Host and the one builtin Module) — touches its own files only, depends only on the already-fixed registry contract.
- `accounting/scope_resolver.py` — touches disjoint tables/files, depends only on the store schema, has no dependency on the Module Host track.

These two tracks share no mutable state and do not need to coordinate with each other; both are wired into the execution pipeline only at integration time — the accounting resolver into `execution/admission.py` (step 5 in §5), the Module Host into `execution/attempt.py` via `execute()` (step 10 in §5).

Tests for a given layer may be written in parallel with that layer's implementation once its public contract is fixed, but must land alongside (not ahead of, as a separate unreviewed claim) the implementation they assert against, per Task-scoped-diff discipline.

## 10. Complexity Justification

| Structure | Why it is required, not speculative |
|---|---|
| Separate `store/sqlite_store.py` seam instead of ad hoc `sqlite3` calls scattered across modules | The frozen baseline itself requires that raw StateStore/SQLite never be exposed to Module code (§17, §29) and that all canonical commits happen inside defined transaction boundaries (§10, §12). Some mediating seam is unavoidable; this plan does not add a driver-agnostic/multi-backend abstraction on top of it — there is no current second backend requirement, so it stays a single concrete adapter. |
| Separate `accounting/scope_resolver.py` unit instead of inlining the check into `execution/activation.py` | Accounting Owner is a frozen separate canonical Owner from Runtime (Accounting/Recovery Frozen Baseline "Accounting Owner / Recovery Owner separation"; Amendment 001 §2 "Runtime owns: execution admission" vs "Accounting Owner owns: AccountingScope identity, ancestry..."). Inlining would blur an ownership boundary the frozen baseline requires to stay distinct — this is required structural complexity, not premature abstraction. |
| Separate `execution/run.py` (`Run`) and `execution/attempt.py` (`RunAttempt`) instead of one merged `run.py` | Directly required by Runtime Orchestration Candidate §9.1/§9.2 and RT-INV-08/09/10/12/14: `Run` and `RunAttempt` are distinct frozen canonical facts with distinct identity (`run_ref` vs `(run_ref, attempt_seq)`) and distinct terminal-state semantics that Review `NYRON-T-20260825-004` (F-001) found the merged version obscured. This is a correction to match an existing frozen distinction, not new speculative structure. |
| Separate `execution/admission.py` step before `execution/activation.py`, instead of checking accounting inside Activation creation | Directly required by Amendment 001 §4's exact wording ("Before Runtime admits a WorkflowExecution ... MUST validate") and Runtime Orchestration Candidate §4.2 `ExecutionAdmission`: the gate is defined at WorkflowExecution admission, which precedes Packet/Delivery/Activation entirely, not at per-Activation time. Checking it later would both misplace the gate relative to the frozen sequence and mean it re-runs redundantly per Activation instead of once per execution. This is a correction to match the frozen admission boundary, not new speculative structure. |
| No Factory/Strategy/plugin registry for Module execution | Explicitly rejected by the frozen baseline itself (§2: no `ModuleType` enum, no three-Executor split) and by `skills/implementation/SKILL.md`. A single `execute()` ABI call per registered `ModuleDefinition` is sufficient for one PURE module. |
| No generic Capability/Effect provider abstraction | Correctly deferred: this slice seeds zero effectful Modules, so there is no current second use case to justify any such layer (`skills/implementation/SKILL.md` §3.1/§3.3). |

## Validation Self-Check (against Task `NYRON-T-20260825-003` §Validation and Task `NYRON-T-20260825-005` §Validation)

- Every proposed responsibility above maps to a frozen requirement (§4 table) or this Task's own scope — no unmapped responsibility introduced.
- No proposed module claims authority owned by another frozen Owner: `accounting/scope_resolver.py` only *resolves/validates* a reference, it does not perform reservation/settlement (Accounting Owner's actual authority); `execution/run.py`/`execution/attempt.py` perform no Capability/Effect logic.
- No second execution path is introduced; everything routes through `Packet -> Delivery -> Activation -> Run/RunAttempt`.
- The first slice has an executable test strategy (§6), not prose-only acceptance.
- No speculative abstraction is proposed merely for future flexibility (§10 justifies each non-trivial structure, including the Run/RunAttempt split, against a current frozen requirement).
- Parallelism (§9) is scoped to disjoint files/tables with no shared mutable workspace conflict.
- All four `NYRON-T-20260825-004` findings are addressed: Run/Attempt/fencing/crash semantics now match the frozen Runtime Orchestration Candidate exactly (F-001); Accounting admission covers all five Amendment 001 §4 conditions and Runtime only consumes the Accounting Owner's result (F-002); atomicity/idempotency/crash-window/determinism tests are explicit in §6 (F-003); the SQLite recommendation no longer claims frozen authority (F-004).
- No Frozen Architecture / Contract / Amendment / Baseline file was modified to produce this correction; only this planning document changed.

## Findings

None. The frozen baseline set read for this Task and its correction (Overall Architecture, Module Design Report, Runtime Orchestration frozen manifest + Design Candidate, Accounting/Recovery, Capability/Resource/Effect Authority freeze manifests, Graph/Accounting Amendment 001) is internally consistent and sufficient to plan and correct this first slice without inventing architecture semantics. The only non-architectural gap found remains the absence of a prior language/runtime decision in the repository; this plan makes a minimally-justified, explicitly overridable recommendation (§3) rather than treating it as a blocking Finding, since Implementation Planning Tasks are expected to propose concrete package boundaries.
