/**
 * Hyperbolic Embeddings Bridge
 *
 * Bridge to ruvector-hyperbolic-hnsw-wasm for hierarchical data representation
 * using Poincaré ball model, Lorentz model, or Klein model.
 */
import type { WasmBridge, WasmModuleStatus, HyperbolicConfig } from '../types.js';
/**
 * Hyperbolic point
 */
export interface HyperbolicPoint {
    coordinates: Float32Array;
    curvature: number;
}
/**
 * Hyperbolic WASM module interface
 */
interface HyperbolicModule {
    embed(vector: Float32Array, config: HyperbolicConfig): HyperbolicPoint;
    project(point: HyperbolicPoint): Float32Array;
    distance(a: HyperbolicPoint, b: HyperbolicPoint): number;
    similarity(a: HyperbolicPoint, b: HyperbolicPoint): number;
    midpoint(a: HyperbolicPoint, b: HyperbolicPoint): HyperbolicPoint;
    geodesic(a: HyperbolicPoint, b: HyperbolicPoint, steps: number): HyperbolicPoint[];
    isAncestor(parent: HyperbolicPoint, child: HyperbolicPoint, threshold: number): boolean;
    hierarchyDepth(point: HyperbolicPoint): number;
    addToIndex(id: string, point: HyperbolicPoint): void;
    search(query: HyperbolicPoint, k: number): Array<{
        id: string;
        distance: number;
    }>;
}
/**
 * Hyperbolic Embeddings Bridge implementation
 */
export declare class HyperbolicBridge implements WasmBridge<HyperbolicModule> {
    readonly name = "ruvector-hyperbolic-hnsw-wasm";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private config;
    constructor(config?: Partial<HyperbolicConfig>);
    get status(): WasmModuleStatus;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    getModule(): HyperbolicModule | null;
    /**
     * Embed a vector into hyperbolic space
     */
    embed(vector: Float32Array, config?: Partial<HyperbolicConfig>): HyperbolicPoint;
    /**
     * Project hyperbolic point to Euclidean space
     */
    project(point: HyperbolicPoint): Float32Array;
    /**
     * Compute hyperbolic distance
     */
    distance(a: HyperbolicPoint, b: HyperbolicPoint): number;
    /**
     * Compute hyperbolic similarity
     */
    similarity(a: HyperbolicPoint, b: HyperbolicPoint): number;
    /**
     * Check if one point is ancestor of another (hierarchy)
     */
    isAncestor(parent: HyperbolicPoint, child: HyperbolicPoint, threshold?: number): boolean;
    /**
     * Get hierarchy depth of a point
     */
    hierarchyDepth(point: HyperbolicPoint): number;
    /**
     * Add point to HNSW index
     */
    addToIndex(id: string, point: HyperbolicPoint): void;
    /**
     * Search in hyperbolic HNSW index
     */
    search(query: HyperbolicPoint, k: number): Array<{
        id: string;
        distance: number;
    }>;
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new hyperbolic bridge
 */
export declare function createHyperbolicBridge(config?: Partial<HyperbolicConfig>): HyperbolicBridge;
export {};
//# sourceMappingURL=hyperbolic.d.ts.map