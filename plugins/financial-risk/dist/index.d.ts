/**
 * Financial Risk Analysis Plugin
 *
 * A high-performance financial risk analysis plugin combining
 * sparse inference for efficient market signal processing with
 * graph neural networks for transaction network analysis.
 *
 * Features:
 * - Portfolio risk analysis (VaR, CVaR, Sharpe, Sortino)
 * - Transaction anomaly detection using GNN
 * - Market regime classification
 * - Regulatory compliance checking (Basel III, MiFID II, AML)
 * - Stress testing with historical and hypothetical scenarios
 *
 * Compliance:
 * - SOX and MiFID II compliant audit logging
 * - Deterministic execution for reproducibility
 * - Role-based access control
 * - Rate limiting for fair resource allocation
 *
 * @packageDocumentation
 * @module @claude-flow/plugin-financial-risk
 */
export * from './types.js';
export { financialTools, toolHandlers, getTool, getToolNames, portfolioRiskTool, anomalyDetectTool, marketRegimeTool, complianceCheckTool, stressTestTool, } from './mcp-tools.js';
export { FinancialEconomyBridge, createEconomyBridge, PortfolioRiskCalculator, } from './bridges/economy-bridge.js';
export { FinancialSparseBridge, createSparseBridge, AnomalyDetector, MarketRegimeClassifier, } from './bridges/sparse-bridge.js';
import type { FinancialConfig, FinancialBridge, Logger } from './types.js';
/**
 * Plugin metadata
 */
export declare const pluginMetadata: {
    name: string;
    version: string;
    description: string;
    author: string;
    license: string;
    category: string;
    tags: string[];
    wasmPackages: string[];
};
/**
 * Financial Risk Plugin class
 */
export declare class FinancialRiskPlugin {
    private config;
    private logger;
    private bridge;
    private initialized;
    constructor(config?: Partial<FinancialConfig>, logger?: Logger);
    /**
     * Initialize the plugin
     */
    initialize(): Promise<void>;
    /**
     * Get all MCP tools
     */
    getTools(): import("./types.js").MCPTool[];
    /**
     * Get the bridge for tool execution
     */
    getBridge(): FinancialBridge;
    /**
     * Get plugin configuration
     */
    getConfig(): FinancialConfig;
    /**
     * Cleanup resources
     */
    destroy(): Promise<void>;
}
/**
 * Create a new Financial Risk Plugin instance
 */
export declare function createFinancialPlugin(config?: Partial<FinancialConfig>, logger?: Logger): FinancialRiskPlugin;
/**
 * Default export for plugin loader
 */
declare const _default: {
    metadata: {
        name: string;
        version: string;
        description: string;
        author: string;
        license: string;
        category: string;
        tags: string[];
        wasmPackages: string[];
    };
    tools: import("./types.js").MCPTool[];
    createPlugin: typeof createFinancialPlugin;
    FinancialRiskPlugin: typeof FinancialRiskPlugin;
};
export default _default;
//# sourceMappingURL=index.d.ts.map