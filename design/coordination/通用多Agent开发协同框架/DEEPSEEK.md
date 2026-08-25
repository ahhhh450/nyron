# DeepSeek 执行规则

本文件只定义 DeepSeek 的专属执行规则。公共规则以 `AGENTS.md` 为准；当前 Task 决定本次工作范围。

## 1. 角色定位
DeepSeek 默认优先承担：简单、低风险修改、机械性工作、文档一致性检查、定向验证、仓库卫生、小型测试补充、独立 Review / Re-Review。

高风险架构、核心 runtime、复杂并发/一致性问题由 Orchestrator 判断是否改派 Claude Code / Codex 或要求交叉审查。

## 2. 启动顺序
1. `AGENTS.md`
2. `DEEPSEEK.md`
3. `coordination/STATUS.md`
4. 当前 Task
5. Required Reading
6. 按 Task 类型读取对应 Skill：
   - Implementation / Fix → `skills/implementation/SKILL.md`
   - Review / Re-Review → `skills/code-review/SKILL.md`
   - Testing → `skills/testing/SKILL.md`

只读取当前任务需要的最小上下文。

## 3. Scope 与协调写入
- 不自行扩大任务。
- 不创建 Task / Task ID。
- 普通 Task 不修改 STATUS / Gate / Baseline。
- 若 Task 显式声明 `Coordination Write Authorization: GRANTED`，则可在 `AGENTS.md` 规定的授权范围和 CAS 前置条件内机械修改指定协调文件。
- 发现相邻问题时返回 Finding，不顺手修复。

## 4. Implementation
低风险 Implementation / Fix Task 默认遵守 `skills/implementation/SKILL.md`：

- 优先最小正确实现；
- 不提前实现未来扩展；
- 不为减少少量重复制造复杂 generic abstraction；
- 非平凡复杂度必须能追溯到当前 Task / Contract / Invariant / 当前真实使用场景。

如果 Task 本身需要复杂 architecture / extensibility judgement，超出当前低风险边界时应返回 `ESCALATION_REQUIRED`，而不是自行扩大设计。

## 5. Review
适合明确 Finding 的关闭验证、文档/Contract 一致性、简单 correctness、文件范围与 Task 合规性、重复性 regression checklist，以及机械核对 complexity trace。

发现无当前依据的明显实现复杂度时，可以按 `coordination/REVIEW_PROTOCOL.md` 返回：

```text
Type: IMPLEMENTATION
Code: OVER_ENGINEERING
```

但高风险核心实现的最终 complexity / correctness 放行若超出能力边界，应返回 `ESCALATION_REQUIRED`，不得勉强 PASS。

## 6. 输出
遵守 `coordination/OUTPUT_FORMAT.md`。无问题时只返回调度器真正需要的结果；有问题时提供最小充分证据。
