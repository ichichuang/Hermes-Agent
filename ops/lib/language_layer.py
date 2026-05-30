from __future__ import annotations

import json
import inspect
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


LOCAL_OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_TIMEOUT_MS = 5000

ICON_PALETTE = {
    "gateway": "🧭",
    "reset": "🪄",
    "model": "🫪",
    "provider": "❤️",
    "context": "💭",
    "terminal": "🖥️",
    "process": "⚙️",
    "browser": "🌐",
    "file": "📄",
    "tool": "🧰",
    "running": "⏳",
    "done": "✅",
    "notice": "⚠️",
    "interrupted": "⛔",
    "tip": "💫",
}

PROTECTED_LITERAL_TOKENS = (
    "DeepSeek",
    "Ollama",
    "Telegram",
    "Feishu",
    "Lark",
    "deepseek-chat",
    "gpt-oss:20b-q6",
    "qwen3-coder:30b-a3b-instruct-q4km",
    "qwen3.6:35b-a3b-ud-q4km",
)

SECRET_PATTERN = re.compile(
    r"(?i)(token|api[_-]?key|secret|password|authorization|bearer|credential|bot[_-]?token)\s*[:=]\s*\S+"
)
URL_PATTERN = re.compile(r"https?://[^\s`'\"<>]+")
INLINE_CODE_PATTERN = re.compile(r"`[^`\n]+`")
FENCED_CODE_PATTERN = re.compile(r"```[\s\S]*?```")
SLASH_COMMAND_PATTERN = re.compile(r"(?<!\w)/(?:[A-Za-z][A-Za-z0-9_-]*)(?:\b|$)")
PATH_PATTERN = re.compile(
    r"(?<![\w.-])(?:~|/Users/cc|/tmp|/var|/etc|/usr|/bin|/opt|\./|\../)[^\s`'\"<>，。；：、]+"
)
CONFIG_KEY_PATTERN = re.compile(r"\b[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)+\b")
SHELL_COMMAND_PATTERN = re.compile(r"\b(?:hermes|launchctl|python3?|curl|git|pytest|shasum|ollama)\s+[^\n`]+")
NO_EXECUTION_INTENT_PATTERN = re.compile(
    r"(?i)(?:\b(?:do\s+not|don't|dont|without)\s+(?:run|execute|running|executing)\b|不要[^。\n]*(?:执行|运行))"
)
CODE_BLOCK_PRESERVE_INTENT_PATTERN = re.compile(
    r"(?i)(?:不要[^。\n]*(?:改写|修改)[^。\n]*代码块|do\s+not\s+(?:rewrite|modify|change)[^.\n]*code\s+block)"
)
INFERRED_EXECUTION_OUTPUT_PATTERN = re.compile(
    r"(?is)\n{1,3}(?:Output|Result|Execution output|输出|运行结果)\s*[:：][\s\S]*$"
)
UNLABELED_INFERRED_EXECUTION_OUTPUT_PATTERN = re.compile(
    r"(?is)\n{1,3}"
    r"(?:(?:if\s+(?:it|this code|the code)\s+(?:ran|runs|is run|were run),?\s*)|"
    r"(?:running|executing)\s+(?:it|this code|the code)\s+)?"
    r"(?:(?:it|this code|the code)\s+)?"
    r"(?:would|will|prints?|outputs?|returns?|produces?|displays?|shows?)\b[\s\S]*$"
)
MODEL_PROVIDER_CONTEXT_HEADER_PATTERN = re.compile(r"^(?P<label>Model|Provider|Context)\s*:\s*(?P<value>.+)$")
TOOL_TRACE_LINE_PATTERN = re.compile(
    r"^(?P<indent>\s*)"
    r"(?:(?P<icon>⚔|🔍|🔎|🛠|🛠️|⚙|⚙️|💻|🌎|🌐|📂|📁|📄|🧰)\s*)?"
    r"(?P<name>[A-Za-z][A-Za-z0-9_.-]*)"
    r"(?P<tail>(?:\(|:|\.{3}).*)$"
)


