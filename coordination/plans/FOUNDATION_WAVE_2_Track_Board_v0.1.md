# Nyron Foundation Wave 2 Track Board v0.1

Status: `ACTIVE COORDINATION BOARD / NOT ARCHITECTURE`
Authority: `Development Director / Global Development Coordination Authority`
Coordination Epoch: `2`
Effective Coordination Revision: `110`
Date: `2026-08-27`

## Purpose

Provide the Director-level control surface for Foundation Wave 2 under the three-level model:

```text
Development Director
→ Track Orchestrator
→ Execution Agent
```

This board controls track activation, dependency readiness, parallelism and stable-candidate handoff. It does not amend frozen architecture and does not replace Track-local Task / Result / Review / Checkpoint records.

## Mandatory Orchestrator Reading

Every Development Director / Track Orchestrator session must include, at minimum, the following coordination protocol set in Required Reading:

1. `coordination/TASK_PROTOCOL.md`
2. `coordination/OUTPUT_FORMAT.md`
3. `coordination/REVIEW_PROTOCOL.md`
4. `coordination/WORKFLOW.md`

Repository files are the formal handoff channel. Chat is trigger, notification and concise status only.

## Global Interlocks

- Production parallelism is `DYNAMIC / NEED-DRIVEN`; there is no permanent numeric maximum.
- The Development Director decides active production concurrency from actual dependency graph, write-surface isolation, review capacity, integration capacity and risk concentration.
- A production track may run in parallel only when all relevant conditions are satisfied, including:
  1. no unresolved Contract dependency that requires serialization;
  2. no overlapping mutable production write surface, or safe physical isolation exists;
  3. required independent review capacity exists for the resulting risk level;
  4. integration checkpoint capacity is sufficient to avoid accumulating uncontrolled unreviewed foundational surfaces.
- Until PWP Core completes required independent exact-SHA review and is accepted as a stable dependency candidate, only Track A may run Foundation Wave 2 production implementation. This is a dependency gate, not a concurrency quota.
- Frozen semantics or Owner-boundary changes require `ESCALATION_REQUIRED` to the Development Director and, when architectural, routing to the Lead Design Authority.
- Implementation Agent must differ from Independent Reviewer for high-risk production.

## Track Board

| Track | Scope | Track Orchestrator | State | Current Gate / Dependency |
|---|---|---|---|---|
| `Track A — PWP / Context Backbone` | Project, Workspace, immutable config/context revisions, policy/environment binding, later IngressRoute/admission context integration | `Web GPT — Track A PWP / Context Backbone Orchestrator` | `ACTIVE / ORCHESTRATOR WINDOW REQUIRED` | `PWP CORE` — Task 116 only |
| `Track B — Distribution / Module Ecosystem` | Import, Resolve, Install, package/module identity, Registry, Trust, Enable | `UNASSIGNED UNTIL READY` | `STAGED / BLOCKED` | Requires reviewed stable PWP Core candidate + dependency/write-surface clearance |
| `Track C — Human Interaction / Approval` | HumanRequest, HumanResponse, HumanDecisionEvidence, approval aggregation, suspension/resume, response ingress | `UNASSIGNED UNTIL READY` | `STAGED / BLOCKED` | Requires reviewed stable PWP Core candidate + dependency/write-surface clearance |
| `Track D — External Interfaces / Workspace Boundary` | Filesystem, Process, Network, Browser, Provider, Workspace Handle, external effects/containment/ingress adapters | `UNASSIGNED` | `DEFERRED / BLOCKED` | Opens only after required PWP context is stable and later dependency checkpoints are ready |
| `Track E — Product / Visual Workflow` | Product Node, Visual Workflow, UI/UX, execution presentation, approval UI, run history, recovery/debug presentation | `UNASSIGNED` | `DEFERRED` | Foundation readiness required; D-006 remains downstream |

## Track-Local File Protocol

