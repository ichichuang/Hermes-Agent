# LANG-M24 — upstream interim output hook PR prep

## Decision

`PR_PREPARED`

This package prepares an upstream/core PR proposal for a safe interim/pre-tool/status output transform hook. It does not apply any Hermes core, site-packages, live plugin, provider, model, credentials, config, `.env`, A-layer, gateway lifecycle, Telegram, slash-command, or local-model/Ollama change.

## Proposed hook

Hook name:

```text
transform_interim_output
```

`transform_interim_output` is preferred over `transform_status_output` for the first upstream PR because the proven blocker is assistant-authored interim commentary emitted during a turn. The same hook can cover the status-adapter fallback for that interim text through a `surface` field. Generic gateway/tool progress status messages should remain out of scope for the first PR unless upstream maintainers request a broader second hook.

## Source path evidence

Local source was inspected read-only under:

```text
/Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages
```

Evidence:

- `hermes_cli/plugins.py:128` defines `VALID_HOOKS`; it includes `transform_llm_output`, `pre_llm_call`, and `post_llm_call`, but no interim/commentary/status-output transform hook.
- `hermes_cli/plugins.py:669` registers hooks; unknown hook names only warn, so a plugin can register forward-looking names but core does not invoke them.
- `hermes_cli/plugins.py:1264` invokes hook callbacks and catches per-callback exceptions.
- `run_agent.py:12433` fires `pre_llm_call` before the main tool-calling loop.
- `run_agent.py:7961` extracts a visible interim assistant message and calls `interim_assistant_callback`.
- `run_agent.py:15016` calls `_emit_interim_assistant_message(interim_msg)` for non-duplicate interim messages.
- `gateway/run.py:15298` defines `_interim_assistant_cb`.
- `gateway/run.py:15305` sends interim text to `StreamConsumer.on_commentary(text)` when a stream consumer exists.
- `gateway/run.py:15310` sends the same interim text through `_status_adapter.send(...)` as the fallback path.
- `gateway/stream_consumer.py:204` queues commentary text for delivery.
- `run_agent.py:15874` invokes `transform_llm_output` only after the tool-calling loop completes, for final output.
- `run_agent.py:15895` fires `post_llm_call` after final-output transformation.

Conclusion: real pre-tool/interim commentary bypasses `transform_llm_output`. The smallest supported design is an additive core hook at the delivery boundary in `gateway/run.py:_interim_assistant_cb`.

## Invocation point

Call `transform_interim_output` immediately before interim text is delivered:

- before `_stream_consumer.on_commentary(text)` for commentary streaming
- before `_status_adapter.send(..., text, ...)` for status-adapter fallback
- not on `already_streamed=True` segment-break-only delivery, because no new text is emitted
- not in `StreamConsumer.on_commentary`, so platform/session context remains available at the gateway boundary
- not in `run_agent.py:_emit_interim_assistant_message`, so gateway-specific surface and adapter routing remain visible

## Payload schema

Proposed kwargs:

```python
{
    "text": str,
    "surface": "commentary" | "status",
    "session_id": str,
    "model": str,
    "platform": str,
    "already_streamed": bool,
}
```

Schema rules:

- `text` is the only mutable field.
- `surface` describes delivery shape only; it is not a permission to alter metadata or routing.
- `session_id`, `model`, `platform`, and `already_streamed` are read-only context.
- Do not pass chat IDs, user IDs, auth metadata, tokens, cookies, `.env` values, provider credentials, or adapter-private metadata.

## Return contract

- `None` means unchanged.
- Empty string means unchanged.
- The first non-empty `str` return value replaces `text`.
- Non-string returns are ignored.
- Exceptions fail open: log the hook failure and deliver the original text.
- A hook must not drop, resend, duplicate, block, or schedule messages.

This mirrors the existing `transform_llm_output` first-string-wins behavior while making no-op behavior safe for existing plugins.

## Mutation boundaries

Allowed:

- Replace the displayed interim `text` once before delivery.
- Return original text or `None` when preservation cannot be guaranteed.

Forbidden:

- Mutating `session_id`, `model`, `platform`, adapter metadata, chat routing, or send timing.
- Sending Telegram or any other platform message from the hook.
- Running slash commands, tools, local models, provider calls, or network calls inside the hook.
- Monkeypatching gateway/runtime objects.
- Editing site-packages or live plugin code as a local workaround.

## Ordering

The hook ordering should be:

```text
pre_llm_call
  -> main LLM/tool loop
     -> zero or more transform_interim_output calls before interim delivery
  -> transform_llm_output for final_response
  -> post_llm_call
```

`transform_interim_output` must not replace `pre_llm_call`, must not run after `transform_llm_output`, and must not mutate persisted conversation history. It only transforms outgoing interim display text.

## Protected-token requirements

Transform plugins using this hook must preserve:

- fenced code blocks, inline code, and language tags
- slash commands such as `/new`, `/start`, and `/sethome`
- filesystem paths
- URLs and Markdown link destinations
- JSON/YAML keys and values
- provider and model names
- command names and command output literals
- opaque IDs, hashes, timestamps, and status tokens
- Markdown table fences and indentation