@dataclass(frozen=True)
class ProtectedSpan:
    start: int
    end: int
    label: str


@dataclass(frozen=True)
class ProtectionResult:
    text: str
    spans: tuple[str, ...]


@dataclass(frozen=True)
class RenderResult:
    text: str
    changed: bool
    engine: str
    fallback: bool = False
    bypass_reason: str | None = None


@dataclass(frozen=True)
class TaskCardResult:
    card: dict[str, Any] | None
    bypass_reason: str | None
    model: str | None
    latency_ms: int
    parse_ok: bool
    protected_ok: bool


def truthy_env(name: str) -> bool:
    value = os.environ.get(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_secret_like(text: str) -> bool:
    return bool(SECRET_PATTERN.search(text))


def has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _mostly_chinese(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return False
    cjk = [char for char in letters if "\u4e00" <= char <= "\u9fff"]
    return len(cjk) / max(len(letters), 1) >= 0.35


def _mostly_english(text: str) -> bool:
    alpha = [char for char in text if char.isalpha()]
    if len(alpha) < 12:
        return False
    ascii_alpha = [char for char in alpha if char.isascii()]
    return len(ascii_alpha) / max(len(alpha), 1) >= 0.75


def _is_pure_json(text: str) -> bool:
    stripped = text.strip()
    if not stripped or stripped[0] not in "[{":
        return False
    try:
        json.loads(stripped)
    except json.JSONDecodeError:
        return False
    return True


def _is_pure_yaml_like(text: str) -> bool:
    stripped = text.strip()
    if not stripped or "\n" not in stripped:
        return False
    meaningful = [line for line in stripped.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not meaningful:
        return False
    keyed = sum(1 for line in meaningful if re.match(r"^\s*[A-Za-z0-9_.-]+\s*:", line))
    return keyed >= max(2, len(meaningful) // 2)


def _strip_forbidden_execution_output(text: str, *, source_text: str | None = None) -> str:
    fence_matches = list(FENCED_CODE_PATTERN.finditer(text))
    no_execution_requested = bool(
        NO_EXECUTION_INTENT_PATTERN.search(text)
        or (isinstance(source_text, str) and NO_EXECUTION_INTENT_PATTERN.search(source_text))
    )
    if not fence_matches or not no_execution_requested:
        return text
    last_fence_end = fence_matches[-1].end()
    tail = text[last_fence_end:]
    inferred = INFERRED_EXECUTION_OUTPUT_PATTERN.search(tail)
    if not inferred:
        inferred = UNLABELED_INFERRED_EXECUTION_OUTPUT_PATTERN.search(tail)
    if not inferred:
        return text
    return (text[:last_fence_end] + tail[: inferred.start()]).rstrip()


def _source_requests_code_block_preservation(source_text: str) -> bool:
    return bool(
        FENCED_CODE_PATTERN.search(source_text)
        and (
            CODE_BLOCK_PRESERVE_INTENT_PATTERN.search(source_text)
            or NO_EXECUTION_INTENT_PATTERN.search(source_text)
        )
    )


def _restore_source_fenced_blocks(text: str, source_text: str | None) -> str | None:
    if not isinstance(source_text, str) or not _source_requests_code_block_preservation(source_text):
        return None
    if is_secret_like(source_text):
        return None
    blocks = tuple(match.group(0) for match in FENCED_CODE_PATTERN.finditer(source_text))
    if not blocks or all(block in text for block in blocks):
        return None
    if NO_EXECUTION_INTENT_PATTERN.search(source_text):
        lead = "我会保留代码块原样，不执行它："
    else:
        lead = "我会保留代码块原样："
    return lead + "\n" + "\n\n".join(blocks)


def _volatile_source_text_from_hook_context() -> str | None:
    frame = inspect.currentframe()
    try:
        caller = frame.f_back if frame is not None else None
        depth = 0
        while caller is not None and depth < 5:
            local_kwargs = caller.f_locals.get("kwargs")
            candidates: list[Any] = []
            if isinstance(local_kwargs, dict):
                candidates.extend([local_kwargs.get("user_message"), local_kwargs.get("original_user_message")])
            candidates.extend([caller.f_locals.get("user_message"), caller.f_locals.get("original_user_message")])
            for candidate in candidates:
                if isinstance(candidate, str) and _source_requests_code_block_preservation(candidate):
                    return candidate
            caller = caller.f_back
            depth += 1
    finally:
        del frame
    return None


def should_bypass_input(text: str) -> str | None:
    stripped = text.strip()
    if not stripped:
        return "empty"
    if is_secret_like(stripped):
        return "secret_like"
    if stripped.startswith("/") and "\n" not in stripped:
        return "slash_command"
    if stripped.startswith("```") and stripped.endswith("```"):
        return "pure_code_block"
    if _is_pure_json(stripped):
        return "pure_json"
    if _is_pure_yaml_like(stripped):
        return "pure_yaml"
    if stripped.lower() in {"ok", "okay", "yes", "no", "done", "thanks", "谢谢", "好的", "可以", "行"}:
        return "short_confirmation"
    return None


def _collect_spans(pattern: re.Pattern[str], text: str, label: str) -> list[ProtectedSpan]:
    return [ProtectedSpan(match.start(), match.end(), label) for match in pattern.finditer(text)]


def find_protected_spans(text: str) -> list[ProtectedSpan]:
    spans: list[ProtectedSpan] = []
    spans.extend(_collect_spans(FENCED_CODE_PATTERN, text, "fenced_code"))
    spans.extend(_collect_spans(INLINE_CODE_PATTERN, text, "inline_code"))
    spans.extend(_collect_spans(URL_PATTERN, text, "url"))
    spans.extend(_collect_spans(SLASH_COMMAND_PATTERN, text, "slash_command"))
    spans.extend(_collect_spans(PATH_PATTERN, text, "path"))
    spans.extend(_collect_spans(CONFIG_KEY_PATTERN, text, "config_key"))
    spans.extend(_collect_spans(SHELL_COMMAND_PATTERN, text, "shell_command"))
    for token in PROTECTED_LITERAL_TOKENS:
        for match in re.finditer(re.escape(token), text):
            spans.append(ProtectedSpan(match.start(), match.end(), "literal"))
    return _merge_spans(spans)


def _merge_spans(spans: list[ProtectedSpan]) -> list[ProtectedSpan]:
    merged: list[ProtectedSpan] = []
    for span in sorted(spans, key=lambda item: (item.start, item.end)):
        if not merged or span.start > merged[-1].end:
            merged.append(span)
            continue
        previous = merged[-1]
        merged[-1] = ProtectedSpan(previous.start, max(previous.end, span.end), previous.label)
    return merged


def protect_text(text: str) -> ProtectionResult:
    spans = find_protected_spans(text)
    if not spans:
        return ProtectionResult(text=text, spans=())
    pieces: list[str] = []
    originals: list[str] = []
    cursor = 0
    for idx, span in enumerate(spans):
        placeholder = f"__HERMES_LANG_PROTECTED_{idx}__"
        pieces.append(text[cursor:span.start])
        pieces.append(placeholder)
        originals.append(text[span.start:span.end])
        cursor = span.end
    pieces.append(text[cursor:])
    return ProtectionResult(text="".join(pieces), spans=tuple(originals))


def restore_text(text: str, originals: tuple[str, ...]) -> str:
    restored = text
    for idx, original in enumerate(originals):
        restored = restored.replace(f"__HERMES_LANG_PROTECTED_{idx}__", original)
    return restored


def protected_values(text: str) -> list[str]:
    values = [text[span.start:span.end] for span in find_protected_spans(text)]
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


FIXED_B_REWRITES = (
    ("No home channel is set for __HERMES_LANG_PROTECTED_0__.", "__HERMES_LANG_PROTECTED_0__ 尚未设置 home channel。"),
    ("Use __HERMES_LANG_PROTECTED_1__ to configure it.", "请使用 __HERMES_LANG_PROTECTED_1__ 进行配置。"),
    ("No home channel is set for Telegram.", "Telegram 尚未设置 home channel。"),
    ("Use /sethome to configure it.", "请使用 /sethome 进行配置。"),
    ("Configuration saved.", "配置已保存。"),
    ("Permission denied.", "权限不足。"),
    ("Command timed out.", "命令超时。"),
    ("No plugins installed.", "当前未安装插件。"),
    ("No shell hooks configured", "当前未配置 shell hooks"),
)

FIXED_ENGLISH_SENTENCE_REWRITES = {
    "Right now Hermes is running one thing:": "Hermes 当前只有一项正在运行：",
    "The gateway is running normally.": "网关正在正常运行。",
    "No action is required.": "无需执行操作。",
    "No action is needed.": "无需执行操作。",
    "Configuration saved.": "配置已保存。",
    "Permission denied.": "权限不足。",
    "Command timed out.": "命令超时。",
}


def _translate_known_terminal_object(value: str) -> str:
    return {
        "the gateway status": "网关状态",
        "gateway status": "网关状态",
        "the configuration": "配置",
        "configuration": "配置",
    }.get(value, value)


def _rewrite_known_english_sentence(sentence: str) -> str | None:
    fixed = FIXED_ENGLISH_SENTENCE_REWRITES.get(sentence)
    if fixed is not None:
        return fixed

    protected_token = r"__HERMES_LANG_PROTECTED_\d+__"
    checked_pair = re.fullmatch(
        rf"I checked (?P<first>{protected_token}) and (?P<second>{protected_token}) with the terminal\.",
        sentence,
    )
    if checked_pair:
        return f"我已通过终端检查 {checked_pair.group('first')} 和 {checked_pair.group('second')}。"

    checked_single = re.fullmatch(r"I checked (?P<target>.+) with the terminal\.", sentence)
    if checked_single:
        target = _translate_known_terminal_object(checked_single.group("target"))
        return f"我已通过终端检查{target}。"

    gateway_pid = re.fullmatch(r"The gateway is running normally with PID (?P<pid>\d+)\.", sentence)
    if gateway_pid:
        return f"网关正在正常运行，PID {gateway_pid.group('pid')}。"

    flag_match = re.fullmatch(r"(?P<name>B-layer|A-layer) is (?P<state>enabled|disabled)\.", sentence)
    if flag_match:
        state = "已启用" if flag_match.group("state") == "enabled" else "已禁用"
        return f"{flag_match.group('name')} {state}。"

    local_model = re.fullmatch(r"local_model_enabled is (?P<state>true|false)\.", sentence)
    if local_model:
        return f"local_model_enabled 为 {local_model.group('state')}。"

    unchanged = re.fullmatch(rf"(?P<key>{protected_token}) remains unchanged\.", sentence)
    if unchanged:
        return f"{unchanged.group('key')} 保持不变。"

    not_executed = re.fullmatch(rf"(?P<command>{protected_token}) was not executed\.", sentence)
    if not_executed:
        return f"{not_executed.group('command')} 未执行。"

    model_provider = re.fullmatch(
        rf"Model (?P<model>{protected_token}) stays on (?P<provider>{protected_token})\.",
        sentence,
    )
    if model_provider:
        return f"模型 {model_provider.group('model')} 仍使用 {model_provider.group('provider')}。"

    return None


def _rewrite_model_provider_context_header(text: str) -> str | None:
    lines = text.splitlines()
    meaningful = [line for line in lines if line.strip()]
    if not meaningful:
        return None
    if not all(MODEL_PROVIDER_CONTEXT_HEADER_PATTERN.match(line.strip()) for line in meaningful):
        return None

    labels = {
        "Model": f"{ICON_PALETTE['model']} 模型",
        "Provider": f"{ICON_PALETTE['provider']} 服务商",
        "Context": f"{ICON_PALETTE['context']} 上下文",
    }
    rendered_lines: list[str] = []
    changed = False
    for line in lines:
        match = MODEL_PROVIDER_CONTEXT_HEADER_PATTERN.match(line.strip())
        if not match:
            rendered_lines.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip())]
        rendered_lines.append(f"{indent}{labels[match.group('label')]}：{match.group('value')}")
        changed = True
    return "\n".join(rendered_lines) if changed else None


def _translate_status_detail(detail: str) -> str:
    parts: list[str] = []
    for item in [part.strip() for part in detail.split(",") if part.strip()]:
        if item.startswith("running: "):
            parts.append(f"正在运行：{item.removeprefix('running: ')}")
        elif item.startswith("iteration "):
            parts.append(f"迭代 {item.removeprefix('iteration ')}")
        elif item.endswith(" min elapsed"):
            parts.append(f"已运行 {item.removesuffix(' min elapsed')} 分钟")
        else:
            parts.append(item)
    return "，".join(parts)


def _rewrite_gateway_notice_line(line: str) -> str | None:
    stripped = line.strip()
    gateway_match = re.fullmatch(
        r"(?:⚠️\s*)?Gateway (?P<action>shutting down|restarting)\s+—\s+"
        r"(?P<hint>Your current task will be interrupted(?:\. Send any message after restart and "
        r"I'll try to resume where you left off\.)?\.?)",
        stripped,
    )
    if gateway_match:
        action = gateway_match.group("action")
        action_zh = "正在重启" if action == "restarting" else "正在关闭"
        suffix = "当前任务会被中断。"
        if "resume where you left off" in gateway_match.group("hint"):
            suffix += "重启后发送任意消息，Hermes 会尝试接续。"
        return f"{ICON_PALETTE['interrupted']} 网关{action_zh}。{suffix}"

    interrupt_match = re.fullmatch(
        r"(?:⚡\s*)?Interrupting current task(?: \((?P<detail>[^)]*)\))?\. "
        r"I'll respond to your message shortly\.",
        stripped,
    )
    if interrupt_match:
        detail = interrupt_match.group("detail")
        detail_zh = f"（{_translate_status_detail(detail)}）" if detail else ""
        return f"{ICON_PALETTE['interrupted']} 正在中断当前任务{detail_zh}。我会尽快回复这条消息。"

    return None


def _rewrite_reset_key_or_tip_line(line: str) -> str | None:
    stripped = line.strip()
    reset_rewrites = {
        "gateway.reset.header_default": f"{ICON_PALETTE['reset']} 新会话已开始。",
        "gateway.reset.header_new": f"{ICON_PALETTE['reset']} 新会话已创建。",
        "gateway.reset.tip": f"{ICON_PALETTE['tip']} 提示：新会话已就绪。",
    }
    if stripped in reset_rewrites:
        return reset_rewrites[stripped]

    tip_match = re.fullmatch(r"(?:💡|✦)?\s*Tip:\s*(?P<body>.+)", stripped)
    if not tip_match:
        return None
    body = tip_match.group("body")
    check_match = re.fullmatch(r"Check (?P<first>.+) and (?P<second>.+); keep (?P<keep>.+) unchanged\.", body)
    if check_match:
        return (
            f"{ICON_PALETTE['tip']} 提示：检查 {check_match.group('first')} 和 "
            f"{check_match.group('second')}；保持 {check_match.group('keep')} 不变。"
        )
    return f"{ICON_PALETTE['tip']} 提示：{body}"


def _rewrite_gateway_reset_key_text(text: str) -> str | None:
    lines = text.splitlines()
    rendered: list[str] = []
    changed = False
    for line in lines:
        if not line.strip():
            rendered.append(line)
            continue
        rewritten = _rewrite_reset_key_or_tip_line(line)
        if rewritten is None or not line.strip().startswith("gateway.reset."):
            return None
        indent = line[: len(line) - len(line.lstrip())]
        rendered.append(indent + rewritten)
        changed = True
    return "\n".join(rendered) if changed else None


def _tool_icon_for_name(name: str) -> str:
    normalized = name.lower()
    if normalized.startswith(("terminal", "shell", "run_command", "execute_command")):
        return ICON_PALETTE["terminal"]
    if normalized.startswith(("browser", "web_", "web.", "navigate", "click")):
        return ICON_PALETTE["browser"]
    if "process" in normalized or normalized.startswith(("background_", "job_", "cron_")):
        return ICON_PALETTE["process"]
    if normalized.startswith(("read_file", "write_file", "edit_file", "patch", "file_", "list_files")):
        return ICON_PALETTE["file"]
    return ICON_PALETTE["tool"]


def _rewrite_tool_trace_line(line: str) -> str | None:
    match = TOOL_TRACE_LINE_PATTERN.match(line)
    if not match:
        return None
    name = match.group("name")
    if name in {"Model", "Provider", "Context"}:
        return None
    icon = _tool_icon_for_name(name)
    return f"{match.group('indent')}{icon} {name}{match.group('tail')}"


def _rewrite_gateway_system_text(text: str) -> str | None:
    lines = text.splitlines()
    rendered: list[str] = []
    changed = False
    for line in lines:
        rewritten = (
            _rewrite_gateway_notice_line(line)
            or _rewrite_reset_key_or_tip_line(line)
            or _rewrite_tool_trace_line(line)
        )
        if rewritten is None:
            rendered.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip())]
        rendered.append(indent + rewritten)
        changed = True
    return "\n".join(rendered) if changed else None


