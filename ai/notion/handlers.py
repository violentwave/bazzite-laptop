"""Notion MCP tool handlers with optional governance integration."""

from typing import Any

from ai.integration_governance import (
    IntegrationContext,
    get_governance,
)
from ai.notion.client import NotionClient, get_notion_config, is_notion_configured

_governance_enabled = True


async def handle_notion_search(args: dict[str, Any]) -> dict[str, Any]:
    """Search pages and databases in Notion.

    Args:
        args: Tool arguments (query, filter_type, limit).

    Returns:
        Search results.
    """
    if _governance_enabled:
        gov = get_governance()
        result = gov.evaluate("notion.search", IntegrationContext(), args)
        if not result.allowed:
            return {"error": result.reason, "governance": "blocked"}

    if not is_notion_configured():
        return {"error": "Notion not configured: missing API key in keys.env"}

    client = get_notion_config()
    notion = NotionClient(client)

    try:
        query = args.get("query", "")
        filter_type = args.get("filter_type")
        limit = int(args.get("limit", 10))
        results = notion.search(query=query, filter_type=filter_type, limit=limit)
        return {"results": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        notion.close()


async def handle_notion_get_page(args: dict[str, Any]) -> dict[str, Any]:
    """Get a Notion page by ID.

    Args:
        args: Tool arguments (page_id).

    Returns:
        Page data.
    """
    if _governance_enabled:
        gov = get_governance()
        result = gov.evaluate("notion.get_page", IntegrationContext(), args)
        if not result.allowed:
            return {"error": result.reason, "governance": "blocked"}

    if not is_notion_configured():
        return {"error": "Notion not configured: missing API key in keys.env"}

    page_id = args.get("page_id")
    if not page_id:
        return {"error": "Missing required argument: page_id"}

    client = get_notion_config()
    notion = NotionClient(client)

    try:
        page = notion.get_page(page_id)
        return {"page": page}
    except Exception as e:
        return {"error": str(e)}
    finally:
        notion.close()


async def handle_notion_get_page_content(args: dict[str, Any]) -> dict[str, Any]:
    """Get content blocks from a Notion page.

    Args:
        args: Tool arguments (page_id).

    Returns:
        Page content blocks.
    """
    if _governance_enabled:
        gov = get_governance()
        result = gov.evaluate("notion.get_page_content", IntegrationContext(), args)
        if not result.allowed:
            return {"error": result.reason, "governance": "blocked"}

    if not is_notion_configured():
        return {"error": "Notion not configured: missing API key in keys.env"}

    page_id = args.get("page_id")
    if not page_id:
        return {"error": "Missing required argument: page_id"}

    client = get_notion_config()
    notion = NotionClient(client)

    try:
        blocks = notion.get_page_content(page_id)
        return {"blocks": blocks, "count": len(blocks)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        notion.close()


async def handle_notion_query_database(args: dict[str, Any]) -> dict[str, Any]:
    """Query a Notion database.

    Args:
        args: Tool arguments (database_id, filter, limit).

    Returns:
        Database query results.
    """
    if _governance_enabled:
        gov = get_governance()
        result = gov.evaluate("notion.query_database", IntegrationContext(), args)
        if not result.allowed:
            return {"error": result.reason, "governance": "blocked"}

    if not is_notion_configured():
        return {"error": "Notion not configured: missing API key in keys.env"}

    database_id = args.get("database_id")
    if not database_id:
        return {"error": "Missing required argument: database_id"}

    client = get_notion_config()
    notion = NotionClient(client)

    try:
        filter_obj = args.get("filter")
        limit = int(args.get("limit", 100))
        results = notion.query_database(database_id, filter_obj=filter_obj, limit=limit)
        return {"results": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        notion.close()