If a plugin cannot prove preservation, it should return `None`.

## Telegram Markdown constraints

The hook receives and returns platform-display text. For Telegram:

- Preserve balanced backticks and triple-backtick fences.
- Do not alter slash-command tokens or command prefixes.
- Do not rewrite URLs, Markdown link destinations, or file paths.
- Do not introduce unmatched MarkdownV2-sensitive punctuation around protected tokens.
- Prefer returning unchanged text for code-heavy, path-heavy, JSON/YAML-heavy, or command-heavy messages.
- Core must not perform Telegram-specific escaping in this hook; adapter formatting remains the adapter's responsibility.

## Draft tests

Upstream/core tests:

1. `VALID_HOOKS` includes `transform_interim_output`.
2. With no registered hook, stream commentary text is unchanged.
3. With no registered hook, status-adapter fallback text is unchanged.
4. A hook returning `None` leaves text unchanged.
5. A hook returning `""` leaves text unchanged.
6. The first non-empty string return replaces text exactly once.
7. A hook exception logs and delivers original text.
8. `already_streamed=True` produces only a segment break and does not duplicate transformed text.
9. `transform_llm_output` final-response behavior remains unchanged.
10. Disabled or absent plugins leave interim text unchanged.

B-layer follow-up tests after upstream support:

1. `Let me check what's happening on my end.` renders as Chinese through `transform_interim_output`.
2. Slash commands such as `/new`, `/start`, and `/sethome` are preserved.
3. Fenced code blocks and inline code are preserved.
4. Paths and URLs are preserved.
5. JSON/YAML keys and values are preserved.
6. Provider/model names are preserved.
7. Hook exception behavior is fail-open.
8. With `hermes-language-layer` disabled, no interim transformation occurs.
9. No A-layer or local-model/Ollama path is invoked.

## Minimal patch sketch

See:

```text
docs/ai-plan/LANG-M24-draft-core-hook.patch
```

The patch is a non-applied sketch only. It is intentionally narrow:

- Add `transform_interim_output` to `VALID_HOOKS`.
- Add a local gateway helper near `_interim_assistant_cb`.
- Invoke the helper only before interim commentary/status fallback delivery.
- Preserve current final output hooks unchanged.
- Add tests for no-op, transform, fail-open, duplicate-suppression, protected-token, and plugin-disabled behavior.

## Migration

1. Open an upstream issue or PR with this evidence package.
2. Keep the core PR limited to hook registration, gateway invocation, docs, and tests.
3. Do not include Hermes-language-layer plugin changes in the upstream/core PR.
4. After an official Hermes release includes the hook, open a separate local phase to update `hermes-language-layer` to register `transform_interim_output`.
5. Validate locally with targeted tests, plugin canaries, read-only `hermes gateway status`, `hermes plugins list`, `hermes config check`, `git diff --check`, staged secret scan, and operator-provided Telegram observation.
6. Any future gateway reload must use the existing `hermes-ops` gate; no raw lifecycle command.

## Rollback

Upstream rollback:

- Remove `transform_interim_output` from `VALID_HOOKS`.
- Remove the gateway helper and invocation.
- Keep `transform_llm_output`, `pre_llm_call`, and `post_llm_call` unchanged.
- Remove or adjust new tests.

Local rollback before upstream support:

- Do nothing to runtime.
- Keep current B-layer enabled for hookable final-output surfaces.
- Keep the interim/pre-tool/status commentary limitation documented.

Local rollback after upstream support:

- Disable the B-layer plugin registration for `transform_interim_output`.
- Keep `transform_llm_output` registration enabled if final-output behavior remains accepted.
- Re-run read-only validation and operator observation.

## Upstream PR checklist

- [ ] Include M22/M23/M24 evidence summary.
- [ ] Include exact source paths and line references.
- [ ] State that monkeypatch/site-packages runtime edits are rejected.
- [ ] State that A-layer, local model/Ollama, provider/model/config/env changes are out of scope.
- [ ] Add `transform_interim_output` to the hook list.
- [ ] Add gateway delivery-boundary invocation.
- [ ] Cover stream commentary and status fallback.
- [ ] Cover no-op and disabled-plugin behavior.
- [ ] Cover exception fail-open behavior.
- [ ] Cover protected tokens: slash command, code fence, path, URL, JSON, YAML.
- [ ] Confirm final `transform_llm_output` behavior is unchanged.
- [ ] Do not open the GitHub PR without explicit operator approval.

## Explicit rejection

Rejected paths:

- plugin monkeypatch of `gateway/run.py`, `StreamConsumer`, adapter send methods, or plugin manager internals
- local site-packages edits as production dependency
- A-layer prompt injection for this surface
- local-model/Ollama rewrite for this surface
- Telegram self-test or slash-command execution by Codex
- gateway restart/reload/stop/start/kickstart/bootstrap/bootout for M24

The bug is not mysterious anymore; it is just standing in the one hallway without a hook.
