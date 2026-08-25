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

Findings:
- NONE | <finding summary>

Blockers:
- NONE | ...
```

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
