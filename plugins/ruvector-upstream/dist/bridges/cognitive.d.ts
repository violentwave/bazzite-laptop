/**
 * Cognitive Kernel Bridge
 *
 * Bridge to cognitum-gate-kernel for cognitive computation including
 * working memory, attention control, meta-cognition, and scaffolding.
 */
import type { WasmBridge, WasmModuleStatus, CognitiveConfig } from '../types.js';
/**
 * Cognitive item in working memory
 */
export interface CognitiveItem {
    id: string;
    content: Float32Array;
    salience: number;
    decay: number;
    associations: string[];
    metadata?: Record<string, unknown>;
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
 * Meta-cognitive assessment
 */
export interface MetaCognitiveAssessment {
    confidence: number;
    uncertainty: number;
    knowledgeGaps: string[];
    suggestedStrategies: string[];
    cognitiveLoad: number;
}
/**
 * Cognitive WASM module interface
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
 * Cognitive Kernel Bridge implementation
 */
export declare class CognitiveBridge implements WasmBridge<CognitiveModule> {
    readonly name = "cognitum-gate-kernel";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private config;
    constructor(config?: Partial<CognitiveConfig>);
    get status(): WasmModuleStatus;
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
     * Perform meta-cognitive assessment
     */
    assess(): MetaCognitiveAssessment;
    /**
     * Get scaffolding for task
     */
    scaffold(task: string, difficulty: number): string[];
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new cognitive bridge
 */
export declare function createCognitiveBridge(config?: Partial<CognitiveConfig>): CognitiveBridge;
export {};
//# sourceMappingURL=cognitive.d.ts.map