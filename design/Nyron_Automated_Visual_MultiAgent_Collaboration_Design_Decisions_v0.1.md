# Nyron Automated Visual Multi-Agent Collaboration — Design Decision Record v0.1

**Status:** Working Design Decision Record  
**Scope:** Product / orchestration / interaction decisions confirmed in the 2026-08-31 to 2026-09-04 `/grill me` discussion  
**Authority:** Conversation-confirmed working design. This document does **not** supersede existing Frozen Baselines or accepted Amendments. If any statement conflicts with frozen architecture, raise an Architecture Finding and follow change control before implementation.

---

## 1. Product intent

Nyron is an **automated, visual multi-Agent collaboration platform**.

The target is not merely an Agent chat UI and not merely a static workflow editor. The platform must support both:

- AI-generated collaboration workflows; and
- human-created or human-modified collaboration workflows.

The visual graph is therefore both:

1. a human-editable collaboration surface; and
2. a visible representation of AI-generated orchestration.

The long-term product direction is Human-AI co-design of workflows rather than forcing either human-only or AI-only planning.

---

## 2. Workflow autonomy model

Workflow regions/nodes may have different autonomy levels.

Accepted model:

- `LOCKED` — AI must not modify.
- `SUGGEST` — AI may propose a mutation but may not directly apply it.
- `AUTONOMOUS` — AI may modify within policy.
- `EPHEMERAL` — AI may create temporary runtime structure that can be removed when no longer needed.

The system must allow AI to design collaboration flow while preserving explicit human control and locked areas.

AI-generated runtime structure does not imply that every generated node must become permanent.

---

## 3. Resource-aware team planning

AI should decide approximately how many engineers/Agents are needed based on:

- task type and complexity;
- user requirements;
- available AI quota/budget;
- concurrency limits;
- model cost/availability;
- reuse opportunities.

The system must distinguish:

- **Logical Role** — a responsibility required by the plan.
- **Agent Identity** — a reusable or temporary execution entity.
- **Session** — one concrete conversational/execution session.

A plan may require more logical roles than simultaneously active Agents.

Example:

```text
logical roles: Architect + Backend + Frontend + Reviewer + Tester
active Agent limit: 2
```

The scheduler/planner may reuse execution capacity across compatible roles, subject to isolation rules such as independent review.

### Budget behavior

Resource limits such as maximum active Agents, session count, or cost ceiling are hard constraints during normal execution.

If more resources are needed, the system may **request expansion** from the user/policy authority.

Within the approved budget, Directors may dynamically create or destroy Subagents.

---

## 4. Agent lifecycle

Nyron supports at least two lifecycle classes.

### Persistent / reusable Agent

Use when the role has continuing value across tasks or phases.

A persistent Agent may retain durable identity, configuration, selected plugins, and memory strategy.

### Ephemeral Agent

Use for temporary investigation or narrowly scoped work.

An ephemeral Agent may be destroyed whenever it is no longer needed. Necessary result/audit information remains durable even if the Agent/Session is removed.

### Identity separation

Do not collapse these identities:

```text
Role != Agent Identity != Session != Workflow Node
```

A persistent node may use new Sessions.  
A Session may end without deleting the Agent.  
An Agent may be replaced without changing the conceptual Role.  
A Workflow Node has its own stable node identity.

---

## 5. Context and memory are plugin-driven

How a persistent Agent remembers history should not be hard-coded as one global policy.

Nyron Core defines lifecycle and context boundaries; plugins may implement memory/context strategies such as:

- recent raw history;
- summarization;
- vector retrieval;
- file-based memory;
- task/track-specific memory;
- hybrid context assembly.

Core decides whether an Agent/Session exists and what authority boundaries apply.

Memory/context plugins decide what relevant information is retained, retrieved, summarized, or injected.

A memory plugin must not gain authority to decide Agent lifecycle merely because it stores history.

---

## 6. Plugin scopes

Plugins may be installed in two scopes.

### Agent scope

Capabilities that are normally available to a particular reusable Agent.

### Workflow scope

Capabilities made available because a particular workflow/task needs them.

Effective capabilities are derived from both, then narrowed by policy and current node/task grants.

A plugin being installed does **not** mean its full authority is granted.

---

