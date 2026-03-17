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
// Export all types
export * from './types.js';
// Export MCP tools
export { financialTools, toolHandlers, getTool, getToolNames, portfolioRiskTool, anomalyDetectTool, marketRegimeTool, complianceCheckTool, stressTestTool, } from './mcp-tools.js';
// Export bridges
export { FinancialEconomyBridge, createEconomyBridge, PortfolioRiskCalculator, } from './bridges/economy-bridge.js';
export { FinancialSparseBridge, createSparseBridge, AnomalyDetector, MarketRegimeClassifier, } from './bridges/sparse-bridge.js';
// Import for plugin definition
import { financialTools } from './mcp-tools.js';
import { FinancialEconomyBridge } from './bridges/economy-bridge.js';
import { FinancialSparseBridge } from './bridges/sparse-bridge.js';
import { DEFAULT_FINANCIAL_CONFIG } from './types.js';
/**
 * Plugin metadata
 */
export const pluginMetadata = {
    name: '@claude-flow/plugin-financial-risk',
    version: '3.0.0-alpha.1',
    description: 'High-performance financial risk analysis with portfolio risk, anomaly detection, and compliance checking',
    author: 'rUv',
    license: 'MIT',
    category: 'finance',
    tags: ['finance', 'risk', 'portfolio', 'var', 'anomaly-detection', 'compliance', 'basel3', 'mifid2'],
    wasmPackages: [
        'micro-hnsw-wasm',
        'ruvector-sparse-inference-wasm',
        'ruvector-gnn-wasm',
        'ruvector-economy-wasm',
        'ruvector-learning-wasm',
    ],
};
/**
 * Financial Risk Plugin class
 */
export class FinancialRiskPlugin {
    config;
    logger;
    bridge;
    initialized = false;
    constructor(config, logger) {
        this.config = { ...DEFAULT_FINANCIAL_CONFIG, ...config };
        this.logger = logger ?? {
            debug: (msg, meta) => console.debug(`[financial-plugin] ${msg}`, meta),
            info: (msg, meta) => console.info(`[financial-plugin] ${msg}`, meta),
            warn: (msg, meta) => console.warn(`[financial-plugin] ${msg}`, meta),
            error: (msg, meta) => console.error(`[financial-plugin] ${msg}`, meta),
        };
        this.bridge = {
            economy: undefined,
            sparse: undefined,
            initialized: false,
        };
    }
    /**
     * Initialize the plugin
     */
    async initialize() {
        if (this.initialized)
            return;
        this.logger.info('Initializing Financial Risk Plugin');
        try {
            // Initialize Economy bridge
            const economyBridge = new FinancialEconomyBridge({ randomSeed: this.config.risk.defaultConfidenceLevel }, this.logger);
            await economyBridge.initialize();
            this.bridge.economy = economyBridge;
            // Initialize Sparse bridge
            const sparseBridge = new FinancialSparseBridge({ sparsityThreshold: this.config.anomaly.defaultThreshold }, this.logger);
            await sparseBridge.initialize();
            this.bridge.sparse = sparseBridge;
            this.bridge.initialized = true;
            this.initialized = true;
            this.logger.info('Financial Risk Plugin initialized successfully', {
                economyReady: economyBridge.initialized,
                sparseReady: sparseBridge.initialized,
            });
        }
        catch (error) {
            this.logger.error('Failed to initialize Financial Risk Plugin', {
                error: error instanceof Error ? error.message : String(error),
            });
            throw error;
        }
    }
    /**
     * Get all MCP tools
     */
    getTools() {
        return financialTools;
    }
    /**
     * Get the bridge for tool execution
     */
    getBridge() {
        return this.bridge;
    }
    /**
     * Get plugin configuration
     */
    getConfig() {
        return this.config;
    }
    /**
     * Cleanup resources
     */
    async destroy() {
        if (this.bridge.economy) {
            this.bridge.economy.destroy();
        }
        if (this.bridge.sparse) {
            this.bridge.sparse.destroy();
        }
        this.bridge.initialized = false;
        this.initialized = false;
        this.logger.info('Financial Risk Plugin destroyed');
    }
}
/**
 * Create a new Financial Risk Plugin instance
 */
export function createFinancialPlugin(config, logger) {
    return new FinancialRiskPlugin(config, logger);
}
/**
 * Default export for plugin loader
 */
export default {
    metadata: pluginMetadata,
    tools: financialTools,
    createPlugin: createFinancialPlugin,
    FinancialRiskPlugin,
};
//# sourceMappingURL=index.js.map