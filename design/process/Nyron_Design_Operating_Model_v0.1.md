# Nyron Design Operating Model v0.1

Status: DRAFT — PROCESS BASELINE IN ACTIVE USE
Purpose: Reusable design, review, coordination, context-management and freeze discipline demonstrated during Nyron v0.1 architecture work.

## 1. Core Principle

GitHub is durable project truth. Chat sessions are temporary working contexts.

Stable architecture conclusions, ownership decisions, contracts, invariants, findings, review evidence, clarifications, amendments, frozen manifests, task state and handoff information belong in the repository.

The project must be reconstructible without one chat window remembering everything.

## 2. Authority Roles

### Lead Design Authority

Owns:
- system-level architecture consistency;
- subsystem decomposition/boundaries;
- canonical Owner arbitration;
- cross-subsystem integration;
- task/review ordering;
- acceptance/rejection of reviewer findings;
- Amendment/superseding-baseline decisions;
- final freeze decisions.

### Specialist Design Session

Produces one bounded Candidate. It does not freeze architecture and may not silently rewrite another Owner/frozen contract.

### Independent Reviewer

Produces review evidence only. Reviewer PASS/FAIL is advisory until Lead validates that the reviewer understood the actual current design and frozen premises.

## 3. Conversation Economy

Do **not** open a new GPT/Claude conversation for every task.

Reuse an existing appropriate window for:
- bounded follow-up;
- clarification;
- targeted re-review;
- small integration work;
- short consistency checks.

Open a dedicated window only when there is a real benefit:
- substantial independent subsystem design;
- context pressure/noise;
- need for a clean independent reasoning context;
- meaningful parallelism.

When a dedicated Nyron design conversation is used, canonical name is the Task ID only:

```text
NYRON-D-XXX
```

## 4. Parallel Design Rules

Parallel work is appropriate when:
- topics own distinct state/object models;
- dependencies are explicit;
- neither task must mutate the other's unresolved Owner/contract;
- shared frozen constraints are already documented.

Block parallelism when:
- tasks compete for the same canonical Owner;
- one cannot be correct until another unresolved semantic decision is made;
- both would amend the same frozen rule;
- a global identity/authority decision is still open.

## 5. Canonical Task State

`design/coordination/STATUS.md` is the single current design-task state table.

Track at minimum:
- Task ID;
- topic;
- status;
- dependency/gate;
- review/freeze state;
- blocker / Architecture Finding.

Update STATUS when work is created, delegated, completed, blocked, reviewed, corrected, frozen or superseded.

Compact STATUS back to current truth after detailed history has been durably recorded elsewhere.

## 6. Context Hygiene

Before a session becomes context-heavy:
1. commit stable conclusions;
2. update STATUS/open questions;
3. write normative clarification/amendment if required;
4. write minimal handoff only if replacing the window;
5. move deep subsystem reasoning out of the main Lead context when useful.

A new session loads only the minimum documents listed in its Task brief.

## 7. Specialist Launch Contract

When a new specialist window is actually necessary, the prompt must explicitly include:
- Nyron project identity;
- repository URL;
- Task ID;
- exact Task file to read first;
- design-only / no-implementation boundary;
- no-freeze authority;
- required repository deliverable;
- commit SHA return requirement;
- Architecture Finding return condition.

Normal completion requires repository write-back when write capability exists.

If unavailable, return:

```text
REPOSITORY_WRITE_UNAVAILABLE
```

plus the complete Candidate.

## 8. Design State Vocabulary

- DRAFT — active design.
- CANDIDATE — coherent proposed design.
- LEAD REVIEW PASS — no Lead-identified blocker.
- INDEPENDENT REVIEW — external review active.
- FREEZE READY — review/integration sufficient for Lead freeze.
- FROZEN — approved implementation contract.
- ARCHITECTURE FINDING OPEN — affected scope blocked.
- SUPERSEDED — replaced by explicit newer baseline.

Task completion and architecture freeze are different facts.

## 9. Freeze Discipline

Default flow:

