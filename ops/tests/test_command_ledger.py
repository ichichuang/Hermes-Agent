from __future__ import annotations

from pathlib import Path

from command_ledger import list_ledgers, record_command, record_not_executed
from evidence_pack import create_archive, ensure_phase


def test_record_command_and_not_executed(tmp_path: Path) -> None:
    archive_root = create_archive(tmp_path / "hermes-new-ledger", activate=False)
    phase_root = ensure_phase(archive_root, "P0.A4")
    stdout_path = phase_root / "stdout.txt"
    stderr_path = phase_root / "stderr.txt"
    stdout_path.write_text("ok\n", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    record_command(
        archive_root,
        phase="P0.A4",
        risk="read-only",
        command="/bin/pwd",
        decision="EXECUTED",
        exit_code=0,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    record_not_executed(
        archive_root,
        phase="P0.A6",
        risk="service-change",
        command="/bin/launchctl enable gui/501/ai.hermes.gateway",
        reason="hard-stop",
        evidence_path=phase_root / "gate-decision.json",
    )
    ledgers = list_ledgers(archive_root)
    assert len(ledgers["executed"]) == 1
    assert len(ledgers["not_executed"]) == 1
