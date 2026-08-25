# 通用多 Agent 开发协同框架

状态：`DRAFT / NOT FROZEN`

本目录用于设计一套可跨项目复用的 **Web GPT + Codex + Claude Code + DeepSeek 多 Agent 软件开发协同体系**。

它的目标不是规定某一个具体项目怎么开发，而是提供一套通用的项目入口、Agent 规则、任务协议、Review 机制、状态管理和协同模板，使 Web GPT 可以作为开发调度器，稳定指挥多个执行 Agent 工作。

---

## 1. 核心角色

### Web GPT — Development Orchestrator

负责项目级协调与裁决，包括：

- 创建和分配 Task；
- 分配 Task ID；
- 选择执行 Agent；
- 管理优先级和依赖；
- 安排 Review / Re-Review；
- 接受或拒绝交付；
- 管理项目状态、Gate、Baseline 和 Release。

核心原则：

> Executor 报告事实，Orchestrator 决定项目状态。

### Codex / Claude Code / DeepSeek — Execution Agents

按明确 Task 执行工作。

一般分工：

- **Codex**：实现、调试、测试、工程化工作、代码 Review；
- **Claude Code**：复杂设计、复杂实现、架构分析、独立 Review；
- **DeepSeek**：简单任务、低风险修改、机械性工作、文档一致性检查、定向验证、Review / Re-Review。

具体分工不是固定权限边界，最终由 Orchestrator 根据任务风险和能力选择。

---

## 2. 核心协同原则

当前框架遵循以下原则：

1. **Single Coordination Authority**  
   一个项目同一时间只有一个有效 Orchestrator 拥有协调裁决权。

2. **Authority != Physical Writer**  
   Orchestrator 决定状态；实际文件写入可以由受控 Agent 执行。

3. **Orchestrator-Issued Task Identity**  
   Task ID 只能由 Orchestrator 分配，Executor 不自行创建正式 Task。

4. **Coordination Revision + Epoch**  
   用于降低过期状态和多个 Orchestrator 并发调度造成的冲突。

5. **Isolated Concurrent Execution**  
   并发 Task 不共享同一个可变工作区，应使用独立 branch / worktree / sandbox 或等价机制。

6. **Independent Review Enforcement**  
   关键交付默认要求实现者与独立 Reviewer 不同。

7. **Executor Reports Facts, Orchestrator Accepts State**  
   Agent 的 `SUCCESS / PASS` 是执行报告，不自动等于项目级 `COMPLETED / ACCEPTED / FROZEN`。

---

## 3. 建议项目结构

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

---

## 4. 文件职责

### `README.md`

项目入口。

只负责告诉人和 Agent：

- 项目是什么；
- 项目目标是什么；
- 如何运行；
- 目录怎么组织；
- AI Agent 从哪里开始读取。

README 不承担复杂协同协议。

### `AGENTS.md`

所有 Agent 的公共强制规则。

定义：

- 权限边界；
- Scope 规则；
- Git / Workspace 公共约束；
- Task 执行原则；
- Review 独立性；
- 禁止行为。

### `CLAUDE.md` / `CODEX.md` / `DEEPSEEK.md`

保存各 Agent 特有规则和工具差异。

公共规则不应在这些文件中重复定义。

### `coordination/`

项目开发协同控制面。

用于保存：

- 当前项目状态；
- Task；
- Result；
- Checkpoint；
- Workflow；
- Review Protocol；
- 输出协议。

### `design/`

保存架构、模块、Contract、Decision、Baseline 等设计资产。

### `skills/`

保存“某一类工作应该如何执行”的可复用方法，例如：

- architecture-review；
- implementation；
- code-review；
- testing；
- release。

### `docs/`

保存开发、运行、维护和用户文档。

---

## 5. 基本工作流

```text
Web GPT
  ↓
Create / Assign Task
  ↓
Codex / Claude Code / DeepSeek
  ↓
Task Result
  ↓
Independent Review（按风险需要）
  ↓
Fix / Re-Review
  ↓
Orchestrator Accept / Reject
  ↓
Integration / Baseline / Release
```

并非所有任务都必须走完整流程。

简单、低风险、机械性任务可以简化；核心代码、Architecture、Contract、Security、Baseline 等修改应提高 Review 要求。

---

## 6. Task 基本原则

所有正式开发工作应基于明确 Task。

推荐 Task ID：

```text
T-YYYYMMDD-NNN
```

Task 至少应明确：

- Task ID；
- Type；
- Assigned Agent；
- Objective；
- Required Reading；
- Scope / Out of Scope；
- Dependencies；
- Validation；
- Deliverables；
- Output Format；
- Completion Criteria。

Agent 不应根据模糊口头描述自行扩展成新的正式任务。

---

## 7. 当前设计状态

本目录中的内容仍属于通用协同框架设计阶段。

详细设计候选见：

`../通用多Agent开发协同框架设计候选版_v0.1.md`

后续计划逐步形成：

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
```

这些文件在完成独立审查并正式冻结前，都应视为可迭代设计资产，而不是不可修改的固定规则。
