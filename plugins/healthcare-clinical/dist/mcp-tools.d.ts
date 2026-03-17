/**
 * Healthcare Clinical MCP Tools
 *
 * HIPAA-compliant clinical decision support tools including:
 * - patient-similarity: Find similar patient cases
 * - drug-interactions: Analyze drug-drug and drug-condition interactions
 * - clinical-pathways: Recommend evidence-based treatment pathways
 * - literature-search: Semantic search across medical literature
 * - ontology-navigate: Navigate medical ontology hierarchies
 */
import type { MCPTool, MCPToolResult, ToolContext } from './types.js';
export declare const patientSimilarityTool: MCPTool;
export declare const drugInteractionsTool: MCPTool;
export declare const clinicalPathwaysTool: MCPTool;
export declare const literatureSearchTool: MCPTool;
export declare const ontologyNavigateTool: MCPTool;
export declare const healthcareTools: MCPTool[];
export declare const toolHandlers: Map<string, (input: Record<string, unknown>, context?: ToolContext) => Promise<MCPToolResult>>;
export declare function getTool(name: string): MCPTool | undefined;
export declare function getToolNames(): string[];
export default healthcareTools;
//# sourceMappingURL=mcp-tools.d.ts.map