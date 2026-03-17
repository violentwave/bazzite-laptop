/**
 * Graph Neural Network Bridge
 *
 * Bridge to ruvector-gnn-wasm for graph-based learning and inference.
 */
import type { WasmBridge, WasmModuleStatus, GnnConfig } from '../types.js';
/**
 * Graph structure
 */
export interface Graph {
    nodes: Float32Array[];
    edges: Array<[number, number]>;
    edgeWeights?: Float32Array;
}
/**
 * GNN inference result
 */
export interface GnnResult {
    nodeEmbeddings: Float32Array[];
    graphEmbedding: Float32Array;
    predictions?: Float32Array;
}
/**
 * GNN WASM module interface
 */
interface GnnModule {
    forward(graph: Graph, config: GnnConfig): GnnResult;
    nodeClassification(graph: Graph, config: GnnConfig): Float32Array;
    linkPrediction(graph: Graph, source: number, targets: number[], config: GnnConfig): Float32Array;
    graphClassification(graphs: Graph[], config: GnnConfig): Float32Array;
}
/**
 * GNN Bridge implementation
 */
export declare class GnnBridge implements WasmBridge<GnnModule> {
    readonly name = "ruvector-gnn-wasm";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private config;
    constructor(config?: Partial<GnnConfig>);
    get status(): WasmModuleStatus;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    getModule(): GnnModule | null;
    /**
     * Forward pass through GNN
     */
    forward(graph: Graph, config?: Partial<GnnConfig>): GnnResult;
    /**
     * Node classification
     */
    nodeClassification(graph: Graph, config?: Partial<GnnConfig>): Float32Array;
    /**
     * Link prediction
     */
    linkPrediction(graph: Graph, source: number, targets: number[], config?: Partial<GnnConfig>): Float32Array;
    /**
     * Graph classification
     */
    graphClassification(graphs: Graph[], config?: Partial<GnnConfig>): Float32Array;
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new GNN bridge
 */
export declare function createGnnBridge(config?: Partial<GnnConfig>): GnnBridge;
export {};
//# sourceMappingURL=gnn.d.ts.map