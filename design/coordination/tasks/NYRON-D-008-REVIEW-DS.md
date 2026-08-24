# NYRON-D-008-REVIEW-DS — External Interfaces / Workspace Independent Consistency Review

Repository: `https://github.com/ahhhh450/nyron`
Mode: review only; no implementation; no repository modification; no freeze authority.

## Read
1. `design/README.md`
2. `design/coordination/STATUS.md`
3. `design/Universal_Runtime_Module_Design_Report_v0.1.md`
4. `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
5. `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`
6. `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`
7. `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`
8. `design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`
9. `design/clarifications/NYRON-D-008_Lead_Integration_Clarification_001.md`
10. `design/clarifications/NYRON-D-008_D-010_Lead_Integration_Clarification_002.md`
11. `design/clarifications/NYRON-D-010_D-001_Lead_Integration_Clarification_001.md`
12. `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md` only for runtime/recovery boundary.

## Correct premises
- D-008 consumes D-004; it does not redefine CapabilityGrant, Resource/ResourceLease or EffectOperation ownership/lifecycle.
- Workspace identity/config is PWP-owned and distinct from Workspace Handle Resource/Lease/raw path.
- PWP EnvironmentBindingRevision is configuration, not proof of live Resource availability or Lease authority.
- IngressRoute identity/revision/config is PWP-owned; Adapter executes route contract but is not route/target fact Owner.
- Generic workflow-start external input targets Runtime-owned ExecutionIngressFact then Trigger Packet -> Delivery -> Activation; no direct Activation.
- HumanResponse/billing/effect/resource callbacks remain owned by their domain Owners.
- Observation is not automatically exempt from EffectOperation; adapter semantics fail closed when read-like operations are billable/stateful/crash-ambiguous/consequential.
- Timeout, disconnect, kill request or absence is not proof of completion/non-dispatch/fencing.

## Review focus
1. workspace containment, symlink/mount/TOCTOU authority boundaries;
2. PWP logical Workspace/config vs Resource Manager live handle/lease separation;
3. process descendant containment and kill/confirm semantics;
4. network destination/DNS/redirect scope revalidation;
5. browser observation vs consequence classification;
6. provider streaming/cancel/timeout/retry safety;
7. remote worker/job Resource vs Effect separation;
8. credential possession not becoming authority;
9. PWP IngressRoute config, Adapter mediation, canonical target Owner and Runtime ExecutionIngressFact boundary;
10. generic ingress dedupe and no direct Activation path;
11. adapter TCB and IsolationProfile claims;
12. durable external IDs/idempotency/lookup and UNKNOWN;
13. import/rebinding cannot widen authority or transfer live Resource/Grant/effect authority;
14. EIW-INV-01..31 consistency and Frozen/D-004/PWP compatibility.

## Return
If valid:
`REVIEW RESULT: PASS`
Then only non-blocking clarifications and freeze recommendation.

If invalid:
`REVIEW RESULT: FAIL`
For each blocker: Finding ID, section/invariant, correctness problem, minimal fix.

If frozen baseline must change:
`ARCHITECTURE FINDING — FROZEN BASELINE IMPACT`