## 7. Capability model

Plugins are capability providers.

Agents should request capabilities rather than depend directly on a concrete plugin implementation where possible.

Example:

```text
repo.read
```

may be provided by GitHub, GitLab, or local-repository providers.

Conceptual lifecycle:

```text
Installed
-> Available
-> Granted
-> Invoked
```

- **Installed:** provider/plugin exists.
- **Available:** provider is currently usable/connected.
- **Granted:** current Agent/Task/Node has authority to use a capability.
- **Invoked:** a concrete operation is executed.

### Permission narrowing

Policy layers may include:

```text
User Policy
-> Workflow Policy
-> Agent Policy
-> Node Policy
```

Lower layers may narrow authority but must not silently widen authority beyond an upper boundary.

---

## 8. Capability + Resource Scope

Authorization must include both capability and resource scope.

Examples:

```text
repo.write @ repository=ahhhh450/nyron @ branch=feature/*
filesystem.write @ /workspace/project/**
database.write @ database=project_db @ schema=staging
```

A generic permission such as `repo.write` without a resource boundary is insufficient for least-privilege execution.

---

## 9. Scope acquisition: do not trust AI self-report

AI may propose a requested scope, but its statement of “minimal scope” is not a security boundary.

The Runtime must rely on independent constraints/evidence where practical.

Accepted mechanisms include:

- static analysis / dependency or call graph evidence;
- sandbox dry-run and diff preview;
- provider/resource metadata;
- execution-time path/resource enforcement.

The final execution layer must re-check every concrete operation against the active Grant.

Proposal-time approval cannot replace execution-time enforcement.

---

## 10. Two-stage scope acquisition

Write scope often cannot be known safely before the Agent explores the target.

Accepted flow:

```text
Discovery
-> Proposal
-> Verification / Policy
-> Grant
-> Execution
```

### Discovery

Give sufficiently broad but read-only scope to understand the target.

### Proposal

After exploration, the Agent requests a narrower write/effect scope based on what it actually found.

### Execution

The Runtime enforces the granted scope per operation.

This avoids forcing the Agent to guess a write scope before it has enough evidence.

---

## 11. Grants are task-scoped leases

Dynamic authority expansion must not accumulate permanently across tasks.

Each dynamic Grant should be bound to relevant identity and task context, conceptually including:

```text
agent_id
task_id
capability
resource_scope
expiry / lifecycle
```

Task success, failure, cancellation, or expiry should revoke the temporary Grant.

A later task starts again from its own minimum necessary authority.

A separate “trusted repeated approval” optimization may exist, but it must not turn a previous task's lease into permanent hidden authority.

---

## 12. Asynchronous authority expansion

When a branch needs more authority, the whole workflow should not necessarily stop.

The affected branch may enter:

```text
WAITING_FOR_GRANT
```

while the scheduler continues work on other ready branches that already have sufficient authority.

Approval is therefore branch/task scoped rather than automatically global workflow blocking.

---

## 13. Scope verification trust model

Domain-specific verification may be plugin-based, but a verifier is not an ordinary self-selected Agent plugin.

Accepted separation:

- **Runtime hard boundary** — generic hard constraints and final enforcement.
- **Trusted Verifier** — produces domain-specific evidence.
- **Policy** — decides whether evidence is sufficient.
- **Runtime** — issues the Grant.

The Agent/Workflow must not be able to grant itself trust by selecting an arbitrary “friendly verifier”.

Verifier selection is controlled by Runtime/User Policy trust configuration.

### Verifier output

Prefer evidence over direct authorization.

Conceptually:

```text
Verifier -> Evidence
Policy   -> authorization decision
Runtime  -> Grant
Provider -> operation enforcement
```

---

## 14. Evidence and Grants are state-bound

Authorization must account for resource revision/state.

Evidence should be bound to a revision token appropriate to the resource type, for example:

- Git commit SHA;
- file content hash;
- database/schema/row version;
- ETag/resource version;
- document revision ID;
- workflow graph revision.

If the resource has materially changed since verification, the old evidence/Grant may be stale and must not silently authorize the changed state.

### Re-validation by risk

- Low risk: may automatically re-verify.
- Medium risk: may re-verify automatically if scope does not expand; expanded scope requires renewed authority.
- High risk: stale evidence requires renewed approval.

