"""MCP tool filtering middleware.

Server-side filtering that exposes only relevant tools per request based on
namespace tags and semantic matching. Prevents tool selection degradation
as tool count grows past 60.
"""

import logging
from pathlib import Path

import lancedb
import pyarrow as pa
import yaml

from ai.config import CONFIGS_DIR, VECTOR_DB_DIR
from ai.rag.embedder import embed_single as embed  # noqa: PLC0415

logger = logging.getLogger("ai.mcp_bridge")

TOOL_GROUPS: dict[str, list[str]] = {
    "security": ["security.", "agents.security"],
    "system": ["system.", "agents.timer", "agents.performance"],
    "knowledge": ["knowledge.", "code.", "agents.knowledge", "agents.code"],
    "logs": ["logs."],
    "gaming": ["gaming."],
    "memory": ["memory."],
    "metrics": [
        "system.metrics",
        "system.provider",
        "system.budget",
        "system.weekly",
        "system.pipeline",
    ],
    "all": [],  # empty = no filtering, expose everything
}

CORE_TOOLS: set[str] = {
    "health",
    "system.disk_usage",
    "system.memory_usage",
    "system.service_status",
    "system.mcp_manifest",
}

_KEYWORDS_TO_NAMESPACE: dict[str, str] = {
    "cve": "security",
    "threat": "security",
    "virus": "security",
    "malware": "security",
    "scan": "security",
    "clamav": "security",
    "disk": "system",
    "cpu": "system",
    "ram": "system",
    "gpu": "system",
    "service": "system",
    "model": "metrics",
    "budget": "metrics",
    "token": "metrics",
    "pipeline": "metrics",
    "provider": "metrics",
    "log": "logs",
    "anomaly": "logs",
    "rag": "knowledge",
    "search": "knowledge",
    "code": "knowledge",
    "game": "gaming",
    "mangohud": "gaming",
}


def _detect_namespace_from_message(message: str) -> list[str]:
    """Detect relevant namespaces from user message keywords."""
    message_lower = message.lower()
    namespaces = set()
    for keyword, namespace in _KEYWORDS_TO_NAMESPACE.items():
        if keyword in message_lower:
            namespaces.add(namespace)
    if not namespaces:
        namespaces.add("system")  # Default fallback
    return list(namespaces)


class ToolFilter:
    """Server-side tool filtering based on namespace and semantic search."""

    def __init__(self, allowlist_path: Path | None = None):
        self.allowlist_path = allowlist_path or (CONFIGS_DIR / "mcp-bridge-allowlist.yaml")
        self._tools: dict[str, dict] = {}
        self._db = None
        self._table = None
        self._load_allowlist()
        self._init_lancedb()

    def _load_allowlist(self) -> None:
        """Load tool definitions from allowlist YAML."""
        with open(self.allowlist_path) as f:
            data = yaml.safe_load(f) or {}
        self._tools = data.get("tools", {})

    def _init_lancedb(self) -> None:
        """Initialize LanceDB table for semantic tool search."""
        try:
            db_path = str(VECTOR_DB_DIR)
            self._db = lancedb.connect(db_path)

            schema = pa.schema(
                [
                    pa.field("tool_name", pa.string()),
                    pa.field("description", pa.string()),
                    pa.field("namespace", pa.string()),
                    pa.field("tags", pa.list_(pa.string())),
                    pa.field("vector", pa.list_(pa.float32(), 768)),
                ]
            )

            table_names = self._db.list_tables()
            if "tool_metadata" in table_names:
                self._table = self._db.open_table("tool_metadata")
            else:
                self._table = self._db.create_table("tool_metadata", schema=schema)
                self._populate_initial_data()
        except Exception as e:
            logger.warning(f"Failed to init LanceDB for tool_filter: {e}")
            self._db = None
            self._table = None

    def _populate_initial_data(self) -> None:
        """Populate initial tool metadata from allowlist."""
        if self._table is None:
            return

        records = []
        for tool_name, tool_def in self._tools.items():
            namespace = "unknown"
            for ns, prefixes in TOOL_GROUPS.items():
                for prefix in prefixes:
                    if tool_name.startswith(prefix):
                        namespace = ns
                        break

            description = tool_def.get("description", "")
            text_to_embed = f"{tool_name} {description}"

            try:
                vector = embed(text_to_embed)
            except Exception as e:
                logger.warning(f"Failed to embed {tool_name}: {e}")
                vector = [0.0] * 768

            records.append(
                {
                    "tool_name": tool_name,
                    "description": description,
                    "namespace": namespace,
                    "tags": [namespace],
                    "vector": vector,
                }
            )

        if records:
            self._table.add(records)

    def filter_by_namespace(self, namespaces: list[str]) -> list[str]:
        """Return tool names matching any of the given namespace prefixes."""
        if not namespaces or "all" in namespaces:
            return list(self._tools.keys())

        matched = set()
        for namespace in namespaces:
            prefixes = TOOL_GROUPS.get(namespace, [f"{namespace}."])
            for tool_name in self._tools:
                for prefix in prefixes:
                    if tool_name.startswith(prefix):
                        matched.add(tool_name)
                        break

        return list(matched)

    def filter_by_query(self, query: str, top_k: int = 15) -> list[str]:
        """Embed query, search tool_metadata, return top_k relevant tool names."""
        if self._table is None or not query:
            return list(self._tools.keys())[:top_k]

        try:
            query_vector = embed(query)
        except Exception as e:
            logger.warning(f"Failed to embed query: {e}")
            return list(self._tools.keys())[:top_k]

        try:
            df = self._table.to_pandas()
            if df.empty:
                return list(self._tools.keys())[:top_k]

            # Simple cosine similarity
            import numpy as np

            vectors = np.array(df["vector"].tolist())
            query_vec = np.array(query_vector).reshape(1, -1)

            # Normalize
            vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
            query_vec = query_vec / np.linalg.norm(query_vec, keepdims=True)

            # Compute similarities
            similarities = vectors @ query_vec.T.flatten()

            # Get top_k indices
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            return df.iloc[top_indices]["tool_name"].tolist()
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return list(self._tools.keys())[:top_k]

    def get_context_tools(self, user_message: str, task_type: str | None = None) -> list[str]:
        """Get tools to expose for this request.

        Combines: always include CORE_TOOLS, add namespace-matched tools
        based on keywords, fill remaining slots via semantic search.
        Max 15 tools returned.
        """
        max_tools = 15
        result = set(CORE_TOOLS)

        # Detect namespace from message
        namespaces = _detect_namespace_from_message(user_message)

        # Add namespace-matched tools
        ns_tools = self.filter_by_namespace(namespaces)
        result.update(ns_tools)

        # If we have room, fill with semantic search
        remaining = max_tools - len(result)
        if remaining > 0:
            semantic_tools = self.filter_by_query(user_message, top_k=remaining)
            for tool in semantic_tools:
                if len(result) >= max_tools:
                    break
                result.add(tool)

        # Filter to only existing tools
        final_result = [t for t in result if t in self._tools]

        # Ensure core tools are always included
        final_result = list(set(final_result) | CORE_TOOLS)

        return final_result[:max_tools]

    def get_all_tools(self) -> list[str]:
        """Return all tool names (bypass filtering, for admin/debug)."""
        return list(self._tools.keys())


_filter_instance: ToolFilter | None = None


def get_filter() -> ToolFilter:
    """Get singleton ToolFilter instance."""
    global _filter_instance
    if _filter_instance is None:
        _filter_instance = ToolFilter()
    return _filter_instance
