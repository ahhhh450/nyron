# Skill: Implementation

用于明确 Task 范围内的代码或配置实现。

## 方法
1. 确认 Scope / Out of Scope / Constraints。
2. 确认隔离 workspace 和当前 git 状态。
3. 采用最小必要改动，不顺手重构无关区域。
4. 执行 Task 指定验证；未指定时执行与改动直接相关的最小测试。
5. 发现架构/Contract 问题时返回 Finding，不越权改设计基线。
6. Commit 保持 Task-scoped。

## 完成条件
实现、验证、Result 三者都完成后才可报告 SUCCESS；是否 ACCEPTED 由 Orchestrator 决定。
