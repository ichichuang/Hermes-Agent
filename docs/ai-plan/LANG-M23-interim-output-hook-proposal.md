# LANG-M23 — B-layer scope and interim output hook decision

## Decision

`DESIGN_CORE_HOOK`

M23 accepts the current B-layer as a stable hookable-only localization layer, but does not accept the remaining interim/pre-tool/status commentary English surface as final scope. The recommended next step is a narrow upstream/core hook proposal. No Hermes core, site-packages, provider, model, credential, config, `.env`, A-layer, gateway lifecycle, Telegram, slash-command, or local-model/Ollama change is part of M23.

## Current B-layer scope

The current B-layer is enabled through `hermes-language-layer` and `b_enabled: true`. It is intentionally deterministic and non-model-backed while `a_enabled: false` and `local_model_enabled: false`.

Covered scope:

- Final assistant output that reaches `transform_llm_output`.
- Tool/terminal final-reply shapes proven hookable by M20.
- M22 hookable status phrase rendering when the phrase is presented through `transform_llm_output`.
- No-execute fenced-code tail stripping for tested English and Chinese inferred-output shapes.
- Protected-token preservation for fenced code, slash commands, paths, URLs, JSON/YAML keys, provider/model names, and command-like literals.

Out of scope under current hooks:

- Real interim assistant commentary emitted before or during tool work.
- Gateway status-adapter sends used as a fallback when stream commentary is unavailable.
- Any direct core/gateway output path that does not call `transform_llm_output`.

## Evidence summary

- `hermes_cli/plugins.py` supports `transform_llm_output`, `transform_tool_result`, `transform_terminal_output`, and related lifecycle hooks, but has no supported interim/commentary/status-output transform hook.
- `run_agent.py:_emit_interim_assistant_message` surfaces mid-turn commentary through `interim_assistant_callback`.
- `gateway/run.py:_interim_assistant_cb` routes that text either to `StreamConsumer.on_commentary(text)` or to `_status_adapter.send(...)`.
- `gateway/stream_consumer.py:on_commentary` queues commentary and `_send_commentary` sends it through `adapter.send(...)`.
- `run_agent.py` invokes `transform_llm_output` only after the tool-calling loop completes, for `final_response`.
- M22/M22B evidence shows the hookable B-layer path is tested and committed, while true pre-tool/interim commentary bypasses the hook.

## Accepted limitations

The accepted operational limitation is narrow:

- Current B-layer can remain enabled and trusted for hookable final-output surfaces.
- The known interim/pre-tool/status commentary surface may still appear in English until an upstream hook exists and the B-layer plugin registers it.
- This limitation is not a reason to enable A-layer, call a local model, monkeypatch runtime objects, edit site-packages, or alter provider/model/config/env settings.

This is an accepted interim limitation, not an accepted final UX boundary.

## Options

### Option A: accept hookable-only scope

Benefits:

- Zero runtime or upstream change.
- Lowest rollback and maintenance cost.
- Preserves the current stable B-layer behavior.

Costs:

- Leaves a user-visible English pre-tool/status surface unresolved.
- Turns a proven architecture gap into permanent scope.
- Future polish tasks would repeatedly rediscover the same boundary.

Use this only if the product accepts mixed-language interim commentary as a durable limitation.

### Option B: design upstream/core interim-output hook

Benefits:

- Keeps M23 non-invasive while giving the remaining gap an explicit upstream path.
- Matches the existing plugin model and first-string-wins transform contract.
- Avoids local site-packages drift, A-layer prompt pressure, and runtime monkeypatching.
- Allows a later B-layer plugin update to cover commentary without changing provider/model/config/env.

Costs:

- No immediate live runtime fix.
- Requires upstream review, tests, and a future gated upgrade before claiming the surface is fixed.

This is the recommended option.

### Option C: unsafe monkeypatch or local core runtime hack

Rejected.

Reasons:

- It would mutate unsupported runtime/core behavior outside the current safe edit scope.
- It would be fragile across Hermes upgrades and hard to audit.
- It risks bypassing the plugin contract, validation gates, and rollback discipline.
- It conflicts with the current M23 hard constraints.

## Minimal upstream hook proposal

### Hook name

`transform_interim_output`

### Invocation point

The narrowest useful placement is inside the gateway interim callback before text is delivered to either commentary streaming or the status adapter:

- `gateway/run.py:_interim_assistant_cb`
- before `_stream_consumer.on_commentary(text)`
- before `_status_adapter.send(..., text, ...)`
- not called when `already_streamed` suppresses duplicate text delivery

This keeps the hook near the delivery boundary and avoids changing final-response handling.

### Payload

```python
invoke_hook(
    "transform_interim_output",
    text=text,
    surface="commentary" | "status",
    session_id=agent.session_id or "",
    model=agent.model,
    platform=platform_name,
    already_streamed=already_streamed,
)
```

Payload constraints:

- Do not include secret values.
- Do not include raw auth metadata, chat IDs, tokens, cookies, or `.env` values.
- Keep `text` as the only mutable output field.

### No-op return contract

- `None` means unchanged.
- Empty string means unchanged.
- First non-empty `str` return value wins.
- Exceptions are logged and leave the original text unchanged.
- The hook must not block, drop, resend, or alter metadata.

This mirrors `transform_llm_output` and keeps existing plugins unaffected.

### Protected-token handling

The hook contract should state that transform plugins must preserve:

- fenced code blocks and language tags
- slash commands
- filesystem paths
- URLs
- JSON/YAML keys and values
- provider/model names
- command names and command output literals
- IDs or opaque tokens present in status text

Core should not attempt localization itself. Core should only expose the hook and keep no-op behavior unchanged.

### Safety tests

Required upstream tests:

- `VALID_HOOKS` includes `transform_interim_output`.
- no registered hook leaves commentary/status text unchanged.
- `None` and empty-string hook returns leave text unchanged.
- first non-empty string return replaces delivered interim text exactly once.
- hook exception leaves original text unchanged and does not break delivery.
- `already_streamed=True` path does not emit duplicate transformed commentary.
- stream commentary path is covered.
- status-adapter fallback path is covered.
- existing `transform_llm_output` final-response behavior remains unchanged.

Required B-layer follow-up tests after upstream support:

- `Let me check what's happening on my end.` renders Chinese through `transform_interim_output`.
- fenced code, slash commands, paths, URLs, JSON/YAML keys, provider/model names, and command literals are preserved.
- no A-layer or local-model path is invoked.

### Rollback

Rollback for the upstream PR is additive and simple:

- remove `transform_interim_output` from `VALID_HOOKS`
- remove the invocation helper from gateway interim delivery
- leave existing `transform_llm_output` behavior unchanged
- disable any B-layer registration for `transform_interim_output`

For local operations before upstream support, rollback is to do nothing: keep current B-layer enabled and keep the interim commentary limitation documented.

### Upstream PR path

1. Open an upstream issue with M22/M23 evidence and the narrow hook proposal.
2. Submit a small PR adding only the hook registration, invocation, docs, and tests.
3. Do not include Hermes-language-layer plugin changes in the core hook PR.
4. After an official Hermes version includes the hook, open a separate local phase to update the B-layer plugin to register `transform_interim_output`.
5. Validate with targeted unit tests, plugin canaries, read-only gateway checks, and an operator-provided Telegram observation. Any gateway reload must use `hermes-ops` gate.

## M23 conclusion

`DESIGN_CORE_HOOK`

The current B-layer scope is accepted for hookable final-output surfaces only. The remaining interim/pre-tool/status commentary gap should be handled by an upstream additive hook, not by A-layer enablement, local-model calls, site-packages edits, or monkeypatching.
