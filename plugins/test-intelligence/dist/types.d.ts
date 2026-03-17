/**
 * Test Intelligence Plugin - Type Definitions
 *
 * Types for predictive test selection, flaky detection, coverage analysis,
 * mutation testing optimization, and test generation.
 */
import { z } from 'zod';
export interface MCPToolInputSchema {
    type: 'object';
    properties: Record<string, unknown>;
    required?: string[];
}
export interface MCPToolResult {
    content: Array<{
        type: 'text' | 'image' | 'resource';
        text?: string;
        data?: string;
        mimeType?: string;
    }>;
    isError?: boolean;
}
export interface MCPTool {
    name: string;
    description: string;
    inputSchema: MCPToolInputSchema;
    category?: string;
    tags?: string[];
    version?: string;
    cacheable?: boolean;
    cacheTTL?: number;
    handler: (input: Record<string, unknown>, context?: ToolContext) => Promise<MCPToolResult>;
}
export interface ToolContext {
    learningBridge?: LearningBridgeInterface;
    sonaBridge?: SonaBridgeInterface;
    config?: TestIntelligenceConfig;
    logger?: Logger;
}
export interface Logger {
    debug(message: string, meta?: Record<string, unknown>): void;
    info(message: string, meta?: Record<string, unknown>): void;
    warn(message: string, meta?: Record<string, unknown>): void;
    error(message: string, meta?: Record<string, unknown>): void;
}
export interface TestIntelligenceConfig {
    selection: {
        defaultStrategy: 'fast_feedback' | 'high_coverage' | 'risk_based' | 'balanced';
        defaultConfidence: number;
        maxTests: number;
    };
    flaky: {
        historyDepth: number;
        threshold: number;
        quarantineEnabled: boolean;
    };
    coverage: {
        minCoverage: number;
        prioritization: 'risk' | 'complexity' | 'churn' | 'recency';
    };
    mutation: {
        defaultBudget: number;
        strategy: 'random' | 'coverage_guided' | 'ml_guided' | 'historical';
    };
}
export declare const DEFAULT_CONFIG: TestIntelligenceConfig;
/**
 * Test result from a single test execution
 */
export interface TestResult {
    testId: string;
    testName: string;
    suite: string;
    status: 'passed' | 'failed' | 'skipped' | 'flaky';
    duration: number;
    timestamp: number;
    error?: string;
    stackTrace?: string;
    retries?: number;
}
/**
 * Test history entry for learning
 */
export interface TestHistoryEntry {
    testId: string;
    results: TestResult[];
    failureRate: number;
    avgDuration: number;
    lastModified: number;
    affectedFiles: string[];
}
/**
 * Test execution pattern for RL
 */
export interface TestExecutionPattern {
    embedding: Float32Array;
    successRate: number;
    avgDuration: number;
    codeChanges: string[];
    selectedTests: string[];
    actualFailures: string[];
}
/**
 * Code change information
 */
export interface CodeChange {
    file: string;
    type: 'added' | 'modified' | 'deleted';
    linesAdded: number;
    linesRemoved: number;
    hunks?: CodeHunk[];
}
/**
 * Code hunk from diff
 */
