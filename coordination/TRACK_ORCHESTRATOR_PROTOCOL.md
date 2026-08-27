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

## 6. Agent Availability Is a Live Coordination Constraint

Track Orchestrators MUST read current Agent availability from `coordination/STATUS.md` before assigning implementation, fix, review or re-review work.

Current availability declarations in STATUS override default model preferences in older prompts or generic orchestration guidance.

If an Agent is marked unavailable:

- do not create a new assignment to that Agent;
- do not instruct the Operator to open a new window for that Agent;
- do not wait for that Agent if another authorized available Agent can safely perform the work;
- re-route according to risk, independence and capability requirements;
- if no available Agent can satisfy a mandatory independent-review or specialist requirement, record a blocker rather than weakening the requirement.

Availability is operational state, not an architecture rule. It may be changed by a later Development Director coordination revision.

## 7. Routing Is Part of Orchestration Work

Creating a Task file without assigning / routing it is not sufficient when the directive requires production to begin.

The Track Orchestrator must identify:

```text
Task ID
Assigned Agent
Execution / Review purpose
Dependency basis
Expected Repository result path
```

### 7.1 Mandatory Dispatch Reply Format

When a Track Orchestrator gives the Operator a copyable instruction for an Execution Agent, reviewer or other Track-scoped Agent window, the reply MUST use a Track dispatch block beginning with a human-facing dispatch label:

```text
[TRACK_A_TASK_001]
Repository:

`https://github.com/ahhhh450/nyron`

你的上级是：

`Development Director / Global Development Coordination Authority`

你不是 Development Director，也不是默认 Implementation Agent。

## Repository Truth
...
```

Use the actual Track letter and a Track-local monotonically increasing dispatch sequence, for example:

```text
[TRACK_A_TASK_001]
[TRACK_A_TASK_002]
[TRACK_B_TASK_001]
[TRACK_C_TASK_001]
```

The dispatch label is **chat/routing metadata only**. It is NOT the formal Repository Task ID and MUST NOT replace or alias the canonical `NYRON-T-...` Task ID.

Every dispatch block must include the formal Repository Task ID explicitly when one exists.

The dispatch sequence is Track-local and does not participate in the global `NYRON-T-*` namespace, so Track A/B/C may each have their own `_001`, `_002`, etc.

### 7.2 Required Dispatch Block Content

A production/review dispatch block must be self-contained and normally include, in this order:

1. `[TRACK_<LETTER>_TASK_<NNN>]`
2. `Repository:` and canonical repository URL
3. superior authority: `Development Director / Global Development Coordination Authority`
4. role boundary: recipient is not Development Director and not automatically an Orchestrator unless explicitly assigned that role
5. `## Repository Truth`
6. exact formal Task ID and Task file path
7. Required Reading
8. exact Coordination Epoch / Revision or instruction to re-read current STATUS under the Task stale policy
9. exact dependency / reviewed SHA basis where applicable
10. objective and authorized scope
11. explicit Out of Scope / authority boundaries
12. validation requirements
13. Result / Review output path and format
14. remote-delivery / exact-SHA evidence requirements when applicable
15. completion chat behavior (`TASK DONE` / `TASK BLOCKED`) after Repository evidence is written

Do not require the Operator to reconstruct missing Task context from previous chat messages.

A dispatch block may state whether the Operator should use a new or existing window, but the copyable block itself remains the authoritative chat instruction format.

## 8. Chat Completion Semantics

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

## 9. Review Chain

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

## 10. Authority Boundary

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
