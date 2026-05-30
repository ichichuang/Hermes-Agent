# LANG-M26 — upstream feedback tracking and PR prep

## Decision

`PR_PLAN_READY`

No upstream maintainer feedback has been recorded on the submitted issue as of `2026-05-30 17:34:56 CST`. This phase therefore prepares a safe implementation plan only. It does not implement a patch, modify live Hermes runtime, open a PR, enable A-layer, call Ollama/local model, send Telegram, run slash commands, restart/reload the gateway, or change provider/model/settings/credentials/config/env.

## Upstream issue snapshot

- Repository: `NousResearch/hermes-agent`
- Issue: `https://github.com/NousResearch/hermes-agent/issues/35264`
- Title: `Proposal: add transform_interim_output hook for interim assistant commentary`
- State: `OPEN`
- Author: `ichichuang`
- Created: `2026-05-30T09:14:22Z`
- Updated: `2026-05-30T09:14:22Z`
- Comments: `0`
- Feedback exists: `NO`
- Feedback summary: no comments, labels, assignees, milestone, linked branch, linked PR, or maintainer response visible in the public issue page / `gh issue view` output.

## Inputs reviewed

- `/Users/cc/.hermes/docs/ai-plan/LANG-M24-upstream-interim-output-hook-pr-prep.md`
- `/Users/cc/.hermes/docs/ai-plan/LANG-M24-draft-core-hook.patch`
- `/Users/cc/.hermes/docs/ai-plan/LANG-M25-b-layer-scope-acceptance.md`
- `/Users/cc/.hermes/docs/ai-plan/LANG-M25-upstream-submission-record.md`
- `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M25-accept-b-layer-scope-and-upstream-hook-submission/reports/M25-upstream-issue-body.md`
- Public GitHub issue page and `gh issue view 35264 --repo NousResearch/hermes-agent --json url,title,state,author,createdAt,updatedAt,closedAt,comments`

## Clone inspection

No separate disposable upstream clone was found. The only matching local directory discovered was the live install path:

```text
/Users/cc/.local/share/hermes-agent-v0.14.0
```

That path is not a disposable upstream clone and was not used as a PR implementation workspace in M26.

## PR implementation plan

Detailed implementation plan:

```text
docs/ai-plan/LANG-M26-pr-implementation-plan.md
```

The plan keeps the upstream PR additive and narrow:

- add `transform_interim_output` to plugin hook registration
- invoke it only at the interim text delivery boundary
- preserve no-op behavior when no hook is registered
- fail open on hook errors
- preserve existing `pre_llm_call`, `transform_llm_output`, and `post_llm_call` ordering
- avoid local runtime, provider, model, config, credential, A-layer, Ollama/local-model, Telegram, slash-command, or gateway lifecycle changes

## Runtime state

Expected current state remains unchanged from M25:

- B-layer: enabled
- A-layer: disabled
- `local_model_enabled`: false
- Gateway: stable; no M26 lifecycle command executed

## Not executed

- No upstream PR opened.
- No clone created.
- No live Hermes core or site-packages edit.
- No A-layer enablement.
- No Ollama/local model call.
- No Telegram send.
- No slash command.
- No gateway restart/reload/stop/start/kickstart/bootstrap/bootout.
- No launchctl enable/bootstrap/bootout/kickstart/load/unload.
- No provider/model/settings/credentials/config/env/auth/session/log/state/DB/cache/PID/lock change.
- No HermesArchive raw-private file added.

## Evidence

- `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M26-upstream-feedback-or-pr-prep/phase-report.md`
- `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M26-upstream-feedback-or-pr-prep/reports/M26-upstream-feedback.md`
- `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M26-upstream-feedback-or-pr-prep/reports/M26-pr-plan-summary.md`
- `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M26-upstream-feedback-or-pr-prep/reports/M26-validation-summary.md`
- `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M26-upstream-feedback-or-pr-prep/reports/M26-final-decision.md`

## Next phase

Recommended next phase: `LANG-M27-upstream-feedback-monitor-or-approved-pr-branch`.

If maintainers respond, record feedback first. If the operator explicitly approves an implementation PR, prepare it in a separate upstream-focused branch/worktree and keep local Hermes runtime unchanged.
