# LANG-M25 — B-layer scope acceptance

## Decision

`ACCEPTED_LOCAL_SCOPE`

The current B-layer is accepted for local production use on hookable final-output paths only.

Accepted scope:

- `hermes-language-layer` remains enabled.
- `b_enabled: true` remains the accepted deterministic local language layer state.
- Final assistant output that reaches `transform_llm_output` is in scope.
- Tool/terminal/final reply shapes that reach `transform_llm_output` are in scope.
- Known protected-token constraints remain active: slash commands, paths, URLs, code blocks, JSON/YAML, provider/model names, command literals, hashes, IDs, and status tokens must be preserved.

Known limitation:

- Real pre-tool/interim/status commentary can still bypass `transform_llm_output`.
- The observed path is `run_agent.py:_emit_interim_assistant_message` -> `gateway/run.py:_interim_assistant_cb` -> `StreamConsumer.on_commentary(text)` or `_status_adapter.send(..., text, ...)`.
- The current plugin API has no supported interim/commentary/status-output transform hook.
- This limitation requires upstream/core support before the B-layer can safely cover it.

Out of scope:

- A-layer enablement.
- Ollama/local-model calls.
- Telegram sends or slash-command tests by Codex.
- Gateway restart/reload/stop/start/kickstart/bootstrap/bootout.
- Hermes core or site-packages edits.
- Provider/model/settings/credentials/config/env changes.
- Plugin monkeypatches of gateway callbacks, adapter sends, or plugin manager internals.

## Production interpretation

For local production operation, the B-layer is considered complete for supported hookable final-output surfaces. The remaining interim/pre-tool/status commentary gap is an accepted documented limitation, not a reason to enable A-layer or use local runtime hacks.

The next safe path is upstream submission of an additive `transform_interim_output` hook proposal. After official upstream support exists, a separate gated local phase can update `hermes-language-layer` to register the new hook and validate it.

## Evidence

- `/Users/cc/.hermes/docs/ai-plan/LANG-M23-interim-output-hook-proposal.md`
- `/Users/cc/.hermes/docs/ai-plan/LANG-M24-upstream-interim-output-hook-pr-prep.md`
- `/Users/cc/.hermes/docs/ai-plan/LANG-M24-draft-core-hook.patch`
- `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M24-upstream-interim-output-hook-pr-prep/reports/M24-source-boundary-evidence.md`

## Result

`B_LAYER_ACCEPTED_FOR_HOOKABLE_FINAL_OUTPUT`

`A_LAYER_DISABLED_AND_OUT_OF_SCOPE`
