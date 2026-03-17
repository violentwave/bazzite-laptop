/**
 * @claude-flow/plugin-perf-optimizer
 *
 * AI-powered performance optimization plugin for Claude Flow V3.
 *
 * Features:
 * - Bottleneck detection using trace analysis
 * - Memory leak detection and analysis
 * - Database query optimization (N+1, missing indexes)
 * - JavaScript bundle optimization
 * - Configuration tuning with SONA learning
 *
 * Uses RuVector WASM packages for high-performance analysis:
 * - ruvector-sparse-inference-wasm: Efficient trace processing
 * - ruvector-fpga-transformer-wasm: Fast configuration optimization
 * - ruvector-gnn-wasm: Dependency chain analysis
 */
export * from './types.js';
export { bottleneckDetectTool, memoryAnalyzeTool, queryOptimizeTool, bundleOptimizeTool, configOptimizeTool, perfOptimizerTools, } from './mcp-tools.js';
export { PerfSparseBridge, createPerfSparseBridge } from './bridges/sparse-bridge.js';
export { PerfFpgaBridge, createPerfFpgaBridge } from './bridges/fpga-bridge.js';
export declare const pluginMetadata: {
    name: string;
    version: string;
    description: string;
    category: string;
    tags: string[];
    author: string;
    license: string;
    repository: string;
    engines: {
        'claude-flow': string;
        node: string;
    };
    capabilities: {
        mcpTools: string[];
        bridges: string[];
        wasmPackages: string[];
    };
    performanceTargets: {
        traceAnalysis: string;
        memoryAnalysis: string;
        queryPatternDetection: string;
        bundleAnalysis: string;
        configOptimization: string;
    };
    supportedFormats: {
        tracing: string[];
        profiling: string[];
        memory: string[];
        bundles: string[];
    };
};
export interface PerfOptimizerPluginOptions {
    sparseConfig?: {
        maxDimensions?: number;
        sparsityRatio?: number;
        hashBuckets?: number;
    };
    fpgaConfig?: {
        modelSize?: 'small' | 'medium' | 'large';
        searchIterations?: number;
        explorationRate?: number;
        bayesianOptimization?: boolean;
    };
    bottleneck?: {
        latencyThresholdMs?: number;
        errorRateThreshold?: number;
        cpuThreshold?: number;
        memoryThreshold?: number;
    };
    memory?: {
        leakThresholdMb?: number;
        gcPressureThreshold?: number;
        maxHeapSize?: number;
    };
    query?: {
        slowQueryThresholdMs?: number;
        maxResultSize?: number;
        indexSuggestionEnabled?: boolean;
    };
    bundle?: {
        maxSizeKb?: number;
        treeshakingEnabled?: boolean;
        codeSplittingEnabled?: boolean;
    };
}
/**
 * Initialize the performance optimizer plugin
 */
export declare function initializePlugin(options?: PerfOptimizerPluginOptions): Promise<{
    sparseBridge: InstanceType<typeof import('./bridges/sparse-bridge.js').PerfSparseBridge>;
    fpgaBridge: InstanceType<typeof import('./bridges/fpga-bridge.js').PerfFpgaBridge>;
    tools: typeof import('./mcp-tools.js').perfOptimizerTools;
}>;
/**
 * Plugin entry point for Claude Flow plugin loader
 */
declare const _default: {
    metadata: {
        name: string;
        version: string;
        description: string;
        category: string;
        tags: string[];
        author: string;
        license: string;
        repository: string;
        engines: {
            'claude-flow': string;
            node: string;
        };
        capabilities: {
            mcpTools: string[];
            bridges: string[];
            wasmPackages: string[];
        };
        performanceTargets: {
            traceAnalysis: string;
            memoryAnalysis: string;
            queryPatternDetection: string;
            bundleAnalysis: string;
            configOptimization: string;
        };
        supportedFormats: {
            tracing: string[];
            profiling: string[];
            memory: string[];
            bundles: string[];
        };
    };
    initialize: typeof initializePlugin;
};
export default _default;
//# sourceMappingURL=index.d.ts.map