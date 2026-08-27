# Output Format

所有 Agent 默认只返回 Orchestrator 执行下一步所需的信息，不返回冗长自检过程。

Repository 文件是正式开发调度事实源。聊天只用于触发、通知和简短状态，不得替代 Task / Result / Review / Checkpoint 文件。

Development Director、Track Orchestrator、Execution Agent 均必须遵守：

- `coordination/TASK_PROTOCOL.md`
- `coordination/OUTPUT_FORMAT.md`
- `coordination/REVIEW_PROTOCOL.md`

## 1. Task Result

```text
[TASK RESULT]

Task ID:
Execution Result: SUCCESS | PARTIAL | BLOCKED | FAILED

Files Changed:
- ...

Validation:
- ...

Commit:
- ...

Remote Branch:
- <branch/ref | NOT_APPLICABLE>

Remote Commit:
- <remote-readable delivery commit SHA | NOT_APPLICABLE>

Findings:
- NONE | <finding summary>

Blockers:
- NONE | ...
```

对于要求 Repository 写入并远端提交的 Task：

- `Commit == Remote Commit == final remotely reviewable delivery-content commit`（强制语义）；
- `Commit` MUST NOT 记录 local-only、pre-amend、pre-rebase、pre-recreate、已被 supersede 或 transient 的 SHA；
- 写入 `Commit` 或 `Remote Commit` 前，必须执行 `git cat-file -t <sha>` 并确认返回 `commit`；
- `Remote Commit` 还必须确认可从 canonical remote / 声明的 remote branch history 读取；
- final delivery-content commit 确定并 push 后，`Commit` 与 `Remote Commit` 记录同一个最终内容提交 SHA；后续用于落盘 Result / Checkpoint 的 record commit 可以让 branch tip 晚于该内容提交，但不得改变该语义；
- 若正式提交前发生 amend / rebase / recreate，只有重新验证后的最终 delivery-content commit 才能出现在任一字段中；
- `Remote Branch` 必须指向 Reviewer / Orchestrator 可从远端读取的正式交付分支或 ref；
- `Remote Commit` 表示**被交付、被审查的内容提交**，不要求 Result 文件自引用“包含它自身的最终记录 commit”；禁止引入“`Remote Commit` 必须等于最终 branch tip”的自引用要求；
- 不得为了让 Result 记录自身 SHA 而制造无限自引用更新；
- 仅存在本地、尚未 push 的 commit 不得作为正式 submitted delivery 报告 `SUCCESS`；
- `LOCAL_ONLY` Task 在显式授权时可记录本地 `Commit`，`Remote Commit` 填 `NOT_APPLICABLE`；`READ_ONLY` / 明确不要求远端提交的 Task 按实际填 `NOT_APPLICABLE`。

Repository 写入 Task 的 Final Result 还必须新增强制 `SHA Verification Evidence` 部分：

```text
SHA Verification Evidence:
- Commit Object: git cat-file -t <final-content-sha> => commit
- Remote Reachability: <final-content-sha> is present in canonical remote branch history => PASS
```

规则：

- 证据中的 SHA 必须与 `Commit` / `Remote Commit` 完全一致（remote-delivery Task）；
- 验证必须发生在 final content commit 形成之后、以及任何会改变其 SHA 的 amend / rebase / recreate 之后；
- 只有 `SHA verified` / `both SHAs verified` 之类的泛化声明、未附 exact SHA + observed result 的，不满足本协议；
- 无法产出真实证据时 fail closed，不得写入该 SHA 或报告正式 `SUCCESS`。

## 2. Review Result

```text
[REVIEW RESULT]

Task ID:
Reviews Task:
Result: PASS | PASS_WITH_FINDINGS | FAIL | ESCALATION_REQUIRED

Findings:
- NONE
```

如有 Finding：
```text
Finding ID:
Type:
Code: <optional standardized code, e.g. OVER_ENGINEERING>
Severity:
Location:
Evidence:
Impact:
Required Resolution:
```

`Code` 为可选字段。只有存在框架定义的标准化问题代码时填写；不要为了形式给每个 Finding 发明新的 Code。

Reviewer 默认只审查，不得顺手修改 Production，除非 Task 明确授权 Review + Fix。

高风险 Production 必须满足：

```text
Implementation Agent != Independent Reviewer
```

## 3. Re-Review Result

```text
[RE-REVIEW RESULT]

Task ID:
Reviews Task:
Result: PASS | FAIL | ESCALATION_REQUIRED

Closed Findings:
Open Findings:
New Findings:
```

Targeted Re-Review 默认只验证原 Finding 是否关闭及修复是否引入新问题，不因 Finding 数量少而重复完整 Review，除非 Task 明确要求。

## 4. Checkpoint

Checkpoint 必须写入：

```text
coordination/checkpoints/<TaskID>-<CheckpointID>.md
```

并创建新文件，不覆盖旧 Checkpoint。

```text
[CHECKPOINT]

Task ID:
Type: PROGRESS | HANDOFF
Current Step:
Completed:
Remaining:
Files Touched:
Validation:
Findings:
Blockers:
Next Action:
```

以下情况必须形成 `HANDOFF`：Agent/session 交接、workspace 交接、quota/tool 中断、任务暂停、Blocking Failure 导致当前执行停止。

以下情况应形成 `PROGRESS`：完成 milestone 但尚未结束；自上次 checkpoint 新触及 5 个不同文件；自上次 checkpoint 新产生 3 个 Task-scoped commits。短任务在达到阈值前直接结束时，Final Result 即可。

## 5. Track Orchestrator Repository Handoff

Track Orchestrator 不得依赖聊天复制子 Task 结果给 Development Director。

正式链路必须先存在 Repository 文件：

```text
Task
→ Result
→ Review / Re-Review Result
→ Checkpoint / Stable Candidate evidence
```

然后 Track Orchestrator 只向 Development Director 汇报：

```text
Track:
Current Gate:
Stable Candidate SHA:
Review State:
Open Findings:
Blockers:
Next Milestone:
```

Development Director 应自行从 Repository 读取原始 Result / Review / Checkpoint。Operator 不承担人工转发 Result 的职责。

## 6. Chat Output

Agent 完成正式 Task 且要求的 Repository Result / Review / Checkpoint 已正确落盘后，聊天默认只返回：

```text
TASK DONE
```

如果任务被阻塞并已形成相应 Result / HANDOFF Checkpoint：

```text
TASK BLOCKED
```

详细证据留在 Repository，不在聊天中复制正式 Result。

## 7. Authority

输出中的 `SUCCESS / PASS` 是 Agent 报告，不自动改变 `coordination/STATUS.md` 中的项目级状态。

只有拥有对应全局协调权限的 Development Director / Active Orchestrator 能裁决：

- `ACCEPTED`
- `COMPLETED`
- Gate `PASS / CLOSED`
- `Last Accepted Production`

Frozen Architecture 仍只能由 Lead Design Authority 裁决。
