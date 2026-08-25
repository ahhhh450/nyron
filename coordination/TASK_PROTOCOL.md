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

## 7. Execution Record Write

本 Task 自己的 Result / Checkpoint 属于执行证据，不是项目状态裁决。

当 Task 允许 Repository 写入且没有显式 `READ_ONLY` 限制时，Agent 可以写入与自己 Task ID 匹配的：

```text
coordination/results/
coordination/checkpoints/
```

不要求 `Coordination Write Authorization: GRANTED`。

但不得借此：
- 改 `STATUS.md`；
- 改 Task 权威 Status / Priority / Gate；
- 改其他 Task 的记录；
- 改 Baseline / Release 结论。

Repository `READ_ONLY` Task 只返回记录内容，不自行落盘。

## 8. Remote Delivery Submission

项目默认采用：

```text
Local workspace = execution state
Remote GitHub = reviewable project state
```

Agent 可以在本地隔离 branch / worktree / sandbox 中实现、测试和形成 Task-scoped commit，但**仅存在本地的 commit 不构成正式 submitted delivery**。

除非 Task 明确声明 `LOCAL_ONLY`、`READ_ONLY` 或其他不要求远端提交的特殊模式，Implementation / Fix / Refactor / Documentation 等 Repository 写入 Task 在报告可供 Review 的 Final Result 前，应满足：

1. Task-scoped commit 已 push 到远端可读取 branch / ref；
2. Final Result 中记录可核验的 `Remote Branch` 与 `Remote Commit`；
3. Task 要求落盘的 Result / Checkpoint 已包含在该远端交付中；
4. Reviewer / Orchestrator 不需要依赖 Executor 的本地 workspace 才能读取交付事实。

如果本地 commit 已完成但无法安全 push，应报告 `PARTIAL` 或 `BLOCKED`，并明确 Push / Capability Blocker；不得把未 push 的 SHA 表述为正式已提交交付。

远端可审查不等于项目级 ACCEPTED。是否接受、集成、merge、Baseline / Release 仍由 Orchestrator 决定。

### Final Result SHA Verification

在把任何 SHA 写入 Final Result 的 `Commit` 或 `Remote Commit` 字段前，Execution Agent 必须执行：

```text
git cat-file -t <sha>
```

并确认输出严格为：

```text
commit
```

`Remote Commit` 还必须从 canonical remote / 声明的 remote branch history 中可读取；仅在本地对象库可解析不足以构成远端交付证据。无法完成任一验证时必须 fail closed，不得写入该 SHA 或报告正式 `SUCCESS`。

如果 commit 曾被 amend、rebase 或 recreate，导致旧 SHA 已不存在或不再属于声明的交付历史，禁止把旧 SHA 写入 Result；必须使用重新验证后的真实 commit 坐标。

## 9. Coordination CAS
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

## 10. Checkpoint Cadence

只要 Task 尚未形成 Final Result，以下任一条件触发 `PROGRESS` Checkpoint：

- 完成一个 Task milestone 且仍有后续工作；
- 自上次 Checkpoint 起触及 5 个新的不同文件且仍需继续；
- 自上次 Checkpoint 起产生 3 个 Task-scoped commit 且仍需继续。

Agent / session / workspace 交接、暂停、quota/tool 中断或 Blocking Failure 导致当前执行停止时，必须形成 `HANDOFF` Checkpoint。

Checkpoint 创建新文件，不覆盖旧记录。短任务在阈值前直接完成时，Final Result 足够。

## 11. Result
Task 完成后必须按 `OUTPUT_FORMAT.md` 提交 Result。Executor 的 SUCCESS 不等于 ACCEPTED。

对于要求 Repository 写入并提交远端的 Task，`SUCCESS` 还要求交付已经满足本文件的 `Remote Delivery Submission`；只有本地 commit 不足以报告正式 SUCCESS。

## 12. Stale Task
如果 Task 的 Epoch 与当前项目 Epoch 不一致，默认失效并 fail closed。

如果 Revision 已变化，按 `Stale Policy` 执行；未声明时默认 `FAIL_CLOSED`。
