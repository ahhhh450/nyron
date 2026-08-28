# Nyron Language / Localization Track Board v0.1

Status: `ACTIVE TRACK-LOCAL COORDINATION BOARD / NOT ARCHITECTURE`
Authority: `Development Director / Global Development Coordination Authority`
Track Orchestrator: `DeepSeek — Language / Localization Orchestrator`
Date: `2026-08-28`

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
| Language Track | `STABLE / IDLE` | Foundation slice accepted by Development Director |
| Localization core | `ACCEPTED FOR DOWNSTREAM PRODUCT-SUPPORT USE` | Task `NYRON-T-20260827-150`, exact SHA `b5c14545e8e7e7554c0173bb214788200e064ff1` |
| `zh-CN` | `SUPPORTED BUILT-IN` | Task 150 |
| `en-US` | `SUPPORTED BUILT-IN` | Task 150 |
| Third-locale extensibility proof | `PASS` | Synthetic additional locale coverage in Task 150 tests |
| Product UI language selector | `DEFERRED` | Product layer not activated |
| User locale persistence | `DEFERRED` | Out of Task 150 scope |
| Automatic content translation | `DEFERRED / SEPARATE CAPABILITY` | Not part of i18n foundation |
| STT/TTS locale routing | `DEFERRED / SEPARATE CAPABILITY` | Not part of i18n foundation |

## Accepted Foundation

`NYRON-T-20260827-150 — Extensible Multilingual Localization Foundation`

Accepted delivery SHA:

`b5c14545e8e7e7554c0173bb214788200e064ff1`

Director acceptance evidence:

`coordination/checkpoints/NYRON-T-20260827-150-DIRECTOR-ACCEPTANCE.md`

Validation evidence:

- localization focused: `30 passed`;
- kernel regression: `416 passed, 2 skipped, 380 subtests passed`;
- Findings: `NONE`;
- Blockers: `NONE`;
- no `src/nyron_kernel/**` changes.

## Near-Term Milestones

### L-1 — Localization Foundation

`COMPLETE / ACCEPTED FOR DOWNSTREAM PRODUCT-SUPPORT USE`

Delivered:

- catalog-driven localization;
- `zh-CN` + `en-US` built-ins;
- fallback;
- placeholder interpolation;
- malformed/conflicting catalog rejection;
- synthetic third-locale extensibility proof;
- no Kernel changes.

### L-2 — Track Review / Stable Candidate

`COMPLETE`

- exact Repository delivery independently inspected by Language Orchestrator;
- focused and kernel tests independently re-run;
- LOW-risk independent Review classified as optional rather than mandatory;
- no Fix/Re-Review required;
- Development Director acceptance recorded.

### L-3 — Product Consumption Preparation

`DEFERRED`

Only after Product/Visual Workflow work actually begins:

- language selector integration;
- Product string-key inventory;
- glossary growth;
- key parity tooling as justified;
- user locale preference persistence through the Product-owned/configured layer selected by global architecture.

Do not start L-3 merely because L-1/L-2 are complete.

### L-4 — Additional Locale

`ON DEMAND`

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

Dedicated Track Orchestrator remains authorized because localization is expected to become recurring and parallelizable as Product UI grows, with separate development, translation, catalog validation and review work.

The Track is currently `STABLE / IDLE`. Do not create Tasks merely to keep the Orchestrator busy. Reactivate only for explicit localization work or Product consumption preparation authorized by the Development Director.