Within an authorized Track, the Track Orchestrator may create formal implementation / fix / review Task files under the Development Director's Track authority. Execution Agents may not create formal Task IDs.

Formal Track execution chain:

```text
coordination/tasks/<TaskID>.md
→ coordination/results/<TaskID>.md
→ independent Review / Re-Review Result
→ coordination/checkpoints/<TaskID>-<CheckpointID>.md when required
→ Track Stable Candidate evidence
```

All formal Task files must conform to `coordination/TASK_PROTOCOL.md` and include the mandatory fields defined there. Unlisted Scope is unauthorized by default.

All Result / Review / Re-Review / Checkpoint files must conform to `coordination/OUTPUT_FORMAT.md` and `coordination/REVIEW_PROTOCOL.md`.

For remote-delivery Tasks, formal `SUCCESS` requires remote-readable delivery with exact `Commit == Remote Commit == final remotely reviewable delivery-content commit` and SHA verification evidence.

## Track Orchestrator Reporting

Track Orchestrators do not copy child Task Results into chat for the Development Director. They first ensure the formal Repository files exist, then report only:

```text
Track:
Current Gate:
Stable Candidate SHA:
Review State:
Open Findings:
Blockers:
Next Milestone:
```

The Development Director reads the underlying Repository Result / Review / Checkpoint directly. Operator is not an inter-Agent message queue.

## Track A — Current Directive

Current formal production Task:

`NYRON-T-20260827-116 — PWP Core Identity / Immutable Revision / Historical Resolution Foundation`

Task 116 is not recreated. It remains the existing HIGH-risk implementation Task and is assigned to Track A.

Track A Orchestrator responsibilities for this task:

- route the existing Task 116 to the assigned implementation lane;
- maintain Track-local progress / checkpoint / Result awareness;
- require exact remote delivery identity;
- route independent exact-SHA review after implementation Result;
- route targeted fix / re-review when needed;
- report Stable Candidate only after review closure;
- escalate frozen-semantics or cross-owner uncertainty rather than designing around it.

## Track A Stable-Candidate Exit Criteria

Track A may report `STABLE CANDIDATE` only when:

1. Task 116 has a formal remote Result with exact production/test content SHA;
2. required validation is complete and honestly evidenced;
3. no blocking implementation/contract/architecture/security finding remains open;
4. independent exact-SHA review is `PASS` or accepted `PASS_WITH_FINDINGS` with no blocking finding;
5. PWP ownership and historical-resolution semantics remain within D-010 + PWP Amendment 001;
6. Development Director accepts the candidate for downstream dependency use.

## Track B Dependency-Ready Criteria

Track B may be activated only when:

- Track A PWP Core is a Director-accepted reviewed stable candidate;
- D-007 remains the frozen authority for Distribution semantics;
- exact Project / Workspace / config / policy context references needed by Distribution are available without inventing new cross-owner Contract semantics;
- planned Distribution production writes can be isolated from other active production tracks;
- `Import != Trust`, `Resolve != Enable`, and exact `module_ref@version` identity remain preserved;
- Distribution does not create or mutate CapabilityGrant authority.

## Track C Dependency-Ready Criteria

Track C may be activated only when:

- Track A PWP Core is a Director-accepted reviewed stable candidate;
- D-009 remains the frozen authority for Human Interaction / Approval semantics;
- required Project / Workspace / policy context references are available without inventing admission or foreign-owner semantics;
- planned Human Interaction production writes can be isolated from other active production tracks;
- HumanRequest / HumanResponse / HumanDecisionEvidence ownership remains separate from Runtime canonical execution truth;
- Runtime suspension/resume integration is not started until the corresponding frozen cross-owner contract surface is concretely dependency-ready.

## Next Global Milestone

`PWP CORE STABLE CANDIDATE`

Sequence:

```text
Task 116 implementation Result
→ independent exact-SHA review
→ targeted fix / re-review if required
→ Director acceptance of PWP Core stable candidate
→ dependency-driven activation decision for Track B / C and any other eligible Track
```
