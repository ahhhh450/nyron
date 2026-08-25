# 通用多 Agent 开发协同框架设计候选版 v0.1

状态：`DESIGN CANDIDATE / NOT FROZEN`

用途：作为 Web GPT 指挥 Codex、Claude Code、DeepSeek 等开发 Agent 的通用协同框架设计基础。后续可进一步演化为跨项目复用的 `README.md`、`AGENTS.md`、`CLAUDE.md`、`CODEX.md`、`DEEPSEEK.md`、Coordination Protocol、Task Template、Review Template 与 Skill 模板体系。

---

## 1. 设计目标

建立一套适用于单人 + 多 AI Agent 软件开发的协同控制结构，使：

- Web GPT 负责开发调度、任务分配、状态裁决和集成决策；
- Codex / Claude Code 负责核心设计、实现、复杂审查等执行工作；
- DeepSeek 默认优先承担简单、低风险、机械性任务，以及独立 Review / Re-Review / 定向验证；
- Repository 中的结构化 Markdown 成为跨模型、跨会话、跨时间的共享事实载体；
- Agent 换会话、上下文中断、额度中断时，项目仍可恢复；
- 并发执行、Review、Task ID、项目状态和 Baseline 不因多 Agent 协作而失控。

---

## 2. 角色模型

### 2.1 Web GPT — Development Orchestrator

Web GPT 是项目的 **Coordination Authority（协同裁决权威）**。

负责决定：

- Task 创建；
- Task ID；
- Assigned Agent；
- Priority；
- Task dependency；
- Development Gate；
- Review / Re-Review 分配；
- 交付接受或拒绝；
- 项目级 STATUS；
- Baseline / Release 是否成立。

原则：

> Executor 报告事实，Orchestrator 决定项目状态。

### 2.2 Codex / Claude Code / DeepSeek — Execution Agent

Execution Agent 可以承担：

- Implementation；
- Design；
- Test；
- Review；
- Re-Review；
- Documentation；
- Mechanical Validation。

但默认无权：

- 自行创建 Task；
- 自行生成 Task ID；
- 自行改变 Priority；
- 自行推进 Development Gate；
- 自行宣布项目级 COMPLETED / ACCEPTED；
- 自行冻结 Baseline；
- 自行取得 Coordination Authority。

---

## 3. Authority 与 Physical Write 分离

原始 Single Writer 思路修正为：

> **Single Coordination Authority**，而不是要求 Orchestrator 必须亲自执行所有文件写入。

即：

```text
Decision Authority != Physical Writer
```

Web GPT 负责决定协调内容。

如果 Web GPT 拥有直接 Repository 写权限，可以直接执行协调文件写入。

如果 Web GPT 没有直接写权限，则应：

```text
Orchestrator 决定协调状态
→ 生成明确 Coordination Update
→ 指定 Execution Agent 机械落盘
→ Agent 返回 diff / commit
→ Orchestrator 验收
```

普通 Implementation Task 不允许“顺手”修改协调控制文件。

协调状态变更应与实现改动分离，避免代码修改与状态裁决捆绑在同一未经授权的变更中。

---

## 4. 单一有效 Orchestrator

一个项目同一时刻只能存在一个有效的 Active Orchestrator。

建议在协调状态中保留：

```text
Active Orchestrator
Coordination Epoch
Coordination Revision
```

新 Web GPT 会话接管项目时，通过显式 handoff 提升 Epoch。

旧 Orchestrator 基于旧 Epoch 发出的协调动作应视为 stale，不再有效。

该机制用于降低两个 Web GPT 会话同时调度同一项目造成的双写和任务冲突风险。

---

## 5. Coordination Revision 与过期检测

项目协调状态应具有可比较的 Revision。

示例：

```text
Coordination Revision: 37
Last Accepted Commit: abc123
```

Task 可记录：

```text
Based On Coordination Revision: 37
```

如果 Orchestrator 在关键状态转换时发现当前 Revision 已发生变化，则旧判断不得直接继续使用，应重新读取最新状态。

目标：避免基于过期 STATUS 继续调度。

---

## 6. 基础目录建议

```text
project/
│
├─ README.md
├─ AGENTS.md
├─ CLAUDE.md
├─ CODEX.md
├─ DEEPSEEK.md
│
├─ coordination/
│  ├─ README.md
│  ├─ STATUS.md
│  ├─ WORKFLOW.md
│  ├─ TASK_PROTOCOL.md
│  ├─ REVIEW_PROTOCOL.md
│  ├─ OUTPUT_FORMAT.md
│  ├─ tasks/
│  ├─ results/
│  ├─ checkpoints/
│  └─ archive/
│
├─ design/
├─ docs/
├─ skills/
├─ src/
└─ tests/
```

