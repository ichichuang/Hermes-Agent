from __future__ import annotations

import os
from pathlib import Path

from autostart import _overall_status, remediation_command


def test_overall_status_requires_required_checks_only() -> None:
    checks = [
        {"status": "PASS", "required": True},
        {"status": "FAIL", "required": False},
    ]
    assert _overall_status(checks) == "PASS"


def test_overall_status_fails_required_failures() -> None:
    checks = [
        {"status": "PASS", "required": True},
        {"status": "FAIL", "required": True},
    ]
    assert _overall_status(checks) == "FAIL"


def test_remediation_command_uses_official_launchagent_path() -> None:
    command = remediation_command("bootstrap")
    assert command[:3] == ["/bin/launchctl", "bootstrap", f"gui/{os.getuid()}"]
    assert command[3] == str(Path.home() / "Library" / "LaunchAgents" / "ai.hermes.gateway.plist")
