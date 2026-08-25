# Nyron Development Design Notes

Status: **WORKING NOTES — NON-NORMATIVE**

本目录用于保存开发过程中有长期参考价值、但尚未进入 Frozen Design / Contract / Baseline 的设计思路、工程取舍、失败方案、经验总结与待验证假设。

目标不是复制 Task / Result，而是回答：

- 为什么选择这个方案；
- 还考虑过哪些方案；
- 哪些边界是刻意不做的；
- 哪些经验可以抽象成后续通用开发文档；
- 哪些想法未来可能晋升为正式 Design / Contract / Amendment。

## 1. Authority

本目录中的内容默认是：

`NON-NORMATIVE / WORKING REFERENCE`

它不能覆盖或修改：

- Frozen Design；
- Contract；
- Coordination STATUS；
- 已接受 Baseline；
- 正式 Task 的 scope / acceptance criteria。

如果 working note 与正式冻结文档冲突，以正式冻结文档为准。

## 2. 什么时候必须记录

遇到以下任一情况，应创建或更新设计工作笔记：

- 做出非显然的架构 / ownership / lifecycle / fencing / recovery / security 取舍；
- 明确拒绝一个看似方便但会破坏边界的方案；
- 为避免 over-engineering 主动推迟某个抽象；
- 发现可复用于其他项目的 Agent 调度、Review、测试、交付或上下文管理方法；
- 实现过程中出现“当前先这样做，未来满足条件后再升级”的重要边界；
- 某个 Finding 暴露出值得沉淀的通用设计规律；
- 用户明确提出新的开发方向、设计思路或后续希望整理成通用文档的内容。

纯机械修改、显然的 bugfix、已经完整写入 Frozen Design 的事实，不需要重复记录。

## 3. 推荐结构

每份笔记尽量包含：

```text
Title:
Date:
Related Task / Design:
Status: WORKING / VALIDATED / SUPERSEDED / PROMOTED

Problem / Context:

Decision / Current Direction:

Why:

Alternatives Considered:

Rejected / Deferred Ideas:

Risks / Open Questions:

Reusable Insight:

Promote To:
- future Design / Contract / Amendment / Development Guide / Generic Documentation / NONE
```

不要求为了格式而填满空项；重点是保存真正有价值的 reasoning artifact（推理产物）。

## 4. 命名

推荐：

```text
YYYY-MM-DD_<topic>.md
```

同一主题持续演进时优先更新同一份笔记，不要因为每个 Task 都重复创建几乎相同的文件。

## 5. 与 Task / Checkpoint / Result 的关系

- `coordination/tasks/`：开始时定义“要做什么、边界是什么”。
- `coordination/checkpoints/`：执行中记录“做到哪里、剩什么、下一步是什么”。
- `coordination/results/`：结束时记录“最终交付了什么、证据是什么”。
- `coordination/STATUS.md`：项目级当前事实快照。
- `docs/development/notes/`：保存“为什么这样设计/调度，以及哪些经验值得未来复用”。

不要用 design notes 代替 Task、Checkpoint、Result 或 STATUS。

## 6. 晋升规则

当某条 working note 被证明稳定且需要成为正式约束时，应通过正式 Task / Design Review 流程晋升到相应 Design、Contract、Amendment 或 Development Guide。

晋升后原 note 可保留 provenance（来源）并标记 `PROMOTED`，但正式文档成为规范事实源。
