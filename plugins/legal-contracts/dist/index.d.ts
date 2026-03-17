/**
 * Legal Contracts Plugin for Claude Flow V3
 *
 * A comprehensive legal contract analysis plugin combining hyperbolic embeddings
 * for legal ontology navigation with fast vector search for clause similarity.
 *
 * Features:
 * - Clause extraction and classification
 * - Risk assessment with severity scoring
 * - Contract comparison with attention-based alignment
 * - Obligation tracking with DAG analysis
 * - Playbook matching for negotiation support
 *
 * Based on ADR-034: Legal Contract Analysis Plugin
 *
 * @module @claude-flow/plugin-legal-contracts
 */
export * from './types.js';
export { AttentionBridge, createAttentionBridge } from './bridges/attention-bridge.js';
export { DAGBridge, createDAGBridge } from './bridges/dag-bridge.js';
export { clauseExtractTool, riskAssessTool, contractCompareTool, obligationTrackTool, playbookMatchTool, legalContractsTools, toolHandlers, createToolContext, } from './mcp-tools.js';
export type { MCPTool, ToolContext, MCPToolResult } from './mcp-tools.js';
import type { LegalContractsConfig, IAttentionBridge, IDAGBridge } from './types.js';
/**
 * Plugin metadata
 */
export declare const pluginMetadata: {
    name: string;
    version: string;
    description: string;
    author: string;
    category: string;
    keywords: string[];
    homepage: string;
    repository: string;
};
/**
 * Plugin state
 */
export type PluginState = 'uninitialized' | 'initializing' | 'ready' | 'error' | 'shutdown';
/**
 * Legal Contracts Plugin Class
 */
export declare class LegalContractsPlugin {
    private state;
    private config;
    private attentionBridge;
    private dagBridge;
    constructor(config?: Partial<LegalContractsConfig>);
    /**
     * Get plugin metadata
     */
    getMetadata(): {
        name: string;
        version: string;
        description: string;
        author: string;
        category: string;
        keywords: string[];
        homepage: string;
        repository: string;
    };
    /**
     * Get current state
     */
    getState(): PluginState;
    /**
     * Initialize the plugin
     */
    initialize(): Promise<void>;
    /**
     * Shutdown the plugin
     */
    shutdown(): Promise<void>;
    /**
     * Get MCP tools provided by this plugin
     */
    getMCPTools(): import("./mcp-tools.js").MCPTool<unknown, unknown>[];
    /**
     * Get tool context for execution
     */
    getToolContext(): {
        get: <T>(key: string) => T | undefined;
        set: <T>(key: string, value: T) => void;
        bridges: {
            attention: IAttentionBridge;
            dag: IDAGBridge;
        };
    };
    /**
     * Get configuration
     */
    getConfig(): LegalContractsConfig;
    /**
     * Update configuration
     */
    updateConfig(config: Partial<LegalContractsConfig>): void;
}
/**
 * Create plugin instance
 */
export declare function createPlugin(config?: Partial<LegalContractsConfig>): LegalContractsPlugin;
/**
 * Default export
 */
export default LegalContractsPlugin;
//# sourceMappingURL=index.d.ts.map