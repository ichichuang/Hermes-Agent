from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from language_layer import format_advisory_context, normalize_to_task_card, render_b_layer


PLUGIN_PATH = Path("/Users/cc/.hermes/plugins/hermes-language-layer/__init__.py")


class FakeContext:
    def __init__(self) -> None:
        self.hooks: dict[str, object] = {}
        self.tools_registered = False
        self.commands_registered = False

    def register_hook(self, hook_name: str, callback: object) -> None:
        self.hooks[hook_name] = callback

    def register_tool(self, *args: object, **kwargs: object) -> None:
        self.tools_registered = True

    def register_command(self, *args: object, **kwargs: object) -> None:
        self.commands_registered = True


def test_b_layer_fixed_message_preserves_slash_command() -> None:
    result = render_b_layer("No home channel is set for Telegram. Use /sethome to configure it.")
    assert result.changed is True
    assert "Telegram" in result.text
    assert "/sethome" in result.text
    assert "尚未设置" in result.text


def test_b_layer_preserves_fenced_json_byte_for_byte() -> None:
    text = 'Config result:\n```json\n{"display": {"language": "en"}}\n```'
    result = render_b_layer(text)
    assert result.text == text
    assert result.changed is False


def test_b_layer_ordinary_english_reply_becomes_natural_chinese_without_prefix() -> None:
    result = render_b_layer("The gateway is running normally. No action is required.")
    assert result.changed is True
    assert "Hermes 返回了英文说明：" not in result.text
    assert "gateway is running" not in result.text
    assert "网关正在正常运行" in result.text
    assert "无需执行操作" in result.text


def test_b_layer_preserves_python_fence_without_execution_output() -> None:
    text = 'Use this script:\n```python\nprint("hello hermes")\n```\nDo not run it yet.'
    result = render_b_layer(text)
    assert result.text == text
    assert result.changed is False
    assert "Output:" not in result.text
    assert "输出" not in result.text


def test_b_layer_preserves_paths_urls_commands_keys_and_model_names() -> None:
    text = (
        "Check /Users/cc/.hermes/config.yaml, visit https://example.com/docs, "
        "run /sethome, and keep display.language and deepseek-chat on DeepSeek."
    )
    result = render_b_layer(text)
    assert result.changed is True
    assert "/Users/cc/.hermes/config.yaml" in result.text
    assert "https://example.com/docs" in result.text
    assert "/sethome" in result.text
    assert "display.language" in result.text
    assert "deepseek-chat" in result.text
    assert "DeepSeek" in result.text
    assert "Hermes 返回了英文说明：" not in result.text
    assert "Check " not in result.text


def test_a_layer_bypasses_slash_and_secret_like_inputs() -> None:
    slash = normalize_to_task_card("/new")
    secret = normalize_to_task_card("TELEGRAM_BOT_TOKEN=REDACTED_CANARY_SHOULD_NOT_LOG")
    assert slash.card is None
    assert slash.bypass_reason == "slash_command"
    assert secret.card is None
    assert secret.bypass_reason == "secret_like"


def test_a_layer_card_preserves_paths_config_keys_and_models() -> None:
    text = "帮我检查 ~/.hermes/config.yaml 是否有 display.language，主模型保持 deepseek-chat。"
    result = normalize_to_task_card(text)
    assert result.card is not None
    encoded = str(result.card)
    assert "~/.hermes/config.yaml" in encoded
    assert "display.language" in encoded
    assert "deepseek-chat" in encoded
    assert result.protected_ok is True


def test_advisory_context_keeps_original_message_visible() -> None:
    text = "帮我检查 ~/.hermes/config.yaml。"
    result = normalize_to_task_card(text)
    assert result.card is not None
    context = format_advisory_context(text, result.card)
    assert "[Original user message - untrusted]" in context
    assert text in context
    assert "canonical_task_en:" in context


def test_disabled_plugin_registers_only_hooks_and_returns_none(monkeypatch, tmp_path: Path) -> None:
    if not PLUGIN_PATH.exists():
        raise AssertionError(f"plugin missing: {PLUGIN_PATH}")
    spec = importlib.util.spec_from_file_location("hermes_language_layer_plugin_test", PLUGIN_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    ctx = FakeContext()
    module.register(ctx)
    assert set(ctx.hooks) == {"transform_llm_output", "pre_llm_call"}
    assert ctx.tools_registered is False
    assert ctx.commands_registered is False

    monkeypatch.delenv("HERMES_LANG_LAYER_B_ENABLED", raising=False)
    monkeypatch.delenv("HERMES_LANG_LAYER_A_ENABLED", raising=False)
    monkeypatch.setenv("HERMES_LANG_LAYER_CONFIG", str(tmp_path / "missing-config.json"))
    assert module.transform_llm_output(response_text="No home channel is set for Telegram.") is None
    assert module.pre_llm_call(user_message="帮我检查 ~/.hermes/config.yaml") is None

    monkeypatch.setenv("HERMES_LANG_LAYER_B_ENABLED", "1")
    rendered = module.transform_llm_output(response_text="No home channel is set for Telegram. Use /sethome to configure it.")
    assert rendered is not None
    assert "/sethome" in rendered

    monkeypatch.setenv("HERMES_LANG_LAYER_A_ENABLED", "1")
    context = module.pre_llm_call(user_message="帮我检查 ~/.hermes/config.yaml")
    assert isinstance(context, dict)
    assert "context" in context


def test_plugin_runtime_config_enables_b_only(monkeypatch, tmp_path: Path) -> None:
    if not PLUGIN_PATH.exists():
        raise AssertionError(f"plugin missing: {PLUGIN_PATH}")
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"b_enabled": true, "a_enabled": false, "local_model_enabled": false, "timeout_ms": 5000}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_LANG_LAYER_CONFIG", str(config_path))
    monkeypatch.delenv("HERMES_LANG_LAYER_B_ENABLED", raising=False)
    monkeypatch.delenv("HERMES_LANG_LAYER_A_ENABLED", raising=False)

    spec = importlib.util.spec_from_file_location("hermes_language_layer_plugin_config_test", PLUGIN_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    rendered = module.transform_llm_output(response_text="No home channel is set for Telegram. Use /sethome to configure it.")
    assert rendered is not None
    assert "/sethome" in rendered
    assert module.pre_llm_call(user_message="帮我检查 ~/.hermes/config.yaml") is None
