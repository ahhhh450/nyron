# NYRON-D-005 — Accounting / Recovery Design

**Conversation:** `Nyron设计-NYRON-D-005-Accounting-Recovery`
**Status:** DELEGATED / IN PROGRESS
**Mode:** Design only; no implementation; no freeze authority.

## Goal
Produce `Nyron Accounting / Recovery Design Candidate v0.1` covering BudgetReservation / AccountingScope / usage facts / UNKNOWN / ReconciliationCase while preserving EffectOperation orthogonality.

## Minimum Context
Read only:
1. `design/README.md`
2. `design/coordination/STATUS.md`
3. `design/Nyron_Overall_System_Architecture_v0.1.md`
4. `design/Universal_Runtime_Module_Design_Report_v0.1.md`
5. `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
6. `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`

Read D-003 only if a Runtime candidate already exists and only for interfaces concerning Attempt lifecycle / terminal facts. Do not redesign Runtime.

## Frozen / Candidate Boundaries
Must preserve:
- EffectOperation ≠ BudgetReservation.
- ResourceLease ≠ BudgetReservation.
- Capability ≠ Budget authority.
- actual external facts must never be rewritten to satisfy budget policy.
- UNKNOWN past facts remain UNKNOWN until evidence resolves them.
- ReconciliationCase is not a second Workflow engine and must not duplicate subject truth.
- static accounting membership derives from immutable Graph/Composite containment, not dynamic packet provenance.
- cross-owner state is not assumed globally atomic.

## Must Design
1. AccountingScope identity and ownership.
2. static scope ancestry / inheritance.
3. Budget policy, limit and quota vocabulary.
4. BudgetReservation identity and lifecycle.
5. reserve / deny / commit / release / reconcile semantics.
6. hierarchical atomic reservation requirements within Accounting Owner.
7. estimated vs actual usage and overrun handling.
8. durable usage facts and deduplication.
9. EffectOperation ↔ BudgetReservation references without ownership collapse.
10. UNKNOWN effect/resource/accounting combinations.
11. ReconciliationCase ownership and lifecycle.
12. retry/backoff/deadline/escalation/manual-resolution boundaries.
13. recovery evidence model and resolution authority.
14. crash/replay/restart semantics.
15. orphan reservation / late provider billing / duplicate usage callback cases.
16. cross-owner Commands/Events with Runtime, Effect Authority, Resource Manager and Human Interaction.
17. what blocks new conflicting work vs what only affects settlement.
18. derived reporting/projection vs canonical accounting truth.
19. `AR-INV-*` invariants.
20. implementation gates and unresolved questions.

## Hard Ownership Boundary
D-005 owns Accounting settlement/reconciliation policy and ReconciliationCase mechanics.
It must NOT redefine Runtime Attempt replacement, EffectOperation lifecycle, ResourceLease lifecycle, Capability policy, Graph membership semantics or product UX.

If UNKNOWN handling requires changing frozen Effect/Resource semantics, raise an `ARCHITECTURE FINDING` instead of silently absorbing the state into Accounting.

## Output
Return a complete `Nyron Accounting / Recovery Design Candidate v0.1` with object/state models, ownership, cross-owner contracts, crash/replay semantics, invariants, open questions, findings and implementation gates.

Do not implement code. Do not freeze architecture.