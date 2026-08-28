# Agent Availability

Status: `ACTIVE OPERATIONAL COORDINATION STATE`
Authority: `Development Director / Global Development Coordination Authority`
Date: `2026-08-28`

This file records current operational availability only. It does not define permanent model capability and does not amend architecture.

## Current Availability

| Agent | Availability | Default Use While State Applies |
|---|---|---|
| `Claude` | `AVAILABLE — OPERATOR-CONFIRMED RESTORED / HIGH-VALUE PRIORITY` | Reserve primarily for highest-value complex architecture/core implementation and adversarial high-risk review/re-review. Do not spend Claude capacity on routine mechanical work when Codex or DeepSeek is sufficient. |
| `Codex` | `AVAILABLE — FULL WEEKLY WINDOW / CONTROLLED PARALLELISM` | Weekly quota has been operator-confirmed reset. May be used for high-risk review, core implementation, blocking fixes, integration/regression, and selected bounded next-slice work. Do not saturate all lanes merely because capacity exists. |
| `DeepSeek` | `AVAILABLE` | Preferred lane for bounded non-production contract tracing, low-risk implementation, localization work, mechanical/schema consistency, regression and targeted verification where risk permits. DeepSeek may provide supplementary/pre-review evidence for high-risk work, but does not by itself satisfy final high-risk acceptance review where `REVIEW_PROTOCOL.md` requires Codex/Claude-class review. |
| `GPT / Web GPT` | `AVAILABLE FOR ORCHESTRATION` | Development Director / Track coordination; not default production implementation or substitute high-risk final reviewer. |

## Mandatory Routing Rule

With Claude restored and Codex in a fresh weekly window:

- controlled parallelism is authorized where dependencies and write surfaces are disjoint;
- finish already-open mandatory exact-SHA reviews and closeout gates before allowing their unresolved dependencies to contaminate later integration;
- high-risk `Implementation Agent != Independent Reviewer` remains mandatory;
- prefer Claude for highest-value adversarial review, complex cross-owner/core work, or cases where architectural judgment materially improves confidence;
- use Codex for core implementation, exact-SHA review, integration/regression, replay/recovery/persistence correctness, and bounded blocking fixes;
- DeepSeek remains preferred for Language/Localization and other low-risk/mechanical work;
- avoid filling every available lane with speculative work; each concurrent lane must have a clear dependency/write-surface reason;
- architecture/security/Owner-boundary/stale/exact-SHA/independent-review requirements are unchanged.

## Execution Mode Failover

Codex assignments may begin in Chat mode. If a Codex session encounters tool execution, repository-write, workspace, or environment errors and there is no durable Task-scoped technical/architecture blocker evidence, treat that signal first as an execution-mode failure rather than a Product blocker.

The Operator may continue the **same Task ID and Scope** in Work mode. A Chat → Work mode switch does not create a new Task, does not reset the required base/SHA, and does not waive Result/checkpoint/review requirements. Only durable Repository evidence may establish a substantive blocker.

## Current Controlled-Parallelism Priority

1. close the currently open Provider foundation blocking-fix chain from Task 161;
2. use the existing Task `NYRON-T-20260828-162` for the targeted fix of the three blocking Provider findings;
3. after Task 162 produces an exact delivery SHA, route a fresh independent targeted Re-Review, preferably to Claude while current restored capacity is available;
4. only after that chain passes may Provider consequential next-slice work be considered;
5. next Track-D consequential external-effect slices should open only with explicit Task scoping and accepted dependency basis.

## Parallelism Rule

A fresh quota window permits multiple lanes, but concurrency remains dependency-driven:

- `Review lane` may run alongside disjoint low-risk Product-support work;
- `Implementation lane` may run alongside review only when it does not mutate the exact SHA under review and has a disjoint write surface;
- final integration/convergence must wait for all required dependency reviews whose content is intended to be included;
- avoid simultaneous high-risk edits to shared persistence/authority surfaces unless separately isolated and integration order is explicit.

## Temporary Window Rule

Codex and Claude are both currently available. This does not imply unlimited useful parallelism. The Development Director may expand or reduce active lanes according to dependency, write-surface isolation, review independence and integration load.

## Change Rule

Agent availability remains operational state and may be superseded only by later explicit Operator / Development Director instruction.