### Effect-bound Grants

For high-risk operations, support authority bound to a specific reviewed effect/diff rather than only a broad scope.

Examples include deployment, destructive migration, deletion, merge, or production configuration changes.

---

## 15. Role templates

Agent creation should use:

```text
Role Template
+ Task Overlay
+ Granted Capabilities
+ Resource Scope
+ Context Policy
```

Role templates may define defaults such as:

- responsibility/behavior rules;
- preferred model;
- default plugins;
- memory strategy;
- concurrency/cost preferences.

Task/Workflow overlays may adapt defaults but must not bypass upper permission boundaries.

AI may propose a new reusable Role Template, but should not silently promote a temporary role into a permanent library entry.

---

## 16. Workflow generation model

Use **Baseline Plan + Runtime Mutation**.

The AI creates an initial baseline workflow showing its current plan, then may adapt the graph during execution as new facts emerge.

The user must be able to distinguish:

- planned structure;
- currently active structure;
- cancelled/removed structure;
- runtime changes and their reasons.

---

## 17. Workflow Event Sourcing

### Mutation Log is the Source of Truth

The append-only Mutation Log is canonical.

```text
Mutation Log
-> fold(events[0..N])
-> Graph Revision N / materialized view
```

Graph revisions and snapshots are derived views and may be rebuilt.

Do not maintain a separately authoritative revision state that can drift from the event log.

### Undo is compensation

Undo must not delete or truncate historical events.

Undo/rollback creates compensating events.

History remains append-only and auditable.

### Stable node identity

Each Workflow Node has a unique, non-reused `node_id`.

UI folding/hiding is not node deletion.

If a removed conceptual role is later recreated, the new node receives a new ID.

### Mutation-created nodes do not inherit expanded authority

A new node created during runtime must not inherit the creator's current expanded dynamic Grant.

It starts from minimum authority and follows the normal Discovery/Proposal/Grant process.

Safe task context may be inherited; write/merge/deploy/destructive grants are not copied.

### Mutation risk levels

Graph mutation and authority grant are separate actions.

Low-risk exploratory/read-only mutations may auto-apply and be recorded.

Mutations that require higher authority may create the node/branch but leave execution waiting for approval.

High-risk capabilities follow the normal approval model.

### Snapshot/checkpoint

Mutation history may grow indefinitely, so periodic snapshots/checkpoints are allowed for replay performance.

A snapshot is a cache/checkpoint, not the Source of Truth.

Replay may start from the latest valid snapshot and then apply subsequent events.

---

## 18. Do not auto-extract reusable workflow templates

The design does **not** currently require automatic extraction of reusable Workflow Templates from a successful runtime graph.

Historical workflows may be replayed or referenced, but a single successful execution should not automatically become a reusable template.

Instead, project completion produces a textual experience summary.

---

## 19. Project experience summary

At project completion, the **final responsible Director** creates one project/workflow experience summary and stores it durably.

Other Agents provide evidence/results but do not independently write competing “project experience” records.

Useful content includes, when relevant:

- how many Agents were actually useful;
- which decomposition worked or caused rework;
- useful plugin/capability patterns;
- temporary nodes that became necessary;
- approval/permission bottlenecks;
- effective concurrency strategy;
- failures and lessons learned.

These records are reference experience for future projects, not mandatory templates or executable rules.

### Project closure authority

Only the final responsible Director determines that the project is closed.

Closure should account for completion, acceptance/review, and unresolved blockers being either resolved or explicitly closed.

The experience summary is produced at closeout.

---

## 20. One-click Handoff

Nyron must support a one-click Handoff for a node/session.

Semantics:

```text
same logical Node / Agent
-> end current active Session
-> create a new Session
-> inject structured Handoff
-> make new Session active
-> archive old Session read-only
```

### Handoff context

Default to **minimum necessary context + traceable references**, not full chat-copy.

Agent-generated portion may include:

- current goal;
- completed work;
- remaining work;
- key decisions;
- blockers;
- next suggested action.

Runtime supplies system facts such as:

- task/node/session identifiers;
- revision/status;
- authoritative file/result/log references;
- current authority state.

### Atomicity

