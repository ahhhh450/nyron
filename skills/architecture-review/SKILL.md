# Skill: Architecture Review

用于架构、模块边界、Contract、Baseline 等设计审查。

## 方法
1. 读取 Task 指定的最小基线。
2. 区分现有已知 Finding 与“除此之外的新缺陷”。
3. 检查 ownership、authority、boundary、state transition、concurrency、replay、recovery、security、compatibility。
4. 不因措辞问题阻塞，优先找结构性 correctness 风险。
5. Review 默认只读。

## 输出
按 `coordination/REVIEW_PROTOCOL.md` 返回 PASS / PASS_WITH_FINDINGS / FAIL / ESCALATION_REQUIRED。
