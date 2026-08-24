# Nyron Accounting / Recovery Frozen Baseline v0.1

Status: **FROZEN ACCOUNTING / RECOVERY ARCHITECTURE BASELINE**
Authority: Nyron Lead Design Authority
Task: `NYRON-D-005`

## Frozen bundle

This baseline freezes the following exact repository artifacts as one normative bundle:

1. `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`
   - blob SHA: `f615f9351ef92c92968f4233b1e025abc8573367`
2. `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`
   - blob SHA: `5ddc298da449c5ca66520354719de5a4bda3e306`
3. `design/clarifications/NYRON-D-005_D-010_Lead_Integration_Clarification_002.md`
   - blob SHA: `4fe1afe1c4b8c43b511e074af78d909d0e701bd6`

The frozen interpretation is Candidate + both Lead clarifications together.

## Review disposition

Lead integration review: **PASS**.
Independent DeepSeek bounded consistency review: **PASS**, as reported to the Lead coordination thread on 2026-08-24. No blocking Architecture Finding was reported.

## Frozen scope

The baseline freezes, among other things:
- Accounting Owner / Recovery Owner separation;
- static accounting membership from immutable definition containment;
- hierarchical owner-local atomic BudgetReservation;
- estimate versus actual separation;
- immutable usage facts and late billing/correction semantics;
- `EffectOperation != BudgetReservation != ResourceLease != CapabilityGrant`;
- UNKNOWN not being converted to zero/success/failure;
- ReconciliationCase as bounded investigation rather than second workflow engine;
- Recovery disposition not being subject truth or universal conflict clearance;
- Project/Workspace policy context supplying pinned inputs without owning Accounting truth;
- no dynamic reassignment of accounting membership from mutable Workspace/Project context.

## Change rule

Implementation MUST NOT silently reinterpret this baseline. A semantic change requires an explicit Architecture Finding and Lead-approved Amendment or superseding frozen baseline.
