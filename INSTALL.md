# INSTALL — 安全放置到 /Users/cc/.hermes

本包的目标是把计划体系放到本机：

```text
/Users/cc/.hermes
```

## 推荐方式：运行安全安装脚本

```bash
cd hermes-upgrade-plan-system-20260527
bash scripts/install_to_hermes_home.sh /Users/cc/.hermes
```

脚本行为：

- 只复制本计划包内的文件。
- 如目标路径已有同名文件，先把该文件备份为 `*.backup-YYYYMMDD_HHMMSS`。
- 不删除 `/Users/cc/.hermes` 既有内容。
- 不读取或打印 `.env`、`auth.json`。
- 不修改 `config.yaml`、`.env`、`auth.json`、launchd plist。
- 不执行 `launchctl` 或 `hermes gateway` 命令。

## 手动方式

```bash
mkdir -p /Users/cc/.hermes
cp -R README.md INSTALL.md AGENTS.md CODEX_DESKTOP_GOAL_PROMPT.md FILE_INDEX.md TREE.txt MANIFEST.json /Users/cc/.hermes/
cp -R .codex docs templates scripts /Users/cc/.hermes/
```

如 `/Users/cc/.hermes/AGENTS.md` 已存在，请先人工合并，不要盲目覆盖。

## CodexDesktop 启动

安装后：

1. 在 CodexDesktop 中打开项目 `/Users/cc/.hermes`。
2. 读取 `/Users/cc/.hermes/CODEX_DESKTOP_GOAL_PROMPT.md`。
3. 将其中 `/goal` 指令复制到 CodexDesktop。

## 不要覆盖的生产文件

```text
/Users/cc/.hermes/config.yaml
/Users/cc/.hermes/.env
/Users/cc/.hermes/auth.json
/Users/cc/.hermes/gateway.json
/Users/cc/.hermes/SOUL.md
/Users/cc/Library/LaunchAgents/ai.hermes.gateway.plist
```
