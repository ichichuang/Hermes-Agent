from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from common import (
    HERMES_HOME,
    assert_archive_contained,
    ensure_dir,
    file_mode,
    mtime_iso,
    now_iso,
    phase_dir_name,
    sha256_file,
    write_json,
    write_text,
)

SECRET_KEY_PATTERN = re.compile(
    r"(API_KEY|TOKEN|SECRET|AUTH|COOKIE|PRIVATE_KEY|BOT_TOKEN|APP_SECRET)",
    re.IGNORECASE,
)
ASSIGNMENT_PATTERN = re.compile(
    r"^(\s*['\"]?[A-Za-z0-9_.-]*?(?:API_KEY|TOKEN|SECRET|AUTH|COOKIE|PRIVATE_KEY|BOT_TOKEN|APP_SECRET)[A-Za-z0-9_.-]*['\"]?\s*[:=]\s*)(.+)$",
    re.IGNORECASE,
)
SK_TOKEN_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]+")
BEARER_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9._-]+", re.IGNORECASE)
TELEGRAM_BOT_URL_PATTERN = re.compile(r"(api\.telegram\.org/bot)([0-9]+:[A-Za-z0-9_-]+)")
JSON_CHAT_ID_PATTERN = re.compile(r'("chat_id"\s*:\s*"?)-?\d+("?|\b)')
CHAT_ID_LABEL_PATTERN = re.compile(r"(chat_id\s*[:=]\s*)-?\d+")
CHAT_ID_PATTERNS = [
    re.compile(r"(chat=)\d+"),
    re.compile(r"(dm:)\d+"),
    re.compile(r"(\bto\s+)\d+"),
    re.compile(r"(telegram:)-?\d+"),
]
GATEWAY_USER_PATTERN = re.compile(r"(user=).*?(\s+chat=)")
GATEWAY_MESSAGE_PATTERN = re.compile(r"(msg=')[^']*(')")


def redact_text(text: str) -> str:
    redacted_lines: list[str] = []
    for line in text.splitlines():
        match = ASSIGNMENT_PATTERN.match(line)
        if match:
            redacted_lines.append(f"{match.group(1)}<REDACTED>")
            continue
        cleaned = SK_TOKEN_PATTERN.sub("<REDACTED>", line)
        cleaned = BEARER_PATTERN.sub(r"\1<REDACTED>", cleaned)
        cleaned = TELEGRAM_BOT_URL_PATTERN.sub(r"\1<REDACTED>", cleaned)
        cleaned = JSON_CHAT_ID_PATTERN.sub(r"\1<REDACTED_ID>\2", cleaned)
        cleaned = CHAT_ID_LABEL_PATTERN.sub(r"\1<REDACTED_ID>", cleaned)
        for pattern in CHAT_ID_PATTERNS:
            cleaned = pattern.sub(r"\1<REDACTED_ID>", cleaned)
        cleaned = GATEWAY_USER_PATTERN.sub(r"\1<REDACTED>\2", cleaned)
        cleaned = GATEWAY_MESSAGE_PATTERN.sub(r"\1<REDACTED>\2", cleaned)
        redacted_lines.append(cleaned)
    return "\n".join(redacted_lines)


def env_key_names(path: Path) -> list[str]:
    if not path.exists():
        return []
    keys: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key:
            keys.append(key)
    return sorted(set(keys))


def yaml_key_names(path: Path) -> list[str]:
    if not path.exists():
        return []
    keys: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:", line)
        if match:
            keys.append(match.group(1))
    return sorted(set(keys))


