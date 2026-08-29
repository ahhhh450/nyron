# Nyron Node / Visual Workflow / Multi-Agent Orchestration Direction v0.1

Status: `DEVELOPMENT DIRECTOR PRODUCT DIRECTION / NON-FROZEN`

> This file records the current Product/Development direction for Node, Visual Workflow, and Multi-Agent orchestration. It does not amend Frozen Architecture by itself. Where implementation requires a new cross-owner or Runtime semantic not already frozen, the correct disposition is `Architecture Finding -> Lead Design Authority`, not local invention.

## 1. Core Direction Correction

Nyron's Node System is **independent from the Module System**.

The relationship MUST NOT be modeled as a mandatory chain:

```text
Module
  -> ProductNodeDefinition
  -> NodeInstance
```

The intended relationship is:

```text
                    Node System
                        |
       +----------------+----------------+
       |                |                |
   Built-in         System-backed    Module-backed
     Node               Node             Node
       |                |                |
       +----------------+----------------+
                        |
                   NodeInstance
                        |
               VisualWorkflowRevision
                        |
                compile / projection
                        |
                 Graph / Runtime
```

A Node answers:

> "How can a user compose work into a workflow?"

A Module answers:

> "What installable/executable capability exists?"

Therefore:

- a Module may exist without any Product Node;
- a Node may exist without any Module;
- a Node may consume one Module, multiple capabilities, or no external capability;
- control/orchestration Nodes such as `Condition`, `Join`, `Wait`, `Controlled Loop`, and `Create Agent Session` must not require a fake Product-level Module identity merely to exist;
- implementation may internally project a Node onto existing Runtime/Graph primitives, including trusted built-in runtime adapters where justified, but the Product Node contract itself must not require an exact Module binding for every Node type.

## 2. Node Contract Direction

The general Node contract should converge toward:

```text
NodeDefinition
  - node_type_ref
  - node_version
  - input_ports
  - output_ports
  - config_schema
  - execution_binding
  - effect / retry declaration where applicable
  - display metadata

NodeInstance
  - instance identity
  - exact NodeDefinition@version
  - config snapshot
  - workflow-local metadata

NodeConnection
  - source NodeInstance / output port
  - target NodeInstance / input port

VisualWorkflowRevision
  - immutable node set
  - immutable connection set
  - entrypoints / outputs
  - exact version bindings
  - deterministic revision identity
```

`execution_binding` must be able to represent at least these conceptual classes without forcing Workflow Core to know concrete node types:

```text
BUILTIN / PURE
SYSTEM_CAPABILITY
MODULE
COMPOSITE_WORKFLOW
```

The exact binding schema requires architecture/readiness verification before Production mutation.

Core principle:

> `Workflow Core knows Node contracts, not concrete Node implementations.`

Adding an ordinary Node should normally require registration of a new Node definition/execution binding, not modification of Workflow Core.

## 3. Node Versioning / Removal

Node semantics are versioned.

```text
Join@1 != Join@2
```

Existing workflows remain pinned to exact Node versions. A Node type may become:

- `ACTIVE`
- `DEPRECATED`
- `DISABLED`
- `UNAVAILABLE`

but historical workflow bindings must never be silently rewritten to a newer Node semantic.

`NodeDefinition != NodeInstance` remains mandatory.

## 4. Visual Workflow / Runtime Boundary

Keep the existing good separation:

```text
VisualWorkflowRevision
        !=
GraphRevision / Runtime canonical execution truth
```

Preferred shape:

```text
VisualWorkflowRevision
        |
        v
Node/Workflow compiler or projection layer
        |
        v
Graph / Runtime authority
```

Product layout/UI state remains non-authoritative presentation state and should not silently mutate executable workflow truth.

## 5. Confirmed Core Node Scope — 31 Nodes

The current core scope contains **31 nodes**:

- Foundation / Pure: 10
- Multi-Agent Orchestration: 19
- Human: 2

Later integration/function Nodes are not counted in this 31-node core.

### 5.1 Foundation / Pure Nodes — 10

1. `Start`
2. `Output`
3. `Constant`
4. `Transform`
5. `Template`
6. `Compare`
7. `Condition`
8. `Switch`
9. `Merge`
10. `Map`

These primarily validate NodeDefinition, ports, instances, connections, branching/data transformation, persistence, deterministic workflow revisioning, and compile/projection.

### 5.2 Multi-Agent Orchestration Nodes — 19

