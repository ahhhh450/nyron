# Repository-Driven Agent Context Routing Design Note v0.1

状态：`DESIGN NOTE / NOT FROZEN`

用途：记录 Nyron 实际开发调度中形成的协同框架设计方向，供后续真实项目运行复盘、归纳与通用框架演进使用。本文件不修改 Nyron Frozen Architecture，也不改变当前 Development Gate。

## 1. 核心目标

理想状态下，Development Orchestrator 不应在每个任务提示词中重复手工列出大量 Markdown 路径。

职责应收敛为：

```text
Orchestrator 决定：做什么、谁做、风险、边界、依赖、验证、交付
Repository 决定：为了完成该 Task，Agent 应读取什么、按什么方法执行
```

目标是让调度 Prompt 越来越短，同时让 Repository 中的角色入口、Task、Skill 和项目设计索引承担稳定的上下文路由责任。

## 2. 理想执行链路

```text
Development Orchestrator
→ 下发固定格式 Task identity / assignment
→ Agent 读取自己的 canonical role entrypoint
→ role entrypoint 导航到 AGENTS / STATUS / 当前 Task
→ 根据 Task Type 选择对应 Skill
→ Task 提供当前任务特有的最小 Required Context
→ Agent 执行、验证并返回固定格式 Result
```

固定框架文件不应由 Orchestrator 每次重复粘贴或重复列举。

## 3. Role Entrypoint

每类 Agent 应具有稳定的 canonical role entrypoint，例如：

- `CODEX.md`
- `CLAUDE.md`
- `DEEPSEEK.md`

角色入口负责告诉 Agent：

1. 公共规则在哪里；
2. 项目协调状态在哪里；
3. 当前 Task 在哪里；
4. 不同 Task Type 应读取哪个 Skill；
5. 如何遵守最小上下文加载原则。

角色入口应长期复用，不随 Task ID 改变。

## 4. Task 的职责

Task 应重点描述当前工作本身，而不是重复整个协同框架。

Task 主要包含：

```text
Task Identity
Type
Risk
Priority
Scope
Out of Scope
Constraints
Dependencies
Required Context
Validation
Deliverables
Acceptance / Completion Criteria
```

其中 `Required Context` 应优先只列当前 Task 特有的设计、Contract、Module、Decision 或其他项目事实。

固定的 `AGENTS.md`、角色文件、`STATUS.md`、对应 Skill 等，应由角色入口和 Task Type 路由，不需要 Orchestrator 每次重复声明。

## 5. Context Routing 原则

默认采用最小必要上下文：

```text
Role Entrypoint
→ Common Rules
→ Coordination Status
→ Current Task
→ Task-Type Skill
→ Task-Specific Required Context
```

禁止因为 Repository 中存在某个文档就默认读取它。

尤其不默认读取：

- 其他 Agent 的角色文件；
- 全部历史 Tasks；
- archive；
- 与当前 Scope 无关的 Frozen Baseline；
- 全部 design 文档；
- 全仓库源码。

## 6. Orchestrator Prompt 收敛目标

成熟状态下，Agent 启动指令应能够收敛到类似：

```text
Repository: <repo>
Role: <role>
Task: <task-id>

Load the repository canonical role entrypoint and execute this Task.
Do not expand scope.
Return the canonical Task Result.
```

具体执行规则由 Repository 自己解析，而不是依赖聊天 Prompt 携带完整操作手册。

## 7. 会话窗口与 Task 解耦

Agent 会话窗口应按长期职责命名，而不是按 Task ID 命名。

例如：

```text
Nyron开发工程师1号-Codex
Nyron开发工程师2号-Claude
Nyron低风险审查员-DeepSeek
```

一个长期角色窗口可以连续处理多个正式 Task。

只有在上下文压力、独立 Review、并行隔离、职责分离或其他明确需要时才新开窗口。Task ID 属于 Task 控制面，不作为会话生命周期的默认边界。

## 8. Future Context Index（候选方向）

如果真实项目运行证明路径定位成为持续负担，可以未来引入轻量 Context Index / Registry，将语义名称映射到权威文档，例如：

```text
Runtime Orchestration
→ <authoritative design path>

Execution Lease
→ <authoritative contract path>
```

当前不因潜在未来需求提前建立该层。只有真实摩擦、重复维护成本或明确消费者出现后再决定是否实现，遵守 YAGNI / Minimum Necessary Complexity。

## 9. 与现有框架的关系

本设计方向建立在现有：

- `AGENTS.md`
- Agent role files
- `coordination/STATUS.md`
- formal Task
- `skills/*`
- `coordination/OUTPUT_FORMAT.md`

之上。

它不是新的 Authority，也不高于 Task / Frozen Contract。

后续应根据 Nyron 真实开发运行证据，判断是否把该设计原则正式归纳进通用多 Agent 开发协同框架。