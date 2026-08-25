# Checkpoints

本目录保存 Task 的过程性恢复点。

推荐命名：
```text
T-YYYYMMDD-NNN-CHECKPOINT.md
```

Type：
- `PROGRESS`：长任务阶段性进度；
- `HANDOFF`：Agent / session / context / quota 中断时交接。

权威顺序：
```text
Accepted Project State
> Final Result
> Latest Checkpoint
> Earlier Checkpoint
```

Checkpoint 不得替代最终 Result。
