# Checkpoint

- Task ID: `T-YYYYMMDD-NNN`
- Checkpoint ID: `<TaskID>-CP-NNN`
- Type: `PROGRESS | HANDOFF`
- Agent: `...`
- Coordination Epoch: `...`
- Based On Coordination Revision: `...`
- Trigger: `MILESTONE | FILE_THRESHOLD | COMMIT_THRESHOLD | HANDOFF | BLOCKER | PAUSE | OTHER`

## Current Step

- ...

## Completed

- ...

## Remaining

- ...

## Files Touched

- ...

## Validation

- ...

## Findings

- `NONE`

## Blockers

- `NONE`

## Next Action

- ...

## Persistence Rule

Checkpoint 应创建新文件，不覆盖旧 Checkpoint。

推荐：
```text
<TaskID>-CP-001.md
<TaskID>-CP-002.md
...
```

> Final Result 生成后，本 Checkpoint 仅保留为历史过程记录，不覆盖 Final Result。
