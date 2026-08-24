# Nyron Capability / Resource / Effect Authority Frozen Baseline v0.1

Status: **FROZEN CAPABILITY / RESOURCE / EFFECT AUTHORITY ARCHITECTURE BASELINE**  
Authority: Nyron Lead Design Authority  
Task: `NYRON-D-004`

## 1. Frozen bundle

This baseline freezes the following exact repository artifacts as one normative D-004 bundle:

1. `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`
   - blob SHA: `77cc1994368fd0b847278e3c5f6e548272912684`
2. `design/clarifications/NYRON-D-004_Lead_Integration_Clarification_002.md`
   - blob SHA: `97f1fe428a3afa1d7783687576c73c125be05c6b`
3. `design/clarifications/NYRON-D-004_Lead_Integration_Clarification_003.md`
   - blob SHA: `2d629d76b54d309555c32ac3a446b7412fc07267`
4. `design/clarifications/NYRON-D-004_Lead_Integration_Clarification_004.md`
   - blob SHA: `671551f7b699169a183ab40c5ab3fb4cdbac86b0`

Mandatory frozen dependency:

5. `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
   - blob SHA: `a179144c7a39f2f991f4ec5001522ddb9af901f8`

Companion frozen cross-subsystem correction:

6. `design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`
   - blob SHA: `9fb007d6e44f869b51022c5fd4ef05482e8cf81c`
   - applies to frozen D-008 retry semantics and is mandatory for integrated interpretation of D-004/D-008 retry safety.

The frozen interpretation is Candidate + Clarifications 002/003/004 together, subject to Frozen Module Amendment 001 and the companion D-008 retry amendment. Later Lead clarification controls only the explicitly clarified point and does not silently rewrite unrelated Candidate semantics.

## 2. Review disposition

- Lead integration review: **PASS WITH FROZEN AMENDMENT 001**.
- Lead re-review found two additional correctness issues and resolved them through Clarification 003.
- Independent GPT adversarial review found two blocking issues:
  - F01 — FENCED incorrectly usable as semantic retry clearance;
  - F02 — authority validation/use race lacked a frozen linearization contract.
- Lead accepted both findings and corrected them through Clarification 004 plus External Interfaces Amendment 001.
- Independent GPT targeted re-review: **PASS**.
- Review receipt: `design/reviews/NYRON-D-004_GPT_Targeted_ReReview_PASS_Receipt_2026-08-24.md`.

No blocking Architecture Finding remains open for D-004.

## 3. Frozen scope

This baseline freezes, among other things:

- Capability Authority, Resource Manager and Effect Authority as separate canonical Owners;
- CapabilityGrant as Attempt/Run/Activation/fencing/scope/validity-bound, revocable and non-transferable authority;
- Resource / ResourceLease as stateful-handle/lifecycle truth independent of Capability;
- EffectOperation as Effect Authority-owned external-effect history/control truth;
- durable `EffectOperation(PREPARED)` before every crash-ambiguous external dispatch;
- external/provider idempotency identity as supplemental evidence, never a replacement for Nyron PREPARED identity;
- actual mediated effect/command authority use must race-safely linearize against relevant replacement/revoke/expire transitions;
- plain check-then-use authority validation is insufficient;
- stale Attempt cannot obtain new effect/command authority admission;
- pre-replacement admitted work remains identifiable in-flight work and is handled by normal effect/target-owner completion, fencing, cancellation, UNKNOWN and reconciliation semantics;
- deterministic/versioned machine-checkable EffectConflictScope semantics;
- unproven disjointness fails closed as conflicting;
- overlapping PREPARED/ACTIVE/REVOKE_REQUESTED/UNKNOWN effects block conflicting future authority as defined by the integrated conflict contract;
- `FENCED` clears active/concurrency continuation only and does not prove no historical consequence or semantic retry safety;
- active-effect conflict clearance and semantic retry clearance are orthogonal;
- historical outcome uncertainty may coexist with FENCED active state;
- Canonical Command remains capability-mediated but target Owner retains final mutation authority;
- cached validation cannot authorize late foreign mutation across a revocation race;
- Human approval is evidence, not CapabilityGrant;
- PWP policy context is input, not Capability authority;
- Package trust/install/enable is not Capability/Resource/Effect/Runtime authority;
- Recovery disposition cannot fabricate Effect/Resource/Capability clearance;
- Capability / Resource / EffectOperation / BudgetReservation remain distinct canonical facts and owners;
- Module Host / adapters are mediation or TCB boundaries, not canonical semantic Owners.

## 4. Key frozen invariants

The original `ARE-INV-01` through `ARE-INV-13` are frozen together with Lead-added invariants:

- `ARE-INV-14` — Policy Context Is Not Capability Authority
- `ARE-INV-15` — Human Approval Is Evidence, Not Grant
- `ARE-INV-16` — Recovery Cannot Fabricate Authority Clearance
- `ARE-INV-17` — Distribution Trust Cannot Grant Runtime Authority
- `ARE-INV-18` — External Recovery Identity Does Not Replace PREPARED
- `ARE-INV-19` — Unproven Disjointness Fails Closed
- `ARE-INV-20` — PREPARED Is Conflict-Relevant Until Non-dispatch Is Proven
- `ARE-INV-21` — FENCED Is Not Semantic Retry Clearance
- `ARE-INV-22` — Active State and Historical Consequence Are Orthogonal
- `ARE-INV-23` — Authority Validation and Use Must Linearize Against Revocation
- `ARE-INV-24` — PREPARED Is Not Authority Consumption
- `ARE-INV-25` — Canonical Command Cannot Cross a Revocation Race on Cached Authority

## 5. Change rule

Implementation MUST NOT silently reinterpret this baseline.

Any semantic change to ownership, authority lifecycle, PREPARED-before-dispatch, conflict-scope safety, FENCED/retry semantics, or authority-consumption linearization requires an explicit Architecture Finding and a Lead-approved Amendment or superseding frozen baseline.
