# Nyron Project / Workspace / Policy Context Frozen Baseline v0.1

**Status:** FROZEN PROJECT / WORKSPACE / POLICY CONTEXT ARCHITECTURE BASELINE  
**Task:** `NYRON-D-010`  
**Freeze authority:** Nyron Lead Design Authority  
**Freeze date:** 2026-08-24

## Frozen constituent content

### Candidate
- Path: `design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`
- Blob SHA: `daa8e45e15d5e90006c4179e5d079401e44571dc`

### Normative Lead clarifications
1. `design/clarifications/NYRON-D-010_D-001_Lead_Integration_Clarification_001.md`
   - Blob SHA: `028e5b8fc60f3fbb0748af77e1d13d549c68ead6`
2. `design/clarifications/NYRON-D-007_D-010_Lead_Integration_Clarification_001.md`
   - Blob SHA: `251eb8dbad2be72b5aac67c2ec39170cbcb0b323`
3. `design/clarifications/NYRON-D-008_D-010_Lead_Integration_Clarification_002.md`
   - Blob SHA: `82967653edc928eca8a08b744ef33eab985944b6`
4. `design/clarifications/NYRON-D-003_D-010_Lead_Integration_Clarification_002.md`
   - Blob SHA: `eac21c88aa52c68c637c85219162cade691e0e15`
5. `design/clarifications/NYRON-D-005_D-010_Lead_Integration_Clarification_002.md`
   - Blob SHA: `4fe1afe1c4b8c43b511e074af78d909d0e701bd6`

### Independent review evidence
- Path: `design/reviews/NYRON-D-007_D-009_D-010_DeepSeek_Review_PASS_Receipt.md`
- Blob SHA: `37be35d983778d2348d6d9ab29bcf85eceb3e691`
- Result for D-010: **PASS**

## Frozen interpretation

Project / Workspace Context Owner (PWP Owner) canonically owns Project/Workspace identity, immutable configuration/policy-context/environment-binding revisions and IngressRoute identity/revision/configuration.

PWP does not own live Resource/ResourceLease, CapabilityGrant, Runtime execution state, Graph topology, Accounting state, HumanResponse truth, EffectOperation, or raw secret values.

Execution admission pins exact immutable Project/Workspace/config/policy/environment/route/Graph context references. Admitted executions never silently re-resolve mutable `current/latest` context.

`workspace_ref` is logical identity and is permanently distinct from live Workspace Handle Resource/Lease, host path or mount identity.

Generic external workflow-start intent is canonically represented by Runtime-owned `ExecutionIngressFact`; PWP owns route configuration only. Domain-specific external business facts remain owned by their corresponding domain Owner.

Higher-level budget scopes remain Accounting-owned; PWP provides immutable context anchors only. Package trust decisions remain Distribution-owned; PWP provides trust-policy context only.

`AF-PWP-001` is resolved by the Runtime-owned generic execution-ingress contract and is closed.

## Freeze decision

Lead Design Authority finds no remaining blocking Architecture Finding for D-010 and freezes this architecture for v0.1 implementation.

Any later semantic change requires an explicit Amendment or superseding frozen baseline.