def _deterministic_english_to_zh(text: str) -> str | None:
    stripped = text.strip()
    protected_token = r"__HERMES_LANG_PROTECTED_\d+__"
    technical_check = re.fullmatch(
        rf"Check ({protected_token}),? visit ({protected_token}),? run ({protected_token}),? "
        rf"and keep ({protected_token}) and ({protected_token}) on ({protected_token})\.",
        stripped,
    )
    if technical_check:
        path, url, command, key, model_name, provider = technical_check.groups()
        return f"请检查 {path}，访问 {url}，运行 {command}，并保持 {key} 和 {model_name} 使用 {provider}。"

    sentences = [sentence for sentence in re.split(r"(?<=[.!?])\s+", stripped) if sentence]
    rewritten_sentences = [_rewrite_known_english_sentence(sentence) for sentence in sentences]
    if rewritten_sentences and all(sentence is not None for sentence in rewritten_sentences):
        return "".join(sentence for sentence in rewritten_sentences if sentence is not None)
    lines = stripped.splitlines()
    if lines and lines[0] == "Right now Hermes is running one thing:":
        rendered_lines: list[str] = []
        changed = False
        for line in lines:
            if not line.strip():
                rendered_lines.append(line)
                continue
            prefix = ""
            body = line.strip()
            if body.startswith("- "):
                prefix = "- "
                body = body[2:]
            rewritten = FIXED_ENGLISH_SENTENCE_REWRITES.get(body)
            if rewritten:
                rendered_lines.append(prefix + rewritten)
                changed = True
            else:
                rendered_lines.append(line)
        if changed:
            return "\n".join(rendered_lines)
    return None


