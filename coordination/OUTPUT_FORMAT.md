# Output Format

所有 Agent 默认只返回 Orchestrator 执行下一步所需的信息，不返回冗长自检过程。

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

- `Commit` 可以记录本地 Task-scoped commit；
- `Remote Branch` 必须指向 Reviewer / Orchestrator 可从远端读取的正式交付分支或 ref；
- `Remote Commit` 表示**被交付、被审查的内容提交**，不要求 Result 文件自引用“包含它自身的最终记录 commit”；
- 如果 Result / Checkpoint 在 delivery commit 之后通过后续 record commit 落盘，允许 branch tip 晚于 `Remote Commit`；Reviewer 应同时核对 `Remote Commit` 的交付内容以及当前 branch tip 是否包含声明的 Result / Checkpoint；
- 不得为了让 Result 记录自身 SHA 而制造无限自引用更新；
- 仅存在本地、尚未 push 的 commit 不得作为正式 submitted delivery 报告 `SUCCESS`；
- `READ_ONLY` / `LOCAL_ONLY` / 明确不要求远端提交的 Task 可填写 `NOT_APPLICABLE`。

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

## 4. Checkpoint

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

## 5. Authority

输出中的 `SUCCESS / PASS` 是 Agent 报告，不自动改变 `STATUS.md` 中的项目级状态。只有 Active Orchestrator 能裁决 ACCEPTED / COMPLETED / FROZEN / RELEASED。
