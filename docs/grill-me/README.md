# Nyron /grill me Interactive Rounds

This directory stores interactive frontier rounds for Nyron design interviews.

## Workflow

1. Open the current round HTML.
2. For every frontier question, choose:
   - **OK** — accept the recommended answer; or
   - **补充 / 修改** — provide the user's correction, constraint, or counterexample.
3. Click **提交结果到 GitHub**.
4. Submit the prefilled GitHub Issue.
5. Tell ChatGPT the round is complete.
6. ChatGPT reads the Issue, updates the design tree, recomputes the frontier, and creates the next round only from decisions whose prerequisites are settled.

The HTML auto-saves answers in browser localStorage until submitted.

## Rounds

- Round 001 — `docs/grill-me/round-001.html`
  - issue prefix: `[NYRON-GRILL-R01]`
  - status: ACTIVE

## Rules

The governing interview protocol is:

- `skills/grill-me/SKILL.md`

Previous rounds are immutable historical questionnaires. A new frontier creates a new round file rather than overwriting an earlier round.
