/**
 * Prime Radiant Plugin - Type Definitions
 *
 * Core types for mathematical AI interpretability engines including
 * sheaf cohomology, spectral analysis, causal inference, quantum topology,
 * category theory, and homotopy type theory.
 */
/**
 * Coherence Energy - measures contradiction level using Sheaf Laplacian
 * Range: [0, 1] where 0 = fully coherent, 1 = fully contradictory
 */
export interface CoherenceEnergy {
    readonly value: number;
    readonly coherent: boolean;
    readonly confidence: number;
    readonly level: 'coherent' | 'warning' | 'contradictory';
}
/**
 * Spectral Gap - difference between first and second eigenvalues
 * Positive gap indicates stability
 */
export interface SpectralGap {
    readonly value: number;
    readonly stable: boolean;
    readonly stabilityLevel: 'stable' | 'marginal' | 'unstable';
}
/**
 * Causal Effect - estimated effect of intervention on outcome
 */
export interface CausalEffect {
    readonly value: number;
    readonly confidence: number;
    readonly significant: boolean;
    readonly direction: 'positive' | 'negative' | 'neutral';
}
/**
 * Betti Numbers - topological invariants
 * b0 = connected components, b1 = loops, b2 = voids
 */
export interface BettiNumbers {
    readonly values: number[];
    readonly b0: number;
    readonly b1: number;
    readonly b2: number;
    readonly connected: boolean;
    readonly hasLoops: boolean;
    readonly hasVoids: boolean;
}
/**
 * Persistence Diagram point - birth and death times
 */
export interface PersistencePoint {
    readonly birth: number;
    readonly death: number;
    readonly persistence: number;
    readonly dimension: number;
}
/**
 * Persistence Diagram - collection of persistence points
 */
export interface PersistenceDiagram {
    readonly points: PersistencePoint[];
    readonly maxPersistence: number;
    readonly totalPersistence: number;
}
/**
 * Result from coherence check using Sheaf Laplacian
 */
export interface CoherenceResult {
    readonly coherent: boolean;
    readonly energy: number;
    readonly violations: string[];
    readonly confidence: number;
}
/**
 * Sheaf structure for coherence computation
 */
export interface Sheaf {
    readonly vertices: number[];
    readonly edges: Array<[number, number]>;
    readonly restrictions: Map<string, Float32Array>;
}
/**
 * Result from spectral stability analysis
 */
export interface SpectralResult {
    readonly stable: boolean;
    readonly eigenvalues: number[];
    readonly spectralGap: number;
    readonly stabilityIndex: number;
}
/**
 * Matrix representation for spectral analysis
 */
export interface Matrix {
    readonly data: number[][] | Float32Array;
    readonly rows: number;
    readonly cols: number;
}
/**
 * Causal graph structure
 */
export interface CausalGraph {
    readonly nodes: string[];
    readonly edges: Array<[string, string]>;
}
/**
 * Intervention in causal inference
 */
export interface Intervention {
    readonly treatment: string;
    readonly outcome: string;
    readonly graph: CausalGraph;
    readonly observedData?: Map<string, number[]>;
}
/**
 * Result from causal inference
 */
export interface CausalResult {
    readonly effect: number;
    readonly confounders: string[];
    readonly interventionValid: boolean;
    readonly backdoorPaths: string[][];
}
/**
 * Simplicial complex for topological computations
 */
export interface SimplicialComplex {
    readonly vertices: number[];
    readonly simplices: number[][];
    readonly maxDimension: number;
}
/**
 * Filtration for persistent homology
 */
export interface Filtration {
    readonly complex: SimplicialComplex;
    readonly values: number[];
}
/**
 * Result from quantum topology computation
 */
export interface TopologyResult {
    readonly bettiNumbers: number[];
    readonly persistenceDiagram: PersistenceDiagram;
    readonly homologyClasses: number;
}
/**
 * Morphism in a category
 */
export interface Morphism {
    readonly source: string;
    readonly target: string;
    readonly name: string;
    readonly data?: unknown;
}
/**
 * Result from morphism application
 */
export interface MorphismResult {
    readonly valid: boolean;
    readonly result: unknown;
    readonly naturalTransformation: boolean;
}
/**
 * Functor between categories
 */
export interface Functor {
    readonly name: string;
    readonly sourceCategory: string;
    readonly targetCategory: string;
}
/**
 * Path in HoTT - represents equality/equivalence
 */
export interface Path {
    readonly source: unknown;
    readonly target: unknown;
    readonly type: string;
    readonly proof?: string;
}
/**
 * Value with its type
 */
