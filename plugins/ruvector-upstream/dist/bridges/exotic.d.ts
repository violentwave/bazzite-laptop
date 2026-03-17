/**
 * Quantum-Inspired Optimization Bridge
 *
 * Bridge to ruvector-exotic-wasm for quantum-inspired algorithms including
 * QAOA, VQE, Grover search, quantum annealing, and tensor networks.
 */
import type { WasmBridge, WasmModuleStatus, ExoticConfig } from '../types.js';
/**
 * Optimization problem definition
 */
export interface OptimizationProblem {
    type: 'qubo' | 'maxcut' | 'maxsat' | 'tsp' | 'scheduling';
    variables: number;
    constraints: Array<{
        coefficients: Float32Array;
        operator: 'eq' | 'le' | 'ge';
        rhs: number;
    }>;
    objective: Float32Array;
}
/**
 * Optimization result
 */
export interface OptimizationResult {
    solution: Float32Array;
    energy: number;
    iterations: number;
    converged: boolean;
    confidence: number;
}
/**
 * Exotic WASM module interface
 */
interface ExoticModule {
    qaoa(problem: OptimizationProblem, config: ExoticConfig): OptimizationResult;
    vqe(problem: OptimizationProblem, config: ExoticConfig): OptimizationResult;
    quantumAnnealing(problem: OptimizationProblem, config: ExoticConfig): OptimizationResult;
    groverSearch(oracle: (input: Uint8Array) => boolean, searchSpace: number, config: ExoticConfig): Uint8Array | null;
    tensorContract(tensors: Float32Array[], contractionOrder: Array<[number, number]>): Float32Array;
    amplitudeEstimation(statePrep: Float32Array, groverIterations: number): number;
}
/**
 * Quantum-Inspired Optimization Bridge implementation
 */
export declare class ExoticBridge implements WasmBridge<ExoticModule> {
    readonly name = "ruvector-exotic-wasm";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private config;
    constructor(config?: Partial<ExoticConfig>);
    get status(): WasmModuleStatus;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    getModule(): ExoticModule | null;
    /**
     * Solve optimization problem with QAOA
     */
    qaoa(problem: OptimizationProblem, config?: Partial<ExoticConfig>): OptimizationResult;
    /**
     * Solve optimization problem with VQE
     */
    vqe(problem: OptimizationProblem, config?: Partial<ExoticConfig>): OptimizationResult;
    /**
     * Solve optimization problem with quantum annealing
     */
    quantumAnnealing(problem: OptimizationProblem, config?: Partial<ExoticConfig>): OptimizationResult;
    /**
     * Grover search algorithm
     */
    groverSearch(oracle: (input: Uint8Array) => boolean, searchSpace: number, config?: Partial<ExoticConfig>): Uint8Array | null;
    /**
     * Tensor network contraction
     */
    tensorContract(tensors: Float32Array[], contractionOrder: Array<[number, number]>): Float32Array;
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new exotic bridge
 */
export declare function createExoticBridge(config?: Partial<ExoticConfig>): ExoticBridge;
export {};
//# sourceMappingURL=exotic.d.ts.map