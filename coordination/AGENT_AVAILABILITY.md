# Agent Availability

Status: `ACTIVE OPERATIONAL COORDINATION STATE`
Authority: `Development Director / Global Development Coordination Authority`
Date: `2026-08-27`

This file records current operational availability only. It does not define permanent model capability and does not amend architecture.

## Current Availability

| Agent | Availability | Default Use While State Applies |
|---|---|---|
| `Claude` | `UNAVAILABLE` | Do not assign new implementation, fix, review, re-review, or specialist work. Do not request a new Claude window. |
| `Codex` | `CONSTRAINED / NO NEW TRACK WORK` | Current quota/capacity is near exhaustion. Do not assign new Track work. Existing already-routed closure work may finish if capacity remains. Restore only by later explicit Operator / Development Director decision. |
| `DeepSeek` | `AVAILABLE` | Preferred current lane for non-production readiness/contract/security audit, low-risk bounded implementation, mechanical/schema consistency, regression and targeted verification where risk permits. |
| `GPT / Web GPT` | `AVAILABLE FOR ORCHESTRATION` | Development Director / Track coordination; not default production implementation. |

## Mandatory Routing Rule

While Claude is `UNAVAILABLE` and Codex is `CONSTRAINED / NO NEW TRACK WORK`:

- do not create new Claude assignments;
- do not create new Codex Track assignments;
- use DeepSeek only for Tasks whose risk/scope is suitable;
- prefer non-production audit/readiness work and bounded low-risk implementation for DeepSeek;
- do not assign DeepSeek sole responsibility for high-risk external-effect/security-critical Production merely to avoid a capacity blocker;
- high-risk `Implementation Agent != Independent Reviewer` remains mandatory;
- if no available Agent can satisfy implementation, specialist review, or independence requirements, record `BLOCKED` rather than weakening requirements.

## Change Rule

Claude and Codex availability states remain in force until a later explicit Operator / Development Director instruction changes or supersedes them.
