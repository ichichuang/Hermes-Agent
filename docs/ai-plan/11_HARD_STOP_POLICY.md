# 11_HARD_STOP_POLICY — 硬停与副作用策略

## 定义

Hard-stop 是不可绕过的安全门禁。触发 hard-stop 时，当前操作必须进入 `NO-GO` 或 `BLOCKED`，并写入 evidence pack 与 not-executed ledger。

## 高风险命令

以下命令禁止直接执行：

```text
launchctl enable
launchctl bootstrap
launchctl bootout
launchctl kickstart
launchctl load -w
launchctl unload -w
hermes gateway install
hermes gateway start
hermes gateway stop
hermes gateway restart
rm -rf
mv /Users/cc/.hermes
chmod/chown secret files
edit /Users/cc/.hermes/config.yaml
edit /Users/cc/.hermes/.env
write ~/Library/LaunchAgents/*.plist
global package install
```

## 允许的安全操作

默认允许：

- `pwd`
- `ls`
- `find` read-only
- `cat` non-secret files
- `stat`
- `shasum` / `sha256sum`
- `plutil -p` read-only plist inspection
- `launchctl print <domain/service>` read-only inspection
- `ps` process listing
- `tail` logs with secret redaction
- 创建 `/Users/cc/.hermes/ops` 文件
- 创建 `/Users/cc/HermesArchive/hermes-new-*` evidence files
- 运行 local tests

## 允许 side-effect 的必要条件

必须全部满足：

1. Active phase exists.
2. Evidence pack exists.
3. Config hash snapshot exists.
4. Launchd preflight exists when command touches launchd/gateway.
5. Exact command appears in the phase allowlist.
6. Risk level is declared.
7. Gate returns `GO` for that exact command.
8. The command output will be captured.
9. Rollback or operator SOP exists for the operation.

## NO-GO 输出要求

当 gate 不满足：

- 不执行命令。
- 在 `explicitly-not-executed.jsonl` 中写入 exact command。
- 在 phase report 中写入 reason。
- 在 `07_STATUS.md` 写入 `NO-GO` 或 `BLOCKED`。
- 继续下一个不依赖该操作的安全任务。

## Secret hard-stop

只要输出包含以下模式，必须 redact：

- `*_API_KEY`
- `*_TOKEN`
- `*_SECRET`
- `BOT_TOKEN`
- `APP_SECRET`
- `AUTH`
- `COOKIE`
- `PRIVATE_KEY`
- `sk-...`

如果无法确认是否已 redact，停止写入报告并标记 `BLOCKED_SECRET_REDACTION`。
