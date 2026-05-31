from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from audit_chain import verify_chain
from common import (
    ARCHIVE_HOME,
    FINAL_TASK_STATUSES,
    HERMES_HOME,
    LATEST_SYMLINK,
    OPS_REPORTS_HOME,
    assert_archive_contained,
    assert_archive_home_allowed,
    assert_archive_root_under_home,
    ensure_dir,
    now_iso,
    status_table_rows,
    truthy_env,
    write_json,
    write_text,
)
from evidence_pack import reports_path, update_manifest
from redaction import env_key_names, summarize_sensitive_file, yaml_key_names


def build_security_baseline(archive_root: Path, *, phase: str, hermes_home: Path = HERMES_HOME) -> dict[str, Any]:
    phase_root = assert_archive_contained(archive_root / "phases" / f"{phase}-security-baseline", archive_root)
    ensure_dir(phase_root)
    env_summary = summarize_sensitive_file(hermes_home / ".env")
    config_keys = yaml_key_names(hermes_home / "config.yaml")
    findings: list[dict[str, str]] = []
    if truthy_env("HERMES_YOLO_MODE"):
        findings.append({"severity": "critical", "status": "FAIL", "message": "HERMES_YOLO_MODE is enabled in the current environment"})
    else:
        findings.append({"severity": "info", "status": "PASS", "message": "HERMES_YOLO_MODE is not enabled"})
    if env_summary.get("mode") and env_summary["mode"] not in {"0o600", "0o400"}:
        findings.append({"severity": "high", "status": "FAIL", "message": f".env permissions are {env_summary['mode']}"})
    elif env_summary.get("exists"):
        findings.append({"severity": "info", "status": "PASS", "message": f".env permissions are {env_summary['mode']}"})
    else:
        findings.append({"severity": "medium", "status": "BLOCKED", "message": ".env is missing"})

    allowlist_keys = [key for key in env_key_names(hermes_home / ".env") if "ALLOW" in key.upper()]
    if allowlist_keys:
        findings.append({"severity": "info", "status": "PASS", "message": f"allowlist-related keys detected: {', '.join(allowlist_keys)}"})
    else:
        findings.append({"severity": "medium", "status": "BLOCKED", "message": "no allowlist-related key names detected"})

    destructive_keys = [key for key in config_keys if "approval" in key.lower() or "destructive" in key.lower() or "yolo" in key.lower()]
    if destructive_keys:
        findings.append({"severity": "medium", "status": "BLOCKED", "message": f"config contains review-worthy keys: {', '.join(destructive_keys)}"})
    else:
        findings.append({"severity": "info", "status": "PASS", "message": "no destructive/approval-related config keys detected"})

    overall = "PASS"
    if any(item["severity"] == "critical" and item["status"] == "FAIL" for item in findings):
        overall = "FAIL"
    elif any(item["status"] == "FAIL" for item in findings):
        overall = "FAIL"
    elif any(item["status"] == "BLOCKED" for item in findings):
        overall = "BLOCKED"

    payload = {"created_at": now_iso(), "overall": overall, "findings": findings}
    write_json(phase_root / "security-baseline.json", payload)
    lines = [
        "# Security Baseline",
        "",
        f"- Overall: `{overall}`",
        "",
        "| Severity | Status | Finding |",
        "|---|---|---|",
    ]
    for item in findings:
        lines.append(f"| {item['severity']} | {item['status']} | {item['message']} |")
    report_root = reports_path(archive_root)
    write_text(report_root / "security-baseline.md", "\n".join(lines) + "\n")
    return payload


def refresh_archive_index(archive_root: Path) -> dict[str, Any]:
    archive_home = assert_archive_home_allowed(ARCHIVE_HOME)
    archive_root = assert_archive_root_under_home(archive_root, archive_home)
    ensure_dir(OPS_REPORTS_HOME)
    if LATEST_SYMLINK.is_symlink() or LATEST_SYMLINK.exists():
        LATEST_SYMLINK.unlink()
    LATEST_SYMLINK.symlink_to(archive_root)
    archives = sorted(
        [path for path in archive_home.iterdir() if path.is_dir() and path.name.startswith("hermes-new-")],
        key=lambda item: item.name,
    )
    payload = {
        "generated_at": now_iso(),
        "latest": str(archive_root),
        "archives": [str(path) for path in archives],
    }
    write_json(archive_home / "index.json", payload)
    return payload


def generate_operator_sop(archive_root: Path, *, decision: str) -> Path:
    report_root = reports_path(archive_root)
    next_action = "- Review final validation blockers and resolve only through hermes-ops gate."
    text = f"""# Operator SOP - Hermes Ops Upgrade

## Current decision

`{decision}`

## Safe commands

```bash
/Users/cc/.hermes/ops/bin/hermes-ops status
/Users/cc/.hermes/ops/bin/hermes-ops launchd inspect --phase P0.A7
/Users/cc/.hermes/ops/bin/hermes-ops hash snapshot --phase P0.A5
/Users/cc/.hermes/ops/bin/hermes-ops audit verify
```

## Forbidden without gate

```bash
launchctl enable gui/$(id -u)/ai.hermes.gateway
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
hermes gateway start
hermes gateway stop
hermes gateway restart
hermes gateway install
```

## Logs

```bash
tail -f /Users/cc/.hermes/logs/gateway.log
```

Redact secrets before copying logs into reports.

## Rollback

- Do not delete evidence packs.
- Do not restore old Hermes code.
- Use recorded before-state and exact commands only.

## Next action

{next_action}
"""
    return write_text(report_root / "operator-sop.md", text)


