"""External MCP server discovery for P105.

Provides read-only discovery and inventory of external MCP servers
without executing untrusted code or exposing secrets.
"""

from __future__ import annotations

import hashlib
import logging
import re
import urllib.parse
from typing import Any

from ai.mcp_bridge.federation.models import (
    CapabilityMap,
    ExternalServerIdentity,
    ExternalToolDefinition,
    ServerCapability,
    ServerToolManifest,
    TrustState,
)

logger = logging.getLogger("ai.mcp_bridge.federation.discovery")

MAX_MANIFEST_SIZE = 1024 * 1024
MAX_TOOLS = 500
MAX_TOOL_NAME_LENGTH = 128
VALID_URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")


class DiscoveryError(Exception):
    """Error during federation discovery."""

    pass


class ExternalServerDiscovery:
    """Discovers and inventories external MCP servers.

    Read-only discovery mode - does not execute remote tools.
    Validates all external manifests as untrusted input.
    """

    def __init__(self, timeout: float = 10.0):
        """Initialize discovery.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self._timeout = timeout
        self._discovered_servers: dict[str, ExternalServerIdentity] = {}

    def validate_server_url(self, url: str) -> tuple[bool, str]:
        """Validate server URL.

        Args:
            url: Server URL to validate

        Returns:
            Tuple of (valid, error_message)
        """
        if not url:
            return False, "URL is required"

        if not VALID_URL_PATTERN.match(url):
            return False, "URL must be HTTP or HTTPS"

        parsed = urllib.parse.urlparse(url)
        if not parsed.netloc:
            return False, "Invalid URL format"

        return True, ""

    def validate_tool_definition(self, tool: dict[str, Any]) -> tuple[bool, str]:
        """Validate tool definition from external manifest.

        Args:
            tool: Tool definition dictionary

        Returns:
            Tuple of (valid, error_message)
        """
        if not isinstance(tool, dict):
            return False, "Tool must be a dictionary"

        name = tool.get("name", "")
        if not name:
            return False, "Tool name is required"

        if len(name) > MAX_TOOL_NAME_LENGTH:
            return False, f"Tool name exceeds {MAX_TOOL_NAME_LENGTH} characters"

        if not re.match(r"^[a-zA-Z0-9._-]+$", name):
            return False, "Tool name contains invalid characters"

        input_schema = tool.get("inputSchema", tool.get("input_schema", {}))
        if not isinstance(input_schema, dict):
            return False, "inputSchema must be a dictionary"

        return True, ""

    def validate_manifest(self, manifest: dict[str, Any], server_id: str) -> tuple[bool, list[str]]:
        """Validate tool manifest from external server.

        Args:
            manifest: Raw manifest dictionary
            server_id: Server identifier

        Returns:
            Tuple of (valid, list of errors)
        """
        errors = []

        if not isinstance(manifest, dict):
            return False, ["Manifest must be a dictionary"]

        tools = manifest.get("tools", [])
        if not isinstance(tools, list):
            errors.append("tools must be a list")
            tools = []

        if len(tools) > MAX_TOOLS:
            errors.append(f"Too many tools: {len(tools)} (max {MAX_TOOLS})")

        for i, tool in enumerate(tools[:10]):
            valid, error = self.validate_tool_definition(tool)
            if not valid:
                errors.append(f"Tool {i}: {error}")

        return len(errors) == 0, errors

    def compute_server_id(self, url: str) -> str:
        """Compute stable server ID from URL.

        Args:
            url: Server URL

        Returns:
            Stable server ID (hash)
        """
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    async def discover_server(
        self,
        url: str,
        name: str | None = None,
        description: str = "",
    ) -> ExternalServerIdentity:
        """Discover external MCP server.

        Args:
            url: Server URL
            name: Optional server name
            description: Server description

        Returns:
            External server identity

        Raises:
            DiscoveryError: If discovery fails
        """
        valid, error = self.validate_server_url(url)
        if not valid:
            raise DiscoveryError(f"Invalid server URL: {error}")

        server_id = self.compute_server_id(url)

        if name is None:
            parsed = urllib.parse.urlparse(url)
            name = parsed.netloc

        capabilities = self._detect_capabilities_from_url(url)

        identity = ExternalServerIdentity(
            server_id=server_id,
            name=name,
            url=url,
            description=description,
            capabilities=capabilities,
            trust_state=TrustState.UNKNOWN,
        )

        self._discovered_servers[server_id] = identity
        logger.info(f"Discovered external server: {server_id} ({name})")

        return identity

    def _detect_capabilities_from_url(self, url: str) -> list[ServerCapability]:
        """Detect server capabilities from URL pattern.

        Args:
            url: Server URL

        Returns:
            List of detected capabilities
        """
        capabilities = [ServerCapability.TOOLS]

        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower()

        if "resource" in path:
            capabilities.append(ServerCapability.RESOURCES)
        if "prompt" in path:
            capabilities.append(ServerCapability.PROMPTS)
        if "log" in path:
            capabilities.append(ServerCapability.LOGGING)

        return capabilities

    def parse_tool_manifest(
        self,
        manifest: dict[str, Any],
        server_id: str,
    ) -> ServerToolManifest:
        """Parse tool manifest from external server.

        Args:
            manifest: Raw manifest from server
            server_id: Server identifier

        Returns:
            Validated tool manifest

        Raises:
            DiscoveryError: If manifest is invalid
        """
        valid, errors = self.validate_manifest(manifest, server_id)
        if not valid:
            raise DiscoveryError(f"Invalid manifest: {', '.join(errors)}")

        tools = []
        for tool_data in manifest.get("tools", []):
            tool = ExternalToolDefinition(
                name=tool_data.get("name", ""),
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", tool_data.get("input_schema", {})),
                annotations=tool_data.get("annotations", {}),
            )
            tools.append(tool)

        return ServerToolManifest(
            server_id=server_id,
            tools=tools,
            resource_templates=manifest.get("resources", []),
            prompt_templates=manifest.get("prompts", []),
        )

    def compute_capability_map(
        self,
        manifest: ServerToolManifest,
    ) -> CapabilityMap:
        """Compute capability map from manifest.

        Args:
            manifest: Tool manifest

        Returns:
            Capability map
        """
        tools = manifest.tools

        has_destructive = any(t.annotations.get("destructive", False) for t in tools)
        has_system = any(t.name.startswith(("system.", "security.", "shell.")) for t in tools)

        return CapabilityMap(
            server_id=manifest.server_id,
            tools_count=len(tools),
            resources_count=len(manifest.resource_templates),
            prompts_count=len(manifest.prompt_templates),
            has_destructive_tools=has_destructive,
            has_system_tools=has_system,
            network_access=False,
            file_access=False,
        )

    def list_discovered(self) -> list[ExternalServerIdentity]:
        """List all discovered servers.

        Returns:
            List of server identities
        """
        return list(self._discovered_servers.values())

    def get_server(self, server_id: str) -> ExternalServerIdentity | None:
        """Get discovered server by ID.

        Args:
            server_id: Server identifier

        Returns:
            Server identity or None
        """
        return self._discovered_servers.get(server_id)

    def remove_server(self, server_id: str) -> bool:
        """Remove discovered server.

        Args:
            server_id: Server identifier

        Returns:
            True if removed
        """
        if server_id in self._discovered_servers:
            del self._discovered_servers[server_id]
            logger.info(f"Removed server: {server_id}")
            return True
        return False
