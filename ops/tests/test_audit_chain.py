from __future__ import annotations

import json
from pathlib import Path

from audit_chain import append_event, verify_chain
from evidence_pack import create_archive


def test_audit_chain_detects_tampering(tmp_path: Path) -> None:
    archive_root = create_archive(tmp_path / "hermes-new-audit", activate=False)
    append_event(archive_root, phase="P1.B4", event="smoke-test")
    assert verify_chain(archive_root)["ok"] is True
    chain_path = archive_root / "audit" / "ops-audit.jsonl"
    payload = json.loads(chain_path.read_text(encoding="utf-8").splitlines()[0])
    payload["event"] = "tampered"
    chain_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    assert verify_chain(archive_root)["ok"] is False
