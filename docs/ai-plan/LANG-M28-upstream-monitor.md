# LANG-M28 — readonly upstream monitor and local stability check

## Decision

`NO_NEW_FEEDBACK_STABLE`

Upstream issue `NousResearch/hermes-agent#35264` remains open. No new maintainer comment, assignee, milestone, linked PR, or issue update was found after the M27 snapshot. The previously recorded metadata-only triage labels remain:

- `type/feature`
- `comp/gateway`
- `comp/plugins`
- `P3`

Local Hermes B-layer stability checks passed without runtime mutation. The B-layer remains enabled, A-layer remains disabled, and local model/Ollama remains disabled.

## Issue snapshot

- Repository: `NousResearch/hermes-agent`
- Issue: `https://github.com/NousResearch/hermes-agent/issues/35264`
- Title: `Proposal: add transform_interim_output hook for interim assistant commentary`
- State: `OPEN`
- Created: `2026-05-30T09:14:22Z`
- Updated: `2026-05-30T09:38:02Z`
- Comments: `0`
- Assignees: none
- Milestone: none
- Linked PR: none found in GraphQL timeline query or PR search

## Feedback summary

No new feedback was recorded in M28. The M27 triage labels are still the latest upstream activity. There is still no maintainer comment, implementation request, rejection, milestone assignment, assignee, or linked PR.

The M26 implementation plan and M27 label-aligned guidance remain current:

1. Keep the first upstream change additive and behavior-preserving by default.
2. Keep the scope to `VALID_HOOKS`, the gateway interim delivery boundary, focused tests, and docs.
3. Do not open a PR unless the operator explicitly approves PR work in a separate phase.
4. Do not modify local Hermes runtime, A-layer state, provider/model/settings/credentials/config/env, or gateway lifecycle while monitoring.

## Local stability summary

- Branch: `main`
- Baseline commit before M28 docs: `c96de487da062a6c9e7773073ae73896f2afd93c`
- Initial repo state: clean
- Gateway status: loaded, PID `97699`
- Gateway process: PID `97699`, parent PID `1`, command `/Users/cc/.local/share/hermes-agent-v0.14.0/bin/python -m hermes_cli.main gateway run --replace`
- Plugin state: `hermes-language-layer` enabled, version `0.2.0`
- Config check: PASS, config version `23`
- B-layer: enabled; `b_enabled: true`
- A-layer: disabled; `a_enabled: false`
- Local model/Ollama: disabled; `local_model_enabled: false`
- Diff check: PASS

## Not executed

- No upstream PR opened.
- No branch created.
- No upstream clone created.
- No Hermes core or site-packages edit.
- No A-layer enablement.
- No Ollama or local model call.
- No Telegram send.
- No slash command.
- No gateway restart, reload, stop, start, kickstart, bootstrap, or bootout.
- No launchctl enable/bootstrap/bootout/kickstart/load/unload.
- No provider, model, settings, credentials, config, env, auth, session, log, state, DB, cache, PID, or lock file change.

## Evidence

- `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M28-readonly-upstream-monitor-and-local-stability-check/phase-report.md`
- `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M28-readonly-upstream-monitor-and-local-stability-check/reports/M28-upstream-monitor.md`
- `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M28-readonly-upstream-monitor-and-local-stability-check/reports/M28-local-stability.md`
- `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M28-readonly-upstream-monitor-and-local-stability-check/reports/M28-validation-summary.md`
- `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M28-readonly-upstream-monitor-and-local-stability-check/reports/M28-final-decision.md`

## Next phase

Continue lightweight read-only monitoring for issue `#35264`. Only start upstream PR workspace work if the operator explicitly approves PR creation or branch/worktree creation in a separate goal.
