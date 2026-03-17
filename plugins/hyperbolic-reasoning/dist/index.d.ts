/**
 * @claude-flow/plugin-hyperbolic-reasoning
 *
 * Hyperbolic reasoning plugin for Claude Flow V3.
 *
 * Provides MCP tools for:
 * - Hierarchy embedding in Poincare ball
 * - Taxonomic reasoning (IS-A, subsumption, LCA)
 * - Hierarchically-aware semantic search
 * - Hierarchy comparison and alignment
 * - Entailment graph construction
 *
 * @module @claude-flow/plugin-hyperbolic-reasoning
 * @version 3.0.0-alpha.1
 */
export type { HyperbolicPoint, HyperbolicModel, MobiusTransform, HierarchyNode, HierarchyEdge, Hierarchy, EmbeddedHierarchy, TaxonomicQueryType, TaxonomicQuery, InferenceConfig, TaxonomicResult, SearchMode, SearchConstraints, SearchResultItem, SearchResult, AlignmentMethod, ComparisonMetric, NodeAlignment, ComparisonResult, Concept, EntailmentRelation, EntailmentAction, PruneStrategy, EntailmentGraph, EntailmentQueryResult, MCPTool, MCPToolResult, MCPToolInputSchema, ToolContext, Logger, HyperbolicReasoningConfig, HyperbolicReasoningBridge, } from './types.js';
export { HierarchyNodeSchema, HierarchyEdgeSchema, HierarchySchema, EmbedHierarchyInputSchema, TaxonomicReasonInputSchema, SemanticSearchInputSchema, HierarchyCompareInputSchema, ConceptSchema, EntailmentGraphInputSchema, successResult, errorResult, POINCARE_BALL_EPS, MAX_NORM, RESOURCE_LIMITS, } from './types.js';
export { clipToBall, poincareDistance, mobiusAdd, expMap, logMap, } from './types.js';
export { HyperbolicBridge, createHyperbolicBridge } from './bridges/hyperbolic-bridge.js';
export { GnnBridge, createGnnBridge } from './bridges/gnn-bridge.js';
export type { WasmModuleStatus } from './bridges/hyperbolic-bridge.js';
export type { GnnConfig, Graph, GnnResult, EntailmentPrediction, } from './bridges/gnn-bridge.js';
export { hyperbolicReasoningTools, toolHandlers, getTool, getToolNames, embedHierarchyTool, taxonomicReasonTool, semanticSearchTool, hierarchyCompareTool, entailmentGraphTool, } from './mcp-tools.js';
export { default } from './mcp-tools.js';
/**
 * Plugin metadata
 */
export declare const pluginMetadata: {
    readonly name: "@claude-flow/plugin-hyperbolic-reasoning";
    readonly version: "3.0.0-alpha.1";
    readonly description: "Hyperbolic geometry for hierarchical reasoning";
    readonly category: "exotic";
    readonly author: "rUv";
    readonly license: "MIT";
    readonly repository: "https://github.com/ruvnet/claude-flow";
    readonly tools: readonly ["hyperbolic_embed_hierarchy", "hyperbolic_taxonomic_reason", "hyperbolic_semantic_search", "hyperbolic_hierarchy_compare", "hyperbolic_entailment_graph"];
    readonly bridges: readonly ["hyperbolic-bridge", "gnn-bridge"];
    readonly wasmPackages: readonly ["@ruvector/hyperbolic-hnsw-wasm", "@ruvector/attention-wasm", "@ruvector/gnn-wasm", "@ruvector/sona"];
};
/**
 * Initialize the plugin
 */
export declare function initializePlugin(): Promise<void>;
/**
 * Plugin configuration validator
 */
export declare function validateConfig(config: unknown): config is HyperbolicReasoningConfig;
/**
 * Default plugin configuration
 */
export declare const defaultConfig: HyperbolicReasoningConfig;
import type { HyperbolicReasoningConfig } from './types.js';
//# sourceMappingURL=index.d.ts.map