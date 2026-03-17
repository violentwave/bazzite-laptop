/**
 * Hyperbolic Reasoning MCP Tools
 *
 * MCP tool definitions for hyperbolic geometry operations including:
 * - hyperbolic/embed-hierarchy: Embed hierarchies in Poincare ball
 * - hyperbolic/taxonomic-reason: Taxonomic reasoning and queries
 * - hyperbolic/semantic-search: Hierarchically-aware search
 * - hyperbolic/hierarchy-compare: Compare hierarchical structures
 * - hyperbolic/entailment-graph: Build and query entailment graphs
 */
import type { MCPTool, MCPToolResult, ToolContext } from './types.js';
export declare const embedHierarchyTool: MCPTool;
export declare const taxonomicReasonTool: MCPTool;
export declare const semanticSearchTool: MCPTool;
export declare const hierarchyCompareTool: MCPTool;
export declare const entailmentGraphTool: MCPTool;
/**
 * All Hyperbolic Reasoning MCP Tools
 */
export declare const hyperbolicReasoningTools: MCPTool[];
/**
 * Tool name to handler map
 */
export declare const toolHandlers: Map<string, (input: Record<string, unknown>, context?: ToolContext) => Promise<MCPToolResult>>;
/**
 * Get a tool by name
 */
export declare function getTool(name: string): MCPTool | undefined;
/**
 * Get all tool names
 */
export declare function getToolNames(): string[];
export default hyperbolicReasoningTools;
//# sourceMappingURL=mcp-tools.d.ts.map