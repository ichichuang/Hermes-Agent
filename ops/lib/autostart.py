from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Sequence

from audit_chain import verify_chain
from command_ledger import record_command, record_not_executed
from common import (
    DEFAULT_HERMES_LABEL,
    HERMES_HOME,
    now_iso,
    read_json,
    run_subprocess,
    shell_join,
    write_json,
    write_text,
)
from evidence_pack import ensure_phase, reports_path, update_manifest
from launchd_inspector import inspect_launchd
from phase_gate import evaluate_gate
from redaction import redact_text

D6_BASELINE_FILE = "D6-autostart-baseline.json"
D6_POST_REBOOT_FILE = "D6-post-reboot-validation-result.json"


def _check(
    name: str,
    expected: str,
    actual: str,
    status: str,
    evidence: str,
    *,
    required: bool = True,
) -> dict[str, Any]:
    return {
        "check": name,
        "expected": expected,
        "actual": actual,
        "status": status,
        "evidence": evidence,
        "required": required,
    }


def _gateway_status(phase_root: Path) -> dict[str, Any]:
    result = run_subprocess(["hermes", "gateway", "status"])
    output_path = phase_root / "gateway-status.redacted.txt"
    combined = redact_text(result.stdout + result.stderr)
    write_text(output_path, combined + ("\n" if combined else ""))
    text = combined.lower()
    if result.returncode != 0:
        status = "BLOCKED"
        actual = "gateway status command unavailable"
    elif "running" in text or "healthy" in text or ("gateway service is loaded" in text and "pid" in text):
        status = "PASS"
        actual = "gateway running"
    elif "stopped" in text or "not running" in text or "not loaded" in text or "has not loaded" in text:
        status = "FAIL"
        actual = "gateway not loaded"
    else:
        status = "BLOCKED"
        actual = "gateway state unclear"
    return {
        "status": status,
        "actual": actual,
        "exit_code": result.returncode,
        "output_path": str(output_path),
    }


def _boot_time() -> dict[str, Any]:
    result = run_subprocess(["/usr/sbin/sysctl", "-n", "kern.boottime"])
    text = (result.stdout + result.stderr).strip()
    match = re.search(r"sec\s*=\s*(\d+)", text)
    return {
        "exit_code": result.returncode,
        "raw_redacted": redact_text(text),
        "sec": int(match.group(1)) if match else None,
    }


def _load_or_create_boot_baseline(archive_root: Path, current_boot: dict[str, Any]) -> dict[str, Any]:
    report_root = reports_path(archive_root)
    path = report_root / D6_BASELINE_FILE
    existing = read_json(path, default=None)
    if isinstance(existing, dict) and existing.get("boot_time_sec"):
        return existing
    payload = {
        "created_at": now_iso(),
        "boot_time_sec": current_boot.get("sec"),
        "boot_time_raw_redacted": current_boot.get("raw_redacted"),
    }
    write_json(path, payload)
    return payload


def _load_latest_redaction_scan(archive_root: Path) -> dict[str, Any] | None:
    candidates = sorted((archive_root / "phases").glob("D6*/redaction-scan.json"))
    if not candidates:
        return None
    return read_json(candidates[-1], default=None)


def _overall_status(checks: list[dict[str, Any]]) -> str:
    required = [item for item in checks if item.get("required", True)]
    statuses = [str(item.get("status")) for item in required]
    if statuses and all(status == "PASS" for status in statuses):
        return "PASS"
    if any(status == "FAIL" for status in statuses):
        return "FAIL"
    if any(status == "BLOCKED" for status in statuses):
        return "BLOCKED"
    return "NOT_APPLICABLE"


