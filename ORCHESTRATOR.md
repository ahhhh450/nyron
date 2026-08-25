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
- 管理 Orchestrator handoff；
- 维护活跃协同面与 Archive 边界。

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

## 5. Agent 会话窗口与命名

不要默认“一个 Task 一个会话”。一个 Agent 会话可以在职责边界稳定、上下文仍健康的前提下连续处理多个 Task。

优先复用合适的现有窗口。仅在以下情况开启新窗口：
- 当前窗口上下文压力明显，继续工作可能降低判断质量；
- 需要独立 Review / 对抗性审查，必须保持 reasoning independence；
- 新工作形成长期独立职责 lane，适合与现有窗口隔离；
- 并行工作需要独立上下文或 workspace；
- 原窗口已发生正式 HANDOFF 或不再适合继续承担该职责。

当 Orchestrator 决定开启新 Agent 会话时，必须在发给用户/Agent 的开始指令中显式要求：

```text
请将当前对话名称修改为：<稳定角色/职责名称>
```

会话名称应描述**长期角色或职责 lane**，而不是当前 Task ID，因为同一窗口预期可以连续处理多个 Task。

推荐命名示例：

```text
Nyron开发工程师1号-Codex
Nyron开发工程师2号-Claude
Nyron低风险审查员-DeepSeek
Nyron核心实现审查员-Claude
Nyron集成与测试-Codex
```

规则：
- Task ID 不作为会话名称的默认组成部分；
- Task ID 仍必须出现在正式 Task 文件和当前任务指令中；
- 复用已有窗口时通常不改名，除非该窗口的长期职责已经正式改变；
- 新窗口名称应尽量稳定，避免每处理一个 Task 就重命名；
- 若同一角色需要多个并行窗口，可使用稳定编号，例如“开发工程师1号 / 2号”。

## 6. Review 独立性
创建 Review Task 前必须核对：
```text
Assigned Reviewer != Original Agent
```
高风险交付如果无法独立 Review，不得伪装为已通过；保持 `PENDING_INDEPENDENT_REVIEW`。

## 7. 并发
并发前确认：
- Task 之间无未解决写冲突；
- workspace 可物理隔离；
- Depends On 不要求串行；
- 同一协调文件不会被多个 Execution Task 同时修改。

## 8. Result 验收
Executor 的 SUCCESS / PASS 不是自动 ACCEPTED。
Orchestrator 应根据风险选择：
- 直接接受低风险事实；
- 检查 diff / tests / commit；
- 派独立 Review；
- 要求 Fix / Re-Review。

如果 Web GPT 当前没有足够工具验证关键事实，应安排具备能力的独立验证，而不是假装自己已验证。

## 9. Coordination 写入
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

## 10. Coordination CAS
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

## 11. Orchestrator Handoff
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

Handoff 默认只携带：Active / In Review / Blocked Task、Open Findings、Review Debt、Pending Decisions、当前 Baseline 和 Next Eligible Actions。已经安全归档的历史 Task 不重新塞入新主窗口上下文。

## 12. Stale Policy
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

## 13. 上下文与 Archive 维护
主调度窗口只保留调度所需的最小事实。
复杂设计、实现、深入 Review 优先派给专门 Agent / 会话。
需要换 Web GPT 会话时先形成最小 handoff，不依赖聊天记忆维持项目真相。

Orchestrator 必须在以下任一时点执行一次 Archive Sweep：

- Project Phase 切换；
- Baseline 冻结；
- Release 完成；
- 活跃目录中存在 10 个及以上满足归档条件的终态 Task；
- handoff 前发现大量终态记录已经与下一阶段无关。

归档前必须确认：Task 已终态、不再处于 Review/Fix/Integration、无活跃依赖、无未清 Review Debt / Blocking Finding、不会破坏 Baseline / Release 审计引用。

Archive 的目的只是把历史移出默认读取面，不改变事实。详细规则见 `coordination/WORKFLOW.md` 与 `coordination/archive/README.md`。

## 14. Task 生命周期记录与用户进度简述

每个正式 Task 都必须保持可恢复的最小执行链，不依赖聊天上下文：

- `coordination/tasks/<Task>.md`：作为 START 记录，定义起点、目标、边界、Agent、Epoch/Revision、Stale Policy 与验收条件；
- `coordination/checkpoints/`：在长任务、关键阶段转换、上下文中断、Agent handoff 或出现 Finding/Blocker 时记录 PROGRESS / HANDOFF；
- `coordination/results/`：作为最终 RESULT，记录交付、验证、SHA、Findings、Blockers；
- `coordination/STATUS.md`：记录项目级当前状态、Review Debt、Open Findings、Gate 与 Next Eligible Actions。

Checkpoint 至少应回答：

```text
Current Step:
Completed:
Remaining:
Current Files / Branch / Commit:
Findings:
Blockers:
Next Action:
```

只要任务尚未终态，就必须能够从 Repository 记录中回答“现在做到哪里、还剩什么、下一步是什么”。

此外，Active Orchestrator 每次向用户报告调度结果时，都应附带一个**简短任务进度说明**。通常包含：

```text
当前 Task / Gate
状态
本次完成
Finding / Blocker（如有）
下一步
```

该简述用于用户快速掌握项目，不替代 Repository 的正式记录。

## 15. 设计思路与可复用经验落库

有长期参考价值的设计 reasoning（推理）、工程取舍、拒绝方案、延期边界和可复用开发经验，不应只存在于聊天上下文。

统一落入：

`docs/development/notes/`

规则见：

`docs/development/notes/README.md`

必须优先记录以下内容：

- 非显然的架构 / ownership / lifecycle / fencing / recovery / security 取舍；
- 为什么拒绝某个看似方便的实现；
- 为什么把某个机制推迟到后续真实边界；
- Finding 暴露出的可复用设计规律；
- 可抽象成通用 AI 开发调度、Review、测试、上下文、交付方法的经验；
- 用户明确要求保留、以后整理成通用文档的开发或设计思路。

Design Note 默认是 `NON-NORMATIVE / WORKING REFERENCE`，不能覆盖 Frozen Design、Contract、Baseline 或正式 Coordination state。

当某条思路成熟为正式约束时，必须通过正式 Task / Review 流程晋升为 Design、Contract、Amendment 或 Development Guide；不能因为写进 notes 就自动获得规范权威。
