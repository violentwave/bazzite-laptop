/**
 * Exotic Bridge - Quantum-Inspired Optimization Algorithms
 *
 * Bridge to @ruvector/exotic-wasm for quantum-inspired optimization
 * including simulated quantum annealing, QAOA emulation, and Grover search.
 */
import type { QUBOProblem, AnnealingConfig, AnnealingResult, ProblemGraph, QAOACircuit, QAOAResult, SearchSpace, AmplificationConfig, GroverResult } from '../types.js';
/**
 * WASM module status
 */
export type WasmModuleStatus = 'unloaded' | 'loading' | 'ready' | 'error';
/**
 * Quantum-Inspired Exotic Bridge
 */
export declare class ExoticBridge {
    readonly name = "quantum-exotic-bridge";
    readonly version = "0.1.0";
    private _status;
    private _module;
    get status(): WasmModuleStatus;
    get initialized(): boolean;
    /**
     * Initialize the WASM module
     */
    initialize(): Promise<void>;
    /**
     * Dispose of resources
     */
    dispose(): Promise<void>;
    /**
     * Solve a QUBO problem using simulated quantum annealing
     */
    solveQubo(problem: QUBOProblem, config?: Partial<AnnealingConfig>): Promise<AnnealingResult>;
    /**
     * Run QAOA optimization
     */
    runQaoa(graph: ProblemGraph, circuit?: Partial<QAOACircuit>): Promise<QAOAResult>;
    /**
     * Grover-inspired search
     */
    groverSearch(space: SearchSpace, config?: Partial<AmplificationConfig>): Promise<GroverResult>;
    private validateQuboProblem;
    private validateProblemGraph;
    private simulatedAnnealing;
    private computeEnergy;
    private updateTemperature;
    private evaluateQaoaCircuit;
    private computeCutValue;
    private estimateGradient;
    private estimateOptimalCut;
    private parseOracle;
    private weightedSample;
    private indexToBits;
    private arraysEqual;
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new ExoticBridge instance
 */
export declare function createExoticBridge(): ExoticBridge;
//# sourceMappingURL=exotic-bridge.d.ts.map