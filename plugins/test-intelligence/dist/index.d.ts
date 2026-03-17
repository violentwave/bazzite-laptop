/**
 * @claude-flow/plugin-test-intelligence
 *
 * AI-powered test intelligence plugin for Claude Flow V3.
 *
 * Features:
 * - Predictive test selection using reinforcement learning
 * - Flaky test detection and analysis
 * - Test coverage gap identification
 * - Mutation testing optimization
 * - Test case generation suggestions
 *
 * Uses RuVector WASM packages for high-performance analysis:
 * - ruvector-learning-wasm: RL-based test selection
 * - SONA: Continuous pattern learning
 * - micro-hnsw-wasm: Code-to-test similarity matching
 */
export * from './types.js';
export { selectPredictiveTool, flakyDetectTool, coverageGapsTool, mutationOptimizeTool, generateSuggestTool, testIntelligenceTools, } from './mcp-tools.js';
export { TestLearningBridge, createTestLearningBridge } from './bridges/learning-bridge.js';
export { TestSonaBridge, createTestSonaBridge } from './bridges/sona-bridge.js';
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
        testSelection: string;
        flakyDetection: string;
        coverageAnalysis: string;
        mutationOptimization: string;
        ciTimeReduction: string;
    };
};
export interface TestIntelligencePluginOptions {
    learningConfig?: {
        algorithm?: 'q-learning' | 'ppo' | 'decision-transformer';
        learningRate?: number;
        gamma?: number;
        batchSize?: number;
    };
    sonaConfig?: {
        mode?: 'real-time' | 'balanced' | 'research' | 'edge' | 'batch';
        loraRank?: number;
        learningRate?: number;
        ewcLambda?: number;
    };
    selection?: {
        defaultStrategy?: 'fast_feedback' | 'high_coverage' | 'risk_based' | 'balanced';
        defaultConfidence?: number;
        maxTests?: number;
    };
    flaky?: {
        historyDepth?: number;
        threshold?: number;
        quarantineEnabled?: boolean;
    };
}
/**
 * Initialize the test intelligence plugin
 */
export declare function initializePlugin(options?: TestIntelligencePluginOptions): Promise<{
    learningBridge: InstanceType<typeof import('./bridges/learning-bridge.js').TestLearningBridge>;
    sonaBridge: InstanceType<typeof import('./bridges/sona-bridge.js').TestSonaBridge>;
    tools: typeof import('./mcp-tools.js').testIntelligenceTools;
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
            testSelection: string;
            flakyDetection: string;
            coverageAnalysis: string;
            mutationOptimization: string;
            ciTimeReduction: string;
        };
    };
    initialize: typeof initializePlugin;
};
export default _default;
//# sourceMappingURL=index.d.ts.map