from __future__ import annotations

from pathlib import Path

from skill_router import resolve_skill


def test_resolve_skill_missing_for_unknown_name() -> None:
    result = resolve_skill("definitely-not-a-real-skill")
    assert result["source"] == "missing"
