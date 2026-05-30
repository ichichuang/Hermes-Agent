from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path


SITE_PACKAGES = Path("/Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages")
GATEWAY_RUN = SITE_PACKAGES / "gateway" / "run.py"
SESSION_INFO = "Model: deepseek-chat\nProvider: deepseek\nContext: 128000 tokens"


class _FakePlatform:
    value = "telegram"


class _FakeSource:
    platform = _FakePlatform()
    user_id = "user-m16"


class _FakeEvent:
    source = _FakeSource()

    def get_command_args(self) -> str:
        return ""


class _FakeHooks:
    async def emit(self, *_args: object, **_kwargs: object) -> None:
        return None


class _FakeEntry:
    session_id = "new-session-m16"


class _FakeSessionStore:
    def __init__(self) -> None:
        self._entries = {"telegram:user-m16": types.SimpleNamespace(session_id="old-session-m16")}

    def reset_session(self, _session_key: str) -> _FakeEntry:
        return _FakeEntry()

    def get_or_create_session(self, *_args: object, **_kwargs: object) -> _FakeEntry:
        return _FakeEntry()


class _FakeRunner:
    def __init__(self, *, session_info: str = SESSION_INFO, topic_header: str = "新会话已开始。") -> None:
        self.session_store = _FakeSessionStore()
        self.hooks = _FakeHooks()
        self._agent_cache_lock = None
        self._queued_events: dict[str, object] = {}
        self._session_model_overrides: dict[str, object] = {}
        self._pending_model_notes: dict[str, object] = {}
        self._session_db = None
        self._session_info = session_info
        self._topic_header = topic_header

    def _session_key_for_source(self, _source: object) -> str:
        return "telegram:user-m16"

    def _invalidate_session_run_generation(self, *_args: object, **_kwargs: object) -> None:
        return None

    def _evict_cached_agent(self, *_args: object, **_kwargs: object) -> None:
        return None

    def _set_session_reasoning_override(self, *_args: object, **_kwargs: object) -> None:
        return None

    def _clear_session_boundary_security_state(self, *_args: object, **_kwargs: object) -> None:
        return None

    def _format_session_info(self) -> str:
        return self._session_info

    def _telegram_topic_new_header(self, _source: object) -> str:
        return self._topic_header

    def _is_telegram_topic_lane(self, _source: object) -> bool:
        return False


def _fake_module(module_name: str, attr_name: str, value: object) -> types.ModuleType:
    module = types.ModuleType(module_name)
    setattr(module, attr_name, value)
    return module


def _load_gateway_run():
    if str(SITE_PACKAGES) not in sys.path:
        sys.path.insert(0, str(SITE_PACKAGES))
    spec = importlib.util.spec_from_file_location("gateway_run_m16_under_test", GATEWAY_RUN)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _render_reset_reply(
    monkeypatch,
    tip_translation: str,
    *,
    random_tip: str = "试试 /status",
    session_info: str = SESSION_INFO,
    topic_header: str = "新会话已开始。",
    translations: dict[str, str] | None = None,
) -> str:
    gateway_run = _load_gateway_run()

    def fake_t(key: str, **_kwargs: object) -> str:
        if translations and key in translations:
            return translations[key]
        if key == "gateway.reset.tip":
            return tip_translation
        return key

    monkeypatch.setattr(gateway_run, "t", fake_t)
    monkeypatch.setitem(
        sys.modules,
        "hermes_cli.tips",
        _fake_module("hermes_cli.tips", "get_random_tip", lambda: random_tip),
    )
    monkeypatch.setitem(
        sys.modules,
        "hermes_cli.plugins",
        _fake_module("hermes_cli.plugins", "invoke_hook", lambda *_args, **_kwargs: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "tools.env_passthrough",
        _fake_module("tools.env_passthrough", "clear_env_passthrough", lambda: None),
    )
    monkeypatch.setitem(
        sys.modules,
        "tools.credential_files",
        _fake_module("tools.credential_files", "clear_credential_files", lambda: None),
    )

    reply = asyncio.run(
        gateway_run.GatewayRunner._handle_reset_command(
            _FakeRunner(session_info=session_info, topic_header=topic_header),
            _FakeEvent(),
        )
    )
    assert isinstance(reply, gateway_run.EphemeralReply)
    return str(reply)


def test_new_reset_tip_uses_chinese_fallback_when_locale_returns_raw_key(monkeypatch) -> None:
    reply = _render_reset_reply(monkeypatch, "gateway.reset.tip")

    assert "gateway.reset.tip" not in reply
    assert "💫 提示：试试 /status" in reply
    assert "💭 上下文：128000 tokens\n\n💫 提示" in reply


def test_new_reset_tip_uses_chinese_fallback_when_locale_returns_empty(monkeypatch) -> None:
    reply = _render_reset_reply(monkeypatch, "")

    assert "gateway.reset.tip" not in reply
    assert "💫 提示：试试 /status" in reply
    assert "💭 上下文：128000 tokens\n\n💫 提示" in reply


def test_new_reset_tip_preserves_model_provider_context_metadata(monkeypatch) -> None:
    reply = _render_reset_reply(monkeypatch, "gateway.reset.tip")

    assert "🫪 模型：deepseek-chat" in reply
    assert "❤️ 服务商：deepseek" in reply
    assert "💭 上下文：128000 tokens" in reply
    assert "Model: deepseek-chat" not in reply
    assert "Provider: deepseek" not in reply
    assert "Context: 128000 tokens" not in reply


def test_new_reset_tip_localizes_existing_english_locale_tip(monkeypatch) -> None:
    reply = _render_reset_reply(monkeypatch, "Tip: keep gateway healthy")

    assert "gateway.reset.tip" not in reply
    assert "Tip: keep gateway healthy" not in reply
    assert "💫 提示：新会话已就绪，可以直接发送下一条消息。" in reply
