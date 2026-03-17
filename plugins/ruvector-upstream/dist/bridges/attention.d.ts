/**
 * Flash Attention Bridge
 *
 * Bridge to ruvector-attention-wasm for efficient attention computation.
 * Achieves 2.49x-7.47x speedup over standard attention.
 */
import type { WasmBridge, WasmModuleStatus, AttentionConfig } from '../types.js';
/**
 * Attention WASM module interface
 */
interface AttentionModule {
    flashAttention(query: Float32Array, key: Float32Array, value: Float32Array, config: AttentionConfig): Float32Array;
    multiHeadAttention(query: Float32Array, key: Float32Array, value: Float32Array, config: AttentionConfig): Float32Array;
    selfAttention(input: Float32Array, config: AttentionConfig): Float32Array;
}
/**
 * Flash Attention Bridge implementation
 */
export declare class AttentionBridge implements WasmBridge<AttentionModule> {
    readonly name = "ruvector-attention-wasm";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private config;
    constructor(config?: Partial<AttentionConfig>);
    get status(): WasmModuleStatus;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    getModule(): AttentionModule | null;
    /**
     * Compute flash attention
     */
    flashAttention(query: Float32Array, key: Float32Array, value: Float32Array, config?: Partial<AttentionConfig>): Float32Array;
    /**
     * Compute multi-head attention
     */
    multiHeadAttention(query: Float32Array, key: Float32Array, value: Float32Array, config?: Partial<AttentionConfig>): Float32Array;
    /**
     * Compute self-attention
     */
    selfAttention(input: Float32Array, config?: Partial<AttentionConfig>): Float32Array;
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new attention bridge
 */
export declare function createAttentionBridge(config?: Partial<AttentionConfig>): AttentionBridge;
export {};
//# sourceMappingURL=attention.d.ts.map