Handoff must behave atomically from the node's point of view.

Preferred sequence:

```text
Prepare Handoff
-> Create New Session
-> Inject Context
-> Validate Ready
-> Switch active_session_id
-> Archive Old Session
```

If new-session creation/injection fails, the old Session remains active.

Each transfer should have a unique `handoff_id`.

### Old Session behavior

After successful Handoff, the old Session is archived read-only.

It is not directly reactivated.

Resume/Fork from an archived Session creates a **new Session** and re-validates current task/resource/policy/grant state.

### Grant behavior

Temporary dynamic Grants do not automatically carry across Handoff merely because the logical Agent remains the same. Current authority must be checked against the new Session/task state.

---

## 21. Central Scheduler

A central Scheduler controls runtime ordering and concurrency.

Planner/Directors declare:

- dependencies;
- priority;
- resource needs;
- constraints.

The Scheduler decides which READY work actually runs based on:

- dependency satisfaction;
- approved resource budget;
- concurrency limits;
- waiting approvals;
- available model/provider capacity.

---

## 22. Management and communication topology

The intended hierarchy is:

```text
Development Director
-> Track Directors
-> Subagents
```

There is no separate “General Director” above the Development Director in this working model.

### Communication rule

The normal real communication path is:

```text
Director <-> direct Subagent
```

Subagents do not freely form uncontrolled peer-to-peer conversations.

Cross-Agent/cross-Track information is mediated by the responsible Director level.

A Subagent is normally given only the context necessary for its own Task.

If it needs another Agent's work, the Director provides the relevant result/reference rather than granting broad access to other Sessions.

---

## 23. Task dispatch

A Director wakes a Subagent with a short command such as:

```text
执行 TASK <task_id>
```

The Task body itself is file-based.

The Task file should contain only task-specific necessary information.

Do not repeatedly embed rules already fixed by global protocol, Agent rules, Skill, or output schema.

Task-specific content may include the goal, acceptance criteria, constraints, and required references where needed, but fixed response formats and global rules should not be redundantly copied into every Task.

### Task revision

A dispatched Task must not be silently overwritten.

Changes create a new `task_revision` so an Agent can determine that the task changed.

---

## 24. Subagent completion communication

Subagent completion communication should be compact and structured.

The detailed result/evidence belongs in a durable result artifact/file/reference.

The wake-up message to the Director should contain only what is necessary to resume orchestration, for example:

```text
TASK <id> completed / blocked / failed
result_ref: ...
minimal feedback: ...
```

Output formats that are already globally fixed by protocol should not be repeated in each Task.

---

## 25. Subagent isolation and Director authority

Subagents are normally scoped to:

- their Task file/packet;
- their own active Session;
- explicitly granted resources/references.

They do not need broad project-state visibility.

The Director owns broader coordination context and injects only necessary information.

When a Subagent reports insufficient information, the Director may continue the same Session/Task for a small clarification; a materially changed goal should use a new task revision or a distinct Task as appropriate.

---

## 26. Retry behavior

Do not blindly auto-retry every failed node.

Retry depends on side effects.

Read-only or idempotent operations may use policy-controlled automatic retry.

For writes/commits/database mutations/other effects, the system must determine whether the previous attempt already produced an effect before deciding Resume, Compensate, or Retry.

---

## 27. Human workflow intervention

Human actions during execution are first-class workflow mutations.

Examples:

- pause;
- cancel;
- override;
- rewire;
- explicit manual edit.

They enter the Mutation Log.

AI must re-plan against the new graph revision and must not silently undo a human edit merely because it differs from its old plan.

---

## 28. Structured operational state for Directors

The system generates lightweight structured state that Directors can read without opening every Agent Session.

A minimal state view may include:

```text
agent_id
task_id
status
last_update / last_activity_at
current_phase
blocker_code / blocker_hint
result_ref
```

Possible statuses include concepts such as:

```text
IDLE
RUNNING
PASS
FAIL
BLOCKED
WAITING
STALE / SUSPECTED_STALL
LOST
```

Detailed work history is not copied into this current-state view.

---

## 29. Stall detection and wake-up

Do not require Agents to spam heartbeat messages merely to appear alive.

Runtime should update activity from real execution events.