export interface CodeHunk {
    oldStart: number;
    oldLines: number;
    newStart: number;
    newLines: number;
    content: string;
}
export declare const SelectPredictiveInputSchema: z.ZodObject<{
    changes: z.ZodObject<{
        files: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        gitDiff: z.ZodOptional<z.ZodString>;
        gitRef: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        files?: string[] | undefined;
        gitDiff?: string | undefined;
        gitRef?: string | undefined;
    }, {
        files?: string[] | undefined;
        gitDiff?: string | undefined;
        gitRef?: string | undefined;
    }>;
    strategy: z.ZodDefault<z.ZodEnum<["fast_feedback", "high_coverage", "risk_based", "balanced"]>>;
    budget: z.ZodOptional<z.ZodObject<{
        maxTests: z.ZodOptional<z.ZodNumber>;
        maxDuration: z.ZodOptional<z.ZodNumber>;
        confidence: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        confidence: number;
        maxTests?: number | undefined;
        maxDuration?: number | undefined;
    }, {
        maxTests?: number | undefined;
        maxDuration?: number | undefined;
        confidence?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    changes: {
        files?: string[] | undefined;
        gitDiff?: string | undefined;
        gitRef?: string | undefined;
    };
    strategy: "fast_feedback" | "high_coverage" | "risk_based" | "balanced";
    budget?: {
        confidence: number;
        maxTests?: number | undefined;
        maxDuration?: number | undefined;
    } | undefined;
}, {
    changes: {
        files?: string[] | undefined;
        gitDiff?: string | undefined;
        gitRef?: string | undefined;
    };
    strategy?: "fast_feedback" | "high_coverage" | "risk_based" | "balanced" | undefined;
    budget?: {
        maxTests?: number | undefined;
        maxDuration?: number | undefined;
        confidence?: number | undefined;
    } | undefined;
}>;
export type SelectPredictiveInput = z.infer<typeof SelectPredictiveInputSchema>;
export interface SelectPredictiveOutput {
    selectedTests: SelectedTest[];
    totalTests: number;
    estimatedDuration: number;
    confidence: number;
    strategy: string;
    details: {
        filesAnalyzed: number;
        testsSkipped: number;
        coverageEstimate: number;
        riskScore: number;
        interpretation: string;
    };
}
export interface SelectedTest {
    testId: string;
    testName: string;
    suite: string;
    priority: number;
    reason: string;
    estimatedDuration: number;
    failureProbability: number;
}
export declare const FlakyDetectInputSchema: z.ZodObject<{
    scope: z.ZodOptional<z.ZodObject<{
        testSuite: z.ZodOptional<z.ZodString>;
        historyDepth: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        historyDepth: number;
        testSuite?: string | undefined;
    }, {
        testSuite?: string | undefined;
        historyDepth?: number | undefined;
    }>>;
    analysis: z.ZodOptional<z.ZodArray<z.ZodEnum<["intermittent_failures", "timing_sensitive", "order_dependent", "resource_contention", "environment_sensitive"]>, "many">>;
    threshold: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    threshold: number;
    scope?: {
        historyDepth: number;
        testSuite?: string | undefined;
    } | undefined;
    analysis?: ("intermittent_failures" | "timing_sensitive" | "order_dependent" | "resource_contention" | "environment_sensitive")[] | undefined;
}, {
    scope?: {
        testSuite?: string | undefined;
        historyDepth?: number | undefined;
    } | undefined;
    analysis?: ("intermittent_failures" | "timing_sensitive" | "order_dependent" | "resource_contention" | "environment_sensitive")[] | undefined;
    threshold?: number | undefined;
}>;
export type FlakyDetectInput = z.infer<typeof FlakyDetectInputSchema>;
export interface FlakyDetectOutput {
    flakyTests: FlakyTest[];
    totalAnalyzed: number;
    flakinessScore: number;
    details: {
        intermittentCount: number;
        timingSensitiveCount: number;
        orderDependentCount: number;
        resourceContentionCount: number;
        environmentSensitiveCount: number;
        recommendations: string[];
    };
}
export interface FlakyTest {
    testId: string;
    testName: string;
    suite: string;
    flakinessScore: number;
    flakinessType: FlakinessType[];
    failurePattern: string;
    lastFlaky: number;
    suggestedFix: string;
}
export type FlakinessType = 'intermittent_failures' | 'timing_sensitive' | 'order_dependent' | 'resource_contention' | 'environment_sensitive';
export declare const CoverageGapsInputSchema: z.ZodObject<{
    targetPaths: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    coverageType: z.ZodDefault<z.ZodEnum<["line", "branch", "function", "semantic"]>>;
    prioritization: z.ZodDefault<z.ZodEnum<["risk", "complexity", "churn", "recency"]>>;
    minCoverage: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    coverageType: "function" | "line" | "branch" | "semantic";
    prioritization: "risk" | "complexity" | "churn" | "recency";
    minCoverage: number;
    targetPaths?: string[] | undefined;
}, {
    targetPaths?: string[] | undefined;
    coverageType?: "function" | "line" | "branch" | "semantic" | undefined;
    prioritization?: "risk" | "complexity" | "churn" | "recency" | undefined;
    minCoverage?: number | undefined;
}>;
export type CoverageGapsInput = z.infer<typeof CoverageGapsInputSchema>;
export interface CoverageGapsOutput {
    gaps: CoverageGap[];
    overallCoverage: number;
    targetCoverage: number;
    details: {
        filesAnalyzed: number;
        uncoveredLines: number;
        uncoveredBranches: number;
        uncoveredFunctions: number;
        priorityDistribution: Record<string, number>;
        interpretation: string;
    };
}
export interface CoverageGap {
    file: string;
    uncoveredLines: number[];
    uncoveredBranches: number[];
    uncoveredFunctions: string[];
    coverage: number;
    priority: 'critical' | 'high' | 'medium' | 'low';
    riskScore: number;
    complexity: number;
    churnScore: number;
    suggestedTests: string[];
}
export declare const MutationOptimizeInputSchema: z.ZodObject<{
    targetPath: z.ZodString;
    budget: z.ZodOptional<z.ZodNumber>;
    strategy: z.ZodDefault<z.ZodEnum<["random", "coverage_guided", "ml_guided", "historical"]>>;
    mutationTypes: z.ZodOptional<z.ZodArray<z.ZodEnum<["arithmetic", "logical", "boundary", "null_check", "return_value"]>, "many">>;
}, "strip", z.ZodTypeAny, {
    strategy: "random" | "coverage_guided" | "ml_guided" | "historical";
    targetPath: string;
    budget?: number | undefined;
    mutationTypes?: ("arithmetic" | "logical" | "boundary" | "null_check" | "return_value")[] | undefined;
}, {
    targetPath: string;
    strategy?: "random" | "coverage_guided" | "ml_guided" | "historical" | undefined;
    budget?: number | undefined;
    mutationTypes?: ("arithmetic" | "logical" | "boundary" | "null_check" | "return_value")[] | undefined;
}>;
export type MutationOptimizeInput = z.infer<typeof MutationOptimizeInputSchema>;
export interface MutationOptimizeOutput {
    mutations: OptimizedMutation[];
    mutationScore: number;
    survivingMutants: number;
    killedMutants: number;
    details: {
        totalMutations: number;
        budgetUsed: number;
        timeEstimate: number;
        coverageImprovement: number;
        weakTests: string[];
        interpretation: string;
    };
}
export interface OptimizedMutation {
    id: string;
    file: string;
    line: number;
    type: MutationType;
    original: string;
    mutated: string;
    status: 'killed' | 'survived' | 'pending' | 'timeout';
    killingTests: string[];
    priority: number;
}
export type MutationType = 'arithmetic' | 'logical' | 'boundary' | 'null_check' | 'return_value';
export declare const GenerateSuggestInputSchema: z.ZodObject<{
    targetFunction: z.ZodString;
    testStyle: z.ZodDefault<z.ZodEnum<["unit", "integration", "property_based", "snapshot"]>>;
    framework: z.ZodDefault<z.ZodEnum<["jest", "vitest", "pytest", "junit", "mocha"]>>;
    edgeCases: z.ZodDefault<z.ZodBoolean>;
    mockStrategy: z.ZodOptional<z.ZodEnum<["minimal", "full", "none"]>>;
}, "strip", z.ZodTypeAny, {
    targetFunction: string;
    testStyle: "unit" | "integration" | "property_based" | "snapshot";
    framework: "jest" | "vitest" | "pytest" | "junit" | "mocha";
    edgeCases: boolean;
    mockStrategy?: "minimal" | "full" | "none" | undefined;
}, {
    targetFunction: string;
    testStyle?: "unit" | "integration" | "property_based" | "snapshot" | undefined;
    framework?: "jest" | "vitest" | "pytest" | "junit" | "mocha" | undefined;
    edgeCases?: boolean | undefined;
    mockStrategy?: "minimal" | "full" | "none" | undefined;
}>;
export type GenerateSuggestInput = z.infer<typeof GenerateSuggestInputSchema>;
export interface GenerateSuggestOutput {
    suggestions: TestSuggestion[];
    coverage: {
        statements: number;
        branches: number;
        functions: number;
    };
    details: {
        functionComplexity: number;
        parametersAnalyzed: number;
        edgeCasesFound: number;
        mockObjectsNeeded: string[];
        interpretation: string;
    };
}
export interface TestSuggestion {
    name: string;
    description: string;
    category: 'happy_path' | 'edge_case' | 'error_handling' | 'boundary' | 'integration';
    code: string;
    priority: number;
    coverageGain: number;
    dependencies: string[];
}
export interface LearningBridgeInterface {
    readonly name: string;
    readonly version: string;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    trainOnHistory(history: TestHistoryEntry[], config?: LearningConfig): Promise<number>;
    predictFailingTests(changes: CodeChange[], topK: number): Promise<PredictedTest[]>;
    updatePolicyWithFeedback(feedback: TestFeedback): Promise<void>;
}
export interface SonaBridgeInterface {
    readonly name: string;
    readonly version: string;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    learnPatterns(patterns: TestExecutionPattern[]): Promise<number>;
    findSimilarPatterns(query: Float32Array, k: number): Promise<TestExecutionPattern[]>;
    storePattern(pattern: TestExecutionPattern): Promise<void>;
}
export interface LearningConfig {
    algorithm: 'q-learning' | 'ppo' | 'decision-transformer';
    learningRate: number;
    gamma: number;
    batchSize: number;
}
export interface PredictedTest {
    testId: string;
    failureProbability: number;
    confidence: number;
    reason: string;
}
export interface TestFeedback {
    predictions: PredictedTest[];
    actualResults: TestResult[];
    reward: number;
}
export declare const TestIntelligenceErrorCodes: {
    readonly BRIDGE_NOT_INITIALIZED: "TI_BRIDGE_NOT_INITIALIZED";
    readonly INVALID_INPUT: "TI_INVALID_INPUT";
    readonly NO_TEST_HISTORY: "TI_NO_TEST_HISTORY";
    readonly ANALYSIS_FAILED: "TI_ANALYSIS_FAILED";
    readonly TIMEOUT: "TI_TIMEOUT";
    readonly RATE_LIMITED: "TI_RATE_LIMITED";
};
export type TestIntelligenceErrorCode = (typeof TestIntelligenceErrorCodes)[keyof typeof TestIntelligenceErrorCodes];
export declare function successResult(data: unknown): MCPToolResult;
export declare function errorResult(error: Error | string): MCPToolResult;
//# sourceMappingURL=types.d.ts.map