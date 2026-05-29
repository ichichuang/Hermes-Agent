from __future__ import annotations

import os
import plistlib
import re
from pathlib import Path
from typing import Any

from common import (
    DEFAULT_HERMES_LABEL,
    HERMES_HOME,
    file_mode,
    mtime_iso,
    now_iso,
    run_subprocess,
    sha256_file,
    write_json,
    write_text,
)
from evidence_pack import ensure_phase
from redaction import redacted_tail, redact_text

FIELD_PATTERNS = {
    "state": re.compile(r"state = ([A-Za-z0-9_-]+)"),
    "last_exit_code": re.compile(r"last exit code = (-?\d+)"),
    "runs": re.compile(r"runs = (\d+)"),
    "pid": re.compile(r"pid = (\d+)"),
    "throttle_interval": re.compile(r"throttle interval = (\d+)"),
}


def summarize_plist(plist_payload: dict[str, Any]) -> dict[str, Any]:
    env = plist_payload.get("EnvironmentVariables") or {}
    hermes_home_value = env.get("HERMES_HOME")
    return {
        "label": plist_payload.get("Label"),
        "program_arguments": plist_payload.get("ProgramArguments") or [],
        "working_directory": plist_payload.get("WorkingDirectory"),
        "run_at_load": plist_payload.get("RunAtLoad"),
        "keep_alive": plist_payload.get("KeepAlive"),
        "standard_out_path": plist_payload.get("StandardOutPath"),
        "standard_error_path": plist_payload.get("StandardErrorPath"),
        "environment": {
            "PATH": env.get("PATH"),
            "VIRTUAL_ENV": env.get("VIRTUAL_ENV"),
            "HERMES_HOME": hermes_home_value,
        },
        "environment_key_names": sorted(env.keys()),
        "environment_checks": {
            "HERMES_HOME_expected": str(HERMES_HOME),
            "HERMES_HOME_matches": hermes_home_value == str(HERMES_HOME),
            "PATH_present": bool(env.get("PATH")),
            "VIRTUAL_ENV_present": bool(env.get("VIRTUAL_ENV")),
        },
    }


def parse_launchctl_output(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for name, pattern in FIELD_PATTERNS.items():
        match = pattern.search(text)
        if match:
            parsed[name] = match.group(1)
    return parsed


def detect_gateway_processes(ps_output: str) -> list[str]:
    lines: list[str] = []
    for line in ps_output.splitlines():
        lowered = line.lower()
        if "hermes-ops" in lowered or "gateway status" in lowered or "launchctl print" in lowered:
            continue
        if (
            ("hermes_cli.main" in lowered and "gateway run" in lowered)
            or "hermes gateway run" in lowered
            or "hermes gateway start" in lowered
            or DEFAULT_HERMES_LABEL in lowered
        ):
            lines.append(line)
    return lines


def find_gateway_plists(label: str = DEFAULT_HERMES_LABEL) -> dict[str, Any]:
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    canonical = launch_agents / f"{label}.plist"
    matches = sorted(launch_agents.glob(f"{label}*.plist*")) if launch_agents.exists() else []
    return {
        "search_root": str(launch_agents),
        "canonical": str(canonical),
        "matches": [str(path) for path in matches],
        "competing": [str(path) for path in matches if path != canonical],
    }


def inspect_launchd(
    archive_root: Path,
    *,
    phase: str,
    hermes_home: Path = HERMES_HOME,
    label: str = DEFAULT_HERMES_LABEL,
) -> dict[str, Any]:
    phase_root = ensure_phase(archive_root, phase)
    uid = os.getuid()
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    log_path = hermes_home / "logs" / "gateway.log"
    plist_payload: dict[str, Any] = {}
    plist_summary: dict[str, Any] = {
        "exists": plist_path.exists(),
        "path": str(plist_path),
        "mode": file_mode(plist_path),
        "mtime": mtime_iso(plist_path),
        "sha256": sha256_file(plist_path),
    }
    if plist_path.exists():
        with plist_path.open("rb") as handle:
            plist_payload = plistlib.load(handle)
        plist_summary.update(summarize_plist(plist_payload))
    write_json(phase_root / "plist-summary.json", plist_summary)
    plist_matches = find_gateway_plists(label)
    write_json(phase_root / "competing-plists.json", plist_matches)

    domain_results: dict[str, Any] = {}
    for domain in ("gui", "user"):
        service = f"{domain}/{uid}/{label}"
        result = run_subprocess(["/bin/launchctl", "print", service])
        combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
        text_path = phase_root / f"launchctl-print-{domain}.txt"
        write_text(text_path, redact_text(combined) + ("\n" if combined else ""))
        domain_results[domain] = {
            "service": service,
            "exit_code": result.returncode,
            "parsed": parse_launchctl_output(combined),
            "output_path": str(text_path),
        }

    ps_result = run_subprocess(["/bin/ps", "-axo", "pid,ppid,command"])
    processes = detect_gateway_processes(ps_result.stdout)
    process_path = phase_root / "process-list.txt"
    write_text(process_path, ("\n".join(processes) + "\n") if processes else "")

    redacted_log = redacted_tail(log_path, lines=100)
    log_tail_path = phase_root / "gateway-log-tail.redacted.txt"
    write_text(log_tail_path, redacted_log + ("\n" if redacted_log else ""))

    summary = {
        "created_at": now_iso(),
        "uid": uid,
        "label": label,
        "plist": plist_summary,
        "plist_search": plist_matches,
        "domains": domain_results,
        "processes": {
            "count": len(processes),
            "duplicate_gateway_processes": len(processes) > 1,
            "path": str(process_path),
        },
        "log_tail_path": str(log_tail_path),
    }
    write_json(phase_root / "launchd-preflight.json", summary)

    md_lines = [
        "# Launchd Preflight",
        "",
        f"- Created at: `{summary['created_at']}`",
        f"- UID: `{uid}`",
        f"- Label: `{label}`",
        f"- Plist exists: `{plist_summary['exists']}`",
        f"- Plist SHA256: `{plist_summary.get('sha256')}`",
        f"- WorkingDirectory: `{plist_summary.get('working_directory')}`",
        f"- HERMES_HOME in plist: `{plist_summary.get('environment', {}).get('HERMES_HOME')}`",
        f"- HERMES_HOME matches expected: `{plist_summary.get('environment_checks', {}).get('HERMES_HOME_matches')}`",
        f"- PATH present: `{plist_summary.get('environment_checks', {}).get('PATH_present')}`",
        f"- VIRTUAL_ENV present: `{plist_summary.get('environment_checks', {}).get('VIRTUAL_ENV_present')}`",
        f"- Competing plist count: `{len(plist_matches['competing'])}`",
        "",
        "| Domain | Service | Exit code | State | Runs | Last exit code |",
        "|---|---|---:|---|---:|---:|",
    ]
    for domain, payload in domain_results.items():
        parsed = payload["parsed"]
        md_lines.append(
            f"| `{domain}` | `{payload['service']}` | `{payload['exit_code']}` | "
            f"`{parsed.get('state', '-')}` | `{parsed.get('runs', '-')}` | `{parsed.get('last_exit_code', '-')}` |"
        )
    md_lines.extend(
        [
            "",
            f"- Gateway process count: `{summary['processes']['count']}`",
            f"- Duplicate gateway processes: `{summary['processes']['duplicate_gateway_processes']}`",
            f"- Redacted log tail: `{log_tail_path}`",
        ]
    )
    write_text(phase_root / "launchd-preflight.md", "\n".join(md_lines) + "\n")
    return summary
