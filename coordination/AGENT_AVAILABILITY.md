# Agent Availability

Status: `ACTIVE OPERATIONAL COORDINATION STATE`
Authority: `Development Director / Global Development Coordination Authority`
Date: `2026-08-27`

This file records current operational availability only. It does not define permanent model capability and does not amend architecture.

## Current Availability

| Agent | Availability | Default Use While State Applies |
|---|---|---|
| `Claude` | `UNAVAILABLE` | Do not assign new implementation, fix, review, re-review, or specialist work. Do not request a new Claude window. |
| `Codex` | `UNAVAILABLE — QUOTA EXHAUSTED / CLOSEOUT HOLD` | Do not dispatch new Codex work until the Operator explicitly restores capacity. Already completed Repository deliveries remain valid; pending mandatory high-risk reviews stay pending rather than being downgraded or reassigned to an ineligible reviewer. |
| `DeepSeek` | `AVAILABLE` | Preferred lane for bounded non-production contract tracing, low-risk implementation, mechanical/schema consistency, regression and targeted verification where risk permits. DeepSeek may provide supplementary/pre-review evidence for high-risk work, but does not by itself satisfy final high-risk acceptance review where `REVIEW_PROTOCOL.md` requires Codex/Claude-class review. |
| `GPT / Web GPT` | `AVAILABLE FOR ORCHESTRATION` | Development Director / Track coordination; not default production implementation or substitute high-risk final reviewer. |

## Mandatory Routing Rule

While Claude is `UNAVAILABLE` and Codex quota is exhausted:

- do not create or dispatch new Claude assignments;
- do not dispatch new Codex assignments until capacity is explicitly restored;
- preserve already-delivered candidates and their exact-SHA review targets;
- high-risk `Implementation Agent != Independent Reviewer` remains mandatory;
- do not downgrade a mandatory high-risk exact-SHA review to DeepSeek solely because Codex quota is unavailable;
- DeepSeek may perform bounded low-risk/mechanical work, targeted verification, or supplementary pre-review where useful, but such work does not close a high-risk independent-review gate by itself;
- if no currently available agent satisfies the required risk/independence class, keep the delivery `PENDING_INDEPENDENT_REVIEW` / capacity-held rather than weakening the gate;
- capacity pressure never authorizes weakening architecture, security, Owner boundaries, stale-check rules, exact-SHA requirements, or independent review.

## Execution Mode Failover

When Codex capacity is available, assignments may begin in Chat mode. If a Codex session encounters tool execution, repository-write, workspace, or environment errors and there is no durable Task-scoped technical/architecture blocker evidence, treat that signal first as an execution-mode failure rather than a Product blocker.

The Operator may continue the **same Task ID and Scope** in Work mode. A Chat → Work mode switch does not create a new Task, does not reset the required base/SHA, and does not waive Result/checkpoint/review requirements. Only durable Repository evidence may establish a substantive blocker.

## Closeout Priority

When eligible reviewer capacity is restored, current closeout priority is:

1. complete mandatory exact-SHA review for Task 142 (`NYRON-T-20260827-148`);
2. complete mandatory exact-SHA review for Task 144;
3. perform only blocking fixes/re-reviews required by those reviews;
4. close or checkpoint the current Foundation / Track D wave cleanly;
5. leave optional next-slice implementation for a later restored-capacity window.

## Temporary Window Rule

This Codex quota-exhausted state is operator-reported operational truth for the current quota window. A later quota reset does not automatically reopen broad Codex parallelism; the Operator / Development Director must explicitly restore availability and choose the next closeout actions.

## Change Rule

Agent availability remains operational state and may be superseded only by later explicit Operator / Development Director instruction.
