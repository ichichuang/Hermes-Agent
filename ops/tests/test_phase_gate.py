from __future__ import annotations

import os
from pathlib import Path

from config_integrity import snapshot
from evidence_pack import create_archive, ensure_phase
from phase_gate import evaluate_gate, is_high_risk_command, is_read_only_command


def test_command_classification() -> None:
    assert is_read_only_command(["/bin/pwd"]) is True
    assert is_high_risk_command(["/bin/launchctl", "enable", "gui/501/ai.hermes.gateway"]) is True


def test_gate_blocks_high_risk_command_without_allowlist(tmp_path: Path) -> None:
    archive_root = create_archive(tmp_path / "hermes-new-gate", activate=False)
    ensure_phase(archive_root, "P0.A6")
    snapshot(archive_root, "P0.A5", hermes_home=tmp_path / "empty-home")
    decision = evaluate_gate(
        archive_root,
        phase="P0.A6",
        command=["/bin/launchctl", "enable", "gui/501/ai.hermes.gateway"],
        risk="service-change",
    )
    assert decision["decision"] == "NO-GO"


def test_d4_launchd_remediation_requires_d4_preflight(tmp_path: Path, monkeypatch) -> None:
    archive_root = create_archive(tmp_path / "hermes-new-gate", activate=False)
    ensure_phase(archive_root, "D4.B")
    snapshot(archive_root, "D4.C", hermes_home=tmp_path / "empty-home")
    (archive_root / "reports").mkdir(parents=True, exist_ok=True)
    (archive_root / "reports" / "operator-sop.md").write_text("# SOP\n", encoding="utf-8")
    monkeypatch.setattr("phase_gate.Path.home", lambda: tmp_path)
    command = [
        "/bin/launchctl",
        "bootstrap",
        f"gui/{os.getuid()}",
        str(tmp_path / "Library" / "LaunchAgents" / "ai.hermes.gateway.plist"),
    ]

    denied = evaluate_gate(archive_root, phase="D4.B", command=command, risk="service-change")
    assert denied["decision"] == "NO-GO"
    assert "launchd preflight missing" in denied["reasons"]

    ensure_phase(archive_root, "D4.A")
    (archive_root / "phases" / "D4.A-read-only-preflight" / "launchd-preflight.json").write_text("{}", encoding="utf-8")
    allowed = evaluate_gate(archive_root, phase="D4.B", command=command, risk="service-change")
    assert allowed["decision"] == "GO"


def test_lang_m6_allows_only_exact_plugin_enable_with_evidence(tmp_path: Path) -> None:
    archive_root = create_archive(tmp_path / "hermes-langlayer-gate", activate=False)
    ensure_phase(archive_root, "LANG-M6")
    snapshot(archive_root, "LANG-M6", hermes_home=tmp_path / "empty-home")
    (archive_root / "reports").mkdir(parents=True, exist_ok=True)
    (archive_root / "reports" / "operator-sop.md").write_text("# SOP\n", encoding="utf-8")

    denied = evaluate_gate(
        archive_root,
        phase="LANG-M6",
        command=["hermes", "plugins", "enable", "other-plugin"],
        risk="config-change",
    )
    assert denied["decision"] == "NO-GO"
    assert "high-risk command not allowlisted" in denied["reasons"]

    allowed = evaluate_gate(
        archive_root,
        phase="LANG-M6",
        command=["hermes", "plugins", "enable", "hermes-language-layer"],
        risk="config-change",
    )
    assert allowed["decision"] == "GO"

    rollback = evaluate_gate(
        archive_root,
        phase="LANG-M6",
        command=["hermes", "plugins", "disable", "hermes-language-layer"],
        risk="config-change",
    )
    assert rollback["decision"] == "GO"
