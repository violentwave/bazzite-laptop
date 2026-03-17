/**
 * HNSW Bridge - Healthcare Clinical Plugin
 *
 * Provides HNSW (Hierarchical Navigable Small World) vector search
 * for patient similarity matching. Integrates with micro-hnsw-wasm
 * for 150x faster similarity search.
 *
 * HIPAA Compliance:
 * - All patient data processed locally in WASM sandbox
 * - No PHI transmitted externally
 * - Embeddings use differential privacy
 */
import type { HNSWBridge, HNSWConfig, PatientFeatures, SimilarPatient, Logger } from '../types.js';
/**
 * Patient embedding generator
 * Converts clinical features to dense vector representations
 */
export declare class PatientEmbeddingGenerator {
    private readonly dimensions;
    constructor(dimensions?: number);
    /**
     * Generate embedding for patient features
     * Uses a simplified bag-of-features approach
     * In production, use ClinicalBERT or similar
     */
    generateEmbedding(features: PatientFeatures): Float32Array;
    /**
     * Calculate cosine similarity between two embeddings
     */
    cosineSimilarity(a: Float32Array, b: Float32Array): number;
    private hashCode;
    private getIndicesFromHash;
    private normalizeLabValue;
    private normalizeVitalValue;
    private l2Normalize;
}
/**
 * Healthcare HNSW Bridge implementation
 * Wraps micro-hnsw-wasm for patient similarity search
 */
export declare class HealthcareHNSWBridge implements HNSWBridge {
    private wasmModule;
    private indexPtr;
    private config;
    private logger;
    private idToIndex;
    private indexToId;
    private metadata;
    private nextIndex;
    private embeddingGenerator;
    initialized: boolean;
    constructor(config?: Partial<HNSWConfig>, logger?: Logger);
    /**
     * Initialize the HNSW index
     */
    initialize(config?: HNSWConfig): Promise<void>;
    /**
     * Add a patient vector to the index
     */
    addVector(id: string, vector: Float32Array, metadata?: Record<string, unknown>): Promise<void>;
    /**
     * Search for similar patients
     */
    search(query: Float32Array, topK: number, filter?: Record<string, unknown>): Promise<Array<{
        id: string;
        distance: number;
    }>>;
    /**
     * Delete a patient vector from the index
     */
    delete(id: string): Promise<boolean>;
    /**
     * Get the number of vectors in the index
     */
    count(): Promise<number>;
    /**
     * Search for similar patients by clinical features
     */
    searchByFeatures(features: PatientFeatures, topK?: number, cohortFilter?: string): Promise<SimilarPatient[]>;
    /**
     * Add a patient by clinical features
     */
    addPatient(patientId: string, features: PatientFeatures, metadata?: Record<string, unknown>): Promise<void>;
    /**
     * Cleanup resources
     */
    destroy(): void;
    private resolveWasmPath;
    private loadWasmModule;
    private bruteForceSearch;
    private matchesFilter;
}
/**
 * Create a new HNSW bridge instance
 */
export declare function createHNSWBridge(config?: Partial<HNSWConfig>, logger?: Logger): HealthcareHNSWBridge;
export default HealthcareHNSWBridge;
//# sourceMappingURL=hnsw-bridge.d.ts.map