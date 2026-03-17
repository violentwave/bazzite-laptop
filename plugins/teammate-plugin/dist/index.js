/**
 * @claude-flow/teammate-plugin
 *
 * Native TeammateTool integration plugin for Claude Flow.
 * Bridges Claude Code v2.1.19+ multi-agent capabilities with Claude Flow.
 *
 * @example
 * ```typescript
 * import { createTeammateBridge, TEAMMATE_MCP_TOOLS } from '@claude-flow/teammate-plugin';
 *
 * // Initialize bridge
 * const bridge = await createTeammateBridge();
 *
 * // Check compatibility
 * const version = bridge.getVersionInfo();
 * console.log(`Claude Code: ${version.claudeCode}, Compatible: ${version.compatible}`);
 *
 * // Create team
 * const team = await bridge.spawnTeam({
 *   name: 'my-team',
 *   topology: 'hierarchical',
 *   maxTeammates: 6,
 * });
 *
 * // Spawn teammate (returns AgentInput for Task tool)
 * const teammate = await bridge.spawnTeammate({
 *   name: 'coder-1',
 *   role: 'coder',
 *   prompt: 'Implement the authentication feature',
 *   teamName: 'my-team',
 *   model: 'sonnet',
 * });
 * ```
 *
 * @module @claude-flow/teammate-plugin
 * @version 1.0.0-alpha.1
 * @requires Claude Code >= 2.1.19
 */
// Core exports
export { TeammateBridge, TeammateError, createTeammateBridge, } from './teammate-bridge.js';
// MCP tools exports
export { TEAMMATE_MCP_TOOLS, handleMCPTool, listTeammateTools, hasTeammateTool, } from './mcp-tools.js';
// BMSSP-powered optimization exports
export { TopologyOptimizer, createTopologyOptimizer, } from './topology-optimizer.js';
export { SemanticRouter, createSemanticRouter, DEFAULT_SEMANTIC_CONFIG, } from './semantic-router.js';
// Utility class exports (extracted modules)
export { RateLimiter, MetricsCollector, HealthChecker, CircuitBreaker, CircuitBreakerOpenError, withRetry, createRetryState, calculateBackoffDelay, sleep, withTimeout, } from './utils/index.js';
// Type exports
export { 
// MCP param limits
MCP_PARAM_LIMITS, 
// Version & Security
MINIMUM_CLAUDE_CODE_VERSION, SECURITY_LIMITS, DEFAULT_PLUGIN_CONFIG, 
// Rate limiting
RATE_LIMIT_DEFAULTS, DEFAULT_RATE_LIMIT_CONFIG, 
// Health checks
HEALTH_CHECK_DEFAULTS, DEFAULT_HEALTH_CHECK_CONFIG, 
// Retry configuration
RETRY_DEFAULTS, DEFAULT_RETRY_CONFIG, 
// Circuit breaker
DEFAULT_CIRCUIT_BREAKER_CONFIG, 
// Enums
TeammateErrorCode, } from './types.js';
// Default export
import { createTeammateBridge } from './teammate-bridge.js';
export default createTeammateBridge;
//# sourceMappingURL=index.js.map