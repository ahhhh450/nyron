# Project Coordination Status

> 本文件是项目协调状态的唯一事实源，由 Active Orchestrator 裁决。Execution Agent 默认只读。

## Coordination

- Active Orchestrator: `UNASSIGNED`
- Coordination Epoch: `0`
- Coordination Revision: `0`
- Last Accepted Commit: `UNSET`
- Development Gate: `UNSET`
- Project Phase: `UNSET`

## Active Tasks

| Task | Type | Agent | State | Depends On |
|---|---|---|---|---|
| — | — | — | — | — |

## In Review

| Task | Reviews | Reviewer | State |
|---|---|---|---|
| — | — | — | — |

## Blocked

| Task | Reason | Blocked By |
|---|---|---|
| — | — | — |

## Pending Independent Review

- None.

## Open Findings

- None.

## Stable Baseline

- Architecture: `NONE`
- Contract: `NONE`
- Module: `NONE`
- Release: `NONE`

## Next Eligible Tasks

- None assigned.

## State Update Rule

任何关键协调变更都应：
1. 基于当前 `Coordination Revision`；
2. 由 Active Orchestrator 决定；
3. 更新后递增 Revision；
4. 新 Orchestrator 接管时递增 Epoch；
5. Executor 不得在普通实现 Task 中顺手修改本文件。