1. `Scheduler Agent`
2. `Task Splitter`
3. `Plan Validator`
4. `State Read`
5. `Dispatch Gate`
6. `Agent Selector`
7. `Create Agent Session`
8. `Context Builder`
9. `Dispatch Task`
10. `Wait / Subscribe`
11. `Timeout`
12. `Join / Barrier`
13. `Result Aggregator`
14. `Result Merger`
15. `Failure Handler`
16. `Cancel`
17. `Concurrency Limit`
18. `Queue / Priority`
19. `Controlled Loop`

### 5.3 Human Nodes — 2

1. `Human Approval`
2. `Human Input`

`Human Approval` returns a bounded decision/evidence path such as approve/reject.

`Human Input` obtains structured data from a human during an active workflow and is not equivalent to approval.

## 6. Orchestration Internal Dependency Order

The 19 orchestration Nodes are not a flat implementation list. They have prerequisites.

Recommended dependency phases:

### O1 — State / Safety Foundations

```text
State Read
Timeout / Durable Deadline support
Plan Validator
Concurrency Limit / Runtime concurrency enforcement
```

### O2 — Expansion / Gate

```text
Task Splitter
Dispatch Gate
```

### O3 — Agent / Session Execution Chain

```text
Agent Selector
Create Agent Session
Context Builder
Dispatch Task
```

### O4 — Async Wait / Synchronization

```text
Wait / Subscribe
Join / Barrier
```

### O5 — Result Handling

```text
Result Aggregator
Result Merger
```

### O6 — Failure / Cancellation

```text
Failure Handler
Cancel
```

### O7 — Resource Scheduling Policy

```text
Queue / Priority
```

### O8 — Iterative Agent Orchestration

```text
Scheduler Agent
Controlled Loop
```

These phases identify prerequisites; they do not require strictly serial development when independent write surfaces and accepted dependencies permit parallel work.

## 7. Multi-Agent Canonical Use Case

A first-class Nyron workflow must be able to express:

```text
[Trigger / Goal]
       |
       v
[Scheduler Agent]
       |
       v
[Plan Validator]
       |
       v
[Task Splitter]
    /     |      \
   v      v       v
[Gate]  [Gate]  [Gate]
   |      |       |
   v      v       v
Agent A Agent B  WAIT dependency
   |      |
 DONE   DONE
    \     /
     v   v
    [Join]
       |
       v
[Result Aggregator]
       |
       v
 [Result Merger]
       |
       v
[Scheduler Agent]
       |
 COMPLETE or next bounded iteration
```

The Scheduler Agent is an Agent, not canonical state authority.

```text
Agent reasoning / decision != State truth
```

Before dispatch or re-dispatch, canonical state must be re-read/validated by the Runtime/State authority.

## 8. Child Agent Session Requirement

Nyron orchestration must support creation and use of child Agent sessions.

Conceptual session policies:

```text
USE_EXISTING
CREATE_NEW
CREATE_IF_NONE_AVAILABLE
```

A child session should receive a minimal Task-scoped context package, not an uncontrolled copy of the entire parent conversation.

`Context Builder` may include:

- Task ID / structured work item
- repository/workspace identity
- required reading/context refs
- exact dependency/base refs
- Agent role
- bounded scope
- completion/result format
- parent Scheduler identity

Session truth should remain canonical outside the Agent's own assertions.

## 9. Runtime Mechanisms — Required but Not Default Canvas Nodes

The following are required Runtime capabilities. They are not necessarily default user-visible Nodes:

- `Dependency Subscription Registry`
- durable event subscription/delivery
- `Durable Deadline / Timer`
- `Session Health`
- suspension / resume
- state persistence
- concurrency enforcement
- cancellation truth
- fencing
- capability enforcement
- Effect tracking
- Recovery authority
- Retry authority

Principle:

> `Functionally required` does not mean `must appear as a visible Node`.

Nodes represent user-composable workflow semantics. Repetitive reliability/state mechanisms should be enforced by Runtime unless an advanced explicit Node is useful for user policy/configuration.

## 10. Dependency Subscription Semantics

`Dependency Watcher` is not currently required as a default visible Node, but dependency watching itself is a first-class Runtime subsystem and MUST be explicitly designed.

Multiple consumers may depend on one upstream Task:

```text
T1
 |
 +--> Gate(T4)
 +--> Gate(T5)
 +--> Join(Batch-X)
```

