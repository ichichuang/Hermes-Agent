# AGENTS.md — Hermes 升级执行规则

本文件是 CodexDesktop / Codex CLI 在 `/Users/cc/.hermes` 中工作的长期规则。

## Source of truth

执行前必须读取：

1. `docs/ai-plan/00_INDEX.md`
2. `docs/ai-plan/01_SPEC.md`
3. `docs/ai-plan/04_PRIORITY_PLAN.md`
4. `docs/ai-plan/05_TASK_MATRIX.md`
5. `docs/ai-plan/06_VALIDATION.md`
6. `docs/ai-plan/07_STATUS.md`
7. `docs/ai-plan/11_HARD_STOP_POLICY.md`
8. `docs/ai-plan/12_LAUNCHD_REMEDIATION.md`
9. `docs/ai-plan/15_FINAL_ACCEPTANCE.md`

如这些文件之间冲突，优先级为：

```text
HARD_STOP_POLICY > SPEC > FINAL_ACCEPTANCE > VALIDATION > TASK_MATRIX > PRIORITY_PLAN > STATUS
```

## Project goal

实现一个非侵入式 Hermes Ops 升级层，默认落在：

```text
/Users/cc/.hermes/ops
/Users/cc/HermesArchive/hermes-new-<timestamp>
```

这个 Ops 层必须提供：

- Phase-based GO/NO-GO gate
- Hard-stop side-effect guard
- Evidence pack
- Executed / not-executed command ledger
- Config / `.env` SHA256 baseline and redacted diff
- macOS launchd read-only preflight and controlled remediation wrapper
- Live validation matrix
- Operator SOP generator
- Skill router compatibility layer
- HermesArchive manifest
- HMAC-SHA256 audit chain
- Codex execution discipline through status ledger and validation gates

## Non-goals

- 不从旧 Hermes 恢复功能代码。
- 不复制旧 plist、旧 config、旧 `.env`、旧 scripts。
- 不重造 Telegram、Feishu/Lark、Weixin、cron、provider、gateway 等官网已有基础功能。
- 不修改 Hermes core，除非 P3 明确要求准备 upstream PR 且已完成本地 ops 层。
- 不以插件或安全绕过方式追求“绝对不间断”。

## Mandatory workflow

For each task in `docs/ai-plan/05_TASK_MATRIX.md`:

1. Read task dependencies.
2. Create or update evidence under the active HermesArchive run directory.
3. Implement the smallest safe change.
4. Run the validation listed in `docs/ai-plan/06_VALIDATION.md`.
5. Update `docs/ai-plan/07_STATUS.md` with:
   - status: `PENDING`, `IN_PROGRESS`, `DONE`, `BLOCKED`, `NO-GO`, or `NOT_APPLICABLE`
   - files changed
   - validation result
   - evidence path
   - next task
6. If a decision is made, append it to `docs/ai-plan/08_DECISIONS.md`.

## Continuous execution rule

Do not pause after every safe task. Continue from `P0` to `P3` until every task is `DONE`, `BLOCKED` with evidence, or `NOT_APPLICABLE` with evidence.

If one task is blocked, continue all independent safe tasks that do not depend on it.

## Hard-stop rule

Never execute these actions directly unless a completed `hermes-ops` gate explicitly allows the exact action:

- `launchctl enable`
- `launchctl bootstrap`
- `launchctl bootout`
- `launchctl kickstart`
- `launchctl load -w`
- `launchctl unload -w`
- `hermes gateway install`
- `hermes gateway start`
- `hermes gateway stop`
- `hermes gateway restart`
- editing `/Users/cc/.hermes/config.yaml`
- editing `/Users/cc/.hermes/.env`
- replacing launchd plist files
- global package installation
- deleting files or directories

When a hard-stop action is not allowed, record it in the not-executed ledger and continue safe tasks.

## Secret handling

Never print, copy, or persist secret values. For `.env`, auth tokens, API keys, bot tokens, webhook secrets, and provider credentials, record only:

- file exists / missing
- file permission
- mtime
- SHA256 hash
- redacted key names

## Codex safety

- Do not use `--yolo`.
- Do not use approval-bypass mode.
- Do not use `danger-full-access` unless the user explicitly moves the work into an isolated disposable VM.
- Prefer `workspace-write` / default Agent mode.
- Network access should remain off unless the specific task requires source refresh and the user approves.

## Done standard

The overall upgrade is not complete until all final artifacts in `docs/ai-plan/15_FINAL_ACCEPTANCE.md` exist and the final GO/NO-GO decision is written.
