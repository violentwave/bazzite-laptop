"""Notion client for Bazzite AI Layer.

Provides safe runtime secret loading and MCP tool implementations for Notion integration.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

from ai.config import load_keys

APP_NAME = "bazzite-ai"
logger = logging.getLogger(APP_NAME)


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

    def update_page_properties(self, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Update page properties.

        Args:
            page_id: The page ID to update.
            properties: Dictionary of property updates.

        Returns:
            Updated page object.
        """
        payload = {"properties": properties}
        return self._request("PATCH", f"/v1/pages/{page_id}", json=payload)

    def create_child_page(
        self,
        parent_id: str,
        title: str,
        content: str | None = None,
    ) -> dict[str, Any]:
        """Create a child page under a parent page.

        Args:
            parent_id: The parent page ID (UUID format).
            title: Title of the new page.
            content: Optional markdown content to add as paragraph blocks.

        Returns:
            Created page object.
        """
        payload = {
            "parent": {"type": "page_id", "page_id": parent_id},
            "properties": {"title": [{"type": "text", "text": {"content": title}}]},
        }

        result = self._request("POST", "/v1/pages", json=payload)
        page_id = result.get("id")

        if content and page_id:
            self._add_paragraph_blocks(page_id, content)

        return result

    def _add_paragraph_blocks(self, page_id: str, content: str) -> None:
        """Add paragraph blocks to a page.

        Args:
            page_id: The page ID to add blocks to.
            content: Text content to add (split by newlines into paragraphs).
        """
        lines = content.strip().split("\n")
        blocks = []
        for line in lines:
            text = line.strip()
            if text:
                import re

                text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
                text = text[:1900]
                blocks.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
                    }
                )

        if blocks:
            chunk_size = 50
            for i in range(0, len(blocks), chunk_size):
                chunk = blocks[i : i + chunk_size]
                try:
                    self._request(
                        "POST", f"/v1/blocks/{page_id}/children", json={"children": chunk}
                    )
                except Exception:
                    for block in chunk:
                        try:
                            self._request(
                                "POST", f"/v1/blocks/{page_id}/children", json={"children": [block]}
                            )
                        except Exception:
                            logger.debug("Failed to add individual block")
                        pass

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()


def get_client() -> NotionClient:
    """Get a configured NotionClient instance.

    Returns:
        NotionClient with credentials from keys.env.
    """
    return NotionClient()
