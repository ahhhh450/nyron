# Claude Code 执行规则

本文件只定义 Claude Code 在通用多 Agent 开发协同体系中的专属执行规则。公共规则以 `AGENTS.md` 为准。

## 1. 角色定位
Claude Code 主要适合复杂设计、复杂实现、跨文件重构、独立 Review / Re-Review、复杂故障定位、Contract / Baseline 审查。

Claude Code 不是 Orchestrator，不得自行创建正式 Task、改变优先级、推进 Gate 或冻结 Baseline。

## 2. 启动顺序
1. `AGENTS.md`
2. `CLAUDE.md`
3. `coordination/STATUS.md`
4. 当前 Task 文件
5. Task 的 Required Reading
6. 按 Task 类型读取对应 Skill：
   - Implementation / Fix / Refactor → `skills/implementation/SKILL.md`
   - Review / Re-Review → `skills/code-review/SKILL.md`
   - Testing → `skills/testing/SKILL.md`

禁止默认扫描整个仓库、历史 tasks、archive 或 logs。

## 3. Workspace 与 Git
- 并行 Task 必须在独立 branch / worktree / sandbox 或等价隔离环境中执行。
- 禁止覆盖其他 Agent 的未提交改动。
- 禁止 `reset --hard`、强制 checkout、force push、删除未知 untracked 文件，除非 Task 明确授权。
- 普通实现 Task 不得顺手修改协调控制文件。
- 若 Task 显式声明 `Coordination Write Authorization: GRANTED`，则可在 `AGENTS.md` 规定的授权范围和 CAS 前置条件内机械修改指定协调文件。
- Commit 只包含当前 Task 范围内改动。

## 4. 实现要求
Implementation / Fix / Refactor Task 默认遵守 `skills/implementation/SKILL.md`。

即使任务本身复杂，也应区分：

```text
required structural complexity
vs
speculative complexity
```

当前 Task / Frozen Contract 要求的复杂结构必须保留；除此之外，不因为“大上下文可以顺手做得更完整”而主动引入额外 framework、abstraction、registry、plugin/extensibility layer。

当选择非平凡复杂方案时，应能明确指出其当前 requirement / invariant 来源。

## 5. Review 模式
REVIEW / RE-REVIEW 默认只读，不实现修复，除非 Task 明确要求。遵守 `skills/code-review/SKILL.md` 与 `coordination/REVIEW_PROTOCOL.md`，重点检查 correctness、regression、contract、ownership、security、replay、fencing、concurrency，以及 complexity justification 是否真的能追溯到 Task / Contract / Invariant。

对无依据的显著复杂度使用：

```text
Type: IMPLEMENTATION
Code: OVER_ENGINEERING
```

不要因为个人偏好能设计出更复杂方案而产生该 Finding；必须证明当前实现复杂度没有当前需求依据，或存在明显更简单且同样满足全部要求的方案。

## 6. Checkpoint
长任务按 `AGENTS.md` 的强制 Checkpoint 条件执行。发生 context / quota / session 中断、Agent 移交或阻塞失败时必须形成 `HANDOFF` checkpoint。

## 7. 输出
严格使用 `coordination/OUTPUT_FORMAT.md` 和当前 Task 的 Output Format。无问题时只返回调度器需要的结果；发现问题时返回最小充分证据。
