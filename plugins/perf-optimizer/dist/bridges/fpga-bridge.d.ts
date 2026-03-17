/**
 * FPGA Transformer Bridge for Performance Optimizer
 *
 * Provides fast configuration optimization using FPGA-accelerated
 * transformer inference from ruvector-fpga-transformer-wasm.
 */
import type { FpgaBridgeInterface, WorkloadProfile, ConfigOptimization } from '../types.js';
/**
 * FPGA transformer configuration
 */
interface FpgaConfig {
    modelSize: 'small' | 'medium' | 'large';
    searchIterations: number;
    explorationRate: number;
    bayesianOptimization: boolean;
}
/**
 * FPGA Transformer Bridge Implementation
 *
 * Uses FPGA-accelerated transformers for:
 * - Configuration space exploration
 * - Performance prediction
 * - Optimal configuration search
 */
export declare class PerfFpgaBridge implements FpgaBridgeInterface {
    readonly name = "perf-optimizer-fpga";
    readonly version = "0.1.0";
    private status;
    private config;
    private performanceModel;
    private configHistory;
    private baselinePerformance;
    constructor(config?: Partial<FpgaConfig>);
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    /**
     * Optimize configuration for workload
     *
     * Uses SONA-based learning to find optimal configuration parameters.
     */
    optimizeConfig(workload: WorkloadProfile, configSpace: Record<string, unknown>): Promise<ConfigOptimization>;
    /**
     * Predict performance for configuration
     *
     * Uses the learned performance model to estimate performance metrics.
     */
    predictPerformance(config: Record<string, unknown>, workload: WorkloadProfile): Promise<number>;
    /**
     * Search for optimal configuration
     *
     * Uses Bayesian optimization or grid search to find the best configuration.
     */
    searchOptimalConfig(objective: string, constraints: Record<string, number>): Promise<Record<string, unknown>>;
    /**
     * Learn from performance feedback
     */
    learnFromFeedback(config: Record<string, unknown>, actualPerformance: number): void;
    private initializePerformanceModel;
    private optimizeParameter;
    private getOptimalRatio;
    private suggestBooleanConfig;
    private suggestEnumConfig;
    private predictImprovement;
    private getWorkloadBaseline;
    private getParameterImpact;
    private embedConfig;
    private embeddingToKey;
    private defineSearchSpace;
    private bayesianSearch;
    private gridSearch;
    private getBestHistoricalValue;
    private evaluateConfig;
    private hashString;
}
/**
 * Create a new FPGA bridge instance
 */
export declare function createPerfFpgaBridge(config?: Partial<FpgaConfig>): PerfFpgaBridge;
export {};
//# sourceMappingURL=fpga-bridge.d.ts.map