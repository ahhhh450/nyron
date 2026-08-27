# Agent Availability

Status: `ACTIVE OPERATIONAL COORDINATION STATE`
Authority: `Development Director / Global Development Coordination Authority`
Date: `2026-08-27`

This file records current operational availability only. It does not define permanent model capability and does not amend architecture.

## Current Availability

| Agent | Availability | Default Use While State Applies |
|---|---|---|
| `Claude` | `UNAVAILABLE` | Do not assign new implementation, fix, review, re-review, or specialist work. Do not request a new Claude window. |
| `Codex` | `AVAILABLE — TEMPORARY PARALLEL CAPACITY WINDOW` | Operator explicitly restored Codex for the current quota window. Multiple parallel Codex sessions are authorized where dependencies and write surfaces are independent. Prioritize high-value security/correctness review and bounded high-risk work; do not create artificial work only to consume quota. |
| `DeepSeek` | `AVAILABLE` | Preferred lane for bounded non-production contract tracing, low-risk implementation, mechanical/schema consistency, regression and targeted verification where risk permits. |
| `GPT / Web GPT` | `AVAILABLE FOR ORCHESTRATION` | Development Director / Track coordination; not default production implementation. |

## Mandatory Routing Rule

While Claude is `UNAVAILABLE` and the temporary Codex parallel window is active:

- do not create new Claude assignments;
- Codex may receive multiple parallel Tasks when dependency, workspace/write-surface, review-independence and integration safety permit;
- prefer independent read-only specialist/security reviews in parallel before opening conflicting Production writes;
- high-risk `Implementation Agent != Independent Reviewer` remains mandatory;
- do not use the same Codex session as both implementation and independent reviewer for a high-risk delivery;
- DeepSeek remains suitable for bounded low-risk/mechanical work and targeted verification;
- capacity availability never authorizes weakening architecture, security, Owner boundaries, stale-check rules, or exact-SHA review requirements.

## Temporary Window Rule

This Codex state is an operator-authorized temporary capacity window. It remains active until the Operator / Development Director explicitly closes or changes it. Quota reset/exhaustion does not itself amend architecture; coordination should re-evaluate active assignments when capacity changes.

## Change Rule

Agent availability remains operational state and may be superseded only by later explicit Operator / Development Director instruction.
