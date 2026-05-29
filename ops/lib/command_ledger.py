from __future__ import annotations

from pathlib import Path
from typing import Any

from common import append_jsonl, now_iso, relative_to_archive, sha256_file
from evidence_pack import ledgers_path


def _normalize_path(value: Path | None, archive_root: Path) -> str | None:
    if value is None:
        return None
    return relative_to_archive(value, archive_root)


def record_command(
    archive_root: Path,
    *,
    phase: str,
    risk: str,
    command: str,
    decision: str,
    exit_code: int | None,
    stdout_path: Path | None,
    stderr_path: Path | None,
    notes: str | None = None,
) -> Path:
    entry: dict[str, Any] = {
        "timestamp": now_iso(),
        "phase": phase,
        "risk": risk,
        "command": command,
        "decision": decision,
        "exit_code": exit_code,
        "stdout_path": _normalize_path(stdout_path, archive_root),
        "stderr_path": _normalize_path(stderr_path, archive_root),
        "sha256_stdout": sha256_file(stdout_path) if stdout_path else None,
        "sha256_stderr": sha256_file(stderr_path) if stderr_path else None,
    }
    if notes:
        entry["notes"] = notes
    ledger = ledgers_path(archive_root) / "command-ledger.jsonl"
    append_jsonl(ledger, entry)
    return ledger


def record_not_executed(
    archive_root: Path,
    *,
    phase: str,
    risk: str,
    command: str,
    reason: str,
    evidence_path: Path,
) -> Path:
    entry = {
        "timestamp": now_iso(),
        "phase": phase,
        "risk": risk,
        "command": command,
        "decision": "NOT_EXECUTED",
        "reason": reason,
        "evidence_path": relative_to_archive(evidence_path, archive_root),
    }
    ledger = ledgers_path(archive_root) / "explicitly-not-executed.jsonl"
    append_jsonl(ledger, entry)
    return ledger


def list_ledgers(archive_root: Path) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {"executed": [], "not_executed": []}
    command_path = ledgers_path(archive_root) / "command-ledger.jsonl"
    no_go_path = ledgers_path(archive_root) / "explicitly-not-executed.jsonl"
    if command_path.exists():
        out["executed"] = [__import__("json").loads(line) for line in command_path.read_text(encoding="utf-8").splitlines() if line]
    if no_go_path.exists():
        out["not_executed"] = [__import__("json").loads(line) for line in no_go_path.read_text(encoding="utf-8").splitlines() if line]
    return out
