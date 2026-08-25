# Skill: Coordination Update

用于 Orchestrator 已作出明确裁决后，由具备 repo 写能力的 Agent 机械执行协调文件落盘。

## 前提
Task 必须显式包含：

```text
Coordination Write Authorization: GRANTED
Authorized Files:
Expected Epoch:
Expected Revision:
New Epoch:
New Revision:
Exact Approved Changes:
```

缺少 `GRANTED` 或任一必要 CAS 字段时，不执行协调写入。

## 执行规则
1. 在任何写入前重新读取当前 `coordination/STATUS.md` 及 Task 指定的相关协调文件。
2. 比较：
   ```text
   Current Epoch == Expected Epoch
   Current Revision == Expected Revision
   ```
3. 任一不一致时立即停止并返回：
   ```text
   COORDINATION_CAS_MISMATCH
   ```
4. CAS 失败时不得写入、不得自行 merge、不得自行重新计算 New Epoch / Revision、不得采用 last-writer-wins。
5. CAS 成功后，只机械执行 `Exact Approved Changes`。
6. 只能修改 `Authorized Files`。
7. 不同时修改业务代码。
8. 不自行新增 Task、改 Priority、改 Gate、改变 Baseline 结论。
9. 正常更新应满足 `New Revision = Expected Revision + 1`；Orchestrator handoff 应满足 `New Epoch = Expected Epoch + 1`。
10. 写入后重新读取并检查结果，返回 diff / commit / Previous Revision / New Revision / Previous Epoch / New Epoch。

## 原则
Execution Agent 在这里拥有受限 physical write capability，但没有 Coordination Authority。

授权来源是 `AGENTS.md` 定义的 `Coordination Write Authorization` 通道，而不是 Agent 自己判断“应该同步”。
