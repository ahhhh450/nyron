# Agent Availability

Status: `ACTIVE OPERATIONAL COORDINATION STATE`
Authority: `Development Director / Global Development Coordination Authority`
Date: `2026-08-27`

This file records current operational availability only. It does not define permanent model capability and does not amend architecture.

## Current Availability

| Agent | Availability | Default Use While State Applies |
|---|---|---|
| `Claude` | `UNAVAILABLE` | Do not assign new implementation, fix, review, re-review, or specialist work. Do not request a new Claude window. |
| `Codex` | `CONSERVATION / CLOSEOUT WINDOW` | Remaining quota is being conserved. Existing active Tasks may finish. Do not automatically refill freed lanes. New Codex work is limited to mandatory exact-SHA review/re-review, blocking fixes required to close already-open gates, and final integration/regression verification. Do not open broad exploratory/specialist work merely because capacity remains. |
| `DeepSeek` | `AVAILABLE` | Preferred lane for bounded non-production contract tracing, low-risk implementation, mechanical/schema consistency, regression and targeted verification where risk permits. |
| `GPT / Web GPT` | `AVAILABLE FOR ORCHESTRATION` | Development Director / Track coordination; not default production implementation. |

## Mandatory Routing Rule

While Claude is `UNAVAILABLE` and Codex is in conservation / closeout mode:

- do not create new Claude assignments;
- allow already-running Codex Tasks to finish;
- do not automatically refill a Codex lane when it becomes free;
- reserve new Codex assignments for mandatory exact-SHA review/re-review, blocking fixes needed to close an already-open gate, or final integration/regression verification;
- defer new broad Track expansion, exploratory specialist review, and optional hardening until capacity is restored;
- high-risk `Implementation Agent != Independent Reviewer` remains mandatory;
- do not use the same Codex session as both implementation and independent reviewer for a high-risk delivery;
- use DeepSeek for bounded low-risk/mechanical work and targeted verification where its risk class permits;
- capacity pressure never authorizes weakening architecture, security, Owner boundaries, stale-check rules, exact-SHA requirements, or independent review.

## Execution Mode Failover

Current Codex assignments may begin in Chat mode. If a Codex session encounters tool execution, repository-write, workspace, or environment errors and there is no durable Task-scoped technical/architecture blocker evidence, treat that signal first as an execution-mode failure rather than a Product blocker.

The Operator may continue the **same Task ID and Scope** in Work mode. A Chat → Work mode switch does not create a new Task, does not reset the required base/SHA, and does not waive Result/checkpoint/review requirements. Only durable Repository evidence may establish a substantive blocker.

## Closeout Priority

Current closeout priority is:

1. finish already-running high-risk implementation/review Tasks;
2. complete mandatory exact-SHA reviews for already-delivered candidates;
3. perform only the fixes/re-reviews required by those reviews;
4. close or checkpoint the current Foundation / Track D wave cleanly;
5. leave optional next-slice implementation for a later restored-capacity window.

## Temporary Window Rule

This Codex conservation state is operator-authorized operational state for the current quota window. It remains active until the Operator / Development Director explicitly changes it. A later quota reset may restore broader Codex use only by explicit coordination decision.

## Change Rule

Agent availability remains operational state and may be superseded only by later explicit Operator / Development Director instruction.
