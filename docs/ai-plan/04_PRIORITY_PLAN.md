# 04_PRIORITY_PLAN — 按优先级排列的完整升级计划

## P0 — 安全施工基础

目标：在不触碰生产配置、不启动/停止服务、不泄露 secrets 的前提下，建立可执行 Ops 框架。

### P0.A0 — Workspace bootstrap

- 读取全部计划文档。
- 创建 active archive run directory。
- 初始化 `manifest.json`。
- 初始化 `07_STATUS.md` 当前运行记录。
- 确认 `/Users/cc/.hermes` 是否为 Git repo；若不是，记录，不强行初始化。

验收：active archive 存在；manifest 存在；STATUS 记录本次运行。

### P0.A1 — Source inventory and research refresh

- 记录 Hermes 本地版本、`which hermes`、`hermes --version`。
- 记录 Python、Node、macOS 版本。
- 记录官方文档 URL 列表。
- 如网络不可用，标记 source refresh 部分 `BLOCKED`，继续本地任务。

验收：`source-inventory/` 完成。

### P0.A2 — Ops layer skeleton

- 创建 `/Users/cc/.hermes/ops` 目录。
- 创建 `bin/hermes-ops` CLI skeleton。
- 创建 `lib/` 与 `tests/`。
- CLI 支持 `--help`、`status`、`phase start`、`phase gate` 的基本路由。

验收：`hermes-ops --help` 正常输出。

### P0.A3 — Evidence pack engine

- 实现 evidence pack 创建。
- 实现 phase report 生成。
- 实现 manifest 更新。
- 实现 evidence path 规范化。

验收：可创建 phase 目录和 `phase-report.md`。

### P0.A4 — Command ledger and not-executed ledger

- 实现 `command-ledger.jsonl`。
- 实现 `explicitly-not-executed.jsonl`。
- 每条记录包含 timestamp、phase、command、risk、exit code、stdout/stderr path、decision。

验收：dry-run 命令和 blocked command 均能入账。

### P0.A5 — Config integrity and redaction

- 对 `~/.hermes/config.yaml`、`~/.hermes/.env`、`~/.hermes/auth.json`、`~/.hermes/SOUL.md` 生成 SHA256。
- `.env` 只提取 key name，不提取 value。
- 输出 redacted summary。

验收：报告无 secret 明文；hash 存在。

### P0.A6 — Phase gate and side-effect guard

- 实现硬停策略。
- 对高风险命令默认 `NO-GO`。
- 只有 phase gate 满足 evidence/config/preflight 时才允许 side-effect。

验收：危险命令 dry-run 被阻止并写入 not-executed ledger。

### P0.A7 — Launchd read-only preflight

- 解析 plist path。
- read-only 检查 label、ProgramArguments、EnvironmentVariables、HERMES_HOME、PATH、VIRTUAL_ENV。
- 探测 `gui/<uid>` 与 `user/<uid>` domain。
- 读取 `launchctl print` 输出，但不执行 enable/bootstrap/bootout/kickstart。
- 检查重复 gateway 进程。

验收：生成 `launchd-preflight.md/json`。

### P0.A8 — P0 validation

- 运行 Python unit tests。
- 运行 shellcheck/shfmt，如工具存在。
- 运行 secret scan，如工具存在。
- 生成 P0 GO/NO-GO。

验收：P0 任务均 `DONE` 或 `BLOCKED` with evidence。

## P1 — 上线验收与受控 remediation

目标：让 Ops Layer 能判断新 Hermes 是否可进入生产使用，并在满足 gate 时执行受控修复。

### P1.B1 — Controlled launchd remediation wrapper

- 实现 `hermes-ops run --risk service-change`。
- 默认 dry-run。
- 对 exact command allowlist、phase prerequisites、evidence path、config hash、preflight result 做检查。
- 支持但不直接推荐：`launchctl bootstrap`、`kickstart`、`enable`、`load -w` fallback 的 gated execution。

验收：没有 gate 时拒绝；gate 满足时只允许 exact command。

### P1.B2 — Live validation matrix

- DeepSeek/provider auth validation。
- Telegram send/receive validation。
- Feishu/Lark websocket/webhook validation。
- Jobs/cron delivery validation。
- Gateway log health validation。
- 允许缺失 token 时标记 `BLOCKED`。

验收：生成 `final-validation-matrix.md` 或 phase validation matrix。

### P1.B3 — Operator SOP generator

生成 `operator-sop.md`，包含：

- 当前结论。
- 可执行命令。
- 禁止命令。
- 如何查看日志。
- 如何回滚。
- 如何接续下一阶段。
- 风险说明。

验收：SOP 可以让第三方操作者接手。

### P1.B4 — HMAC-SHA256 audit chain

- 生成 0600 key。
- append-only JSONL audit chain。
- 每条记录含 prev_hmac、entry_hmac。
- 提供 verify 命令。

验收：篡改任一 entry 后 verify 失败。

### P1.B5 — Security baseline

- 检查 YOLO 环境变量。
- 检查 config 是否关闭 destructive confirmation。
- 检查 allowlist 是否为空或 allow-all。
- 检查 `.env` 权限。

验收：生成 `security-baseline.md`。

### P1.B6 — P1 final GO/NO-GO

- 汇总 P0/P1。
- 写入 `final-go-nogo.md`。

验收：明确 `GO`、`NO-GO` 或 `GO_WITH_BLOCKERS`。

## P2 — 长期维护与扩展

### P2.C1 — Skill router compatibility layer

- repo-local skill 优先。
- user skill 次之。
- built-in skill 最后。
- 记录实际加载路径。

### P2.C2 — HermesArchive standardization

- 标准化 archive manifest。
- 生成 latest symlink。
- 生成 archive index。

### P2.C3 — Codex/Hermes skill packaging

- 将重复流程封装为 Codex skill 或 Hermes skill。
- 不把 plugin 当作安全绕过。

### P2.C4 — Kanban integration design

- 可选：把 task matrix 映射到 Hermes Kanban。
- 保留 STATUS.md 作为主账本。

### P2.C5 — Web UI gateway collision detector

- 只读检测重复 gateway 进程。
- 生成建议，不自动 patch web UI。

## P3 — 上游贡献与维护自动化

### P3.D1 — Upstream PR prep

- 如果发现 Hermes core launchd bug，准备最小 PR 草案。
- 不直接改 core 作为本地生产依赖。

### P3.D2 — Maintenance automation

- 周期性运行 read-only health check。
- 不自动执行 remediation。

### P3.D3 — Self-evaluation and regression pack

- 建立回归测试。
- 每次 Hermes 更新后跑 preflight。

### P3.D4 — Final documentation bundle

- 生成完整 docs bundle。
- 生成 next-actions。
