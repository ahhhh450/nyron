# Agent Availability

Status: `ACTIVE OPERATIONAL COORDINATION STATE`
Authority: `Development Director / Global Development Coordination Authority`
Date: `2026-08-27`

This file records current operational availability only. It does not define permanent model capability and does not amend architecture.

## Current Availability

| Agent | Availability | Default Use While State Applies |
|---|---|---|
| `Claude` | `UNAVAILABLE` | Do not assign new implementation, fix, review, re-review, or specialist work. Do not request a new Claude window. |
| `Codex` | `AVAILABLE — CLOSEOUT ONLY / LIMITED WEEKLY CAPACITY` | Operator has restored Codex capacity, but remaining weekly quota is limited. Use only for mandatory high-risk exact-SHA review/re-review, blocking fixes required by those reviews, and final closeout verification. Do not reopen broad parallel development. |
| `DeepSeek` | `AVAILABLE` | Preferred lane for bounded non-production contract tracing, low-risk implementation, localization work, mechanical/schema consistency, regression and targeted verification where risk permits. DeepSeek may provide supplementary/pre-review evidence for high-risk work, but does not by itself satisfy final high-risk acceptance review where `REVIEW_PROTOCOL.md` requires Codex/Claude-class review. |
| `GPT / Web GPT` | `AVAILABLE FOR ORCHESTRATION` | Development Director / Track coordination; not default production implementation or substitute high-risk final reviewer. |

## Mandatory Routing Rule

While Claude is `UNAVAILABLE` and Codex is restored with limited weekly capacity:

- do not create or dispatch new Claude assignments;
- do not reopen broad Codex parallelism;
- preserve already-delivered candidates and their exact-SHA review targets;
- high-risk `Implementation Agent != Independent Reviewer` remains mandatory;
- reserve Codex for mandatory high-risk exact-SHA review/re-review, any blocking fix needed to close those reviews, and final closeout verification;
- DeepSeek may perform bounded low-risk/mechanical work, localization work, targeted verification, or supplementary pre-review where useful, but such work does not close a high-risk independent-review gate by itself;
- capacity pressure never authorizes weakening architecture, security, Owner boundaries, stale-check rules, exact-SHA requirements, or independent review.

## Execution Mode Failover

Codex assignments may begin in Chat mode. If a Codex session encounters tool execution, repository-write, workspace, or environment errors and there is no durable Task-scoped technical/architecture blocker evidence, treat that signal first as an execution-mode failure rather than a Product blocker.

The Operator may continue the **same Task ID and Scope** in Work mode. A Chat → Work mode switch does not create a new Task, does not reset the required base/SHA, and does not waive Result/checkpoint/review requirements. Only durable Repository evidence may establish a substantive blocker.

## Closeout Priority

Current closeout priority is deliberately sequential to conserve weekly Codex capacity:

1. complete Task `NYRON-T-20260827-149` — independent exact-SHA review of Task 144 Effect historical-outcome orthogonality;
2. if Task 149 is PASS or otherwise does not consume a blocking-fix cycle, complete Task `NYRON-T-20260827-148` — independent exact-SHA review of Task 142 PWP IngressRoute/IngressRouteRevision;
3. perform only blocking fixes/re-reviews required by those reviews;
4. perform the smallest required final convergence/closeout verification;
5. leave optional next-slice implementation for a later capacity window.

Do not run Tasks 148 and 149 in parallel by default while weekly capacity is limited. Task 149 is first because Effect/replay/recovery semantics carry the higher correctness risk.

## Temporary Window Rule

This limited-capacity restoration is operator-authorized operational truth for the current quota window. It does not restore the prior broad parallel-capacity mode. Broader Codex use requires a later explicit Operator / Development Director decision.

## Change Rule

Agent availability remains operational state and may be superseded only by later explicit Operator / Development Director instruction.
