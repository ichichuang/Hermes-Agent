# M17 Apply Core Patch

Scope: minimal local site-packages patch for `/new` reset header, metadata labels/icon palette, and reset tip body only.

Core file:

`/Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py`

Patch:

`/Users/cc/.hermes/ops/patches/M17-new-reset-header-metadata.patch`

Evidence:

`/Users/cc/HermesArchive/hermes-langlayer-goal-20260529_005838/phases/LANG-M17-new-reset-header-metadata-polish`

Pre-M17 SHA256:

`e35ed8a7a5321b80edce3ec5f4d261b31341af160e0fd1f6781875bd40c102c4`

Post-patch SHA256:

`2d2c8a42296dc147b516361ca85bf7f138c308d3b607c184ded39fca229aca4d`

Expected `/new` reset palette:

- `🪄` reset/new
- `🫪` model / `模型`
- `❤️` provider / `服务商`
- `💭` context / `上下文`
- `💫` tip

Apply:

```bash
patch /Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py < /Users/cc/.hermes/ops/patches/M17-new-reset-header-metadata.patch
python3 -m py_compile /Users/cc/.local/share/hermes-agent-v0.14.0/lib/python3.11/site-packages/gateway/run.py
env PYTHONPATH=/Users/cc/.hermes/ops/.pytest-deps python3 -m pytest /Users/cc/.hermes/ops/tests
hermes config check
hermes plugins list
git diff --check
/Users/cc/.hermes/ops/bin/hermes-ops run --phase LANG-M6 --risk service-change -- hermes gateway restart
```

Constraints:

- Do not edit `gateway/platforms/base.py`.
- Do not edit `/Users/cc/.hermes/config.yaml` or `/Users/cc/.hermes/.env`.
- Do not enable A-layer or local model/Ollama.
- Do not send Telegram messages or run slash commands from automation.
- Reload only through `hermes-ops` gated wrapper.
