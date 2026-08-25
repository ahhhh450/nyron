# Skill: Implementation

用于明确 Task 范围内的代码或配置实现。

本 Skill 定义的是**默认实现方法**，不是新的架构层或高于 Task 的强制需求来源。

优先级遵循 `AGENTS.md`：

```text
明确的人类指令
> 已冻结项目规则 / Baseline
> AGENTS.md
> Task 中由 AGENTS.md 明确定义的特殊授权字段
> Agent 专属规则
> Task 一般执行内容
> Skill / 执行建议
```

因此：

- Task / Frozen Contract 决定“必须实现什么”；
- 本 Skill 只决定“在多个合规方案中优先选择哪个实现”；
- 如果 Task 明确要求可扩展、多 Provider、插件化、隔离层或其他复杂结构，则应满足该明确需求，但仍选择满足需求的最简单方案。

---

## 1. 适用范围

本 Skill 主要约束实现层代码、配置、测试辅助代码和 Task-scoped 工程修改。

它**不用于否定**已经有现实 correctness / coordination / audit / recovery / security 需求依据的结构化协议，例如：

- Task / Result / Checkpoint；
- Coordination Epoch / Revision；
- CAS / fencing；
- Review Debt；
- Frozen Baseline / Amendment；
- 为 crash / replay / multi-agent correctness 明确要求的 durable state 或 protocol。

核心区别：

```text
禁止 speculative complexity
允许 required structural complexity
```

YAGNI 反对的是“为了可能的未来而提前制造实现复杂度”，不是删除已经由当前需求证明必要的治理或正确性结构。

---

## 2. 核心实现原则

### 2.1 Simple Correct First

在满足当前 Task、Contract、Invariant、安全要求和验证要求的多个方案中，优先选择：

```text
simple correct code
> clever code
> speculative abstraction
> premature generalization
```

不要为了显得完整而主动增加 Factory / Manager / Coordinator / Wrapper / Registry / Interface / Strategy 等层级。

每增加一层间接结构，都必须能说明它解决哪个**当前真实问题**。

### 2.2 YAGNI

不要因为以下理由提前实现能力：

- “以后可能需要”；
- “这样更灵活”；
- “未来可能支持更多 Provider / DB / plugin”；
- “先把框架搭好以后方便”。

除非这些能力已经出现在当前 Task Scope / Constraints、Frozen Contract、明确验收标准或当前真实使用场景中。

### 2.3 Single Clear Responsibility

函数、类、模块应有一个清晰责任边界。

不要机械追求固定行数；判断标准是：一个单元是否因为多个不同原因而需要修改。

如果一个函数同时承担验证、数据库写入、外部调用、状态推进、重试和日志编排等多个独立职责，应优先拆成更清晰的单元。

### 2.4 Explicit Over Magic

优先显式的数据流、状态变化、依赖和错误路径。

避免为了“优雅”引入隐藏注册、隐式 hook、难追踪 callback 链、运行时魔法或隐藏 durable state。

### 2.5 Small Task-Scoped Diff

只修改完成当前 Task 必需的代码。

禁止无授权的：

- 顺手重构；
- 顺手统一全仓库风格；
- 顺手替换框架；
- 顺手抽象公共层；
- 顺手修复相邻非阻塞问题。

相邻问题返回 Finding，由 Orchestrator 决定是否另建 Task。

---

## 3. Abstraction Policy

### 3.1 两个场景不是充分条件

“出现两个使用场景”只代表可以开始评估抽象，不代表必须抽象。

只有同时满足以下条件时，才优先考虑公共抽象：

```text
存在至少两个真实当前场景
+ 表达的是同一个语义概念
+ 预计会因为同一个原因变化
+ 抽象后比保持分离更清晰
```

否则允许保留少量重复。

### 3.2 DRY 的 reason-to-change 判据

两段看起来相似的代码，如果未来大概率会因为**不同原因**独立变化，就不应为了消除重复而强行合并。

例如：

```text
validate_capability()
validate_resource_lease()
```

即使当前实现有几行相似，只要它们分别受不同 Contract / lifecycle 驱动，就不应仅为了 DRY 合并成难以理解的 GenericValidator。

原则：

```text
same-looking code
+ different semantic meaning / different reason to change
-> keep separate
```

### 3.3 不允许猜测性公共框架

没有当前真实消费者、当前 Task 要求或 Frozen Contract 依据时，不得主动建立大范围通用 framework、plugin system、strategy registry、multi-backend abstraction 或 extensibility layer。

---

## 4. Complexity Must Be Justified

任何明显增加实现复杂度的结构，都必须能追溯到至少一个当前依据：

- Task Scope；
- Task Constraints；
- Frozen Contract / Invariant；
- 当前明确验收标准；
- 当前真实存在的第二使用场景。

实现 Agent 在需要采用较复杂方案时，应能回答：

```text
1. 这层复杂度解决哪个当前问题？
2. 对应哪一条 Task / Contract / Invariant？
3. 如果删除这层复杂度，哪条当前 requirement 会失败？
```

仅以下理由不足以证明复杂度合理：

```text
为了以后扩展
为了更灵活
更通用
可能以后会用到
业界通常这样做
```

如果无法建立可核验的当前需求链，应回退到更简单实现。

---

## 5. 可读性与控制流

优先：

- 直接、领域明确的命名；
- early return 降低嵌套；
- 清楚的数据流：input -> validate -> transform/execute -> persist -> result；
- 小而明确的 public API；
- 局部、可定位的错误处理。

避免：

- 含义模糊的 `manager` / `helper` / `processor` 大杂烩；
- 多层无业务价值转发；
- 深层嵌套；
- callback / wrapper / hook 形成难追踪链路；
- 为减少几行重复引入更复杂的参数化通用函数。

---

## 6. 标准执行方法

1. 确认 Scope / Out of Scope / Constraints。
2. 确认当前 Task 是否显式要求某种扩展性或复杂结构。
3. 确认隔离 workspace 和当前 git 状态。
4. 先寻找满足当前 Contract 的最小正确实现。
5. 若引入非平凡抽象/层级，建立 Complexity Justification。
6. 采用最小必要改动，不顺手重构无关区域。
7. 执行 Task 指定验证；未指定时执行与改动直接相关的最小测试。
8. 发现架构/Contract 问题时返回 Finding，不越权改设计基线。
9. Commit 保持 Task-scoped。

---

## 7. 完成前自检

实现 Agent 在报告 SUCCESS 前至少检查：

```text
- 是否存在 Task 没要求的新抽象层？
- 是否实现了“以后可能需要”的能力？
- 是否有可以删除而不影响当前 requirement 的复杂结构？
- 新抽象是否真的有两个当前场景、同一概念、同一变化原因？
- 是否为了 DRY 把不同领域语义错误合并？
- 是否发生无关重构或 Scope 扩张？
- 是否所有声明的复杂度都能追溯到 Task / Contract / Invariant？
```

无法合理解释的复杂度应在交付前简化。

---

## 8. 完成条件

实现、验证、Result 三者都完成后才可报告 SUCCESS；是否 ACCEPTED 由 Orchestrator 决定。

实现风格的目标不是追求“最少代码行数”，而是：

> **在不牺牲 correctness、security、replay、recovery、maintainability 和明确当前需求的前提下，保持最少的必要复杂度。**
