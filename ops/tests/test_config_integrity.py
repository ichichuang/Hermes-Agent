from __future__ import annotations

from pathlib import Path

from config_integrity import snapshot
from evidence_pack import create_archive


def test_snapshot_writes_hashes_without_secrets(tmp_path: Path) -> None:
    hermes_home = tmp_path / "hermes-home"
    hermes_home.mkdir()
    (hermes_home / "config.yaml").write_text("provider: deepseek\n", encoding="utf-8")
    (hermes_home / ".env").write_text("DEEPSEEK_API_KEY=secret\n", encoding="utf-8")
    (hermes_home / "auth.json").write_text('{"token":"secret"}\n', encoding="utf-8")
    (hermes_home / "SOUL.md").write_text("# soul\n", encoding="utf-8")
    archive_root = create_archive(tmp_path / "hermes-new-config", activate=False)
    result = snapshot(archive_root, "P0.A5", hermes_home=hermes_home)
    output = Path(result["json_path"]).read_text(encoding="utf-8")
    assert "secret" not in output
    assert "DEEPSEEK_API_KEY" in output
