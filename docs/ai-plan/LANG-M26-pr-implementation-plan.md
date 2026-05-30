# LANG-M26 — transform_interim_output PR implementation plan

## Scope

Prepare an upstream PR implementation plan for `transform_interim_output` only. This document is not an implementation patch and does not authorize a PR to be opened.

## Target files

Primary implementation targets:

- `hermes_cli/plugins.py`
  - Add `transform_interim_output` to `VALID_HOOKS`.
  - Keep existing `transform_llm_output`, `pre_llm_call`, and `post_llm_call` behavior unchanged.
- `gateway/run.py`
  - Add a small helper local to, or immediately adjacent to, `_interim_assistant_cb`.
  - Invoke the helper before interim text is delivered through stream commentary or status-adapter fallback.
- `tests/test_transform_interim_output_hook.py`
  - Add focused tests for registration, no-op behavior, transform behavior, fail-open behavior, duplicate suppression, and final-output compatibility.

Documentation targets after inspecting upstream docs layout:

- existing plugin hook docs or README section that lists supported hooks
- release note / changelog entry only if upstream project convention requires it

## Hook insertion points

Insert the hook in `gateway/run.py:_interim_assistant_cb`:

1. If `_stream_consumer is not None` and `already_streamed` is false, transform `text` immediately before `_stream_consumer.on_commentary(text)`.
2. If `_stream_consumer is not None` and `already_streamed` is true, keep current segment-break behavior and do not invoke the hook.
3. If the status-adapter fallback path is used, transform `text` immediately before `_status_adapter.send(..., text, ...)`.
4. Do not insert the hook in `run_agent.py:_emit_interim_assistant_message`; gateway/session/platform context is needed at the delivery boundary.
5. Do not insert the hook inside `StreamConsumer.on_commentary`; gateway/session/platform context would be less explicit there.

## Payload schema

Pass only display-safe context:

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

Rules:

- `text` is the only mutable value.
- `surface` describes the delivery surface only.
- `session_id`, `model`, `platform`, and `already_streamed` are read-only context.
- Do not pass chat IDs, user IDs, auth metadata, cookies, tokens, `.env` values, provider credentials, or adapter-private metadata.

## No-op contract

The hook must be behavior-preserving by default:

- no registered hook leaves text unchanged
- disabled plugin leaves text unchanged
- `None` return leaves text unchanged
- empty string return leaves text unchanged
- non-string return is ignored
- first non-empty string return replaces the outgoing display text once
- hook must not drop, resend, duplicate, delay, or schedule messages

## Failure behavior

The hook must fail open:

- catch unexpected hook invocation failures
- log a warning without exposing sensitive payload values
- deliver the original text
- do not interrupt the active turn
- do not alter gateway routing, adapter metadata, or final response generation

If upstream `invoke_hook` already catches per-plugin exceptions, keep a narrow wrapper around the delivery-boundary helper for unexpected integration failures.

## Ordering

Expected order within one turn:

```text
pre_llm_call
  -> main LLM/tool loop
     -> zero or more transform_interim_output calls before interim delivery
  -> transform_llm_output for final_response
  -> post_llm_call
```

`transform_interim_output` must not mutate conversation history and must not change the text later passed to final-output hooks unless the core already uses that display text for another purpose. It is only an outgoing interim display transform.

## Tests

Add targeted upstream tests for:

1. `VALID_HOOKS` includes `transform_interim_output`.
2. Stream commentary is unchanged when no hook is registered.
3. Status-adapter fallback is unchanged when no hook is registered.
4. Hook returning `None` leaves text unchanged.
5. Hook returning `""` leaves text unchanged.
6. First non-empty string return replaces text exactly once.
7. Non-string returns are ignored.
8. Hook exception logs and delivers original text.
9. `already_streamed=True` creates only a segment break and does not duplicate transformed text.
10. Existing `transform_llm_output` final-response behavior remains unchanged.
11. Disabled or absent plugins leave interim text unchanged.
12. Hook payload contains only the safe schema fields.
13. Protected-token fixture preserves slash commands, fenced code blocks, paths, URLs, JSON/YAML, provider/model names, command names, output literals, IDs, hashes, timestamps, and status tokens.

If upstream has existing plugin/gateway fixture patterns, adapt these tests to that style rather than introducing a parallel test harness.

## Docs

Document:

- hook name and purpose
- invocation timing
- payload schema
- no-op contract
- fail-open behavior
- protected-token expectations
- no provider/model/config/credential/routing side effects
- no message-send, slash-command, tool, provider call, network call, A-layer, or local-model work inside the hook

## Rollback

Upstream rollback:

- remove `transform_interim_output` from `VALID_HOOKS`
- remove the gateway helper and invocation points
- remove or update the new tests/docs
- keep `pre_llm_call`, `transform_llm_output`, and `post_llm_call` unchanged

Local runtime rollback for this M26 phase:

- no action; M26 does not modify live runtime

Future local rollout rollback after official support:

- disable only the B-layer registration for `transform_interim_output`
- keep the existing final-output `transform_llm_output` registration enabled if still accepted
- use `hermes-ops` gate for any future gateway lifecycle action

## Compatibility

Compatibility expectations:

- additive hook name only; existing plugins remain valid
- no behavior change when no plugin registers the new hook
- no behavior change for final response transformation
- no provider/model/settings/credentials/config/env migration
- no new runtime dependency
- no Telegram-specific escaping inside core hook
- no A-layer or prompt-injection dependency
- no local-model/Ollama dependency
- no site-packages-only local production dependency

## PR preparation checklist

- Confirm upstream default branch and current test layout in a separate safe upstream workspace after operator approval.
- Implement only hook registration, gateway delivery-boundary invocation, tests, and docs.
- Do not include local `hermes-language-layer` changes in the upstream PR.
- Run upstream targeted tests first, then broader test suite if available.
- Run formatting/lint commands only if defined by upstream scripts.
- Run secret scan on staged diff.
- Open PR only after explicit operator approval.
