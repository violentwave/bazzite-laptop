"""Tool lifecycle management.

P101: MCP Tool Governance + Analytics Platform

Manages tool versioning, deprecation, and retirement workflows.
"""

from datetime import datetime, timedelta

from ai.mcp_bridge.governance.models import (
    LifecycleState,
    MigrationPath,
    ToolLifecycleState,
)


class ToolLifecycleManager:
    """Manages tool versioning, deprecation, and retirement.

    Provides systematic lifecycle management for MCP tools including
    version tracking, deprecation workflows, and retirement procedures.
    """

    def __init__(self):
        """Initialize lifecycle manager."""
        self._lifecycle_states: dict[str, ToolLifecycleState] = {}
        self._migration_paths: dict[str, MigrationPath] = {}
        self._initialize_builtin_tools()

    def _initialize_builtin_tools(self) -> None:
        """Initialize lifecycle states for all 133 built-in tools."""
        # This would ideally be loaded from a configuration file
        # For now, initialize all tools as active
        builtin_tools = [
            # Security tools
            ("security.last_scan", "security"),
            ("security.health_snapshot", "security"),
            ("security.status", "security"),
            ("security.threat_lookup", "security"),
            ("security.ip_lookup", "security"),
            ("security.url_lookup", "security"),
            ("security.run_scan", "security"),
            ("security.run_health", "security"),
            ("security.sandbox_submit", "security"),
            ("security.cve_check", "security"),
            ("security.threat_summary", "security"),
            ("security.alert_summary", "security"),
            ("security.run_ingest", "security"),
            ("security.ops_overview", "security"),
            ("security.ops_findings", "security"),
            ("security.ops_provider_health", "security"),
            ("security.correlate", "security"),
            ("security.recommend_action", "security"),
            # System tools
            ("system.disk_usage", "system"),
            ("system.cpu_temps", "system"),
            ("system.gpu_status", "system"),
            ("system.memory_usage", "system"),
            ("system.uptime", "system"),
            ("system.service_status", "system"),
            ("system.llm_models", "system"),
            ("system.key_status", "system"),
            ("system.release_watch", "system"),
            ("system.fedora_updates", "system"),
            ("system.pkg_intel", "system"),
            ("system.gpu_perf", "system"),
            ("system.gpu_health", "system"),
            ("system.cache_stats", "system"),
            ("system.token_report", "system"),
            ("system.pipeline_status", "system"),
            ("system.budget_status", "system"),
            ("system.metrics_summary", "system"),
            ("system.provider_status", "system"),
            ("system.perf_profile", "system"),
            ("system.mcp_audit", "system"),
            ("system.mcp_manifest", "system"),
            ("system.llm_status", "system"),
            ("system.alert_history", "system"),
            ("system.alert_rules", "system"),
            ("system.dep_audit", "system"),
            ("system.dep_audit_history", "system"),
            ("system.dep_scan", "system"),
            ("system.weekly_insights", "system"),
            ("system.insights", "system"),
            ("system.create_tool", "system"),
            ("system.list_dynamic_tools", "system"),
            ("system.test_analysis", "system"),
            # Knowledge tools
            ("knowledge.rag_query", "knowledge"),
            ("knowledge.rag_qa", "knowledge"),
            ("knowledge.ingest_docs", "knowledge"),
            ("knowledge.pattern_search", "knowledge"),
            ("knowledge.task_patterns", "knowledge"),
            ("knowledge.session_history", "knowledge"),
            # Shell tools
            ("shell.create_session", "shell"),
            ("shell.list_sessions", "shell"),
            ("shell.get_session", "shell"),
            ("shell.execute_command", "shell"),
            ("shell.terminate_session", "shell"),
            ("shell.get_context", "shell"),
            ("shell.get_audit_log", "shell"),
            # Project tools
            ("project.context", "project"),
            ("project.workflow_history", "project"),
            ("project.phase_timeline", "project"),
            ("project.artifacts", "project"),
            # Code tools
            ("code.search", "code"),
            ("code.rag_query", "code"),
            ("code.fused_context", "code"),
            ("code.impact_analysis", "code"),
            ("code.dependency_graph", "code"),
            ("code.blast_radius", "code"),
            ("code.find_callers", "code"),
            ("code.suggest_tests", "code"),
            ("code.complexity_report", "code"),
            ("code.class_hierarchy", "code"),
            # Workflow tools
            ("workflow.list", "workflow"),
            ("workflow.run", "workflow"),
            ("workflow.agents", "workflow"),
            ("workflow.handoff", "workflow"),
            ("workflow.history", "workflow"),
            ("workflow.status", "workflow"),
            ("workflow.history_steps", "workflow"),
            ("workflow.cancel", "workflow"),
            # Agents tools
            ("agents.security_audit", "agents"),
            ("agents.performance_tuning", "agents"),
            ("agents.knowledge_storage", "agents"),
            ("agents.code_quality", "agents"),
            ("agents.timer_health", "agents"),
            # Collab tools
            ("collab.queue_status", "collab"),
            ("collab.add_task", "collab"),
            ("collab.search_knowledge", "collab"),
            # Intel tools
            ("intel.scrape_now", "intel"),
            ("intel.ingest_pending", "intel"),
            # Settings tools
            ("settings.pin_status", "settings"),
            ("settings.setup_pin", "settings"),
            ("settings.verify_pin", "settings"),
            ("settings.list_secrets", "settings"),
            ("settings.reveal_secret", "settings"),
            ("settings.set_secret", "settings"),
            ("settings.delete_secret", "settings"),
            ("settings.audit_log", "settings"),
            # Logs tools
            ("logs.health_trend", "logs"),
            ("logs.scan_history", "logs"),
            ("logs.anomalies", "logs"),
            ("logs.search", "logs"),
            ("logs.stats", "logs"),
            # Memory tools
            ("memory.search", "memory"),
            # Providers tools
            ("providers.discover", "providers"),
            ("providers.models", "providers"),
            ("providers.routing", "providers"),
            ("providers.refresh", "providers"),
            ("providers.health", "providers"),
            # Notion tools
            ("notion.search", "notion"),
            ("notion.get_page", "notion"),
            ("notion.get_page_content", "notion"),
            ("notion.query_database", "notion"),
            # Slack tools
            ("slack.list_channels", "slack"),
            ("slack.list_users", "slack"),
            ("slack.get_history", "slack"),
            ("slack.post_message", "slack"),
            # Figma tools
            ("figma.list_teams", "figma"),
            ("figma.list_projects", "figma"),
            ("figma.list_project_files", "figma"),
            ("figma.get_file", "figma"),
            ("figma.find_project", "figma"),
            ("figma.reconcile", "figma"),
            # Gaming tools
            ("gaming.profiles", "gaming"),
            ("gaming.mangohud_preset", "gaming"),
        ]

        for tool_name, _category in builtin_tools:
            self._lifecycle_states[tool_name] = ToolLifecycleState(
                tool_name=tool_name,
                current_state=LifecycleState.ACTIVE,
                version="1.0.0",
            )

    async def register_version(
        self,
        tool_name: str,
        version: str,
        changelog: str | None = None,
    ) -> ToolLifecycleState:
        """Register a new tool version.

        Args:
            tool_name: Name of the tool
            version: New version string (semver)
            changelog: Optional changelog description

        Returns:
            Updated lifecycle state
        """
        if tool_name not in self._lifecycle_states:
            self._lifecycle_states[tool_name] = ToolLifecycleState(
                tool_name=tool_name,
                current_state=LifecycleState.ACTIVE,
                version=version,
            )
        else:
            self._lifecycle_states[tool_name].version = version

        return self._lifecycle_states[tool_name]

    async def deprecate_tool(
        self,
        tool_name: str,
        replacement_tool: str | None = None,
        migration_guide: str | None = None,
        sunset_days: int = 30,
    ) -> ToolLifecycleState:
        """Mark tool as deprecated with migration guidance.

        Args:
            tool_name: Name of the tool to deprecate
            replacement_tool: Optional replacement tool name
            migration_guide: Optional migration documentation
            sunset_days: Days until tool is retired

        Returns:
            Updated lifecycle state
        """
        if tool_name not in self._lifecycle_states:
            raise ValueError(f"Tool {tool_name} not found")

        state = self._lifecycle_states[tool_name]
        state.current_state = LifecycleState.DEPRECATED
        state.deprecated_at = datetime.utcnow()
        state.sunset_date = datetime.utcnow() + timedelta(days=sunset_days)
        state.replacement_tool = replacement_tool
        state.migration_guide = migration_guide

        # Register migration path if replacement provided
        if replacement_tool:
            self._migration_paths[tool_name] = MigrationPath(
                from_tool=tool_name,
                to_tool=replacement_tool,
                compatibility_level="partial",
                migration_steps=[
                    f"Replace calls to {tool_name} with {replacement_tool}",
                    "Update argument names if different",
                    "Test functionality in staging environment",
                ],
            )

        return state

    async def mark_legacy(self, tool_name: str) -> ToolLifecycleState:
        """Mark tool as legacy (maintenance only).

        Args:
            tool_name: Name of the tool

        Returns:
            Updated lifecycle state
        """
        if tool_name not in self._lifecycle_states:
            raise ValueError(f"Tool {tool_name} not found")

        state = self._lifecycle_states[tool_name]
        state.current_state = LifecycleState.LEGACY

        return state

    async def retire_tool(self, tool_name: str) -> ToolLifecycleState:
        """Permanently retire a tool.

        Args:
            tool_name: Name of the tool to retire

        Returns:
            Updated lifecycle state
        """
        if tool_name not in self._lifecycle_states:
            raise ValueError(f"Tool {tool_name} not found")

        state = self._lifecycle_states[tool_name]
        state.current_state = LifecycleState.RETIRED
        state.retired_at = datetime.utcnow()

        return state

    async def get_lifecycle_state(self, tool_name: str) -> ToolLifecycleState | None:
        """Get current lifecycle state of a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Lifecycle state or None if tool not found
        """
        return self._lifecycle_states.get(tool_name)

    async def list_tools_by_state(
        self,
        state: LifecycleState | None = None,
    ) -> list[ToolLifecycleState]:
        """List tools filtered by lifecycle state.

        Args:
            state: Optional state filter

        Returns:
            List of lifecycle states
        """
        tools = list(self._lifecycle_states.values())

        if state:
            tools = [t for t in tools if t.current_state == state]

        return sorted(tools, key=lambda t: t.tool_name)

    async def get_migration_path(self, tool_name: str) -> MigrationPath | None:
        """Get migration path for a deprecated tool.

        Args:
            tool_name: Name of the deprecated tool

        Returns:
            Migration path or None
        """
        return self._migration_paths.get(tool_name)

    async def check_deprecated_tools(self) -> list[ToolLifecycleState]:
        """Check for tools that should be retired.

        Returns:
            List of tools past their sunset date
        """
        now = datetime.utcnow()
        overdue = []

        for state in self._lifecycle_states.values():
            if (
                state.current_state == LifecycleState.DEPRECATED
                and state.sunset_date
                and state.sunset_date <= now
            ):
                overdue.append(state)

        return overdue

    async def get_statistics(self) -> dict:
        """Get lifecycle statistics.

        Returns:
            Dictionary with counts by state
        """
        stats = {
            "total": len(self._lifecycle_states),
            "active": 0,
            "deprecated": 0,
            "legacy": 0,
            "retired": 0,
        }

        for state in self._lifecycle_states.values():
            if state.current_state == LifecycleState.ACTIVE:
                stats["active"] += 1
            elif state.current_state == LifecycleState.DEPRECATED:
                stats["deprecated"] += 1
            elif state.current_state == LifecycleState.LEGACY:
                stats["legacy"] += 1
            elif state.current_state == LifecycleState.RETIRED:
                stats["retired"] += 1

        return stats

    async def reactivate_tool(self, tool_name: str) -> ToolLifecycleState:
        """Reactivate a deprecated or legacy tool.

        Args:
            tool_name: Name of the tool to reactivate

        Returns:
            Updated lifecycle state
        """
        if tool_name not in self._lifecycle_states:
            raise ValueError(f"Tool {tool_name} not found")

        state = self._lifecycle_states[tool_name]
        state.current_state = LifecycleState.ACTIVE
        state.deprecated_at = None
        state.sunset_date = None
        state.retired_at = None

        # Remove migration path if exists
        if tool_name in self._migration_paths:
            del self._migration_paths[tool_name]

        return state
