# Maintenance Automation

## Objective

Provide a repeatable, read-only health check path that can be scheduled later without granting automatic remediation.

## Script

- `/Users/cc/.hermes/ops/bin/hermes-ops-healthcheck`

## Safe sequence

1. `hermes-ops status`
2. `hermes-ops launchd inspect --phase P0.A7`
3. `hermes-ops validate live --phase P1.B2 --dry-run`
4. `hermes-ops security baseline --phase P1.B5`
5. `hermes-ops audit verify`
6. `hermes-ops archive refresh`

## Scheduling guidance

- Use a user-level scheduler only after operator review.
- Keep cadence low, for example daily or every 6 hours.
- Do not attach any auto-remediation step.
- Send only report paths or status summaries, never secrets.
