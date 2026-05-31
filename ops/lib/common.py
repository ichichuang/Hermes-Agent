from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

HERMES_HOME = Path(os.environ.get("HERMES_OPS_HERMES_HOME", "/Users/cc/.hermes")).expanduser()
ARCHIVE_HOME = Path(os.environ.get("HERMES_OPS_ARCHIVE_HOME", "/Users/cc/HermesArchive")).expanduser()
OPS_HOME = HERMES_HOME / "ops"
OPS_REPORTS_HOME = OPS_HOME / "reports"
LATEST_SYMLINK = OPS_REPORTS_HOME / "latest"
DEFAULT_HERMES_LABEL = "ai.hermes.gateway"
FORBIDDEN_WRITE_ROOTS = [
    Path("/Users/cc/.agents/skills"),
    Path("/Users/cc/.codex/skills"),
    Path("/Users/cc/.codex/plugins/cache"),
    Path("/Users/cc/.ai/views/codex"),
    Path("/Users/cc/.hermes/skills"),
]

PHASE_SLUGS = {
    "P0.A0": "bootstrap",
    "P0.A1": "source-inventory",
    "P0.A2": "ops-skeleton",
    "P0.A3": "evidence-pack-engine",
    "P0.A4": "command-ledgers",
    "P0.A5": "config-integrity",
    "P0.A6": "phase-gate",
    "P0.A7": "launchd-preflight",
    "P0.A8": "p0-validation",
    "P1.B1": "controlled-launchd-remediation",
    "P1.B2": "live-validation",
    "P1.B3": "operator-sop",
    "P1.B4": "audit-chain",
    "P1.B5": "security-baseline",
    "P1.B6": "final-go-nogo",
    "P2.C1": "skill-router",
    "P2.C2": "archive-standardization",
    "P2.C3": "skill-packaging",
    "P2.C4": "kanban-integration-design",
    "P2.C5": "gateway-collision-detector",
    "P3.D1": "upstream-pr-prep",
    "P3.D2": "maintenance-automation",
    "P3.D3": "regression-pack",
    "P3.D4": "final-documentation-bundle",
    "D4": "production-enablement-remediation",
    "D4.A": "read-only-preflight",
    "D4.B": "launchd-remediation",
    "D4.C": "security-baseline",
    "D4.D": "toolchain",
    "D4.E": "live-validation",
    "D5": "authorized-external-live-validation",
    "D5.A": "baseline-recheck",
    "D5.B": "provider-live-validation",
    "D5.C": "telegram-live-validation",
    "D5.D": "jobs-cron-delivery-validation",
    "D5.E": "feishu-lark-validation",
    "D5.F": "post-validation-audit",
    "D5.G": "final-decision",
    "D6": "reboot-autostart-daemon-assurance",
    "D6.A": "official-autostart-baseline",
    "D6.B": "autostart-capability",
    "D6.C": "gated-autostart-remediation",
    "D6.D": "reboot-instruction-report",
    "D6.E": "final-autostart-reports",
    "D6.F": "post-autostart-validation",
    "LANG-M6": "gated-b-layer-live-activation",
}

FINAL_TASK_STATUSES = {"DONE", "BLOCKED", "NO-GO", "NOT_APPLICABLE"}


def now() -> datetime:
    return datetime.now().astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def now_token() -> str:
    return now().strftime("%Y%m%d_%H%M%S")


def resolve_path(path: Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def is_relative_to_path(child: Path, parent: Path) -> bool:
    child_resolved = resolve_path(child)
    parent_resolved = resolve_path(parent)
    return child_resolved == parent_resolved or child_resolved.is_relative_to(parent_resolved)


def assert_not_forbidden_write_path(path: Path) -> Path:
    resolved = resolve_path(path)
    for forbidden in FORBIDDEN_WRITE_ROOTS:
        forbidden_resolved = resolve_path(forbidden)
        if resolved == forbidden_resolved or resolved.is_relative_to(forbidden_resolved):
            raise RuntimeError(f"Refusing to write under forbidden skill/cache path: {resolved}")
    return resolved


def assert_archive_home_allowed(archive_home: Path | None = None) -> Path:
    return assert_not_forbidden_write_path(archive_home or ARCHIVE_HOME)


def assert_archive_root_under_home(archive_root: Path, archive_home: Path | None = None) -> Path:
    home = assert_archive_home_allowed(archive_home)
    root = assert_not_forbidden_write_path(archive_root)
    if not (root == home or root.is_relative_to(home)):
        raise RuntimeError(f"Refusing active archive root outside configured archive home: {root} not under {home}")
    return root


def assert_archive_contained(path: Path, archive_root: Path) -> Path:
    resolved = assert_not_forbidden_write_path(path)
    root = assert_not_forbidden_write_path(archive_root)
    if not (resolved == root or resolved.is_relative_to(root)):
        raise RuntimeError(f"Refusing archive write outside active archive root: {resolved} not under {root}")
    return resolved


def ensure_dir(path: Path) -> Path:
    path = assert_not_forbidden_write_path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, text: str) -> Path:
    path = assert_not_forbidden_write_path(path)
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")
    return path


def write_json(path: Path, data: Any) -> Path:
    path = assert_not_forbidden_write_path(path)
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_bytes(path: Path, data: bytes) -> Path:
    path = assert_not_forbidden_write_path(path)
    ensure_dir(path.parent)
    path.write_bytes(data)
    return path


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, entry: dict[str, Any]) -> Path:
    path = assert_not_forbidden_write_path(path)
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_mode(path: Path) -> str | None:
    if not path.exists():
        return None
    return oct(path.stat().st_mode & 0o777)


def mtime_iso(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")


def phase_dir_name(phase: str) -> str:
    return f"{phase}-{PHASE_SLUGS.get(phase, phase.lower().replace('.', '-'))}"


def shell_join(command: Sequence[str]) -> str:
    return shlex.join([str(part) for part in command])


def relative_to_archive(path: Path, archive_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(archive_root.resolve()))
    except ValueError:
        return str(path)


def run_subprocess(command: Sequence[str], *, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(part) for part in command],
        capture_output=True,
        text=text,
        check=False,
    )


def latest_archive_root(archive_home: Path | None = None) -> Path | None:
    home = assert_archive_home_allowed(archive_home)
    if not home.exists():
        return None
    archives = sorted(
        (path for path in home.iterdir() if path.is_dir() and path.name.startswith("hermes-new-")),
        key=lambda item: item.name,
    )
    return assert_archive_root_under_home(archives[-1], home) if archives else None


def status_table_rows(status_path: Path | None = None) -> dict[str, dict[str, str]]:
    status_path = status_path or (HERMES_HOME / "docs" / "ai-plan" / "07_STATUS.md")
    if not status_path.exists():
        return {}
    rows: dict[str, dict[str, str]] = {}
    in_table = False
    for raw_line in status_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "## Task status":
            in_table = True
            continue
        if not in_table:
            continue
        if not line:
            if rows:
                break
            continue
        if not line.startswith("|"):
            continue
        if line.startswith("| ID |") or line.startswith("|---|"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) < 5:
            continue
        rows[parts[0]] = {
            "status": parts[1],
            "evidence_path": parts[2],
            "validation": parts[3],
            "notes": parts[4],
        }
    return rows


def truthy_env(name: str) -> bool:
    value = os.environ.get(name)
    if value is None:
        return False
    return value.lower() not in {"", "0", "false", "no", "off"}


def count_files(paths: Iterable[Path]) -> int:
    return sum(1 for _ in paths)
