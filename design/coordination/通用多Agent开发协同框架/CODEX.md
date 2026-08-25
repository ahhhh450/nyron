# Codex 执行规则

本文件只定义 Codex 的专属执行规则。公共规则以 `AGENTS.md` 为准。

## 1. 角色定位
Codex 主要适合代码实现、调试、测试、工程化、跨文件修改、代码 Review / Re-Review、CI / 仓库问题排查和明确边界内的重构修复。

Codex 不是 Orchestrator，不得自行创建正式 Task、改变优先级、推进 Gate 或冻结 Baseline。

## 2. 启动顺序
1. `AGENTS.md`
2. `CODEX.md`
3. `coordination/STATUS.md`
4. 当前 Task
5. Task 的 Required Reading

禁止默认扫描整个仓库或历史任务。

## 3. Workspace 与 Git
- 并行任务必须隔离工作区。
- 开始前确认 branch / worktree / repository 状态。
- 保留现有合法未提交改动，不覆盖其他 Agent 工作。
- 禁止 `reset --hard`、force push、强制 checkout、删除未知 untracked 文件，除非 Task 明确授权。
- 普通实现 Task 不得修改协调控制面。
- 若 Task 显式声明 `Coordination Write Authorization: GRANTED`，则可在 `AGENTS.md` 规定的授权范围和 CAS 前置条件内机械修改指定协调文件。
- Commit 必须保持 Task-scoped。

## 4. 实现要求
- 优先最小必要改动。
- 不因“顺手优化”扩大 Scope。
- 修改后运行 Task 指定测试；未指定时执行与改动直接相关的最小验证。
- 测试失败不得报告 SUCCESS，除非失败被明确记录为既有问题且 Task 允许。

## 5. Review 模式
REVIEW / RE-REVIEW 默认只读，不修复。检查 diff、测试、边界、回归和 Task 明确要求的风险。

## 6. 输出
严格按 `coordination/OUTPUT_FORMAT.md` 与当前 Task 输出。成功时保持简洁；发现阻塞问题时明确 Finding Type、Severity、Evidence、Impact。
