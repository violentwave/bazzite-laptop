/**
 * Performance Optimizer Plugin - Type Definitions
 *
 * Types for bottleneck detection, memory analysis, query optimization,
 * bundle optimization, and configuration tuning.
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
    sparseBridge?: SparseBridgeInterface;
    fpgaBridge?: FpgaBridgeInterface;
    config?: PerfOptimizerConfig;
    logger?: Logger;
}
export interface Logger {
    debug(message: string, meta?: Record<string, unknown>): void;
    info(message: string, meta?: Record<string, unknown>): void;
    warn(message: string, meta?: Record<string, unknown>): void;
    error(message: string, meta?: Record<string, unknown>): void;
}
export interface PerfOptimizerConfig {
    bottleneck: {
        latencyThresholdMs: number;
        errorRateThreshold: number;
        cpuThreshold: number;
        memoryThreshold: number;
    };
    memory: {
        leakThresholdMb: number;
        gcPressureThreshold: number;
        maxHeapSize: number;
    };
    query: {
        slowQueryThresholdMs: number;
        maxResultSize: number;
        indexSuggestionEnabled: boolean;
    };
    bundle: {
        maxSizeKb: number;
        treeshakingEnabled: boolean;
        codeSplittingEnabled: boolean;
    };
}
export declare const DEFAULT_CONFIG: PerfOptimizerConfig;
/**
 * Span from distributed trace
 */
export interface TraceSpan {
    traceId: string;
    spanId: string;
    parentSpanId?: string;
    operationName: string;
    serviceName: string;
    startTime: number;
    duration: number;
    status: 'ok' | 'error' | 'timeout';
    attributes: Record<string, unknown>;
    events?: SpanEvent[];
}
/**
 * Span event
 */
export interface SpanEvent {
    name: string;
    timestamp: number;
    attributes?: Record<string, unknown>;
}
/**
 * Trace data container
 */
export interface TraceData {
    format: 'otlp' | 'chrome_devtools' | 'jaeger' | 'zipkin';
    spans: TraceSpan[];
    metrics?: Record<string, number>;
}
/**
 * Bottleneck detection result
 */
export interface Bottleneck {
    id: string;
    type: BottleneckType;
    severity: 'critical' | 'high' | 'medium' | 'low';
    location: string;
    description: string;
    impact: {
        latencyMs: number;
        throughput: number;
        errorRate: number;
    };
    suggestedFix: string;
    relatedSpans: string[];
}
export type BottleneckType = 'cpu' | 'memory' | 'io' | 'network' | 'database' | 'render' | 'lock_contention' | 'gc_pressure';
/**
 * Heap snapshot summary
 */
export interface HeapSnapshot {
    totalSize: number;
    usedSize: number;
    objects: HeapObject[];
    retainers: RetainerPath[];
}
/**
 * Heap object
 */
export interface HeapObject {
    name: string;
    type: string;
    size: number;
    count: number;
    shallowSize: number;
    retainedSize: number;
}
/**
 * Retainer path for memory leak detection
 */
export interface RetainerPath {
    object: string;
    path: string[];
    retainedSize: number;
    distance: number;
}
/**
 * Memory timeline point
 */
export interface MemoryTimelinePoint {
    timestamp: number;
    heapUsed: number;
    heapTotal: number;
    external: number;
    arrayBuffers: number;
}
/**
 * Memory leak detection result
 */
export interface MemoryLeak {
    id: string;
    type: MemoryLeakType;
    severity: 'critical' | 'high' | 'medium' | 'low';
    object: string;
    retainedSize: number;
    growthRate: number;
    retainerPath: string[];
    suggestedFix: string;
}
export type MemoryLeakType = 'detached_dom' | 'closure_leak' | 'event_listener' | 'timer_leak' | 'global_variable' | 'cache_unbounded';
/**
 * Database query info
 */
export interface QueryInfo {
    sql: string;
    duration: number;
    stackTrace?: string;
    resultSize?: number;
    explain?: QueryExplainPlan;
}
/**
 * Query explain plan
 */
export interface QueryExplainPlan {
    type: string;
    table: string;
    rows: number;
    filtered: number;
    extra?: string;
    key?: string;
    possibleKeys?: string[];
}
/**
 * Query pattern detection
 */