If an Agent exceeds a configured no-activity threshold:

1. mark/identify a possible stall;
2. send a **short structured wake-up message** to the responsible Director;
3. do not inject large logs automatically.

A stall message should contain only minimal facts such as:

```text
agent/task identity
no-activity duration
current status/phase
blocker hint
monitor/diagnostic entry point
```

Repeated notifications must be de-duplicated and escalated by policy rather than firing every polling cycle.

---

## 30. Monitor

A Director may invoke a lightweight **Monitor** when an Agent has not reported or appears stuck.

Monitor is a diagnostic entry point, not a second full logging system.

It should answer questions such as:

- where execution appears to be stuck;
- last meaningful action;
- what it is waiting for;
- whether a process is still active;
- pending permission/approval;
- visible tool/provider error.

The Monitor should return a short diagnostic summary.

If deeper investigation is needed, the Director may:

- fetch the specific relevant log range;
- inspect a referenced artifact;
- instruct the existing Subagent to investigate;
- create a dedicated investigation Subagent;
- Handoff/Retry/Cancel as appropriate.

Runtime reports the problem; the Director makes task-level decisions.

---

## 31. Batched/staged structured persistence

Structured information intended for Agent/Director retrieval should not accumulate into one giant file.

Persist it in **stages/batches** so an Agent can read only the relevant phase/time range.

Useful indexing dimensions include:

```text
project
track
phase
time_window
type
```

Keep the index small; store references to stage/time-specific batches.

This principle applies to structured operational information that Agents may need to retrieve later: the purpose is to avoid injecting irrelevant historical context.

Monitor results themselves should remain lightweight. Durable diagnostic history may be stored in staged/batched form rather than as an ever-growing monolithic monitor log.

### Retention

Detailed historical batches may follow a retention/archive policy.

At project closeout, preserve key structured records and the Director's final project experience summary; lower-value raw detail may be archived or pruned according to policy.

---

## 32. Idempotent Task wake-up

Repeated:

```text
执行 TASK <task_id>
```

must not blindly start duplicate execution.

Runtime should distinguish at least:

- already running;
- already completed;
- task revision changed;
- inconsistent/problem state.

Identity should include the relevant combination of `task_id`, `agent_id`, and `task_revision`.

If idempotency checking discovers a problem or inconsistency, the system must return a short structured error/feedback instead of silently ignoring it.

---

## 33. Deferred / not-yet-decided frontier

The following questions were raised after the last confirmed round but were **not yet answered by the user** and therefore are not accepted decisions in this record:

- whether Subagents may directly set final Task `PASS/FAIL` or only report execution completion while Track Director owns final acceptance;
- exact two-layer completion/result notification contract beyond the already accepted compact structured feedback rule;
- exact semantics for rework: same `task_id` new attempt vs new revision vs new Task in every case;
- exact escalation contract from Track Director to Development Director;
- whether Handoff should ever auto-trigger versus only be suggested/policy-enabled.

These remain open frontier items for future `/grill me` rounds.

---

## 34. Summary of core invariants from this discussion

```text
Human and AI may both design/modify workflows.
AI autonomy is policy-scoped, not unlimited.
Logical Role != Agent != Session != Workflow Node.
Persistent Agents may be reused; ephemeral Agents may be destroyed.
Plugin installed != capability granted.
Capability authority = capability + resource scope.
AI-proposed scope is not trusted without independent constraints/evidence.
Dynamic Grants are task-scoped leases, not cumulative permanent authority.
Verifier produces evidence; Policy decides; Runtime grants/enforces.
Evidence/Grant may be bound to resource revision/effect.
Mutation Log is workflow Source of Truth.
Undo is compensation, never history deletion.
Runtime-created nodes do not inherit expanded grants.
Workflow Template extraction is deferred; project experience is textual.
Development Director -> Track Directors -> Subagents.
Normal communication is Director <-> direct Subagent.
Task wake-up is short; Task content lives in files.
Operational state is lightweight and structured.
Stall detection wakes the Director with minimal information.
Monitor diagnoses; it does not duplicate full logs.
Structured history is stored in phase/time batches for selective retrieval.
Handoff creates a new Session and archives the old one read-only.
Central Scheduler controls actual runtime ordering/concurrency.
```
