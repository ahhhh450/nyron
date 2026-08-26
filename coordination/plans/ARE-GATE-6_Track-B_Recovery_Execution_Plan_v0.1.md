# ARE-GATE-6 Track B — Recovery / ReconciliationCase Execution Plan v0.1

Status: `ACTIVE TRACK PLAN / NOT ARCHITECTURE`
Owner: `Track B Development Orchestrator`
Date: `2026-08-26`
Coordination Basis: `Epoch 2 / Revision 88`
Accepted Production Basis: `84156a5be8d77dc69fd21b02ffa2cf49f5154a8b`
Parent Plan: `coordination/plans/ARE-GATE-6_Parallel_Development_Plan_v0.1.md`

## 1. Purpose

Provide the execution route for Parallel Track B only:

- `ReconciliationCase` foundation;
- stable/idempotent case opening;
- Recovery evidence;
- recovery attempt identity;
- bounded retry/backoff/deadline;
- escalation;
- `RESOLVED / ESCALATED` semantics;
- manual disposition as Recovery-owned truth;
- Track B review, correction and re-review checkpoints.

This plan is scheduling/coordination only. It does not amend the frozen Accounting / Recovery architecture.

## 2. Reset Decision

Task `NYRON-T-20260826-091` never started and was explicitly voided by the operator before implementation.

Rules:

- 091 is `VOID / SUPERSEDED / DO NOT EXECUTE`;
- no production or Result from a stale 091 session may be accepted;
- Track B restarts from the same accepted production basis under a new Task identity;
- restarting does not grant permission to modify Track A production or global coordination state.

## 3. Agent Session Identity Rule

Every execution or review Agent session used by Track B MUST declare its Session Name before doing substantive work.

Fixed Track B naming rule:

`TRACK_B_TASK_<TaskNumber>`

Examples:

- Task 092 primary session: `TRACK_B_TASK_092`
- future Task 105 primary session: `TRACK_B_TASK_105`

If the same Task intentionally uses multiple simultaneous Agent sessions, keep the same fixed prefix and append a numeric suffix:

`TRACK_B_TASK_<TaskNumber>_2`, `TRACK_B_TASK_<TaskNumber>_3`, etc.

The exact declared Session Name MUST be recorded in the repository Result. Agent model/role is recorded separately in the Result and is not part of the Session Name.

## 4. Execution Route

### Stage B1 — Recovery Foundation Implementation

- Agent class: `Codex`
- Risk: `HIGH`
- Goal: implement Recovery-owned `ReconciliationCase`, evidence, retry scheduling state, bounded escalation and manual Recovery disposition without mutating subject Owners.
- Exact production SHA required before Result commit.
- Full `tests/kernel` and focused Recovery tests required.

### Stage B2 — Independent Semantic Review

Starts only after Stage B1 produces an exact production SHA and repository Result.

- Preferred Agent class: `Claude`
- Independent from implementation session.
- Review exact production SHA, not branch tip.
- Focus: Owner boundary, identity/idempotency, replay/crash correctness, retry authority, deadline/escalation, evidence semantics, manual disposition, write isolation and blind-effect-replay prohibition.
- Output: `PASS`, `PASS WITH NON_BLOCKING FINDINGS`, or `FINDINGS / BLOCKED` with typed findings.

The concrete Task ID is allocated from the next globally free Task number at routing time to avoid collisions with Track A.

### Stage B3 — Targeted Correction

Conditional on blocking implementation/contract findings.

- Preferred Agent: reuse the Stage B1 Codex session if context remains reliable.
- Otherwise open a new Codex session using the fixed Track B Session Name rule.
- Scope limited to accepted findings; no opportunistic redesign.
- New exact production SHA required.

Architecture findings are not implementation work. They fail closed and escalate to Lead authority.

### Stage B4 — Targeted Re-Review

Conditional on Stage B3.

- Preferred Agent: reuse the Stage B2 Claude reviewer session when possible.
- Verify only prior findings plus regression surface introduced by corrections.
- Do not replace this with implementation-agent self-review.

### Stage B5 — Mechanical Audit (Optional)

Use `DeepSeek` only when the implementation/review diff creates enough mechanical verification work to justify it, such as:

- schema/DDL consistency;
- exhaustive test matrix checking;
- scope/write-surface audit;
- duplicate/stale field checks;
- repository protocol verification.

DeepSeek does not replace the independent semantic review for this HIGH-risk foundation.

### Stage B6 — Track B Stable Candidate Checkpoint

Track B may be declared a stable component candidate only when:

- implementation Result exists;
- exact production SHA is known;
- all blocking findings are closed;
- final independent review passes the exact candidate SHA;
- no cross-Track contract was silently invented;
- production remains Recovery-package-local under the authorized scope.

This checkpoint is not global production acceptance and does not authorize Track B to merge Track A or alter Accounting canonical truth.

## 5. Dependency / Parallelism Rules

- Track A may continue independently.
- Do not read or depend on unaccepted Track A production as a cross-Track contract.
- If Recovery needs a public UsageFact/Accounting contract not already frozen, record `WAITING / BLOCKED` and escalate rather than inventing one.
- Settlement remains outside Track B.
- `src/nyron_kernel/accounting/` and `src/nyron_kernel/store/sqlite_store.py` remain forbidden write surfaces unless a later Task explicitly re-authorizes them.
- Do not update `coordination/STATUS.md` without separate global Coordination Write Authority.

## 6. Result Protocol

For every executable/review Task:

1. Task file is canonical instruction.
2. Agent declares the fixed Track B Session Name at session start.
3. Production content is committed first when production changes exist.
4. Exact production SHA is recorded.
5. Result is written to `coordination/results/<TaskID>.md`.
6. Result records Agent model and declared Session Name.
7. Result commit must not obscure production content identity.
8. Chat is trigger/status only; the operator only needs to report which Agent/Task finished.

## 7. Orchestrator Reporting Contract

Every Track B orchestrator progress report must include:

- `Active / Running`
- `Waiting`
- `Completed`
- `Findings / Blockers`
- `Next Route`

The orchestrator reads repository Results directly after the operator reports completion.
