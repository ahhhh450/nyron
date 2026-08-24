# NYRON-D-005-REVIEW-DS — Accounting / Recovery Independent Consistency Review

Repository: `https://github.com/ahhhh450/nyron`
Mode: review only; no implementation; no repository modification; no freeze authority.

## Read
1. `design/README.md`
2. `design/coordination/STATUS.md`
3. `design/Universal_Runtime_Module_Design_Report_v0.1.md`
4. `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
5. `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`
6. `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`
7. `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`
8. `design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`
9. `design/Nyron_Human_Interaction_Approval_Authority_Design_Candidate_v0.1.md`
10. `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`
11. `design/clarifications/NYRON-D-005_D-010_Lead_Integration_Clarification_002.md`
12. `design/clarifications/NYRON-D-009_Lead_Integration_Clarification_001.md` only for manual-policy evidence boundary.

## Correct premises
- EffectOperation != BudgetReservation != ResourceLease != CapabilityGrant.
- Accounting owns BudgetReservation/UsageFact/settlement and the hard-limit AccountingScope hierarchy; Recovery owns ReconciliationCase only.
- Recovery never owns subject truth.
- UNKNOWN is not zero/success/failure.
- ReconciliationCase.RESOLVED does not itself clear Effect/Resource conflicts.
- Recovery may produce a scope-specific administrative disposition permitting Runtime closure while foreign subject truth remains UNKNOWN; only the subject Owner can clear its own conflict authority.
- Static accounting membership is pinned from immutable definition containment; mutable current PWP context cannot dynamically reassign an admitted Activation.
- PWP may supply stable Project/Workspace/accounting policy context refs, but does not own BudgetPolicyRevision/Reservation/settlement.
- Higher-level Project/Workspace/organization budget scopes, if used, remain Accounting-owned and full-ancestry reservation remains owner-local atomic.
- Human Interaction owns response evidence; PWP/Identity owns role context; Accounting owns budget-policy/state transition.

## Review focus
1. AccountingScope identity/static ancestry correctness;
2. hierarchical atomic reservation across ancestor chain, including any PWP-anchored higher-level accounting scopes;
3. BudgetReservation lifecycle and idempotent request identity;
4. estimate vs actual separation;
5. usage callback dedupe/conflicting evidence handling;
6. late billing/reopen settlement semantics;
7. Effect/Resource/Capability/Budget orthogonality;
8. ReconciliationCase bounded retry/escalation;
9. manual evidence vs policy disposition;
10. Runtime closure disposition vs foreign conflict clearance separation;
11. crash/replay/orphan reservation correctness;
12. mutable PWP config/policy cannot reinterpret historical accounting membership;
13. cross-owner context refs do not split hard reservation into best-effort PWP+Accounting transactions;
14. AR-INV-01..24 consistency and Frozen baseline compatibility.

## Return
If valid:
`REVIEW RESULT: PASS`
Then only non-blocking clarifications and freeze recommendation.

If invalid:
`REVIEW RESULT: FAIL`
For each blocker: Finding ID, section/invariant, correctness problem, minimal fix.

If frozen baseline must change:
`ARCHITECTURE FINDING — FROZEN BASELINE IMPACT`
