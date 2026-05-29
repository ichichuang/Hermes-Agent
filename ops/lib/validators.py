from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from common import HERMES_HOME, now_iso, run_subprocess, write_json, write_text
from evidence_pack import ensure_phase, reports_path
from redaction import env_key_names, redact_text, redacted_tail, yaml_key_names


TEST_MESSAGE = "HERMES_D5_LIVE_VALIDATION_TEST"
JOB_TEST_MESSAGE = "HERMES_D5_JOB_DELIVERY_TEST"
PROVIDER_TEST_MESSAGE = "HERMES_D5_PROVIDER_HEALTHCHECK"


@dataclass
class ValidationCheck:
    check: str
    expected: str
    actual: str
    status: str
    evidence: str


def _provider_configured(env_keys: list[str], config_keys: list[str]) -> bool:
    markers = ("DEEPSEEK", "OPENAI", "ANTHROPIC", "OPENROUTER", "PROVIDER")
    keys = env_keys + config_keys
    return any(any(marker in key.upper() for marker in markers) for key in keys)


def _configured(keys: list[str], *markers: str) -> bool:
    marker_set = [marker.upper() for marker in markers]
    return any(any(marker in key.upper() for marker in marker_set) for key in keys)


def _env_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            values[key] = value
    return values


def _split_targets(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().strip("'\"") for item in re.split(r"[,;\s]+", value) if item.strip()]


def _target_type(chat_id: str | None) -> str:
    if not chat_id:
        return "unknown"
    text = str(chat_id).strip()
    if text.startswith("-"):
        return "group"
    if text.isdigit():
        return "dm"
    return "unknown"


def _load_channel_directory(hermes_home: Path) -> dict[str, Any]:
    path = hermes_home / "channel_directory.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _yaml_scalar(value: str) -> str:
    value = value.split(" #", 1)[0].strip()
    return value.strip("'\"")


def _extract_telegram_home_from_config(path: Path) -> str | None:
    if not path.exists():
        return None
    stack: list[tuple[int, str]] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        while stack and indent <= stack[-1][0]:
            stack.pop()
        stripped = raw_line.strip()
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:\s*(.*)$", stripped)
        if not match:
            continue
        key, value = match.group(1), match.group(2)
        path_keys = [item[1] for item in stack] + [key]
        if value:
            if "telegram" in path_keys and "home_channel" in path_keys and key in {"chat_id", "home_channel"}:
                return _yaml_scalar(value)
            if path_keys == ["telegram", "home_channel"]:
                return _yaml_scalar(value)
        else:
            stack.append((indent, key))
    return None


def _telegram_targets(hermes_home: Path, env_values: dict[str, str]) -> dict[str, dict[str, str] | None]:
    home = (
        env_values.get("TELEGRAM_HOME_CHANNEL")
        or _extract_telegram_home_from_config(hermes_home / "config.yaml")
        or ""
    )
    directory = _load_channel_directory(hermes_home)
    telegram_items = directory.get("platforms", {}).get("telegram", []) if isinstance(directory, dict) else []

    dm_candidates: list[tuple[str, str]] = []
    group_candidates: list[tuple[str, str]] = []

    if home:
        target = ("home_channel", str(home))
        if _target_type(home) == "dm":
            dm_candidates.append(target)
        elif _target_type(home) == "group":
            group_candidates.append(target)

    for item in telegram_items if isinstance(telegram_items, list) else []:
        if not isinstance(item, dict):
            continue
        chat_id = str(item.get("id", "")).strip()
        item_type = str(item.get("type", "")).lower()
        if not chat_id:
            continue
        if item_type in {"private", "dm"} or _target_type(chat_id) == "dm":
            dm_candidates.append(("channel_directory", chat_id))
        if item_type in {"group", "supergroup", "channel"} or _target_type(chat_id) == "group":
            group_candidates.append(("channel_directory", chat_id))

    for key in ("TELEGRAM_ALLOWED_USERS", "TELEGRAM_ALLOW_FROM"):
        for candidate in _split_targets(env_values.get(key)):
            if _target_type(candidate) == "dm":
                dm_candidates.append((key, candidate))

    for key in ("TELEGRAM_GROUP_ALLOWED_CHATS", "TELEGRAM_ALLOWED_CHATS"):
        for candidate in _split_targets(env_values.get(key)):
            if _target_type(candidate) == "group":
                group_candidates.append((key, candidate))

    def first(items: list[tuple[str, str]]) -> dict[str, str] | None:
        seen: set[str] = set()
        for source, target in items:
            if target in seen:
                continue
            seen.add(target)
            return {"source": source, "target": target, "target_type": _target_type(target)}
        return None

    return {
        "dm": first(dm_candidates),
        "group": first(group_candidates),
        "home": {"source": "home_channel", "target": home, "target_type": _target_type(home)} if home else None,
    }


