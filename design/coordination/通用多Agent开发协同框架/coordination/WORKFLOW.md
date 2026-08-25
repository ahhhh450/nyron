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
→ Archive terminal artifacts when safe
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

## 6. Checkpoint 生命周期

Checkpoint 用于保证 Task 在长时间执行、换会话、换 Agent 或工具中断后仍可恢复。

强制频率以 `AGENTS.md` 为准。核心规则：

- milestone 完成但 Task 未结束 → `PROGRESS`；
- 自上次 Checkpoint 起累计触及 5 个新的不同文件且仍需继续 → `PROGRESS`；
- 自上次 Checkpoint 起累计 3 个 Task-scoped commit 且仍需继续 → `PROGRESS`；
- Agent / session / workspace 交接、暂停或阻塞退出 → `HANDOFF`。

Checkpoint 必须新建，不覆盖旧记录。

Task 在触发阈值前直接结束时，Final Result 即可，不要求额外 Checkpoint。

## 7. Archive 生命周期

`tasks/`、`results/`、`checkpoints/` 是活跃协同面，不应无限积累历史记录。

Task 只有同时满足以下条件时才可归档：

1. 已进入终态：`ACCEPTED | REJECTED | CANCELLED`；
2. 不再处于 Review / Re-Review / Fix / Integration 流程；
3. 没有 Active / Blocked Task 仍依赖其原始文件路径；
4. 没有未清的 Review Debt 或 Blocking Finding 要求继续以该 Task 为活跃对象；
5. 归档不会破坏当前 Baseline / Release 的必要审计引用。

建议归档结构：

```text
coordination/archive/<TaskID>/
├─ TASK.md
├─ RESULT.md            # 如有
└─ checkpoints/         # 如有
```

归档由 Orchestrator 决定。若由 Execution Agent 物理执行，视为 Coordination Update，必须走显式授权与 CAS。

### Archive Sweep 触发条件

Orchestrator 在以下任一时点执行一次 archive sweep：

- Project Phase 切换；
- Baseline 冻结；
- Release 完成；
- 活跃目录中累计存在 **10 个及以上已终态且满足归档条件的 Task**；
- Orchestrator handoff 前发现活跃协同面已包含大量与下一阶段无关的终态记录。

Archive 只减少默认读取集合，不改变历史事实、Result 或已接受结论。

## 8. Orchestrator 上下文维护

Orchestrator 默认只读取：

```text
STATUS
+ Active / In Review / Blocked Tasks
+ Open Findings / Review Debt
+ 当前决策必要的 Result / Checkpoint
```

`archive/` 默认不进入新会话上下文。只有发生历史追溯、回归分析或明确依赖时才读取。

Handoff 只携带当前活跃状态、未决风险和下一步；已经安全归档的 Task 不重新塞入主窗口上下文。

## 9. Fail Closed

遇到以下情况不得猜测继续：
- Epoch 不一致；
- Revision 明显过期；
- 依赖状态不确定；
- Scope 冲突；
- 并发 workspace 不安全；
- 高风险 Review independence 无法满足且准备进入稳定基线。

此时返回 Blocker 或请求 Orchestrator 重新裁决。
