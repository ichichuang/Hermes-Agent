from __future__ import annotations

from pathlib import Path

from redaction import env_key_names, redact_text, scan_evidence_for_sensitive_values, summarize_sensitive_file


def test_redact_text_masks_assignment_values() -> None:
    text = "DEEPSEEK_API_KEY=super-secret\nAuthorization: Bearer abc123"
    redacted = redact_text(text)
    assert "super-secret" not in redacted
    assert "abc123" not in redacted
    assert "<REDACTED>" in redacted


def test_redact_text_masks_gateway_chat_context() -> None:
    text = "inbound message: platform=telegram user=Jane Doe chat=123456 msg='hello secret-ish text'"
    redacted = redact_text(text)
    assert "Jane Doe" not in redacted
    assert "123456" not in redacted
    assert "hello secret-ish text" not in redacted


def test_env_key_names_only_return_keys(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("FOO=1\nBAR_TOKEN=secret\n# COMMENT\n", encoding="utf-8")
    assert env_key_names(env_path) == ["BAR_TOKEN", "FOO"]


def test_sensitive_summary_does_not_include_values(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("BAR_TOKEN=secret\n", encoding="utf-8")
    summary = summarize_sensitive_file(env_path)
    assert summary["key_names"] == ["BAR_TOKEN"]
    assert "secret" not in str(summary)


def test_redact_text_masks_telegram_bot_url_and_chat_id() -> None:
    text = 'https://api.telegram.org/bot123456:ABC_secret/sendMessage {"chat_id": -1001234567890}'
    redacted = redact_text(text)
    assert "123456:ABC_secret" not in redacted
    assert "-1001234567890" not in redacted
    assert "<REDACTED>" in redacted
    assert "<REDACTED_ID>" in redacted


def test_scan_evidence_reports_secret_file_without_values(tmp_path: Path) -> None:
    archive = tmp_path / "hermes-new-test"
    evidence = archive / "phases" / "D5-test" / "evidence.txt"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("DEEPSEEK_API_KEY=actual-secret-value\n", encoding="utf-8")
    reports = archive / "reports"
    reports.mkdir(parents=True)
    hermes_home = tmp_path / "home"
    hermes_home.mkdir()
    (hermes_home / ".env").write_text("DEEPSEEK_API_KEY=actual-secret-value\n", encoding="utf-8")
    result = scan_evidence_for_sensitive_values(
        archive,
        phase="D5.F",
        hermes_home=hermes_home,
        scope_prefix="D5",
    )
    assert result["status"] == "FAIL"
    assert result["findings"][0]["key_name"] == "DEEPSEEK_API_KEY"
    assert "actual-secret-value" not in str(result)
