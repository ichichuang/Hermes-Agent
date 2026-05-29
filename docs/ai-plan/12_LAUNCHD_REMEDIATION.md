# 12_LAUNCHD_REMEDIATION — macOS launchd 专项计划

## 目标

把 Hermes Gateway 的 macOS launchd 状态纳入可审计 preflight 与受控 remediation。先检查，再决定；无证据不执行。

## 官方基础信息

默认 Hermes Home 为 `~/.hermes` 时：

```text
Label: ai.hermes.gateway
Plist: ~/Library/LaunchAgents/ai.hermes.gateway.plist
Log: ~/.hermes/logs/gateway.log
```

plist 应包含：

- `PATH`
- `VIRTUAL_ENV`
- `HERMES_HOME`

## Read-only preflight 检查项

1. 当前用户 UID。
2. `gui/<uid>` 是否存在。
3. `user/<uid>` 是否存在。
4. plist 是否存在。
5. plist `Label` 是否匹配。
6. plist `ProgramArguments` 是否指向当前 `hermes`。
7. plist `EnvironmentVariables.PATH` 是否合理。
8. plist `EnvironmentVariables.VIRTUAL_ENV` 是否存在。
9. plist `EnvironmentVariables.HERMES_HOME` 是否等于 `/Users/cc/.hermes`。
10. `launchctl print <domain>/ai.hermes.gateway` 状态。
11. last exit status、runs、state、throttle 等字段。
12. 是否有多个 `hermes gateway` 进程。
13. gateway log 最近 100 行，必须 redacted。

## 绝不在 preflight 执行的命令

- `launchctl enable`
- `launchctl bootstrap`
- `launchctl bootout`
- `launchctl kickstart`
- `launchctl load -w`
- `launchctl unload -w`
- `hermes gateway install/start/stop/restart`

## Remediation 允许条件

只有 P1.B1 或更高阶段允许讨论 remediation，并且必须满足 `11_HARD_STOP_POLICY.md` 的 gate 条件。

## GitHub issue 驱动的检查点

| Issue | Check |
|---|---|
| #11323 bootstrap exit 5 | 记录 bootstrap 历史风险；不要盲目 bootstrap |
| #4820 deprecated start/stop | 不依赖 deprecated `launchctl start/stop` |
| #5589 EX_CONFIG 78 | 读取 last exit code，记录 spawn scheduled |
| #27041 duplicate gateway | 检查重复 gateway 进程和 Web UI spawn |
| #30586 gui domain hardcode | 同时探测 `gui/<uid>` 与 `user/<uid>` |

## Preflight 输出

生成：

```text
phases/P0.A7-launchd-preflight/
  launchd-preflight.json
  launchd-preflight.md
  launchctl-print-gui.txt
  launchctl-print-user.txt
  plist-summary.json
  process-list.txt
  gateway-log-tail.redacted.txt
```

## Remediation 输出

若后续 gate 允许执行 remediation，必须生成：

```text
phases/P1.B1-controlled-launchd-remediation/
  before-state.json
  gate-decision.json
  exact-command.txt
  command-output.txt
  after-state.json
  rollback-note.md
```
