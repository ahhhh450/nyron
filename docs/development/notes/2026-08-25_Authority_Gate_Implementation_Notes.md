# Authority Gate Implementation Notes

- Date: `2026-08-25`
- Related Design: `NYRON-D-004`
- Related Tasks: `NYRON-T-20260825-034` through current ARE gate work
- Status: `WORKING / VALIDATED BY CURRENT IMPLEMENTATION REVIEWS`
- Promote To: future Nyron development guide / generic AI-assisted development documentation

## Problem / Context

Frozen D-004 requires Capability, Resource and EffectOperation to remain distinct canonical facts and owners. Clarification 004 additionally requires actual authority consumption to linearize race-safely against replacement/revoke/expiry and explicitly forbids plain check-then-use.

A tempting implementation shortcut is to make Capability or Resource validation return a reusable permit/token before any real EffectOperation or Canonical Command boundary exists.

## Decision / Current Direction

Do **not** invent a hypothetical authority-use permit merely to complete an earlier gate.

Implement each owner foundation only to the real boundary available in that gate:

- Capability gate: canonical CapabilityType / CapabilityGrant ownership, scope, lifecycle, current-authority validation; validation remains advisory/non-consumptive.
- Resource gate: canonical Resource / ResourceLease ownership, real bounded resource lifecycle, provenance/crash recovery, lease lifecycle/current-authority validation; validation remains advisory/non-consumptive.
- Effect/Command gate: only when a real consequential boundary exists, implement the race-safe authority-consumption linearization required by Clarification 004.

## Why

This preserves the architecture instead of satisfying a future invariant with a fake abstraction that has no real consumption point.

It also avoids:

- cached validation being mistaken for authority;
- premature permit/ticket/admission frameworks;
- cross-owner semantics leaking into Capability or Resource owners;
- over-engineering around hypothetical future providers/effects;
- having to later unwind a wrong authority boundary.

## Alternatives Considered

1. Add an ARE-GATE-1B generic authority-use permit.
   - Rejected: no real external/foreign consequence boundary exists yet; would create speculative semantics.

2. Treat `ValidateCapability` / `ValidateLease` as sufficient immediately before future use.
   - Rejected: frozen Clarification 004 explicitly forbids plain check-then-use.

3. Build a generalized multi-owner admission framework early.
   - Deferred: should be driven by a concrete EffectOperation / Canonical Command implementation and tested against real replacement/revoke races.

## Reusable Insight

**Implement safety invariants at the first real boundary where they can be made true, not at an earlier layer through a placeholder abstraction.**

For AI-assisted development, this becomes a useful anti-over-engineering rule:

> A future invariant is not permission to invent future machinery early. Preserve the boundary, record the deferred invariant, and implement it when its real linearization/ownership point exists.

## Related Process Insight

High-risk owner/lifecycle boundaries should be independently reviewed after implementation and before integration. Review sessions should be isolated when reasoning independence or substantially different risk context is required, rather than mechanically opening one new session per Task.
