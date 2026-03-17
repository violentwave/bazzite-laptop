/**
 * Legal Contracts Plugin - MCP Tools
 *
 * Implements 5 MCP tools for legal contract analysis:
 * 1. legal/clause-extract - Extract and classify clauses
 * 2. legal/risk-assess - Identify and score contractual risks
 * 3. legal/contract-compare - Compare contracts with attention-based alignment
 * 4. legal/obligation-track - Extract obligations with DAG analysis
 * 5. legal/playbook-match - Match clauses against negotiation playbook
 *
 * Based on ADR-034: Legal Contract Analysis Plugin
 *
 * @module v3/plugins/legal-contracts/mcp-tools
 */
import { z } from 'zod';
import type { ClauseExtractionResult, RiskAssessmentResult, ContractComparisonResult, ObligationTrackingResult, PlaybookMatchResult, IAttentionBridge, IDAGBridge } from './types.js';
import { ClauseExtractInputSchema, RiskAssessInputSchema, ContractCompareInputSchema, ObligationTrackInputSchema, PlaybookMatchInputSchema } from './types.js';
/**
 * MCP Tool definition
 */
export interface MCPTool<TInput = unknown, TOutput = unknown> {
    name: string;
    description: string;
    category: string;
    version: string;
    inputSchema: z.ZodType<TInput, z.ZodTypeDef, any>;
    handler: (input: TInput, context: ToolContext) => Promise<MCPToolResult<TOutput>>;
}
/**
 * Tool execution context
 */
export interface ToolContext {
    get<T>(key: string): T | undefined;
    set<T>(key: string, value: T): void;
    bridges: {
        attention: IAttentionBridge;
        dag: IDAGBridge;
    };
}
/**
 * MCP Tool result format
 */
export interface MCPToolResult<T = unknown> {
    content: Array<{
        type: 'text';
        text: string;
    }>;
    data?: T;
}
/**
 * MCP Tool: legal/clause-extract
 *
 * Extract and classify clauses from legal documents
 */
export declare const clauseExtractTool: MCPTool<z.infer<typeof ClauseExtractInputSchema>, ClauseExtractionResult>;
/**
 * MCP Tool: legal/risk-assess
 *
 * Assess contractual risks with severity scoring
 */
export declare const riskAssessTool: MCPTool<z.infer<typeof RiskAssessInputSchema>, RiskAssessmentResult>;
/**
 * MCP Tool: legal/contract-compare
 *
 * Compare two contracts with detailed diff and semantic alignment
 */
export declare const contractCompareTool: MCPTool<z.infer<typeof ContractCompareInputSchema>, ContractComparisonResult>;
/**
 * MCP Tool: legal/obligation-track
 *
 * Extract obligations, deadlines, and dependencies using DAG analysis
 */
export declare const obligationTrackTool: MCPTool<z.infer<typeof ObligationTrackInputSchema>, ObligationTrackingResult>;
/**
 * MCP Tool: legal/playbook-match
 *
 * Compare contract clauses against negotiation playbook
 */
export declare const playbookMatchTool: MCPTool<z.infer<typeof PlaybookMatchInputSchema>, PlaybookMatchResult>;
/**
 * All Legal Contracts MCP Tools
 */
export declare const legalContractsTools: MCPTool[];
/**
 * Tool name to handler map
 */
export declare const toolHandlers: Map<string, (input: unknown, context: ToolContext) => Promise<MCPToolResult<unknown>>>;
/**
 * Create tool context with bridges
 */
export declare function createToolContext(): ToolContext;
export default legalContractsTools;
//# sourceMappingURL=mcp-tools.d.ts.map