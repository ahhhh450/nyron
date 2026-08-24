# NYRON-D-010 — Project / Workspace / Policy Context Design

**Conversation name:** `NYRON-D-010`
**Status:** READY / DELEGATED WHEN OPENED
**Mode:** design only; no implementation; no freeze authority.

Repository: `https://github.com/ahhhh450/nyron`

## Goal
Produce `Nyron Project / Workspace / Policy Context Design Candidate v0.1` defining canonical ownership of project/workspace identity, immutable configuration/policy context, environment bindings and ingress-route configuration without taking over live Resources, Runtime execution or Capability decisions.

## Minimum Context
Read only:
1. `design/README.md`
2. `design/coordination/STATUS.md`
3. `design/Nyron_Overall_System_Architecture_v0.1.md`
4. `design/Nyron_Graph_Composite_Frozen_Baseline_v0.1.md`
5. `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`
6. `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`
7. `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`
8. `design/clarifications/NYRON-D-008_Lead_Integration_Clarification_001.md`
9. `design/clarifications/NYRON-D-003_D-005_Lead_Integration_Clarification_001.md` only for ingress/runtime binding.

Do not scan unrelated history.

## Hard Boundaries
Must preserve:
- `workspace_ref` logical identity != live Workspace Handle Resource.
- Resource Manager owns live Resources/Leases.
- Capability Authority owns Grant decisions; policy documents are inputs, not Grants.
- Runtime owns execution admission/Attempt state.
- GraphRevision is immutable definition authority.
- External adapters do not own workspace/project identity.
- secrets/credentials are referenced, not owned as raw values by this design.

## Must Design
1. Project identity and lifecycle at architecture level.
2. Workspace identity and lifecycle at architecture level.
3. project/workspace relationship and nesting rules.
4. immutable/revisioned ProjectConfig / WorkspaceConfig.
5. canonical policy source ownership: project/workspace/security/runtime-admission inputs.
6. policy precedence/restriction composition without duplicating Capability Authority.
7. environment binding identity (local root/provider/browser/worker classes) vs live Resource distinction.
8. workspace root declarations and portability descriptors.
9. binding revisions and historical pinning.
10. Graph execution admission context references to project/workspace/config/policy revisions.
11. external ingress route registration/configuration Owner.
12. ingress route identity, auth policy ref, target canonical Owner/event type, Graph ingress binding.
13. import/export/rebinding semantics without authority widening.
14. project/workspace archival/deprecation and historical resolvability.
15. policy/config updates and whether active executions observe them or remain pinned.
16. user/system policy references without defining account/auth subsystem internals.
17. cross-owner contracts with Graph, Runtime, Capability, Resource, Accounting, External Interfaces, Human Interaction.
18. canonical vs derived workspace/project state.
19. `PWP-INV-*` invariants.
20. implementation gates/open questions/findings.

If this design needs to own live Resource state, CapabilityGrant, Runtime Attempt or Graph topology, it has crossed its boundary and must raise an `ARCHITECTURE FINDING` instead.

## Required Repository Deliverable
Write the complete Candidate to:

`design/Nyron_Project_Workspace_Policy_Context_Design_Candidate_v0.1.md`

Commit it to the repository.

Final response must return only:
- result status;
- file path;
- commit SHA;
- Architecture Finding, if any.

If repository writing is unavailable, return `REPOSITORY_WRITE_UNAVAILABLE` plus the complete Candidate.
