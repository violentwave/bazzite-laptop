/**
 * GNN Bridge - Graph Neural Network Operations
 *
 * Bridge to @ruvector/gnn-wasm for graph-based reasoning,
 * node classification, link prediction, and graph embeddings.
 */
import type { Concept, EntailmentGraph } from '../types.js';
/**
 * WASM module status
 */
export type WasmModuleStatus = 'unloaded' | 'loading' | 'ready' | 'error';
/**
 * GNN configuration
 */
export interface GnnConfig {
    /** Input feature dimension */
    readonly inputDim: number;
    /** Hidden layer dimension */
    readonly hiddenDim: number;
    /** Output dimension */
    readonly outputDim: number;
    /** Number of GNN layers */
    readonly numLayers: number;
    /** Aggregation method */
    readonly aggregation: 'mean' | 'sum' | 'max' | 'attention';
    /** Dropout rate */
    readonly dropout: number;
}
/**
 * Graph structure for GNN
 */
export interface Graph {
    /** Node features (each node has a feature vector) */
    readonly nodeFeatures: Float32Array[];
    /** Edges as [source, target] pairs */
    readonly edges: Array<[number, number]>;
    /** Edge weights */
    readonly edgeWeights?: Float32Array;
    /** Node labels (for supervised learning) */
    readonly labels?: Uint32Array;
}
/**
 * GNN inference result
 */
export interface GnnResult {
    /** Node embeddings */
    readonly nodeEmbeddings: Float32Array[];
    /** Graph-level embedding */
    readonly graphEmbedding: Float32Array;
    /** Node predictions (if applicable) */
    readonly predictions?: Float32Array[];
    /** Attention weights (if using attention aggregation) */
    readonly attentionWeights?: Map<string, Float32Array>;
}
/**
 * Entailment prediction result
 */
export interface EntailmentPrediction {
    /** Premise concept ID */
    readonly premise: string;
    /** Hypothesis concept ID */
    readonly hypothesis: string;
    /** Probability of entailment */
    readonly entailmentProb: number;
    /** Probability of contradiction */
    readonly contradictionProb: number;
    /** Probability of neutral */
    readonly neutralProb: number;
    /** Final relation type */
    readonly relation: 'entails' | 'contradicts' | 'neutral';
}
/**
 * Graph Neural Network Bridge
 */
export declare class GnnBridge {
    readonly name = "hyperbolic-gnn-bridge";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private _config;
    constructor(config?: Partial<GnnConfig>);
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
     * Forward pass through GNN
     */
    forward(graph: Graph, config?: Partial<GnnConfig>): GnnResult;
    /**
     * Predict links between nodes
     */
    predictLinks(graph: Graph, sourceNodes: number[], targetNodes: number[]): Float32Array;
    /**
     * Build entailment graph from concepts using GNN
     */
    buildEntailmentGraph(concepts: ReadonlyArray<Concept>, threshold?: number): Promise<EntailmentGraph>;
    /**
     * Predict entailment between two concepts
     */
    predictEntailment(premiseEmb: Float32Array, hypothesisEmb: Float32Array): EntailmentPrediction;
    /**
     * Compute transitive closure of entailment graph
     */
    computeTransitiveClosure(graph: EntailmentGraph): EntailmentGraph;
    /**
     * Prune entailment graph using transitive reduction
     */
    transitiveReduction(graph: EntailmentGraph): EntailmentGraph;
    private computeEntailmentScore;
    private computeMaxDepth;
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new GnnBridge instance
 */
export declare function createGnnBridge(config?: Partial<GnnConfig>): GnnBridge;
//# sourceMappingURL=gnn-bridge.d.ts.map