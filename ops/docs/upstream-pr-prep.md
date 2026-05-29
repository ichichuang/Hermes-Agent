# Upstream PR Prep Notes

## Local findings worth upstream attention

1. `launchctl print gui/<uid>/ai.hermes.gateway` and `launchctl print user/<uid>/ai.hermes.gateway` both returned exit code `113` in local preflight despite plist presence.
2. Current gateway status is not conclusively healthy from local read-only signals.
3. Launchd domain ambiguity and modern `launchctl` behavior match the risks captured in the plan research brief.

## Minimal upstream patch ideas

### 1. Improve `hermes gateway status`

- Detect and surface `gui/<uid>` vs `user/<uid>` domain resolution attempts.
- Show exact plist path, detected `HERMES_HOME`, and last launchctl exit code.

### 2. Add read-only doctor output

- A built-in `hermes gateway doctor --read-only` could emit:
  - plist summary
  - current domain probes
  - process count
  - redacted log hints

### 3. Clarify launchd docs

- Document domain fallback behavior on modern macOS.
- Document exit code `113` handling and next safe inspection steps.

## Local policy

- These are notes only.
- No Hermes core code was modified as part of this ops-layer implementation.
