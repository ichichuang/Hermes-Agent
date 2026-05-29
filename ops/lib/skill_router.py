from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from common import HERMES_HOME, append_jsonl
from evidence_pack import ensure_phase


def _plugin_cache_roots() -> list[Path]:
    cache_root = Path("/Users/cc/.codex/plugins/cache")
    if not cache_root.exists():
        return []
    return [path for path in cache_root.glob("**/skills") if path.is_dir()]


def resolve_skill(skill_name: str) -> dict[str, Any]:
    search_roots: list[tuple[str, Path]] = [
        ("repo-local", HERMES_HOME / ".ai" / "skills"),
        ("repo-local", HERMES_HOME / "skills"),
        ("user", Path("/Users/cc/.codex/skills")),
        ("built-in", Path("/Users/cc/.codex/skills/.system")),
    ]
    for root in _plugin_cache_roots():
        search_roots.append(("built-in", root))
    for source, root in search_roots:
        candidate = root / skill_name / "SKILL.md"
        if candidate.exists():
            return {"skill": skill_name, "source": source, "path": str(candidate)}
    return {"skill": skill_name, "source": "missing", "path": None}


def record_resolution(archive_root: Path, *, phase: str, skill_name: str) -> dict[str, Any]:
    resolution = resolve_skill(skill_name)
    phase_root = ensure_phase(archive_root, phase)
    append_jsonl(phase_root / "skill-router-resolutions.jsonl", resolution)
    (phase_root / "skill-router-last.json").write_text(json.dumps(resolution, indent=2) + "\n", encoding="utf-8")
    return resolution
