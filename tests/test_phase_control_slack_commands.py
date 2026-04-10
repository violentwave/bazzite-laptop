"""Slack command parser tests for P55."""

from ai.phase_control.slack_commands import SlackCommandType, parse_slack_command


def test_parse_supported_command_with_reason():
    cmd = parse_slack_command(
        "approve ship it",
        channel="C1",
        thread_ts="123.45",
        expected_channel="C1",
        expected_thread_ts="123.45",
    )
    assert cmd is not None
    assert cmd.command == SlackCommandType.APPROVE
    assert cmd.reason_text == "ship it"


def test_parse_unknown_command_returns_none():
    cmd = parse_slack_command(
        "launch-now",
        channel="C1",
        thread_ts="123.45",
        expected_channel="C1",
        expected_thread_ts="123.45",
    )
    assert cmd is None


def test_parse_ignores_wrong_channel_or_thread():
    cmd = parse_slack_command(
        "status",
        channel="C2",
        thread_ts="123.45",
        expected_channel="C1",
        expected_thread_ts="123.45",
    )
    assert cmd is None

    cmd = parse_slack_command(
        "status",
        channel="C1",
        thread_ts="999.00",
        expected_channel="C1",
        expected_thread_ts="123.45",
    )
    assert cmd is None
