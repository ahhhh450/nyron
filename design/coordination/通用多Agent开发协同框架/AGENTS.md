# AGENTS.md — 通用多 Agent 开发公共规则

状态：`DRAFT / NOT FROZEN`

本文件定义项目中所有 Execution Agent 的公共强制规则。

适用对象包括但不限于：

- Codex
- Claude Code
- DeepSeek
- 后续接入的其他开发 / Review Agent

各 Agent 的专属文件只能补充工具和执行差异，不得覆盖本文件的公共权限边界。

---

## 1. 角色与最高原则

### 1.1 Development Orchestrator

Web GPT 默认承担 `Development Orchestrator`，是项目的 **Coordination Authority（协同裁决权威）**。

Orchestrator 负责决定：

- Task 是否创建；
- Task ID；
- Assigned Agent；
- Priority；
- Dependencies；
- Development Gate；
- Review / Re-Review 分配；
- Delivery 接受或拒绝；
- 项目级 STATUS；
- Baseline / Release 状态。

### 1.2 Execution Agent

Execution Agent 负责执行已分配 Task，并报告事实。

核心原则：

> **Executor reports facts; Orchestrator decides project state.**

Agent 返回 `SUCCESS / PASS`，只代表其执行结果，不自动等价于：

- `COMPLETED`
- `ACCEPTED`
- `INTEGRATED`
- `FROZEN`
- `RELEASED`

这些项目级状态只能由 Orchestrator 裁决。

---

## 2. Single Coordination Authority

一个项目同一时刻只能存在一个有效的 Active Orchestrator。

Execution Agent 不得：

- 自行取得 Orchestrator 身份；
- 自行推进项目 Gate；
- 自行改变 Task Priority；
- 自行宣布 Baseline 已冻结；
- 自行决定 Release 成立。

如果发现多个 Orchestrator 指令互相冲突、Epoch 不一致或无法判断哪一个有效，应 **fail closed**：停止相关协调动作并报告冲突，不自行选择。

---

## 3. Authority 与 Physical Write 分离

`Decision Authority != Physical Writer`

Orchestrator 拥有协调裁决权，但不要求其必须亲自执行所有 Repository 写入。

当 Orchestrator 无法直接写 Repository 时，可以明确授权 Execution Agent 机械执行协调文件变更。

但是：

- 普通 Implementation / Design / Review Task 不得顺手修改项目协调状态；
- 对 `STATUS.md`、Task assignment、Gate、Baseline 状态等协调控制内容的写入必须有明确授权；
- 协调状态变更应与普通实现改动分离，除非 Task 明确允许合并；
- Agent 不得因为“内容显然需要同步”而自行扩大协调写权限。

---

## 4. Task Identity

正式工作必须绑定明确 Task。

Task ID 只能由 Orchestrator 分配。

Execution Agent 不得：

- 自行创建正式 Task ID；
- 使用“最大编号 + 1”推导新 Task；
- 为发现的新问题自行派生正式子 Task；
- 把未授权工作包装成新的正式 Task。

如果执行过程中发现额外工作，应作为 `Finding` 返回，由 Orchestrator 决定是否创建新 Task。

---

## 5. Task 是执行边界

Agent 只执行当前 Task 明确授权的工作。

必须遵守：

- `Objective`
- `Scope`
- `Out of Scope`
- `Required Reading`
- `Constraints`
- `Allowed Files / Forbidden Files`（如有）
- `Validation`
- `Deliverables`
- `Output Format`

不得因为认为“顺便做了更好”而扩大范围。

若 Task 与项目公共规则冲突，优先级为：

```text
明确的人类指令
> 已冻结项目级规则 / Baseline
> AGENTS.md
> Agent 专属规则
> Task
> Skill / 执行建议
```

如果冲突无法安全解释，应停止冲突部分并报告，而不是自行裁决架构或权限问题。

---

## 6. Context Loading Policy

默认采用最小必要上下文。

Agent 应：

1. 先读 Task 指定的 Required Reading；
2. 只在完成任务确有必要时扩展读取；
3. 避免无目的扫描整个 Repository、历史 Task、日志和归档；
4. 如扩展读取影响了设计判断，应在结果中说明关键新增依据。

