# Nyron Design Operating Model v0.1

Status: DRAFT
Purpose: Capture reusable design methods, multi-session coordination patterns, context-management rules, review/freeze discipline, and workflow lessons learned during Nyron design. This document evolves only from practices demonstrated in real project work.

## 1. Core Principle

GitHub is the durable project truth. Chat sessions are temporary working contexts.

Stable design conclusions, task state, contracts, invariants, architecture findings, review results, clarifications, freeze manifests, and handoff information should be committed to repository documents before a session becomes too large or is retired.

The design process must not depend on one chat window remembering everything.

## 2. Roles

### Lead Design Authority

Owns:
- system-level architecture consistency;
- subsystem boundaries;
- contract/invariant integration;
- design arbitration;
- task decomposition and dependency ordering;
- review acceptance/rejection;
- frozen-baseline amendments;
- final freeze decisions.

### Dedicated Design Session

Owns one bounded design topic only. It may analyze and produce a Candidate, but cannot freeze architecture independently.

A specialist must not silently rewrite another task's canonical Owner or frozen contract. Cross-boundary conflicts return to Lead as explicit Architecture Findings.

### Independent Reviewer

Reviews a bounded candidate or integrated architecture from a cleaner context.

Reviewer output is advisory evidence, not design authority. A reviewer cannot freeze, amend or silently rewrite the baseline.

## 3. Multi-Session Coordination

Every substantial design session should have:
- a unique Task ID;
- a conversation name equal to the Task ID only;
- one exact design target;
- explicit dependencies;
- frozen constraints that must not change;
- a defined repository deliverable;
- stop/escalation conditions;
- a return path to Lead Design Authority.

Conversation naming rule:

```text
NYRON-D-XXX
```

Examples:
- `NYRON-D-003`
- `NYRON-D-005`
- `NYRON-D-010`

The main coordination/design-authority conversation is `NYRON-D-001`.

Do not add topic suffixes or decorative prefixes to canonical conversation names.

## 4. Parallel Design Rules

Parallel sessions are allowed when ownership boundaries are sufficiently independent.

Parallel work is appropriate when:
- topics have distinct state/object models;
- neither task must mutate the other's unresolved canonical contract;
- dependencies are explicit;
- shared global constraints are already documented;
- integration review can resolve remaining assumptions.

Parallel work should be blocked when:
- two tasks define the same canonical Owner;
- one task requires unresolved semantics from another before it can be correct;
- both tasks would amend the same frozen contract;
- a global ownership/identity decision is still unresolved.

When two parallel tasks touch the same boundary from different sides, Lead should define which side owns the semantic decision and which side only consumes the contract.

## 5. Task Coordination Record

`design/coordination/STATUS.md` is the single current design-task status table.

For each task it should track at minimum:
- Task ID;
- topic;
- dependency;
- status;
- current gate;
- expected repository deliverable;
- review/freeze state;
- blockers / Architecture Findings.

The main design conversation updates STATUS when tasks are created, delegated, completed, blocked, superseded, integrated, reviewed or frozen.

Process history does not belong indefinitely in STATUS. Once a state transition is durably captured elsewhere, STATUS should be compacted back to current truth.

## 6. Context Hygiene

Do not use one conversation as an infinite archive.

Before a session becomes context-heavy:
1. commit stable conclusions to GitHub;
2. update task state and open questions;
3. write any normative clarification/amendment needed for later reconstruction;
4. produce a minimal handoff summary when replacing the window;
5. move deep subsystem reasoning out of the main coordination session.

A new session loads only the minimum required documents listed by its Task brief.

Do not copy entire historical chats into a new session unless absolutely necessary.

## 7. Specialist Launch Contract

A new specialist window has no obligation to infer project context from prior conversations.

Every launch prompt MUST explicitly include:
- Nyron project identity;
- repository URL;
- Task ID;
- instruction to rename the current conversation to the Task ID;
- exact Task-brief repository path to read first;
- design-only / no-implementation boundary;
- no-freeze authority boundary;
- mandatory repository write-back requirement;
- commit SHA return requirement;
- Architecture Finding return condition.

Canonical minimal launch form:

```text
请将当前对话名称修改为：NYRON-D-XXX

你现在负责 Nyron 项目的独立设计专题 NYRON-D-XXX。
仓库：https://github.com/ahhhh450/nyron

请首先读取：
design/coordination/tasks/NYRON-D-XXX.md

然后严格按照 Task 文件规定的最小上下文、设计边界和输出要求完成任务。
本窗口只做设计，不实现代码，不拥有冻结权。
最终必须将完整 Candidate 写入 Task 指定 GitHub 路径并 commit。
最后只返回：结果状态、文件路径、commit SHA、Architecture Finding（如有）。
```