export interface QueryPattern {
    id: string;
    type: QueryPatternType;
    severity: 'critical' | 'high' | 'medium' | 'low';
    queries: string[];
    count: number;
    totalDuration: number;
    suggestedFix: string;
    suggestedIndex?: IndexSuggestion;
}
export type QueryPatternType = 'n_plus_1' | 'missing_index' | 'full_scan' | 'large_result' | 'slow_join' | 'duplicate_query';
/**
 * Index suggestion
 */
export interface IndexSuggestion {
    table: string;
    columns: string[];
    type: 'btree' | 'hash' | 'gin' | 'gist';
    estimatedImprovement: number;
    createStatement: string;
}
/**
 * Bundle stats
 */
export interface BundleStats {
    totalSize: number;
    chunks: BundleChunk[];
    modules: BundleModule[];
    assets: BundleAsset[];
}
/**
 * Bundle chunk
 */
export interface BundleChunk {
    name: string;
    size: number;
    modules: string[];
    initial: boolean;
    entry: boolean;
}
/**
 * Bundle module
 */
export interface BundleModule {
    name: string;
    size: number;
    chunks: string[];
    issuers: string[];
    reasons: string[];
    usedExports?: string[];
    providedExports?: string[];
}
/**
 * Bundle asset
 */
export interface BundleAsset {
    name: string;
    size: number;
    chunks: string[];
}
/**
 * Bundle optimization suggestion
 */
export interface BundleOptimization {
    id: string;
    type: BundleOptimizationType;
    severity: 'critical' | 'high' | 'medium' | 'low';
    target: string;
    currentSize: number;
    potentialSavings: number;
    description: string;
    suggestedFix: string;
}
export type BundleOptimizationType = 'tree_shaking' | 'code_splitting' | 'duplicate_deps' | 'large_modules' | 'dynamic_import' | 'polyfill_reduction';
/**
 * Workload profile
 */
export interface WorkloadProfile {
    type: 'web' | 'api' | 'batch' | 'stream' | 'hybrid';
    metrics: {
        requestsPerSecond: number;
        avgResponseTime: number;
        errorRate: number;
        concurrency: number;
    };
    constraints: {
        maxLatency?: number;
        maxMemory?: number;
        maxCpu?: number;
        maxCost?: number;
    };
}
/**
 * Configuration parameter
 */
export interface ConfigParameter {
    name: string;
    type: 'number' | 'boolean' | 'string' | 'enum';
    current: unknown;
    suggested: unknown;
    range?: [number, number];
    options?: string[];
    impact: number;
    confidence: number;
}
/**
 * Configuration optimization result
 */