def generate_next_actions(archive_root: Path, *, blocked_tasks: list[str]) -> Path:
    report_root = reports_path(archive_root)
    blockers = "\n".join(f"- {task}" for task in blocked_tasks) or "- none"
    text = f"""# Next Actions

## Immediate

- Review `/Users/cc/.hermes/docs/ai-plan/07_STATUS.md`.
- Resolve blocked live validation items only through hermes-ops gate.

## Blockers to resolve

{blockers}

## Recommended follow-up

- Re-run `hermes-ops validate live --phase P1.B2 --final` only after explicit operator approval for external checks.
- Re-run `hermes-ops report final` after blocker resolution.

## Do not do

- Do not run launchd or gateway commands outside `hermes-ops` gate.
- Do not copy `.env` into reports.
- Do not restore old Hermes scripts/config/plist.
"""
    return write_text(report_root / "next-actions.md", text)


def _load_validation_report(archive_root: Path) -> dict[str, Any]:
    path = reports_path(archive_root) / "final-validation-matrix.json"
    if not path.exists():
        return {"checks": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_security_report(archive_root: Path) -> dict[str, Any]:
    for candidate in archive_root.glob("phases/P1.B5*/security-baseline.json"):
        return json.loads(candidate.read_text(encoding="utf-8"))
    return {"overall": "BLOCKED", "findings": []}


def _load_launchd_preflight(archive_root: Path) -> dict[str, Any]:
    path = archive_root / "phases" / "P0.A7-launchd-preflight" / "launchd-preflight.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def generate_final_report(archive_root: Path) -> dict[str, Any]:
    rows = status_table_rows()
    incomplete = sorted(task_id for task_id, row in rows.items() if row["status"] not in FINAL_TASK_STATUSES)
    blocked = sorted(task_id for task_id, row in rows.items() if row["status"] in {"BLOCKED", "NO-GO"})
    completed = sorted(task_id for task_id, row in rows.items() if row["status"] == "DONE")

    validation = _load_validation_report(archive_root)
    security = _load_security_report(archive_root)
    launchd = _load_launchd_preflight(archive_root)
    audit = verify_chain(archive_root)
    manifest = json.loads((archive_root / "manifest.json").read_text(encoding="utf-8"))
    config_hashes = manifest.get("config_hashes", {})

    validation_statuses = {item["check"]: item["status"] for item in validation.get("checks", [])}
    blocked_live = any(status == "BLOCKED" for status in validation_statuses.values())
    failed_live = any(status == "FAIL" for status in validation_statuses.values())

    if incomplete or not audit.get("ok"):
        decision = "NO-GO"
    elif security.get("overall") == "FAIL" or failed_live:
        decision = "NO-GO"
    elif blocked_live:
        decision = "GO_WITH_BLOCKERS"
    else:
        decision = "GO"

    report_root = reports_path(archive_root)
    not_executed_path = archive_root / "ledgers" / "explicitly-not-executed.jsonl"
    not_executed = not_executed_path.read_text(encoding="utf-8") if not_executed_path.exists() else ""
    final_text = f"""# Final GO / NO-GO - Hermes Ops Upgrade

## Decision

`{decision}`

## Scope

- Archive: `{archive_root}`
- Generated at: `{now_iso()}`

## Completed tasks

{chr(10).join(f"- {task}" for task in completed) or "- none"}

## Blocked tasks

{chr(10).join(f"- {task}" for task in blocked) or "- none"}

## Explicitly not executed commands

```json
{not_executed.strip() or "[]"}
```

## Config hash summary

```json
{json.dumps(config_hashes, indent=2)}
```

## Launchd preflight summary

```json
{json.dumps(launchd, indent=2)}
```

## Live validation summary

```json
{json.dumps(validation_statuses, indent=2)}
```

## Security baseline summary

```json
{json.dumps(security, indent=2)}
```

## Audit verify result

```json
{json.dumps(audit, indent=2)}
```

## Residual risks

- External live checks remain blocked unless explicitly approved.
- No side-effectful launchd or gateway mutation was executed during this run.

## Next actions

- Re-run final live validation only after explicit operator approval for external actions.
- Use `hermes-ops run --phase P1.B1 --risk service-change --dry-run -- <command>` before any remediation.
"""
    write_text(report_root / "final-go-nogo.md", final_text)
    generate_operator_sop(archive_root, decision=decision)
    generate_next_actions(archive_root, blocked_tasks=blocked)
    update_manifest(archive_root, decision=decision)
    return {"decision": decision, "incomplete": incomplete, "blocked": blocked, "completed": completed}
