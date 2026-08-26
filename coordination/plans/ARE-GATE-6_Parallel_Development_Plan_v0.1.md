# ARE-GATE-6 Parallel Development Plan v0.1

Status: `ACTIVE ORCHESTRATION PLAN / NOT ARCHITECTURE`
Owner: `Web GPT — Development Orchestrator`
Date: `2026-08-26`

## Purpose

Adopt the user-approved development pattern for the remaining ARE-GATE-6 work:

`Frozen Backbone -> bounded parallel component development -> frequent integration checkpoints -> exact-SHA final integration/review`

This is a scheduling/integration plan only. It does not amend the frozen Accounting / Recovery architecture.

## Five-Part Shape

1. **Backbone** — canonical objects, Owner boundaries, state/Command/Event contracts, replay/idempotency rules.
2. **Usage / Ledger** — UsageFact, UsageAdjustmentFact, immutable actual-usage evidence, stable dedupe, late correction basis.
3. **Settlement** — BudgetReservation COMMITTED / RELEASED / RECONCILING transitions, overrun and reserved-vs-actual accounting.
4. **Recovery** — ReconciliationCase, evidence, retry/backoff/deadline, escalation and manual disposition boundaries.
5. **Integration** — Accounting <-> Recovery <-> Runtime / Effect / Resource cross-owner integration, crash/replay/E2E and final independent review.

## Backbone Disposition

For the current Gate-6 continuation, Part 1 does not require a new standalone design task. The operative Backbone is already supplied by:

- `design/Nyron_Accounting_Recovery_Frozen_Baseline_v0.1.md`
- its frozen candidate / Lead clarification bundle;
- `design/clarifications/NYRON-D-005_Lead_Integration_Clarification_003.md` for the Gate-6A policy-chain semantics;
- accepted Gate-6A production at `84156a5be8d77dc69fd21b02ffa2cf49f5154a8b`.

If implementation discovers an unresolved public cross-owner contract or semantic ambiguity, the affected track must fail closed and escalate rather than silently inventing a new Backbone rule.

## Current Parallelism Limit

Current operator capacity: **2 active development parts at one time**.

Initial slots:

- **Track A — Usage / Ledger**: Task `NYRON-T-20260826-090`.
- **Track B — Recovery / ReconciliationCase Foundation**: Task `NYRON-T-20260826-091`.

Deferred until a slot is explicitly opened by the operator:

- **Settlement** (Part 3), normally the next Accounting track once Usage/Ledger exposes stable accepted facts/interfaces.
- any additional review/implementation track beyond the two active development slots.

The operator may request a higher parallelism limit later; this plan does not pre-authorize it.

## Parallel Safety Rules

- Both initial tracks start from the same exact accepted production basis.
- Use dedicated branches/worktrees; never share a mutable working tree between active tracks.
- Avoid overlapping production write surfaces. Track B must remain Recovery-package-local and must not edit Accounting production or `src/nyron_kernel/store/sqlite_store.py`; if that proves impossible, stop with `ESCALATION_REQUIRED` rather than silently creating a shared-write dependency.
- Track A must not implement Recovery Owner state or settlement transitions.
- No track may mutate another Owner's canonical truth.
- No final acceptance is based on branch tip identity; exact production SHA is mandatory.

## Integration Policy

Do not wait until every remaining Gate-6 component is finished before first integration.

Use bounded checkpoints:

1. each track produces an exact production SHA and Result;
2. independent review as risk requires;
3. accepted component content is integrated or rebased into the current accepted backbone before the next dependent slice grows large;
4. later Settlement and final cross-owner integration build on accepted exact content, not manually reconstructed branches;
5. final Gate-6 closure still requires exact-SHA independent integrated review.

## Scheduling Model

The project should be treated as a dependency graph, not a globally serial Task queue.

Parallel by default only when BOTH are true:

- no unsettled Contract dependency exists;
- no overlapping production write surface exists.

Otherwise the dependent task waits.

## Current Decision

Gate-6A is `PASS / CLOSED`. Start only Track A and Track B now. Keep Settlement and further tracks waiting until the operator explicitly increases capacity or one current slot becomes free.
