"""Notion client for Bazzite AI Layer.

Provides safe runtime secret loading and MCP tool implementations for Notion integration.
"""

import os
from dataclasses import dataclass
from typing import Any

import httpx

from ai.config import load_keys

APP_NAME = "bazzite-ai"


@dataclass
class NotionConfig:
    """Configuration for Notion client."""

    api_key: str | None = None


def get_notion_config() -> NotionConfig:
    """Load Notion configuration from keys.env using scoped loading.

    Returns:
        NotionConfig with API key loaded from environment.
    """
    load_keys(scope="notion")
    return NotionConfig(
        api_key=os.environ.get("NOTION_API_KEY"),
    )


def is_notion_configured() -> bool:
    """Check if Notion is configured with required credentials.

    Returns:
        True if api_key is set.
    """
    config = get_notion_config()
    return config.api_key is not None and config.api_key != ""


def redact_api_key(api_key: str | None) -> str | None:
    """Redact Notion API key for safe logging.

    Args:
        api_key: The API key to redact.

    Returns:
        Redacted string like "secret_****abc" or None.
    """
    if not api_key:
        return None
    if len(api_key) <= 12:
        return "secret_****"
    return f"{api_key[:12]}****{api_key[-4:]}"


class NotionClient:
    """Notion API client with scoped secret loading."""

    def __init__(self, config: NotionConfig | None = None):
        """Initialize Notion client.

        Args:
            config: Optional NotionConfig. If not provided, loads from keys.env.
        """
        self._config = config or get_notion_config()
        self._client = httpx.Client(
            headers=self._build_headers(),
            timeout=30.0,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers with API key."""
        headers = {"Content-Type": "application/json", "Notion-Version": "2022-06-28"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make authenticated request to Notion API.

        Args:
            method: HTTP method (GET, POST).
            endpoint: Notion API endpoint (e.g., "/v1/search").
            **kwargs: Additional arguments passed to httpx.

        Returns:
            Notion API response as dictionary.

        Raises:
            ValueError: If Notion is not configured.
            httpx.HTTPStatusError: On API errors.
        """
        if not self._config.api_key:
            raise ValueError("Notion not configured: missing API key")

        url = f"https://api.notion.com{endpoint}"
        response = self._client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def search(
        self, query: str = "", filter_type: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search pages and databases in Notion.

        Args:
            query: Search query string.
            filter_type: Filter by "page" or "database".
            limit: Maximum number of results.

        Returns:
            List of search results.
        """
        payload: dict[str, Any] = {"page_size": limit}
        if query:
            payload["query"] = query
        if filter_type:
            payload["filter"] = {"property": "object", "value": filter_type}

        result = self._request("POST", "/v1/search", json=payload)
        return result.get("results", [])

    def get_page(self, page_id: str) -> dict[str, Any]:
        """Get a page by ID.

        Args:
            page_id: The page ID (UUID format).

        Returns:
            Page object with content.
        """
        return self._request("GET", f"/v1/pages/{page_id}")

    def get_page_content(self, page_id: str) -> list[dict[str, Any]]:
        """Get page blocks/content.

        Args:
            page_id: The page ID (UUID format).

        Returns:
            List of blocks.
        """
        result = self._request("GET", f"/v1/blocks/{page_id}/children?page_size=100")
        return result.get("results", [])

    def query_database(
        self, database_id: str, filter_obj: dict[str, Any] | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Query a database.

        Args:
            database_id: The database ID (UUID format).
            filter_obj: Optional filter object.
            limit: Maximum number of results.

        Returns:
            List of database entries.
        """
        payload: dict[str, Any] = {"page_size": limit}
        if filter_obj:
            payload["filter"] = filter_obj

        return self._request("POST", f"/v1/databases/{database_id}/query", json=payload).get(
            "results", []
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()


def get_client() -> NotionClient:
    """Get a configured NotionClient instance.

    Returns:
        NotionClient with credentials from keys.env.
    """
    return NotionClient()
