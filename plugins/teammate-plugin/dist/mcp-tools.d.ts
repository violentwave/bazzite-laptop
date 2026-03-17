/**
 * MCP Tools for TeammateTool Integration
 *
 * Exposes 21 MCP tools for multi-agent orchestration via Claude Code:
 * - 16 core TeammateTool integration tools
 * - 5 BMSSP optimization tools (10-15x faster with WASM)
 *
 * @module @claude-flow/teammate-plugin/mcp
 * @version 1.0.0-alpha.1
 */
import type { TeammateBridge } from './teammate-bridge.js';
export interface MCPTool {
    name: string;
    description: string;
    inputSchema: {
        type: 'object';
        properties: Record<string, unknown>;
        required?: string[];
    };
}
export declare const TEAMMATE_MCP_TOOLS: MCPTool[];
export type ToolResult = {
    success: boolean;
    data?: unknown;
    error?: string;
};
export declare function handleMCPTool(bridge: TeammateBridge, toolName: string, params: Record<string, unknown>): Promise<ToolResult>;
export declare function listTeammateTools(): MCPTool[];
export declare function hasTeammateTool(name: string): boolean;
declare const _default: {
    tools: MCPTool[];
    handleTool: typeof handleMCPTool;
    listTools: typeof listTeammateTools;
    hasTool: typeof hasTeammateTool;
};
export default _default;
//# sourceMappingURL=mcp-tools.d.ts.map