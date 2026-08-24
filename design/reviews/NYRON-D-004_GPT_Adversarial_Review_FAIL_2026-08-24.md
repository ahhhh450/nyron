# NYRON-D-004 — GPT Independent Adversarial Review FAIL Record

**Date:** 2026-08-24  
**Reviewer:** independent GPT review window  
**Authority:** advisory review evidence; no freeze authority  
**Lead disposition:** both findings accepted as valid

## Review Result

`REVIEW RESULT: FAIL`

The independent GPT reviewer was explicitly instructed not to repeat the two issues already corrected by D-004 Lead Clarification 003 and to search for additional correctness holes.

It identified two new blocking findings.

---

## NYRON-D-004-GPT-F01 — FENCED incorrectly sufficient for semantic retry

Affected scope:
- D-004 provider/retry semantics;
- D-008 frozen provider retry semantics §11.7;
- EffectOperation FENCED interpretation.

Finding:
An old non-idempotent operation may be authoritatively stopped and therefore `FENCED` only after it already produced partial or complete external consequences. Treating `FENCED` as sufficient safe-redispatch evidence can duplicate external side effects.

Lead assessment: **VALID BLOCKER**.

Frozen baseline impact: **YES**, specifically frozen D-008 retry semantics.

Correction:
- `design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`
- `design/clarifications/NYRON-D-004_Lead_Integration_Clarification_004.md`

Normative correction:

```text
FENCED clears active/concurrency continuation risk
!= proof of no prior consequence
!= semantic retry clearance
```

Same-semantic retry requires independent no-consequence evidence, reliable idempotency/dedupe, explicit distinct-operation semantics, or policy accepting duplicates.

---

## NYRON-D-004-GPT-F02 — Authority validation/use revocation race

Affected scope:
- CapabilityGrant / ResourceLease / current Attempt fencing;
- effect boundary admission;
- Canonical Command target-owner acceptance.

Finding:
A plain check-then-use sequence can validate current Attempt/Grant/Lease, race with replacement/revoke, then use stale cached validation to dispatch externally or mutate a foreign Owner.

Lead assessment: **VALID BLOCKER**.

Frozen baseline impact: **NO**.

Reason:
The frozen baselines already require stale Attempts to lose future effect/commit authority and require authority validation at the actual boundary. The missing contract is the race-safe linearization needed to make those existing invariants implementable.

Correction:
- `design/clarifications/NYRON-D-004_Lead_Integration_Clarification_004.md`

Normative correction:
- actual authority consumption must be race-safely ordered against replacement/revoke;
- cached validation cannot cross the linearization point;
- if revoke wins first, use is rejected;
- if exact operation admission wins first, it becomes durably identifiable pre-revoke in-flight work and later replacement cannot pretend it never entered the boundary.

---

## Lead Review Conclusion

The pre-Clarification-004 D-004 bundle was **NOT FREEZE-CLEAN**.

The Lead has corrected both accepted findings through:
- `design/clarifications/NYRON-D-004_Lead_Integration_Clarification_004.md`;
- `design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`.

D-004 requires targeted independent re-review of the corrected bundle before freeze.

The same GPT review conversation should be reused; opening another GPT window is unnecessary.
