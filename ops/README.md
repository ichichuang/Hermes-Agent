# Hermes Ops

Non-intrusive operations layer for `/Users/cc/.hermes`.

Primary entrypoint:

```bash
/Users/cc/.hermes/ops/bin/hermes-ops --help
```

Core guarantees:

- evidence first
- secret-safe summaries only
- hard-stop guard for launchd and gateway mutations
- append-only ledgers and audit chain
- read-only launchd preflight
- live validation matrix with explicit `PASS` / `FAIL` / `BLOCKED` / `NOT_APPLICABLE`