def _jobs_configured(hermes_home: Path) -> bool:
    cron_root = hermes_home / "cron"
    if not cron_root.exists():
        return False
    for path in cron_root.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith(".") or "output" in path.parts:
            continue
        return True
    return False


def _safe_error_category(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"http_{exc.code}"
    if isinstance(exc, urllib.error.URLError):
        reason = str(getattr(exc, "reason", "url_error")).lower()
        if "timed out" in reason or "timeout" in reason:
            return "network_timeout"
        return "network_error"
    if isinstance(exc, subprocess.TimeoutExpired):
        return "timeout"
    return exc.__class__.__name__


def _http_json(url: str, *, token: str | None = None, payload: dict[str, Any] | None = None, timeout: int = 20) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data)
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", "hermes-ops-live-validation")
    if payload is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(body) if body else {}
        return int(getattr(response, "status", 200)), parsed


def _provider_healthcheck(
    phase_root: Path,
    *,
    env_values: dict[str, str],
    configured: bool,
    dry_run: bool,
    allow_external: bool,
) -> dict[str, Any]:
    evidence_path = phase_root / "provider-healthcheck.redacted.json"
    if not configured:
        payload = {
            "created_at": now_iso(),
            "provider": "unknown",
            "category": "provider",
            "status": "BLOCKED",
            "result": "No provider key names detected",
        }
        write_json(evidence_path, payload)
        return payload
    if dry_run or not allow_external:
        payload = {
            "created_at": now_iso(),
            "provider": "DeepSeek",
            "category": "openai-compatible-provider",
            "status": "BLOCKED",
            "result": "Provider configured; external auth call withheld",
        }
        write_json(evidence_path, payload)
        return payload

    api_key = env_values.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        payload = {
            "created_at": now_iso(),
            "provider": "DeepSeek",
            "category": "openai-compatible-provider",
            "status": "BLOCKED",
            "result": "DeepSeek key not available from safe env loader",
        }
        write_json(evidence_path, payload)
        return payload

    base_url = (env_values.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1").rstrip("/")
    url = f"{base_url}/models"
    try:
        status_code, data = _http_json(url, token=api_key)
        models = data.get("data", []) if isinstance(data, dict) else []
        payload = {
            "created_at": now_iso(),
            "provider": "DeepSeek",
            "category": "openai-compatible-provider",
            "status": "PASS" if 200 <= status_code < 300 else "FAIL",
            "http_status": status_code,
            "model_count": len(models) if isinstance(models, list) else None,
            "credential_exposed": False,
        }
    except Exception as exc:
        payload = {
            "created_at": now_iso(),
            "provider": "DeepSeek",
            "category": "openai-compatible-provider",
            "status": "FAIL",
            "error_category": _safe_error_category(exc),
            "credential_exposed": False,
        }
    write_json(evidence_path, payload)
    return payload


def _telegram_api(token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    status_code, data = _http_json(url, payload=payload, timeout=20)
    ok = bool(data.get("ok")) if isinstance(data, dict) else False
    if not ok:
        return {"status": "FAIL", "http_status": status_code, "error_category": f"telegram_api_{status_code}"}
    result = data.get("result", {}) if isinstance(data, dict) else {}
    return {
        "status": "PASS",
        "http_status": status_code,
        "message_id_present": bool(isinstance(result, dict) and result.get("message_id")),
    }


def _telegram_get_me(token: str) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/getMe"
    status_code, data = _http_json(url, timeout=20)
    ok = bool(data.get("ok")) if isinstance(data, dict) else False
    result = data.get("result", {}) if isinstance(data, dict) else {}
    return {
        "status": "PASS" if ok else "FAIL",
        "http_status": status_code,
        "username": str(result.get("username") or "") if isinstance(result, dict) else "",
    }


def _send_telegram_validation_message(token: str, target: dict[str, str], message: str) -> dict[str, Any]:
    try:
        result = _telegram_api(token, "sendMessage", {"chat_id": target["target"], "text": message})
        return {
            "status": result["status"],
            "target_source": target["source"],
            "target_type": target["target_type"],
            "chat_id_redacted": True,
            "http_status": result.get("http_status"),
            "message_id_present": result.get("message_id_present", False),
            "error_category": result.get("error_category"),
        }
    except Exception as exc:
        return {
            "status": "FAIL",
            "target_source": target["source"],
            "target_type": target["target_type"],
            "chat_id_redacted": True,
            "error_category": _safe_error_category(exc),
        }


def _telegram_validation(
    phase_root: Path,
    *,
    env_values: dict[str, str],
    hermes_home: Path,
    dry_run: bool,
    allow_external: bool,
) -> dict[str, Any]:
    evidence_path = phase_root / "telegram-validation.redacted.json"
    token = env_values.get("TELEGRAM_BOT_TOKEN", "")
    configured = bool(token or env_values.get("TELEGRAM_ALLOWED_USERS"))
    targets = _telegram_targets(hermes_home, env_values)
    payload: dict[str, Any] = {
        "created_at": now_iso(),
        "configured": configured,
        "allow_external": allow_external,
        "dm": {"status": "NOT_APPLICABLE"},
        "group_mention": {"status": "NOT_APPLICABLE"},
    }
    if not configured:
        payload["dm"] = {"status": "NOT_APPLICABLE", "result": "No Telegram key names detected"}
        write_json(evidence_path, payload)
        return payload
    if not token:
        payload["dm"] = {"status": "BLOCKED", "result": "Telegram configured but bot token unavailable from safe env loader"}
        write_json(evidence_path, payload)
        return payload
    if dry_run or not allow_external:
        payload["dm"] = {"status": "BLOCKED", "result": "Telegram configured; send withheld"}
        if targets.get("group"):
            payload["group_mention"] = {"status": "BLOCKED", "result": "Configured group detected; send withheld"}
        write_json(evidence_path, payload)
        return payload

    dm_target = targets.get("dm")
    if dm_target:
        payload["dm"] = _send_telegram_validation_message(token, dm_target, TEST_MESSAGE)
    else:
        payload["dm"] = {"status": "BLOCKED", "result": "No configured Telegram DM target detected"}

    group_target = targets.get("group")
    if group_target:
        bot = _telegram_get_me(token)
        mention = f"@{bot['username']} " if bot.get("status") == "PASS" and bot.get("username") else ""
        payload["group_mention"] = _send_telegram_validation_message(
            token,
            group_target,
            f"{mention}{TEST_MESSAGE}",
        )
        payload["group_mention"]["bot_username_available"] = bool(mention)
    else:
        payload["group_mention"] = {
            "status": "NOT_APPLICABLE",
            "result": "No configured Telegram group target detected",
        }
    write_json(evidence_path, payload)
    return payload


def _jobs_validation(
    phase_root: Path,
    *,
    env_values: dict[str, str],
    hermes_home: Path,
    dry_run: bool,
    allow_external: bool,
) -> dict[str, Any]:
    evidence_path = phase_root / "jobs-validation.redacted.json"
    cron_list = run_subprocess(["hermes", "cron", "list", "--all"])
    cron_list_path = phase_root / "cron-list.redacted.txt"
    write_text(cron_list_path, redact_text(cron_list.stdout + cron_list.stderr))

    jobs_present = _jobs_configured(hermes_home)
    targets = _telegram_targets(hermes_home, env_values)
    home = targets.get("home")
    token = env_values.get("TELEGRAM_BOT_TOKEN", "")
    payload: dict[str, Any] = {
        "created_at": now_iso(),
        "jobs_configured": jobs_present,
        "home_channel_configured": bool(home),
        "cron_list_path": str(cron_list_path),
        "status": "NOT_APPLICABLE",
    }
    if not jobs_present and not home:
        payload["result"] = "No scheduled jobs or home channel detected"
        write_json(evidence_path, payload)
        return payload
    if dry_run or not allow_external:
        payload["status"] = "BLOCKED"
        payload["result"] = "Jobs/home delivery configured; delivery withheld"
        write_json(evidence_path, payload)
        return payload
    if not home:
        payload["status"] = "BLOCKED"
        payload["result"] = "Jobs configured but no safe home-channel delivery target detected"
        write_json(evidence_path, payload)
        return payload
    if home["target_type"] == "unknown" or not token:
        payload["status"] = "BLOCKED"
        payload["result"] = "Home channel detected but Telegram delivery prerequisites are incomplete"
        payload["target_type"] = home["target_type"]
        write_json(evidence_path, payload)
        return payload

    result = _send_telegram_validation_message(token, home, JOB_TEST_MESSAGE)
    payload.update(result)
    payload["result"] = "Minimal home-channel delivery attempted"
    write_json(evidence_path, payload)
    return payload


def _feishu_validation(
    phase_root: Path,
    *,
    env_values: dict[str, str],
    dry_run: bool,
    allow_external: bool,
) -> dict[str, Any]:
    evidence_path = phase_root / "feishu-lark-validation.redacted.json"
    app_id = env_values.get("FEISHU_APP_ID") or env_values.get("LARK_APP_ID") or ""
    app_secret = env_values.get("FEISHU_APP_SECRET") or env_values.get("LARK_APP_SECRET") or ""
    configured = bool(app_id or app_secret)
    if not configured:
        payload = {
            "created_at": now_iso(),
            "status": "NOT_APPLICABLE",
            "result": "No Feishu/Lark key names detected",
        }
        write_json(evidence_path, payload)
        return payload
    if not app_id or not app_secret:
        payload = {
            "created_at": now_iso(),
            "status": "BLOCKED",
            "result": "Feishu/Lark appears configured but app credential pair is incomplete",
        }
        write_json(evidence_path, payload)
        return payload
    if dry_run or not allow_external:
        payload = {
            "created_at": now_iso(),
            "status": "BLOCKED",
            "result": "Feishu/Lark configured; connectivity withheld",
        }
        write_json(evidence_path, payload)
        return payload

    domain = (env_values.get("FEISHU_DOMAIN") or "feishu").lower()
    host = "open.larksuite.com" if domain == "lark" else "open.feishu.cn"
    url = f"https://{host}/open-apis/auth/v3/app_access_token/internal"
    try:
        status_code, data = _http_json(url, payload={"app_id": app_id, "app_secret": app_secret})
        ok = isinstance(data, dict) and data.get("code") == 0 and bool(data.get("app_access_token"))
        payload = {
            "created_at": now_iso(),
            "status": "PASS" if ok else "FAIL",
            "http_status": status_code,
            "domain": domain,
            "token_exposed": False,
        }
    except Exception as exc:
        payload = {
            "created_at": now_iso(),
            "status": "FAIL",
            "domain": domain,
            "error_category": _safe_error_category(exc),
            "token_exposed": False,
        }
    write_json(evidence_path, payload)
    return payload


def _write_d5_report(path: Path, title: str, rows: list[tuple[str, str]]) -> None:
    lines = [f"# {title}", "", f"Generated at: `{now_iso()}`", ""]
    for key, value in rows:
        lines.append(f"- {key}: {value}")
    write_text(path, "\n".join(lines) + "\n")


def _write_d5_external_reports(
    archive_root: Path,
    *,
    phase: str,
    checks: list[ValidationCheck],
    provider: dict[str, Any],
    telegram: dict[str, Any],
    jobs: dict[str, Any],
    feishu: dict[str, Any],
) -> None:
    report_root = reports_path(archive_root)
    matrix_lines = [
        "# D5 Validation Matrix",
        "",
        f"Generated at: `{now_iso()}`",
        "",
        "| Check | Expected | Actual | Status | Evidence |",
        "|---|---|---|---|---|",
    ]
    for check in checks:
        matrix_lines.append(
            f"| {check.check} | {check.expected} | {check.actual} | {check.status} | {check.evidence} |"
        )
    write_text(report_root / "D5-validation-matrix.md", "\n".join(matrix_lines) + "\n")

    _write_d5_report(
        report_root / "D5-provider-validation-report.md",
        "D5 Provider Validation Report",
        [
            ("Provider", f"`{provider.get('provider', 'unknown')}`"),
            ("Category", f"`{provider.get('category', 'provider')}`"),
            ("Status", f"`{provider.get('status')}`"),
            ("Credential exposure", "`false`"),
            ("Evidence", f"`{report_root.parent / 'phases' / phase}`"),
        ],
    )
    _write_d5_report(
        report_root / "D5-telegram-validation-report.md",
        "D5 Telegram Validation Report",
        [
            ("DM status", f"`{telegram.get('dm', {}).get('status')}`"),
            ("Group mention status", f"`{telegram.get('group_mention', {}).get('status')}`"),
            ("Message", f"`{TEST_MESSAGE}`"),
            ("Bot token exposure", "`false`"),
            ("Chat ID exposure", "`false`"),
        ],
    )
    _write_d5_report(
        report_root / "D5-jobs-validation-report.md",
        "D5 Jobs Validation Report",
        [
            ("Status", f"`{jobs.get('status')}`"),
            ("Jobs configured", f"`{jobs.get('jobs_configured')}`"),
            ("Home channel configured", f"`{jobs.get('home_channel_configured')}`"),
            ("Sensitive delivery target exposure", "`false`"),
        ],
    )
    _write_d5_report(
        report_root / "D5-feishu-lark-validation-report.md",
        "D5 Feishu/Lark Validation Report",
        [
            ("Status", f"`{feishu.get('status')}`"),
            ("Result", f"`{feishu.get('result', feishu.get('error_category', '-'))}`"),
            ("Credential exposure", "`false`"),
        ],
    )
    write_text(
        report_root / "D5-operator-sop.md",
        "\n".join(
            [
                "# D5 Operator SOP",
                "",
                "## Current State",
                "",
                "D5 external validation has been executed only through `hermes-ops`.",
                "",
                "## Safe Recheck Commands",
                "",
                "```bash",
                "/Users/cc/.hermes/ops/bin/hermes-ops launchd inspect --phase D5.A",
                "/Users/cc/.hermes/ops/bin/hermes-ops validate live --phase D5 --final --allow-external",
                "/Users/cc/.hermes/ops/bin/hermes-ops audit verify",
                "/Users/cc/.hermes/ops/bin/hermes-ops security scan-evidence --phase D5.F --scope-prefix D5",
                "env PYTHONPATH=/Users/cc/.hermes/ops/.pytest-deps python3 -m pytest /Users/cc/.hermes/ops/tests",
                "```",
                "",
                "## Forbidden",
                "",
                "- Do not edit `/Users/cc/.hermes/config.yaml` or `/Users/cc/.hermes/.env`.",
                "- Do not run raw `launchctl enable/bootstrap/bootout/kickstart/load/unload`.",
                "- Do not run raw `hermes gateway install/start/stop/restart`.",
                "- Do not print provider keys, bot tokens, chat IDs, or webhook secrets.",
                "",
            ]
        ),
    )
    write_text(
        report_root / "D5-next-actions.md",
        "\n".join(
            [
                "# D5 Next Actions",
                "",
                "Final action depends on the D5 final GO/NO-GO report.",
                "",
                "- If `D5-final-go-nogo.md` says `PRODUCTION_GO`, operate Hermes with the D5 SOP.",
                "- If it says `NO-GO`, resolve only the named failing integration.",
                "- If any item is `NOT_APPLICABLE`, do not treat it as a failure unless it becomes configured later.",
                "",
            ]
        ),
    )


def validate_live(
    archive_root: Path,
    *,
    phase: str,
    hermes_home: Path = HERMES_HOME,
    dry_run: bool = False,
    final: bool = False,
    allow_external: bool = False,
) -> dict[str, Any]:
    phase_root = ensure_phase(archive_root, phase)
    env_values = _env_values(hermes_home / ".env")
    env_keys = sorted(env_values)
    config_keys = yaml_key_names(hermes_home / "config.yaml")
    report_root = reports_path(archive_root)
    checks: list[ValidationCheck] = []

    hermes_version = run_subprocess(["hermes", "--version"])
    hermes_cli_path = phase_root / "hermes-version.txt"
    write_text(hermes_cli_path, redact_text(hermes_version.stdout + hermes_version.stderr))
    checks.append(
        ValidationCheck(
            check="Hermes CLI",
            expected="callable",
            actual="callable" if hermes_version.returncode == 0 else "not callable",
            status="PASS" if hermes_version.returncode == 0 else "FAIL",
            evidence=str(hermes_cli_path),
        )
    )

    provider = _provider_healthcheck(
        phase_root,
        env_values=env_values,
        configured=_provider_configured(env_keys, config_keys),
        dry_run=dry_run,
        allow_external=allow_external,
    )
    checks.append(
        ValidationCheck(
            check="Provider / DeepSeek",
            expected="minimal healthcheck succeeds",
            actual=str(provider.get("result") or provider.get("error_category") or provider.get("http_status") or provider.get("status")),
            status=str(provider.get("status")),
            evidence=str(phase_root / "provider-healthcheck.redacted.json"),
        )
    )

    gateway_status = run_subprocess(["hermes", "gateway", "status"])
    gateway_status_path = phase_root / "gateway-status.txt"
    write_text(gateway_status_path, redact_text(gateway_status.stdout + gateway_status.stderr))
    gateway_text = (gateway_status.stdout + gateway_status.stderr).lower()
    if gateway_status.returncode != 0:
        gateway_state = "gateway status unavailable"
        gateway_result = "BLOCKED"
    elif "running" in gateway_text or "healthy" in gateway_text or ("gateway service is loaded" in gateway_text and "pid" in gateway_text):
        gateway_state = "gateway running"
        gateway_result = "PASS"
    elif "stopped" in gateway_text or "not running" in gateway_text or "not loaded" in gateway_text or "has not loaded" in gateway_text:
        gateway_state = "gateway not loaded"
        gateway_result = "FAIL"
    else:
        gateway_state = "gateway state unclear"
        gateway_result = "BLOCKED"
    checks.append(
        ValidationCheck(
            check="Gateway status",
            expected="healthy",
            actual=gateway_state,
            status=gateway_result,
            evidence=str(gateway_status_path),
        )
    )

    telegram = _telegram_validation(
        phase_root,
        env_values=env_values,
        hermes_home=hermes_home,
        dry_run=dry_run,
        allow_external=allow_external,
    )
    checks.append(
        ValidationCheck(
            check="Telegram DM",
            expected="minimal DM delivery succeeds if Telegram is configured",
            actual=str(telegram.get("dm", {}).get("result") or telegram.get("dm", {}).get("error_category") or telegram.get("dm", {}).get("target_type") or telegram.get("dm", {}).get("status")),
            status=str(telegram.get("dm", {}).get("status")),
            evidence=str(phase_root / "telegram-validation.redacted.json"),
        )
    )
    checks.append(
        ValidationCheck(
            check="Telegram group mention",
            expected="minimal group mention succeeds if configured group exists",
            actual=str(telegram.get("group_mention", {}).get("result") or telegram.get("group_mention", {}).get("error_category") or telegram.get("group_mention", {}).get("target_type") or telegram.get("group_mention", {}).get("status")),
            status=str(telegram.get("group_mention", {}).get("status")),
            evidence=str(phase_root / "telegram-validation.redacted.json"),
        )
    )

    feishu = _feishu_validation(
        phase_root,
        env_values=env_values,
        dry_run=dry_run,
        allow_external=allow_external,
    )
    checks.append(
        ValidationCheck(
            check="Feishu/Lark",
            expected="connected if configured",
            actual=str(feishu.get("result") or feishu.get("error_category") or feishu.get("status")),
            status=str(feishu.get("status")),
            evidence=str(phase_root / "feishu-lark-validation.redacted.json"),
        )
    )

    jobs = _jobs_validation(
        phase_root,
        env_values=env_values,
        hermes_home=hermes_home,
        dry_run=dry_run,
        allow_external=allow_external,
    )
    checks.append(
        ValidationCheck(
            check="Jobs / cron delivery",
            expected="delivery works if jobs or home channel are configured",
            actual=str(jobs.get("result") or jobs.get("error_category") or jobs.get("status")),
            status=str(jobs.get("status")),
            evidence=str(phase_root / "jobs-validation.redacted.json"),
        )
    )

    pairing_dir = hermes_home / "pairing"
    allowlist_signals = [key for key in env_keys if "ALLOW" in key.upper()]
    if allowlist_signals or any(pairing_dir.iterdir()) if pairing_dir.exists() else False:
        allowlist_status = "PASS"
        allowlist_actual = "allowlist or pairing signal detected"
    else:
        allowlist_status = "BLOCKED"
        allowlist_actual = "No allowlist or pairing evidence detected from safe metadata"
    checks.append(
        ValidationCheck(
            check="Allowlist",
            expected="restricted",
            actual=allowlist_actual,
            status=allowlist_status,
            evidence=str(phase_root / "live-validation.json"),
        )
    )

    redacted_log = redacted_tail(hermes_home / "logs" / "gateway.log", lines=100)
    log_tail_path = phase_root / "gateway-log-tail.redacted.txt"
    write_text(log_tail_path, redacted_log + ("\n" if redacted_log else ""))
    fatal_markers = ("traceback", "fatal", "ex_config", "uncaught", "exception")
    if not redacted_log:
        logs_status = "BLOCKED"
        logs_actual = "Gateway log missing or empty"
    elif any(marker in redacted_log.lower() for marker in fatal_markers):
        logs_status = "FAIL"
        logs_actual = "fatal markers found in log tail"
    else:
        logs_status = "PASS"
        logs_actual = "no fatal markers in redacted tail"
    checks.append(
        ValidationCheck(
            check="Logs",
            expected="no fatal errors",
            actual=logs_actual,
            status=logs_status,
            evidence=str(log_tail_path),
        )
    )

    payload = {
        "created_at": now_iso(),
        "phase": phase,
        "mode": "final" if final else "dry-run" if dry_run else "local",
        "allow_external": allow_external,
        "test_message": TEST_MESSAGE if allow_external and not dry_run else None,
        "checks": [asdict(check) for check in checks],
    }
    json_path = write_json(phase_root / "live-validation.json", payload)

    md_lines = [
        "# Final Validation Matrix",
        "",
        "| Check | Expected | Actual | Status | Evidence |",
        "|---|---|---|---|---|",
    ]
    for check in checks:
        md_lines.append(
            f"| {check.check} | {check.expected} | {check.actual} | {check.status} | {check.evidence} |"
        )
    report_md = "\n".join(md_lines) + "\n"
    write_text(report_root / "final-validation-matrix.md", report_md)
    write_text(report_root / "final-validation-matrix.json", json.dumps(payload, indent=2) + "\n")
    if phase.startswith("D5"):
        _write_d5_external_reports(
            archive_root,
            phase=phase,
            checks=checks,
            provider=provider,
            telegram=telegram,
            jobs=jobs,
            feishu=feishu,
        )
    return {"json_path": str(json_path), "report_path": str(report_root / "final-validation-matrix.md"), "checks": payload["checks"]}
