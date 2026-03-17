/**
 * Performance Optimizer MCP Tools
 *
 * 5 MCP tools for AI-powered performance optimization:
 * 1. perf/bottleneck-detect - Detect performance bottlenecks
 * 2. perf/memory-analyze - Analyze memory usage and leaks
 * 3. perf/query-optimize - Detect and optimize query patterns
 * 4. perf/bundle-optimize - Optimize JavaScript bundles
 * 5. perf/config-optimize - Optimize configuration parameters
 */
import type { MCPTool } from './types.js';
export declare const bottleneckDetectTool: MCPTool;
export declare const memoryAnalyzeTool: MCPTool;
export declare const queryOptimizeTool: MCPTool;
export declare const bundleOptimizeTool: MCPTool;
export declare const configOptimizeTool: MCPTool;
export declare const perfOptimizerTools: MCPTool[];
/**
 * Get a tool by name
 */
export declare function getTool(name: string): MCPTool | undefined;
/**
 * Get all tool names
 */
export declare function getToolNames(): string[];
//# sourceMappingURL=mcp-tools.d.ts.map