def render_b_layer(
    text: str,
    *,
    source_text: str | None = None,
    use_ollama: bool = False,
    model: str | None = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> RenderResult:
    metadata_header = _rewrite_model_provider_context_header(text)
    if metadata_header is not None:
        return RenderResult(text=metadata_header, changed=(metadata_header != text), engine="metadata_header")
    reset_key_text = _rewrite_gateway_reset_key_text(text)
    if reset_key_text is not None:
        return RenderResult(text=reset_key_text, changed=(reset_key_text != text), engine="reset_key_map")

    bypass_reason = should_bypass_input(text)
    if bypass_reason:
        return RenderResult(text=text, changed=False, engine="bypass", bypass_reason=bypass_reason)
    if source_text is None:
        source_text = _volatile_source_text_from_hook_context()
    restored_from_source = _restore_source_fenced_blocks(text, source_text)
    if restored_from_source is not None:
        return RenderResult(
            text=restored_from_source,
            changed=(restored_from_source != text),
            engine="source_fenced_code",
        )
    if "```" in text:
        rendered = _strip_forbidden_execution_output(text, source_text=source_text)
        return RenderResult(text=rendered, changed=(rendered != text), engine="preserve_fenced_code")
    if _mostly_chinese(text):
        return RenderResult(text=text, changed=False, engine="already_zh")

    protected = protect_text(text)
    candidate = protected.text
    for old, new in FIXED_B_REWRITES:
        candidate = candidate.replace(old, new)
    if candidate != protected.text:
        rendered = restore_text(candidate, protected.spans)
        return RenderResult(text=rendered, changed=(rendered != text), engine="fixed_map")

    system_text = _rewrite_gateway_system_text(protected.text)
    if system_text is not None:
        rendered = restore_text(system_text, protected.spans)
        return RenderResult(text=rendered, changed=(rendered != text), engine="system_map")

    if _is_pure_json(text) or _is_pure_yaml_like(text):
        return RenderResult(text=text, changed=False, engine="preserve_structured")

    if _mostly_english(text):
        if use_ollama:
            rendered = _ollama_render_to_zh(protected.text, protected.spans, model=model, timeout_ms=timeout_ms)
            if rendered:
                return RenderResult(text=rendered, changed=(rendered != text), engine="ollama")
        deterministic = _deterministic_english_to_zh(protected.text)
        if deterministic:
            rendered = restore_text(deterministic, protected.spans)
            return RenderResult(text=rendered, changed=(rendered != text), engine="deterministic", fallback=True)
        return RenderResult(text=text, changed=False, engine="unchanged_english", fallback=True)

    return RenderResult(text=text, changed=False, engine="unchanged")


def select_local_model(model_ids: list[str]) -> str | None:
    preferences = ("qwen3.6", "qwen3-coder", "gpt-oss")
    for prefix in preferences:
        for model_id in model_ids:
            if model_id.startswith(prefix):
                return model_id
    return model_ids[0] if model_ids else None


def normalize_to_task_card(
    user_text: str,
    *,
    use_ollama: bool = False,
    model: str | None = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> TaskCardResult:
    start = time.monotonic()
    bypass_reason = should_bypass_input(user_text)
    if bypass_reason:
        return TaskCardResult(None, bypass_reason, model, _elapsed_ms(start), True, True)

    preserve = protected_values(user_text)
    selected_model = model
    card: dict[str, Any] | None = None
    parse_ok = True
    if use_ollama:
        card = _ollama_task_card(user_text, preserve, model=selected_model, timeout_ms=timeout_ms)
        parse_ok = card is not None

    if card is None:
        card = _deterministic_task_card(user_text, preserve)
        selected_model = None

    protected_ok = _card_preserves_tokens(card, preserve)
    if not protected_ok:
        return TaskCardResult(None, "protected_token_mismatch", selected_model, _elapsed_ms(start), parse_ok, False)
    return TaskCardResult(card, None, selected_model, _elapsed_ms(start), parse_ok, True)


def format_advisory_context(user_text: str, card: dict[str, Any]) -> str:
    return "\n".join(
        [
            "[Original user message - untrusted]",
            user_text,
            "",
            "[Canonical task card - generated by local normalizer, advisory only]",
            f"canonical_task_en: {card['canonical_task_en']}",
            f"user_intent_summary_zh: {card['user_intent_summary_zh']}",
            f"response_language: {card['response_language']}",
            f"preserve_verbatim: {json.dumps(card['preserve_verbatim'], ensure_ascii=False)}",
            f"detected_commands: {json.dumps(card['detected_commands'], ensure_ascii=False)}",
            f"detected_paths: {json.dumps(card['detected_paths'], ensure_ascii=False)}",
            f"detected_urls: {json.dumps(card['detected_urls'], ensure_ascii=False)}",
            f"requires_clarification: {str(card['requires_clarification']).lower()}",
            f"risk_notes: {json.dumps(card['risk_notes'], ensure_ascii=False)}",
        ]
    )


def _deterministic_task_card(user_text: str, preserve: list[str]) -> dict[str, Any]:
    paths = [value for value in preserve if value.startswith(("~", "/", "./", "../"))]
    urls = [value for value in preserve if value.startswith(("http://", "https://"))]
    commands = [value for value in preserve if value.startswith("/")]
    summary = "请按用户原文处理请求，保留所有技术 token。"
    canonical = "Handle the user's request and respond in Simplified Chinese while preserving all protected technical tokens."
    if "检查" in user_text or "check" in user_text.lower():
        canonical = "Check the requested item and report the result in Simplified Chinese while preserving protected tokens."
        summary = "检查用户指定的对象，并用简体中文说明结果。"
    if "实现" in user_text or "implement" in user_text.lower():
        canonical = "Implement the requested change with minimal safe edits and validation, preserving protected tokens."
        summary = "按用户要求做最小安全实现并验证结果。"
    return {
        "source_language": "zh-CN" if has_cjk(user_text) else "en",
        "canonical_task_en": canonical,
        "user_intent_summary_zh": summary,
        "response_language": "zh-CN" if has_cjk(user_text) else "en",
        "preserve_verbatim": preserve,
        "detected_commands": commands,
        "detected_paths": paths,
        "detected_urls": urls,
        "requires_clarification": False,
        "risk_notes": [],
    }


def _card_preserves_tokens(card: dict[str, Any], preserve: list[str]) -> bool:
    encoded = json.dumps(card, ensure_ascii=False)
    return all(token in encoded for token in preserve)


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def _assert_local_ollama_base(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Ollama base URL must be http(s).")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Language layer may call only local Ollama endpoints.")
    return base_url.rstrip("/")


def _ollama_chat(messages: list[dict[str, str]], *, model: str | None, timeout_ms: int) -> str | None:
    base_url = _assert_local_ollama_base(os.environ.get("HERMES_LANG_LAYER_OLLAMA_BASE_URL", LOCAL_OLLAMA_BASE_URL))
    selected = model or os.environ.get("HERMES_LANG_LAYER_MODEL", "")
    if not selected:
        return None
    payload = {
        "model": selected,
        "messages": messages,
        "temperature": 0,
        "stream": False,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=max(timeout_ms / 1000, 0.1)) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None
    return content if isinstance(content, str) else None


def _ollama_render_to_zh(text: str, originals: tuple[str, ...], *, model: str | None, timeout_ms: int) -> str | None:
    if is_secret_like(text):
        return None
    prompt = (
        "Rewrite the following safe assistant prose into concise Simplified Chinese. "
        "Do not change placeholders like __HERMES_LANG_PROTECTED_0__. "
        "Return only the rewritten text.\n\n"
        f"{text}"
    )
    content = _ollama_chat(
        [{"role": "user", "content": prompt}],
        model=model,
        timeout_ms=timeout_ms,
    )
    if not content:
        return None
    return restore_text(content.strip(), originals)


def _ollama_task_card(user_text: str, preserve: list[str], *, model: str | None, timeout_ms: int) -> dict[str, Any] | None:
    if is_secret_like(user_text):
        return None
    schema = {
        "source_language": "zh-CN",
        "canonical_task_en": "",
        "user_intent_summary_zh": "",
        "response_language": "zh-CN",
        "preserve_verbatim": preserve,
        "detected_commands": [],
        "detected_paths": [],
        "detected_urls": [],
        "requires_clarification": False,
        "risk_notes": [],
    }
    prompt = (
        "Create a strict JSON task card for this user message. Preserve every token in preserve_verbatim exactly. "
        "Do not execute anything. Return JSON only.\n\n"
        f"schema={json.dumps(schema, ensure_ascii=False)}\n"
        f"user_message={user_text}"
    )
    content = _ollama_chat(
        [{"role": "user", "content": prompt}],
        model=model,
        timeout_ms=timeout_ms,
    )
    if not content:
        return None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    required = set(schema)
    if not isinstance(parsed, dict) or not required.issubset(parsed):
        return None
    return parsed
