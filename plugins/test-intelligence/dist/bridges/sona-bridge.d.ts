/**
 * SONA Bridge for Test Intelligence
 *
 * Provides pattern learning and continuous adaptation for test intelligence
 * using SONA (Self-Optimizing Neural Architecture) with LoRA fine-tuning
 * and EWC++ memory preservation.
 */
import type { SonaBridgeInterface, TestExecutionPattern } from '../types.js';
/**
 * SONA configuration for test intelligence
 */
interface SonaConfig {
    mode: 'real-time' | 'balanced' | 'research' | 'edge' | 'batch';
    loraRank: number;
    learningRate: number;
    ewcLambda: number;
    batchSize: number;
}
/**
 * SONA Bridge Implementation for Test Intelligence
 *
 * Provides continuous learning capabilities for test pattern recognition:
 * - Pattern storage and retrieval using HNSW-indexed embeddings
 * - LoRA-based fine-tuning for domain adaptation
 * - EWC++ for preventing catastrophic forgetting
 */
export declare class TestSonaBridge implements SonaBridgeInterface {
    readonly name = "test-intelligence-sona";
    readonly version = "0.1.0";
    private status;
    private config;
    private patterns;
    private patternEmbeddings;
    private loraWeights;
    private ewcState;
    private patternIndex;
    constructor(config?: Partial<SonaConfig>);
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    /**
     * Learn from test execution patterns
     *
     * Uses SONA's continuous learning to extract and store patterns
     * from successful test selections.
     */
    learnPatterns(patterns: TestExecutionPattern[]): Promise<number>;
    /**
     * Find similar patterns to a query embedding
     *
     * Uses approximate nearest neighbor search to find patterns
     * with similar characteristics.
     */
    findSimilarPatterns(query: Float32Array, k: number): Promise<TestExecutionPattern[]>;
    /**
     * Store a single pattern
     */
    storePattern(pattern: TestExecutionPattern): Promise<void>;
    /**
     * Get current operating mode
     */
    getMode(): SonaConfig['mode'];
    /**
     * Set operating mode
     */
    setMode(mode: SonaConfig['mode']): void;
    /**
     * Get pattern count
     */
    getPatternCount(): number;
    /**
     * Predict test selection based on learned patterns
     */
    predictSelection(codeChanges: string[], availableTests: string[]): {
        tests: string[];
        confidence: number;
    };
    private initializeMockLoRA;
    private generatePatternId;
    private hashArray;
    private computePatternGradients;
    private updateLoRA;
    private updateEWCState;
    private applyLoRA;
    private cosineSimilarity;
    private createQueryEmbedding;
    private findSimilarPatternsSync;
    private hashString;
}
/**
 * Create a new SONA bridge instance
 */
export declare function createTestSonaBridge(config?: Partial<SonaConfig>): TestSonaBridge;
export {};
//# sourceMappingURL=sona-bridge.d.ts.map