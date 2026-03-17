/**
 * RuVector WASM Types
 */
import { z } from 'zod';
/**
 * WASM module status
 */
export type WasmModuleStatus = 'unloaded' | 'loading' | 'ready' | 'error';
/**
 * Base WASM bridge interface
 */
export interface WasmBridge<T = unknown> {
    readonly name: string;
    readonly version: string;
    readonly status: WasmModuleStatus;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    getModule(): T | null;
}
/**
 * HNSW configuration
 */
export declare const HnswConfigSchema: z.ZodObject<{
    dimensions: z.ZodDefault<z.ZodNumber>;
    maxElements: z.ZodDefault<z.ZodNumber>;
    efConstruction: z.ZodDefault<z.ZodNumber>;
    M: z.ZodDefault<z.ZodNumber>;
    efSearch: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    dimensions: number;
    maxElements: number;
    efConstruction: number;
    M: number;
    efSearch: number;
}, {
    dimensions?: number | undefined;
    maxElements?: number | undefined;
    efConstruction?: number | undefined;
    M?: number | undefined;
    efSearch?: number | undefined;
}>;
export type HnswConfig = z.infer<typeof HnswConfigSchema>;
/**
 * Vector search result
 */
export interface SearchResult {
    id: string;
    score: number;
    vector?: Float32Array;
    metadata?: Record<string, unknown>;
}
/**
 * Flash attention configuration
 */
export declare const AttentionConfigSchema: z.ZodObject<{
    headDim: z.ZodDefault<z.ZodNumber>;
    numHeads: z.ZodDefault<z.ZodNumber>;
    seqLength: z.ZodDefault<z.ZodNumber>;
    causal: z.ZodDefault<z.ZodBoolean>;
    dropout: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    headDim: number;
    numHeads: number;
    seqLength: number;
    causal: boolean;
    dropout: number;
}, {
    headDim?: number | undefined;
    numHeads?: number | undefined;
    seqLength?: number | undefined;
    causal?: boolean | undefined;
    dropout?: number | undefined;
}>;
export type AttentionConfig = z.infer<typeof AttentionConfigSchema>;
/**
 * GNN configuration
 */
export declare const GnnConfigSchema: z.ZodObject<{
    inputDim: z.ZodDefault<z.ZodNumber>;
    hiddenDim: z.ZodDefault<z.ZodNumber>;
    outputDim: z.ZodDefault<z.ZodNumber>;
    numLayers: z.ZodDefault<z.ZodNumber>;
    aggregation: z.ZodDefault<z.ZodEnum<["mean", "sum", "max", "attention"]>>;
}, "strip", z.ZodTypeAny, {
    inputDim: number;
    hiddenDim: number;
    outputDim: number;
    numLayers: number;
    aggregation: "mean" | "sum" | "max" | "attention";
}, {
    inputDim?: number | undefined;
    hiddenDim?: number | undefined;
    outputDim?: number | undefined;
    numLayers?: number | undefined;
    aggregation?: "mean" | "sum" | "max" | "attention" | undefined;
}>;
export type GnnConfig = z.infer<typeof GnnConfigSchema>;
/**
 * Hyperbolic embedding configuration
 */
export declare const HyperbolicConfigSchema: z.ZodObject<{
    dimensions: z.ZodDefault<z.ZodNumber>;
    curvature: z.ZodDefault<z.ZodNumber>;
    model: z.ZodDefault<z.ZodEnum<["poincare", "lorentz", "klein"]>>;
}, "strip", z.ZodTypeAny, {
    dimensions: number;
    curvature: number;
    model: "poincare" | "lorentz" | "klein";
}, {
    dimensions?: number | undefined;
    curvature?: number | undefined;
    model?: "poincare" | "lorentz" | "klein" | undefined;
}>;
export type HyperbolicConfig = z.infer<typeof HyperbolicConfigSchema>;
/**
 * Reinforcement learning configuration
 */
