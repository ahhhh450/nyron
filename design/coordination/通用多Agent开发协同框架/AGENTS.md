# AGENTS.md — 通用多 Agent 开发公共规则

状态：`DRAFT / NOT FROZEN`

本文件定义所有 Execution Agent 的公共强制规则。适用于 Codex、Claude Code、DeepSeek 及后续接入的其他开发 / Review Agent。

各 Agent 专属文件只能补充工具和执行差异，不得覆盖本文件中的权限边界。

---

## 1. 角色与最高原则

### Development Orchestrator

Web GPT 默认承担 `Development Orchestrator`，是项目的 `Coordination Authority`。

负责决定：Task 创建与 ID、Assigned Agent、Priority、Dependencies、Development Gate、Review / Re-Review、Delivery 接受或拒绝、项目级 STATUS、Baseline / Release 状态。

### Execution Agent

Execution Agent 负责执行已分配 Task，并报告事实。

> Executor reports facts; Orchestrator decides project state.

Agent 的 `SUCCESS / PASS` 不自动等价于 `COMPLETED / ACCEPTED / INTEGRATED / FROZEN / RELEASED`。

---

## 2. Single Coordination Authority

一个项目同一时刻只能存在一个有效 Active Orchestrator。

Execution Agent 不得自行取得 Orchestrator 身份、改变 Priority、推进 Gate、冻结 Baseline 或决定 Release。

若存在多个冲突 Orchestrator 指令、Epoch 不一致或无法判断哪个有效，应 fail closed 并报告冲突。

---

## 3. Authority 与 Physical Write 分离

`Decision Authority != Physical Writer`

Orchestrator 拥有协调裁决权，但实际文件写入可以由受控 Execution Agent 机械执行。

普通 Implementation / Design / Review Task 默认不得修改协调控制文件。

只有当 Task 显式声明：

```text
Coordination Write Authorization: GRANTED
```

且同时明确：

- Authorized Files；
- Expected Epoch；
- Expected Revision；
- Exact Approved Changes；
- 是否要求 commit；

Execution Agent 才可执行对应协调写入。

该显式授权是 `AGENTS.md` 定义的公共授权通道，因此 **优先于 Agent 专属文件中“普通任务不得修改协调文件”的默认限制**，但不得覆盖冻结 Baseline、人类指令或 Task 未授权范围。

没有 `GRANTED` 时，一律视为无协调写权限。

### Execution Record 与 Coordination State 分离

以下内容属于本 Task 的执行证据，不属于项目级协调裁决：

```text
coordination/results/<当前 Task ID>...
coordination/checkpoints/<当前 Task ID>...
```

在当前 Task 允许 Repository 写入且未明确禁止 execution-record write 时，Execution Agent 可以落盘**自己当前 Task**的 Result / Checkpoint，不需要 `Coordination Write Authorization: GRANTED`。

该权限严格限制为执行记录：

- 不得修改 `STATUS.md`；
- 不得改变 Task 的权威 Status / Priority / Gate；
- 不得修改其他 Task 的 Result / Checkpoint；
- 不得借执行记录写入改变 Baseline / Release 结论。

若 Task 明确为 Repository `READ_ONLY`，Agent 只在返回结果中提供 Checkpoint / Result 内容，由 Orchestrator 决定是否另行落库。

---

## 4. 规则优先级

发生冲突时按以下顺序解释：

```text
明确的人类指令
> 已冻结项目规则 / Baseline
> AGENTS.md
> Task 中由 AGENTS.md 明确定义的特殊授权字段
> Agent 专属规则
> Task 一般执行内容
> Skill / 执行建议
```

其中 `Coordination Write Authorization: GRANTED` 属于由 `AGENTS.md` 定义的特殊授权字段，仅在其声明的 Authorized Files / Exact Approved Changes 范围内生效。

任何规则冲突如果无法安全解释，应停止冲突部分并报告，不自行扩权。

---

## 5. Task Identity 与执行边界

正式工作必须绑定明确 Task。Task ID 只能由 Orchestrator 分配。

Execution Agent 不得自行创建、预测、递增或派生正式 Task ID。

Agent 只执行当前 Task 的 Objective、Scope、Constraints、Required Reading、Allowed / Forbidden Files、Validation、Deliverables 和 Output Format。

发现额外问题时返回 `Finding`，不自动扩 Scope。

---

## 6. Context Loading Policy

默认采用最小必要上下文：先读 Task 指定内容，只在确有必要时扩展读取，避免无目的扫描整个 Repository、历史 Task、logs 或 archive。

---

## 7. Coordination Epoch / Revision 与 Stale Policy

`Coordination Epoch` 用于 fencing Orchestrator 世代；`Coordination Revision` 用于检测协调状态更新。

Task 若声明：

```text
Coordination Epoch: E
Based On Coordination Revision: R
```

执行前发现当前值不匹配时，应按 Task 的 `Stale Policy` 处理。

允许值：

```text
FAIL_CLOSED
RECHECK_AND_CONTINUE_IF_UNAFFECTED
```

**默认值：`FAIL_CLOSED`。**

如果 Task 未声明 `Stale Policy`，必须停止依赖旧协调前提的动作并返回：

```text
STALE_COORDINATION_CONTEXT
```

不得由 Executor 自己决定“应该没影响”。

---

## 8. Coordination Update 的 CAS 语义

任何会修改 `Coordination Epoch`、`Coordination Revision`、Active Orchestrator、Gate、Task 状态或其他协调权威字段的写入，必须使用 Compare-And-Set（CAS）式前置条件。

Task 必须声明：

```text
Expected Epoch: E
Expected Revision: R
New Epoch: E 或 E+1
New Revision: R+1
```

