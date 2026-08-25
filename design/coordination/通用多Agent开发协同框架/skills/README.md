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
└─ release/SKILL.md
```

Task 可以在 Required Reading 中引用某个 Skill，避免每次重复粘贴长篇执行方法。

优先级：
```text
AGENTS.md / 当前 Task
> Agent 专属规则
> Skill
```

Skill 不得自行扩大 Task Scope 或获得 Coordination Authority。
