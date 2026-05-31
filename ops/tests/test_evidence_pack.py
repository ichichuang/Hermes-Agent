from __future__ import annotations

from pathlib import Path

import pytest

from evidence_pack import create_archive, ensure_phase, get_active_archive, load_manifest


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


def test_active_archive_accepts_latest_target_under_archive_home(monkeypatch, tmp_path: Path) -> None:
    archive_home = tmp_path / "HermesArchive"
    reports_home = tmp_path / "reports"
    latest = reports_home / "latest"
    monkeypatch.setattr("evidence_pack.ARCHIVE_HOME", archive_home)
    monkeypatch.setattr("evidence_pack.OPS_REPORTS_HOME", reports_home)
    monkeypatch.setattr("evidence_pack.LATEST_SYMLINK", latest)
    monkeypatch.setattr("common.ARCHIVE_HOME", archive_home)

    archive_root = create_archive(archive_home / "hermes-new-ok", activate=True)

    assert get_active_archive(create=False) == archive_root.resolve()


@pytest.mark.parametrize(
    "forbidden_home",
    [
        Path("/Users/cc/.codex/skills"),
        Path("/Users/cc/.agents/skills"),
    ],
)
def test_archive_home_rejects_forbidden_skill_roots(monkeypatch, forbidden_home: Path) -> None:
    monkeypatch.setattr("evidence_pack.ARCHIVE_HOME", forbidden_home)

    with pytest.raises(RuntimeError, match="forbidden skill/cache path"):
        create_archive(activate=False)


def test_latest_symlink_target_must_stay_under_archive_home(monkeypatch, tmp_path: Path) -> None:
    archive_home = tmp_path / "HermesArchive"
    reports_home = tmp_path / "reports"
    latest = reports_home / "latest"
    reports_home.mkdir(parents=True)
    latest.symlink_to(tmp_path / "outside-archive")
    monkeypatch.setattr("evidence_pack.ARCHIVE_HOME", archive_home)
    monkeypatch.setattr("evidence_pack.LATEST_SYMLINK", latest)

    with pytest.raises(RuntimeError, match="outside configured archive home"):
        get_active_archive(create=False)


def test_latest_symlink_target_rejects_codex_skill_path(monkeypatch, tmp_path: Path) -> None:
    archive_home = tmp_path / "HermesArchive"
    reports_home = tmp_path / "reports"
    latest = reports_home / "latest"
    reports_home.mkdir(parents=True)
    latest.symlink_to(Path("/Users/cc/.codex/skills/some-skill"))
    monkeypatch.setattr("evidence_pack.ARCHIVE_HOME", archive_home)
    monkeypatch.setattr("evidence_pack.LATEST_SYMLINK", latest)

    with pytest.raises(RuntimeError, match="forbidden skill/cache path"):
        get_active_archive(create=False)


def test_archive_root_rejects_codex_plugin_cache() -> None:
    archive_root = Path("/Users/cc/.codex/plugins/cache/hermes-new-bad")

    with pytest.raises(RuntimeError, match="forbidden skill/cache path"):
        create_archive(archive_root, activate=False)


def test_phase_path_rejects_parent_traversal(tmp_path: Path) -> None:
    archive_root = create_archive(tmp_path / "hermes-new-traversal", activate=False)

    with pytest.raises(RuntimeError, match="outside active archive root"):
        ensure_phase(archive_root, "../../escape")
