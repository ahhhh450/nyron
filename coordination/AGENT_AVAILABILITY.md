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

1. `NYRON-T-20260828-171` is the current P0 Product-mainline Task: Codex `NODE FOUNDATION v0.1` bounded Production implementation;
2. Task 171 owns the bounded Graph multi-instance/Edge publish completion plus Product Node/Workflow persistence/compiler and the pure/mock `Text Input → Mock LLM → Text Output` proof;
3. after Task 171 delivers an exact Production SHA, reserve an independent Claude session for the mandatory HIGH-risk exact-SHA Review unless the Development Director explicitly chooses another independent Codex-class reviewer;
4. `NYRON-T-20260828-168` remains `PAUSED — PRODUCT-VERTICAL-SLICE HOLD`; restored Codex capacity does not by itself authorize resuming it;
5. `NYRON-T-20260828-169` remains `DEFERRED / NOT STARTED`; resume only when Human Approval Product Node creates the concrete need;
6. lower-level Track A/B/C/D work opens or resumes only when a concrete Product Node requires a missing capability or a true blocker demands it.

## Parallelism Rule

A fresh quota window permits multiple lanes, but concurrency remains dependency-driven:

- `Review lane` may run alongside disjoint low-risk Product-support work;
- `Implementation lane` may run alongside review only when it does not mutate the exact SHA under review and has a disjoint write surface;
- final integration/convergence must wait for all required dependency reviews whose content is intended to be included;
- avoid simultaneous high-risk edits to shared persistence/authority surfaces unless separately isolated and integration order is explicit;
- do not create speculative work merely to occupy available Agent capacity.

## Temporary Window Rule

Codex and Claude are both currently available. This does not imply unlimited useful parallelism. The Development Director may expand or reduce active lanes according to dependency, write-surface isolation, review independence and integration load.

## Change Rule

Agent availability remains operational state and may be superseded only by later explicit Operator / Development Director instruction.
