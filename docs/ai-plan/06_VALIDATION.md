# 06_VALIDATION — 验收命令与判定标准

## 通用验证

每个 milestone 至少运行：

```bash
/Users/cc/.hermes/ops/bin/hermes-ops status || true
python3 -m pytest /Users/cc/.hermes/ops/tests || true
```

如果 `pytest` 不存在，记录 `BLOCKED_TOOL_MISSING`，但继续可执行的 stdlib smoke tests。

## P0 验证

### P0.A2 skeleton

```bash
/Users/cc/.hermes/ops/bin/hermes-ops --help
/Users/cc/.hermes/ops/bin/hermes-ops status
```

通过标准：命令输出帮助或 JSON 状态，不抛异常。

### P0.A3 evidence pack

```bash
/Users/cc/.hermes/ops/bin/hermes-ops phase start P0.A3 --dry-run
/Users/cc/.hermes/ops/bin/hermes-ops phase start P0.A3
```

通过标准：生成 phase directory、phase-report.md、manifest update。

### P0.A4 ledger

```bash
/Users/cc/.hermes/ops/bin/hermes-ops run --phase P0.A4 --risk read-only --dry-run -- /bin/pwd
/Users/cc/.hermes/ops/bin/hermes-ops ledger list
```

通过标准：command-ledger 和 not-executed ledger 都能追加记录。

### P0.A5 config integrity

```bash
/Users/cc/.hermes/ops/bin/hermes-ops hash snapshot --phase P0.A5
```

通过标准：输出 hash；`.env` 中无 value 明文。

### P0.A6 hard-stop guard

```bash
/Users/cc/.hermes/ops/bin/hermes-ops run --phase P0.A6 --risk service-change --dry-run -- /bin/launchctl enable gui/$(/usr/bin/id -u)/ai.hermes.gateway
```

通过标准：命令被拒绝或仅 dry-run；not-executed ledger 记录。

### P0.A7 launchd inspect

```bash
/Users/cc/.hermes/ops/bin/hermes-ops launchd inspect --phase P0.A7
```

通过标准：只读输出 plist/domain/process/log 状态；未执行 enable/bootstrap/bootout/kickstart/load/unload。

## P1 验证

### P1.B1 controlled remediation

```bash
/Users/cc/.hermes/ops/bin/hermes-ops gate check --phase P1.B1
/Users/cc/.hermes/ops/bin/hermes-ops run --phase P1.B1 --risk service-change --dry-run -- /bin/launchctl print gui/$(/usr/bin/id -u)/ai.hermes.gateway
```

通过标准：read-only command 可 dry-run；有副作用 command 只有 gate 满足时才可执行。

### P1.B2 live validation

```bash
/Users/cc/.hermes/ops/bin/hermes-ops validate live --phase P1.B2 --dry-run
```

通过标准：每项为 PASS/FAIL/BLOCKED/NOT_APPLICABLE；缺 token 不失败整个计划，而是记录 BLOCKED。

### P1.B4 audit chain

```bash
/Users/cc/.hermes/ops/bin/hermes-ops audit append --phase P1.B4 --event smoke-test
/Users/cc/.hermes/ops/bin/hermes-ops audit verify
```

通过标准：verify PASS；篡改测试能 FAIL。

## 工具验证

如果工具存在，运行：

```bash
command -v shellcheck && shellcheck /Users/cc/.hermes/ops/bin/hermes-ops || true
command -v shfmt && shfmt -d /Users/cc/.hermes/ops/bin || true
command -v gitleaks && gitleaks detect --no-git --source /Users/cc/.hermes/ops --redact || true
```

工具不存在时，不允许全局安装；只记录 `OPTIONAL_TOOL_MISSING`。

## 最终验收

```bash
/Users/cc/.hermes/ops/bin/hermes-ops report final
/Users/cc/.hermes/ops/bin/hermes-ops audit verify
/Users/cc/.hermes/ops/bin/hermes-ops validate live --final
```

通过标准见 `15_FINAL_ACCEPTANCE.md`。
