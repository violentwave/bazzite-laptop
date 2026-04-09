"""Slack client for Bazzite AI Layer.

Provides safe runtime secret loading and MCP tool implementations for Slack integration.
"""

import os
from dataclasses import dataclass
from typing import Any

import httpx

from ai.config import load_keys

APP_NAME = "bazzite-ai"


@dataclass
class SlackConfig:
    """Configuration for Slack client."""

    bot_token: str | None = None
    app_token: str | None = None
    signing_secret: str | None = None
    team_id: str | None = None


def get_slack_config() -> SlackConfig:
    """Load Slack configuration from keys.env using scoped loading.

    Returns:
        SlackConfig with tokens loaded from environment.
    """
    load_keys(scope="slack")
    return SlackConfig(
        bot_token=os.environ.get("SLACK_BOT_TOKEN"),
        app_token=os.environ.get("SLACK_APP_TOKEN"),
        signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    )


def is_slack_configured() -> bool:
    """Check if Slack is configured with required credentials.

    Returns:
        True if bot_token is set.
    """
    config = get_slack_config()
    return config.bot_token is not None and config.bot_token != ""


def redact_token(token: str | None) -> str | None:
    """Redact Slack token for safe logging.

    Args:
        token: The token to redact.

    Returns:
        Redacted string like "xoxb-****abc" or None.
    """
    if not token:
        return None
    if len(token) <= 8:
        return "xoxb-****"
    return f"{token[:8]}****{token[-4:]}"


class SlackClient:
    """Slack API client with scoped secret loading."""

    def __init__(self, config: SlackConfig | None = None):
        """Initialize Slack client.

        Args:
            config: Optional SlackConfig. If not provided, loads from keys.env.
        """
        self._config = config or get_slack_config()
        self._client = httpx.Client(
            headers=self._build_headers(),
            timeout=30.0,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers with bot token."""
        headers = {"Content-Type": "application/json"}
        if self._config.bot_token:
            headers["Authorization"] = f"Bearer {self._config.bot_token}"
        return headers

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make authenticated request to Slack API.

        Args:
            method: HTTP method (GET, POST).
            endpoint: Slack API endpoint (e.g., "/conversations.list").
            **kwargs: Additional arguments passed to httpx.

        Returns:
            Slack API response as dictionary.

        Raises:
            ValueError: If Slack is not configured.
            httpx.HTTPStatusError: On API errors.
        """
        if not self._config.bot_token:
            raise ValueError("Slack not configured: missing bot token")

        url = f"https://slack.com/api{endpoint}"
        response = self._client.request(method, url, **kwargs)
        response.raise_for_status()

        data = response.json()
        if not data.get("ok", False):
            error = data.get("error", "unknown")
            raise ValueError(f"Slack API error: {error}")

        return data

    def list_channels(self, limit: int = 100) -> list[dict[str, Any]]:
        """List Slack channels.

        Args:
            limit: Maximum number of channels to return.

        Returns:
            List of channel objects.
        """
        result = self._request("GET", "/conversations.list", params={"limit": limit})
        return result.get("channels", [])

    def post_message(
        self,
        channel: str,
        text: str,
        thread_ts: str | None = None,
    ) -> dict[str, Any]:
        """Post a message to a Slack channel.

        Args:
            channel: Channel ID (e.g., "C01234567").
            text: Message text.
            thread_ts: Optional thread timestamp to reply in thread.

        Returns:
            Message response with ts and channel.
        """
        payload: dict[str, Any] = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts

        return self._request("POST", "/chat.postMessage", json=payload)

    def get_channel_history(
        self,
        channel: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get message history from a channel.

        Args:
            channel: Channel ID.
            limit: Maximum number of messages.

        Returns:
            List of message objects.
        """
        result = self._request(
            "GET",
            "/conversations.history",
            params={"channel": channel, "limit": limit},
        )
        return result.get("messages", [])

    def list_users(self) -> list[dict[str, Any]]:
        """List Slack workspace users.

        Returns:
            List of user objects.
        """
        result = self._request("GET", "/users.list")
        return result.get("members", [])

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()


def get_client() -> SlackClient:
    """Get a configured SlackClient instance.

    Returns:
        SlackClient with credentials from keys.env.
    """
    return SlackClient()
