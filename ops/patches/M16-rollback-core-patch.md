# M16 Rollback Core Patch

## Backup

Raw private backup:

`/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M16-new-reset-tip-fallback-fix/backups/raw-private/gateway.run.py.pre-m16`

Recorded pre-M16 SHA256:

`67277329e09842ac3463a39f5b79ce4795c96a0b638d4f6bbc71298441df855e`

## Rollback

```bash
cp /Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M16-new-reset-tip-fallback-fix/backups/raw-private/gateway.run.py.pre-m16 /Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py
python3 -m py_compile /Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py
/Users/cc/.hermes/ops/bin/hermes-ops run --phase LANG-M6 --risk service-change -- hermes gateway restart
```

## Rollback Checks

```bash
shasum -a 256 /Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py
hermes gateway status
hermes plugins list
hermes config check
env PYTHONPATH=/Users/cc/.hermes/ops/.pytest-deps python3 -m pytest /Users/cc/.hermes/ops/tests
```

Rollback decision should be `NO-GO_WITH_ROLLBACK` only if validation fails and the backup restore succeeds. If backup restore fails, decision should be `NO-GO`.