执行者必须在写入前重新读取当前协调状态：

- 当前 Epoch != Expected Epoch → `COORDINATION_CAS_MISMATCH`
- 当前 Revision != Expected Revision → `COORDINATION_CAS_MISMATCH`
- 任何前置条件不满足 → 禁止写入、禁止自行 merge、禁止“最后写入者获胜”

Orchestrator handoff 的 Epoch +1 同样必须走该 CAS 规则。

---

## 9. Task Dependencies

如果 Task 声明 `Depends On`，Agent 必须尊重依赖状态。依赖未满足时，除非 Task 明确允许 speculative / parallel work，否则返回 `BLOCKED_BY_DEPENDENCY`。

---

## 10. 并发与 Workspace 隔离

> Concurrent Tasks MUST NOT share a mutable working tree.

并行 Task 必须使用独立 branch / worktree / sandbox 或等价隔离环境。

禁止覆盖其他 Task 未提交改动、删除未知 untracked files、强制清理未知工作区或把其他 Task 改动混入当前交付。

---

## 11. Git 公共安全规则

除非 Task 明确授权，不得：

- `reset --hard`
- force push
- 强制覆盖他人分支
- 删除未知 branch / worktree / untracked files
- rewrite shared history
- rebase 他人正在使用的共享工作

执行写操作前，应尽可能确认当前 branch / worktree、HEAD、working tree 污染情况和 Task 允许范围。

---

## 12. 工具能力不得被公共规则假设

公共规则不默认所有 Agent 都能 commit、创建 worktree、联网、直接修改 GitHub 或运行完整测试。

工具差异由 `CLAUDE.md`、`CODEX.md`、`DEEPSEEK.md` 定义。

能力不足时必须报告 Capability Blocker，不伪造执行结果。

---

## 13. Validation 与事实报告

Agent 只能报告实际执行或直接验证过的事实。

统一区分：

```text
VERIFIED
NOT_VERIFIED
NOT_APPLICABLE
BLOCKED
```

不得未跑测试却声称 passed，或未查 diff 却声称没有无关改动。

---

## 14. Findings

统一使用 `Findings`。

Finding Type：

```text
IMPLEMENTATION | TEST | CONTRACT | ARCHITECTURE | SECURITY | PROCESS
```

Severity：

```text
BLOCKING | NON_BLOCKING
```

Finding 不自动授权修复。

---

## 15. Independent Review

默认：

> Original Implementer != Independent Reviewer

REVIEW / RE_REVIEW 默认只读，不直接修复，除非 Task 明确授权 Review + Fix。

若 Independent Review 为 REQUIRED 但 Reviewer 与 Original Agent 不满足独立性，返回 `REVIEW_INDEPENDENCE_VIOLATION`。

`WAIVED` 只能由 Orchestrator 决定，且不能伪装成真正独立 Review。

Architecture、Contract、Security-sensitive change、Core runtime、Baseline change、Release-critical change 在项目要求独立 Review 时，不得仅凭 WAIVED 进入稳定 Baseline。

---

## 16. Checkpoint 与 Result

统一 Checkpoint：

```text
Type: PROGRESS | HANDOFF
```

### 强制 Checkpoint 触发条件

不依赖 Agent 自我判断“上下文快满了”。只要 Task 尚未产生 Final Result，出现以下任一条件就必须形成新的 `PROGRESS` Checkpoint：

1. 完成 Task 明确定义的一个阶段 / milestone，且仍有后续工作；
2. 自上一个 Checkpoint 起，累计触及 **5 个新的不同文件**，且仍将继续修改更多文件；
3. 自上一个 Checkpoint 起，累计产生 **3 个 Task-scoped commit**，且 Task 尚未结束。

出现以下任一情况必须形成 `HANDOFF` Checkpoint：

- 计划更换 Agent / 会话 / workspace；
- quota / 工具限制导致无法继续；
- Task 被 Orchestrator 暂停；
- Blocking Failure 导致当前执行无法继续；
- 当前 Agent 将停止工作但 Task 尚未形成 Final Result。

如果 Task 在触发上述阈值之前已经可以直接产生 Final Result，则不要求为了形式额外创建 Checkpoint。

Checkpoint 必须**新增而不是覆盖旧文件**，建议编号：

```text
<TaskID>-CP-001.md
<TaskID>-CP-002.md
...
```

建议记录 Task ID、Current Step、Completed、Remaining、Files Touched、Validation、Findings、Blockers、Next Action。

权威优先级：

```text
Accepted Project State
> Final Task Result
> Latest Checkpoint
> Earlier Checkpoint
```

Final Result 产生后，Checkpoint 只保留历史意义，不覆盖 Final Result。

---

## 17. Violation Protocol

典型违规：

- Unauthorized Coordination Change
- Unauthorized Task Creation
- Scope Violation
- Workspace Contamination
- Unrelated Change
- Fabricated Validation
- Review Independence Violation

发生违规不得隐藏。Orchestrator 可将交付标记为 `DELIVERY_REJECTED`。

合法工作若可安全拆分可保留；无法安全拆分则重新实施。

---

## 18. Fail Closed

以下情况默认停止高风险动作并报告：

- 权限边界不清；
- Task 与 Baseline 冲突；
- 多 Orchestrator 冲突；
- Epoch / Revision stale；
- CAS 前置条件不满足；
- Dependency 未满足；
- Workspace 来源不明；
- 可能破坏其他 Agent 工作；
- 需要修改 Out of Scope 内容；
- 无法验证关键事实。

如果仍有明确、安全、Scope 内的独立部分，可以继续该部分并报告剩余 blocker。