def json_key_names(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    keys: set[str] = set()

    def walk(node: Any, prefix: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                full_key = f"{prefix}.{key}" if prefix else key
                keys.add(full_key)
                walk(value, full_key)
        elif isinstance(node, list):
            for item in node:
                walk(item, prefix)

    walk(payload)
    return sorted(keys)


def summarize_sensitive_file(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "mode": file_mode(path),
        "mtime": mtime_iso(path),
        "sha256": sha256_file(path),
    }
    if not path.exists():
        summary["key_names"] = []
        return summary
    if path.name == ".env":
        summary["key_names"] = env_key_names(path)
    elif path.suffix == ".json":
        summary["key_names"] = json_key_names(path)
    elif path.suffix in {".yaml", ".yml"}:
        summary["key_names"] = yaml_key_names(path)
    else:
        summary["key_names"] = []
    return summary


def redacted_tail(path: Path, *, lines: int = 100) -> str:
    if not path.exists():
        return ""
    chunks = path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    return redact_text("\n".join(chunks))


def _env_pairs(path: Path) -> dict[str, str]:
    pairs: dict[str, str] = {}
    if not path.exists():
        return pairs
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            pairs[key] = value
    return pairs


def _sensitive_env_needles(path: Path) -> dict[str, list[str]]:
    needles: dict[str, list[str]] = {}
    for key, value in _env_pairs(path).items():
        upper = key.upper()
        is_sensitive = bool(SECRET_KEY_PATTERN.search(key)) or (
            upper.startswith("TELEGRAM_")
            and any(marker in upper for marker in ("ALLOWED", "HOME_CHANNEL", "CHAT", "USER"))
        )
        if not is_sensitive:
            continue
        parts = [part.strip() for part in re.split(r"[,;\s]+", value) if part.strip()]
        if value and value not in parts:
            parts.append(value)
        safe_parts = [part for part in parts if len(part) >= 6]
        if safe_parts:
            needles[key] = safe_parts
    return needles


def _iter_text_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    ignored_parts = {"__pycache__", ".pytest_cache"}
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in ignored_parts for part in path.parts):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip"}:
            continue
        files.append(path)
    return files


def scan_evidence_for_sensitive_values(
    archive_root: Path,
    *,
    phase: str,
    hermes_home: Path = HERMES_HOME,
    scope_prefix: str = "D5",
) -> dict[str, Any]:
    """Scan generated D5 evidence without returning matched secret values."""
    phase_root = assert_archive_contained(archive_root / "phases" / phase_dir_name(phase), archive_root)
    ensure_dir(phase_root)
    evidence_roots = [
        archive_root / "phases",
        archive_root / "reports",
    ]
    needles = _sensitive_env_needles(hermes_home / ".env")
    findings: list[dict[str, Any]] = []

    for root in evidence_roots:
        for path in _iter_text_files(root):
            relative = str(path.relative_to(archive_root))
            if root.name == "phases" and not path.relative_to(root).parts[0].startswith(scope_prefix):
                continue
            if root.name == "reports" and not path.name.startswith(scope_prefix):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for key, values in needles.items():
                for value in values:
                    if value and value in text:
                        findings.append(
                            {
                                "path": relative,
                                "category": "sensitive-env-value",
                                "key_name": key,
                            }
                        )
                        break
            if TELEGRAM_BOT_URL_PATTERN.search(text):
                findings.append({"path": relative, "category": "telegram-bot-token-url"})
            if re.search(r'"chat_id"\s*:\s*"?-?\d{5,}', text) or re.search(r"\bchat_id\s*[:=]\s*-?\d{5,}", text):
                findings.append({"path": relative, "category": "chat-id"})

    payload = {
        "created_at": now_iso(),
        "phase": phase,
        "scope_prefix": scope_prefix,
        "status": "PASS" if not findings else "FAIL",
        "scanned_roots": [str(root) for root in evidence_roots],
        "sensitive_key_count": len(needles),
        "finding_count": len(findings),
        "findings": findings,
    }
    json_path = write_json(phase_root / "redaction-scan.json", payload)
    report_name = f"{scope_prefix}-security-redaction-report.md" if scope_prefix else "security-redaction-report.md"
    lines = [
        f"# {scope_prefix} Security Redaction Report" if scope_prefix else "# Security Redaction Report",
        "",
        f"Generated at: `{payload['created_at']}`",
        "",
        f"- Status: `{payload['status']}`",
        f"- Sensitive key values scanned: `{payload['sensitive_key_count']}`",
        f"- Findings: `{payload['finding_count']}`",
        f"- JSON evidence: `{json_path}`",
        "",
        "| Category | File | Key name |",
        "|---|---|---|",
    ]
    if findings:
        for item in findings:
            lines.append(f"| {item['category']} | `{item['path']}` | `{item.get('key_name', '-')}` |")
    else:
        lines.append("| none | - | - |")
    write_text(archive_root / "reports" / report_name, "\n".join(lines) + "\n")
    return payload
