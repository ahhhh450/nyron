# 通用多 Agent 开发协同框架

状态：`PILOT ACTIVE / REVIEW PASS / NOT FROZEN`

本目录是一套可直接复制到新项目中使用的 **Web GPT + Codex + Claude Code + DeepSeek 多 Agent 软件开发协同模板**。

当前已完成独立框架审查，Blocking Finding 为 0。自 2026-08-25 起进入真实项目试运行阶段；后续只根据实际运行中发现的问题迭代，不再因为纯纸面完善而阻塞使用。

目标：让 Web GPT 作为 Development Orchestrator（开发调度器），通过 Repository 中结构化 Markdown 指挥多个执行 Agent，并让项目在换会话、并发开发、Review、额度中断和长期迭代后仍可恢复和审计。

---

## 1. 实际使用方式

新项目建立后，把本目录中的协同文件复制到项目根目录，并根据项目实际技术栈调整 README、Agent 专属规则和 design/docs 内容。

推荐项目根结构：

```text
project/
│
├─ README.md
├─ AGENTS.md
├─ ORCHESTRATOR.md
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
│  │
│  ├─ templates/
│  │  ├─ TASK_TEMPLATE.md
│  │  ├─ RESULT_TEMPLATE.md
│  │  ├─ CHECKPOINT_TEMPLATE.md
│  │  ├─ ORCHESTRATOR_HANDOFF_TEMPLATE.md
│  │  └─ COORDINATION_UPDATE_TEMPLATE.md
│  │
│  ├─ tasks/
│  │  └─ README.md
│  ├─ results/
│  │  └─ README.md
│  ├─ checkpoints/
│  │  └─ README.md
│  └─ archive/
│     └─ README.md
│
├─ skills/
│  ├─ README.md
│  ├─ architecture-review/SKILL.md
│  ├─ implementation/SKILL.md
│  ├─ code-review/SKILL.md
│  ├─ testing/SKILL.md
│  ├─ coordination-update/SKILL.md
│  └─ release/SKILL.md
│
├─ design/
│  ├─ README.md
│  ├─ architecture/
│  ├─ modules/
│  ├─ contracts/
│  ├─ decisions/
│  └─ baselines/
│
├─ docs/
│  ├─ README.md
│  ├─ development/
│  ├─ operations/
│  └─ user/
│
├─ src/                 # 项目实际源码，名称可按技术栈调整
├─ tests/               # 项目实际测试，名称可按技术栈调整
└─ ...                  # package/config/build/deploy 等项目文件
```

`src/`、`tests/` 并非强制名称；协同框架只要求 Task 明确真实源码与测试范围。

---

## 2. 角色

### Web GPT — Development Orchestrator

Web GPT 是 Coordination Authority，负责：
- 恢复项目真实状态；
- 创建 Task 与分配 Task ID；
- 选择 Agent；
- 管理优先级、依赖、并发与 Gate；
- 安排 Review / Re-Review；
- 接受或拒绝交付；
- 决定 Integration / Baseline / Release；
- 管理 Orchestrator handoff。

读取 `ORCHESTRATOR.md`。

### Codex

默认适合实现、调试、测试、工程化、代码 Review、CI / 仓库排查。

读取 `CODEX.md`。

### Claude Code

默认适合复杂设计、复杂实现、架构/Contract 分析、复杂 Review。

读取 `CLAUDE.md`。

### DeepSeek

默认优先承担简单、低风险、机械性任务、文档一致性、定向验证、Review / Re-Review。

读取 `DEEPSEEK.md`。

具体 Agent 分配由 Orchestrator 根据任务风险决定，不把以上分工当成绝对能力边界。

---

## 3. 核心原则

1. **Single Coordination Authority**  
   一个项目同一时间只有一个有效 Orchestrator。

2. **Authority != Physical Writer**  
   Web GPT 做协调裁决；实际 Repository 写入可以由受控 Agent 机械执行。

3. **Orchestrator-Issued Task Identity**  
   正式 Task ID 只能由 Orchestrator 分配。

4. **Coordination Revision + Epoch**  
   Revision 防止基于过期状态继续调度；Epoch 用于 Orchestrator handoff / fencing。

5. **Isolated Concurrent Execution**  
   并发 Task 不共享 mutable working tree。

6. **Independent Review Enforcement**  
   关键交付默认实现者与独立 Reviewer 不同。

7. **Executor Reports Facts, Orchestrator Accepts State**  
   Agent 的 SUCCESS / PASS 不自动等于 ACCEPTED / COMPLETED / FROZEN / RELEASED。

