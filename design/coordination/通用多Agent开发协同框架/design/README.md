# Design

本目录保存“为什么这样设计”的项目设计资产，不保存日常任务状态。

推荐结构：
```text
design/
├─ architecture/
├─ modules/
├─ contracts/
├─ decisions/
└─ baselines/
```

- `architecture/`：整体架构、边界、数据流、运行模型。
- `modules/`：模块级设计与职责。
- `contracts/`：模块间 / 外部 Contract。
- `decisions/`：重要设计裁决（ADR / Decision）。
- `baselines/`：经过正式审查后冻结的稳定设计基线。

快速项目可以只使用部分目录；Baseline / Decision 不要求从第一天启用。
