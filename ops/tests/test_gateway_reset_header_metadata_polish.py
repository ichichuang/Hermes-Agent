from __future__ import annotations

from test_gateway_reset_tip_fallback import _render_reset_reply


SESSION_INFO_DIAMOND = "◆ Model: `deepseek-chat`\n◆ Provider: deepseek\n◆ Context: 128000 tokens"


def test_new_reset_missing_locale_uses_chinese_header_fallback(monkeypatch) -> None:
    reply = _render_reset_reply(
        monkeypatch,
        "gateway.reset.tip",
        session_info=SESSION_INFO_DIAMOND,
        topic_header="",
    )

    assert "gateway.reset.header_default" not in reply
    assert "gateway.reset.tip" not in reply
    assert reply.startswith("🪄 新会话已开始。")


def test_new_reset_metadata_uses_chinese_labels_and_icons(monkeypatch) -> None:
    reply = _render_reset_reply(
        monkeypatch,
        "gateway.reset.tip",
        session_info=SESSION_INFO_DIAMOND,
        topic_header="",
    )

    assert "🫪 模型：`deepseek-chat`" in reply
    assert "❤️ 服务商：deepseek" in reply
    assert "💭 上下文：128000 tokens" in reply
    assert "◆ Model:" not in reply
    assert "◆ Provider:" not in reply
    assert "◆ Context:" not in reply


def test_new_reset_tip_body_is_chinese_when_locale_returns_english(monkeypatch) -> None:
    reply = _render_reset_reply(
        monkeypatch,
        "Tip: /status shows current session state.",
        random_tip="/status shows current session state.",
        session_info=SESSION_INFO_DIAMOND,
        topic_header="",
    )

    assert "Tip:" not in reply
    assert "shows current session state" not in reply
    assert "💫 提示：可使用 /status 继续操作。" in reply


def test_new_reset_keeps_model_provider_context_values_unchanged(monkeypatch) -> None:
    reply = _render_reset_reply(
        monkeypatch,
        "gateway.reset.tip",
        session_info=SESSION_INFO_DIAMOND,
        topic_header="",
    )

    assert "`deepseek-chat`" in reply
    assert "deepseek" in reply
    assert "128000 tokens" in reply


def test_new_reset_does_not_corrupt_slash_commands_in_tip(monkeypatch) -> None:
    reply = _render_reset_reply(
        monkeypatch,
        "gateway.reset.tip",
        random_tip="/status and /model stay available.",
        session_info=SESSION_INFO_DIAMOND,
        topic_header="",
    )

    assert "/status" in reply
    assert "/model" in reply
    assert "／status" not in reply
    assert "／model" not in reply