```text
Candidate
-> Lead integration review
-> independent review when warranted
-> valid findings corrected
-> targeted/full re-review as appropriate
-> explicit Lead Frozen Baseline / manifest
```

Frozen architecture is an implementation contract.

A semantic change to frozen behavior requires:
- explicit Amendment; or
- explicit superseding frozen baseline.

Silent reinterpretation is forbidden.

## 10. Reviewer Premise Validation

A reviewer result is invalid when it materially misstates:
- formal object names;
- ownership;
- frozen lifecycle states;
- Graph/Runtime semantics;
- current amendments/clarifications;
- corrected review premises.

Lead may classify a finding/result as:
- valid blocker;
- non-blocking clarification;
- invalid/misread finding;
- frozen-baseline impact.

Reviewer confidence does not override source text.

## 11. Repository Visibility vs Reviewer Tool Access

Repository visibility and reviewer environment access are different facts.

If a reviewer cannot reach a public repository/file because of browser/network/URL-discovery limitations, record an environment/access limitation rather than claiming the repository is missing.

When direct repository navigation is blocked, use explicit file URLs or a bounded Review Packet.

If evidence is truly insufficient, return:

```text
INSUFFICIENT REVIEW EVIDENCE
```

Never fabricate a PASS/FAIL from unread material.

## 12. Reviewer Tiers — Demonstrated Nyron Policy

Nyron v0.1 demonstrated that different review styles have different evidentiary strength.

### L1 — Consistency / Checklist Review

Best for:
- object/invariant completeness;
- obvious ownership collisions;
- terminology/state consistency;
- known-issue verification;
- bounded document cross-checks.

A lower-cost reviewer such as DeepSeek may be useful here.

**L1 PASS means only: no obvious issue was found under the supplied checklist. It is not, by itself, architecture safety proof or freeze authority.**

Nyron observed concrete cases where an L1 reviewer returned PASS while later adversarial review found real correctness defects or the reviewer materially misread the design.

### L2 — Lead Architecture Review

Lead actively attacks:
- canonical ownership;
- replay/crash ambiguity;
- fencing/revocation races;
- UNKNOWN semantics;
- cross-owner convergence;
- hidden authority escalation;
- implementation-critical open questions.

Lead determines whether a Candidate is freeze-ready, subject to independent evidence appropriate to risk.

### L3 — Independent Adversarial Review

Use for:
- high-risk subsystem boundaries;
- frozen-amendment correctness;
- integrated architecture freeze;
- cases where a clean independent context is valuable.

The reviewer is instructed to search for counterexamples, hidden race windows, replay gaps and cross-owner contradictions rather than merely verify that the document appears internally consistent.

### Freeze Evidence Rule

Do not use:

```text
Lead PASS + L1 PASS -> automatic freeze
```

Instead:

```text
risk-appropriate evidence
+ Lead validation of reviewer premises/findings
+ explicit freeze decision
```

Small low-risk clarifications may be Lead-reviewed only. High-risk authority/fencing/replay changes should normally receive adversarial or targeted independent re-review.

## 13. Review Scope Construction

A review task should state:
- exact Candidate/frozen bundle;
- exact current amendments/clarifications;
- corrected premises from earlier invalid review;
- mandatory attack areas;
- blocking criteria;
- required output format.

Do not FAIL merely because naming, implementation technology, UX, schema layout or optional optimization is deferred.

A blocker should demonstrate correctness impact: Owner conflict/gap, fencing hole, replay ambiguity, guessed UNKNOWN history, unsafe duplicate consequence, authority escalation, cross-owner non-convergence, frozen contradiction or non-reconstructible canonical history.

## 14. Targeted Re-Review Rule

After a bounded correction, reuse the same independent review window when practical and review only:
- whether the finding is actually closed;
- whether the correction introduces a new correctness problem.

Do not automatically repeat a full-system review after every narrow Amendment.

Repeat the full integrated attack only when the correction materially changes broad system semantics.

## 15. Product-to-Architecture Translation

Pattern:

