# M16 Apply Core Patch

## Scope

Apply only the local Hermes core patch for `/new` reset tip fallback:

- Target: `/Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py`
- Patch: `/Users/cc/.hermes/ops/patches/M16-new-reset-tip-fallback.patch`
- Evidence: `/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M16-new-reset-tip-fallback-fix`

Do not edit `gateway/platforms/base.py`, `ops/lib/language_layer.py`, `config.yaml`, `.env`, provider/model settings, or credentials.

## Apply

```bash
patch /Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py < /Users/cc/.hermes/ops/patches/M16-new-reset-tip-fallback.patch
python3 -m py_compile /Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py
env PYTHONPATH=/Users/cc/.hermes/ops/.pytest-deps python3 -m pytest /Users/cc/.hermes/ops/tests/test_gateway_reset_tip_fallback.py
```

Load into the live gateway only through the gated wrapper:

```bash
/Users/cc/.hermes/ops/bin/hermes-ops run --phase LANG-M6 --risk service-change -- hermes gateway restart
```

## Post-Apply Checks

```bash
hermes gateway status
hermes plugins list
hermes config check
python3 -m py_compile /Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py
env PYTHONPATH=/Users/cc/.hermes/ops/.pytest-deps python3 -m pytest /Users/cc/.hermes/ops/tests
git diff --check
```

Manual Telegram validation remains operator-only: send `/new` and verify no raw `gateway.reset.tip` appears.