Do not create uncontrolled polling loops or wake every subscriber for every irrelevant state mutation.

The design should support predicate-based subscriptions, conceptually:

```text
dependency_ref
predicate / wake condition
subscriber_ref
workflow_execution_ref
generation/version
delivery/dedupe identity
```

Example:

```text
wake_when T1 in {DONE, FAILED, BLOCKED, CANCELLED}
```

Required properties:

- restart-safe;
- duplicate-delivery safe;
- stale subscription identifiable;
- Gate re-entry idempotent;
- terminal cleanup/unsubscribe;
- shared canonical event source may fan out to multiple subscribers.

## 11. Timeout / Durable Deadline Contract

Timeout is required from the first real orchestration slice.

`Wait`, `Join`, Agent session waits, Human Input, and Approval must not depend on an unbounded in-memory timer.

Runtime should provide one durable deadline mechanism reused by nodes:

```text
Wait(timeout=...)
Join(timeout=...)
AgentSession(timeout=...)
HumanInput(timeout=...)
HumanApproval(timeout=...)
```

A visible `Timeout` Node may express a branch/workflow policy, but the underlying durable deadline capability must exist independently.

## 12. Concurrency Contract

Concurrency safety MUST NOT depend on the user remembering to place a `Concurrency Limit` Node.

Two layers are required:

### Runtime hard safety limits

Always active, even when no visible limit Node exists.

Potential scopes include:

- global
- project/workspace
- workflow
- Agent type
- Provider/executor type

### Explicit `Concurrency Limit` Node

Allows a workflow/branch to request a stricter or otherwise policy-authorized local limit.

An explicit Node may never bypass a Runtime hard ceiling.

Principle:

> `Scheduler proposes; Runtime enforces.`

Development order:

```text
1. hard Concurrency enforcement
2. durable waiting queue
3. Queue / Priority policy
```

## 13. Plan Validator Contract

Scheduler output is untrusted planning data until validated.

Required chain:

```text
Scheduler Agent
     -> Plan Validator
     -> Task Splitter
     -> execution path
```

At minimum validate:

- Task IDs are valid/unique;
- required fields exist;
- Agent/session policy values are recognized;
- dependency refs resolve;
- dependency graph does not contain prohibited cycles;
- requested capacity/concurrency fields are valid;
- unknown enums/fields fail closed according to schema policy;
- structured Scheduler output matches the executable Task Plan schema.

`Scheduler output != executable authority`.

## 14. Map vs Task Splitter

`Map` and `Task Splitter` have different user semantics but should not create two independent fan-out engines.

```text
Map
= generic cardinality expansion primitive
```

It knows nothing about Agent identity, Task dependencies, sessions, or scheduling.

```text
Task Splitter
= orchestration-domain specialization of expansion
```

It consumes a validated `TaskPlan` and emits `TaskEnvelope[]`, including orchestration fields such as:

- task identity
- Agent requirements
- dependency refs
- priority
- context policy
- session policy

`Task Splitter` should reuse the generic cardinality/expansion primitive where practical.

## 15. Failure Handler v0.1

The first Failure Handler should support a small frozen strategy subset rather than an open-ended vague interface:

```text
ABORT_WORKFLOW
SKIP_BRANCH
RETURN_TO_SCHEDULER
```

### ABORT_WORKFLOW

Stop new downstream scheduling and move the workflow into its defined failed terminal path.

### SKIP_BRANCH

Terminate only the failed branch; independent branches may continue if their dependency semantics remain valid.

### RETURN_TO_SCHEDULER

Return failure facts, current canonical state references, and accepted child results to the Scheduler Agent for a new validated plan.

Defer from Failure Handler v0.1:

- automatic `CONTINUE` semantics;
- generic `FALLBACK`;
- `WAIT_FOR_HUMAN` convenience policy;
- automatic `COMPENSATE`;
- automatic retry.

These may be added as separately defined strategies later.

## 16. Retry / Recovery Safety Contract

Retry is not a blind "run again" Node.

Node/Module execution declarations should eventually distinguish at least:

```text
effect_semantics:
  PURE
  CONSEQUENTIAL

idempotency:
  SAFE
  IDEMPOTENCY_KEY_REQUIRED
  UNSAFE
  UNKNOWN
```

Conservative defaults:

```text
effect_semantics = CONSEQUENTIAL
idempotency = UNKNOWN
```

Therefore absent stronger accepted evidence:

