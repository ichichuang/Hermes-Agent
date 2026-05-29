# 02_RESEARCH_BRIEF — 研究依据摘要

## 1. Hermes 官方能力边界

Hermes Agent 官方文档和 GitHub README 表明，Hermes 已经是多平台、多 provider、自带学习循环的 agent，支持 Telegram/Discord/Slack/WhatsApp/Signal 等消息入口，也支持 cron scheduler、skills、providers 和后台 gateway。
来源：

- https://github.com/NousResearch/hermes-agent
- https://hermes-agent.nousresearch.com/docs/
- https://hermes-agent.nousresearch.com/docs/getting-started/quickstart
- https://hermes-agent.nousresearch.com/docs/user-guide/messaging/
- https://hermes-agent.nousresearch.com/docs/integrations/providers

结论：不要重造 messaging/provider/cron 基础能力。升级重点应是 Ops 控制层。

## 2. Messaging gateway 与 launchd

官方 messaging 文档说明：gateway 是单一后台进程，连接所有已配置平台，处理 sessions、cron jobs 和 voice messages。macOS 下可用 `hermes gateway install/start/stop/status`，生成 plist 路径为：

```text
~/Library/LaunchAgents/ai.hermes.gateway.plist
```

plist 包含 `PATH`、`VIRTUAL_ENV`、`HERMES_HOME` 等环境变量。
来源：

- https://hermes-agent.nousresearch.com/docs/user-guide/messaging/
- https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/messaging/index.md

结论：launchd 不是要重造，而是要纳入 read-only preflight、controlled remediation、证据包和硬停规则。

## 3. Gateway 安全与 allowlist

官方 messaging 文档显示 gateway 默认拒绝未在 allowlist 或未通过 DM pairing 的用户，并列出各平台 allowed users 环境变量。
来源：

- https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

结论：新 Ops 层应验证 allowlist/pairing 配置是否存在，但不得输出 secrets。

## 4. Background sessions 与 jobs

官方文档支持 `/background <prompt>`，后台 session 独立运行，完成后回传结果；gateway 同时负责 cron job delivery。
来源：

- https://hermes-agent.nousresearch.com/docs/user-guide/messaging/

结论：Jobs/live validation 应验证官方能力是否可用，而不是重新实现 job scheduler。

## 5. Provider 支持

官方 providers 文档列出多 provider，包括 OpenRouter、OpenAI、Anthropic、DeepSeek 等。
来源：

- https://hermes-agent.nousresearch.com/docs/integrations/providers

结论：DeepSeek 应作为 live validation 的 provider 检查项，不作为重造项。

## 6. 配置与 secrets

官方配置文档说明 `hermes config set` 会把 API keys 保存到 `.env`，其他配置保存到 `config.yaml`。
来源：

- https://hermes-agent.nousresearch.com/docs/user-guide/configuration

结论：Ops 层必须对 `config.yaml` 与 `.env` 生成 SHA256 和 redacted summary，但不能复制 `.env` 明文。

## 7. YOLO / approval 风险

官方 security 文档说明 YOLO mode 会绕过危险命令 approval，可以通过 CLI flag、slash command 或环境变量启用。
来源：

- https://hermes-agent.nousresearch.com/docs/user-guide/security

结论：本计划明确禁止 `--yolo`、`/yolo`、`HERMES_YOLO_MODE=1` 与 approval bypass。

## 8. 近期 launchd 相关 GitHub 问题

已检索到多个 macOS launchd / gateway 相关问题，说明 launchd remediation 必须设为 P0/P1：

| Issue | 发现 | 对本计划的影响 |
|---|---|---|
| #11323 | `launchctl bootstrap` exit 5 可能导致 gateway start/install 失败 | preflight 必须记录 bootstrap 风险；remediation 不能盲目执行 |
| #4820 | 现代 macOS 下 deprecated `launchctl start/stop` 可能失败；建议 bootstrap/kickstart/kill | wrapper 必须识别现代命令，但仍受 gate 控制 |
| #5589 | launchd 下可能出现 EX_CONFIG 78，导致服务卡在 spawn scheduled | inspect 必须读取 last exit code、runs、state |
| #27041 | Web UI 可能重复 spawn gateway，造成 restart loops | inspect 必须检查重复 gateway 进程 |
| #30586 | `gui/<uid>` 硬编码在 SSH/headless 场景可能失效，应 fallback `user/<uid>` | preflight 必须同时探测 `gui/<uid>` 与 `user/<uid>` |

来源：

- https://github.com/NousResearch/hermes-agent/issues/11323
- https://github.com/NousResearch/hermes-agent/issues/4820
- https://github.com/NousResearch/hermes-agent/issues/5589
- https://github.com/NousResearch/hermes-agent/issues/27041
- https://github.com/NousResearch/hermes-agent/issues/30586

## 9. CodexDesktop 执行策略

OpenAI Codex 文档显示：

- Codex 会读取 `AGENTS.md` 作为项目规则。
- Goal mode 是持久目标，适合有明确完成条件和验证面的长期任务。
- Codex app 支持并行 threads、worktrees、automations、Git 功能、skills。
- 默认 sandbox 通常限制在 active workspace，网络默认关闭，越界写入或网络访问需要 approval。
- Worktrees 依赖 Git repo；非 Git 项目不能直接使用 worktree。
- Skills 用于复用工作流；plugins 是可安装分发单元，不是绕过安全审批的工具。

来源：

- https://developers.openai.com/codex/guides/agents-md
- https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex
- https://developers.openai.com/codex/app/features
- https://developers.openai.com/codex/app/worktrees
- https://developers.openai.com/codex/agent-approvals-security
- https://developers.openai.com/codex/skills

结论：最佳执行方式是 `AGENTS.md + docs/ai-plan + STATUS.md + /goal + validation gates`。不建议寻找第三方插件来实现“无限不间断”。

## 10. 开源工具结论

未发现一个开源免费工具能完整替代本计划所需的 Hermes-specific phase gate + evidence pack + launchd remediation + live validation + audit chain。应采用“小工具组合 + Python stdlib”策略：

- Python stdlib：核心实现。
- `jq` / `yq`：可选 JSON/YAML 辅助。
- `pytest`：Python 测试。
- `bats-core`：shell wrapper 测试。
- `ShellCheck` / `shfmt`：shell 质量。
- `gitleaks`：secret 扫描。
- `pre-commit`：可选本地门禁。
- `just` / `Task`：可选命令编排。

来源：

- https://github.com/jqlang/jq
- https://github.com/mikefarah/yq
- https://github.com/pytest-dev/pytest
- https://github.com/bats-core/bats-core
- https://github.com/koalaman/shellcheck
- https://github.com/mvdan/sh
- https://github.com/gitleaks/gitleaks
- https://pre-commit.com/
- https://github.com/casey/just
- https://taskfile.dev/
