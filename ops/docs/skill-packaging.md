# Codex/Hermes Skill Packaging

## Scope

Package the repeatable Hermes Ops workflow as a repo-local skill so future Codex runs resolve it before broader user or built-in skills.

## Deliverables

- `/Users/cc/.hermes/ops/skills/hermes-ops/SKILL.md`
- repo-local resolution evidence in the active archive

## Resolution order

1. repo-local: `/Users/cc/.hermes/.ai/skills/*` or `/Users/cc/.hermes/skills/*`
2. user: `/Users/cc/.codex/skills/*`
3. built-in/plugin cache skills

## Notes

- This packaging does not bypass approvals or hard-stop rules.
- The skill intentionally points back to `hermes-ops` commands instead of embedding side-effectful shell directly.
