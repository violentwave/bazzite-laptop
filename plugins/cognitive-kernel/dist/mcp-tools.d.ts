/**
 * Cognitive Kernel MCP Tools
 *
 * 5 MCP tools for cognitive augmentation:
 * - cognition/working-memory: Working memory slot management
 * - cognition/attention-control: Cognitive attention control
 * - cognition/meta-monitor: Meta-cognitive monitoring
 * - cognition/scaffold: Cognitive scaffolding
 * - cognition/cognitive-load: Cognitive load management
 */
import type { MCPTool, MCPToolResult, ToolContext } from './types.js';
export declare const workingMemoryTool: MCPTool;
export declare const attentionControlTool: MCPTool;
export declare const metaMonitorTool: MCPTool;
export declare const scaffoldTool: MCPTool;
export declare const cognitiveLoadTool: MCPTool;
export declare const cognitiveKernelTools: MCPTool[];
export declare const toolHandlers: Map<string, (input: Record<string, unknown>, context?: ToolContext) => Promise<MCPToolResult>>;
export declare function getTool(name: string): MCPTool | undefined;
export declare function getToolNames(): string[];
export default cognitiveKernelTools;
//# sourceMappingURL=mcp-tools.d.ts.map