# 03_ARCHITECTURE — 目标架构

## 总体设计

采用非侵入式本地 Ops Layer：

```text
Hermes official core
  └─ existing gateway / providers / cron / messaging / skills

Hermes Ops Layer
  ├─ phase gate
  ├─ side-effect guard
  ├─ evidence pack
  ├─ command ledger
  ├─ config integrity
  ├─ launchd inspector
  ├─ live validators
  ├─ SOP generator
  ├─ skill router compatibility layer
  └─ audit chain
```

Ops Layer 不替代 Hermes core，只包裹生产化操作。

## 目标目录

```text
/Users/cc/.hermes/ops/
  README.md
  bin/
    hermes-ops
  lib/
    __init__.py
    audit_chain.py
    command_ledger.py
    config_integrity.py
    evidence_pack.py
    launchd_inspector.py
    phase_gate.py
    redaction.py
    skill_router.py
    validators.py
  tests/
    test_audit_chain.py
    test_command_ledger.py
    test_config_integrity.py
    test_evidence_pack.py
    test_launchd_inspector.py
    test_phase_gate.py
    test_redaction.py
    test_skill_router.py
  reports/
    latest -> /Users/cc/HermesArchive/hermes-new-<timestamp>
```

## CLI 目标形态

```bash
/Users/cc/.hermes/ops/bin/hermes-ops status
/Users/cc/.hermes/ops/bin/hermes-ops phase start P0.A0
/Users/cc/.hermes/ops/bin/hermes-ops phase gate P0.A3
/Users/cc/.hermes/ops/bin/hermes-ops hash snapshot --phase P0.A4
/Users/cc/.hermes/ops/bin/hermes-ops launchd inspect
/Users/cc/.hermes/ops/bin/hermes-ops validate live --dry-run
/Users/cc/.hermes/ops/bin/hermes-ops sop generate
/Users/cc/.hermes/ops/bin/hermes-ops run --phase P1.B1 --risk service-change -- <command>
```

## Evidence Pack 数据结构

```text
/Users/cc/HermesArchive/hermes-new-<timestamp>/
  manifest.json
  source-inventory/
    hermes-version.txt
    official-docs-sources.md
    local-files.txt
  phases/
    P0.A0-bootstrap/
      phase-report.md
      before-state.json
      after-state.json
      commands.log
      decision.json
  ledgers/
    command-ledger.jsonl
    explicitly-not-executed.jsonl
  audit/
    ops-audit.jsonl
    ops-audit.key  # chmod 0600; do not copy to public reports
  reports/
    final-go-nogo.md
    final-validation-matrix.md
    operator-sop.md
    next-actions.md
```

## 核心模块职责

| 模块 | 职责 |
|---|---|
| `phase_gate.py` | 阶段创建、依赖检查、GO/NO-GO 判定 |
| `evidence_pack.py` | 证据包目录、manifest、phase report |
| `command_ledger.py` | 已执行与未执行命令账本 |
| `config_integrity.py` | config/env/auth/SOUL hash 和 redacted summary |
| `redaction.py` | secrets masking 与 key-only summary |
| `launchd_inspector.py` | read-only plist/domain/process/log inspection |
| `validators.py` | DeepSeek/Telegram/Feishu/Jobs/Gateway live validation |
| `audit_chain.py` | HMAC-SHA256 append-only audit chain |
| `skill_router.py` | repo-local/user/built-in skill resolution 记录 |

## 关键不变量

- Evidence first, side effects later.
- Secrets never leave their files.
- Gate failure means command is not executed.
- Every final conclusion must cite evidence pack path.
- Launchd remediation is never the first operation; inspect comes first.
