from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/cc/.hermes")
CLI = ROOT / "ops" / "bin" / "hermes-ops"


def run(*args: str) -> tuple[int, str]:
    result = subprocess.run([str(CLI), *args], capture_output=True, text=True, check=False)
    return result.returncode, result.stdout or result.stderr


def assert_ok(code: int, output: str, label: str) -> None:
    if code != 0:
        raise SystemExit(f"{label} failed:\n{output}")


def main() -> int:
    code, output = run("status")
    assert_ok(code, output, "status")
    status_payload = json.loads(output)
    if not status_payload.get("active_archive"):
        raise SystemExit("active archive missing")

    checks = [
        ("phase start dry-run", ["phase", "start", "P0.A3", "--dry-run"]),
        ("hash snapshot", ["hash", "snapshot", "--phase", "P0.A5"]),
        ("launchd inspect", ["launchd", "inspect", "--phase", "P0.A7"]),
        ("validate live dry-run", ["validate", "live", "--phase", "P1.B2", "--dry-run"]),
        ("audit verify", ["audit", "verify"]),
    ]
    for label, args in checks:
        code, output = run(*args)
        assert_ok(code, output, label)
    print("smoke PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
