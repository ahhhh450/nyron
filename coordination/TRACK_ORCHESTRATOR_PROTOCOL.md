# Track Orchestrator Protocol

Status: `ACTIVE COORDINATION PROCESS RULE`
Authority: `Development Director / Global Development Coordination Authority`
Date: `2026-08-27`

## 1. Purpose

This file defines the mandatory behavior of Track Orchestrators under the three-level model:

```text
Development Director
→ Track Orchestrator
→ Execution Agent
```

A Track Orchestrator is a persistent coordination role. It is not an Execution Agent and must not treat repository reading, readiness analysis, or planning alone as completion of a production-activation directive.

Repository files are authoritative. Chat is trigger / notification / concise status only.

## 2. Mandatory Reading

Every Track Orchestrator must read at minimum:

1. `AGENTS.md`
2. `ORCHESTRATOR.md`
3. `coordination/STATUS.md`
4. `coordination/TASK_PROTOCOL.md`
5. `coordination/OUTPUT_FORMAT.md`
6. `coordination/REVIEW_PROTOCOL.md`
7. `coordination/WORKFLOW.md`
8. `coordination/TRACK_ORCHESTRATOR_PROTOCOL.md`
9. the active Track Board / Plan
10. the Track's frozen architecture authority

## 3. Track Activation Completion Rule

When the Development Director authorizes a Track Orchestrator to activate a production Track, the activation directive is **not complete** merely because the Orchestrator:

- read Repository Truth;
- completed a readiness check;
- identified a possible first slice;
- stated that the Track is ready;
- returned `TASK DONE` in chat.

A readiness assessment by itself is never a production activation result.

### 3.1 Readiness PASS

If the Track readiness check is `PASS`, the Track Orchestrator MUST, in the same activation flow:

1. define the smallest valid first production slice within frozen Track authority;
2. allocate a formal Task ID;
3. create `coordination/tasks/<TaskID>.md` conforming to `coordination/TASK_PROTOCOL.md`;
4. include mandatory protocol reading, exact dependency basis, Scope / Out of Scope, validation, deliverables and completion criteria;
5. assign an appropriate Execution Agent;
6. route the Task to that Execution Agent / execution lane;
7. verify the formal Task file is remotely readable;
8. only then report concise activation status.

For an activation directive whose objective is to start production, `TASK DONE` is invalid unless at least one formal production Task has actually been created and routed.

### 3.2 Readiness BLOCKED

If readiness is not satisfied, the Track Orchestrator MUST NOT create speculative production work.

It MUST instead:

1. record the exact blocker in a Track-scoped Repository checkpoint or other Director-approved durable coordination artifact;
2. identify whether the blocker is dependency, write-surface, review-capacity, integration-capacity, Contract, Architecture or Security;
3. return `TASK BLOCKED` in chat;
4. escalate to Development Director when cross-Track or global coordination is required;
5. use `ESCALATION_REQUIRED` for frozen-semantics / Owner-boundary / undefined cross-owner Contract issues.

A blocked Track must never return `TASK DONE` merely because the readiness check itself finished.

## 4. Task ID Allocation Under Parallel Tracks

Track Orchestrators may allocate formal Task IDs only within their authorized Track scope.

Because multiple Track Orchestrators may operate concurrently, allocation MUST be collision-safe:

1. read the latest Repository task namespace immediately before allocation;
2. choose the next available ID according to the current project convention;
3. create the Task file using an atomic create operation; never overwrite an existing Task file;
4. if creation fails because the ID/path already exists, treat this as an allocation race, re-read Repository Truth, choose the next available ID and retry;
5. never delete, replace or repurpose another Track's Task to obtain an ID;
6. never let an Execution Agent allocate or derive a formal Task ID.

Task identity collision is a coordination event, not permission to use last-writer-wins.

## 5. Formal Task Requirements

Every Track-local formal Task must comply with `coordination/TASK_PROTOCOL.md` and include at minimum:

- Task ID
- Type
- Risk
- Assigned Agent
- Status
- Priority
- Orchestrator
- Track Orchestrator
- Coordination Epoch
- Based On Coordination Revision
- Stale Policy
- Parent Task
- Depends On
- Reviews Task when applicable
- Objective
- Required Reading
- Scope
- Out of Scope
- Constraints
- Validation
- Deliverables
- Output Format
- Completion Criteria

Unlisted Scope is unauthorized by default.

## 6. Routing Is Part of Orchestration Work

Creating a Task file without assigning / routing it is not sufficient when the directive requires production to begin.

The Track Orchestrator must identify:

```text
Task ID
Assigned Agent
Execution / Review purpose
Dependency basis
Expected Repository result path
```

If the Operator must open a new Execution Agent window, the Track Orchestrator must explicitly return:

```text
【新开窗口｜模型｜用途】
```

with one complete copyable instruction.

If an existing window should be reused:

```text
【发给已有窗口｜模型｜用途】
```

with one complete copyable instruction.

## 7. Chat Completion Semantics

`TASK DONE` is reserved for a directive whose required durable Repository artifacts and routing actions are actually complete.

Track Orchestrators MUST NOT use `TASK DONE` for:

- repository reading only;
- readiness analysis only;
- planning only;
- a recommendation to create a Task later;
- a production activation directive where no formal Task was created;
- a blocked activation.

For blocked activation use:

```text
TASK BLOCKED
```

For ordinary Director reporting, use the Track report format instead of `TASK DONE`:

```text
Track:
Current Gate:
Stable Candidate SHA:
Review State:
Open Findings:
Blockers:
Next Milestone:
```

## 8. Review Chain

For high-risk production:

```text
Implementation Agent != Independent Reviewer
```

Track Orchestrator is responsible for routing:

```text
Implementation
→ Result
→ Independent Review
→ Fix if required
→ Targeted Re-Review if required
→ Track Stable Candidate
```

Reviewer output does not automatically create global acceptance.

## 9. Authority Boundary

Track Orchestrators may create Track-local implementation / fix / review / re-review Tasks and manage Track-local stable candidates.

They may not:

- modify Frozen Architecture;
- change Owner boundaries;
- redefine other Track canonical semantics;
- declare Global Accepted;
- update Last Accepted Production;
- bypass required independent review;
- invent unfrozen cross-owner Contracts.

Such cases require escalation to the Development Director, and Architecture Findings must be routed to the Lead Design Authority.
