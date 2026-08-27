# Agent Availability

Status: `ACTIVE OPERATIONAL COORDINATION STATE`
Authority: `Development Director / Global Development Coordination Authority`
Date: `2026-08-27`

This file records current operational availability only. It does not define permanent model capability and does not amend architecture.

## Current Availability

| Agent | Availability | Default Use While State Applies |
|---|---|---|
| `Claude` | `UNAVAILABLE` | Do not assign new implementation, fix, review, re-review, or specialist work. Do not request a new Claude window. |
| `Codex` | `AVAILABLE` | Primary implementation / correctness / tests / CI / independent review lane, subject to required independence. |
| `DeepSeek` | `AVAILABLE` | Low-risk, mechanical, schema/document consistency, regression, targeted verification/review where risk permits. |
| `GPT / Web GPT` | `AVAILABLE FOR ORCHESTRATION` | Development Director / Track Orchestrator coordination; not default production implementation. |

## Mandatory Routing Rule

While Claude is `UNAVAILABLE`:

- existing generic guidance that prefers Claude for architecture-sensitive work is suspended operationally;
- Track Orchestrators must choose an available Agent that satisfies the Task's risk and independence requirements;
- Codex is the default substitute for complex implementation and high-risk code review when suitable;
- DeepSeek may be used only where the Task risk/scope permits;
- high-risk `Implementation Agent != Independent Reviewer` remains mandatory;
- if no available Agent can provide required independent/specialist review, record `BLOCKED` rather than weakening review requirements.

## Change Rule

Claude remains unavailable until a later explicit Operator / Development Director instruction changes this file or supersedes it through a newer coordination decision.
