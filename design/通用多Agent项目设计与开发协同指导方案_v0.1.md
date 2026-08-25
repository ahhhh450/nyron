# 通用多 Agent 项目设计与开发协同指导方案 v0.1

状态：`GUIDANCE BASELINE / PILOT ACTIVE / NOT FROZEN`

用途：作为后续通用软件项目、AI 项目、工具项目及复杂多模块项目进行方案设计、架构设计、开发组织和多 Agent 协同时的上位指导方案。

本文件不是某一个具体项目的 Architecture，也不替代具体项目的 Baseline。它定义的是“以后设计和开发项目时，默认应该怎么组织思考、文件、职责、任务、审查和演进”。

配套执行框架：

`coordination/通用多Agent开发协同框架/`

---

## 1. 总体目标

项目设计不应只产生代码，也不应只产生一份大而全的设计文档。

默认把项目拆成四种不同性质的事实：

1. **项目当前是什么**：README、STATUS、稳定版本、当前 Gate；
2. **为什么这样设计**：Architecture、Module、Contract、Decision、Baseline；
3. **现在谁做什么**：Task、Result、Checkpoint、Review；
4. **某类工作怎么做**：Skill、开发文档、测试与运维说明。

不同性质的信息必须尽量分层保存，避免聊天记录、设计事实、任务状态和执行方法互相污染。

---

## 2. 默认角色模型

### Development Orchestrator

默认由 Web GPT 承担项目级 Development Orchestrator。

负责：

- 恢复项目真实状态；
- 拆分任务；
- 分配 Task ID；
- 选择 Agent；
- 控制依赖、优先级、并发与 Gate；
- 安排 Review / Re-Review；
- 接受或拒绝交付；
- 决定 Integration、Baseline、Release；
- 管理跨会话 handoff。

### Execution Agents

默认 Agent 组合：

- **Claude Code**：复杂设计、复杂实现、架构、Contract、高风险 Review；
- **Codex**：实现、调试、测试、工程化、代码 Review、CI 与仓库问题；
- **DeepSeek**：简单、低风险、机械任务、文档一致性、定向验证、独立 Review / Re-Review。

具体分工由任务风险决定，不把模型名称当成绝对权限边界。

---

## 3. 七条通用协同原则

### 3.1 Single Coordination Authority

同一项目同一时刻只保留一个有效的协调裁决源。

### 3.2 Authority != Physical Writer

拥有决定权的人或 Agent，不一定必须亲自执行文件写入。

允许受控 Agent 机械落盘，但不得把物理写权限误当成项目裁决权。

### 3.3 Orchestrator-Issued Task Identity

正式 Task ID 由 Orchestrator 分配，Executor 不自行派生任务体系。

### 3.4 Revision + Epoch

关键协调状态需要版本与世代信息，用于 stale detection、handoff 和 fencing。

### 3.5 Isolated Concurrent Execution

并发任务必须隔离 mutable workspace，避免多 Agent 互相覆盖或混入改动。

### 3.6 Independent Review

高风险设计和实现默认由不同 Agent 独立审查；自审不能伪装成独立 Review。

### 3.7 Executor Reports Facts, Orchestrator Accepts State

Executor 的 SUCCESS / PASS 是事实报告，不自动产生项目级 ACCEPTED / COMPLETED / FROZEN / RELEASED。

---

## 4. 设计文件分层原则

### README

只做入口：项目是什么、目标、运行方式、目录和阅读入口。

### design/

保存“为什么这样设计”。建议按需启用：

```text
design/
├─ architecture/
├─ modules/
├─ contracts/
├─ decisions/
└─ baselines/
```

### docs/

保存“怎么开发、怎么部署、怎么使用”。

```text
docs/
├─ development/
├─ operations/
└─ user/
```

### coordination/

保存“当前开发过程如何被控制”。

```text
coordination/
├─ STATUS.md
├─ tasks/
├─ results/
├─ checkpoints/
└─ archive/
```

### skills/

保存“某类任务怎么做”的复用方法，不保存项目当前事实。

---

## 5. 方案设计默认顺序

复杂项目默认按以下顺序推进：

```text
问题与目标
→ 系统边界
→ Architecture
→ Module Ownership
→ Contract / Interface
→ Failure / Recovery / Security / Concurrency
→ Baseline
→ Implementation Task
→ Review
→ Integration
```

不要在核心边界尚未明确时过早大量实现，也不要为了追求完整而无限停留在纸面设计阶段。

当设计已经没有 Blocking Finding，应进入真实运行，用实际反馈推动下一轮设计。

