from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from autostart import build_autostart_assessment, run_gated_remediation, write_autostart_reports
from audit_chain import append_event, verify_chain
from command_ledger import list_ledgers, record_command, record_not_executed
from common import HERMES_HOME, now_iso, run_subprocess, shell_join, write_text
from config_integrity import snapshot
from evidence_pack import create_archive, ensure_phase, get_active_archive, phase_path
from launchd_inspector import inspect_launchd
from phase_gate import active_archive_or_raise, evaluate_gate, is_read_only_command
from redaction import redact_text, scan_evidence_for_sensitive_values
from reporting import build_security_baseline, generate_final_report, generate_operator_sop, refresh_archive_index
from skill_router import record_resolution
from validators import validate_live


def _archive(create: bool = False) -> Path:
    archive_root = get_active_archive(create=create)
    if archive_root is None:
        raise SystemExit("No active archive found.")
    return archive_root


def cmd_status(_: argparse.Namespace) -> int:
    archive_root = get_active_archive(create=False)
    payload = {
        "timestamp": now_iso(),
        "hermes_home": str(HERMES_HOME),
        "active_archive": str(archive_root) if archive_root else None,
        "archive_exists": archive_root.exists() if archive_root else False,
        "config_snapshot": bool((archive_root / "manifest.json").exists()) if archive_root else False,
        "launchd_preflight": bool(list((archive_root / "phases").glob("*/launchd-preflight.json"))) if archive_root else False,
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_phase_start(args: argparse.Namespace) -> int:
    archive_root = _archive(create=True)
    phase_root = ensure_phase(archive_root, args.phase, dry_run=args.dry_run)
    payload = {"archive_root": str(archive_root), "phase": args.phase, "phase_root": str(phase_root), "dry_run": args.dry_run}
    print(json.dumps(payload, indent=2))
    return 0


def cmd_phase_gate(args: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    ensure_phase(archive_root, args.phase)
    payload = evaluate_gate(archive_root, phase=args.phase)
    print(json.dumps(payload, indent=2))
    return 0 if payload["decision"] == "GO" else 1


def cmd_hash_snapshot(args: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = snapshot(archive_root, args.phase)
    print(json.dumps(result["summary"], indent=2))
    return 0


def cmd_launchd_inspect(args: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = inspect_launchd(archive_root, phase=args.phase)
    print(json.dumps(result, indent=2))
    return 0


def _command_output_paths(phase_root: Path, command_text: str) -> tuple[Path, Path]:
    stamp = now_iso().replace(":", "").replace("+", "_")
    safe_name = command_text.replace("/", "_").replace(" ", "_")[:60]
    return (
        phase_root / f"{stamp}-{safe_name}.stdout.txt",
        phase_root / f"{stamp}-{safe_name}.stderr.txt",
    )


def cmd_run(args: argparse.Namespace) -> int:
    if not args.command_args:
        raise SystemExit("Missing command after `--`.")
    archive_root = active_archive_or_raise()
    phase_root = ensure_phase(archive_root, args.phase)
    gate = evaluate_gate(archive_root, phase=args.phase, command=args.command_args, risk=args.risk)
    command_text = shell_join(args.command_args)
    stdout_path, stderr_path = _command_output_paths(phase_root, command_text)

    if args.dry_run:
        write_text(stdout_path, "")
        write_text(stderr_path, "")
        if gate["decision"] != "GO" or not is_read_only_command(args.command_args):
            record_not_executed(
                archive_root,
                phase=args.phase,
                risk=args.risk,
                command=command_text,
                reason="dry-run: command withheld by hard-stop or non-read-only policy",
                evidence_path=phase_root / "gate-decision.json",
            )
            print(json.dumps({"decision": "NOT_EXECUTED", "reason": "dry-run withheld", "gate": gate}, indent=2))
            return 0
        record_command(
            archive_root,
            phase=args.phase,
            risk=args.risk,
            command=command_text,
            decision="DRY_RUN",
            exit_code=0,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            notes="dry-run only; command not executed",
        )
        print(json.dumps({"decision": "DRY_RUN", "gate": gate}, indent=2))
        return 0

    if gate["decision"] != "GO":
        record_not_executed(
            archive_root,
            phase=args.phase,
            risk=args.risk,
            command=command_text,
            reason="gate denied execution",
            evidence_path=phase_root / "gate-decision.json",
        )
        print(json.dumps({"decision": "NOT_EXECUTED", "gate": gate}, indent=2))
        return 1

    result = run_subprocess(args.command_args)
    write_text(stdout_path, redact_text(result.stdout))
    write_text(stderr_path, redact_text(result.stderr))
    record_command(
        archive_root,
        phase=args.phase,
        risk=args.risk,
        command=command_text,
        decision="EXECUTED",
        exit_code=result.returncode,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    print(
        json.dumps(
            {
                "decision": "EXECUTED",
                "command": command_text,
                "exit_code": result.returncode,
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
            },
            indent=2,
        )
    )
    return result.returncode


def cmd_ledger_list(_: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    print(json.dumps(list_ledgers(archive_root), indent=2))
    return 0


def cmd_validate_live(args: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = validate_live(
        archive_root,
        phase=args.phase,
        dry_run=args.dry_run,
        final=args.final,
        allow_external=args.allow_external,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_audit_append(args: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    event = append_event(archive_root, phase=args.phase, event=args.event)
    print(json.dumps(event, indent=2))
    return 0


def cmd_audit_verify(_: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = verify_chain(archive_root)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def cmd_sop_generate(_: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    final_report = archive_root / "reports" / "final-go-nogo.md"
    decision = "PENDING"
    if final_report.exists():
        for line in final_report.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("`") and line.strip().endswith("`"):
                decision = line.strip().strip("`")
                break
    path = generate_operator_sop(archive_root, decision=decision)
    print(json.dumps({"path": str(path), "decision": decision}, indent=2))
    return 0


def cmd_security_baseline(args: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = build_security_baseline(archive_root, phase=args.phase)
    print(json.dumps(result, indent=2))
    return 0 if result.get("overall") != "FAIL" else 1


def cmd_security_scan_evidence(args: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = scan_evidence_for_sensitive_values(
        archive_root,
        phase=args.phase,
        scope_prefix=args.scope_prefix,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "PASS" else 1


def cmd_archive_refresh(_: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = refresh_archive_index(archive_root)
    print(json.dumps(result, indent=2))
    return 0


def cmd_skill_resolve(args: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = record_resolution(archive_root, phase=args.phase, skill_name=args.skill_name)
    print(json.dumps(result, indent=2))
    return 0


def cmd_report_final(_: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = generate_final_report(archive_root)
    print(json.dumps(result, indent=2))
    return 0 if result["decision"] != "NO-GO" else 1


def cmd_autostart_status(args: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = build_autostart_assessment(archive_root, phase=args.phase, write_reports=False)
    print(
        json.dumps(
            {
                "overall": result["overall"],
                "current_baseline_decision": result["current_baseline_decision"],
                "post_reboot_validation": result["post_reboot_validation"],
                "evidence": str(phase_path(archive_root, args.phase) / "autostart-assessment.json"),
            },
            indent=2,
        )
    )
    return 0


def cmd_autostart_verify(args: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = build_autostart_assessment(archive_root, phase=args.phase, write_reports=True)
    print(json.dumps({"overall": result["overall"], "post_reboot_validation": result["post_reboot_validation"]}, indent=2))
    return 0 if result["overall"] == "PASS" else 1


def cmd_autostart_report(args: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = build_autostart_assessment(archive_root, phase=args.phase, write_reports=False)
    report = write_autostart_reports(archive_root, result)
    print(json.dumps(report, indent=2))
    return 0 if report["current_decision"] in {"D6_CURRENT_BASELINE_GO", "D6_CURRENT_BASELINE_PENDING_REDACTION_SCAN"} else 1


def cmd_autostart_remediate(args: argparse.Namespace) -> int:
    archive_root = active_archive_or_raise()
    result = run_gated_remediation(archive_root, phase=args.phase, action=args.action, execute=args.execute)
    print(json.dumps(result, indent=2))
    if result["decision"] == "EXECUTED":
        return int(result.get("exit_code", 1))
    return 0 if not args.execute else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-ops")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status")
    status_parser.set_defaults(func=cmd_status)

    phase_parser = subparsers.add_parser("phase")
    phase_subparsers = phase_parser.add_subparsers(dest="phase_command", required=True)
    phase_start = phase_subparsers.add_parser("start")
    phase_start.add_argument("phase")
    phase_start.add_argument("--dry-run", action="store_true")
    phase_start.set_defaults(func=cmd_phase_start)
    phase_gate = phase_subparsers.add_parser("gate")
    phase_gate.add_argument("phase")
    phase_gate.set_defaults(func=cmd_phase_gate)

    gate_parser = subparsers.add_parser("gate")
    gate_subparsers = gate_parser.add_subparsers(dest="gate_command", required=True)
    gate_check = gate_subparsers.add_parser("check")
    gate_check.add_argument("--phase", required=True)
    gate_check.set_defaults(func=cmd_phase_gate)

    hash_parser = subparsers.add_parser("hash")
    hash_subparsers = hash_parser.add_subparsers(dest="hash_command", required=True)
    hash_snapshot = hash_subparsers.add_parser("snapshot")
    hash_snapshot.add_argument("--phase", required=True)
    hash_snapshot.set_defaults(func=cmd_hash_snapshot)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--phase", required=True)
    run_parser.add_argument("--risk", required=True)
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("command_args", nargs=argparse.REMAINDER)
    run_parser.set_defaults(func=cmd_run)

    ledger_parser = subparsers.add_parser("ledger")
    ledger_subparsers = ledger_parser.add_subparsers(dest="ledger_command", required=True)
    ledger_list = ledger_subparsers.add_parser("list")
    ledger_list.set_defaults(func=cmd_ledger_list)

    launchd_parser = subparsers.add_parser("launchd")
    launchd_subparsers = launchd_parser.add_subparsers(dest="launchd_command", required=True)
    launchd_inspect = launchd_subparsers.add_parser("inspect")
    launchd_inspect.add_argument("--phase", required=True)
    launchd_inspect.set_defaults(func=cmd_launchd_inspect)

    validate_parser = subparsers.add_parser("validate")
    validate_subparsers = validate_parser.add_subparsers(dest="validate_command", required=True)
    validate_live_parser = validate_subparsers.add_parser("live")
    validate_live_parser.add_argument("--phase", required=False, default="P1.B2")
    validate_live_parser.add_argument("--dry-run", action="store_true")
    validate_live_parser.add_argument("--final", action="store_true")
    validate_live_parser.add_argument("--allow-external", action="store_true")
    validate_live_parser.set_defaults(func=cmd_validate_live)

    audit_parser = subparsers.add_parser("audit")
    audit_subparsers = audit_parser.add_subparsers(dest="audit_command", required=True)
    audit_append = audit_subparsers.add_parser("append")
    audit_append.add_argument("--phase", required=True)
    audit_append.add_argument("--event", required=True)
    audit_append.set_defaults(func=cmd_audit_append)
    audit_verify = audit_subparsers.add_parser("verify")
    audit_verify.set_defaults(func=cmd_audit_verify)

    sop_parser = subparsers.add_parser("sop")
    sop_subparsers = sop_parser.add_subparsers(dest="sop_command", required=True)
    sop_generate = sop_subparsers.add_parser("generate")
    sop_generate.set_defaults(func=cmd_sop_generate)

    security_parser = subparsers.add_parser("security")
    security_subparsers = security_parser.add_subparsers(dest="security_command", required=True)
    security_baseline = security_subparsers.add_parser("baseline")
    security_baseline.add_argument("--phase", required=False, default="P1.B5")
    security_baseline.set_defaults(func=cmd_security_baseline)
    security_scan = security_subparsers.add_parser("scan-evidence")
    security_scan.add_argument("--phase", required=True)
    security_scan.add_argument("--scope-prefix", required=False, default="D5")
    security_scan.set_defaults(func=cmd_security_scan_evidence)

    archive_parser = subparsers.add_parser("archive")
    archive_subparsers = archive_parser.add_subparsers(dest="archive_command", required=True)
    archive_refresh = archive_subparsers.add_parser("refresh")
    archive_refresh.set_defaults(func=cmd_archive_refresh)

    skill_parser = subparsers.add_parser("skill")
    skill_subparsers = skill_parser.add_subparsers(dest="skill_command", required=True)
    skill_resolve = skill_subparsers.add_parser("resolve")
    skill_resolve.add_argument("skill_name")
    skill_resolve.add_argument("--phase", required=False, default="P2.C1")
    skill_resolve.set_defaults(func=cmd_skill_resolve)

    report_parser = subparsers.add_parser("report")
    report_subparsers = report_parser.add_subparsers(dest="report_command", required=True)
    report_final = report_subparsers.add_parser("final")
    report_final.set_defaults(func=cmd_report_final)

    autostart_parser = subparsers.add_parser("autostart")
    autostart_subparsers = autostart_parser.add_subparsers(dest="autostart_command", required=True)
    autostart_status = autostart_subparsers.add_parser("status")
    autostart_status.add_argument("--phase", required=False, default="D6.B")
    autostart_status.set_defaults(func=cmd_autostart_status)
    autostart_verify = autostart_subparsers.add_parser("verify")
    autostart_verify.add_argument("--phase", required=False, default="D6.B")
    autostart_verify.set_defaults(func=cmd_autostart_verify)
    autostart_report = autostart_subparsers.add_parser("report")
    autostart_report.add_argument("--phase", required=False, default="D6.E")
    autostart_report.set_defaults(func=cmd_autostart_report)
    autostart_remediate = autostart_subparsers.add_parser("remediate")
    autostart_remediate.add_argument("--phase", required=False, default="D6.C")
    autostart_remediate.add_argument("--action", choices=["install", "bootstrap", "start"], required=True)
    autostart_remediate.add_argument("--execute", action="store_true")
    autostart_remediate.set_defaults(func=cmd_autostart_remediate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "command_args", None) and args.command_args[0] == "--":
        args.command_args = args.command_args[1:]
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
