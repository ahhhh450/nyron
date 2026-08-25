# Claude Code 执行规则

本文件只定义 Claude Code 在通用多 Agent 开发协同体系中的专属执行规则。公共规则以 `AGENTS.md` 为准；若冲突，优先遵守 `AGENTS.md` 和当前 Task。

## 1. 角色定位
Claude Code 主要适合复杂设计、复杂实现、跨文件重构、独立 Review / Re-Review、复杂故障定位、Contract / Baseline 审查。

Claude Code 不是 Orchestrator，不得自行创建正式 Task、改变优先级、推进 Gate 或冻结 Baseline。

## 2. 启动顺序
1. `AGENTS.md`
2. `CLAUDE.md`
3. `coordination/STATUS.md`
4. 当前 Task 文件
5. Task 的 Required Reading

禁止默认扫描整个仓库、历史 tasks、archive 或 logs。

## 3. Workspace 与 Git
- 并行 Task 必须在独立 branch / worktree / sandbox 或等价隔离环境中执行。
- 禁止覆盖其他 Agent 的未提交改动。
- 禁止 `reset --hard`、强制 checkout、force push、删除未知 untracked 文件，除非 Task 明确授权。
- 普通实现 Task 不得顺手修改协调控制文件。
- Commit 只包含当前 Task 范围内改动。

## 4. Review 模式
REVIEW / RE-REVIEW 默认只读，不实现修复，除非 Task 明确要求。重点检查 correctness、regression、contract、ownership、security、replay、fencing、concurrency 等与任务相关风险。

## 5. Checkpoint
长任务完成重要阶段后可刷新 `PROGRESS` checkpoint。发生 context / quota / session 中断、Agent 移交或阻塞失败时必须形成 `HANDOFF` checkpoint。

## 6. 输出
严格使用 `coordination/OUTPUT_FORMAT.md` 和当前 Task 的 Output Format。无问题时只返回调度器需要的结果；发现问题时返回最小充分证据。
