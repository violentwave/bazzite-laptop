/**
 * SONA Bridge
 *
 * Bridge to SONA (Self-Optimizing Neural Architecture) for continuous
 * learning with LoRA fine-tuning and EWC++ memory preservation.
 */
import type { WasmBridge, WasmModuleStatus, SonaConfig } from '../types.js';
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
 * SONA pattern
 */
export interface SonaPattern {
    id: string;
    embedding: Float32Array;
    successRate: number;
    usageCount: number;
    domain: string;
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
 * SONA WASM module interface
 */
interface SonaModule {
    learn(trajectories: SonaTrajectory[], config: SonaConfig): number;
    predict(state: Float32Array): {
        action: string;
        confidence: number;
    };
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
export declare class SonaBridge implements WasmBridge<SonaModule> {
    readonly name = "sona";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private config;
    constructor(config?: Partial<SonaConfig>);
    get status(): WasmModuleStatus;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    getModule(): SonaModule | null;
    /**
     * Learn from trajectories
     */
    learn(trajectories: SonaTrajectory[], config?: Partial<SonaConfig>): number;
    /**
     * Predict next action
     */
    predict(state: Float32Array): {
        action: string;
        confidence: number;
    };
    /**
     * Store a pattern
     */
    storePattern(pattern: SonaPattern): void;
    /**
     * Find similar patterns
     */
    findPatterns(query: Float32Array, k: number): SonaPattern[];
    /**
     * Apply LoRA transformation
     */
    applyLoRA(input: Float32Array, weights: LoRAWeights): Float32Array;
    /**
     * Consolidate memory with EWC
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
export {};
//# sourceMappingURL=sona.d.ts.map