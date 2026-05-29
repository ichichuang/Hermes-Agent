from __future__ import annotations

from pathlib import Path
from typing import Any

from common import HERMES_HOME, now_iso, write_json, write_text
from evidence_pack import ensure_phase, update_manifest
from redaction import summarize_sensitive_file

TARGETS = {
    "config_yaml": HERMES_HOME / "config.yaml",
    "env_file": HERMES_HOME / ".env",
    "auth_json": HERMES_HOME / "auth.json",
    "soul_md": HERMES_HOME / "SOUL.md",
    "lang_layer_config": HERMES_HOME / "lang-layer" / "config.json",
}


def snapshot(archive_root: Path, phase: str, *, hermes_home: Path = HERMES_HOME) -> dict[str, Any]:
    phase_root = ensure_phase(archive_root, phase)
    targets = {
        "config_yaml": hermes_home / "config.yaml",
        "env_file": hermes_home / ".env",
        "auth_json": hermes_home / "auth.json",
        "soul_md": hermes_home / "SOUL.md",
        "lang_layer_config": hermes_home / "lang-layer" / "config.json",
    }
    summary = {
        "phase": phase,
        "created_at": now_iso(),
        "files": {name: summarize_sensitive_file(path) for name, path in targets.items()},
    }
    json_path = write_json(phase_root / "config-integrity.json", summary)
    md_lines = [
        "# Config Integrity Snapshot",
        "",
        f"- Phase: `{phase}`",
        f"- Created at: `{summary['created_at']}`",
        "",
        "| File | Exists | Mode | Mtime | SHA256 | Key names |",
        "|---|---|---|---|---|---|",
    ]
    manifest_hashes: dict[str, str | None] = {}
    for name, payload in summary["files"].items():
        key_names = ", ".join(payload.get("key_names", [])) or "-"
        md_lines.append(
            f"| `{payload['path']}` | `{payload['exists']}` | `{payload['mode'] or '-'}` | "
            f"`{payload['mtime'] or '-'}` | `{payload['sha256'] or '-'}` | `{key_names}` |"
        )
        manifest_hashes[name] = payload.get("sha256")
    write_text(phase_root / "config-integrity.md", "\n".join(md_lines) + "\n")
    manifest = update_manifest(archive_root, config_hashes=manifest_hashes)
    return {
        "json_path": str(json_path),
        "markdown_path": str(phase_root / "config-integrity.md"),
        "manifest": manifest,
        "summary": summary,
    }
