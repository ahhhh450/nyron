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

## Review Debt

| Delivery / Task | Review Type | Reason | Risk | Clearance Condition |
|---|---|---|---|---|
| — | — | — | — | — |

`WAIVED` Review 不自动关闭本表记录。只有满足 Clearance Condition 的独立 Review / Re-Review 被 Orchestrator 接受后才可移除。

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
5. Executor 不得在普通实现 Task 中顺手修改本文件；
6. `WAIVED` Review 形成的 Review Debt 必须显式保留到清偿完成。