def build_autostart_assessment(
    archive_root: Path,
    *,
    phase: str = "D6.B",
    write_reports: bool = False,
) -> dict[str, Any]:
    phase_root = ensure_phase(archive_root, phase)
    launchd = inspect_launchd(archive_root, phase=phase)
    plist = launchd.get("plist", {})
    domains = launchd.get("domains", {})
    gui = domains.get("gui", {})
    user = domains.get("user", {})
    gui_state = str(gui.get("parsed", {}).get("state") or "")
    user_present = user.get("exit_code") == 0
    gateway = _gateway_status(phase_root)
    audit = verify_chain(archive_root)
    boot = _boot_time()
    boot_baseline = _load_or_create_boot_baseline(archive_root, boot)
    post_reboot_observed = bool(
        boot.get("sec") and boot_baseline.get("boot_time_sec") and boot.get("sec") != boot_baseline.get("boot_time_sec")
    )

    checks = [
        _check(
            "LaunchAgent plist exists",
            f"{Path.home()}/Library/LaunchAgents/{DEFAULT_HERMES_LABEL}.plist",
            "exists" if plist.get("exists") else "missing",
            "PASS" if plist.get("exists") else "FAIL",
            str(phase_root / "plist-summary.json"),
        ),
        _check(
            "LaunchAgent plist SHA256",
            "recorded",
            str(plist.get("sha256") or "missing"),
            "PASS" if plist.get("sha256") else "FAIL",
            str(phase_root / "plist-summary.json"),
        ),
        _check(
            "LaunchAgent label",
            DEFAULT_HERMES_LABEL,
            str(plist.get("label") or "missing"),
            "PASS" if plist.get("label") == DEFAULT_HERMES_LABEL else "FAIL",
            str(phase_root / "plist-summary.json"),
        ),
        _check(
            "HERMES_HOME",
            str(HERMES_HOME),
            str(plist.get("environment", {}).get("HERMES_HOME") or "missing"),
            "PASS" if plist.get("environment_checks", {}).get("HERMES_HOME_matches") else "FAIL",
            str(phase_root / "plist-summary.json"),
        ),
        _check(
            "PATH environment",
            "present",
            "present" if plist.get("environment_checks", {}).get("PATH_present") else "missing",
            "PASS" if plist.get("environment_checks", {}).get("PATH_present") else "FAIL",
            str(phase_root / "plist-summary.json"),
        ),
        _check(
            "VIRTUAL_ENV environment",
            "present for official virtualenv LaunchAgent",
            "present" if plist.get("environment_checks", {}).get("VIRTUAL_ENV_present") else "missing",
            "PASS" if plist.get("environment_checks", {}).get("VIRTUAL_ENV_present") else "FAIL",
            str(phase_root / "plist-summary.json"),
        ),
        _check(
            "gui launchd service loaded",
            f"gui/{os.getuid()}/{DEFAULT_HERMES_LABEL} loaded and running",
            f"exit={gui.get('exit_code')} state={gui_state or '-'}",
            "PASS" if gui.get("exit_code") == 0 and gui_state == "running" else "FAIL",
            str(phase_root / "launchctl-print-gui.txt"),
        ),
        _check(
            "user launchd service presence recorded",
            "present or absent recorded",
            "present" if user_present else "absent",
            "PASS",
            str(phase_root / "launchctl-print-user.txt"),
            required=False,
        ),
        _check(
            "Gateway process count",
            "1",
            str(launchd.get("processes", {}).get("count")),
            "PASS" if launchd.get("processes", {}).get("count") == 1 else "FAIL",
            str(phase_root / "process-list.txt"),
        ),
        _check(
            "Gateway status",
            "PASS",
            gateway["actual"],
            gateway["status"],
            gateway["output_path"],
        ),
        _check(
            "Audit chain verify",
            "PASS",
            f"ok={audit.get('ok')} checked={audit.get('checked')}",
            "PASS" if audit.get("ok") else "FAIL",
            str(archive_root / "audit" / "audit-verify.json"),
        ),
    ]

    overall = _overall_status(checks)
    post_reboot_status = "POST_REBOOT_GO" if post_reboot_observed and overall == "PASS" else "PENDING_OPERATOR_REBOOT"
    payload = {
        "created_at": now_iso(),
        "phase": phase,
        "overall": overall,
        "current_baseline_decision": "D6_CURRENT_BASELINE_GO" if overall == "PASS" else f"D6_CURRENT_BASELINE_{overall}",
        "post_reboot_validation": post_reboot_status,
        "post_reboot_observed": post_reboot_observed,
        "boot_time": boot,
        "boot_baseline": boot_baseline,
        "launchd": launchd,
        "gateway_status": gateway,
        "audit": audit,
        "checks": checks,
    }
    write_json(phase_root / "autostart-assessment.json", payload)
    _append_reboot_result(archive_root, payload)
    if write_reports:
        write_autostart_reports(archive_root, payload)
    return payload


