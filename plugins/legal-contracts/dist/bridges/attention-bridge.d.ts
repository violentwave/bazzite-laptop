/**
 * Flash Attention Bridge for Legal Contract Analysis
 *
 * Provides cross-attention computation for clause alignment and similarity
 * using ruvector-attention-wasm for high-performance attention operations.
 *
 * Features:
 * - Cross-attention for contract comparison
 * - Clause alignment between documents
 * - Semantic similarity scoring
 * - Memory-efficient attention patterns
 *
 * Based on ADR-034: Legal Contract Analysis Plugin
 *
 * @module v3/plugins/legal-contracts/bridges/attention-bridge
 */
import type { IAttentionBridge, ExtractedClause, ClauseAlignment } from '../types.js';
/**
 * Flash Attention Bridge Implementation
 */
export declare class AttentionBridge implements IAttentionBridge {
    private wasmModule;
    private initialized;
    private readonly embeddingDim;
    constructor(embeddingDim?: number);
    /**
     * Initialize the WASM module
     */
    initialize(): Promise<void>;
    /**
     * Check if initialized
     */
    isInitialized(): boolean;
    /**
     * Compute cross-attention between clause embeddings
     */
    computeCrossAttention(queryEmbeddings: Float32Array[], keyEmbeddings: Float32Array[], mask?: boolean[][]): Promise<Float32Array[][]>;
    /**
     * Align clauses between two documents using attention
     */
    alignClauses(baseClauses: ExtractedClause[], compareClauses: ExtractedClause[]): Promise<ClauseAlignment[]>;
    /**
     * Find most relevant clauses for a given query
     */
    findRelevantClauses(query: string | Float32Array, clauses: ExtractedClause[], topK: number): Promise<Array<{
        clause: ExtractedClause;
        score: number;
    }>>;
    /**
     * Load WASM module dynamically
     */
    private loadWasmModule;
    /**
     * Flatten array of embeddings into single Float32Array
     */
    private flattenEmbeddings;
    /**
     * Compute attention scores in pure JavaScript (fallback)
     */
    private computeAttentionScoresJS;
    /**
     * Compute softmax over array
     */
    private softmax;
    /**
     * Get embeddings from clauses or compute them
     */
    private getOrComputeEmbeddings;
    /**
     * Embed text to vector (placeholder - would use embedding model)
     */
    private embedText;
    /**
     * Compute differences between two clauses
     */
    private computeDifferences;
}
/**
 * Create and export default bridge instance
 */
export declare function createAttentionBridge(embeddingDim?: number): IAttentionBridge;
export default AttentionBridge;
//# sourceMappingURL=attention-bridge.d.ts.map