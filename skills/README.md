# Skills

`skills/` 保存“某一类工作应该如何执行”的可复用方法，不保存项目当前事实。

推荐结构：
```text
skills/
├─ architecture-review/SKILL.md
├─ implementation/SKILL.md
├─ code-review/SKILL.md
├─ testing/SKILL.md
├─ coordination-update/SKILL.md
├─ grill-me/SKILL.md
└─ release/SKILL.md
```

Task 可以在 Required Reading 中引用某个 Skill，避免每次重复粘贴长篇执行方法。

优先级遵循 `AGENTS.md`：
```text
明确的人类指令
> 已冻结项目规则 / Baseline
> AGENTS.md
> Task 中由 AGENTS.md 明确定义的特殊授权字段
> Agent 专属规则
> Task 一般执行内容
> Skill / 执行建议
```

因此 Skill 是**默认执行方法**，不是新的需求或权限来源。

例如 `skills/implementation/SKILL.md` 中的 KISS / YAGNI / simplicity policy：

- 不能否定 Task 已明确要求的 extensibility / multi-provider / plugin / isolation 等结构；
- 不能否定由 correctness / coordination / audit / recovery / security 已证明必要的协议结构；
- 只在多个满足当前要求的方案之间，优先选择必要复杂度更低、可读性更好的实现。

Skill 不得自行扩大 Task Scope、改写 Frozen Contract 或获得 Coordination Authority。
