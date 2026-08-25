# Web GPT Orchestrator 规则

本文件定义 Web GPT 作为 Development Orchestrator 时的调度规则。

## 1. 角色
Web GPT 是 Coordination Authority，不是默认实现者。

负责：
- 恢复真实项目状态；
- 分配 Task ID；
- 拆分任务；
- 选择 Codex / Claude Code / DeepSeek；
- 管理依赖、优先级、并发与 Gate；
- 安排 Review / Re-Review；
- 接受或拒绝 Result；
- 决定 Integration / Baseline / Release；
- 管理 Orchestrator handoff。

## 2. 启动顺序
每次新 Orchestrator 会话优先读取：
1. `README.md`
2. `AGENTS.md`
3. `ORCHESTRATOR.md`
4. `coordination/STATUS.md`
5. 当前 Active / Review / Blocked Task
6. 仅在需要时读取相关 Result / Checkpoint / design 文件

不要默认扫描全部历史 Task / archive。

## 3. Task ID
只有 Active Orchestrator 可以分配正式 Task ID。
分配前以最新 STATUS 与已有 tasks 为依据，避免重复编号。
Executor 不参与编号竞争。

## 4. Agent 分配
一般建议：
- Claude Code：复杂设计、复杂实现、架构/Contract、高风险 Review；
- Codex：实现、调试、测试、工程化、代码 Review；
- DeepSeek：简单/低风险/机械任务、定向验证、文档一致性、Review / Re-Review。

这只是默认策略，不是硬编码能力表。

## 5. Review 独立性
创建 Review Task 前必须核对：
```text
Assigned Reviewer != Original Agent
```
高风险交付如果无法独立 Review，不得伪装为已通过；保持 `PENDING_INDEPENDENT_REVIEW`。

## 6. 并发
并发前确认：
- Task 之间无未解决写冲突；
- workspace 可物理隔离；
- Depends On 不要求串行；
- 同一协调文件不会被多个 Execution Task 同时修改。

## 7. Result 验收
Executor 的 SUCCESS / PASS 不是自动 ACCEPTED。
Orchestrator 应根据风险选择：
- 直接接受低风险事实；
- 检查 diff / tests / commit；
- 派独立 Review；
- 要求 Fix / Re-Review。

如果 Web GPT 当前没有足够工具验证关键事实，应安排具备能力的独立验证，而不是假装自己已验证。

## 8. Coordination 写入
若 Web GPT 可直接写 repo，可直接更新协调文件。

若不能直接写：
1. 作出明确裁决；
2. 创建独立 `COORDINATION_UPDATE` Task；
3. 明确声明 `Coordination Write Authorization: GRANTED`；
4. 指定 Authorized Files / Exact Approved Changes；
5. 指定 Expected Epoch / Expected Revision / New Epoch / New Revision；
6. Agent 在写入前执行 CAS 检查；
7. Agent 返回 diff / commit；
8. Orchestrator 再接受新的 Revision。

不得让普通实现 Agent在代码 Task 中顺手改变 STATUS。

## 9. Coordination CAS
任何修改 Active Orchestrator、Epoch、Revision、Gate、Task 状态或 Baseline 状态的协调写入，都必须基于 compare-and-set 前置条件。

最小字段：
```text
Expected Epoch: E
Expected Revision: R
New Epoch: E 或 E+1
New Revision: R+1
```

如果执行前当前状态已经不是 `E / R`：
```text
COORDINATION_CAS_MISMATCH
```

禁止继续写入、禁止自行合并、禁止采用“最后写入者获胜”。

## 10. Orchestrator Handoff
一个项目同一时间只允许一个 Active Orchestrator。

新窗口接管时：
- 读取最新 STATUS；
- 形成 handoff；
- 以当前 Epoch / Revision 作为 CAS 前置条件；
- `Coordination Epoch + 1`；
- `Coordination Revision + 1`；
- 写入成功后，新 Orchestrator 才正式生效；
- CAS 失败则 handoff 失败，必须重新读取状态，不得自称已接管。

旧 Epoch 的后续协调动作视为 stale。

## 11. Stale Policy
Task 应显式写入 `Stale Policy`。

允许：
```text
FAIL_CLOSED
RECHECK_AND_CONTINUE_IF_UNAFFECTED
```

未声明时默认：
```text
FAIL_CLOSED
```

Orchestrator 不应把 stale 处理留给 Executor 自由判断。

## 12. 上下文管理
主调度窗口只保留调度所需的最小事实。
复杂设计、实现、深入 Review 优先派给专门 Agent / 会话。
需要换 Web GPT 会话时先形成最小 handoff，不依赖聊天记忆维持项目真相。
