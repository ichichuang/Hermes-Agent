# 13_LIVE_VALIDATION — 实时验收矩阵

## 目标

判断新 Hermes 是否真的可用，而不是只判断文件和进程存在。

## 状态枚举

- `PASS`：验证成功。
- `FAIL`：验证执行且失败。
- `BLOCKED`：缺少 token、权限、网络、人工输入或 gate。
- `NOT_APPLICABLE`：该平台未配置或用户明确不启用。

## 验收矩阵

| Check | Method | Secret handling | Expected |
|---|---|---|---|
| Hermes CLI chat | `hermes --version`, optional smoke chat | no secrets | CLI callable |
| Provider / DeepSeek | provider config exists; optional test call | no API key output | auth succeeds or BLOCKED |
| Gateway process | `hermes gateway status` or read-only process inspect | redact logs | status healthy or documented |
| Telegram | bot config exists; optional send/receive validation | no bot token output | DM/group behavior verified or BLOCKED |
| Feishu/Lark | app config exists; websocket/webhook mode inspect | no app secret output | connected or BLOCKED |
| Jobs / cron | list configured jobs; optional delivery to home channel | no secrets | due job delivery verified or BLOCKED |
| Allowlist | inspect env/config keys only | key names only | allowlist/pairing policy documented |
| Gateway logs | tail redacted logs | redact | no fatal errors |

## Dry-run behavior

`hermes-ops validate live --dry-run` 必须：

- 不发送消息。
- 不调用 provider API。
- 不修改 config。
- 只判断配置是否足以执行 live validation。

## Live behavior

`hermes-ops validate live --final` 可在用户授权和 token 存在时执行：

- 发送 Telegram test message。
- 请求 provider minimal completion。
- 验证 Feishu/Lark connection。
- 验证 cron/job delivery。

每个 live check 都必须写证据；失败不允许静默吞掉。

## 报告格式

生成：

```text
reports/final-validation-matrix.md
```

模板见：

```text
templates/reports/final-validation-matrix.template.md
```