```text
UNSAFE or UNKNOWN
-> NO AUTOMATIC RETRY
```

Final retry clearance belongs to Runtime/Recovery authority, not to a Node or Module self-assertion.

A Node/Module declaration is evidence/contract input, not authority to override Effect historical truth, fencing, or RecoveryDisposition.

In particular:

```text
consequential Effect historical outcome = UNKNOWN
!= automatic retry clearance
```

## 17. Compensation Semantics

Compensation is not rollback of canonical history.

A compensation is a **new task/effect** intended to counteract a prior consequence where possible.

First version does not require a dedicated `Compensation` primitive Node.

Static pattern:

```text
Failure Handler
  -> Dispatch Task (known compensating action)
```

Dynamic pattern:

```text
Failure Handler
  -> Scheduler Agent
  -> validated compensating Task Plan
  -> Dispatch Task
```

A later convenience Compensation Node may be added if useful, but it must still produce new canonical work rather than erase prior Effect truth.

## 18. Cancel Contract

Cancellation must distinguish logical cancellation from real executor termination.

```text
CANCELLED != EXECUTION_TERMINATED
```

### Logical cancel

Must be supportable independent of executor hard-stop capability:

- future downstream scheduling is prevented according to policy;
- cancelled work cannot later become authoritative merely because a late Agent result arrives;
- late results are handled explicitly as non-authoritative/stale according to Runtime truth.

### Executor termination

A best-effort or guaranteed termination signal is only truthful when the concrete Executor supports and proves it.

If hard termination is unavailable, the system must say so explicitly instead of pretending the Agent stopped consuming resources.

Executor capabilities should eventually expose termination support rather than letting the Cancel Node infer it.

## 19. Controlled Loop Safety Contract

Loop is a high-risk orchestration primitive, not equivalent in risk to `Constant` or `Compare`.

Nyron v0.1 must reject an unbounded orchestration loop.

At minimum:

```text
max_iterations > 0
```

For Scheduler loops, each iteration should produce an explicit validated disposition such as:

```text
CONTINUE
COMPLETE
BLOCKED
ESCALATE
```

Runtime hard guards should reserve/support:

```text
max_iterations
max_generated_tasks
max_wall_clock_duration
```

Reaching a hard limit routes to Failure Handler / defined terminal handling; the Scheduler is not simply called forever.

Core rule:

> `No unbounded orchestration loop.`

## 20. Result Aggregator vs Result Merger

Keep these as separate semantics.

### Result Aggregator

Answers:

> "When is enough child work complete to form a result batch?"

Works with Join semantics such as:

- ALL
- ANY
- N_OF_M
- NAMED_SET

### Result Merger

Answers:

> "How are the completed child results normalized/combined into the next input?"

A deterministic merger may be pure rules. A future LLM synthesis Node may consume the normalized batch separately.

## 21. Future Function / Integration Nodes

These are expected later but are not part of the 31-node core count:

- LLM
- HTTP
- Filesystem
- Browser
- Memory
- TTS
- STT
- Avatar / Digital Human
- Image Generation
- Notification
- installable Custom Module Node
- Composite Node authoring conveniences

External/consequential nodes pull the smallest required lower-level Track slice when they become concrete Product requirements.

## 22. ComfyUI Inspiration / Nyron Difference

Borrow from ComfyUI:

- lightweight Node definitions;
- Node registry/extension model;
- typed ports;
- workflow serialization;
- default UI generation from Node metadata/config schema;
- optional custom frontend extension for special Node UX;
- adding ordinary nodes without editing the Workflow Core.

Do not copy its execution assumptions blindly.

ComfyUI is primarily a computation-graph/DAG system. Nyron additionally requires:

- Multi-Agent execution;
- child sessions;
- durable long-running waits;
- restart-safe event subscriptions;
- cancellation;
- concurrency limits;
- dependency-aware dispatch;
- result barriers/aggregation;
- Scheduler replanning loops;
- Human waiting/input;
- consequential Effect/Recovery safety.

Nyron therefore targets a **durable visual orchestration runtime**, not only a synchronous computation graph.

---

# 23. Current Repository Direction Audit — 2026-08-29

The current accepted work contains valuable reusable foundations, but the Product direction has two major mismatches with the refined requirement.

## Audit Finding A — Current accepted ProductNodeDefinition is mandatory Module-backed

Severity: `HIGH / PRODUCT MODEL DIRECTION`

