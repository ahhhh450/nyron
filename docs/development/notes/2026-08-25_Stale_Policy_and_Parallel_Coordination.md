# Stale Policy and Parallel Coordination

Status: **WORKING NOTES — NON-NORMATIVE**

Date: 2026-08-25  
Related Tasks: `NYRON-T-20260825-036`, `039`, `041`, `042`

## Problem / Context

Task 039 was a low-risk Result-metadata correction. It used `FAIL_CLOSED`, so an unrelated Coordination Revision change caused the task to become stale before execution even though none of its facts, files, or invariants had changed.

That created avoidable orchestration churn and risked delaying an unrelated high-priority implementation lane.

## Decision / Current Direction

Choose stale policy according to semantic coupling, not by habit.

Use `FAIL_CLOSED` for work whose correctness depends on the exact current coordination/design/authority state, especially:
- high-risk implementation;
- architecture/contract-sensitive changes;
- security/fencing/ownership boundaries;
- review whose conclusion can change if coordination assumptions change.

Use `RECHECK_AND_CONTINUE_IF_UNAFFECTED` for isolated low-risk work when all relevant facts can be explicitly revalidated, especially:
- Result metadata correction;
- test-only maintenance whose production basis is unchanged;
- mechanical documentation/process cleanup;
- bounded tasks on separate files/branches with no semantic dependency on unrelated Gate movement.

## Why

The goal of stale protection is to prevent execution under invalid assumptions, not to make every unrelated coordination update invalidate every active task.

A good stale policy minimizes both:
- unsafe continuation under changed assumptions; and
- unnecessary rework from irrelevant coordination churn.

## Reusable Insight

Parallel orchestration needs **semantic staleness**, not merely revision-number sensitivity.

A practical rule:

```text
high semantic coupling / high risk
-> FAIL_CLOSED

low semantic coupling + explicit recheckable facts
-> RECHECK_AND_CONTINUE_IF_UNAFFECTED
```

The Executor still must re-read current state and prove the named facts remain unchanged before continuing.

## Risks / Open Questions

`RECHECK_AND_CONTINUE_IF_UNAFFECTED` must never become a blanket permission for the Executor to decide that arbitrary architectural or security changes are irrelevant. The Task must state the exact facts allowed to be rechecked.

## Promote To

- future Generic Development Orchestration Guide
- future Task Protocol guidance if repeated evidence supports formalization
