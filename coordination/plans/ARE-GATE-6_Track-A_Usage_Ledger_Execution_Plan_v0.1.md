# ARE-GATE-6 Track A — Usage / Ledger Execution Plan v0.1

Status: `ACTIVE TRACK-LOCAL ORCHESTRATION PLAN / NOT ARCHITECTURE`
Owner: `GPT — Nyron Track-A Development Orchestrator`
Date: `2026-08-26`
Coordination Basis: `Epoch 2 / Revision 88`
Accepted Production Basis: `84156a5be8d77dc69fd21b02ffa2cf49f5154a8b`
Global Plan: `coordination/plans/ARE-GATE-6_Parallel_Development_Plan_v0.1.md`

## Scope

This plan governs only Parallel Track A — Usage / Ledger:

- `UsageFact`
- `UsageAdjustmentFact`
- actual usage canonical truth
- stable source dedupe
- duplicate callback idempotency
- conflicting source fact handling
- append-only late correction / refund semantics
- usage ingestion crash / replay
- Track-A-local review, re-review and stable-candidate handoff

It does not authorize BudgetReservation settlement, Recovery Owner / ReconciliationCase implementation, Runtime / Effect / Resource canonical mutation, or global Accounting <-> Recovery integration.

## Operating Rules

- Repository truth overrides chat and this plan.
- Do not modify `coordination/STATUS.md` without explicit global Coordination Write Authority.
- Production Content Commit and Result Commit identities must remain distinct.
- Every implementation/review task must be anchored to an exact production SHA.
- Do not pre-allocate future global Task IDs. Before creating each follow-up Task, inspect repository truth and choose a currently unused Task ID so Track B cannot collide with Track A.
- Preserve the project-wide parallelism cap. A completed Track-A task releases its slot before a Track-A follow-up review/fix task is started unless the global operator explicitly increases capacity.
- Cross-track dependency or overlapping write-surface discovery => `WAITING / BLOCKED` or `ESCALATION_REQUIRED`; never silently implement Track B responsibilities.
- Frozen contract insufficiency => STOP and raise Architecture / Contract Finding. Track A does not reinterpret frozen design.

## Agent Allocation Policy

Default Track-A routing hierarchy:

- `Claude Code` — primary development Agent for core implementation, difficult fixes, contract-sensitive implementation, and other high-value production work.
- `Codex` — primary development Agent and independent high-risk reviewer; may own core implementation, difficult fixes, targeted refactors, exact-SHA semantic review, or cross-checks where independence from Claude is useful.
- `DeepSeek` — auxiliary Agent for simple/mechanical work only by default: bounded mechanical audit, changed-file/scope verification, documentation consistency checks, deterministic validation, repetitive checks, straightforward test-gap identification, and other low-risk tasks with explicit boundaries.

Claude Code and Codex are the principal development capacity. DeepSeek should not be the default owner for architecture-sensitive core implementation or final high-risk semantic acceptance review unless the Orchestrator explicitly overrides this policy for a bounded reason.

Multiple concurrent sessions of Claude Code or Codex are allowed when their write surfaces and dependencies are independent and the active-slot policy permits it. DeepSeek tasks should preferentially remain read-only or mechanically bounded so they can assist the main development line without becoming an implicit architecture authority.

## Agent Session Naming Rule

Every newly opened Agent conversation must begin by self-declaring a unique session name before execution.

Required format:

`NYRON-TA-<TASKID>-<ROLE>-<AGENT>-<N>`

Examples:

- `NYRON-TA-090-IMPL-CLAUDE-1`
- `NYRON-TA-<TASKID>-MECH-DEEPSEEK-1`
- `NYRON-TA-<TASKID>-REVIEW-CODEX-1`

Multiple concurrent sessions of the same Agent family are allowed only when write surfaces and dependencies are independent and the active-slot policy permits it. Session identity is not a substitute for formal Task ID or exact production SHA.

## Planned Route

### A0 — Foundation implementation

Formal Task: `NYRON-T-20260826-090`
Assigned Agent: `Claude Code`
State at plan creation: `READY / START NEXT`
Risk: `HIGH`

Deliverable:

- exact production content SHA;
- `coordination/results/NYRON-T-20260826-090.md`;
- required tests and scope evidence.

No acceptance is inferred from executor success.

### A1 — Bounded mechanical audit

Trigger: Task 090 Result exists and exact production SHA is verified.
Preferred Agent: `DeepSeek`
Mode: read-only audit; no production edits.

Audit targets:

- exact changed-file scope against Task 090 authorization;
- no forbidden Recovery / Settlement / Runtime / Effect / Resource edits;
- schema uniqueness / dedupe constraints;
- UsageFact / UsageAdjustmentFact append-only and immutability enforcement;
- duplicate and conflicting identity test coverage;
- UNKNOWN != zero coverage;
- crash/retry idempotency coverage;
- complete `tests/kernel` result evidence;
- `git diff --check` evidence;
- production SHA versus later Result commit separation.

Outcome:

- `PASS` => route to A2;
- finding => classify as IMPLEMENTATION / TEST / CONTRACT / ARCHITECTURE and route accordingly.

### A2 — Independent high-risk semantic review

Trigger: A1 clean or its findings dispositioned.
Preferred Agent: `Codex`, independent from Task 090 implementation.
Mode: exact-SHA review; no production edits.

Reviewer must verify frozen Usage/Ledger semantics, especially:

- exact semantic duplicate returns the existing canonical fact;
- same source dedupe identity plus changed semantic payload fails closed and preserves existing truth;
- legitimate distinct provider line items remain independently recordable;
- adjustment/refund is append-only;
- duplicate adjustment is idempotent;
- no latest-by-time overwrite semantics;
- no implicit Recovery case creation;
- no settlement side effects;
- retry/replay cannot double count.

Outcome:

- `PASS / FINDINGS NONE` => route to A4;
- blocking implementation/test finding => A3 fix;
- contract/architecture finding => STOP / ESCALATE.

### A3 — Fix and Re-Review loop, only if required

Preferred implementation Agent: reuse the original Claude Code implementation session when context remains valid; otherwise open another uniquely named Claude session. Codex may instead own a fix when independence, workload balancing, or task characteristics make it the better primary developer.

Rules:

- fix must be a new formal Task based on the reviewed exact production SHA;
- no scope expansion;
- produce new exact production SHA and separate Result commit;
- reviewer re-reviews the new exact SHA;
- repeat until `PASS` or escalation.

### A4 — Track A stable-candidate handoff

Trigger: exact-SHA independent review is `PASS` with no unresolved blocking finding.

Produce a Track-A-local handoff/checkpoint identifying:

- final reviewed exact production SHA;
- review Result(s);
- unresolved non-blocking debt, if any;
- exported stable Usage/Ledger interfaces available to later Settlement / final integration;
- explicit statement that Track A does not itself accept global production and does not modify global `STATUS.md` without authority.

Track A then becomes `COMPLETED / STABLE CANDIDATE READY FOR GLOBAL INTEGRATION`.

## User Interaction Contract

The operator only needs to report which Agent/session finished.

On each such report, Track-A Orchestrator will:

1. read repository Result and latest repository truth;
2. verify exact production SHA and task freshness;
3. classify findings/blockers;
4. create the next formal Task when required;
5. give the operator only the next Agent-opening instruction, if a new session is needed;
6. report Track A progress using the fixed sections below.

## Mandatory Progress Report Format

Every Track-A Orchestrator response must include:

- `Active / Running`
- `Waiting`
- `Completed`
- `Findings / Blockers`
- `Next Route`

This progress report is chat status only; formal delivery remains repository-file based.
