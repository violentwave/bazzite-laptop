"""Slack MCP tool handlers."""

from typing import Any

from ai.slack.client import SlackClient, get_slack_config, is_slack_configured


async def handle_slack_list_channels(args: dict[str, Any]) -> dict[str, Any]:
    """List Slack channels.

    Args:
        args: Tool arguments (limit, etc.).

    Returns:
        List of channels.
    """
    if not is_slack_configured():
        return {"error": "Slack not configured: missing bot token in keys.env"}

    client = get_slack_config()
    slack = SlackClient(client)

    try:
        limit = int(args.get("limit", 100))
        channels = slack.list_channels(limit=limit)
        return {"channels": channels, "count": len(channels)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        slack.close()


async def handle_slack_post_message(args: dict[str, Any]) -> dict[str, Any]:
    """Post a message to Slack channel.

    Args:
        args: Tool arguments (channel, text, thread_ts).

    Returns:
        Message result.
    """
    if not is_slack_configured():
        return {"error": "Slack not configured: missing bot token in keys.env"}

    channel = args.get("channel")
    text = args.get("text")

    if not channel or not text:
        return {"error": "Missing required arguments: channel, text"}

    client = get_slack_config()
    slack = SlackClient(client)

    try:
        thread_ts = args.get("thread_ts")
        result = slack.post_message(channel, text, thread_ts=thread_ts)
        return {
            "ok": True,
            "channel": result.get("channel"),
            "ts": result.get("ts"),
            "message": "Message posted successfully",
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        slack.close()


async def handle_slack_list_users(args: dict[str, Any]) -> dict[str, Any]:
    """List Slack workspace users.

    Args:
        args: Tool arguments.

    Returns:
        List of users.
    """
    if not is_slack_configured():
        return {"error": "Slack not configured: missing bot token in keys.env"}

    client = get_slack_config()
    slack = SlackClient(client)

    try:
        users = slack.list_users()
        return {"users": users, "count": len(users)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        slack.close()


async def handle_slack_get_history(args: dict[str, Any]) -> dict[str, Any]:
    """Get channel message history.

    Args:
        args: Tool arguments (channel, limit).

    Returns:
        Messages from channel.
    """
    if not is_slack_configured():
        return {"error": "Slack not configured: missing bot token in keys.env"}

    channel = args.get("channel")
    if not channel:
        return {"error": "Missing required argument: channel"}

    client = get_slack_config()
    slack = SlackClient(client)

    try:
        limit = int(args.get("limit", 100))
        messages = slack.get_channel_history(channel, limit=limit)
        return {"messages": messages, "count": len(messages)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        slack.close()
