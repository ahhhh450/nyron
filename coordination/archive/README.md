# Archive

本目录保存已经退出活跃协同面的历史 Task、Result、Checkpoint 或旧协议快照。

Archive 的目标是减少 Orchestrator 和 Execution Agent 的默认读取集合，而不是删除历史。

## 1. 可归档条件

Task 只有同时满足以下条件时才可归档：

1. 已进入终态：`ACCEPTED | REJECTED | CANCELLED`；
2. 不再处于 Review / Re-Review / Fix / Integration；
3. 没有 Active / Blocked Task 仍依赖其原始文件路径；
4. 没有未清 Review Debt 或 Blocking Finding 要求继续保持活跃；
5. 归档不会破坏当前 Baseline / Release 所需审计引用。

## 2. 推荐结构

```text
archive/<TaskID>/
├─ TASK.md
├─ RESULT.md
└─ checkpoints/
   ├─ <TaskID>-CP-001.md
   └─ ...
```

不存在的 Result / Checkpoint 可以省略。

## 3. Archive Sweep

由 Orchestrator 在以下任一条件满足时执行 archive sweep：

- Project Phase 切换；
- Baseline 冻结；
- Release 完成；
- 活跃目录中存在 10 个及以上已终态且满足归档条件的 Task；
- Orchestrator handoff 前，活跃协同面包含大量与下一阶段无关的终态记录。

归档属于协调状态维护。若由 Execution Agent 物理执行，必须使用明确的 Coordination Update 授权并遵守 CAS。

## 4. 读取规则

- Archive 默认不是 Agent 的 Required Reading；
- 不因历史文件存在就扫描全部 archive；
- 只有当前 Task 明确要求历史追溯、回归调查或依赖旧决策时才读取；
- 新 Orchestrator handoff 默认不重新加载已安全归档 Task 的完整内容。

## 5. 不变量

- 归档不能改变已接受结果的语义；
- 归档不能抹掉 Findings、Review、Checkpoint 或 Result 的历史证据；
- 归档前若仍存在基于原始路径的有效引用，应先保持原位或由 Orchestrator明确处理引用，禁止直接搬迁导致断链。
