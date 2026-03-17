/**
 * Cognitive Bridge
 *
 * Bridge to cognitum-gate-kernel for cognitive computation including
 * working memory, attention control, meta-cognition, and scaffolding.
 */
import type { CognitiveItem, MetaCognitiveAssessment } from '../types.js';
/**
 * WASM module status
 */
export type WasmModuleStatus = 'unloaded' | 'loading' | 'ready' | 'error';
/**
 * Cognitive configuration
 */
export interface CognitiveConfig {
    /** Working memory capacity (Miller's 7 +/- 2) */
    workingMemorySize: number;
    /** Attention span in seconds */
    attentionSpan: number;
    /** Enable meta-cognitive monitoring */
    metaCognitionEnabled: boolean;
    /** Scaffolding level */
    scaffoldingLevel: 'none' | 'light' | 'moderate' | 'heavy';
    /** Decay rate for memory items */
    decayRate: number;
}
/**
 * Attention state
 */
export interface AttentionState {
    focus: string[];
    breadth: number;
    intensity: number;
    distractors: string[];
}
/**
 * WASM cognitive module interface
 */
interface CognitiveModule {
    store(item: CognitiveItem): boolean;
    retrieve(id: string): CognitiveItem | null;
    search(query: Float32Array, k: number): CognitiveItem[];
    decay(deltaTime: number): void;
    consolidate(): void;
    focus(ids: string[]): AttentionState;
    broaden(): AttentionState;
    narrow(): AttentionState;
    getAttentionState(): AttentionState;
    assess(): MetaCognitiveAssessment;
    monitor(task: string): number;
    regulate(strategy: string): void;
    scaffold(task: string, difficulty: number): string[];
    adapt(performance: number): void;
}
/**
 * Cognitive Bridge implementation
 */
export declare class CognitiveBridge {
    readonly name = "cognitum-gate-kernel";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private config;
    constructor(config?: Partial<CognitiveConfig>);
    get status(): WasmModuleStatus;
    get initialized(): boolean;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    getModule(): CognitiveModule | null;
    /**
     * Store item in working memory
     */
    store(item: CognitiveItem): boolean;
    /**
     * Retrieve item from working memory
     */
    retrieve(id: string): CognitiveItem | null;
    /**
     * Search working memory
     */
    search(query: Float32Array, k: number): CognitiveItem[];
    /**
     * Apply memory decay
     */
    decay(deltaTime: number): void;
    /**
     * Consolidate working memory to long-term
     */
    consolidate(): void;
    /**
     * Focus attention on specific items
     */
    focus(ids: string[]): AttentionState;
    /**
     * Broaden attention
     */
    broaden(): AttentionState;
    /**
     * Narrow attention
     */
    narrow(): AttentionState;
    /**
     * Get current attention state
     */
    getAttentionState(): AttentionState;
    /**
     * Perform meta-cognitive assessment
     */
    assess(): MetaCognitiveAssessment;
    /**
     * Monitor task performance
     */
    monitor(task: string): number;
    /**
     * Apply cognitive regulation strategy
     */
    regulate(strategy: string): void;
    /**
     * Get scaffolding for task
     */
    scaffold(task: string, difficulty: number): string[];
    /**
     * Adapt scaffolding based on performance
     */
    adapt(performance: number): void;
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new cognitive bridge
 */
export declare function createCognitiveBridge(config?: Partial<CognitiveConfig>): CognitiveBridge;
export default CognitiveBridge;
//# sourceMappingURL=cognitive-bridge.d.ts.map