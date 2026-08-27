# Dispatch Format

Status: `ACTIVE COORDINATION PROCESS RULE`
Authority: `Development Director / Global Development Coordination Authority`
Date: `2026-08-27`

## Principle

Formal Task content lives in Repository files. Chat dispatch must not duplicate the Task body.

When a formal Task already exists at `coordination/tasks/<TaskID>.md`, the dispatch message only identifies the Track dispatch label, repository, authority relationship, Repository Truth entrypoint, formal Task ID/path, assigned role/model, and completion behavior.

The Agent must read the formal Task file and execute it exactly. Scope, Out of Scope, Constraints, Validation, Deliverables, review requirements and remote-delivery evidence remain authoritative in the Task and protocol files and should not be copied into chat unless a narrow clarification is necessary.

## Standard Dispatch Template

```text
[TRACK_<LETTER>_TASK_<NNN>]

Repository：
`https://github.com/ahhhh450/nyron`

你的上级是：
`Development Director / Global Development Coordination Authority`

你不是 Development Director，也不是 Track Orchestrator。

## Repository Truth

先读取：
1. `coordination/STATUS.md`
2. `coordination/AGENT_AVAILABILITY.md`
3. `coordination/tasks/<TaskID>.md`
4. Task 文件中的 Required Reading

正式 Task：
`<TaskID>`

Task 文件：
`coordination/tasks/<TaskID>.md`

严格按照 Task 文件执行，不扩展 Scope。

完成后按 Repository 协议落盘 Result / Review / Checkpoint。

聊天只返回：
`TASK DONE`

阻塞则：
`TASK BLOCKED`
```

## Rules

- `[TRACK_X_TASK_NNN]` is a chat dispatch label only; it is not the canonical `NYRON-T-*` Task ID.
- Do not repeat the full Task body in chat when the Task is already remotely readable.
- Do not require the Operator to relay Result content between windows.
- Current Agent availability in `coordination/STATUS.md` / `coordination/AGENT_AVAILABILITY.md` overrides older model preferences.
- If a Task-specific clarification is needed, add only that clarification; do not duplicate the full Task specification.