def _append_reboot_result(archive_root: Path, assessment: dict[str, Any]) -> None:
    report_root = reports_path(archive_root)
    result_path = report_root / D6_POST_REBOOT_FILE
    if not assessment.get("post_reboot_observed"):
        return
    write_json(
        result_path,
        {
            "created_at": assessment["created_at"],
            "post_reboot_validation": assessment["post_reboot_validation"],
            "overall": assessment["overall"],
            "boot_time_sec": assessment.get("boot_time", {}).get("sec"),
            "baseline_boot_time_sec": assessment.get("boot_baseline", {}).get("boot_time_sec"),
            "evidence": str(archive_root / "phases" / "D6.B-autostart-capability" / "autostart-assessment.json"),
        },
    )


def _report_redaction_status(archive_root: Path) -> dict[str, Any]:
    scan = _load_latest_redaction_scan(archive_root)
    if not scan:
        return {"status": "PENDING", "evidence": "redaction scan not run yet"}
    return {
        "status": scan.get("status", "BLOCKED"),
        "finding_count": scan.get("finding_count"),
        "evidence": str(archive_root / "phases" / "D6.F-post-autostart-validation" / "redaction-scan.json"),
    }


def write_autostart_reports(archive_root: Path, assessment: dict[str, Any] | None = None) -> dict[str, Any]:
    assessment = assessment or build_autostart_assessment(archive_root, phase="D6.E", write_reports=False)
    report_root = reports_path(archive_root)
    redaction = _report_redaction_status(archive_root)
    redaction_pass = redaction.get("status") == "PASS"
    current_decision = "D6_CURRENT_BASELINE_GO" if assessment["overall"] == "PASS" and redaction_pass else assessment["current_baseline_decision"]
    if assessment["overall"] == "PASS" and not redaction_pass:
        current_decision = "D6_CURRENT_BASELINE_PENDING_REDACTION_SCAN"

    matrix_lines = [
        "# D6 Autostart Validation Matrix",
        "",
        f"Generated at: `{now_iso()}`",
        "",
        "| Check | Expected | Actual | Status | Evidence |",
        "|---|---|---|---|---|",
    ]
    for item in assessment["checks"]:
        matrix_lines.append(
            f"| {item['check']} | {item['expected']} | {item['actual']} | {item['status']} | `{item['evidence']}` |"
        )
    matrix_lines.append(
        f"| D6 redaction scan | PASS | findings={redaction.get('finding_count', '-')} | {redaction.get('status')} | `{redaction.get('evidence')}` |"
    )
    write_text(report_root / "D6-autostart-validation-matrix.md", "\n".join(matrix_lines) + "\n")

    instructions = """# D6 Reboot Autostart Validation Instructions

## Operator Steps

1. Reboot the Mac.
2. Log in as user `cc`.
3. Run:

```bash
/Users/cc/.hermes/ops/bin/hermes-ops autostart verify
```

4. Confirm:
   - launchd service loaded
   - gateway process count = 1
   - gateway status PASS
   - audit verify PASS
5. If PASS, append the result to the D6 report. The `autostart verify` command also records the observed boot time and post-reboot result in the archive.
6. If FAIL, do not run raw `launchctl`; run the gated hermes-ops remediation path:

```bash
/Users/cc/.hermes/ops/bin/hermes-ops autostart remediate --phase D6.C --action install
/Users/cc/.hermes/ops/bin/hermes-ops autostart remediate --phase D6.C --action bootstrap
/Users/cc/.hermes/ops/bin/hermes-ops autostart remediate --phase D6.C --action start
```

Add `--execute` only after the D6 phase gate explicitly approves the exact action.
"""
    write_text(report_root / "D6-reboot-autostart-validation-instructions.md", instructions)

    final_lines = [
        "# D6 Autostart Final",
        "",
        f"Generated at: `{now_iso()}`",
        "",
        "## Decision",
        "",
        f"- Current baseline: `{current_decision}`",
        f"- Post-reboot validation: `{assessment['post_reboot_validation']}`",
        "",
        "## Scope",
        "",
        "- Preserve official Hermes macOS LaunchAgent behavior after Mac reboot and user login.",
        "- Do not create a custom root LaunchDaemon.",
        "- Do not modify `/Users/cc/.hermes/config.yaml` or `/Users/cc/.hermes/.env`.",
        "- Do not perform external provider or Telegram live validation in D6.",
        "",
        "## Required Evidence",
        "",
        f"- Autostart assessment: `{archive_root / 'phases' / 'D6.B-autostart-capability' / 'autostart-assessment.json'}`",
        f"- Validation matrix: `{report_root / 'D6-autostart-validation-matrix.md'}`",
        f"- Reboot instructions: `{report_root / 'D6-reboot-autostart-validation-instructions.md'}`",
        f"- Redaction scan: `{redaction.get('evidence')}`",
        "",
        "## Post-Reboot Rule",
        "",
        "`POST_REBOOT_GO` is not allowed until the operator actually reboots, logs in as `cc`, and `hermes-ops autostart verify` passes after the new boot time is observed.",
        "",
    ]
    write_text(report_root / "D6-autostart-final.md", "\n".join(final_lines))

    next_actions = """# D6 Next Actions

## Immediate

- Reboot the Mac when ready.
- Log in as `cc`.
- Run `/Users/cc/.hermes/ops/bin/hermes-ops autostart verify`.

## If PASS

- Treat post-reboot autostart as verified.
- Preserve the D5 production baseline and D6 evidence pack.

## If FAIL

- Do not run raw `launchctl`.
- Do not run raw `hermes gateway install/start/stop/restart`.
- Use `/Users/cc/.hermes/ops/bin/hermes-ops autostart remediate --phase D6.C --action <install|bootstrap|start>` and add `--execute` only after gate approval.
"""
    write_text(report_root / "D6-next-actions.md", next_actions)

    update_manifest(
        archive_root,
        d6_decision=current_decision,
        d6_post_reboot_validation=assessment["post_reboot_validation"],
        d6_autostart_report=str(report_root / "D6-autostart-final.md"),
    )
    return {
        "current_decision": current_decision,
        "post_reboot_validation": assessment["post_reboot_validation"],
        "report": str(report_root / "D6-autostart-final.md"),
        "matrix": str(report_root / "D6-autostart-validation-matrix.md"),
        "instructions": str(report_root / "D6-reboot-autostart-validation-instructions.md"),
        "next_actions": str(report_root / "D6-next-actions.md"),
    }


