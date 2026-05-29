# 10_OPEN_SOURCE_TOOLS — 开源工具选型

## 结论

未发现一个免费开源工具能完整替代本计划所需的 Hermes-specific production gate。采用以下策略：

```text
核心：Python stdlib
增强：成熟小工具
禁止：为了不间断而使用审批绕过插件
```

## 推荐工具

| Tool | Priority | Use | Install policy |
|---|---:|---|---|
| Python stdlib | P0 | hash、JSON、plist、subprocess、pathlib、hmac | 必需；系统已有则使用 |
| pytest | P0/P1 | Python unit tests | 若已有则使用；缺失则记录 |
| gitleaks | P0/P1 | secret scan | 推荐；缺失不阻塞核心 |
| ShellCheck | P0/P1 | shell static analysis | 推荐；缺失不阻塞核心 |
| shfmt | P1 | shell formatting | 可选 |
| jq | P1 | JSON filtering | 可选 |
| yq | P1 | YAML inspection | 可选；核心用 stdlib 或安全解析 |
| bats-core | P1 | shell wrapper tests | 可选 |
| pre-commit | P2 | 本地质量门禁 | 可选 |
| just | P2 | command runner | 可选 |
| Task | P2 | command runner | 可选 |

## 工具探测命令

```bash
for tool in python3 pytest gitleaks shellcheck shfmt jq yq bats pre-commit just task; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "FOUND $tool: $(command -v "$tool")"
  else
    echo "MISSING $tool"
  fi
done
```

## 禁止事项

- 不全局安装工具，除非用户明确批准。
- 不运行未知 third-party installer。
- 不复制 `.env` 给 gitleaks 之外的任何外部工具。
- 不把 optional tool 缺失当作全局失败。
