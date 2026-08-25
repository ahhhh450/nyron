# Skill: Coordination Update

用于 Orchestrator 已作出明确裁决后，由具备 repo 写能力的 Agent 机械执行协调文件落盘。

## 前提
Task 必须明确给出：
- 允许修改的 coordination 文件；
- 目标 Coordination Epoch；
- 基于哪个 Coordination Revision；
- 要写入的确定内容；
- 是否要求 commit。

## 执行规则
1. 先读取当前 `coordination/STATUS.md`。
2. Epoch 不一致时立即停止并返回 `STALE_CONTEXT`。
3. Revision 与 Task 前提不一致且会影响写入时停止，不自行合并裁决。
4. 只机械执行 Orchestrator 已批准的内容。
5. 不同时修改业务代码。
6. 不自行新增 Task、改 Priority、改 Gate、改变 Baseline 结论。
7. 写入后返回 diff / commit / 新 Revision。

## 原则
Execution Agent 在这里拥有 physical write capability，但没有 Coordination Authority。
