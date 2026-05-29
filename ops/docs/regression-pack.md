# Regression Pack

## Purpose

Give Hermes upgrades a small repeatable verification pack that still works when optional tooling is incomplete.

## Layers

1. `python3 /Users/cc/.hermes/ops/tests/run_smoke.py`
2. `python3 -m pytest /Users/cc/.hermes/ops/tests` when local pytest is healthy
3. `hermes-ops launchd inspect --phase P0.A7`
4. `hermes-ops validate live --phase P1.B2 --dry-run`
5. `hermes-ops audit verify`

## Expected use

- Run after Hermes upgrades.
- Run after ops-layer changes.
- Keep results in the active archive and update `07_STATUS.md`.
