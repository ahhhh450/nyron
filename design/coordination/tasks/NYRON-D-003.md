# NYRON-D-003 — Runtime Orchestration Design

**Conversation:** `Nyron设计-NYRON-D-003-Runtime-Orchestration`
**Status:** DELEGATED / IN PROGRESS
**Mode:** Design only; no implementation; no freeze authority.

## Goal
Produce `Nyron Runtime Orchestration Design Candidate v0.1` covering Runtime-owned execution semantics above the frozen Module contract and review-pending Graph candidate.

## Minimum Context
Read only:
1. `design/README.md`
2. `design/coordination/STATUS.md`
3. `design/Nyron_Overall_System_Architecture_v0.1.md`
4. `design/Universal_Runtime_Module_Design_Report_v0.1.md`
5. `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
6. `design/Nyron_Graph_Composite_Design_Candidate_v0.1.md`
7. `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md` only where Attempt replacement/fencing interfaces are needed.

Do not scan unrelated history.

## Frozen / Candidate Boundaries
Must preserve:
- Packet → Delivery → Activation → Run / Attempt.
- Module never creates Activation, schedules downstream Modules, owns retry policy, or decides workflow convergence.
- GraphRevision is immutable execution definition; Runtime never resolves `latest/current` and never re-flattens Composite.
- FEEDBACK is only an intentional-cycle definition marker; it adds no special runtime semantics.
- Delivery binding/readiness semantics from the frozen Module baseline remain authoritative.
- Commit Fencing and Effect Fencing both remain mandatory.
- D-004 ownership is consumed, not redesigned: Runtime does not own CapabilityGrant, Resource/Lease, or EffectOperation.
- Amendment 001 PREPARED semantics must remain compatible.

## Must Design
1. Runtime canonical ownership map.
2. Workflow execution identity / execution admission.
3. Packet projection to Delivery.
4. Delivery lifecycle and deterministic projection/deduplication.
5. Activation readiness evaluation and atomic consumptive binding.
6. Run / Attempt identity and state machine.
7. retry vs replacement vs resume distinctions.
8. Attempt replacement and current-attempt fencing.
9. cancellation / termination semantics.
10. Suspension / Subscription / EventDelivery / resume integration.
11. FEEDBACK-cycle execution without loop primitive or Activation reuse.
12. branch/join behavior as ordinary graph/module semantics.
13. convergence / workflow terminal-state criteria without product taxonomy.
14. crash recovery and replay of Runtime-owned state.
15. cross-owner Commands/Events to Capability, Resource, Effect, Accounting, Recovery.
16. deterministic ordering rules and what is explicitly non-semantic.
17. Runtime derived state vs canonical state.
18. `RT-INV-*` invariants.
19. implementation gates and unresolved integration questions.

## Hard Ownership Boundary
D-003 owns Runtime Attempt/retry/replacement/cancellation lifecycle.
It must NOT define Recovery policy for UNKNOWN, Accounting settlement, Capability policy, Resource lifecycle, EffectOperation lifecycle, Graph topology, or product Node taxonomy.

If a required Runtime rule contradicts D-002, D-004, Amendment 001, or the frozen Module baseline, stop at that boundary and raise an explicit `ARCHITECTURE FINDING`.

## Repository Deliverable — REQUIRED
The completed candidate MUST be written to the repository at:

`design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`

Requirements:
- write the complete candidate, not a summary;
- do not modify frozen baselines or other subsystem candidates;
- commit the new/updated candidate to the repository;
- after the write, return the repository path and commit SHA to the orchestrator;
- the task is not considered complete merely because the candidate was printed in chat.

If repository write capability is unavailable, do not claim completion. Return:

`REPOSITORY_WRITE_UNAVAILABLE`

followed by the complete candidate so the Lead Design Authority can integrate it.

## Output
Return a complete `Nyron Runtime Orchestration Design Candidate v0.1` with:
- object/state model;
- ownership and cross-owner contracts;
- lifecycle semantics;
- crash/replay semantics;
- invariants;
- open questions;
- findings;
- recommended implementation gates.

Do not implement code. Do not freeze architecture.