职责：

- `README.md`：项目入口；
- `AGENTS.md`：所有 Agent 的公共强制规则；
- `CLAUDE.md`：Claude Code 特有执行规则；
- `CODEX.md`：Codex 特有执行规则；
- `DEEPSEEK.md`：DeepSeek 特有执行规则；
- `coordination/`：开发协同控制面；
- `design/`：架构、模块、Contract、Decision、Baseline；
- `skills/`：某类任务的通用执行方法；
- `docs/`：开发、运行、用户文档。

工具能力差异应尽量收敛在各 Agent 专属文件中，`AGENTS.md` 不应假设所有 Agent 拥有完全相同的 Git / Sandbox / Commit 能力。

---

## 7. Task 模型

所有正式工作应基于明确 Task。

Task ID 只能由 Orchestrator 分配，Executor 不允许通过“当前最大编号 + 1”等方式推导或创建 Task ID。

建议通用 Task ID：

```text
T-YYYYMMDD-NNN
```

项目需要命名空间时可扩展：

```text
PROJECT-T-YYYYMMDD-NNN
```

Task 建议至少包含：

```text
Task ID
Type
Assigned Agent
Status
Priority
Based On Coordination Revision

Parent Task
Depends On
Blocks
Reviews Task

Objective
Required Reading
Scope
Out of Scope
Constraints
Required Changes
Validation
Deliverables
Output Format
Completion Criteria
```

`Required Reading` 应遵循最小上下文原则，不默认要求扫描整个 Repository。

---

## 8. Task Dependency

依赖关系必须成为一等结构，而不是只写在自然语言说明中。

示例：

```text
Task: T-003
Depends On:
- T-001
- T-002
```

当依赖尚未达到要求的接受状态时，Task 应保持 `BLOCKED`，而不是由 Executor 自行猜测是否可以继续。

---

## 9. 并发执行与工作区隔离

公共强制原则：

> Concurrent Tasks MUST NOT share a mutable working tree.

并行 Task 必须获得隔离的 branch / worktree / sandbox 或等价执行环境。

例如：

```text
T-021 -> Workspace A
T-022 -> Workspace B
T-023 -> Workspace C
```

具体如何建立隔离环境，由 `CLAUDE.md`、`CODEX.md`、`DEEPSEEK.md` 根据各自工具能力定义。

---

## 10. Result 模型

Executor 完成任务后返回统一结果。

示例：

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

`Execution Result: SUCCESS` 只代表 Executor 报告其执行成功。

它不自动等价于：

```text
Task = COMPLETED
Delivery = ACCEPTED
Baseline = FROZEN
```

这些项目级状态由 Orchestrator 裁决。

---

## 11. Findings 统一模型

统一使用术语：

```text
Findings
```

Finding 可分类：

```text
IMPLEMENTATION
TEST
CONTRACT
ARCHITECTURE
SECURITY
PROCESS
```

严重程度建议至少支持：

```text
BLOCKING
NON_BLOCKING
```

避免同时使用 Architecture Finding、Known Problems、Issues 等多个含义重叠的术语。

---

## 12. Checkpoint

只保留一套 Checkpoint 结构，通过 Type 区分用途：

```text
Type: PROGRESS | HANDOFF
```

建议字段：

```text
Task ID
Type
Current Step
Completed
Remaining
Files Touched
Validation
Findings
Blockers
Next Action
```

长任务可在重要阶段刷新 `PROGRESS` Checkpoint。

发生以下情况应产生 `HANDOFF` Checkpoint：

- Agent 更换；
- context 中断；
- quota 中断；
- Task 暂停；
- Blocking Failure；
- 需要新会话继续。

权威优先级：

```text
Accepted Project State
> Final Result
> Latest Checkpoint
> Earlier Checkpoint
```

Final Result 产生后，Checkpoint 只作为历史过程记录，不覆盖最终结果。

---

## 13. 独立 Review

默认原则：

> Implementation Agent != Independent Reviewer

Orchestrator 分配 Review Task 时必须检查 Reviewer 与 Original Implementation Agent 是否不同。

Review Task 应显式包含：

```text
Reviews Task
Original Agent
Assigned Reviewer
Review Independence
```

可使用：

```text
REQUIRED
OPTIONAL
WAIVED
```

如果只能自审，可标记 `WAIVED`，但自审不应伪装成真正的独立审查。

