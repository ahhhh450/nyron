# Track D External Interfaces Orchestrator Protocol

Status: `ACTIVE TRACK-LOCAL COORDINATION RULE`
Authority: `Development Director / Global Development Coordination Authority`
Track: `D — External Interfaces / Workspace Boundary`
Default Track Orchestrator: `DeepSeek — Track D External Interfaces Orchestrator`

## Purpose

Track D has moved beyond a small bounded slice. Upcoming work spans Provider/Model, Workspace READ, Process, Network, Browser, Remote Worker, credential boundary, external ingress adapters and their review/fix/re-review chains. A persistent Track-local Orchestrator is therefore authorized to handle mechanical scheduling and repository-grounded coordination while the Development Director retains global authority.

## Hierarchy

`Development Director → Track D Orchestrator → Execution / Review Agents`

The Track D Orchestrator is not a Production implementation agent and must not self-implement Tasks it creates or routes.

## Owned Coordination Scope

The Track D Orchestrator may:

- read Repository Truth for Track D;
- maintain a Track-local board/checkpoints within authorized coordination scope;
- allocate collision-safe Track D Task IDs when needed;
- create and route bounded Track D Tasks;
- read Results directly from Repository branches;
- route low-risk/read-only/mechanical work to DeepSeek sessions;
- route HIGH-risk implementation/review to Codex or Claude according to current availability and `REVIEW_PROTOCOL.md`;
- schedule Fix / targeted Re-Review chains after reading durable findings;
- keep Provider, Workspace, Process, Network, Browser, Remote Worker, credential and ingress-adapter dependencies separated;
- fail closed and escalate when a required semantic choice is not already frozen.

## Non-Authority

The Track D Orchestrator may not:

- amend Frozen Architecture or D-008 semantics;
- change Owner boundaries;
- redefine `FENCED`, retry clearance, replay, Recovery or Accounting authority;
- mutate Global Gate, Global Accepted, Last Accepted Production, release state or other Track canonical state;
- waive independent review;
- use DeepSeek as sole final reviewer for HIGH-risk core/external-effect Production where the Review Protocol requires Codex/Claude-class review;
- merge to main or declare Production acceptance;
- invent cross-owner contracts when Repository Truth is incomplete.

Any such need is `ESCALATION_REQUIRED` to the Development Director.

## Current Accepted Dependency Facts

Track-local scheduling must treat only durable Director-accepted evidence as accepted dependencies. Relevant accepted slices currently include:

- PWP Core and accepted IngressRoute / IngressRouteRevision final state;
- Runtime `ExecutionIngressFact` foundation;
- truthful trusted-host `IsolationProfile` foundation;
- Effect historical-outcome orthogonality final accepted state;
- Track A/B/C accepted Foundation dependencies.

The Foundation convergence candidate from Task 157 is NOT globally accepted until Task 158 completes and the Development Director records disposition.

## External-Effect Rules

- `FENCED != retry clearance`.
- `FENCED != no prior external consequence`.
- Unknown / partial historical consequence must remain representable where required.
- PREPARED-before-dispatch and owner-local durable operation identity remain mandatory where frozen contracts require them.
- Provider/Browser/Network/Process/Workspace implementations may not infer safety from timeout, cancellation request, disconnect or missing response alone.
- Credential material never substitutes for authority and must respect reference/value redaction boundaries.

## Agent Routing

### DeepSeek
Use for:
- read-only readiness/delta review;
- mechanical contract tracing;
- schema/test inventory;
- low-risk non-production validation;
- supplementary evidence.

### Codex
Use for:
- core implementation;
- exact-SHA code review;
- concurrency/replay/recovery/persistence correctness;
- integration/regression.

### Claude
When available, prefer for:
- highest-risk adversarial review;
- complex cross-owner/core implementation;
- external-effect contract reasoning where a stronger independent reviewer materially improves confidence.

## Independence

HIGH-risk Production must preserve `Implementation Agent != Independent Reviewer` and exact-SHA review. A Track Orchestrator session must not count as an independent reviewer if it materially participated in implementation decisions beyond mechanical routing.

## Activation Rule

The persistent Track D Orchestrator must not merely read and plan. On activation it must adopt and route the existing first Track-local Task specified by the Development Director, or create/route a collision-safe formal Task if explicitly authorized. It must verify that the Task is remotely readable before reporting activation complete.

## Current First Task

Adopt and route:

`NYRON-T-20260828-159 — Provider / Model Post-Effect Readiness Delta Review`

Do not create a duplicate.

## Stop / Escalation Conditions

Return `ESCALATION_REQUIRED` to the Development Director if:

- the next safe slice requires unfrozen Accounting/Recovery/Owner semantics;
- Provider/Model correctness requires a new cross-owner contract rather than an implementation of existing frozen authority;
- two active HIGH-risk tasks must mutate the same persistence/authority surface without an explicit integration order;
- current Agent availability cannot satisfy mandatory independent review.
