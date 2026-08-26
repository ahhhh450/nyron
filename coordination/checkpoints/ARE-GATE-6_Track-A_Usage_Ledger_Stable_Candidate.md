# ARE-GATE-6 Track A — Usage / Ledger Stable Candidate Handoff

Status: `COMPLETED / STABLE CANDIDATE READY FOR GLOBAL INTEGRATION`
Owner: `GPT — Nyron Track-A Development Orchestrator`
Coordination Basis: `Epoch 2 / Revision 88`
Track: `PARALLEL TRACK A — Usage / Ledger`
Global Acceptance Authority: `NOT OWNED BY TRACK A`

## Final Reviewed Production Candidate

- Exact production SHA: `e5acf1abb9a03667315a364ba7e1a8b002ed31cd`
- Production branch: `task/NYRON-T-20260826-095`
- Original foundation SHA: `838af6360002f2ca98439c543bc66dd50b76be7a`
- Accepted production basis inherited by Track A: `84156a5be8d77dc69fd21b02ffa2cf49f5154a8b`

## Task / Review Chain

- `NYRON-T-20260826-090` — Claude Code — Usage / Ledger foundation implementation — `SUCCESS`.
- `NYRON-T-20260826-093` — DeepSeek — bounded mechanical audit of original SHA — `FINDINGS`; sole finding `F-093-001` identified missing DELETE immutability guards on the original candidate.
- `NYRON-T-20260826-094` — Codex — independent high-risk semantic review of original SHA — `FINDINGS / BLOCKING`; `NYRON-T-20260826-094-F-001` confirmed canonical UsageFact / UsageAdjustmentFact rows were deletable.
- `NYRON-T-20260826-095` — Claude Code — implementation-local fix — `SUCCESS`; added database-level DELETE immutability guards and focused regression tests.
- `NYRON-T-20260826-099` — Codex — independent exact-SHA re-review of fixed candidate — `PASS / FINDINGS NONE / F-001 CLOSED`.

## Findings Disposition

### `NYRON-T-20260826-094-F-001`

- Type: `IMPLEMENTATION`
- Severity: `BLOCKING`
- State: `CLOSED`
- Closed by production SHA: `e5acf1abb9a03667315a364ba7e1a8b002ed31cd`
- Closure review: `NYRON-T-20260826-099`

### `F-093-001`

- Mechanical observation on original SHA `838af6360002f2ca98439c543bc66dd50b76be7a`.
- Same underlying DELETE-immutability defect later classified blocking by Task 094.
- Disposition: `SUPERSEDED / CLOSED BY TASK 095 + TASK 099`.

Track A has no unresolved blocking finding at this handoff point.

## Stable Track-A Surface

The reviewed candidate provides the bounded Accounting-owned Usage / Ledger foundation:

- `UsageFact`
- `UsageFactRequest`
- `UsageAdjustmentFact`
- `UsageAdjustmentFactRequest`
- `UsageLedger`
- `UsageLedgerError`
- Accounting-local SQLite support for immutable `usage_facts` and `usage_adjustment_facts`
- stable source dedupe identity based on `(source_authority_ref, source_fact_id, fact_kind, dimension_ref)`
- exact duplicate callback idempotency
- conflicting same-identity fail-closed behavior with machine-readable reconciliation-required outcomes
- append-only correction / refund facts referencing original usage truth
- replay-after-commit idempotency
- UPDATE and DELETE immutability guards for both canonical fact tables

## Preserved Boundaries

This Track-A candidate does not implement or own:

- BudgetReservation settlement transitions;
- reserved-to-committed exposure conversion;
- Recovery Owner / ReconciliationCase canonical state;
- Runtime / Effect / Resource / Capability / Host canonical mutation;
- cross-owner global Accounting <-> Recovery integration;
- provider-specific billing, pricing, currency conversion or rolling-window policy.

No frozen Accounting / Recovery Contract was changed or reinterpreted by Track A.

## Final Validation Evidence

At exact reviewed SHA `e5acf1abb9a03667315a364ba7e1a8b002ed31cd`:

- focused Usage/Ledger tests: `21 passed`;
- complete `tests/kernel`: `284 passed, 2 skipped, 96 subtests passed, 0 failed`;
- `git diff --check`: clean;
- Codex independent re-review: `PASS / FINDINGS NONE / F-001 CLOSED`.

## Integration Handoff Rule

This checkpoint does not modify `coordination/STATUS.md`, does not globally accept production, and does not merge any Track B branch.

Global integration should consume the exact reviewed Track-A production candidate SHA `e5acf1abb9a03667315a364ba7e1a8b002ed31cd` and the review chain above. Any later Settlement or global Accounting <-> Recovery integration must build on explicit accepted exact-SHA content rather than reconstructing Track-A behavior manually.
