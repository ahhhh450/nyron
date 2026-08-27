# Nyron Language / Localization Track Board v0.1

Status: `ACTIVE TRACK-LOCAL COORDINATION BOARD / NOT ARCHITECTURE`
Authority: `Development Director / Global Development Coordination Authority`
Track Orchestrator: `DeepSeek — Language / Localization Orchestrator`
Date: `2026-08-27`

## Purpose

Provide a bounded control surface for Nyron localization/i18n development without expanding the System Foundation or Product architecture.

## Track Scope

Owned implementation surface:

- `src/nyron_i18n/**`
- localization catalogs / locale assets
- `tests/i18n/**` or equivalent isolated tests
- localization documentation / glossary

Current supported locales:

- `zh-CN`
- `en-US`

Future locales are expected to be catalog-driven additions.

## Current State

| Item | State | Evidence / Gate |
|---|---|---|
| Language Track | `ACTIVATING` | Dedicated DeepSeek Language Orchestrator authorized |
| Localization core | `ASSIGNED` | Task `NYRON-T-20260827-150` |
| `zh-CN` | `PLANNED BUILT-IN` | Task 150 |
| `en-US` | `PLANNED BUILT-IN` | Task 150 |
| Third-locale extensibility proof | `REQUIRED` | Task 150 validation |
| Product UI language selector | `DEFERRED` | Product layer not activated |
| User locale persistence | `DEFERRED` | Out of Task 150 scope |
| Automatic content translation | `DEFERRED / SEPARATE CAPABILITY` | Not part of i18n foundation |
| STT/TTS locale routing | `DEFERRED / SEPARATE CAPABILITY` | Not part of i18n foundation |

## Active Task

`NYRON-T-20260827-150 — Extensible Multilingual Localization Foundation`

Execution assignment:

`DeepSeek — Localization Foundation Implementation`

The persistent Language Orchestrator session must route Task 150 to a separate implementation session and must not implement it itself.

## Near-Term Milestones

### L-1 — Localization Foundation

Complete Task 150:

- catalog-driven localization;
- `zh-CN` + `en-US` built-ins;
- fallback;
- placeholder interpolation;
- malformed/conflicting catalog rejection;
- synthetic third-locale extensibility proof;
- no Kernel changes.

### L-2 — Track Review / Stable Candidate

After Task 150 Result:

- inspect exact delivery SHA;
- classify whether independent LOW-risk review is required/useful;
- perform bounded review/fix/re-review if needed;
- record Track-local stable candidate evidence;
- report to Development Director.

### L-3 — Product Consumption Preparation

Only after Product/Visual Workflow work actually begins:

- language selector integration;
- Product string-key inventory;
- glossary growth;
- key parity tooling as justified;
- user locale preference persistence through the Product-owned/configured layer selected by global architecture.

Do not start L-3 merely because L-1 finishes.

### L-4 — Additional Locale

When explicitly requested, add locales through bounded Track Tasks. Expected default sequence:

```text
catalog
→ translation
→ placeholder/key parity validation
→ focused tests
→ review as risk requires
```

No core lookup redesign unless a genuine locale requirement proves it necessary.

## Hard Interlocks

- `src/nyron_kernel/**` is outside Track authority.
- No frozen architecture changes.
- No other canonical Owner mutation.
- No Provider/LLM machine-translation integration without a separate Development Director authorization because that touches external-provider boundaries.
- No security/legal/approval/billing semantic translation should be accepted casually; ambiguous or consequence-bearing wording requires escalation/review appropriate to risk.
- Global acceptance remains Development Director authority.

## Orchestration Mode

Dedicated Track Orchestrator is justified because localization is expected to become recurring and parallelizable as Product UI grows, with separate development, translation, catalog validation and review work.

The Track remains intentionally lightweight. Do not create Tasks merely to keep the Orchestrator busy.