目标是降低上下文污染、历史规则误引用和无关信息干扰。

---

## 7. Coordination Revision / Epoch

当项目启用了 `Coordination Revision` 或 `Coordination Epoch` 时，Agent 必须把它们视为 fencing 信息。

如果 Task 声明：

```text
Based On Coordination Revision: N
Coordination Epoch: E
```

而执行时发现当前协调状态已不匹配，则不得自行继续依赖旧状态完成关键协调动作。

应返回：

```text
STALE_COORDINATION_CONTEXT
```

并说明检测到的 Revision / Epoch 差异。

普通代码实现是否可以继续，由 Task 中的 stale policy 决定；Agent 不得自行假设。

---

## 8. Task Dependencies

如果 Task 声明 `Depends On`，Agent 必须尊重依赖状态。

依赖未满足时：

- 不得自行绕过；
- 不得把依赖视为“应该已经完成”；
- 不得自行修改依赖 Task 状态。

除非 Task 明确允许 speculative / parallel work，否则应报告 `BLOCKED_BY_DEPENDENCY`。

---

## 9. 并发与 Workspace 隔离

公共强制规则：

> **Concurrent Tasks MUST NOT share a mutable working tree.**

并行 Task 必须使用独立：

- branch；
- worktree；
- sandbox；
- 或其他等价隔离环境。

Agent 不得：

- 覆盖其他 Task 的未提交改动；
- 删除无法确认来源的 untracked files；
- 用 `reset --hard`、force checkout 等方式清理未知工作；
- 把其他 Task 的改动混入当前交付；
- 在未经授权的情况下复用一个已被其他并行任务占用的可变工作区。

具体隔离方式由各 Agent 专属规则定义。

---

## 10. Git 公共安全规则

除非 Task 明确授权，不得：

- `reset --hard`
- force push
- 强制覆盖他人分支
- 删除未知 branch / worktree
- 删除未知 untracked files
- rewrite shared history
- rebase 他人正在使用的共享工作

执行写操作前，应尽可能确认：

- 当前 branch / worktree；
- 当前 HEAD；
- working tree 是否包含非本 Task 改动；
- Task 允许的提交范围。

发现 Workspace contamination 时，应停止可能破坏他人工作的操作并报告。

---

## 11. Agent 工具能力不得被公共规则假设

`AGENTS.md` 只定义结果与边界，不假设所有 Agent 都拥有相同能力。

例如不得默认所有 Agent 都：

- 能直接 commit；
- 能创建 worktree；
- 能访问网络；
- 能直接修改 GitHub；
- 能运行完整测试环境。

这些差异由：

- `CLAUDE.md`
- `CODEX.md`
- `DEEPSEEK.md`

分别定义。

如果当前 Agent 缺少完成 Task 所需能力，应明确报告 Capability Blocker，不伪造执行结果。

---

## 12. Validation 与事实报告

Agent 只能报告自己实际执行或直接验证过的事实。

禁止：

- 未运行测试却报告 `tests passed`；
- 未检查 diff 却声称“没有无关改动”；
- 未读取目标文件却声称“已确认”；
- 把推测写成已验证事实。

如验证不完整，应明确区分：

```text
VERIFIED
NOT_VERIFIED
NOT_APPLICABLE
BLOCKED
```

Orchestrator 将据此决定是否接受交付或安排额外 Review。

---

## 13. Findings

执行中发现的额外问题统一返回为 `Findings`。

建议类型：

```text
IMPLEMENTATION
TEST
CONTRACT
ARCHITECTURE
SECURITY
PROCESS
```

严重程度：

```text
BLOCKING
NON_BLOCKING
```

Finding 不自动授权 Agent 修复。

如果 Finding 超出当前 Scope：

```text
发现
-> 记录
-> 返回 Orchestrator
-> 等待是否创建新 Task
```

---

## 14. Independent Review

独立 Review 的默认原则：

> **Original Implementer != Independent Reviewer**

Review Agent 必须审查交付，而不是重新实现任务。

Review 时不得因为自己能快速修复问题就直接扩大 Scope 修改代码，除非 Review Task 明确授权 Review + Fix。

如果 Task 声明 Independent Review 为 `REQUIRED`，但当前 Reviewer 与原执行 Agent 不满足独立性，应报告：

