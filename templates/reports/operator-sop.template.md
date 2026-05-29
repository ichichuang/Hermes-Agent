# Operator SOP — Hermes Ops Upgrade

## Current decision

`GO | NO-GO | GO_WITH_BLOCKERS`

## Safe commands

```bash
/Users/cc/.hermes/ops/bin/hermes-ops status
/Users/cc/.hermes/ops/bin/hermes-ops launchd inspect
/Users/cc/.hermes/ops/bin/hermes-ops hash snapshot
/Users/cc/.hermes/ops/bin/hermes-ops audit verify
```

## Forbidden without gate

```bash
launchctl enable gui/$(id -u)/ai.hermes.gateway
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.gateway.plist
hermes gateway start
hermes gateway stop
hermes gateway restart
hermes gateway install
```

## Logs

```bash
tail -f /Users/cc/.hermes/logs/gateway.log
```

Redact secrets before copying logs into reports.

## Rollback

- Do not delete evidence packs.
- Do not restore old Hermes code.
- Use recorded before-state and exact commands only.

## Next action

- TBD
