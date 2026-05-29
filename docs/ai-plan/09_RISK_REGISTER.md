# 09_RISK_REGISTER — 风险登记册

| Risk ID | Risk | Severity | Mitigation | Owner | Status |
|---|---|---:|---|---|---|
| R-001 | D2/旧证据路径缺失导致误操作 | High | 不使用旧证据作为执行前提；新建 fresh archive | Codex | Open |
| R-002 | `.env` secret 泄露到 evidence | Critical | 只记录 hash/key name/metadata；运行 redaction tests | Codex | Open |
| R-003 | launchd 命令误启停生产 gateway | Critical | side-effect guard；exact command allowlist；not-executed ledger | Codex | Open |
| R-004 | `gui/<uid>` domain 不存在导致 remediation 失败 | High | 同时探测 `gui/<uid>` 与 `user/<uid>`；不盲目执行 | Codex | Open |
| R-005 | gateway plist PATH/VIRTUAL_ENV/HERMES_HOME 漂移 | High | launchd preflight 读取 plist env 与当前 env 对比 | Codex | Open |
| R-006 | Web UI 重复 spawn gateway | Medium | process detector；报告建议；不自动 patch | Codex | Open |
| R-007 | Codex 长任务上下文漂移 | Medium | AGENTS.md + STATUS.md + validation gates + Goal prompt | Codex | Open |
| R-008 | 工具链缺失导致测试无法运行 | Medium | optional tool 缺失记 BLOCKED_TOOL_MISSING；核心用 stdlib | Codex | Open |
| R-009 | 过度修改 Hermes core | High | 默认不改 core；P3 才准备 upstream PR notes | Codex | Open |
| R-010 | 用户误以为 BLOCKED 等于失败 | Low | final report 区分 FAIL、BLOCKED、NOT_APPLICABLE | Codex | Open |