If repository write capability is unavailable, the specialist must return:

```text
REPOSITORY_WRITE_UNAVAILABLE
```

plus the complete Candidate so Lead can integrate it. Chat-only output is not considered normal task completion when repository write capability exists.

## 8. Design State Vocabulary

- DRAFT — active design, not implementation authority.
- CANDIDATE — coherent proposed subsystem/system design.
- LEAD REVIEW PASS — Lead integration found no blocking contradiction.
- INDEPENDENT REVIEW — bounded external review active.
- FREEZE READY — review/integration gates are complete enough for Lead freeze consolidation.
- FROZEN — approved implementation baseline.
- ARCHITECTURE FINDING OPEN — semantic conflict blocks affected scope.
- SUPERSEDED — replaced by an explicit newer baseline.

Task status and architecture-document status should not be conflated. A task can be complete while its Candidate remains unfrozen.

## 9. Freeze Discipline

A dedicated session or reviewer cannot declare a system-level baseline frozen.

Default flow:

```text
Candidate
-> Lead integration review
-> independent review when warranted
-> valid findings resolved
-> Lead consolidation
-> explicit Frozen Baseline / manifest commit
```

Frozen design is an implementation contract, not an implementation suggestion.

If a frozen semantic lifecycle/state/invariant changes, the change MUST occur through:
- an explicit Amendment identifying the affected frozen contract; or
- an explicit superseding frozen baseline.

Silent reinterpretation is forbidden even when the new design appears "compatible".

## 10. Independent Review Acceptance Rule

Independent review is useful only when the reviewer actually understood the reviewed design.

A returned `PASS` is invalid if the reviewer materially misstates:
- formal object names;
- ownership;
- frozen lifecycle states;
- Graph/Runtime semantics;
- accepted amendments;
- corrected review premises.

Lead MUST reject such a PASS as `review-invalid` and request corrected bounded re-review.

Reviewer output is evidence, not authority.

## 11. Repository Visibility vs Reviewer Environment Access

Repository visibility and reviewer network/tool access are different facts.

A public GitHub repository does not prove a given reviewer runtime can access GitHub.

When a reviewer reports missing repository files, distinguish:

1. repository does not exist / is private / path is wrong;
2. reviewer environment has no network/browser/Git capability;
3. reviewer failed to clone/fetch/read the repository.

A reviewer without network access should report an environment limitation such as:

```text
ENVIRONMENT_NETWORK_UNAVAILABLE
```

It must not claim the repository itself is unavailable without evidence.

When repository access is genuinely unavailable to the reviewer, Lead may use **Review Packet mode**: provide only the minimum frozen baseline/candidate/clarifications/questions required for that review. The reviewer must return `INSUFFICIENT REVIEW EVIDENCE` rather than invent missing facts.

## 12. When to Use Independent Review

Independent review is most valuable after a coherent contract boundary exists, not during early brainstorming.

Good review points:
- complete system-foundation candidate;
- subsystem object/state model + invariant set;
- cross-owner contract;
- amendment to frozen baseline;
- gate before implementation begins.

Avoid spending review effort on unstable fragments still being actively reshaped.

Bounded subsystem consistency review should normally use a lower-cost independent reviewer.
Broad integrated adversarial review should be reserved for the integrated architecture where cross-subsystem assumptions can be challenged together.

## 13. Review Scope Construction

A bounded review should state:
- exact candidate;
- exact frozen baselines/amendments;
- corrected premises from earlier invalid reviews;
- blocking criteria;
- non-blocking clarification category;
- required output format.

Reviewers should not FAIL merely because they can imagine a more elaborate design. A blocking finding should identify a correctness, ownership, replay, fencing, authority, frozen-baseline or convergence defect.

## 14. Product-to-Architecture Translation Pattern

The product owner may primarily describe desired user-facing nodes, workflows, behaviors and future extension needs.

Lead translates them into architecture without requiring the product owner to understand low-level mechanics.

Pattern:

```text
Product requirement
-> identify generic capability/state/interaction needs
-> map to Module / Composite / Graph / Runtime / Capability / Resource / Effect / State / Event / Human Interaction / Accounting / Suspension
-> verify frozen contracts can express it
-> add a generic extension point only if necessary
-> avoid product-specific Kernel primitives
```

## 15. Product Extension Envelope

For each future user-facing Node, evaluate whether the architecture can express:
- Input;
- Output;
- Configuration;
- Capability;
- Resource;
- Effect;
- State;
- Event;
- Human Interaction;
- Accounting;
- Suspension / Resume;
- Composite composition.

Not every Node needs every dimension. The purpose is to avoid sealing off future extension paths.