export interface TypedValue {
    readonly value: unknown;
    readonly type: string;
}
/**
 * Result from HoTT verification
 */
export interface HottResult {
    readonly valid: boolean;
    readonly type: string;
    readonly normalForm: string;
}
/**
 * Cohomology Engine interface - Sheaf Laplacian coherence
 */
export interface ICohomologyEngine {
    checkCoherence(vectors: Float32Array[]): Promise<CoherenceResult>;
    computeLaplacianEnergy(sheaf: Sheaf): Promise<number>;
    detectContradictions(vectors: Float32Array[]): Promise<string[]>;
}
/**
 * Spectral Engine interface - stability analysis
 */
export interface ISpectralEngine {
    analyzeStability(matrix: number[][]): Promise<SpectralResult>;
    computeEigenvalues(matrix: number[][] | Float32Array): Promise<number[]>;
    computeSpectralGap(eigenvalues: number[]): number;
    computeStabilityIndex(eigenvalues: number[]): number;
}
/**
 * Causal Engine interface - do-calculus
 */
export interface ICausalEngine {
    infer(intervention: Intervention): Promise<CausalResult>;
    computeDoCalculus(graph: CausalGraph, treatment: string, outcome: string): Promise<CausalEffect>;
    identifyConfounders(graph: CausalGraph, treatment: string, outcome: string): string[];
    findBackdoorPaths(graph: CausalGraph, treatment: string, outcome: string): string[][];
}
/**
 * Quantum Engine interface - topology
 */
export interface IQuantumEngine {
    computeBettiNumbers(complex: SimplicialComplex): Promise<BettiNumbers>;
    persistenceDiagram(filtration: Filtration): Promise<PersistenceDiagram>;
    computeHomologyClasses(complex: SimplicialComplex): Promise<number>;
}
/**
 * Category Engine interface - functors and morphisms
 */
export interface ICategoryEngine {
    applyFunctor(morphism: Morphism): Promise<MorphismResult>;
    compose(f: Morphism, g: Morphism): Promise<Morphism>;
    validateMorphism(source: unknown, target: unknown, morphism: string): boolean;
    isNaturalTransformation(morphism: string): boolean;
}
/**
 * HoTT Engine interface - type theory
 */
export interface IHottEngine {
    checkPathEquivalence(path1: Path, path2: Path): Promise<boolean>;
    transportAlong(path: Path, value: TypedValue): Promise<TypedValue>;
    verifyProof(proposition: string, proof: string): Promise<boolean>;
    inferType(term: string): Promise<string>;
    normalize(term: string): Promise<string>;
}
/**
 * WASM Module interface matching prime-radiant-advanced-wasm
 */
export interface WasmModule {
    cohomology_compute_energy(vectors: Float32Array, dims: Uint32Array): number;
    cohomology_detect_contradictions(vectors: Float32Array, dims: Uint32Array): Uint8Array;
    spectral_compute_eigenvalues(matrix: Float32Array, n: number): Float32Array;
    spectral_compute_gap(eigenvalues: Float32Array): number;
    spectral_stability_index(eigenvalues: Float32Array): number;
    causal_estimate_effect(treatment: number, outcome: number, adjMatrix: Float32Array, n: number): number;
    causal_find_confounders(treatment: number, outcome: number, adjMatrix: Float32Array, n: number): Uint32Array;
    causal_backdoor_paths(treatment: number, outcome: number, adjMatrix: Float32Array, n: number): Uint32Array;
    quantum_betti_numbers(points: Float32Array, n: number, dim: number, maxDim: number): Uint32Array;
    quantum_persistence_diagram(points: Float32Array, n: number, dim: number): Float32Array;
    quantum_homology_classes(points: Float32Array, n: number, dim: number, targetDim: number): number;
    category_apply_morphism(sourcePtr: number, morphismId: number): number;
    category_compose(morphismAId: number, morphismBId: number): number;
    category_is_natural(morphismId: number): boolean;
    hott_verify_proof(propositionPtr: number, proofPtr: number): boolean;
    hott_infer_type(termPtr: number): number;
    hott_normalize(termPtr: number): number;
    hott_path_equivalent(path1Ptr: number, path2Ptr: number): boolean;
    hott_transport(pathPtr: number, valuePtr: number): number;
    alloc(size: number): number;
    dealloc(ptr: number, size: number): void;
    memory: WebAssembly.Memory;
}
/**
 * Configuration for WASM bridge initialization
 */
export interface WasmBridgeConfig {
    wasmPath?: string;
    enableLogging?: boolean;
    cacheSize?: number;
}
/**
 * Status of WASM initialization
 */
