/**
 * HNSW Bridge
 *
 * Bridge to micro-hnsw-wasm for ultra-fast vector similarity search.
 * Achieves 150x-12,500x faster search compared to brute-force.
 */
import type { WasmBridge, WasmModuleStatus, HnswConfig, SearchResult } from '../types.js';
/**
 * HNSW WASM module interface
 */
interface HnswModule {
    create(config: HnswConfig): HnswIndex;
}
/**
 * HNSW index interface
 */
interface HnswIndex {
    add(id: string, vector: Float32Array, metadata?: Record<string, unknown>): void;
    search(query: Float32Array, k: number): SearchResult[];
    remove(id: string): boolean;
    size(): number;
    save(): Uint8Array;
    load(data: Uint8Array): void;
}
/**
 * HNSW Bridge implementation
 */
export declare class HnswBridge implements WasmBridge<HnswModule> {
    readonly name = "micro-hnsw-wasm";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private _index;
    private config;
    constructor(config?: Partial<HnswConfig>);
    get status(): WasmModuleStatus;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    getModule(): HnswModule | null;
    /**
     * Get the HNSW index
     */
    getIndex(): HnswIndex | null;
    /**
     * Add a vector to the index
     */
    add(id: string, vector: Float32Array, metadata?: Record<string, unknown>): void;
    /**
     * Search for similar vectors
     */
    search(query: Float32Array, k: number): SearchResult[];
    /**
     * Remove a vector from the index
     */
    remove(id: string): boolean;
    /**
     * Get index size
     */
    size(): number;
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new HNSW bridge
 */
export declare function createHnswBridge(config?: Partial<HnswConfig>): HnswBridge;
export {};
//# sourceMappingURL=hnsw.d.ts.map