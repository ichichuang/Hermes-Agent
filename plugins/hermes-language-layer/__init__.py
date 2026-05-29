from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from typing import Any


LIB_ROOT = Path("/Users/cc/.hermes/ops/lib")
if str(LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(LIB_ROOT))

from language_layer import format_advisory_context, normalize_to_task_card, render_b_layer, truthy_env


PLUGIN_VERSION = "0.2.0-b-layer-gated"
DEFAULT_CONFIG_PATH = Path("/Users/cc/.hermes/lang-layer/config.json")


def _config_path() -> Path:
    return Path(os.environ.get("HERMES_LANG_LAYER_CONFIG", str(DEFAULT_CONFIG_PATH))).expanduser()


def _load_runtime_config() -> dict[str, Any]:
    path = _config_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _enabled(config_key: str, env_name: str, *, default: bool = False) -> bool:
    if env_name in os.environ:
        return truthy_env(env_name)
    value = _load_runtime_config().get(config_key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _runtime_model() -> str | None:
    if os.environ.get("HERMES_LANG_LAYER_MODEL"):
        return os.environ.get("HERMES_LANG_LAYER_MODEL")
    value = _load_runtime_config().get("model")
    return value if isinstance(value, str) and value.strip() else None


def _runtime_timeout_ms() -> int:
    raw = os.environ.get("HERMES_LANG_LAYER_TIMEOUT_MS")
    if raw is None:
        raw = _load_runtime_config().get("timeout_ms")
    try:
        return max(int(raw), 100)
    except (TypeError, ValueError):
        return 5000


def _local_model_enabled() -> bool:
    return _enabled("local_model_enabled", "HERMES_LANG_LAYER_LOCAL_MODEL", default=False)


def transform_llm_output(*args: Any, **kwargs: Any) -> str | None:
    if not _enabled("b_enabled", "HERMES_LANG_LAYER_B_ENABLED", default=False):
        return None
    response_text = kwargs.get("response_text")
    if response_text is None and args:
        response_text = args[0]
    if not isinstance(response_text, str):
        return None
    result = render_b_layer(
        response_text,
        use_ollama=_local_model_enabled(),
        model=_runtime_model(),
        timeout_ms=_runtime_timeout_ms(),
    )
    return result.text if result.changed else None


def pre_llm_call(*args: Any, **kwargs: Any) -> dict[str, str] | None:
    if not _enabled("a_enabled", "HERMES_LANG_LAYER_A_ENABLED", default=False):
        return None
    user_message = kwargs.get("user_message")
    if user_message is None and args:
        user_message = args[0]
    if not isinstance(user_message, str):
        return None
    result = normalize_to_task_card(
        user_message,
        use_ollama=_local_model_enabled(),
        model=_runtime_model(),
        timeout_ms=_runtime_timeout_ms(),
    )
    if result.card is None:
        return None
    return {"context": format_advisory_context(user_message, result.card)}


def register(ctx: Any) -> None:
    ctx.register_hook("transform_llm_output", transform_llm_output)
    ctx.register_hook("pre_llm_call", pre_llm_call)