export declare const LearningConfigSchema: z.ZodObject<{
    algorithm: z.ZodDefault<z.ZodEnum<["q-learning", "sarsa", "actor-critic", "ppo", "dqn", "decision-transformer"]>>;
    learningRate: z.ZodDefault<z.ZodNumber>;
    gamma: z.ZodDefault<z.ZodNumber>;
    batchSize: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    algorithm: "q-learning" | "sarsa" | "actor-critic" | "ppo" | "dqn" | "decision-transformer";
    learningRate: number;
    gamma: number;
    batchSize: number;
}, {
    algorithm?: "q-learning" | "sarsa" | "actor-critic" | "ppo" | "dqn" | "decision-transformer" | undefined;
    learningRate?: number | undefined;
    gamma?: number | undefined;
    batchSize?: number | undefined;
}>;
export type LearningConfig = z.infer<typeof LearningConfigSchema>;
/**
 * Quantum-inspired optimization configuration
 */
export declare const ExoticConfigSchema: z.ZodObject<{
    algorithm: z.ZodDefault<z.ZodEnum<["qaoa", "vqe", "grover", "quantum-annealing", "tensor-network"]>>;
    numQubits: z.ZodDefault<z.ZodNumber>;
    depth: z.ZodDefault<z.ZodNumber>;
    shots: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    algorithm: "qaoa" | "vqe" | "grover" | "quantum-annealing" | "tensor-network";
    numQubits: number;
    depth: number;
    shots: number;
}, {
    algorithm?: "qaoa" | "vqe" | "grover" | "quantum-annealing" | "tensor-network" | undefined;
    numQubits?: number | undefined;
    depth?: number | undefined;
    shots?: number | undefined;
}>;
export type ExoticConfig = z.infer<typeof ExoticConfigSchema>;
/**
 * Cognitive kernel configuration
 */
export declare const CognitiveConfigSchema: z.ZodObject<{
    workingMemorySize: z.ZodDefault<z.ZodNumber>;
    attentionSpan: z.ZodDefault<z.ZodNumber>;
    metaCognitionEnabled: z.ZodDefault<z.ZodBoolean>;
    scaffoldingLevel: z.ZodDefault<z.ZodEnum<["none", "light", "moderate", "heavy"]>>;
}, "strip", z.ZodTypeAny, {
    workingMemorySize: number;
    attentionSpan: number;
    metaCognitionEnabled: boolean;
    scaffoldingLevel: "none" | "light" | "moderate" | "heavy";
}, {
    workingMemorySize?: number | undefined;
    attentionSpan?: number | undefined;
    metaCognitionEnabled?: boolean | undefined;
    scaffoldingLevel?: "none" | "light" | "moderate" | "heavy" | undefined;
}>;
export type CognitiveConfig = z.infer<typeof CognitiveConfigSchema>;
/**
 * SONA (Self-Optimizing Neural Architecture) configuration
 */
export declare const SonaConfigSchema: z.ZodObject<{
    mode: z.ZodDefault<z.ZodEnum<["real-time", "balanced", "research", "edge", "batch"]>>;
    loraRank: z.ZodDefault<z.ZodNumber>;
    learningRate: z.ZodDefault<z.ZodNumber>;
    ewcLambda: z.ZodDefault<z.ZodNumber>;
    batchSize: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    learningRate: number;
    batchSize: number;
    mode: "real-time" | "balanced" | "research" | "edge" | "batch";
    loraRank: number;
    ewcLambda: number;
}, {
    learningRate?: number | undefined;
    batchSize?: number | undefined;
    mode?: "real-time" | "balanced" | "research" | "edge" | "batch" | undefined;
    loraRank?: number | undefined;
    ewcLambda?: number | undefined;
}>;
export type SonaConfig = z.infer<typeof SonaConfigSchema>;
//# sourceMappingURL=types.d.ts.map