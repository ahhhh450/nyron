# Review Protocol

## 1. 独立性

默认：
```text
Implementation Agent != Independent Reviewer
```

Review Task 必须记录：
- Reviews Task
- Original Agent
- Assigned Reviewer
- Review Independence

可选值：
```text
REQUIRED
OPTIONAL
WAIVED
```

`WAIVED` 不等于独立审查已完成。

当本应执行的独立 Review 被 `WAIVED` 时，必须产生显式 `Review Debt`，由 Orchestrator 记录到协调状态中。不得因为后续继续开发而自动消失。

Review Debt 至少记录：
- 对应 Task / Delivery；
- 被 Waive 的 Review 类型；
- 原因；
- 风险等级；
- 清偿条件。

只有真正满足清偿条件的独立 Review / Re-Review 完成并被 Orchestrator 接受后，Review Debt 才能关闭。

## 2. 高风险交付

以下内容在进入稳定 Baseline / Release 前必须完成真正独立 Review：
- Architecture
- Contract
- Security-sensitive change
- Core Runtime
- Concurrency / Replay / Recovery
- Baseline change
- Release-critical change

若暂时无法独立 Review，状态保持：
```text
PENDING_INDEPENDENT_REVIEW
```

并形成 Review Debt。

高风险交付存在未清偿 Review Debt 时，不得进入稳定 Baseline / Release。

## 3. Review 默认只读

Reviewer 默认不得顺手修复被审查内容。若需要修复，应创建 Fix Task 或由原 Implementation Task 的责任 Agent 处理。

## 4. Review 输出

结论：
```text
PASS
PASS_WITH_FINDINGS
FAIL
ESCALATION_REQUIRED
```

Finding 统一字段：
- Finding ID
- Type
- Code（可选，但标准化问题应优先填写）
- Severity
- Location
- Evidence
- Impact
- Required Resolution

Finding Type：
```text
IMPLEMENTATION
TEST
CONTRACT
ARCHITECTURE
SECURITY
PROCESS
```

标准 Finding Code 包括：
```text
OVER_ENGINEERING
```

`OVER_ENGINEERING` 使用：
```text
Type: IMPLEMENTATION
Code: OVER_ENGINEERING
```

这样保留稳定的一级 Finding taxonomy，同时让“过度设计”成为可搜索、可统计、可 Re-Review 的标准问题类型。

Severity：
```text
BLOCKING
NON_BLOCKING
```

## 5. Implementation Complexity Review

对 Implementation / Refactor / Fix Task，Reviewer 必须把复杂度合理性作为显式检查项，而不是只检查代码能否运行。

### 5.1 Complexity trace

当实现引入以下任一结构时，应检查其当前需求来源：

- 新 abstraction layer；
- Factory / Strategy / Registry / Manager / Coordinator / Wrapper；
- generic framework；
- plugin/extensibility layer；
- 多 backend / 多 provider 抽象；
- 多层间接调用；
- 为消除少量重复而引入的高度参数化通用逻辑。

Reviewer 应尝试把该复杂度追溯到至少一个明确依据：

```text
Task Scope
Task Constraints
Frozen Contract / Invariant
明确验收标准
当前真实存在的使用场景
```

如果 Implementer 声称某结构是为了满足 Constraint / Contract，Reviewer 必须实际核对对应文字，而不是接受自我解释。

### 5.2 三个核验问题

Reviewer 至少问：

```text
1. 这层复杂度解决哪个当前问题？
2. 对应 Task / Contract / Invariant 的哪一条？
3. 删除这层复杂度后，哪条当前 requirement 会失败？
```

如果只能得到以下理由，默认不足以证明复杂度合理：

```text
以后可能扩展
这样更灵活
更通用
可能以后会用到
业界常见做法
```

### 5.3 OVER_ENGINEERING Finding

满足以下模式之一时，应产生：

```text
Type: IMPLEMENTATION
Code: OVER_ENGINEERING
```

典型触发条件：

- 找不到当前 Task / Contract / Invariant 对复杂结构的需求依据；
- 删除该层复杂度后当前 requirement 仍全部满足；
- 为一个当前场景提前建立通用框架；
- 为两个表面相似、但语义不同或变化原因不同的代码路径强行抽象；
- Task 未要求，却引入大范围可扩展机制；
- 为减少少量重复显著降低可读性、可定位性或可独立演化能力。

Severity 判断：

- `BLOCKING`：复杂度明显扩大当前维护/故障/正确性风险，污染核心路径，或使 Task 交付偏离 Scope；
- `NON_BLOCKING`：局部冗余抽象但当前风险有限，可由 Orchestrator 决定是否立即简化。

### 5.4 DRY / abstraction review

看到重复代码时，不以“重复存在”本身要求抽象。

应检查：

```text
至少两个真实当前场景
+ 同一语义概念
+ 同一 reason to change
+ 抽象后更清晰
```

若两个路径未来可能因为不同 Contract / domain rule 独立变化，应优先保持分离，即使存在少量重复。

### 5.5 范围边界

本节用于识别 speculative implementation complexity。

它不得被用来攻击已经由当前 correctness / coordination / audit / recovery / security 需求证明必要的结构，例如 Task / Result / Checkpoint、Epoch / Revision、CAS、fencing、Review Debt、Frozen Baseline 等。

Reviewer 判断的是：

```text
required structural complexity
vs
speculative complexity
```

不是简单按“代码行数少”判优。

## 6. Re-Review

Re-Review 应优先做 targeted verification，只验证原 Finding 是否关闭以及修复是否引入新问题，不默认重复完整审查。

如果 Re-Review 的目标是清偿 Review Debt，Task 必须明确指出所清偿的 Debt / Delivery，避免一次无关 Review 被错误当成债务已关闭。

对于 `OVER_ENGINEERING` 的 Re-Review，应验证：
- 无依据的层级/抽象是否被删除或简化；
- 如果保留，是否已经提供可核验的当前 requirement trace；
- 简化是否引入 correctness / contract regression。

## 7. Reviewer 选择

- Claude Code：复杂架构、复杂实现、Contract、高风险 Review。
- Codex：代码 correctness、工程实现、测试、CI、复杂代码 Review。
- DeepSeek：低风险 Review、定向 Re-Review、文档一致性、机械验证。

DeepSeek 可以检查明确的 complexity trace / checklist，但高风险核心实现的最终放行仍由 Orchestrator 根据风险选择 Codex / Claude Code 或交叉 Review。

实际分配由 Orchestrator 根据风险裁决。