Current accepted Product code at accepted base `103a47324807f01c76990df7b5bca9d3668cb552` defines `ProductNodeDefinition` as a wrapper around exactly one `ModuleDefinition@version`.

Current fields include mandatory:

```text
bound_module_ref
bound_module_version
input_port_bindings -> Module ports
output_port_bindings -> Module ports
```

The current registry refuses registration unless the exact Module exists and requires Product ports to bind the Module port surface.

This was deliberate in Task 170/171, but it is now too restrictive for the clarified Product requirement.

Impact:

- pure Product control Nodes are forced to masquerade as Modules;
- System-backed Nodes such as `State Read`, `Create Agent Session`, `Wait`, or `Human Input` cannot be represented naturally;
- Composite Nodes cannot be expressed as a first-class Node binding;
- Node extensibility remains coupled to Module identity and Module port shape;
- a user-facing Node cannot cleanly present a contract independent of a specific Module backend.

Required adjustment:

Do **not** delete the entire accepted Node Foundation. Generalize the Node contract so Module binding becomes one `execution_binding` variant, not a mandatory field on every NodeDefinition.

## Audit Finding B — Current Product compiler assumes every Node becomes a ModuleInstanceRevision

Severity: `HIGH / PRODUCT-RUNTIME EXPRESSIVENESS`

The current `ProductGraphCompiler` resolves a ModuleDefinition for every Product Node and creates a `ModuleInstanceRevision` for every NodeInstance.

This is consistent with the old Module-first assumption but insufficient as the general Node/Orchestration model.

Required adjustment:

Before writing the orchestration nodes, perform a bounded architecture/readiness delta review to determine how each execution-binding class projects into the frozen Graph/Runtime authority.

Possible implementation strategies must be evidence-driven, for example:

- Module-backed Nodes -> existing ModuleInstanceRevision path;
- pure/built-in Nodes -> trusted built-in execution adapters or another already-frozen generic mechanism;
- System-backed Nodes -> stable system capability/service contracts without giving Product direct authority;
- Composite Nodes -> expansion/projection into a frozen workflow/graph form;
- async orchestration Nodes -> existing/newly-authorized durable Runtime suspension/event primitives.

If current frozen Graph/Runtime cannot express a required category without new semantics, raise an Architecture Finding. Do not hide the gap by creating fake Module semantics at Product level.

## Audit Finding C — Current Handoff still encodes the old mandatory Module -> Node chain

Severity: `MEDIUM / COORDINATION DIRECTION`

Current Handoff R2 still describes:

```text
Module
  -> ProductNodeDefinition
  -> NodeInstance
```

and its Node Foundation acceptance standard assumes every Node is an exact Module exposure.

Required adjustment:

Supersede that Product-direction section after the generalized Node contract is formally reviewed. Keep the Handoff repository-truth and Agent-operating rules; only the Node/Module model is stale.

## Audit Finding D — Current P0 target over-focuses on real LLM / Network gate

Severity: `HIGH / SCHEDULING PRIORITY`

Current coordination state names:

```text
Current Gate: REAL PROVIDER / NETWORK CONSEQUENTIAL SECURITY READINESS
Current Target: LLM PRODUCT NODE v0.1 — FIRST REAL SINGLE-TURN PROVIDER SLICE
```

This is a valid future Product vertical slice, but it should not be the sole/primary Product-development gate after the clarified goal.

Why:

- the general Node contract is still too Module-coupled;
- Multi-Agent orchestration is the core target capability;
- pure and orchestration Node work can proceed without real Internet/Provider Production;
- making Track E wait on Track D recreates the earlier failure mode where Product progress is blocked by lower-level external infrastructure.

Required adjustment:

Reclassify real LLM/Network work as a **parallel support lane**, not the sole Product mainline gate.

Existing read-only Tasks 186/187 may finish because they do not mutate Production and their findings remain useful for the eventual real LLM Node. Their completion must not imply that Node/Orchestration work waits for real Network Production.

## Audit Finding E — Accepted Node Foundation contains substantial reusable work

Severity: `POSITIVE / PRESERVE`

Do not discard accepted `NODE FOUNDATION v0.1` wholesale.

Keep/reuse where still correct:

- `NodeDefinition != NodeInstance` separation;
- immutable/persistent VisualWorkflowRevision approach;
- NodeConnection persistence/validation concepts;
- separate layout/presentation state;
- deterministic compile/projection concept;
- Graph remains executable authority;
- Product does not become CapabilityGrant/Runtime authority;
- exact version pinning/restart/replay discipline;
- multi-instance Graph publication work;
- existing pure/mock E2E proof as a regression case for the Module-backed Node category.