以下高风险交付不应在只有 WAIVED Review 的情况下直接进入稳定 Baseline：

- Architecture；
- Contract；
- Security-sensitive change；
- Core runtime；
- Baseline change；
- Release-critical change。

这些交付在缺少独立 Review 时可保持：

```text
PENDING_INDEPENDENT_REVIEW
```

DeepSeek 可优先承担低风险独立 Review、定向验证和 Re-Review；高风险架构或复杂实现仍应根据能力选择更合适的 Reviewer。

---

## 14. 基本开发链路

推荐：

```text
Task
-> Implementation
-> Review
-> Fix
-> Targeted Re-Review
-> Integration
-> Baseline / Release
```

并非所有 Task 都必须走完整流程。

低风险、机械性任务可以简化。

核心代码、Architecture、Contract、Security、Baseline 等修改应提高 Review 要求。

---

## 15. Violation Protocol

如果 Execution Agent 出现以下行为：

- 修改 Task 明确禁止的文件；
- 未授权修改协调控制文件；
- 自行创建 Task / Task ID；
- 超出 Scope；
- 将无关变更混入交付；
- 污染其他并发 Workspace；

则该交付可以直接标记：

```text
DELIVERY_REJECTED
```

常见分类：

```text
Unauthorized Coordination Change
Unauthorized Task Creation
Scope Violation
Workspace Contamination
Unrelated Change
```

处理原则：

```text
Reject delivery
-> 保留合法工作（如果可安全拆分）
-> 去除违规改动
-> Re-submit
```

如果无法安全拆分，则重新实施，而不是接受被污染的交付。

---

## 16. 项目成熟度

避免所有项目一开始就承担完整流程成本。

### Level 1 — RAPID

适合早期、小型、快速项目：

```text
README
AGENTS
coordination
Tasks
Tests
```

### Level 2 — STRUCTURED

增加：

```text
design/
architecture/
modules/
contracts/
decisions/
```

### Level 3 — CONTROLLED

增加：

```text
Frozen Baseline
Formal Review Gate
Baseline Change Protocol
Release Gate
```

Baseline / Decision 机制不要求所有项目从第一天启用。

---

## 17. 当前七条核心原则

### 1. Single Coordination Authority

一个项目同一时间只有一个有效 Orchestrator 拥有协调裁决权。

### 2. Authority != Physical Writer

Orchestrator 决定状态；文件写入可以由 Orchestrator 自己完成，也可以由受控 Executor 机械执行。

### 3. Orchestrator-Issued Task Identity

Task ID 只能由 Orchestrator 分配，Executor 不生成、不预测、不自行派生正式 Task。

### 4. Coordination Revision + Epoch

通过 Revision 防止基于过期状态继续调度，通过 Epoch 降低双 Orchestrator 并发裁决风险。

### 5. Isolated Concurrent Execution

并发 Task 必须隔离 mutable workspace。

### 6. Independent Review Enforcement

关键交付必须经过真正独立的 Review；WAIVED 不等于独立审查已完成。

### 7. Executor Reports Facts, Orchestrator Accepts State

Executor 返回执行事实、测试结果和 Findings；项目级 ACCEPTED / COMPLETED / FROZEN 等状态由 Orchestrator 决定。

---

## 18. 后续演化方向

本文件当前只定义协同框架，不直接充当最终通用模板。

后续可基于本设计生成一套跨项目复用资产：

```text
README.md
AGENTS.md
CLAUDE.md
CODEX.md
DEEPSEEK.md

coordination/README.md
coordination/STATUS.md
coordination/WORKFLOW.md
coordination/TASK_PROTOCOL.md
coordination/REVIEW_PROTOCOL.md
coordination/OUTPUT_FORMAT.md

skills/*/SKILL.md
Task Template
Review Template
Checkpoint Template
Result Template
```

并进一步验证：

- Web GPT 是否拥有直接 Repository 写权限时，两种执行模式如何统一；
- Coordination Revision / Epoch 的最小实现；
- 多 Workspace Integration / Merge 策略；
- Task dependency 状态机；
- 不同模型能力差异下的调度策略；
- 审计轨迹与流程豁免记录；
- 如何将该体系抽象成可自动初始化的新项目模板。

---

## 19. 当前定位

本设计为：

```text
通用多 Agent 开发协同框架
Design Candidate v0.1
```

它不是 Nyron 产品架构冻结基线，也不自动改变 Nyron 当前 Development Gate。

其主要价值是保存当前已经形成的多 Agent 开发协同设计，以便未来继续演化为通用项目协同 Markdown / Skill / Template 体系。