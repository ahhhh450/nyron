# Nyron System Foundation — First Implementation Slice Plan v0.1

**Task:** `NYRON-T-20260825-003`
**Type:** Implementation Planning (this document proposes no runtime code and changes no frozen semantics)
**Coordination basis:** Epoch `1` / Revision `4`
**Authoritative sources this plan traces to:**
- `design/Nyron_Overall_System_Architecture_Frozen_Baseline_v0.1.md`
- `design/Universal_Runtime_Module_Design_Report_v0.1.md`
- `design/Nyron_Runtime_Orchestration_Frozen_Baseline_v0.1.md`
- `design/Nyron_Accounting_Recovery_Frozen_Baseline_v0.1.md`
- `design/amendments/Graph_Accounting_Amendment_001_Static_Accounting_Scope_Resolution.md`
- `design/Nyron_Capability_Resource_Effect_Authority_Frozen_Baseline_v0.1.md` (boundary only; not exercised by this slice)

This plan does not reinterpret, extend, or narrow any frozen semantic. Where it makes an implementation-tooling choice not fixed by the frozen baselines (language/runtime, file layout), that choice is marked explicitly and is not itself a Frozen Architecture decision.

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

Python 3.11+, stdlib `sqlite3` as the canonical StateStore backing. Justification: the Module baseline itself names "raw StateStore/SQLite" (§17, §29) as the thing a Module implementation must not be handed directly — this presupposes SQLite as the canonical store the Kernel mediates, so choosing SQLite is reading an existing signal, not inventing one. Python is chosen only for fast, dependency-light transactional/state-machine code for a first slice; nothing in this plan blocks a future Module Host boundary (§29) from hosting non-Python Modules later — that boundary is already frozen as a protocol boundary, not a language commitment. If the Orchestrator already has a different language decision from context outside this Task's minimal reading, this recommendation should be treated as overridable, not authoritative.

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
│   └── scope_resolver.py     # MINIMAL AccountingScope resolution stub satisfying
│                              # GA-INV-01/02 only (existence + structural ancestry
│                              # validity check). Explicitly NOT BudgetReservation,
│                              # NOT estimate/actual settlement — those stay out of
│                              # scope for this slice (see §8).
├── execution/
│   ├── packet.py              # immutable Packet facts
│   ├── delivery.py            # delivery_order_key, idempotent Packet->Delivery
│   │                          # projection, Delivery uniqueness constraint
│   ├── activation.py          # transactional Activation creation per §10
│   └── run.py                 # Run/Attempt, execute() ABI invocation,
│                              # Completed/Failed handling, canonical commit
│                              # transaction per §12, current-attempt fencing check
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
| `accounting/scope_resolver.py` | GA-INV-01, GA-INV-02 (fail closed; unresolved never means unlimited/no budget) |
| `execution/delivery.py` | §9 deterministic `delivery_order_key`, Delivery uniqueness, idempotent replay-safe projection |
| `execution/activation.py` | §10 atomic Activation-creation transaction (no partial consume, no double-bind of a consumptive Delivery) |
| `execution/run.py` | M-INV-01, M-INV-02, M-INV-07 (stale Attempt cannot canonical-commit), §12 canonical commit ordering (durable output → verify attempt → Run SUCCESS → Output Packets → canonical events) |
| `host/trusted_host.py` | §11 `execute()` ABI contract exactly; §29 TRUSTED MODULE MODE boundary (v0.1 explicitly does not claim hostile-plugin sandboxing) |
| `modules/builtin_text_concat.py` | §28 PURE contract (no clock/random/env/filesystem/network/mutable-global access) |

## 5. Execution Order and Dependencies

Serial build order (each step's tests need the previous step's durable schema fixed):

1. `store/sqlite_store.py` — schema + transaction boundary primitives.
2. `definitions/registry.py` (+ `schema.py`) — nothing downstream can register/resolve without this.
3. `graph/revision.py` — depends on (2) for `module_ref@version` resolution.
4. `execution/packet.py`, `execution/delivery.py` — depend on (1) only; independent of (3) in code, but tests need a published `GraphRevision` from (3) to be meaningful.
5. `execution/activation.py` — depends on (3) and (4).
6. `host/trusted_host.py` + `modules/builtin_text_concat.py` — depends on (2)'s contract only.
7. `execution/run.py` — depends on (5) and (6); this is where §12 canonical commit and current-attempt fencing land.
8. `accounting/scope_resolver.py` — depends on (1) only for storage, but must be wired into the admission path *before* step (5)/(7) are considered "done" per GA-INV-01 (admission gate precedes Activation, not just Run commit).
9. End-to-end acceptance tests (§6) — last, after all of the above.

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
- Run is the current Attempt at canonical-commit time; a second, injected stale Attempt for the same Activation must be rejected at commit and must not produce an Output Packet.
- Output schema is validated and durable output confirmed to exist before the canonical transaction commits.

**Accounting gate:**
- Admission denied with `UNRESOLVED_ACCOUNTING_SCOPE_REFERENCE` / `ACCOUNTING_SCOPE_ANCESTRY_INVALID` when the scope is unresolved, ambiguous, or has broken ancestry.
- Admission proceeds only when the scope resolver positively confirms resolution (never "absence of scope info ⇒ allow").