```text
Product requirement
-> identify generic state/capability/interaction needs
-> map to Module / Composite / Graph / Runtime / Capability / Resource / Effect / Event / Human / Accounting / Suspension
-> verify frozen contracts can express it
-> add generic extension only if necessary
-> avoid product-specific Kernel primitives
```

## 16. Product Extension Envelope

For future user-facing Nodes, test whether the foundation can express:
- Input / Output;
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

Detailed Product Node taxonomy need not block System Foundation freeze if this envelope is sufficient and no correctness-critical Owner is missing.

## 17. Documentation Strategy

Create a dedicated document when a topic develops:
- its own object/state model;
- independent invariants;
- independent gate;
- dedicated review needs;
- enough complexity to pollute unrelated context.

Use small normative clarifications for precise pre-freeze integration tightening.

Use Amendments when a frozen semantic rule changes or an explicit correction must become authoritative over a frozen baseline.

## 18. Frozen Baseline Manifest Pattern

A Frozen Baseline manifest should identify:
- baseline/version/status;
- exact constituent paths;
- immutable blob/commit refs where practical;
- included clarifications/amendments;
- review evidence;
- Lead freeze decision;
- change-control rule.

The manifest is authoritative even if a source Candidate header still says CANDIDATE/DRAFT.

## 19. Repository as Design Memory

Repository design memory should contain:
- Overall baseline;
- subsystem designs;
- contracts/invariants;
- amendments/clarifications;
- Architecture Findings;
- Task briefs;
- STATUS;
- review outcomes;
- frozen manifests;
- implementation gates;
- process rules;
- Lead queue when useful.

## 20. Continuous Execution Rule

When Lead states a concrete next action and it is executable now, perform it in the same turn.

A commit/status update is not a stopping condition.

Stop only when:
- a genuine user/architecture decision is required;
- a hard external dependency is unavailable;
- an Architecture Finding blocks continuation;
- all currently executable work is complete.

## 21. Client-Project Reuse Goal

Reusable workflow:

1. Product intent capture
2. System boundary definition
3. Architecture decomposition
4. Parallel bounded subsystem design
5. Contract/invariant freeze preparation
6. Risk-appropriate independent review
7. Explicit baseline freeze
8. Implementation gate opening
9. Multi-agent implementation coordination
10. Review/re-review/integration testing
11. Design-memory consolidation
12. Project handoff/maintenance baseline

## 22. Lessons-Learned Update Rule

Record process lessons only when demonstrated in real work or when a recurring failure exposes a missing rule.

Do not record incidental conversation details.

## 23. Current Demonstrated Lessons

1. GitHub carries durable design memory; chats carry active reasoning context.
2. Keep the main Lead window focused on ownership, integration, freeze and coordination.
3. Do not create a new conversation for every task; create one only when it provides real context/independence/parallelism benefit.
4. Specialists propose; Lead integrates/freezes.
5. New dedicated windows require repository URL + exact Task path; never assume context.
6. Require repository write-back/commit SHA for normal specialist completion.
7. Maintain one compact STATUS table for current truth.
8. Reviewer PASS is invalid when material premises are misread.
9. A checklist/consistency PASS is weaker evidence than adversarial review and must not become automatic freeze authority.
10. Deep adversarial review can find correctness defects that locally consistent documents and L1 reviews miss, especially race windows and cross-owner reference/resolution gaps.
11. Distinguish repository visibility from reviewer tool/network/URL-discovery access.
12. Explicit Raw URLs/Review Packets are useful when reviewer navigation is blocked.
13. Frozen semantic changes require Amendment/superseding baseline, not friendly reinterpretation.
14. Small corrections should receive targeted re-review rather than automatically re-running a full system review.
15. Exact manifests prevent later source edits from silently changing what was frozen.
16. Product Nodes remain product abstractions over generic architecture mechanisms.
17. Main coordination continues executing available queue items; administrative checkpoints are not automatic stopping points.
18. Architecture freeze should open an explicit implementation gate and define when implementation must raise a new Architecture Finding.
