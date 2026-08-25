# Skill: Code Review

用于实现交付的独立代码审查。

## 方法
1. 确认 Reviews Task、Original Agent、Reviewer independence。
2. 优先检查 diff，不默认重读整个仓库。
3. 检查 correctness、regression、error handling、boundary、state consistency、tests、scope contamination。
4. 对高风险代码额外关注 concurrency、replay、recovery、security。
5. 对 Implementation / Refactor / Fix 交付，执行 complexity review：
   - 新抽象/层级是否能追溯到 Task Scope / Constraints / Frozen Contract / 当前真实场景；
   - 删除该复杂度后是否仍能满足全部当前 requirement；
   - 是否为了未来可能性提前建立 framework / registry / plugin / multi-backend abstraction；
   - DRY 抽象是否满足“同一语义概念 + 同一 reason to change”，而不是只因代码表面相似。
6. 若复杂度无法建立当前 requirement trace，按 `coordination/REVIEW_PROTOCOL.md` 返回：

```text
Type: IMPLEMENTATION
Code: OVER_ENGINEERING
```

7. 不在 Review Task 中顺手修复。

## 判断原则

Code Review 不以“代码越少越好”为目标，而是在 correctness / security / maintainability / frozen semantics 均满足的前提下，检查是否存在没有当前需求依据的 speculative complexity。

已由当前 coordination、audit、recovery、security、crash/replay correctness 明确要求的结构，不得仅以 YAGNI 为理由删除。

## 输出
使用统一 Finding 模型。没有阻塞问题时保持简洁；若需要更高能力审查，返回 `ESCALATION_REQUIRED`。
