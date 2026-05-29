# 14_CODEX_EXECUTION — CodexDesktop 执行策略

## 核心结论

不需要寻找第三方插件来让 CodexDesktop “无限制、不间断”执行。正确做法是：

```text
AGENTS.md
+ docs/ai-plan/
+ STATUS.md
+ /goal
+ validation gates
+ evidence pack
```

## 推荐模式

### 如果 `/Users/cc/.hermes` 不是 Git 仓库

使用 CodexDesktop Local 模式。不要强行创建 worktree。Codex 仍可读取 `AGENTS.md` 和计划文件，并持续更新 `07_STATUS.md`。

### 如果用户希望使用 Worktree

只有在 Git repo 中可用。可让 Codex 建议创建独立 workspace，但不要移动、删除或重写现有 `.hermes` 文件。

### 如果任务很长

使用 `/goal`。Goal 必须包含：

- 完成条件。
- 验证命令。
- hard-stop 条件。
- status ledger 更新要求。
- final artifact 要求。

## 不建议的模式

- 把超长计划只粘贴在对话里。
- 依赖插件替代计划文件。
- 用 `--yolo` 追求无人值守。
- 在没有 `STATUS.md` 的情况下跑长任务。
- 在没有 evidence pack 的情况下执行 remediation。

## 必须保留的中断点

即使用户希望“不间断”，以下场景也不得绕过：

- secret 缺失或暴露风险。
- 要修改 `.env` / `config.yaml`。
- 要操作 launchd/gateway 服务。
- 要全局安装依赖。
- 要访问网络而 sandbox 禁止。
- 要删除或移动文件。

处理方式不是停止整个计划，而是：

```text
当前任务 BLOCKED/NO-GO + 证据
继续不依赖该任务的安全任务
```

## Codex 启动指令

见根目录：

```text
CODEX_DESKTOP_GOAL_PROMPT.md
```
