from __future__ import annotations

import hmac
import json
import secrets
from hashlib import sha256
from pathlib import Path
from typing import Any

from common import now_iso, write_json
from evidence_pack import audit_path


def ensure_audit_key(archive_root: Path) -> Path:
    audit_root = audit_path(archive_root)
    key_path = audit_root / "ops-audit.key"
    if not key_path.exists():
        key_path.write_bytes(secrets.token_bytes(32))
        key_path.chmod(0o600)
    return key_path


def _load_key(archive_root: Path) -> bytes:
    return ensure_audit_key(archive_root).read_bytes()


def _entry_hmac(key: bytes, prev_hmac: str, payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hmac.new(key, f"{prev_hmac}\n{body}".encode("utf-8"), sha256).hexdigest()


def append_event(archive_root: Path, *, phase: str, event: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    audit_root = audit_path(archive_root)
    chain_path = audit_root / "ops-audit.jsonl"
    previous = "GENESIS"
    if chain_path.exists():
        last_line = [line for line in chain_path.read_text(encoding="utf-8").splitlines() if line][-1]
        previous = json.loads(last_line)["entry_hmac"]
    payload = {
        "timestamp": now_iso(),
        "phase": phase,
        "event": event,
        "details": details or {},
        "prev_hmac": previous,
    }
    payload["entry_hmac"] = _entry_hmac(_load_key(archive_root), previous, payload)
    with chain_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload


def verify_chain(archive_root: Path) -> dict[str, Any]:
    chain_path = audit_path(archive_root) / "ops-audit.jsonl"
    if not chain_path.exists():
        return {"ok": False, "checked": 0, "reason": "audit chain missing"}
    key = _load_key(archive_root)
    previous = "GENESIS"
    checked = 0
    for raw_line in chain_path.read_text(encoding="utf-8").splitlines():
        if not raw_line:
            continue
        payload = json.loads(raw_line)
        expected = payload.get("entry_hmac")
        content = dict(payload)
        content.pop("entry_hmac", None)
        actual = _entry_hmac(key, previous, content)
        if actual != expected:
            result = {"ok": False, "checked": checked, "reason": "entry_hmac mismatch", "entry": payload}
            write_json(audit_path(archive_root) / "audit-verify.json", result)
            return result
        previous = expected
        checked += 1
    result = {"ok": True, "checked": checked}
    write_json(audit_path(archive_root) / "audit-verify.json", result)
    return result
