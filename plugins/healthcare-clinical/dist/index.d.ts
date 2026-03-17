/**
 * Healthcare Clinical Decision Support Plugin
 *
 * A HIPAA-compliant clinical decision support plugin that combines
 * ultra-fast vector search for medical literature retrieval with
 * graph neural networks for patient pathway analysis.
 *
 * Features:
 * - Patient similarity search using HNSW (150x faster)
 * - Drug interaction detection using GNN
 * - Clinical pathway recommendations
 * - Medical literature semantic search
 * - Ontology navigation (ICD-10, SNOMED-CT, LOINC, RxNorm)
 *
 * HIPAA Compliance:
 * - All patient data processed locally in WASM sandbox
 * - No PHI transmitted externally
 * - Complete audit logging
 * - Role-based access control
 *
 * @packageDocumentation
 * @module @claude-flow/plugin-healthcare-clinical
 */
export * from './types.js';
export { healthcareTools, toolHandlers, getTool, getToolNames, patientSimilarityTool, drugInteractionsTool, clinicalPathwaysTool, literatureSearchTool, ontologyNavigateTool, } from './mcp-tools.js';
export { HealthcareHNSWBridge, createHNSWBridge, PatientEmbeddingGenerator, } from './bridges/hnsw-bridge.js';
export { HealthcareGNNBridge, createGNNBridge, } from './bridges/gnn-bridge.js';
import type { HealthcareConfig, HealthcareBridge, Logger } from './types.js';
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
 * Healthcare Clinical Plugin class
 */
export declare class HealthcareClinicalPlugin {
    private config;
    private logger;
    private bridge;
    private initialized;
    constructor(config?: Partial<HealthcareConfig>, logger?: Logger);
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
    getBridge(): HealthcareBridge;
    /**
     * Get plugin configuration
     */
    getConfig(): HealthcareConfig;
    /**
     * Cleanup resources
     */
    destroy(): Promise<void>;
}
/**
 * Create a new Healthcare Clinical Plugin instance
 */
export declare function createHealthcarePlugin(config?: Partial<HealthcareConfig>, logger?: Logger): HealthcareClinicalPlugin;
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
    createPlugin: typeof createHealthcarePlugin;
    HealthcareClinicalPlugin: typeof HealthcareClinicalPlugin;
};
export default _default;
//# sourceMappingURL=index.d.ts.map