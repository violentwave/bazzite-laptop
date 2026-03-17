/**
 * Cohomology Engine - Sheaf Laplacian Coherence
 *
 * Implements coherence checking using sheaf cohomology and Laplacian energy.
 * Energy 0 = fully coherent, Energy 1 = fully contradictory.
 *
 * Based on: https://arxiv.org/abs/1808.04718 (Sheaf Laplacian Theory)
 */
import type { ICohomologyEngine, CoherenceResult, CoherenceEnergy, Sheaf, WasmModule } from '../types.js';
/**
 * CohomologyEngine - WASM wrapper for sheaf Laplacian coherence checking
 */
export declare class CohomologyEngine implements ICohomologyEngine {
    private wasmModule;
    private readonly coherenceThreshold;
    private readonly contradictionThreshold;
    constructor(wasmModule?: WasmModule);
    /**
     * Set the WASM module after initialization
     */
    setWasmModule(module: WasmModule): void;
    /**
     * Check coherence of a set of vectors using Sheaf Laplacian energy
     *
     * @param vectors - Array of embedding vectors to check
     * @returns CoherenceResult with energy and violation details
     */
    checkCoherence(vectors: Float32Array[]): Promise<CoherenceResult>;
    /**
     * Compute Sheaf Laplacian energy for coherence measurement
     *
     * @param sheaf - Sheaf structure with vertices, edges, and restrictions
     * @returns Energy value [0, 1]
     */
    computeLaplacianEnergy(sheaf: Sheaf): Promise<number>;
    /**
     * Detect contradictions in a set of vectors
     *
     * @param vectors - Embedding vectors to analyze
     * @returns Array of violation descriptions
     */
    detectContradictions(vectors: Float32Array[]): Promise<string[]>;
    /**
     * Create CoherenceEnergy value object from raw energy
     */
    createCoherenceEnergy(value: number): CoherenceEnergy;
    /**
     * Internal: Compute Sheaf Laplacian energy from vectors
     */
    private computeSheafLaplacianEnergy;
    /**
     * Pure JS implementation of Sheaf Laplacian energy
     * Uses the graph Laplacian approximation
     */
    private computeEnergyJS;
    /**
     * Compute cosine similarity between two vectors
     */
    private cosineSimilarity;
    /**
     * Compute difference between two vectors
     */
    private vectorDifference;
    /**
     * Compute L2 norm of a vector
     */
    private vectorNorm;
    /**
     * Flatten array of vectors for WASM
     */
    private flattenVectors;
}
//# sourceMappingURL=CohomologyEngine.d.ts.map