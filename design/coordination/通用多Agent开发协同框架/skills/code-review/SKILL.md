# Skill: Code Review

用于实现交付的独立代码审查。

## 方法
1. 确认 Reviews Task、Original Agent、Reviewer independence。
2. 优先检查 diff，不默认重读整个仓库。
3. 检查 correctness、regression、error handling、boundary、state consistency、tests、scope contamination。
4. 对高风险代码额外关注 concurrency、replay、recovery、security。
5. 不在 Review Task 中顺手修复。

## 输出
使用统一 Finding 模型。没有阻塞问题时保持简洁；若需要更高能力审查，返回 `ESCALATION_REQUIRED`。
