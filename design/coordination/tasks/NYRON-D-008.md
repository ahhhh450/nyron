# NYRON-D-008 — External Interfaces / Workspace Boundary Design

**Conversation:** `Nyron设计-NYRON-D-008-External-Interfaces-Workspace`
**Status:** DELEGATED / IN PROGRESS
**Mode:** Design only; no implementation; no freeze authority.

## Goal
Produce `Nyron External Interfaces / Workspace Boundary Design Candidate v0.1` defining how Nyron safely maps workspace/filesystem, process, network, browser, provider/model, remote-worker and external-event boundaries onto the generic Capability / Resource / Effect model.

## Minimum Context
Read only:
1. `design/README.md`
2. `design/coordination/STATUS.md`
3. `design/Nyron_Overall_System_Architecture_v0.1.md`
4. `design/Universal_Runtime_Module_Design_Report_v0.1.md`
5. `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
6. `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`

Read Graph/Runtime candidates only when interface semantics require exact references. Do not scan unrelated history.

## Hard Boundary
D-008 consumes D-004. It must NOT redefine CapabilityGrant, Resource/ResourceLease, EffectOperation ownership/lifecycles, Attempt fencing, Accounting, or Graph topology.

## Must Design
1. External World Boundary taxonomy without Kernel/provider hardcoding.
2. Workspace identity vs live Workspace Handle.
3. path containment / symlink / mount boundary requirements.
4. read vs write effect classification.
5. process start, process group, child-process containment, kill/confirm semantics.
6. network destination scope and mediated request boundary.
7. browser session/resource, observation vs consequential action boundary.
8. provider/model adapter boundary, provider sessions, streaming, cancellation, timeout ambiguity.
9. remote worker/job mapping.
10. credential/secret usage boundary at architecture level without designing secret store internals.
11. external event ingress authentication/validation/canonicalization boundary.
12. adapter trust / TCB responsibilities.
13. host isolation claims and profile requirements.
14. durable external IDs / idempotency / lookup requirements.
15. import/export portability implications for environment-bound resources.
16. unsafe raw-access prohibitions.
17. cross-owner interfaces to Runtime, Capability Authority, Resource Manager, Effect Authority, Recovery.
18. `EIW-INV-*` invariants.
19. implementation gates and open questions.

## Product Mapping Requirement
The design must support future Browser, Shell, File, HTTP, Claude/Codex/provider, Tool, Remote Worker and External Event nodes through generic Module + Capability + Resource + Effect mechanisms. None may become a Kernel primitive merely because it is user-visible.

## Output
Return a complete `Nyron External Interfaces / Workspace Boundary Design Candidate v0.1`, including object/boundary model, operation mappings, trust assumptions, crash/UNKNOWN cases, invariants, open questions, findings and implementation gates.

If D-004 cannot express a required external-world safety rule without changing its authority model, raise an explicit `ARCHITECTURE FINDING` and stop at that boundary.

Do not implement code. Do not freeze architecture.