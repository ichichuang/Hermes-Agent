from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from common import DEFAULT_HERMES_LABEL, shell_join, write_json
from evidence_pack import ensure_phase, get_active_archive, load_manifest, phase_path

HARD_STOP_PATTERNS = [
    "launchctl enable",
    "launchctl bootstrap",
    "launchctl bootout",
    "launchctl kickstart",
    "launchctl load -w",
    "launchctl unload -w",
    "hermes gateway install",
    "hermes gateway start",
    "hermes gateway stop",
    "hermes gateway restart",
    "hermes plugins enable",
    "hermes plugins disable",
    "rm -rf",
]

SAFE_BASENAMES = {
    "pwd",
    "ls",
    "find",
    "cat",
    "stat",
    "shasum",
    "sha256sum",
    "ps",
    "tail",
    "plutil",
    "printenv",
}


def _basename(command: Sequence[str]) -> str:
    if not command:
        return ""
    return Path(command[0]).name


def touches_launchd(command: Sequence[str]) -> bool:
    rendered = shell_join(command).lower()
    return "launchctl" in rendered or "hermes gateway" in rendered or DEFAULT_HERMES_LABEL in rendered


def is_read_only_command(command: Sequence[str]) -> bool:
    if not command:
        return False
    rendered = shell_join(command).lower()
    basename = _basename(command)
    if basename in SAFE_BASENAMES:
        return True
    if basename == "launchctl":
        return len(command) > 1 and command[1] == "print"
    if basename == "hermes":
        if len(command) > 2 and command[1] == "gateway" and command[2] == "status":
            return True
        if len(command) > 2 and command[1] == "plugins" and command[2] in {"list", "ls"}:
            return True
        if len(command) > 2 and command[1] == "hooks" and command[2] == "list":
            return True
        if len(command) > 2 and command[1] == "config" and command[2] == "check":
            return True
        return False
    return " launchctl print " in f" {rendered} "


def is_high_risk_command(command: Sequence[str]) -> bool:
    rendered = shell_join(command).lower()
    return any(pattern in rendered for pattern in HARD_STOP_PATTERNS)


def exact_allowlist_for_phase(phase: str) -> set[str]:
    uid = os.getuid()
    if phase == "P1.B1":
        return {
            f"/bin/launchctl print gui/{uid}/{DEFAULT_HERMES_LABEL}",
            f"/bin/launchctl print user/{uid}/{DEFAULT_HERMES_LABEL}",
            f"launchctl print gui/{uid}/{DEFAULT_HERMES_LABEL}",
            f"launchctl print user/{uid}/{DEFAULT_HERMES_LABEL}",
            "hermes gateway status",
        }
    if phase == "D4.B":
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{DEFAULT_HERMES_LABEL}.plist"
        return {
            f"/bin/launchctl bootstrap gui/{uid} {plist_path}",
            f"/bin/launchctl enable gui/{uid}/{DEFAULT_HERMES_LABEL}",
            f"/bin/launchctl kickstart -k gui/{uid}/{DEFAULT_HERMES_LABEL}",
        }
    if phase == "D6.C":
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{DEFAULT_HERMES_LABEL}.plist"
        return {
            "hermes gateway install",
            f"/bin/launchctl bootstrap gui/{uid} {plist_path}",
            "hermes gateway start",
        }
    if phase == "LANG-M6":
        return {
            "hermes plugins enable hermes-language-layer",
            "hermes plugins disable hermes-language-layer",
            "hermes gateway restart",
            "hermes gateway status",
        }
    return set()


def launchd_preflight_exists(archive_root: Path, phase: str) -> bool:
    if phase.startswith("D4."):
        return (phase_path(archive_root, "D4.A") / "launchd-preflight.json").exists()
    if phase.startswith("D6."):
        return (
            (phase_path(archive_root, "D6.A") / "launchd-preflight.json").exists()
            or (phase_path(archive_root, "D6.B") / "launchd-preflight.json").exists()
        )
    if phase.startswith("LANG-M"):
        return (phase_path(archive_root, phase) / "launchd-preflight.json").exists()
    return (phase_path(archive_root, "P0.A7") / "launchd-preflight.json").exists()


def evaluate_gate(
    archive_root: Path,
    *,
    phase: str,
    command: Sequence[str] | None = None,
    risk: str = "read-only",
) -> dict[str, object]:
    archive_exists = archive_root.exists()
    phase_root = phase_path(archive_root, phase)
    phase_exists = phase_root.exists()
    manifest = load_manifest(archive_root) if archive_exists else {}
    config_snapshot = bool(manifest.get("config_hashes"))
    launchd_preflight = launchd_preflight_exists(archive_root, phase)
    operator_sop = (archive_root / "reports" / "operator-sop.md").exists()
    command_text = shell_join(command) if command else None
    launchd_command = touches_launchd(command or [])
    read_only = is_read_only_command(command or []) if command else True
    high_risk = is_high_risk_command(command or []) if command else False
    allowlist = exact_allowlist_for_phase(phase)
    exact_allowed = command_text in allowlist if command_text else False

    checks = {
        "archive_exists": archive_exists,
        "phase_exists": phase_exists,
        "config_snapshot": config_snapshot,
        "launchd_preflight": (not launchd_command) or launchd_preflight,
        "operator_sop": operator_sop,
        "exact_allowlist": exact_allowed,
        "read_only_command": read_only,
        "high_risk_command": high_risk,
    }

    decision = "GO"
    reasons: list[str] = []
    if not archive_exists:
        decision = "NO-GO"
        reasons.append("active archive missing")
    if not phase_exists:
        decision = "NO-GO"
        reasons.append("phase evidence missing")
    if command:
        if launchd_command and not launchd_preflight:
            decision = "NO-GO"
            reasons.append("launchd preflight missing")
        if not read_only and not config_snapshot:
            decision = "NO-GO"
            reasons.append("config snapshot missing")
        if high_risk and not exact_allowed:
            decision = "NO-GO"
            reasons.append("high-risk command not allowlisted")
        if not read_only and not operator_sop:
            decision = "NO-GO"
            reasons.append("operator SOP missing")
    else:
        if phase == "P1.B1":
            if not config_snapshot:
                decision = "NO-GO"
                reasons.append("config snapshot missing")
            if not launchd_preflight:
                decision = "NO-GO"
                reasons.append("launchd preflight missing")

    if not reasons:
        reasons.append("all gate checks satisfied")

    payload = {
        "phase": phase,
        "risk": risk,
        "command": command_text,
        "decision": decision,
        "checks": checks,
        "reasons": reasons,
    }
    phase_root = ensure_phase(archive_root, phase)
    write_json(phase_root / "gate-decision.json", payload)
    return payload


def active_archive_or_raise() -> Path:
    archive_root = get_active_archive(create=False)
    if archive_root is None:
        raise SystemExit("No active archive. Run `hermes-ops phase start <phase>` first.")
    return archive_root
