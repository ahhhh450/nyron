# Task Protocol

## 1. Task Authority

正式 Task 只能由 Active Orchestrator 创建并分配 Task ID。Execution Agent 不得自行推导、创建或派生正式 Task。

推荐 ID：
```text
T-YYYYMMDD-NNN
```

项目需要命名空间时：
```text
PROJECT-T-YYYYMMDD-NNN
```

## 2. 必填字段

每个 Task 至少包含：
- Task ID
- Type
- Risk
- Assigned Agent
- Status
- Priority
- Orchestrator
- Coordination Epoch
- Based On Coordination Revision
- Parent Task
- Depends On
- Reviews Task（如适用）
- Objective
- Required Reading
- Scope
- Out of Scope
- Constraints
- Validation
- Deliverables
- Output Format
- Completion Criteria

## 3. Dependency

依赖必须结构化写入 `Depends On`。依赖未达到 Task 要求的接受状态时，本 Task 不能进入 READY / IN_PROGRESS。

## 4. Scope

Task 必须明确允许修改的范围。未列入 Scope 的工作默认不授权。
发现相邻问题时返回 Finding，不自动扩大任务。

## 5. Required Reading

使用最小上下文原则。禁止默认要求 Agent 扫描整个 Repository、历史 Task 或 archive。

## 6. Coordination 文件

普通实现 Task 默认禁止修改：
- `coordination/STATUS.md`
- 与当前任务无关的 Task / Result / Checkpoint
- Baseline / Gate 文件

如需协调更新，应单独授权。

## 7. Result

Task 完成后必须按 `OUTPUT_FORMAT.md` 提交 Result。Executor 的 SUCCESS 不等于 ACCEPTED。

## 8. Stale Task

如果 Task 的 Epoch 与当前项目 Epoch 不一致，Task 默认失效。
如果 Coordination Revision 已显著变化且影响任务前提，Executor 应停止关键动作并报告 `STALE_CONTEXT`。
