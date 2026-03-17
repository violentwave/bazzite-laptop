/**
 * Hyperbolic Bridge - Poincare Ball and Lorentz Model Operations
 *
 * Bridge to @ruvector/hyperbolic-hnsw-wasm for hyperbolic geometry operations
 * including embeddings, distance computation, and hierarchical search.
 */
import type { HyperbolicPoint, Hierarchy, EmbeddedHierarchy, SearchResult, EmbedHierarchyInput } from '../types.js';
/**
 * WASM module status
 */
export type WasmModuleStatus = 'unloaded' | 'loading' | 'ready' | 'error';
/**
 * Hyperbolic Embeddings Bridge
 */
export declare class HyperbolicBridge {
    readonly name = "hyperbolic-reasoning-bridge";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private _indices;
    get status(): WasmModuleStatus;
    get initialized(): boolean;
    /**
     * Initialize the WASM module
     */
    initialize(): Promise<void>;
    /**
     * Dispose of resources
     */
    dispose(): Promise<void>;
    /**
     * Embed a hierarchy into hyperbolic space
     */
    embedHierarchy(hierarchy: Hierarchy, config?: Partial<EmbedHierarchyInput['parameters']>): Promise<EmbeddedHierarchy>;
    /**
     * Compute hyperbolic distance between two points
     */
    distance(a: HyperbolicPoint, b: HyperbolicPoint): number;
    /**
     * Check if one point is ancestor of another (closer to origin)
     */
    isAncestor(parent: HyperbolicPoint, child: HyperbolicPoint, threshold?: number): boolean;
    /**
     * Get hierarchy depth from hyperbolic point
     */
    hierarchyDepth(point: HyperbolicPoint): number;
    /**
     * Create or get an index
     */
    createIndex(id: string, dimension: number, curvature: number): void;
    /**
     * Add point to index
     */
    addToIndex(indexId: string, nodeId: string, point: HyperbolicPoint): void;
    /**
     * Search in hyperbolic space
     */
    search(query: HyperbolicPoint, indexId: string, k: number, mode?: 'nearest' | 'subtree' | 'ancestors' | 'siblings' | 'cone'): Promise<SearchResult>;
    private validateHierarchy;
    private computeDistanceGradient;
    private estimateCurvatureGradient;
    private computeEmbeddingMetrics;
    private inCone;
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new HyperbolicBridge instance
 */
export declare function createHyperbolicBridge(): HyperbolicBridge;
//# sourceMappingURL=hyperbolic-bridge.d.ts.map