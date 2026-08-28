# Coordination 控制面

本目录保存多 Agent 开发的调度状态与协议，不保存业务实现。

## 权威边界
- Web GPT / Active Orchestrator：唯一 Coordination Authority。
- Codex / Claude Code / DeepSeek：Execution Agent，可按 Task 执行受控写入，但不得自行裁决项目状态。

## 推荐读取顺序

### Orchestrator
1. `STATUS.md`
2. `AGENT_AVAILABILITY.md`
3. `WORKFLOW.md`
4. 当前 Task / Result / Checkpoint
5. 如为新窗口接管，读取 `handoffs/LATEST.md` 作为恢复辅助
6. 必要的设计与代码

> Handoff 只是恢复辅助，不是 Repository Truth。Handoff 与当前 STATUS / Task / Result / Checkpoint / Frozen Architecture 冲突时，以当前 Repository 权威状态为准。

### Executor
1. 根目录 `AGENTS.md`
2. 自己的专属规则文件
3. `STATUS.md`
4. 当前 Task
5. Task 的 Required Reading

## 目录
```text
coordination/
├─ README.md
├─ STATUS.md
├─ AGENT_AVAILABILITY.md
├─ WORKFLOW.md
├─ TASK_PROTOCOL.md
├─ REVIEW_PROTOCOL.md
├─ OUTPUT_FORMAT.md
├─ handoffs/
│  ├─ LATEST.md
│  └─ <dated handoff>.md
├─ templates/
│  ├─ TASK_TEMPLATE.md
│  ├─ RESULT_TEMPLATE.md
│  └─ CHECKPOINT_TEMPLATE.md
├─ tasks/
├─ results/
├─ checkpoints/
└─ archive/
```

`templates/` 保存模板；`tasks/`、`results/`、`checkpoints/` 保存真实运行记录，二者不得混用。