**Determinism / replay:**
- `delivery_order_key` ordering is a pure function of committed facts (assert two different projector-worker interleavings yield the same order).
- Process restart between the §10 transaction commit and the §12 transaction commit must recompute the same next pending work from durable state alone (§39); no reliance on in-memory state that crash would destroy.

## 7. Replay / Fencing / Authority / Accounting / Recovery Checks Applicable to This Slice

- **Fencing (in scope):** the §12 canonical-commit path must re-verify current Attempt before commit, and this must be tested with an injected stale-Attempt scenario — not left as "nothing to fence yet" reasoning, because M-INV-07 is a Run-level invariant independent of whether any Effect exists.
- **Accounting (partially in scope):** only static `AccountingScope` reference resolution (GA-INV-01/02) at admission. Full hierarchical `BudgetReservation`, estimate-vs-actual settlement, and Accounting/Recovery Owner separation beyond the resolution check are explicitly **out of scope** — the resolver stub must still fail closed (GA-INV-02) so it cannot later be mistaken for a completed Accounting implementation.
- **Authority / Capability / Resource / Effect (out of scope):** no `CapabilityGrant`, `Resource`/`ResourceLease`, or `EffectOperation` exists in this slice because the only seeded Module is `PURE`.
- **Recovery (out of scope):** no `ReconciliationCase` machinery; nothing in this slice can produce an `UNKNOWN` external fact since there is no external effect.
- **Replay (in scope):** §39 Committed-History Determinism must hold for the Packet/Delivery/Activation/Run facts this slice already creates.

## 8. Explicit Out of Scope for the First Slice

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

**Must remain serial** (shared SQLite schema / canonical transaction boundaries — concurrent authors would conflict): `store/` → `definitions/registry.py` → `graph/revision.py` → `execution/{packet,delivery,activation,run}.py`.

**Safe to run in parallel** once (1) the store schema and (2) the registry's public contract (function signatures + error codes) are fixed:
- `host/trusted_host.py` + `modules/builtin_text_concat.py` (Module Host and the one builtin Module) — touches its own files only, depends only on the already-fixed registry contract.
- `accounting/scope_resolver.py` — touches disjoint tables/files, depends only on the store schema, has no dependency on the Module Host track.

These two tracks share no mutable state and do not need to coordinate with each other; both are wired into `execution/activation.py`/`run.py` only at integration time (step 7–8 in §5).

Tests for a given layer may be written in parallel with that layer's implementation once its public contract is fixed, but must land alongside (not ahead of, as a separate unreviewed claim) the implementation they assert against, per Task-scoped-diff discipline.

## 10. Complexity Justification

| Structure | Why it is required, not speculative |
|---|---|
| Separate `store/sqlite_store.py` seam instead of ad hoc `sqlite3` calls scattered across modules | The frozen baseline itself requires that raw StateStore/SQLite never be exposed to Module code (§17, §29) and that all canonical commits happen inside defined transaction boundaries (§10, §12). Some mediating seam is unavoidable; this plan does not add a driver-agnostic/multi-backend abstraction on top of it — there is no current second backend requirement, so it stays a single concrete adapter. |
| Separate `accounting/scope_resolver.py` unit instead of inlining the check into `execution/activation.py` | Accounting Owner is a frozen separate canonical Owner from Runtime (Accounting/Recovery Frozen Baseline "Accounting Owner / Recovery Owner separation"; Amendment 001 §2 "Runtime owns: execution admission" vs "Accounting Owner owns: AccountingScope identity, ancestry..."). Inlining would blur an ownership boundary the frozen baseline requires to stay distinct — this is required structural complexity, not premature abstraction. |
| No Factory/Strategy/plugin registry for Module execution | Explicitly rejected by the frozen baseline itself (§2: no `ModuleType` enum, no three-Executor split) and by `skills/implementation/SKILL.md`. A single `execute()` ABI call per registered `ModuleDefinition` is sufficient for one PURE module. |
| No generic Capability/Effect provider abstraction | Correctly deferred: this slice seeds zero effectful Modules, so there is no current second use case to justify any such layer (`skills/implementation/SKILL.md` §3.1/§3.3). |

## Validation Self-Check (against Task `NYRON-T-20260825-003` §Validation)

- Every proposed responsibility above maps to a frozen requirement (§4 table) or this Task's own scope — no unmapped responsibility introduced.
- No proposed module claims authority owned by another frozen Owner: `accounting/scope_resolver.py` only *resolves/validates* a reference, it does not perform reservation/settlement (Accounting Owner's actual authority); `execution/run.py` performs no Capability/Effect logic.
- No second execution path is introduced; everything routes through `Packet -> Delivery -> Activation -> Run`.
- The first slice has an executable test strategy (§6), not prose-only acceptance.
- No speculative abstraction is proposed merely for future flexibility (§10 justifies each non-trivial structure against a current frozen requirement).
- Parallelism (§9) is scoped to disjoint files/tables with no shared mutable workspace conflict.

## Findings

None. The frozen baseline set read for this Task (Overall Architecture, Module Design Report, Runtime Orchestration, Accounting/Recovery, Capability/Resource/Effect Authority freeze manifests, Graph/Accounting Amendment 001) is internally consistent and sufficient to plan this first slice without inventing architecture semantics. The only non-architectural gap found is the absence of a prior language/runtime decision in the repository; this plan makes a minimally-justified recommendation (§3) rather than treating it as a blocking Finding, since Implementation Planning Tasks are expected to propose concrete package boundaries.