---

## 6. Ownership 与边界

复杂系统设计优先回答：

- 谁拥有状态；
- 谁可以修改状态；
- 谁只提供机制；
- 谁负责裁决；
- 谁负责持久化；
- 跨模块如何通信；
- 失败后谁恢复；
- replay / retry 是否保持同一语义。

默认避免：

- 多模块共同拥有同一状态；
- Provider 因为保存数据就获得业务所有权；
- Scheduler / Router 因为负责传递就获得语义裁决权；
- Physical Writer 因为能写文件就获得状态决定权。

---

## 7. Task 设计原则

每个正式 Task 应尽量做到：

- 单一目标；
- 明确 Scope / Out of Scope；
- 最小 Required Reading；
- 明确依赖；
- 明确风险；
- 明确验证方式；
- 明确交付格式；
- 明确 Git / workspace 权限。

发现相邻问题时优先返回 Finding，由 Orchestrator 决定是否创建新 Task，而不是让 Executor 无限扩展工作范围。

---

## 8. Review 原则

Review 的目标不是证明作者做得对，而是主动寻找作者可能遗漏的问题。

高风险 Review 应重点关注：

- correctness；
- ownership；
- contract；
- concurrency；
- fencing；
- retry / replay；
- failure / recovery；
- security；
- backward compatibility；
- state transition；
- hidden authority transfer。

Re-Review 默认 targeted，只验证原 Finding 是否关闭及修复是否引入新问题。

---

## 9. WAIVED 与 Review Debt

如果现实条件下暂时无法完成独立 Review，可以明确 WAIVED，但必须形成 `Review Debt`。

Review Debt 必须：

- 显式记录；
- 绑定交付物或 Task；
- 说明所欠 Review 类型；
- 在后续真正独立 Review 后才能清除。

关键 Architecture、Contract、Security、Core Runtime、Concurrency、Replay、Baseline、Release-critical 交付存在未清 Review Debt 时，不得进入稳定 Baseline / Release。

---

## 10. 协调状态写入

当 Orchestrator 无法直接写 Repository 时：

```text
Orchestrator 作出确定裁决
→ 发出 Coordination Update Task
→ 明确 Coordination Write Authorization
→ 指定 Authorized Files / Exact Approved Changes
→ 使用 Expected Epoch / Expected Revision 做 CAS
→ Agent 机械落盘
→ 返回 diff / commit
→ Orchestrator 验收新 Revision
```

CAS 不匹配时 fail closed，不允许 last-writer-wins。

---

## 11. 上下文与长期维护

Repository 才是项目长期事实载体，聊天上下文只用于当前推理与调度。

默认原则：

- 新 Agent 读取最小必要上下文；
- 不默认扫描全部历史 Task / logs / archive；
- context 或 quota 中断时写 HANDOFF checkpoint；
- 新 Orchestrator 会话从 README / AGENTS / ORCHESTRATOR / STATUS 恢复；
- 不依赖模型“记得以前聊过什么”维持项目正确性。

---

## 12. 项目成熟度

### RAPID

适合小型、早期、快速验证项目。

保留：README、AGENTS、ORCHESTRATOR、Agent 专属规则、coordination、tests。

### STRUCTURED

增加：Architecture、Modules、Contracts、Decisions。

### CONTROLLED

增加：Frozen Baseline、Formal Review Gate、Baseline Change Protocol、Release Gate。

流程复杂度应随项目风险增长，而不是从第一天就把所有项目做成重型治理系统。

---

## 13. 实际运行优先原则

当框架或设计已经满足：

- Blocking Finding = 0；
- 核心 Authority / Ownership / Contract 无已知矛盾；
- 能够恢复状态；
- 能够独立 Review；
- 能够检测 stale / concurrency 冲突；

则默认进入真实项目试运行。

不要因为追求理论上的“完美流程”无限推迟使用。

实际摩擦、错误、遗漏和失败模式应成为下一轮设计修订的主要证据。

---

## 14. 当前采用状态

自 2026-08-25 起，本指导方案与配套 `通用多Agent开发协同框架` 进入真实项目试运行。

当前结论：

```text
Framework Review: PASS
Blocking Findings: 0
Operational State: PILOT ACTIVE
Freeze State: NOT FROZEN
```

后续通用方案设计默认参考本文件；具体项目可以裁剪，但不得在没有明确理由的情况下破坏 Authority、Ownership、Task Identity、Workspace Isolation、Validation Honesty、Independent Review 和 State Acceptance 等核心原则。
