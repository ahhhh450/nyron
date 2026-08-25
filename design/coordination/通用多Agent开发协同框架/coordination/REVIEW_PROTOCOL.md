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

Severity：
```text
BLOCKING
NON_BLOCKING
```

## 5. Re-Review

Re-Review 应优先做 targeted verification，只验证原 Finding 是否关闭以及修复是否引入新问题，不默认重复完整审查。

## 6. Reviewer 选择

- Claude Code：复杂架构、复杂实现、Contract、高风险 Review。
- Codex：代码 correctness、工程实现、测试、CI、复杂代码 Review。
- DeepSeek：低风险 Review、定向 Re-Review、文档一致性、机械验证。

实际分配由 Orchestrator 根据风险裁决。
