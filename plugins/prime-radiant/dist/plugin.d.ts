/**
 * Prime Radiant Plugin - Main Plugin Class
 *
 * PrimeRadiantPlugin class implementing the IPlugin interface:
 * - register(): Register with claude-flow plugin system
 * - initialize(): Load WASM bundle, set up engines
 * - shutdown(): Cleanup WASM resources
 *
 * Integrates the 92KB WASM bundle for mathematical AI interpretability.
 *
 * @module prime-radiant/plugin
 * @version 0.1.3
 */
import type { IPlugin, IPrimeRadiantBridge, ICoherenceGate, PluginContext, PluginMCPTool, PluginHook, IResultCache } from './interfaces.js';
import type { PrimeRadiantConfig } from './types.js';
/**
 * Prime Radiant Plugin for Claude Flow V3
 *
 * Provides mathematical AI interpretability capabilities:
 * - Sheaf Laplacian coherence detection
 * - Spectral stability analysis
 * - Do-calculus causal inference
 * - Quantum topology computation
 * - Category theory morphisms
 * - Homotopy Type Theory proofs
 */
export declare class PrimeRadiantPlugin implements IPlugin {
    readonly name = "prime-radiant";
    readonly version = "0.1.3";
    readonly description = "Mathematical AI interpretability with sheaf cohomology, spectral analysis, and causal inference";
    private bridge;
    private coherenceGate;
    private cache;
    private config;
    private context;
    constructor(config?: Partial<PrimeRadiantConfig>);
    /**
     * Register the plugin with claude-flow
     */
    register(context: PluginContext): Promise<void>;
    /**
     * Initialize the plugin (load WASM, set up engines)
     */
    initialize(context: PluginContext): Promise<{
        success: boolean;
        error?: string;
    }>;
    /**
     * Shutdown the plugin (cleanup WASM resources)
     */
    shutdown(_context: PluginContext): Promise<{
        success: boolean;
        error?: string;
    }>;
    /**
     * Get plugin capabilities
     */
    getCapabilities(): string[];
    /**
     * Get plugin MCP tools
     */
    getMCPTools(): PluginMCPTool[];
    /**
     * Get plugin hooks
     */
    getHooks(): PluginHook[];
    private createCoherenceCheckTool;
    private createSpectralAnalyzeTool;
    private createCausalInferTool;
    private createConsensusVerifyTool;
    private createQuantumTopologyTool;
    private createMemoryGateTool;
    private createPreMemoryStoreHook;
    private createPreConsensusHook;
    private createPostSwarmTaskHook;
    private createPreRagRetrievalHook;
    private cosineSimilarity;
    /**
     * Get the WASM bridge instance
     */
    getBridge(): IPrimeRadiantBridge;
    /**
     * Get the coherence gate instance
     */
    getCoherenceGate(): ICoherenceGate;
    /**
     * Get the result cache instance
     */
    getCache(): IResultCache<unknown>;
    /**
     * Get the current configuration
     */
    getConfig(): PrimeRadiantConfig;
    /**
     * Update configuration
     */
    updateConfig(config: Partial<PrimeRadiantConfig>): void;
}
//# sourceMappingURL=plugin.d.ts.map