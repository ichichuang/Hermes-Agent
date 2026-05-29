from __future__ import annotations

from pathlib import Path
from typing import Any

from common import (
    ARCHIVE_HOME,
    HERMES_HOME,
    LATEST_SYMLINK,
    OPS_REPORTS_HOME,
    ensure_dir,
    latest_archive_root,
    now_iso,
    now_token,
    phase_dir_name,
    read_json,
    write_json,
    write_text,
)

PLAN_VERSION = "2026-05-27"


def create_archive(archive_root: Path | None = None, *, activate: bool = True) -> Path:
    archive_root = archive_root or (ARCHIVE_HOME / f"hermes-new-{now_token()}")
    ensure_dir(archive_root)
    for name in ("source-inventory", "phases", "ledgers", "audit", "reports"):
        ensure_dir(archive_root / name)
    manifest_path = archive_root / "manifest.json"
    if not manifest_path.exists():
        write_json(
            manifest_path,
            {
                "archive_id": archive_root.name,
                "created_at": now_iso(),
                "hermes_home": str(HERMES_HOME),
                "archive_root": str(archive_root),
                "plan_version": PLAN_VERSION,
                "decision": "PENDING",
                "side_effects_executed": False,
                "phases": [],
                "config_hashes": {},
                "secret_policy": "hash-and-redacted-key-names-only",
            },
        )
    if activate:
        activate_archive(archive_root)
    return archive_root


def activate_archive(archive_root: Path) -> Path:
    ensure_dir(OPS_REPORTS_HOME)
    if LATEST_SYMLINK.is_symlink() or LATEST_SYMLINK.exists():
        LATEST_SYMLINK.unlink()
    LATEST_SYMLINK.symlink_to(archive_root)
    return LATEST_SYMLINK


def get_active_archive(create: bool = False) -> Path | None:
    if LATEST_SYMLINK.is_symlink():
        return LATEST_SYMLINK.resolve()
    latest = latest_archive_root()
    if latest is not None:
        return latest
    if create:
        return create_archive()
    return None


def load_manifest(archive_root: Path) -> dict[str, Any]:
    return read_json(archive_root / "manifest.json", default={}) or {}


def update_manifest(archive_root: Path, **updates: Any) -> dict[str, Any]:
    manifest = load_manifest(archive_root)
    manifest.update(updates)
    write_json(archive_root / "manifest.json", manifest)
    return manifest


def register_phase(archive_root: Path, phase: str) -> dict[str, Any]:
    manifest = load_manifest(archive_root)
    phases = list(manifest.get("phases", []))
    if phase not in phases:
        phases.append(phase)
        manifest["phases"] = phases
        write_json(archive_root / "manifest.json", manifest)
    return manifest


def phase_path(archive_root: Path, phase: str) -> Path:
    return archive_root / "phases" / phase_dir_name(phase)


def ensure_phase(archive_root: Path, phase: str, *, dry_run: bool = False) -> Path:
    phase_root = phase_path(archive_root, phase)
    if dry_run:
        return phase_root
    ensure_dir(phase_root)
    register_phase(archive_root, phase)
    report_path = phase_root / "phase-report.md"
    if not report_path.exists():
        write_text(
            report_path,
            (
                f"# Phase Report - {phase}\n\n"
                "## Decision\n\n"
                "`PENDING`\n\n"
                "## Findings\n\n"
                "- Phase initialized by hermes-ops.\n"
            ),
        )
    return phase_root


def source_inventory_path(archive_root: Path) -> Path:
    return ensure_dir(archive_root / "source-inventory")


def ledgers_path(archive_root: Path) -> Path:
    return ensure_dir(archive_root / "ledgers")


def audit_path(archive_root: Path) -> Path:
    return ensure_dir(archive_root / "audit")


def reports_path(archive_root: Path) -> Path:
    return ensure_dir(archive_root / "reports")
