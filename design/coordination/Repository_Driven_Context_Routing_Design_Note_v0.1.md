# Repository-Driven Agent Context Routing Design Note v0.1

状态：`DESIGN NOTE / NOT FROZEN`

用途：记录 Nyron 实际开发调度中形成的协同框架设计方向，供后续真实项目运行复盘、归纳与通用框架演进使用。本文件不修改 Nyron Frozen Architecture，也不改变当前 Development Gate。

## 1. 核心原则

Development Orchestrator 不应依赖聊天会话承载 Agent 之间的正式上下文传递。

职责应收敛为：

```text
Orchestrator 决定：做什么、谁做、风险、边界、依赖、验证、交付
Repository 决定：Agent 应读取什么、执行什么、如何交付、如何被下一 Agent 消费
Chat Session 只负责：启动 / 指向 / 状态通知
```

核心设计结论：

> Agent 间的正式 handoff 应是 Repository file handoff，而不是 conversation handoff。

目标是让调度 Prompt 越来越短，同时让 Repository 中的 Role Entrypoint、Task、Result、Checkpoint、STATUS、Skill 和设计索引承担稳定的上下文路由责任。

## 2. Repository 作为 Agent 协作总线

正式信息流应通过 Repository 持久化，而不是通过用户复制粘贴一个 Agent 的长输出给另一个 Agent。

推荐链路：

```text
Development Orchestrator
    ↓ writes
coordination/tasks/<TaskID>.md
    ↓ Agent reads
Developer / Reviewer / Auditor
    ↓ executes
code / tests / commit
    ↓ writes
coordination/results/<TaskID>.md
    ↓ Orchestrator reads
Disposition / Finding / next Task / STATUS
```

若任务中断或需要跨窗口 / 跨 Agent 继续：

```text
coordination/checkpoints/<TaskID>-CP-xxx.md
```

因此，正式上下文的生命周期属于 Repository，而不是聊天窗口。

## 3. 文件职责分离

推荐固定语义：

```text
Task       = instruction / contract for one unit of work
Result     = evidence + conclusion for that Task
Checkpoint = interrupted execution state / handoff state
STATUS     = compact canonical coordination index
Design     = durable design rationale / reusable principles
```

### 3.1 Task

Task 只描述当前工作：

- Task identity;
- type / risk / priority;
- assigned Agent;
- scope / non-goals;
- dependencies / exact basis;
- required context;
- validation;
- delivery contract;
- canonical result path。

Task 不追加最终执行结果。

### 3.2 Result

每个正式 Task 应拥有独立结果文件：

```text
coordination/results/<TaskID>.md
```

Result 只记录：

- exact delivered / reviewed SHA;
- key validation evidence;
- conclusion;
- Findings;
- interlocks;
- blockers;
- integration recommendation where applicable。

Result 应引用 Task / Finding / SHA，而不是复制整个 Task 或完整历史上下文。

### 3.3 Checkpoint

Checkpoint 只在真实中断、额度耗尽、会话切换、Agent handoff 或长任务恢复时使用。

它记录：

- 当前 Task;
- 已完成内容;
- 未完成内容;
- exact current files / SHA;
- blockers;
- next action。

正常完成的 Task 不需要额外生成 Checkpoint。

### 3.4 STATUS

`coordination/STATUS.md` 应保持紧凑，只承担：

- current Epoch / Revision;
- active Tasks;
- accepted production tip;
- current Gate / Phase;
- open Findings / blockers;
- pointers to Task / Result / Checkpoint。

STATUS 不应成为历史全文日志。

## 4. Conversation 不是正式传输层

聊天窗口是 transient execution interface，不是 canonical project state。

成熟状态下，Agent 启动消息应尽量收敛为：

```text
[NEW WINDOW | Codex]
Repository: <repo>
Task: <TaskID>
Load the repository canonical role entrypoint and execute this Task.
```

或已有窗口：

```text
[EXISTING WINDOW | Claude Code]
Task: <TaskID>
```

不应继续通过聊天重复传递：

- 上一个 Agent 的完整输出；
- 大段设计背景；
- 完整测试日志；
- 全部 Findings 历史；
- 多份 Markdown 正文。

这些应由 Task 引用 Repository 中的 canonical files。

## 5. Agent 完成协议

正式 Agent 完成任务时，默认不要求用户把大段 `[TASK RESULT]` 从一个窗口复制给 Orchestrator。

Agent 应：

1. 完成代码 / review / audit；
2. 写入自己的 `coordination/results/<TaskID>.md`；
3. commit + push Result；
4. 不修改 Orchestrator-owned `coordination/STATUS.md`，除非 Task 明确授权；
5. 聊天中只返回极短完成通知，例如：

```text
TASK DONE: NYRON-T-...
Result: coordination/results/NYRON-T-....md
```

用户只需要告诉 Orchestrator：

```text
079 done
```

Orchestrator 随后自行从 Repository 读取 Result、验证远端事实并继续调度。

## 6. Role Entrypoint

每类 Agent 应具有稳定的 canonical role entrypoint，例如：

- `CODEX.md`
- `CLAUDE.md`
- `DEEPSEEK.md`

角色入口负责告诉 Agent：

1. 公共规则在哪里；
2. 项目协调状态在哪里；
3. 当前 Task 在哪里；
4. 不同 Task Type 应读取哪个 Skill；
5. 如何遵守最小上下文加载原则；
6. 如何执行 Repository Result Protocol。

角色入口长期复用，不随 Task ID 改变。

## 7. Context Routing 原则

默认采用最小必要上下文：

```text
Role Entrypoint
→ Common Rules
→ Coordination Status
→ Current Task
→ Task-Type Skill
→ Task-Specific Required Context
→ referenced prior Result only when needed
```

禁止因为 Repository 中存在某个文档就默认读取它。

尤其不默认读取：

- 其他 Agent 的角色文件；
- 全部历史 Tasks / Results；
- archive；
- 与当前 Scope 无关的 Frozen Baseline；
- 全部 design 文档；
- 全仓库源码。

## 8. 会话窗口与 Task 解耦

Agent 会话窗口不是 Task 的 canonical state container。

同一个 Agent 可以同时拥有 2–3 个独立会话，只要：

- 不产生未协调的同文件写冲突；
- 不并行修改同一尚未冻结 Contract；
- 每个会话都绑定明确 Task / exact basis；
- Result 独立落库。

只有上下文压力、独立 Review、并行隔离、职责分离等原因才决定新开窗口。Task ID 属于 Task 控制面，不作为会话生命周期的默认边界。

## 9. Orchestrator Prompt 收敛目标

成熟状态下，启动 Prompt 可以缩短为：

```text
Repository: <repo>
Task: <task-id>

Load canonical role entrypoint and execute the Task.
```

真正传递的是 Task 文件引用，而不是聊天上下文。

## 10. Future Context Index（候选方向）

如果真实项目运行证明路径定位成为持续负担，可以未来引入轻量 Context Index / Registry，将语义名称映射到权威文档。

当前不因潜在未来需求提前建立该层。只有真实摩擦、重复维护成本或明确消费者出现后再决定是否实现，遵守 YAGNI / Minimum Necessary Complexity。

## 11. 与现有框架的关系

本设计方向建立在现有：

- `AGENTS.md`
- Agent role files
- `coordination/STATUS.md`
- formal Task / Result / Checkpoint
- `skills/*`
- `coordination/OUTPUT_FORMAT.md`

之上。

它不是新的 Authority，也不高于 Task / Frozen Contract。

后续应根据 Nyron 的真实开发运行证据，判断是否把该设计原则正式归纳进通用多 Agent 开发协同框架。
