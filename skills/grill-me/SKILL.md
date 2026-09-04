---
name: grill-me
description: Relentlessly interview the user to sharpen a plan, design, or decision by exhausting a dependency-aware design tree.
---

# /grill me

## Purpose

Use this skill when the user asks to `/grill me`, asks to stress-test a design, or wants a decision tree driven to shared understanding before implementation.

The goal is not to produce a design on the user's behalf. The goal is to expose assumptions, branch the design into explicit decisions, and keep interviewing until no decision remains silently assumed.

## Core model: design tree

Represent the design as a dependency tree.

- A decision may unlock downstream decisions.
- The **frontier** is the set of all decisions whose prerequisites are already settled.
- Ask the **whole current frontier in one round**.
- Do not ask a question whose answer depends on another still-open question in the same round; leave it for the next round.
- After the user answers, recompute the frontier from the updated tree.

Do not degrade into one-question-at-a-time interviewing when multiple independent frontier questions are already decidable.

## Round format

Each frontier question must be numbered and include a recommendation.

Preferred shape:

```text
❓ **Q1 - <title>**: <decision, context, options if useful>

➡️ <recommended answer>

---

❓ **Q2 - <title>**: <decision, context, options if useful>

➡️ <recommended answer>
```

The user owns decisions. Recommendations are advisory, not implicit approval.

## Facts vs decisions

Finding facts is the assistant/agent's job.

- Do not ask the user for facts that can be obtained from the repository, filesystem, tools, runtime state, documentation, or connected systems.
- Gather those facts independently.
- A fact-gathering branch that is still unresolved blocks only its downstream decisions; continue asking the rest of the current frontier.
- Ask the user only for actual product/design choices, preferences, authority decisions, risk tolerances, or other decisions that belong to them.

## Completion rule

The grilling session is complete only when:

1. the frontier is empty;
2. every reachable design branch has been visited or explicitly deferred;
3. no material assumption remains silently unresolved; and
4. the user confirms shared understanding.

Do **not** move into implementation merely because several decisions have been accepted.

## Nyron-specific operating constraints

When this skill is used for Nyron design discussions:

- Treat existing Frozen Baselines and accepted Amendments as higher authority than a conversational recommendation.
- Do not silently rewrite frozen architecture through a grill answer. Surface a conflict as a design finding/change-control question.
- Keep confirmed decisions distinct from open questions.
- Do not label a decision "frozen" merely because the assistant recommended it; it becomes an accepted discussion decision only after the user confirms it.
- When talking with Claude or another design reviewer, compress the response to:
  - the current frontier questions;
  - material reviewer objections/loopholes;
  - the assistant's recommendation;
  - only the minimum context needed to decide.
- Avoid long explanatory essays unless the user explicitly asks to expand a specific question.
- If a reviewer identifies a prerequisite that invalidates a current frontier question, repair the tree before continuing.

## Anti-patterns

Do not:

- ask one question per turn when several independent frontier decisions are available;
- repeatedly say "freeze this" and substitute assistant judgment for user decisions;
- keep drilling downstream details whose prerequisite is still unsettled;
- ask the user to research facts the system can inspect itself;
- mix implementation work into an unfinished grilling session;
- treat chat history as the authoritative design store when a durable repository record is required.
