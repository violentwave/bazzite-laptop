/**
 * SONA Bridge
 *
 * Bridge to SONA (Self-Optimizing Neural Architecture) for continuous
 * learning with LoRA fine-tuning and EWC++ memory preservation.
 */
import type { SonaPattern } from '../types.js';
/**
 * WASM module status
 */
export type WasmModuleStatus = 'unloaded' | 'loading' | 'ready' | 'error';
/**
 * SONA configuration
 */
export interface SonaConfig {
    /** Operating mode */
    mode: 'real-time' | 'balanced' | 'research' | 'edge' | 'batch';
    /** LoRA rank for fine-tuning */
    loraRank: number;
    /** Learning rate */
    learningRate: number;
    /** EWC++ lambda (memory preservation strength) */
    ewcLambda: number;
    /** Batch size for training */
    batchSize: number;
}
/**
 * SONA trajectory for learning
 */
export interface SonaTrajectory {
    id: string;
    domain: string;
    steps: SonaStep[];
    qualityScore: number;
    metadata?: Record<string, unknown>;
}
/**
 * SONA learning step
 */
export interface SonaStep {
    stateBefore: Float32Array;
    action: string;
    stateAfter: Float32Array;
    reward: number;
    timestamp: number;
}
/**
 * LoRA weights
 */
export interface LoRAWeights {
    A: Map<string, Float32Array>;
    B: Map<string, Float32Array>;
    rank: number;
    alpha: number;
}
/**
 * EWC state
 */
export interface EWCState {
    fisher: Map<string, Float32Array>;
    means: Map<string, Float32Array>;
    lambda: number;
}
/**
 * SONA prediction result
 */
export interface SonaPrediction {
    action: string;
    confidence: number;
    alternativeActions?: Array<{
        action: string;
        confidence: number;
    }>;
}
/**
 * SONA WASM module interface
 */
interface SonaModule {
    learn(trajectories: SonaTrajectory[], config: SonaConfig): number;
    predict(state: Float32Array): SonaPrediction;
    storePattern(pattern: SonaPattern): void;
    findPatterns(query: Float32Array, k: number): SonaPattern[];
    updatePatternSuccess(patternId: string, success: boolean): void;
    applyLoRA(input: Float32Array, weights: LoRAWeights): Float32Array;
    updateLoRA(gradients: Float32Array, config: SonaConfig): LoRAWeights;
    computeFisher(trajectories: SonaTrajectory[]): Map<string, Float32Array>;
    consolidate(ewcState: EWCState): void;
    setMode(mode: SonaConfig['mode']): void;
    getMode(): SonaConfig['mode'];
}
/**
 * SONA Bridge implementation
 */
export declare class SonaBridge {
    readonly name = "sona";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private config;
    constructor(config?: Partial<SonaConfig>);
    get status(): WasmModuleStatus;
    get initialized(): boolean;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    getModule(): SonaModule | null;
    /**
     * Learn from trajectories
     * Returns improvement score (0-1)
     */
    learn(trajectories: SonaTrajectory[], config?: Partial<SonaConfig>): number;
    /**
     * Predict next action
     */
    predict(state: Float32Array): SonaPrediction;
    /**
     * Store a pattern
     */
    storePattern(pattern: SonaPattern): void;
    /**
     * Find similar patterns
     */
    findPatterns(query: Float32Array, k: number): SonaPattern[];
    /**
     * Update pattern success rate
     */
    updatePatternSuccess(patternId: string, success: boolean): void;
    /**
     * Apply LoRA transformation
     */
    applyLoRA(input: Float32Array, weights: LoRAWeights): Float32Array;
    /**
     * Update LoRA weights from gradients
     */
    updateLoRA(gradients: Float32Array, config?: Partial<SonaConfig>): LoRAWeights;
    /**
     * Compute Fisher information matrix
     */
    computeFisher(trajectories: SonaTrajectory[]): Map<string, Float32Array>;
    /**
     * Consolidate memory with EWC++
     */
    consolidate(ewcState: EWCState): void;
    /**
     * Set operating mode
     */
    setMode(mode: SonaConfig['mode']): void;
    /**
     * Get current mode
     */
    getMode(): SonaConfig['mode'];
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new SONA bridge
 */
export declare function createSonaBridge(config?: Partial<SonaConfig>): SonaBridge;
export default SonaBridge;
//# sourceMappingURL=sona-bridge.d.ts.map