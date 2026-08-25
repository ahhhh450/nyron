# Orchestrator Handoff

- Previous Orchestrator: `...`
- New Orchestrator: `...`
- Previous Epoch: `...`
- New Epoch: `...`
- Previous Revision: `...`
- New Revision: `...`
- Last Accepted Commit: `...`

## Active Tasks

- ...

## In Review

- ...

## Blocked

- ...

## Review Debt

- `NONE`，或列出仍待独立 Review 的 Task / Delivery。

## Open Findings

- ...

## Pending Decisions

- ...

## Stable Baseline

- ...

## Next Eligible Actions

- ...

## Handoff Rule

新 Orchestrator 接管必须通过协调 CAS 更新完成后才生效。旧 Epoch 的新增协调动作默认视为 stale。项目事实以最新 `coordination/STATUS.md` 和已接受 Result 为准，不依赖旧聊天上下文。
