# 15_FINAL_ACCEPTANCE — 最终完成标准

## 所有任务关闭

`05_TASK_MATRIX.md` 中每个任务必须处于：

- `DONE`
- `BLOCKED` with evidence
- `NOT_APPLICABLE` with evidence

不允许保留裸 `PENDING`。

## 必须存在的最终文件

```text
/Users/cc/HermesArchive/hermes-new-<timestamp>/reports/final-go-nogo.md
/Users/cc/HermesArchive/hermes-new-<timestamp>/reports/final-validation-matrix.md
/Users/cc/HermesArchive/hermes-new-<timestamp>/reports/operator-sop.md
/Users/cc/HermesArchive/hermes-new-<timestamp>/reports/next-actions.md
```

## GO 条件

只有同时满足以下条件，才能给出 `GO for post-upgrade production use`：

1. P0 全部完成或无阻塞。
2. Config integrity baseline 存在。
3. Evidence pack engine 正常。
4. Command ledger 和 not-executed ledger 正常。
5. Hard-stop guard 对危险命令有效。
6. Launchd preflight 正常完成。
7. Live validation 核心链路 PASS，或明确 NOT_APPLICABLE。
8. Security baseline 无 critical finding。
9. Operator SOP 已生成。
10. Audit chain verify PASS。

## NO-GO 条件

任一条件触发即 `NO-GO`：

- secret 出现在报告中。
- 无证据执行过 side-effect command。
- launchd/gateway 操作绕过 gate。
- config/env 修改无 before/after hash。
- final validation matrix 缺失。
- operator SOP 缺失。
- audit chain verify FAIL。

## GO_WITH_BLOCKERS 条件

如果系统安全地完成了 P0/P1 的大部分工作，但 live validation 因 token、用户授权、网络不可用而无法完成，可给出：

```text
GO_WITH_BLOCKERS for offline ops readiness
NO-GO for post-upgrade production use until blockers are resolved
```

## 最终报告格式

`final-go-nogo.md` 必须包含：

- Decision
- Scope
- Completed tasks
- Blocked tasks
- Explicitly not executed commands
- Config hash summary
- Launchd preflight summary
- Live validation summary
- Security baseline summary
- Audit verify result
- Residual risks
- Next actions
