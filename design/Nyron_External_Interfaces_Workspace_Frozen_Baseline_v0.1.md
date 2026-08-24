# Nyron External Interfaces / Workspace Boundary Frozen Baseline v0.1

Status: **FROZEN EXTERNAL INTERFACES / WORKSPACE BOUNDARY ARCHITECTURE BASELINE**
Authority: Nyron Lead Design Authority
Task: `NYRON-D-008`

## Frozen bundle

This baseline freezes the following exact repository artifacts as one normative bundle:

1. `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`
   - blob SHA: `b0bb4e0e35da517dfb3d5b63496a2a3d43eb8777`
2. `design/clarifications/NYRON-D-008_Lead_Integration_Clarification_001.md`
   - blob SHA: `bd53387b90c9d3c0721d5742bd6eb21f0d1e64a0`
3. `design/clarifications/NYRON-D-008_D-010_Lead_Integration_Clarification_002.md`
   - blob SHA: `82967653edc928eca8a08b744ef33eab985944b6`

The frozen interpretation is Candidate + both Lead clarifications together.

## Review disposition

Lead integration review: **PASS**.
Independent DeepSeek bounded consistency review: **PASS**, as reported to the Lead coordination thread on 2026-08-24. No blocking Architecture Finding was reported.

## Frozen scope

The baseline freezes, among other things:
- external integrations as generic Module + Capability + Resource + Effect mappings, not Kernel primitives;
- Workspace identity distinct from live Workspace Handle Resource;
- Project / Workspace Context Owner owning durable workspace identity/configuration while D-008 owns only boundary semantics;
- PWP-owned IngressRoute configuration with explicit canonical target Owner;
- resolved path containment, symlink/mount/TOCTOU posture;
- process descendant containment and kill-confirm semantics;
- network effective-destination revalidation;
- browser/provider/remote observation-versus-consequence classification;
- PREPARED-before-dispatch for crash-ambiguous consequential operations;
- timeout/disconnect/cancel request/absence not being terminal proof;
- credential possession not being authority;
- external ingress canonicalization and no direct Activation ingress;
- explicit truthful IsolationProfile claims.

## Change rule

Implementation MUST NOT silently reinterpret this baseline. A semantic change requires an explicit Architecture Finding and Lead-approved Amendment or superseding frozen baseline.
