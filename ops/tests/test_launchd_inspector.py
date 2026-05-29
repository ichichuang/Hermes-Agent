from __future__ import annotations

from launchd_inspector import detect_gateway_processes, parse_launchctl_output, summarize_plist


def test_summarize_plist_extracts_expected_fields() -> None:
    summary = summarize_plist(
        {
            "Label": "ai.hermes.gateway",
            "ProgramArguments": ["hermes", "gateway", "start"],
            "WorkingDirectory": "/Users/cc/.hermes",
            "EnvironmentVariables": {"PATH": "/bin", "VIRTUAL_ENV": "/venv", "HERMES_HOME": "/Users/cc/.hermes"},
        }
    )
    assert summary["label"] == "ai.hermes.gateway"
    assert summary["working_directory"] == "/Users/cc/.hermes"
    assert summary["environment"]["HERMES_HOME"] == "/Users/cc/.hermes"
    assert summary["environment_checks"]["HERMES_HOME_matches"] is True
    assert summary["environment_checks"]["PATH_present"] is True
    assert summary["environment_checks"]["VIRTUAL_ENV_present"] is True


def test_parse_launchctl_output_finds_key_fields() -> None:
    parsed = parse_launchctl_output("state = running\nlast exit code = 78\nruns = 2\npid = 123")
    assert parsed["state"] == "running"
    assert parsed["last_exit_code"] == "78"
    assert parsed["runs"] == "2"


def test_detect_gateway_processes_filters_irrelevant_lines() -> None:
    processes = detect_gateway_processes(
        "1 0 launchd\n"
        "2 1 hermes gateway start\n"
        "3 1 python\n"
        "4 1 python -m hermes_cli.main gateway run --replace\n"
        "5 1 python /Users/cc/.hermes/ops/bin/hermes-ops run --phase D4.B --risk read-only -- hermes gateway status\n"
    )
    assert processes == ["2 1 hermes gateway start", "4 1 python -m hermes_cli.main gateway run --replace"]
