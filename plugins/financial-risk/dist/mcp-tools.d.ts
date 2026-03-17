/**
 * Financial Risk MCP Tools
 *
 * High-performance financial risk analysis tools including:
 * - portfolio-risk: Calculate VaR, CVaR, Sharpe, and other risk metrics
 * - anomaly-detect: Detect anomalies in transactions using GNN
 * - market-regime: Classify current market regime using pattern matching
 * - compliance-check: Verify regulatory compliance (Basel III, MiFID II, etc.)
 * - stress-test: Run stress testing scenarios on portfolios
 */
import type { MCPTool, MCPToolResult, ToolContext } from './types.js';
export declare const portfolioRiskTool: MCPTool;
export declare const anomalyDetectTool: MCPTool;
export declare const marketRegimeTool: MCPTool;
export declare const complianceCheckTool: MCPTool;
export declare const stressTestTool: MCPTool;
export declare const financialTools: MCPTool[];
export declare const toolHandlers: Map<string, (input: Record<string, unknown>, context?: ToolContext) => Promise<MCPToolResult>>;
export declare function getTool(name: string): MCPTool | undefined;
export declare function getToolNames(): string[];
export default financialTools;
//# sourceMappingURL=mcp-tools.d.ts.map