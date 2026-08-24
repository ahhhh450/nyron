# Nyron Runtime Orchestration Frozen Baseline v0.1

Status: **FROZEN RUNTIME ORCHESTRATION ARCHITECTURE BASELINE**
Authority: Nyron Lead Design Authority
Task: `NYRON-D-003`

## Frozen bundle

This baseline freezes the following exact repository artifacts as one normative bundle:

1. `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`
   - blob SHA: `25859f00f47cab7652d6089d2701b681f124d317`
2. `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md`
   - blob SHA: `5ddc298da449c5ca66520354719de5a4bda3e306`
3. `design/clarifications/NYRON-D-003_D-010_Lead_Integration_Clarification_002.md`
   - blob SHA: `eac21c88aa52c68c637c85219162cade691e0e15`

The frozen interpretation is Candidate + both Lead clarifications together. If wording conflicts, the later Lead clarification controls only the explicitly clarified integration point and does not otherwise rewrite the Candidate.

## Review disposition

Lead integration review: **PASS**.
Independent DeepSeek bounded consistency review: **PASS**, as reported to the Lead coordination thread on 2026-08-24. No blocking Architecture Finding was reported.

## Frozen scope

The baseline freezes, among other things:
- immutable GraphRevision admission context;
- Packet -> Delivery -> Activation -> Run / Attempt as the sole execution path;
- one Run lineage per Activation and one current Attempt per Run;
- retry/replacement creating a new Attempt; resume preserving Attempt identity;
- current-attempt fencing and stale Attempt rejection;
- explicit durable suspension / Subscription / EventDelivery resume path;
- FEEDBACK having no special Runtime semantics;
- canonical quiescence/directive-based terminal state;
- Runtime ownership of generic workflow-only `ExecutionIngressFact` after authoritative external canonicalization;
- no direct Activation ingress;
- foreign Owner clearance never fabricated by Runtime or Recovery.

## Change rule

Implementation MUST NOT silently reinterpret this baseline. A semantic change requires an explicit Architecture Finding and Lead-approved Amendment or superseding frozen baseline.
