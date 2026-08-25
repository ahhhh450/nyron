# Multi-Agent Development Workflow

## 1. 基本链路

```text
Orchestrator reads STATUS
→ creates Task
→ assigns isolated Executor workspace
→ Executor works and returns Result
→ Review if required
→ Fix / Re-Review if needed
→ Orchestrator Accepts or Rejects
→ Coordination Update
→ Integration / Baseline / Release when eligible
```

## 2. Task 状态建议

```text
DRAFT
READY
IN_PROGRESS
BLOCKED
RESULT_SUBMITTED
IN_REVIEW
FIX_REQUIRED
PENDING_INDEPENDENT_REVIEW
ACCEPTED
REJECTED
CANCELLED
ARCHIVED
```

Executor 可以报告执行状态，但不得自行把项目级 Task 裁决为 `ACCEPTED`。

## 3. 调度顺序

创建 Task 前检查：
- 当前 Coordination Epoch / Revision；
- `Depends On` 是否已满足；
- 是否存在 workspace 冲突；
- Agent 是否适合任务风险；
- Review independence 是否可满足。

## 4. 风险分级

### LOW
文档、机械检查、小型低风险修改。允许简化 Review。

### MEDIUM
正常功能实现、一般重构、测试改动。通常需要 Review。

### HIGH
Architecture、Contract、Security、Core Runtime、Concurrency、Replay、Baseline、Release-critical。必须独立 Review；若暂时无法完成，保持 `PENDING_INDEPENDENT_REVIEW`。

## 5. Coordination Update

实现代码与 Coordination 更新应分离。若 Orchestrator 无直接 repo 写权限，应单独下发机械性的 Coordination Update，不允许 Executor 在实现 commit 中顺手修改 STATUS。

## 6. Fail Closed

遇到以下情况不得猜测继续：
- Epoch 不一致；
- Revision 明显过期；
- 依赖状态不确定；
- Scope 冲突；
- 并发 workspace 不安全；
- 高风险 Review independence 无法满足且准备进入稳定基线。

此时返回 Blocker 或请求 Orchestrator 重新裁决。
