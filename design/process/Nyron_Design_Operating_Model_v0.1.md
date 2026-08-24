# Nyron Design Operating Model v0.1

Status: DRAFT
Purpose: Capture reusable design methods, multi-session coordination patterns, context-management rules, review/freeze discipline, and workflow lessons learned during Nyron design. This document is intended to evolve from project-specific practice into a reusable client-project design workflow.

## 1. Core Principle

GitHub is the durable project truth. Chat sessions are temporary working contexts.

Stable design conclusions, task state, contracts, invariants, architecture findings, review results, and handoff information should be committed to repository documents before a session becomes too large or is retired.

## 2. Roles

### Lead Design Authority

Owns system-level architecture consistency, subsystem boundaries, contracts, design arbitration, integration review, freeze decisions, and design-task coordination.

### Dedicated Design Session

Owns one bounded design topic only. It may analyze and propose a candidate design, but cannot freeze architecture independently.

### Independent Reviewer

Reviews a candidate or frozen-boundary change from a clean context and returns blocking issues, risks, or approval recommendation. It does not silently rewrite the design authority model.

## 3. Multi-Session Coordination

Every substantial design session should have:

- a unique Task ID;
- a fixed conversation name;
- one exact design target;
- explicit dependencies;
- frozen constraints that must not be changed;
- a defined deliverable;
- stop/escalation conditions;
- a return path to the Lead Design Authority.

Recommended conversation naming:

`Nyron设计-[Task ID]-[Topic]`

The main coordination conversation remains:

`Nyron设计-总设计调度`

## 4. Parallel Design Rules

Parallel sessions are allowed when their ownership boundaries are sufficiently independent.

Parallel work is appropriate when:

- the topics have distinct state/object models;
- neither task needs to mutate the other's canonical contract while in progress;
- dependencies are explicit;
- shared global constraints are already documented;
- integration review can resolve remaining cross-topic assumptions.

Parallel work should be blocked when:

- two tasks are defining the same canonical owner;
- one task depends on unresolved semantics from another;
- both tasks are changing the same frozen contract;
- a global architecture decision has not yet been made.

## 5. Task Coordination Record

`design/coordination/STATUS.md` is the single current design-task status table.

For each task it should track at minimum:

- Task ID
- conversation name
- topic
- owner/session
- dependencies
- status
- design gate
- expected deliverable
- blockers / architecture findings
- integration/review state

The main design conversation must update this record when tasks are created, completed, blocked, split, superseded, or moved into review.

## 6. Context Hygiene

Do not use one conversation as an infinite archive.

Before a session becomes context-heavy:

1. Commit stable conclusions to GitHub.
2. Update task status and open questions.
3. Produce a minimal handoff summary.
4. Move detailed local reasoning out of the main coordination session.
5. Open a new dedicated session when the topic has its own state model, contract family, or sustained reasoning burden.

A new session should load only the minimum required documents.

Do not copy complete historical conversations into a new session unless absolutely necessary.

## 7. Session Handoff Contract

Every handoff prompt should contain:

- Role
- Task ID
- Conversation name
- Exact design target
- Repository path
- Minimum required documents
- Frozen constraints
- In-scope questions
- Out-of-scope topics
- Expected deliverable
- Architecture Finding stop condition
- Return format

The target session should not independently expand scope unless it raises the expansion as an explicit dependency or finding.

## 8. Design State Vocabulary

- DRAFT — active design, not implementation authority.
- IN REVIEW — candidate design under formal review.
- FROZEN — approved implementation baseline.
- ARCHITECTURE FINDING OPEN — a required semantic change or unresolved conflict blocks the affected scope.
- SUPERSEDED — replaced by a newer explicit baseline.

## 9. Freeze Discipline

A dedicated session cannot declare a system-level design frozen.

Freeze flow:

Candidate Design
→ Lead Design Authority integration review
→ independent review when warranted
→ blocking issues resolved
→ explicit freeze decision
→ repository status updated

Frozen design is an implementation contract, not an implementation suggestion.

## 10. When to Use Independent Review

Independent review is most valuable after a coherent contract boundary exists, not during early brainstorming.

Good review points include:

- a complete system-foundation candidate;
- a subsystem state machine and invariant set;
- a cross-owner contract;
- a proposed change to a frozen baseline;
- a design gate before implementation begins.

Avoid spending review effort on unstable fragments that are still being actively reshaped.

## 11. Product-to-Architecture Translation Pattern

The product owner may primarily describe desired user-facing nodes, workflows, behaviors, and future extension needs.

The Lead Design Authority translates those requests into architecture without requiring the product owner to understand low-level mechanics.

Pattern:

Product requirement
→ identify required generic capabilities
→ map to Module / Composite / Graph / Runtime / Capability / Resource / State / Event / Human Interaction / Accounting / Suspension
→ verify existing contracts can express it
→ add generic extension point only if necessary
→ avoid creating product-specific Kernel primitives

## 12. Product Extension Envelope

For each future user-facing node, evaluate whether the architecture can express:

- Input
- Output
- Configuration
- Capability
- Resource
- State
- Event
- Human Interaction
- Accounting
- Suspension / Resume
- Composite composition

Not every node needs every dimension. The purpose is to avoid accidentally sealing off future extension paths.

## 13. Documentation Strategy

Separate documents when a topic develops:

- its own object/state model;
- independent invariants;
- independent implementation gate;
- dedicated review needs;
- enough complexity to pollute unrelated design context.

Cross-domain rules should be referenced, not duplicated where possible.

## 14. Repository as Design Memory

The repository should progressively contain:

- overall architecture baseline;
- focused subsystem designs;
- contracts;
- invariants;
- architecture decisions;
- architecture findings;
- coordination status;
- review outcomes;
- implementation gates;
- design operating model.

This reduces dependence on long-lived model memory or one specific chat session.

## 15. Client-Project Reuse Goal

The Nyron process should eventually be abstracted into a reusable customer-facing development workflow with phases such as:

1. Product intent capture
2. System boundary definition
3. Architecture decomposition
4. Parallel subsystem design
5. Contract / invariant freeze
6. Independent review
7. Implementation gate opening
8. Multi-agent implementation coordination
9. Review / re-review
10. Integration / test / release
11. Design-memory consolidation
12. Project handoff / maintenance baseline

The reusable workflow must separate customer-facing requirements from internal architecture complexity while preserving traceable decisions and clean agent handoffs.

## 16. Lessons-Learned Update Rule

This document should be updated only when a design-process lesson has been demonstrated in practice or when a recurring coordination failure reveals a missing rule.

Do not record every incidental conversation detail.

Good candidates for inclusion:

- a multi-session pattern that worked reliably;
- a context-cleaning technique that reduced ambiguity;
- a failed delegation pattern and the corrective rule;
- a review gate that caught a real architecture defect;
- a reusable method for translating product-node requests into generic architecture;
- a task/status convention that prevented parallel-work conflicts.

## 17. Current Initial Lessons

1. Keep the main design session focused on global decisions and coordination.
2. Move deep subsystem state-machine work into dedicated sessions.
3. Give every session a stable Task ID and conversation name.
4. Maintain one repository-backed status table for all design tasks.
5. Commit stable design before replacing or cleaning a context window.
6. Let specialist sessions propose; let the Lead Design Authority integrate and freeze.
7. Use independent review after a coherent candidate exists.
8. Treat user-facing nodes as product abstractions, not automatic Runtime or Kernel primitives.
9. Preserve future node extensibility through generic capability/resource/state/event envelopes.
10. Evolve project-specific practice into a reusable customer-project workflow only from tested patterns, not theory alone.
