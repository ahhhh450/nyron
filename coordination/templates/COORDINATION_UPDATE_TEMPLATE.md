# Coordination Update Task

- Task ID: `T-YYYYMMDD-NNN`
- Type: `COORDINATION_UPDATE`
- Risk: `LOW | MEDIUM`
- Assigned Agent: `...`
- Orchestrator: `...`
- Coordination Write Authorization: `GRANTED`
- Stale Policy: `FAIL_CLOSED`

## CAS Preconditions

- Expected Epoch: `...`
- Expected Revision: `...`
- New Epoch: `...`
- New Revision: `...`

规则：
- 普通协调更新：`New Revision = Expected Revision + 1`
- 非 handoff：通常 `New Epoch = Expected Epoch`
- Orchestrator handoff：`New Epoch = Expected Epoch + 1`

执行 Agent 必须在写入前重新读取当前状态。若当前 Epoch / Revision 与 Expected 值任一不一致，返回 `COORDINATION_CAS_MISMATCH`，不得写入或自行合并。

## Authorized Files

- `coordination/STATUS.md`
- 其他明确列出的协调文件

## Exact Approved Changes

逐条写出 Orchestrator 已经裁决的内容。Agent 只机械落盘，不重新裁决。

## Forbidden

- 修改未列入 Authorized Files 的文件；
- 修改业务代码；
- 自行创建其他 Task；
- 改变未授权 Priority / Gate / Baseline；
- 自行重算 Epoch / Revision；
- CAS 失败后继续写入；
- 基于个人判断补充额外状态变化。

## Validation

- 写前重新读取当前 Epoch / Revision；
- 执行 CAS；
- 写入后检查 diff；
- 重新读取最终 Epoch / Revision；
- 返回 commit / 新状态。

## Output

```text
[COORDINATION UPDATE RESULT]
Task ID:
Result:
Files Changed:
Previous Epoch:
New Epoch:
Previous Revision:
New Revision:
Commit:
Blockers:
```