The correction is to **broaden the Node abstraction**, not erase the valid persistence/Graph/Runtime foundation.

---

# 24. Recommended Direction Adjustment

## Primary Product Milestone

Replace the effective mainline goal of:

```text
REAL LLM PRODUCT NODE FIRST
```

with:

```text
GENERAL NODE CONTRACT + MULTI-AGENT ORCHESTRATION FOUNDATION
```

Real LLM remains an important later/parallel vertical slice.

## Recommended next architecture/readiness unit

Before Production changes to the accepted Product subsystem, run a HIGH-risk bounded read-only architecture/readiness review covering:

1. generalized `NodeDefinition` independent of mandatory Module binding;
2. `execution_binding` kinds and ownership;
3. native Product port contract vs Module-port adapter binding;
4. how built-in/system/module/composite Nodes compile/project to current frozen Graph/Runtime;
5. whether current Graph semantics can express Condition/Switch/Merge/Map without new Kernel semantics;
6. durable async semantics required by Wait/Join/Agent Session/Human nodes;
7. Dependency Subscription Registry and re-entry/dedupe semantics;
8. durable deadline/timeout ownership;
9. global Runtime concurrency enforcement + optional local Concurrency Limit Node;
10. cancellation truth vs executor termination;
11. Failure Handler v0.1 strategies;
12. Controlled Loop hard termination bounds;
13. Retry declarations and Runtime Retry Authority;
14. Agent Session canonical identity/state/parent-child relation;
15. Scheduler Plan -> Plan Validator -> Task Splitter trust boundary;
16. exact smallest Production refactor that preserves the accepted Module-backed E2E while enabling at least one non-Module Node category.

Required readiness outcome should be one of:

```text
GO_BOUNDED_GENERAL_NODE_REFACTOR
BLOCKED_BY_EXISTING_RUNTIME_GAP
ESCALATION_REQUIRED
```

## Minimum refactor proof after readiness GO

A corrected Node foundation should prove at least:

```text
one PURE/Built-in Node
one SYSTEM-backed Node
one MODULE-backed Node
```

coexisting under the same Node registry/Workflow contract without requiring Workflow Core to hard-code their concrete types.

The existing Module-backed `Text Input -> Mock LLM -> Text Output` test should remain green as backward/regression evidence.

A subsequent orchestration vertical slice should prove something like:

```text
Scheduler/Plan
  -> Plan Validator
  -> Task Splitter
  -> bounded parallel child execution/session simulation
  -> Wait/Join with durable timeout semantics
  -> Result Aggregator/Merger
  -> Scheduler completion decision
```

Real external Agent-session creation may be introduced only when the concrete executor/session contract is ready; an initial deterministic simulated executor is acceptable if truthfully labeled.

---

# 25. Scheduling Recommendation

Current safe parallel structure:

```text
PRIMARY PRODUCT LANE
General Node Contract / Orchestration readiness and bounded correction

PARALLEL SUPPORT LANE
Task 186 — real Provider/Network security readiness (read-only)
Task 187 — concrete Provider/Credential/Network inventory (read-only)
```

Do not start real Provider/Network Production merely because Tasks 186/187 finish.

The Product Node framework and orchestration contract should progress independently where dependencies/write surfaces permit.

Track C Human suspension/resume should be pulled when `Human Approval` / `Human Input` or orchestration waiting creates a concrete requirement. At that point Task 169 may become relevant again, but its exact assumptions must be rechecked against this generalized Node direction before resumption.

---

# 26. Direction Summary

Current corrected model:

```text
Node System
  != Module System

NodeDefinition
  -> optional/typed ExecutionBinding
       - Built-in/Pure
       - System Capability
       - Module
       - Composite Workflow

NodeInstance + Ports + Connections
  -> VisualWorkflowRevision
  -> deterministic validated projection
  -> existing Graph/Runtime authority
```

Product priority:

```text
1. General Node contract correction
2. Runtime safety contracts required by orchestration
3. Multi-Agent orchestration foundation
4. concrete Product vertical slices in parallel as dependencies permit
5. real LLM/Network only when its external gate is specifically needed/accepted
```

The accepted lower-level Foundation remains valuable. The principal correction is **Product abstraction and scheduling priority**, not wholesale system-foundation replacement.
