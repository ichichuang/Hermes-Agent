# Hermes 升级计划体系（CodexDesktop 执行版）

生成日期：2026-05-27
目标目录：`/Users/cc/.hermes`
目标：为全新 Hermes Agent 建立一套**非侵入式、可审计、可验证、可硬停**的生产化 Ops 升级层。

本计划不从旧 Hermes 恢复功能代码。旧系统只作为需求来源：Phase gate、GO/NO-GO、证据包、命令账本、配置 SHA256、launchd 预检、live validation、SOP、HermesArchive 归档、审计链。

## 使用方式

### 1. 解压到本机

建议解压后把本目录内容复制到：

```bash
/Users/cc/.hermes
```

可使用本包提供的安全复制脚本：

```bash
cd hermes-upgrade-plan-system-20260527
bash scripts/install_to_hermes_home.sh /Users/cc/.hermes
```

脚本不会删除 `.hermes` 中已有文件；如有同名文件，会先备份。

### 2. 在 CodexDesktop 打开项目

首选打开：

```text
/Users/cc/.hermes
```

如果 `/Users/cc/.hermes` 不是 Git 仓库，CodexDesktop 不能使用 Worktree 模式；这不影响 Local 模式执行。若你希望用 Worktree，可让 Codex 先创建一个专用 Git workspace，但不要让它移动或删除现有 `.hermes` 文件。

### 3. 启动 Goal

在 CodexDesktop 中打开 `CODEX_DESKTOP_GOAL_PROMPT.md`，复制其中 `/goal` 指令执行。

核心规则：

- 连续执行 `P0 -> P1 -> P2 -> P3`。
- 不在每个小任务后等待人工确认。
- 遇到 hard-stop 条件时，必须把当前任务标记为 `BLOCKED` / `NO-GO` 并写入证据，然后继续所有不依赖该阻塞项的安全任务。
- 不使用 `--yolo`、approval bypass、danger full access。
- 不打印、不复制、不持久化 secrets。
- 不直接执行 `launchctl enable/bootstrap/bootout/kickstart` 或 `hermes gateway start/stop/restart/install`，除非 `hermes-ops` gate 明确允许。

## 文件角色

| 文件 | 作用 |
|---|---|
| `INSTALL.md` | 安全安装/复制说明 |
| `AGENTS.md` | Codex 长期工作规则 |
| `.codex/config.toml` | Codex 本地建议配置；启用 goals，默认禁用命令网络访问 |
| `CODEX_DESKTOP_GOAL_PROMPT.md` | 可直接粘贴给 CodexDesktop 的持续执行目标 |
| `docs/ai-plan/00_INDEX.md` | 计划文件索引 |
| `docs/ai-plan/01_SPEC.md` | 目标、非目标、硬约束、交付物 |
| `docs/ai-plan/02_RESEARCH_BRIEF.md` | 官网、GitHub、Codex、开源工具研究摘要 |
| `docs/ai-plan/03_ARCHITECTURE.md` | Hermes Ops 层目标架构 |
| `docs/ai-plan/04_PRIORITY_PLAN.md` | 按优先级排列的完整执行计划 |
| `docs/ai-plan/05_TASK_MATRIX.md` | 可执行任务矩阵 |
| `docs/ai-plan/06_VALIDATION.md` | 验收命令与判定标准 |
| `docs/ai-plan/07_STATUS.md` | Codex 必须持续更新的进度账本 |
| `docs/ai-plan/08_DECISIONS.md` | 架构决策记录 |
| `docs/ai-plan/09_RISK_REGISTER.md` | 风险登记册 |
| `docs/ai-plan/10_OPEN_SOURCE_TOOLS.md` | 开源工具选型 |
| `docs/ai-plan/11_HARD_STOP_POLICY.md` | 硬停与副作用策略 |
| `docs/ai-plan/12_LAUNCHD_REMEDIATION.md` | macOS launchd 专项计划 |
| `docs/ai-plan/13_LIVE_VALIDATION.md` | DeepSeek / Telegram / Jobs / Feishu-Lark 验收矩阵 |
| `docs/ai-plan/14_CODEX_EXECUTION.md` | CodexDesktop 执行策略 |
| `docs/ai-plan/15_FINAL_ACCEPTANCE.md` | 最终完成标准 |
| `templates/` | 证据包、报告、SOP 模板 |
| `scripts/` | 安装/检查/打印目录的辅助脚本 |

## 一句话目标

把新 Hermes 的基础功能保留为官方能力，把老系统中真正有价值的生产化纪律封装为 `hermes-ops`：**无证据不改机器，有副作用必过 gate，所有结论可审计，所有上线可回滚。**