---

## 4. 文件职责

### `AGENTS.md`
所有 Execution Agent 的公共强制规则：权限、Scope、Git、workspace、validation、Review independence、违规处理、fail closed。

### `ORCHESTRATOR.md`
Web GPT 调度规则：状态恢复、Task ID、Agent 分配、验收、Review、并发、协调写入、handoff。

### `CLAUDE.md` / `CODEX.md` / `DEEPSEEK.md`
只保存各 Agent 特有的能力和执行差异，不重新定义公共权限。

### `coordination/`
项目协同控制面。
- `STATUS.md`：当前协调状态唯一事实源；
- `tasks/`：正式任务；
- `results/`：最终结果；
- `checkpoints/`：进度/交接恢复点；
- `archive/`：退出活跃控制面的历史记录；
- `templates/`：可复制模板，不与真实记录混放。

### `skills/`
保存“某类任务怎么做”的可复用方法，不保存项目当前事实。

### `design/`
保存“为什么这样设计”：Architecture、Module、Contract、Decision、Baseline。

### `docs/`
保存“怎么开发、怎么运行、怎么使用”：development、operations、user。

---

## 5. 推荐读取顺序

### 新 Web GPT 调度窗口

```text
README.md
→ AGENTS.md
→ ORCHESTRATOR.md
→ coordination/STATUS.md
→ Active / Review / Blocked Tasks
→ 必要 Result / Checkpoint / design 文件
```

### Codex

```text
AGENTS.md
→ CODEX.md
→ coordination/STATUS.md
→ 当前 Task
→ Task.Required Reading
```

### Claude Code

```text
AGENTS.md
→ CLAUDE.md
→ coordination/STATUS.md
→ 当前 Task
→ Task.Required Reading
```

### DeepSeek

```text
AGENTS.md
→ DEEPSEEK.md
→ coordination/STATUS.md
→ 当前 Task
→ Task.Required Reading
```

默认不扫描全部历史 Task / archive。

---

## 6. 基本工作流

```text
Web GPT reads STATUS
→ Create Task
→ Assign Agent + isolated workspace
→ Execution
→ Task Result
→ Independent Review（按风险）
→ Fix
→ Targeted Re-Review
→ Orchestrator Accept / Reject
→ Coordination Update
→ Integration / Baseline / Release
```

低风险机械任务可以简化；Architecture、Contract、Security、Core Runtime、Concurrency、Replay、Baseline、Release-critical 等高风险工作提高 Review 要求。

---

## 7. Task / Result / Checkpoint

推荐 Task ID：
```text
T-YYYYMMDD-NNN
```

项目需要命名空间时：
```text
PROJECT-T-YYYYMMDD-NNN
```

Task 由 Orchestrator 创建；Executor 不自行生成。

权威优先级：
```text
Accepted Project State
> Final Result
> Latest Checkpoint
> Earlier Checkpoint
```

Checkpoint 使用一个模板，通过 `PROGRESS | HANDOFF` 区分阶段记录与正式交接。

---

## 8. Coordination 实际写入

如果 Web GPT 能直接写 Repository，可直接落协调变更。

如果不能：
```text
Web GPT 作出裁决
→ 创建独立 Coordination Update Task
→ Agent 按 exact approved changes 机械落盘
→ 返回 diff / commit
→ Web GPT 验收新 Revision
```

普通实现 Agent 不得在代码 commit 中顺手修改 `STATUS.md`。

---

## 9. 项目复杂度

### RAPID
只启用 README、AGENTS、ORCHESTRATOR、Agent 专属文件、coordination、tests。

### STRUCTURED
增加 design/architecture、modules、contracts、decisions。

### CONTROLLED
增加 Frozen Baseline、Formal Review Gate、Baseline Change Protocol、Release Gate。

不要求小项目从第一天启用所有机制。

---

## 10. 当前状态

本目录已通过独立框架审查并进入：

`PILOT ACTIVE / REVIEW PASS / NOT FROZEN`

Blocking Findings：`0`

当前策略：

```text
停止纯纸面扩展
→ 直接用于真实项目
→ 记录实际摩擦与失败模式
→ 仅针对真实问题修正
→ 累积足够运行证据后再决定是否冻结为正式通用 Baseline
```

详细设计来源：

`../通用多Agent开发协同框架设计候选版_v0.1.md`

上位通用指导：

`../../通用多Agent项目设计与开发协同指导方案_v0.1.md`