def remediation_command(action: str) -> list[str]:
    uid = os.getuid()
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{DEFAULT_HERMES_LABEL}.plist"
    commands = {
        "install": ["hermes", "gateway", "install"],
        "bootstrap": ["/bin/launchctl", "bootstrap", f"gui/{uid}", str(plist_path)],
        "start": ["hermes", "gateway", "start"],
    }
    if action not in commands:
        raise ValueError(f"Unsupported remediation action: {action}")
    return commands[action]


def run_gated_remediation(
    archive_root: Path,
    *,
    phase: str,
    action: str,
    execute: bool = False,
) -> dict[str, Any]:
    phase_root = ensure_phase(archive_root, phase)
    command = remediation_command(action)
    command_text = shell_join(command)
    gate = evaluate_gate(archive_root, phase=phase, command=command, risk="service-change")
    gate_path = phase_root / "gate-decision.json"
    write_json(phase_root / f"gate-decision-{action}.json", gate)
    write_text(phase_root / "exact-command.txt", command_text + "\n")
    write_text(phase_root / f"exact-command-{action}.txt", command_text + "\n")
    if not execute:
        record_not_executed(
            archive_root,
            phase=phase,
            risk="service-change",
            command=command_text,
            reason="D6 remediation dry-run; --execute not provided",
            evidence_path=gate_path,
        )
        return {"decision": "NOT_EXECUTED", "reason": "dry-run", "gate": gate, "command": command_text}
    if gate["decision"] != "GO":
        record_not_executed(
            archive_root,
            phase=phase,
            risk="service-change",
            command=command_text,
            reason="D6 remediation gate denied execution",
            evidence_path=gate_path,
        )
        return {"decision": "NOT_EXECUTED", "reason": "gate denied", "gate": gate, "command": command_text}

    result = run_subprocess(command)
    stdout_path = phase_root / f"{action}.stdout.redacted.txt"
    stderr_path = phase_root / f"{action}.stderr.redacted.txt"
    write_text(stdout_path, redact_text(result.stdout))
    write_text(stderr_path, redact_text(result.stderr))
    record_command(
        archive_root,
        phase=phase,
        risk="service-change",
        command=command_text,
        decision="EXECUTED",
        exit_code=result.returncode,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    return {
        "decision": "EXECUTED",
        "command": command_text,
        "exit_code": result.returncode,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }
