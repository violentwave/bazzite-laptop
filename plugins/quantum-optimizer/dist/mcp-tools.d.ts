/**
 * Quantum Optimizer MCP Tools
 *
 * MCP tool definitions for quantum-inspired optimization including:
 * - quantum/annealing-solve: Simulated quantum annealing
 * - quantum/qaoa-optimize: QAOA circuit optimization
 * - quantum/grover-search: Grover-inspired search
 * - quantum/dependency-resolve: Package dependency resolution
 * - quantum/schedule-optimize: Task scheduling optimization
 */
import type { MCPTool, MCPToolResult, ToolContext } from './types.js';
export declare const annealingSolveTool: MCPTool;
export declare const qaoaOptimizeTool: MCPTool;
export declare const groverSearchTool: MCPTool;
export declare const dependencyResolveTool: MCPTool;
export declare const scheduleOptimizeTool: MCPTool;
/**
 * All Quantum Optimizer MCP Tools
 */
export declare const quantumOptimizerTools: MCPTool[];
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
export default quantumOptimizerTools;
//# sourceMappingURL=mcp-tools.d.ts.map