export interface ConfigOptimization {
    parameters: ConfigParameter[];
    objective: 'latency' | 'throughput' | 'cost' | 'balanced';
    predictedImprovement: {
        latency: number;
        throughput: number;
        cost: number;
    };
    confidence: number;
    warnings: string[];
}
export declare const BottleneckDetectInputSchema: z.ZodObject<{
    traceData: z.ZodObject<{
        format: z.ZodEnum<["otlp", "chrome_devtools", "jaeger", "zipkin"]>;
        spans: z.ZodArray<z.ZodUnknown, "many">;
        metrics: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    }, "strip", z.ZodTypeAny, {
        format: "otlp" | "chrome_devtools" | "jaeger" | "zipkin";
        spans: unknown[];
        metrics?: Record<string, unknown> | undefined;
    }, {
        format: "otlp" | "chrome_devtools" | "jaeger" | "zipkin";
        spans: unknown[];
        metrics?: Record<string, unknown> | undefined;
    }>;
    analysisScope: z.ZodDefault<z.ZodArray<z.ZodEnum<["cpu", "memory", "io", "network", "database", "render", "all"]>, "many">>;
    threshold: z.ZodOptional<z.ZodObject<{
        latencyP95: z.ZodOptional<z.ZodNumber>;
        throughput: z.ZodOptional<z.ZodNumber>;
        errorRate: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        throughput?: number | undefined;
        latencyP95?: number | undefined;
        errorRate?: number | undefined;
    }, {
        throughput?: number | undefined;
        latencyP95?: number | undefined;
        errorRate?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    traceData: {
        format: "otlp" | "chrome_devtools" | "jaeger" | "zipkin";
        spans: unknown[];
        metrics?: Record<string, unknown> | undefined;
    };
    analysisScope: ("cpu" | "memory" | "io" | "network" | "database" | "render" | "all")[];
    threshold?: {
        throughput?: number | undefined;
        latencyP95?: number | undefined;
        errorRate?: number | undefined;
    } | undefined;
}, {
    traceData: {
        format: "otlp" | "chrome_devtools" | "jaeger" | "zipkin";
        spans: unknown[];
        metrics?: Record<string, unknown> | undefined;
    };
    analysisScope?: ("cpu" | "memory" | "io" | "network" | "database" | "render" | "all")[] | undefined;
    threshold?: {
        throughput?: number | undefined;
        latencyP95?: number | undefined;
        errorRate?: number | undefined;
    } | undefined;
}>;
export type BottleneckDetectInput = z.infer<typeof BottleneckDetectInputSchema>;
export declare const MemoryAnalyzeInputSchema: z.ZodObject<{
    heapSnapshot: z.ZodOptional<z.ZodString>;
    timeline: z.ZodOptional<z.ZodArray<z.ZodUnknown, "many">>;
    analysis: z.ZodOptional<z.ZodArray<z.ZodEnum<["leak_detection", "retention_analysis", "allocation_hotspots", "gc_pressure"]>, "many">>;
    compareBaseline: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    heapSnapshot?: string | undefined;
    timeline?: unknown[] | undefined;
    analysis?: ("gc_pressure" | "leak_detection" | "retention_analysis" | "allocation_hotspots")[] | undefined;
    compareBaseline?: string | undefined;
}, {
    heapSnapshot?: string | undefined;
    timeline?: unknown[] | undefined;
    analysis?: ("gc_pressure" | "leak_detection" | "retention_analysis" | "allocation_hotspots")[] | undefined;
    compareBaseline?: string | undefined;
}>;
export type MemoryAnalyzeInput = z.infer<typeof MemoryAnalyzeInputSchema>;
export declare const QueryOptimizeInputSchema: z.ZodObject<{
    queries: z.ZodArray<z.ZodObject<{
        sql: z.ZodString;
        duration: z.ZodNumber;
        stackTrace: z.ZodOptional<z.ZodString>;
        resultSize: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        sql: string;
        duration: number;
        stackTrace?: string | undefined;
        resultSize?: number | undefined;
    }, {
        sql: string;
        duration: number;
        stackTrace?: string | undefined;
        resultSize?: number | undefined;
    }>, "many">;
    patterns: z.ZodOptional<z.ZodArray<z.ZodEnum<["n_plus_1", "missing_index", "full_scan", "large_result", "slow_join"]>, "many">>;
    suggestIndexes: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    queries: {
        sql: string;
        duration: number;
        stackTrace?: string | undefined;
        resultSize?: number | undefined;
    }[];
    suggestIndexes: boolean;
    patterns?: ("n_plus_1" | "missing_index" | "full_scan" | "large_result" | "slow_join")[] | undefined;
}, {
    queries: {
        sql: string;
        duration: number;
        stackTrace?: string | undefined;
        resultSize?: number | undefined;
    }[];
    patterns?: ("n_plus_1" | "missing_index" | "full_scan" | "large_result" | "slow_join")[] | undefined;
    suggestIndexes?: boolean | undefined;
}>;
export type QueryOptimizeInput = z.infer<typeof QueryOptimizeInputSchema>;
export declare const BundleOptimizeInputSchema: z.ZodObject<{
    bundleStats: z.ZodString;
    analysis: z.ZodOptional<z.ZodArray<z.ZodEnum<["tree_shaking", "code_splitting", "duplicate_deps", "large_modules", "dynamic_import"]>, "many">>;
    targets: z.ZodOptional<z.ZodObject<{
        maxSize: z.ZodOptional<z.ZodNumber>;
        maxChunks: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        maxSize?: number | undefined;
        maxChunks?: number | undefined;
    }, {
        maxSize?: number | undefined;
        maxChunks?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    bundleStats: string;
    analysis?: ("tree_shaking" | "code_splitting" | "duplicate_deps" | "large_modules" | "dynamic_import")[] | undefined;
    targets?: {
        maxSize?: number | undefined;
        maxChunks?: number | undefined;
    } | undefined;
}, {
    bundleStats: string;
    analysis?: ("tree_shaking" | "code_splitting" | "duplicate_deps" | "large_modules" | "dynamic_import")[] | undefined;
    targets?: {
        maxSize?: number | undefined;
        maxChunks?: number | undefined;
    } | undefined;
}>;
export type BundleOptimizeInput = z.infer<typeof BundleOptimizeInputSchema>;
export declare const ConfigOptimizeInputSchema: z.ZodObject<{
    workloadProfile: z.ZodObject<{
        type: z.ZodEnum<["web", "api", "batch", "stream", "hybrid"]>;
        metrics: z.ZodOptional<z.ZodObject<{
            requestsPerSecond: z.ZodOptional<z.ZodNumber>;
            avgResponseTime: z.ZodOptional<z.ZodNumber>;
            errorRate: z.ZodOptional<z.ZodNumber>;
            concurrency: z.ZodOptional<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            errorRate?: number | undefined;
            requestsPerSecond?: number | undefined;
            avgResponseTime?: number | undefined;
            concurrency?: number | undefined;
        }, {
            errorRate?: number | undefined;
            requestsPerSecond?: number | undefined;
            avgResponseTime?: number | undefined;
            concurrency?: number | undefined;
        }>>;
        constraints: z.ZodOptional<z.ZodObject<{
            maxLatency: z.ZodOptional<z.ZodNumber>;
            maxMemory: z.ZodOptional<z.ZodNumber>;
            maxCpu: z.ZodOptional<z.ZodNumber>;
            maxCost: z.ZodOptional<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            maxLatency?: number | undefined;
            maxMemory?: number | undefined;
            maxCpu?: number | undefined;
            maxCost?: number | undefined;
        }, {
            maxLatency?: number | undefined;
            maxMemory?: number | undefined;
            maxCpu?: number | undefined;
            maxCost?: number | undefined;
        }>>;
    }, "strip", z.ZodTypeAny, {
        type: "web" | "api" | "batch" | "stream" | "hybrid";
        metrics?: {
            errorRate?: number | undefined;
            requestsPerSecond?: number | undefined;
            avgResponseTime?: number | undefined;
            concurrency?: number | undefined;
        } | undefined;
        constraints?: {
            maxLatency?: number | undefined;
            maxMemory?: number | undefined;
            maxCpu?: number | undefined;
            maxCost?: number | undefined;
        } | undefined;
    }, {
        type: "web" | "api" | "batch" | "stream" | "hybrid";
        metrics?: {
            errorRate?: number | undefined;
            requestsPerSecond?: number | undefined;
            avgResponseTime?: number | undefined;
            concurrency?: number | undefined;
        } | undefined;
        constraints?: {
            maxLatency?: number | undefined;
            maxMemory?: number | undefined;
            maxCpu?: number | undefined;
            maxCost?: number | undefined;
        } | undefined;
    }>;
    configSpace: z.ZodRecord<z.ZodString, z.ZodObject<{
        type: z.ZodString;
        range: z.ZodOptional<z.ZodArray<z.ZodUnknown, "many">>;
        current: z.ZodUnknown;
    }, "strip", z.ZodTypeAny, {
        type: string;
        range?: unknown[] | undefined;
        current?: unknown;
    }, {
        type: string;
        range?: unknown[] | undefined;
        current?: unknown;
    }>>;
    objective: z.ZodEnum<["latency", "throughput", "cost", "balanced"]>;
}, "strip", z.ZodTypeAny, {
    workloadProfile: {
        type: "web" | "api" | "batch" | "stream" | "hybrid";
        metrics?: {
            errorRate?: number | undefined;
            requestsPerSecond?: number | undefined;
            avgResponseTime?: number | undefined;
            concurrency?: number | undefined;
        } | undefined;
        constraints?: {
            maxLatency?: number | undefined;
            maxMemory?: number | undefined;
            maxCpu?: number | undefined;
            maxCost?: number | undefined;
        } | undefined;
    };
    configSpace: Record<string, {
        type: string;
        range?: unknown[] | undefined;
        current?: unknown;
    }>;
    objective: "latency" | "throughput" | "cost" | "balanced";
}, {
    workloadProfile: {
        type: "web" | "api" | "batch" | "stream" | "hybrid";
        metrics?: {
            errorRate?: number | undefined;
            requestsPerSecond?: number | undefined;
            avgResponseTime?: number | undefined;
            concurrency?: number | undefined;
        } | undefined;
        constraints?: {
            maxLatency?: number | undefined;
            maxMemory?: number | undefined;
            maxCpu?: number | undefined;
            maxCost?: number | undefined;
        } | undefined;
    };
    configSpace: Record<string, {
        type: string;
        range?: unknown[] | undefined;
        current?: unknown;
    }>;
    objective: "latency" | "throughput" | "cost" | "balanced";
}>;
export type ConfigOptimizeInput = z.infer<typeof ConfigOptimizeInputSchema>;
export interface BottleneckDetectOutput {
    bottlenecks: Bottleneck[];
    criticalPath: string[];
    overallScore: number;
    details: {
        spanCount: number;
        analysisScope: string[];
        p50Latency: number;
        p95Latency: number;
        p99Latency: number;
        errorRate: number;
        interpretation: string;
    };
}
export interface MemoryAnalyzeOutput {
    leaks: MemoryLeak[];
    hotspots: HeapObject[];
    gcPressure: number;
    details: {
        heapUsed: number;
        heapTotal: number;
        objectCount: number;
        analysisType: string[];
        interpretation: string;
    };
}
export interface QueryOptimizeOutput {
    patterns: QueryPattern[];
    optimizations: IndexSuggestion[];
    totalQueries: number;
    details: {
        slowQueries: number;
        nPlusOneCount: number;
        missingIndexCount: number;
        estimatedImprovement: number;
        interpretation: string;
    };
}
export interface BundleOptimizeOutput {
    optimizations: BundleOptimization[];
    totalSize: number;
    potentialSavings: number;
    details: {
        chunkCount: number;
        moduleCount: number;
        duplicateDeps: string[];
        largestModules: string[];
        interpretation: string;
    };
}
export interface ConfigOptimizeOutput {
    recommendations: ConfigParameter[];
    objective: string;
    predictedImprovement: {
        latency: number;
        throughput: number;
        cost: number;
    };
    details: {
        parametersAnalyzed: number;
        optimizationsFound: number;
        confidence: number;
        warnings: string[];
        interpretation: string;
    };
}
export interface SparseBridgeInterface {
    readonly name: string;
    readonly version: string;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    encodeTraces(spans: TraceSpan[]): Promise<Float32Array>;
    detectAnomalies(encoded: Float32Array, threshold: number): Promise<number[]>;
    analyzeCriticalPath(encoded: Float32Array): Promise<string[]>;
}
export interface FpgaBridgeInterface {
    readonly name: string;
    readonly version: string;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    optimizeConfig(workload: WorkloadProfile, configSpace: Record<string, unknown>): Promise<ConfigOptimization>;
    predictPerformance(config: Record<string, unknown>, workload: WorkloadProfile): Promise<number>;
    searchOptimalConfig(objective: string, constraints: Record<string, number>): Promise<Record<string, unknown>>;
}
export declare const PerfOptimizerErrorCodes: {
    readonly BRIDGE_NOT_INITIALIZED: "PO_BRIDGE_NOT_INITIALIZED";
    readonly INVALID_INPUT: "PO_INVALID_INPUT";
    readonly TRACE_PARSE_ERROR: "PO_TRACE_PARSE_ERROR";
    readonly ANALYSIS_FAILED: "PO_ANALYSIS_FAILED";
    readonly TIMEOUT: "PO_TIMEOUT";
    readonly RATE_LIMITED: "PO_RATE_LIMITED";
};
export type PerfOptimizerErrorCode = (typeof PerfOptimizerErrorCodes)[keyof typeof PerfOptimizerErrorCodes];
export declare function successResult(data: unknown): MCPToolResult;
export declare function errorResult(error: Error | string): MCPToolResult;
//# sourceMappingURL=types.d.ts.map