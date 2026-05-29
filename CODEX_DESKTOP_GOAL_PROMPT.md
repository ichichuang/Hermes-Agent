# CodexDesktop Goal Prompt

将下面整段复制到 CodexDesktop 的 composer 中执行。首选使用 `/goal`。

```text
/goal You are working in /Users/cc/.hermes on the Hermes Ops upgrade plan system.

Read AGENTS.md and every file under docs/ai-plan/ before making changes.

Treat docs/ai-plan/01_SPEC.md as the source of truth, docs/ai-plan/04_PRIORITY_PLAN.md as the priority order, docs/ai-plan/05_TASK_MATRIX.md as the execution queue, docs/ai-plan/06_VALIDATION.md as the validation contract, docs/ai-plan/07_STATUS.md as the live progress ledger, and docs/ai-plan/11_HARD_STOP_POLICY.md as non-negotiable safety policy.

Execute the plan continuously from P0 to P3. Do not pause after each task. Do not ask for confirmation for safe read-only inspection, file creation under /Users/cc/.hermes/ops, evidence-pack generation, tests, documentation, local dry-run validation, or updating STATUS/DECISIONS.

Never bypass safety gates. Never use --yolo, approval-bypass, or danger-full-access. Never print or persist secrets. Never directly run launchctl enable/bootstrap/bootout/kickstart/load/unload, hermes gateway install/start/stop/restart, or edit ~/.hermes/config.yaml or ~/.hermes/.env unless the implemented hermes-ops phase gate and side-effect guard explicitly allow the exact action and evidence has been recorded.

If a task is blocked by missing credentials, missing permissions, missing upstream evidence, network approval, missing local Hermes source, or a failed hard-stop condition, mark that task BLOCKED or NO-GO with evidence in docs/ai-plan/07_STATUS.md and the active evidence pack. Then continue all independent safe tasks that do not depend on the blocked action.

For each task:
1. Restate the task ID and intended deliverable briefly.
2. Implement the smallest safe change.
3. Create or update evidence under /Users/cc/HermesArchive/hermes-new-<timestamp>/.
4. Run the relevant validation from docs/ai-plan/06_VALIDATION.md.
5. Update docs/ai-plan/07_STATUS.md with status, files changed, validation result, evidence path, and next task.
6. Append architectural choices to docs/ai-plan/08_DECISIONS.md.

Stop only when every task in docs/ai-plan/05_TASK_MATRIX.md is DONE, BLOCKED with evidence, or NOT_APPLICABLE with evidence. At the end, produce final-go-nogo.md, final-validation-matrix.md, operator-sop.md, next-actions.md, and a concise final report.

Begin with P0.A0.
```

## 备用：如果 `/goal` 不可用

先运行：

```text
Read CODEX_DESKTOP_GOAL_PROMPT.md and execute the embedded plan as a normal multi-step task. If /goal is unavailable, continue task-by-task in the same thread and update docs/ai-plan/07_STATUS.md after every milestone so work can resume safely.
```
