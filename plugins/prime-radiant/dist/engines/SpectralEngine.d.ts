/**
 * Spectral Engine - Stability Analysis
 *
 * Implements spectral graph theory analysis for system stability.
 * Uses eigenvalue decomposition to detect clustering, connectivity,
 * and stability issues in multi-agent systems.
 */
import type { ISpectralEngine, SpectralResult, SpectralGap, WasmModule } from '../types.js';
/**
 * SpectralEngine - WASM wrapper for spectral stability analysis
 */
export declare class SpectralEngine implements ISpectralEngine {
    private wasmModule;
    private readonly stabilityThreshold;
    constructor(wasmModule?: WasmModule);
    /**
     * Set the WASM module after initialization
     */
    setWasmModule(module: WasmModule): void;
    /**
     * Analyze stability of a system represented as adjacency matrix
     *
     * @param matrix - Adjacency matrix (2D array)
     * @returns SpectralResult with stability metrics
     */
    analyzeStability(matrix: number[][]): Promise<SpectralResult>;
    /**
     * Compute eigenvalues of a matrix
     *
     * @param matrix - Square matrix (2D array or flattened Float32Array)
     * @returns Sorted eigenvalues (descending)
     */
    computeEigenvalues(matrix: number[][] | Float32Array): Promise<number[]>;
    /**
     * Compute spectral gap (difference between first and second eigenvalues)
     *
     * @param eigenvalues - Array of eigenvalues
     * @returns Spectral gap value
     */
    computeSpectralGap(eigenvalues: number[]): number;
    /**
     * Compute stability index from eigenvalues
     *
     * @param eigenvalues - Array of eigenvalues
     * @returns Stability index [0, 1]
     */
    computeStabilityIndex(eigenvalues: number[]): number;
    /**
     * Create SpectralGap value object
     */
    createSpectralGap(eigenvalues: number[]): SpectralGap;
    /**
     * Build Laplacian matrix from adjacency matrix
     */
    buildLaplacian(adjacency: Float32Array, n: number): Float32Array;
    /**
     * Pure JS eigenvalue computation using power iteration
     */
    private computeEigenvaluesJS;
    /**
     * Matrix-vector multiplication
     */
    private matrixVectorMultiply;
    /**
     * Normalize vector to unit length
     */
    private normalizeVector;
    /**
     * Dot product of two vectors
     */
    private dotProduct;
}
//# sourceMappingURL=SpectralEngine.d.ts.map