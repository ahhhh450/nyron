# Agent Availability

Status: `ACTIVE OPERATIONAL COORDINATION STATE`
Authority: `Development Director / Global Development Coordination Authority`
Date: `2026-08-28`

This file records current operational availability only. It does not define permanent model capability and does not amend architecture.

## Current Availability

| Agent | Availability | Default Use While State Applies |
|---|---|---|
| `Claude` | `UNAVAILABLE — PENDING OPERATOR CONFIRMATION OF RESET` | Do not assign new implementation, fix, review, re-review, or specialist work until the Operator confirms reset/availability. |
| `Codex` | `AVAILABLE — FULL WEEKLY WINDOW / CONTROLLED PARALLELISM` | Weekly quota has been operator-confirmed reset. May be used for high-risk review, core implementation, blocking fixes, integration/regression, and selected bounded next-slice work. Do not saturate all lanes merely because capacity exists. |
| `DeepSeek` | `AVAILABLE` | Preferred lane for bounded non-production contract tracing, low-risk implementation, localization work, mechanical/schema consistency, regression and targeted verification where risk permits. DeepSeek may provide supplementary/pre-review evidence for high-risk work, but does not by itself satisfy final high-risk acceptance review where `REVIEW_PROTOCOL.md` requires Codex/Claude-class review. |
| `GPT / Web GPT` | `AVAILABLE FOR ORCHESTRATION` | Development Director / Track coordination; not default production implementation or substitute high-risk final reviewer. |

## Mandatory Routing Rule

While Claude is still pending reset confirmation and Codex has a fresh weekly window:

- do not create or dispatch new Claude assignments until Operator confirmation;
- controlled parallelism is authorized where dependencies and write surfaces are disjoint;
- finish already-open mandatory exact-SHA reviews and closeout gates before allowing their unresolved dependencies to contaminate later integration;
- high-risk `Implementation Agent != Independent Reviewer` remains mandatory;
- Codex may take high-risk review/core implementation/integration work when appropriate;
- DeepSeek remains preferred for Language/Localization and other low-risk/mechanical work;
- avoid filling every available lane with speculative work; each concurrent lane must have a clear dependency/write-surface reason;
- architecture/security/Owner-boundary/stale/exact-SHA/independent-review requirements are unchanged.

## Execution Mode Failover

Codex assignments may begin in Chat mode. If a Codex session encounters tool execution, repository-write, workspace, or environment errors and there is no durable Task-scoped technical/architecture blocker evidence, treat that signal first as an execution-mode failure rather than a Product blocker.

The Operator may continue the **same Task ID and Scope** in Work mode. A Chat → Work mode switch does not create a new Task, does not reset the required base/SHA, and does not waive Result/checkpoint/review requirements. Only durable Repository evidence may establish a substantive blocker.

## Current Controlled-Parallelism Priority

1. complete mandatory exact-SHA Task `NYRON-T-20260827-148` for PWP IngressRoute/IngressRouteRevision;
2. after 148 disposition, perform the smallest required Foundation convergence/closeout integration and independent verification;
3. in parallel, allow clearly disjoint low-risk work such as Language/Localization through DeepSeek;
4. once Claude reset is explicitly confirmed, reserve Claude primarily for the highest-value complex architecture/core implementation or adversarial review lane rather than routine work;
5. next Track-D consequential external-effect slices should open only with explicit Task scoping and accepted dependency basis.

## Parallelism Rule

A fresh quota window permits multiple lanes, but concurrency remains dependency-driven:

- `Review lane` may run alongside disjoint low-risk Product-support work;
- `Implementation lane` may run alongside review only when it does not mutate the exact SHA under review and has a disjoint write surface;
- final integration/convergence must wait for all required dependency reviews whose content is intended to be included;
- avoid simultaneous high-risk edits to shared persistence/authority surfaces unless separately isolated and integration order is explicit.

## Temporary Window Rule

Codex is fully available for the current weekly window, but this does not imply unlimited useful parallelism. The Development Director may expand or reduce active lanes according to dependency and integration load. Claude remains unavailable until explicitly confirmed restored by the Operator.

## Change Rule

Agent availability remains operational state and may be superseded only by later explicit Operator / Development Director instruction.
