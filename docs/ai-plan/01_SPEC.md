# 01_SPEC — 新 Hermes Ops 升级规格

## 目标

为全新 Hermes Agent 建立本地 Ops 层，使其具备旧系统中有价值的生产化能力：

1. Phase-based GO/NO-GO gate
2. Hard-stop side-effect guard
3. Evidence pack
4. Executed / not-executed command ledger
5. Config / `.env` SHA256 baseline and redacted diff
6. macOS launchd read-only preflight and controlled remediation wrapper
7. Live validation matrix
8. Operator SOP generator
9. Skill router compatibility layer
10. HermesArchive manifest
11. HMAC-SHA256 tamper-evident audit chain
12. CodexDesktop execution discipline via `AGENTS.md`, `PLAN.md`, `STATUS.md`, and validation gates

## 非目标

- 不恢复旧 Hermes 的功能代码。
- 不迁移旧系统的 config、secrets、plist、scripts。
- 不重写 Hermes 官方已实现的 gateway、messaging adapter、provider、cron、skills。
- 不默认修改 Hermes core。
- 不把第三方插件当作“无限无人值守”的解决方案。

## 目标路径

```text
/Users/cc/.hermes/
  AGENTS.md
  CODEX_DESKTOP_GOAL_PROMPT.md
  docs/ai-plan/
  ops/
    bin/hermes-ops
    lib/*.py
    tests/*
    reports/latest -> /Users/cc/HermesArchive/hermes-new-<timestamp>

/Users/cc/HermesArchive/
  hermes-new-<timestamp>/
    manifest.json
    source-inventory/
    phases/
    ledgers/
    audit/
    reports/
```

## 操作原则

- 只要缺少证据，就不执行有副作用操作。
- 只要可能泄露 secrets，就只记录 hash / key name / metadata。
- 只要任务被阻塞，就记录 `BLOCKED`，继续安全独立任务。
- 只要涉及 launchd，就先 read-only inspect，再 gate，再 remediation。
- 只要涉及上线，就必须有 final validation matrix 和 operator SOP。

## 成功标准

所有任务在 `05_TASK_MATRIX.md` 中进入以下状态之一：

- `DONE`
- `BLOCKED` with evidence
- `NOT_APPLICABLE` with evidence

并且最终报告产生：

- `final-go-nogo.md`
- `final-validation-matrix.md`
- `operator-sop.md`
- `next-actions.md`
