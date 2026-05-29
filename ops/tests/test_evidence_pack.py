from __future__ import annotations

from pathlib import Path

from evidence_pack import create_archive, ensure_phase, load_manifest


def test_create_archive_builds_manifest(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HERMES_OPS_ARCHIVE_HOME", str(tmp_path))
    archive_root = create_archive(tmp_path / "hermes-new-test", activate=False)
    manifest = load_manifest(archive_root)
    assert archive_root.exists()
    assert manifest["archive_id"] == "hermes-new-test"


def test_ensure_phase_creates_phase_report(tmp_path: Path) -> None:
    archive_root = create_archive(tmp_path / "hermes-new-phase", activate=False)
    phase_root = ensure_phase(archive_root, "P0.A3")
    assert phase_root.exists()
    assert (phase_root / "phase-report.md").exists()
