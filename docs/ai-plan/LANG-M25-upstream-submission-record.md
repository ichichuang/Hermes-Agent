# LANG-M25 — upstream submission record

## Decision

`ACCEPTED_AND_SUBMITTED`

The current hookable-only B-layer scope was accepted for local production use, and the upstream/core interim output hook proposal was submitted as a GitHub issue.

## Submission target

- Repository: `NousResearch/hermes-agent`
- URL: `https://github.com/NousResearch/hermes-agent`
- Target evidence:
  - repo docs reference `https://github.com/NousResearch/hermes-agent`
  - current local `origin` is `https://github.com/ichichuang/Hermes-Agent.git`
  - `gh repo view NousResearch/hermes-agent` succeeded
  - `hasIssuesEnabled: true`
  - `viewerPermission: READ`
  - `git ls-remote https://github.com/NousResearch/hermes-agent.git main` succeeded
- Submission type: GitHub issue
- Issue URL: `https://github.com/NousResearch/hermes-agent/issues/35264`
- Issue title: `Proposal: add transform_interim_output hook for interim assistant commentary`
- Issue author: `ichichuang`
- Issue state at creation verification: `OPEN`

## Submitted body

The exact submitted body is recorded at:

```text
/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M25-accept-b-layer-scope-and-upstream-hook-submission/reports/M25-upstream-issue-body.md
```

Read-back verification was performed with:

```bash
gh issue view 35264 --repo NousResearch/hermes-agent --json url,title,state,author,body
```

## Patch reference

The issue links to the non-applied M24 patch sketch:

```text
https://github.com/ichichuang/Hermes-Agent/blob/593d11f156dcedc3ca8be5e15cbf54f1be86af6c/docs/ai-plan/LANG-M24-draft-core-hook.patch
```

And the full M24 proposal notes:

```text
https://github.com/ichichuang/Hermes-Agent/blob/593d11f156dcedc3ca8be5e15cbf54f1be86af6c/docs/ai-plan/LANG-M24-upstream-interim-output-hook-pr-prep.md
```

## Local runtime effect

None.

No A-layer, Ollama/local model, Telegram send, slash command, gateway lifecycle command, Hermes core/site-packages edit, provider/model/settings/credentials/config/env change, plugin monkeypatch, or raw-private file addition was performed.

## Follow-up

Wait for upstream maintainer feedback. If maintainers request an implementation PR, prepare it in a separate upstream-focused branch/worktree against `NousResearch/hermes-agent` and keep local Hermes runtime changes out of scope until an official release or approved patch path exists.
