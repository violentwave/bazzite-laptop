/**
 * Quantum Engine - Topology Operations
 *
 * Implements quantum topology computations including:
 * - Betti numbers (topological invariants)
 * - Persistent homology
 * - Simplicial complex analysis
 *
 * Used for analyzing agent relationship graphs and memory topology.
 */
import type { IQuantumEngine, BettiNumbers, PersistenceDiagram, SimplicialComplex, Filtration, TopologyResult, WasmModule } from '../types.js';
/**
 * QuantumEngine - WASM wrapper for quantum topology operations
 */
export declare class QuantumEngine implements IQuantumEngine {
    private wasmModule;
    constructor(wasmModule?: WasmModule);
    /**
     * Set the WASM module after initialization
     */
    setWasmModule(module: WasmModule): void;
    /**
     * Compute Betti numbers for a simplicial complex
     *
     * @param complex - Simplicial complex
     * @returns BettiNumbers value object
     */
    computeBettiNumbers(complex: SimplicialComplex): Promise<BettiNumbers>;
    /**
     * Compute persistence diagram for a filtration
     *
     * @param filtration - Filtration of simplicial complex
     * @returns PersistenceDiagram
     */
    persistenceDiagram(filtration: Filtration): Promise<PersistenceDiagram>;
    /**
     * Compute number of homology classes
     *
     * @param complex - Simplicial complex
     * @returns Number of homology classes
     */
    computeHomologyClasses(complex: SimplicialComplex): Promise<number>;
    /**
     * Compute full topology result
     *
     * @param points - Point cloud as Float32Array[]
     * @param maxDimension - Maximum dimension for Betti numbers
     * @returns TopologyResult
     */
    computeTopology(points: Float32Array[], maxDimension?: number): Promise<TopologyResult>;
    /**
     * Create BettiNumbers value object
     */
    createBettiNumbers(values: number[]): BettiNumbers;
    /**
     * Pure JS implementation of Betti number computation
     * Uses rank-nullity approach on boundary matrices
     */
    private computeBettiNumbersJS;
    /**
     * Count connected components using union-find
     */
    private countConnectedComponents;
    /**
     * Compute b1 (number of 1-cycles / loops)
     */
    private computeB1;
    /**
     * Compute b2 (number of 2-cycles / voids)
     */
    private computeB2;
    /**
     * Pure JS implementation of persistence diagram
     */
    private computePersistenceDiagramJS;
    /**
     * Parse WASM persistence diagram result
     */
    private parsePersistenceDiagram;
    /**
     * Build Vietoris-Rips complex from point cloud
     */
    private buildRipsComplex;
    /**
     * Build filtration from complex
     */
    private buildFiltration;
    /**
     * Compute threshold for Rips complex
     */
    private computeThreshold;
    /**
     * Euclidean distance between two points
     */
    private euclideanDistance;
    /**
     * Convert simplicial complex to point cloud for WASM
     */
    private complexToPointCloud;
}
//# sourceMappingURL=QuantumEngine.d.ts.map