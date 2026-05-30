# M17 Rollback Core Patch

Rollback source:

`/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M17-new-reset-header-metadata-polish/backups/raw-private/gateway.run.py.pre-m17`

Rollback target:

`/Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py`

Recorded pre-M17 SHA256:

`e35ed8a7a5321b80edce3ec5f4d261b31341af160e0fd1f6781875bd40c102c4`

Rollback:

```bash
cp /Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M17-new-reset-header-metadata-polish/backups/raw-private/gateway.run.py.pre-m17 /Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py
chmod 0644 /Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py
python3 -m py_compile /Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py
/Users/cc/.hermes/ops/bin/hermes-ops run --phase LANG-M6 --risk service-change -- hermes gateway restart
```

Post-rollback verification:

```bash
shasum -a 256 /Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py
hermes gateway status
hermes config check
hermes plugins list
```

Do not use raw `hermes gateway restart`; keep reloads behind the existing `LANG-M6` gate.
