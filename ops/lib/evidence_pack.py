from __future__ import annotations

from pathlib import Path
from typing import Any

from common import (
    ARCHIVE_HOME,
    HERMES_HOME,
    LATEST_SYMLINK,
    OPS_REPORTS_HOME,
    assert_archive_contained,
    assert_archive_home_allowed,
    assert_archive_root_under_home,
    assert_not_forbidden_write_path,
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
    archive_home = assert_archive_home_allowed(ARCHIVE_HOME)
    archive_root = archive_root or (archive_home / f"hermes-new-{now_token()}")
    archive_root = assert_archive_root_under_home(archive_root, archive_home) if activate else assert_not_forbidden_write_path(archive_root)
    ensure_dir(archive_root)
    for name in ("source-inventory", "phases", "ledgers", "audit", "reports"):
        ensure_dir(assert_archive_contained(archive_root / name, archive_root))
    manifest_path = archive_root / "manifest.json"
    if not manifest_path.exists():
        write_json(
            assert_archive_contained(manifest_path, archive_root),
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
    archive_root = assert_archive_root_under_home(archive_root, ARCHIVE_HOME)
    ensure_dir(OPS_REPORTS_HOME)
    if LATEST_SYMLINK.is_symlink() or LATEST_SYMLINK.exists():
        LATEST_SYMLINK.unlink()
    LATEST_SYMLINK.symlink_to(archive_root)
    return LATEST_SYMLINK


def get_active_archive(create: bool = False) -> Path | None:
    archive_home = assert_archive_home_allowed(ARCHIVE_HOME)
    if LATEST_SYMLINK.is_symlink():
        return assert_archive_root_under_home(LATEST_SYMLINK.resolve(strict=False), archive_home)
    latest = latest_archive_root(archive_home)
    if latest is not None:
        return latest
    if create:
        return create_archive()
    return None


def load_manifest(archive_root: Path) -> dict[str, Any]:
    return read_json(assert_archive_contained(archive_root / "manifest.json", archive_root), default={}) or {}


def update_manifest(archive_root: Path, **updates: Any) -> dict[str, Any]:
    manifest = load_manifest(archive_root)
    manifest.update(updates)
    write_json(assert_archive_contained(archive_root / "manifest.json", archive_root), manifest)
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
    return assert_archive_contained(archive_root / "phases" / phase_dir_name(phase), archive_root)


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
    return ensure_dir(assert_archive_contained(archive_root / "source-inventory", archive_root))


def ledgers_path(archive_root: Path) -> Path:
    return ensure_dir(assert_archive_contained(archive_root / "ledgers", archive_root))


def audit_path(archive_root: Path) -> Path:
    return ensure_dir(assert_archive_contained(archive_root / "audit", archive_root))


def reports_path(archive_root: Path) -> Path:
    return ensure_dir(assert_archive_contained(archive_root / "reports", archive_root))
