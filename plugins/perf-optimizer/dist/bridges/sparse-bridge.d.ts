/**
 * Sparse Inference Bridge for Performance Optimizer
 *
 * Provides efficient trace analysis using sparse inference techniques
 * from ruvector-sparse-inference-wasm for processing large performance traces.
 */
import type { SparseBridgeInterface, TraceSpan } from '../types.js';
/**
 * Sparse encoding configuration
 */
interface SparseEncodingConfig {
    maxDimensions: number;
    sparsityRatio: number;
    hashBuckets: number;
    featureExtraction: 'auto' | 'manual' | 'learned';
}
/**
 * Sparse Inference Bridge Implementation
 *
 * Provides efficient trace analysis capabilities:
 * - Sparse encoding of trace spans for memory efficiency
 * - Anomaly detection using sparse representations
 * - Critical path analysis using dependency graphs
 */
export declare class PerfSparseBridge implements SparseBridgeInterface {
    readonly name = "perf-optimizer-sparse";
    readonly version = "0.1.0";
    private status;
    private config;
    private featureHashes;
    private encodingCache;
    constructor(config?: Partial<SparseEncodingConfig>);
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    /**
     * Encode traces into sparse representation
     *
     * Uses feature hashing and sparse encoding to efficiently
     * represent trace spans for downstream analysis.
     */
    encodeTraces(spans: TraceSpan[]): Promise<Float32Array>;
    /**
     * Detect anomalies in encoded traces
     *
     * Uses sparse representations to identify outliers and anomalous patterns.
     */
    detectAnomalies(encoded: Float32Array, threshold: number): Promise<number[]>;
    /**
     * Analyze critical path in traces
     *
     * Uses dependency analysis to identify the critical path through
     * the trace spans.
     */
    analyzeCriticalPath(encoded: Float32Array): Promise<string[]>;
    /**
     * Analyze trace patterns for bottleneck detection
     */
    analyzePatterns(spans: TraceSpan[]): {
        patterns: Map<string, number>;
        hotspots: string[];
        dependencies: Map<string, string[]>;
    };
    private initializeFeatureHashes;
    private extractSpanFeatures;
    private hashFeature;
    private hashString;
    private bucketize;
    private normalizeEncoding;
    private sparsify;
    private computeCacheKey;
}
/**
 * Create a new sparse bridge instance
 */
export declare function createPerfSparseBridge(config?: Partial<SparseEncodingConfig>): PerfSparseBridge;
export {};
//# sourceMappingURL=sparse-bridge.d.ts.map