export interface WasmStatus {
    initialized: boolean;
    loadTime?: number;
    bundleSize?: number;
    engines: {
        cohomology: boolean;
        spectral: boolean;
        causal: boolean;
        quantum: boolean;
        category: boolean;
        hott: boolean;
    };
}
/**
 * Coherence check result (simplified alias for compatibility)
 */
export interface CoherenceCheckResult {
    coherent: boolean;
    energy: number;
    violations: string[];
    confidence: number;
}
/**
 * Coherence validation result with action
 */
export interface CoherenceValidationResult {
    action: CoherenceAction;
    coherenceResult: CoherenceCheckResult;
    interpretation: string;
}
/**
 * Coherence thresholds configuration
 */
export interface CoherenceThresholds {
    reject: number;
    warn: number;
    allow: number;
}
/**
 * Validation action based on coherence check
 */
export type CoherenceAction = 'allow' | 'warn' | 'reject';
/**
 * Spectral analysis result (simplified)
 */
export interface SpectralAnalysisResult {
    stable: boolean;
    eigenvalues: number[];
    spectralGap: number;
    stabilityIndex: number;
}
/**
 * Type of spectral analysis
 */
export type SpectralAnalysisType = 'stability' | 'clustering' | 'connectivity';
/**
 * Stability index type alias
 */
export type StabilityIndex = number;
/**
 * Causal inference result (simplified)
 */
export interface CausalInferenceResult {
    effect: number;
    confounders: string[];
    interventionValid: boolean;
    backdoorPaths: string[];
}
/**
 * Causal query parameters
 */
export interface CausalQuery {
    treatment: string;
    outcome: string;
    graph: CausalGraph;
}
/**
 * Betti interpretation strings
 */
export interface BettiInterpretation {
    b0: string;
    b1: string;
    b2: string;
}
/**
 * HoTT proof result (simplified)
 */
export interface HottProofResult {
    valid: boolean;
    type: string;
    normalForm: string;
}
/**
 * HoTT verification input
 */
export interface HottVerification {
    proposition: string;
    proof: string;
}
/**
 * Functor application context
 */
export interface FunctorContext {
    source: unknown;
    target: unknown;
    morphism: string;
}
/**
 * Agent state for consensus verification
 */
export interface AgentState {
    agentId: string;
    embedding: number[];
    vote?: string | boolean;
    metadata?: Record<string, unknown>;
}
/**
 * Consensus result from mathematical verification
 */
export interface ConsensusResult {
    consensusAchieved: boolean;
    agreementRatio: number;
    coherenceEnergy: number;
    spectralStability: boolean;
    spectralGap: number;
    violations: string[];
    recommendation: string;
}
/**
 * Consensus verification parameters
 */
export interface ConsensusParams {
    agentStates: AgentState[];
    consensusThreshold?: number;
}
/**
 * Memory entry for coherence validation
 */
export interface MemoryEntry {
    key: string;
    content: string;
    embedding: Float32Array;
    metadata?: Record<string, unknown>;
}
/**
 * Memory coherence gate validation result
 */
export interface MemoryCoherenceValidation {
    entry: MemoryEntry;
    existingContext?: MemoryEntry[];
    coherenceResult: CoherenceCheckResult;
    action: CoherenceAction;
}
/**
 * Plugin configuration options
 */
export interface PrimeRadiantConfig {
    coherence: {
        warnThreshold: number;
        rejectThreshold: number;
        cacheEnabled: boolean;
        cacheTTL: number;
    };
    spectral: {
        stabilityThreshold: number;
        maxMatrixSize: number;
    };
    causal: {
        maxBackdoorPaths: number;
        confidenceThreshold: number;
    };
}
/**
 * Default configuration values
 */
export declare const DEFAULT_CONFIG: PrimeRadiantConfig;
/**
 * Prime Radiant specific error codes
 */
export declare const PrimeRadiantErrorCodes: {
    readonly WASM_NOT_INITIALIZED: "PR_WASM_NOT_INITIALIZED";
    readonly COHERENCE_VIOLATION: "PR_COHERENCE_VIOLATION";
    readonly INVALID_VECTORS: "PR_INVALID_VECTORS";
    readonly INVALID_CAUSAL_GRAPH: "PR_INVALID_CAUSAL_GRAPH";
    readonly MATRIX_SIZE_EXCEEDED: "PR_MATRIX_SIZE_EXCEEDED";
    readonly ENGINE_NOT_AVAILABLE: "PR_ENGINE_NOT_AVAILABLE";
};
export type PrimeRadiantErrorCode = (typeof PrimeRadiantErrorCodes)[keyof typeof PrimeRadiantErrorCodes];
//# sourceMappingURL=types.d.ts.map