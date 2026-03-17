/**
 * Causal Engine - Do-Calculus Inference
 *
 * Implements causal inference using Pearl's do-calculus.
 * Supports interventional queries, confounder identification,
 * and backdoor path analysis.
 *
 * Based on: https://arxiv.org/abs/1305.5506 (Do-Calculus)
 */
import type { ICausalEngine, CausalResult, CausalEffect, CausalGraph, Intervention, WasmModule } from '../types.js';
/**
 * CausalEngine - WASM wrapper for causal inference operations
 */
export declare class CausalEngine implements ICausalEngine {
    private wasmModule;
    private readonly significanceThreshold;
    constructor(wasmModule?: WasmModule);
    /**
     * Set the WASM module after initialization
     */
    setWasmModule(module: WasmModule): void;
    /**
     * Perform causal inference using do-calculus
     *
     * @param intervention - Intervention specification
     * @returns CausalResult with effect estimation
     */
    infer(intervention: Intervention): Promise<CausalResult>;
    /**
     * Compute causal effect using do-calculus
     * P(Y | do(X)) estimation
     *
     * @param graph - Causal graph
     * @param treatment - Treatment variable
     * @param outcome - Outcome variable
     * @returns CausalEffect with confidence
     */
    computeDoCalculus(graph: CausalGraph, treatment: string, outcome: string): Promise<CausalEffect>;
    /**
     * Identify confounders between treatment and outcome
     *
     * @param graph - Causal graph
     * @param treatment - Treatment variable
     * @param outcome - Outcome variable
     * @returns Array of confounder variable names
     */
    identifyConfounders(graph: CausalGraph, treatment: string, outcome: string): string[];
    /**
     * Find all backdoor paths from treatment to outcome
     *
     * @param graph - Causal graph
     * @param treatment - Treatment variable
     * @param outcome - Outcome variable
     * @returns Array of paths (each path is array of node names)
     */
    findBackdoorPaths(graph: CausalGraph, treatment: string, outcome: string): string[][];
    /**
     * Create CausalEffect value object
     */
    createCausalEffect(value: number, confidence: number): CausalEffect;
    /**
     * Validate if an intervention is valid (backdoor criterion satisfied)
     */
    private validateIntervention;
    /**
     * Pure JS implementation of causal effect estimation
     */
    private computeEffectJS;
    /**
     * Compute confidence based on graph structure
     */
    private computeConfidence;
    /**
     * Convert graph to adjacency matrix
     */
    private graphToAdjMatrix;
    /**
     * Get parent nodes (direct causes)
     */
    private getParents;
    /**
     * Get ancestors (all causes)
     */
    private getAncestors;
    /**
     * Get descendants (all effects)
     */
    private getDescendants;
    /**
     * Check if there's a direct edge from source to target
     */
    private hasDirectEdge;
    /**
     * Check if there's a path from source to target
     */
    private hasPathTo;
    /**
     * Find all paths from source to target
     */
    private findAllPaths;
}
//# sourceMappingURL=CausalEngine.d.ts.map