Detailed product-node taxonomy does not have to block System Foundation freeze if this envelope remains sufficient and no unresolved canonical Owner is required for correctness.

## 16. Documentation Strategy

Separate a topic into its own document when it develops:
- its own object/state model;
- independent invariants;
- independent implementation gate;
- dedicated review needs;
- enough complexity to pollute unrelated context.

Cross-domain rules should be referenced rather than duplicated where practical.

Use small normative clarification documents when a Candidate is sound but requires precise integration tightening. Do not rewrite a large Candidate merely to fix a small cross-subsystem contract unless consolidation is required for freeze.

## 17. Frozen Baseline Manifest Pattern

When a Candidate + accepted clarification together form the frozen architecture, Lead may freeze them through an explicit manifest/baseline document that pins the exact authoritative content identities.

A manifest should identify:
- baseline name/version;
- exact constituent paths;
- exact immutable content/commit/blob references when available;
- accepted clarifications/amendments;
- review evidence;
- Lead freeze decision.

This prevents later edits to a Candidate path from silently changing what was actually frozen.

## 18. Repository as Design Memory

The repository should progressively contain:
- overall architecture baseline;
- focused subsystem designs;
- contracts;
- invariants;
- amendments;
- clarifications;
- architecture findings;
- task briefs;
- coordination status;
- review outcomes;
- frozen manifests;
- implementation gates;
- design operating model;
- Lead active queue where useful.

This reduces dependence on long-lived model memory or one specific chat session.

## 19. Lead Active Queue and Continuous Execution Rule

`design/coordination/LEAD_ACTIVE_QUEUE.md` may be used as the main design window's operational scratch queue.

It is not canonical architecture truth; STATUS remains the authoritative task-state table.

When Lead states a concrete next action and the action is currently executable, Lead should execute it in the same turn instead of stopping after announcing it.

Lead should stop only when:
- user/Lead architecture decision is genuinely required;
- a hard dependency is unavailable;
- an Architecture Finding blocks safe continuation;
- all currently executable work for the wave is complete.

A commit/status update is not by itself a valid stopping condition if another unblocked queue item is immediately executable.

This rule was added after repeated coordination stalls where the design process stopped at an administrative checkpoint despite available work.

## 20. Client-Project Reuse Goal

The Nyron process should eventually be abstracted into a reusable customer-facing development workflow:

1. Product intent capture
2. System boundary definition
3. Architecture decomposition
4. Parallel subsystem design
5. Contract / invariant freeze
6. Independent review
7. Implementation gate opening
8. Multi-agent implementation coordination
9. Review / re-review
10. Integration / fault testing / release
11. Design-memory consolidation
12. Project handoff / maintenance baseline

The reusable workflow separates customer-facing requirements from architecture complexity while preserving traceable decisions and clean agent handoffs.

## 21. Lessons-Learned Update Rule

Update this document only when a process lesson has been demonstrated in practice or a recurring coordination failure reveals a missing rule.

Do not record every incidental conversation detail.

Good candidates:
- a multi-session pattern that worked reliably;
- a context-cleaning technique;
- a failed delegation pattern and corrective rule;
- a review gate that caught a real architecture defect;
- a freeze/amendment pattern that prevented ambiguity;
- a task/status convention that prevented parallel conflicts.

## 22. Current Demonstrated Lessons

1. GitHub should carry durable design memory; chats should carry only active reasoning context.
2. Keep the main design session focused on ownership, integration, freeze and task coordination.
3. Move deep subsystem state-machine work into dedicated sessions.
4. Give every specialist one stable Task ID and name the conversation exactly that Task ID.
5. New windows need explicit repository URL + Task path; never assume they know where project files live.
6. Require specialist Candidates to be committed to the repository and return commit SHA.
7. Maintain one compact repository-backed STATUS table for current design truth.
8. Let specialists propose; let Lead integrate/freeze.
9. Reviewer PASS is invalid when the reviewer materially misread the design.
10. Distinguish public repository visibility from reviewer environment network/tool access.
11. Use Review Packet mode when a reviewer cannot directly access the repository.
12. Frozen semantic changes require explicit Amendment/superseding baseline, not friendly reinterpretation.
13. Small cross-subsystem precision issues can be captured as normative Lead clarifications before freeze.
14. Exact frozen manifests are useful when Candidate + clarification together define the actual baseline.
15. User-facing Nodes remain product abstractions rather than automatic Runtime/Kernel primitives.
16. Preserve future extensibility through generic capability/resource/effect/state/event envelopes.
17. Main coordination should continue executing available queue items; administrative checkpoints are not automatic stopping points.
18. Evolve reusable methodology only from tested project behavior, not theory alone.
