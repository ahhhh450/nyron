# EffectOperation Gate 3 Subdivision

Date: 2026-08-25
Related Design: NYRON-D-004 §26; Clarification 003; Clarification 004
Status: WORKING / NON-NORMATIVE

## Problem / Context

Frozen D-004 ARE-GATE-3 ultimately requires EffectOperation foundation strong enough to cover bounded mutation plus long/async effect behavior, PREPARED-before-dispatch, crash ambiguity, completion, revoke and UNKNOWN.

Implementing every one of those behaviors in one initial Task would combine several independent high-risk correctness boundaries:

- Effect Authority canonical ownership;
- durable PREPARED identity;
- Capability + ResourceLease + Runtime Attempt/fencing authority-consumption linearization;
- external dispatch evidence;
- crash-before/after-dispatch distinction;
- cancellation/revoke/fencing;
- long-running/async state;
- UNKNOWN and later reconciliation handoff;
- conflict/retry semantics.

That is too broad for one first implementation slice and would make review evidence harder to isolate.

## Decision / Current Direction

Treat frozen ARE-GATE-3 as an umbrella Gate and implement it through bounded internal sub-gates without changing the frozen architecture:

- ARE-GATE-3A — Bounded EffectOperation Foundation: establish Effect Authority ownership, durable PREPARED-before-dispatch, exact authority binding, one real bounded mutation, and the first race-safe authority-consumption admission at the actual dispatch boundary.
- Later ARE-GATE-3B — Long/Async + Crash Ambiguity: add a genuinely long/async external operation and prove ACTIVE/COMPLETED/UNKNOWN behavior across dispatch crash windows.
- Revoke/fencing/conflict/retry behavior remains added only when the corresponding real operation semantics exist; no speculative generalized framework is introduced in 3A.

ARE-GATE-3 is not considered closed merely because 3A passes.

## Why

This keeps each review focused on one new semantic axis at a time. Most importantly, Clarification 004's authority-consumption linearization is introduced only where a real external consequence is about to begin. It avoids inventing a hypothetical permit during Capability/Resource foundations and avoids simultaneously coupling that first linearization proof to long-running cancellation and UNKNOWN semantics.

## Alternatives Considered

### One large ARE-GATE-3 implementation Task
Rejected because it bundles too many failure modes and creates a large review surface.

### Build generic effect/provider/adapter framework first
Rejected as over-engineering. Gate 3A should use one bounded concrete effect sufficient to prove the canonical protocol.

### Keep ValidateCapability / ValidateLease as pre-dispatch check-then-use
Forbidden by Clarification 004. Actual external consequence must begin only after a race-safe admission for the exact operation.

## Reusable Insight

When a frozen architecture Gate spans several independent correctness dimensions, the Orchestrator may split implementation into internal sub-gates as long as:

1. the frozen architecture is not reinterpreted;
2. the parent Gate is not falsely declared complete early;
3. each sub-gate has an independently reviewable semantic objective;
4. future mechanisms are not pre-built speculatively merely to make the first slice look complete.

This pattern is useful for AI-assisted development because it keeps Agent context, diff size, review independence and regression evidence bounded.

## Promote To

Future Generic Documentation / Development Orchestration Guide.
