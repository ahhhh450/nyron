# Baselines

保存经过正式 Review 后冻结的稳定设计基线。

Baseline 适用于需要稳定接口、架构或发布控制的项目阶段。

规则：
- 未冻结设计不要放这里伪装成稳定基线；
- Baseline 修改必须经过显式变更任务和独立 Review；
- Executor 不得在普通实现 Task 中自行改写 Baseline。
