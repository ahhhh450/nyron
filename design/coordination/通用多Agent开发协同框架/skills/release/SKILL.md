# Skill: Release

用于进入稳定版本、Baseline 或 Release 前的最终检查。

## 前置检查
- 所有 required dependency 已 ACCEPTED；
- 高风险改动已完成独立 Review；
- Blocker 已关闭；
- 必要测试通过；
- Release candidate 与预期 commit 一致；
- 没有未授权 coordination / workspace 污染。

## 执行边界
Release Agent 可以验证和执行 Task 明确授权的发布动作，但不能自行决定“应该发布”。Release / Baseline 成立与否由 Orchestrator 裁决。

## 输出
返回验证事实、commit / tag / artifact（如有）、残余 Finding 与 Blocker。
