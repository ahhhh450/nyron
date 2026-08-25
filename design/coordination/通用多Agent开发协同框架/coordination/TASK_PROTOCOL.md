# Task Protocol

## 1. Task Authority
正式 Task 只能由 Active Orchestrator 创建并分配 Task ID。Execution Agent 不得自行推导、创建或派生正式 Task。

推荐 ID：
```text
T-YYYYMMDD-NNN
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
- Stale Policy
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

`Stale Policy` 允许：
```text
FAIL_CLOSED
RECHECK_AND_CONTINUE_IF_UNAFFECTED
```
未声明时默认 `FAIL_CLOSED`。

## 3. Dependency
依赖必须结构化写入 `Depends On`。依赖未达到 Task 要求的接受状态时，本 Task 不能进入 READY / IN_PROGRESS，除非明确允许 speculative / parallel work。

## 4. Scope
Task 必须明确允许修改的范围。未列入 Scope 的工作默认不授权。发现相邻问题时返回 Finding，不自动扩大任务。

## 5. Required Reading
使用最小上下文原则。禁止默认要求 Agent 扫描整个 Repository、历史 Task 或 archive。

## 6. Coordination 文件与显式授权
普通 Task 默认禁止修改：
- `coordination/STATUS.md`
- 与当前任务无关的 Task / Result / Checkpoint
- Baseline / Gate 文件

需要协调写入时，Task 必须显式声明：
```text
Coordination Write Authorization: GRANTED
Authorized Files:
Expected Epoch:
Expected Revision:
New Epoch:
New Revision:
Exact Approved Changes:
```

没有 `GRANTED` 时即无协调写权限。

该字段是由 `AGENTS.md` 定义的特殊授权通道，可覆盖 Agent 专属文件中的普通默认禁写规则，但只对明确 Authorized Files / Exact Approved Changes 生效。

## 7. Coordination CAS
协调写入必须在落盘前重新读取当前状态，并比较：
```text
Current Epoch == Expected Epoch
Current Revision == Expected Revision
```
任一不成立：
```text
COORDINATION_CAS_MISMATCH
```
并立即停止，不自行 merge，不采用 last-writer-wins。

正常协调更新的 `New Revision` 应为 `Expected Revision + 1`。Orchestrator handoff 的 `New Epoch` 应为 `Expected Epoch + 1`。

## 8. Result
Task 完成后必须按 `OUTPUT_FORMAT.md` 提交 Result。Executor 的 SUCCESS 不等于 ACCEPTED。

## 9. Stale Task
如果 Task 的 Epoch 与当前项目 Epoch 不一致，默认失效并 fail closed。

如果 Revision 已变化，按 `Stale Policy` 执行；未声明时默认 `FAIL_CLOSED`。