```text
REVIEW_INDEPENDENCE_VIOLATION
```

不得把自审包装成 Independent Review。

`WAIVED` 只能由 Orchestrator 明确决定。

---

## 15. 高风险交付

以下类型默认属于高风险：

- Architecture；
- Contract；
- Security-sensitive change；
- Core runtime；
- Baseline change；
- Release-critical change。

如果项目规则要求独立 Review，则这些交付在独立 Review 未完成前不得由 Executor 自行宣布进入稳定 Baseline。

Agent 可以报告实现成功，但项目状态应保持由 Orchestrator 裁决。

---

## 16. Checkpoint

长任务或中断任务使用统一 Checkpoint。

```text
Type: PROGRESS | HANDOFF
```

至少记录：

```text
Task ID
Current Step
Completed
Remaining
Files Touched
Validation
Findings
Blockers
Next Action
```

推荐产生 `HANDOFF` Checkpoint 的场景：

- Agent 更换；
- context 即将中断；
- quota / 工具中断；
- Task 暂停；
- Blocking Failure；
- 必须切换新会话继续。

权威优先级：

```text
Accepted Project State
> Final Task Result
> Latest Checkpoint
> Earlier Checkpoint
```

Checkpoint 不得覆盖已经产生的 Final Result。

---

## 17. Result

Task 完成或停止时，应按照项目规定格式返回结果。

基础结构：

```text
[TASK RESULT]

Task ID:
Execution Result:

Files Changed:
Validation:
Commit:

Findings:
Blockers:
```

如果 Task 明确要求“只返回特定字段”，以 Task 的输出要求为准。

Result 应尽量短、结构化、可被 Orchestrator 直接用于下一步调度。

---

## 18. Violation Protocol

以下行为属于典型交付违规：

- Unauthorized Coordination Change
- Unauthorized Task Creation
- Scope Violation
- Workspace Contamination
- Unrelated Change
- Fabricated Validation
- Review Independence Violation

发现自己已经发生违规时，不得隐藏或继续把交付包装为正常成功。

应明确报告违规事实和受影响范围。

Orchestrator 可以将该交付标记：

```text
DELIVERY_REJECTED
```

合法工作若可安全拆分，可以保留；无法安全拆分时，应重新实施，而不是要求 Orchestrator 接受被污染交付。

---

## 19. Fail Closed

遇到以下情况时，默认停止高风险动作并报告，而不是自行猜测：

- 权限边界不清；
- Task 与 Baseline 冲突；
- 多个 Orchestrator 指令冲突；
- Coordination Epoch / Revision stale；
- Dependency 未满足；
- Workspace 来源不明；
- 可能破坏其他 Agent 工作；
- 需要修改明确 Out of Scope 内容；
- 无法验证关键事实。

Fail closed 不意味着停止一切工作；如果仍有明确、安全、Scope 内的独立部分，可以继续完成该部分并报告剩余 blocker。

---

## 20. 公共规则与专属规则的边界

本文件定义的是跨 Agent 公共约束。

各 Agent 专属文件应该主要定义：

- 工具能力；
- sandbox / worktree 建立方式；
- Git 操作细节；
- 测试执行方式；
- Agent 特定上下文策略；
- Agent 特定输出注意事项。

专属规则不得弱化本文件中的：

- Coordination Authority；
- Task Identity；
- Scope；
- Workspace Isolation；
- Review Independence；
- Validation Honesty；
- Project State Authority。

---

## 21. 最小公共原则

任何 Agent 即使没有读取完整流程文档，也必须遵守以下七条：

1. **Single Coordination Authority** — 项目协调裁决权只属于当前有效 Orchestrator。
2. **Authority != Physical Writer** — 可以受控执行落盘，但不能把物理写权限当作决策权限。
3. **Orchestrator-Issued Task Identity** — Executor 不创建正式 Task ID。
4. **Coordination Revision + Epoch** — stale 协调状态不得被当作当前事实。
5. **Isolated Concurrent Execution** — 并发任务不得共享 mutable working tree。
6. **Independent Review Enforcement** — 自审不等于独立 Review。
7. **Executor Reports Facts, Orchestrator Accepts State** — Agent 报告执行事实，Orchestrator 裁决项目状态。
