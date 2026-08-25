# Coordination Update Task

- Task ID: `T-YYYYMMDD-NNN`
- Type: `COORDINATION_UPDATE`
- Risk: `LOW | MEDIUM`
- Assigned Agent: `...`
- Orchestrator: `...`
- Coordination Epoch: `...`
- Based On Coordination Revision: `...`

## Authorized Files

- `coordination/STATUS.md`
- 其他明确列出的协调文件

## Exact Approved Changes

逐条写出 Orchestrator 已经裁决的内容。Agent 只机械落盘，不重新裁决。

## Forbidden

- 修改业务代码；
- 自行创建其他 Task；
- 改变未授权 Priority / Gate / Baseline；
- 基于个人判断补充额外状态变化。

## Validation

- 读取当前 Epoch / Revision；
- stale 时停止；
- 写入后检查 diff；
- 返回 commit / 新 Revision。

## Output

```text
[COORDINATION UPDATE RESULT]
Task ID:
Result:
Files Changed:
Previous Revision:
New Revision:
Commit:
Blockers:
```
