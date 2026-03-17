/**
 * Performance Optimizer Plugin - Type Definitions
 *
 * Types for bottleneck detection, memory analysis, query optimization,
 * bundle optimization, and configuration tuning.
 */
import { z } from 'zod';
export const DEFAULT_CONFIG = {
    bottleneck: {
        latencyThresholdMs: 100,
        errorRateThreshold: 0.01,
        cpuThreshold: 80,
        memoryThreshold: 85,
    },
    memory: {
        leakThresholdMb: 50,
        gcPressureThreshold: 0.3,
        maxHeapSize: 2048,
    },
    query: {
        slowQueryThresholdMs: 100,
        maxResultSize: 10000,
        indexSuggestionEnabled: true,
    },
    bundle: {
        maxSizeKb: 500,
        treeshakingEnabled: true,
        codeSplittingEnabled: true,
    },
};
// ============================================================================
// Input Schemas
// ============================================================================
export const BottleneckDetectInputSchema = z.object({
    traceData: z.object({
        format: z.enum(['otlp', 'chrome_devtools', 'jaeger', 'zipkin']),
        spans: z.array(z.unknown()).max(1_000_000),
        metrics: z.record(z.string(), z.unknown()).optional(),
    }),
    analysisScope: z.array(z.enum(['cpu', 'memory', 'io', 'network', 'database', 'render', 'all'])).default(['all']),
    threshold: z.object({
        latencyP95: z.number().min(0).max(86400000).optional(),
        throughput: z.number().min(0).optional(),
        errorRate: z.number().min(0).max(1).optional(),
    }).optional(),
});
export const MemoryAnalyzeInputSchema = z.object({
    heapSnapshot: z.string().max(500).optional(),
    timeline: z.array(z.unknown()).max(100000).optional(),
    analysis: z.array(z.enum([
        'leak_detection',
        'retention_analysis',
        'allocation_hotspots',
        'gc_pressure',
    ])).optional(),
    compareBaseline: z.string().max(500).optional(),
});
export const QueryOptimizeInputSchema = z.object({
    queries: z.array(z.object({
        sql: z.string().max(10000),
        duration: z.number().min(0).max(86400000),
        stackTrace: z.string().max(50000).optional(),
        resultSize: z.number().int().min(0).optional(),
    })).min(1).max(10000),
    patterns: z.array(z.enum(['n_plus_1', 'missing_index', 'full_scan', 'large_result', 'slow_join'])).optional(),
    suggestIndexes: z.boolean().default(true),
});
export const BundleOptimizeInputSchema = z.object({
    bundleStats: z.string().max(500),
    analysis: z.array(z.enum([
        'tree_shaking',
        'code_splitting',
        'duplicate_deps',
        'large_modules',
        'dynamic_import',
    ])).optional(),
    targets: z.object({
        maxSize: z.number().min(0).optional(),
        maxChunks: z.number().int().min(1).optional(),
    }).optional(),
});
export const ConfigOptimizeInputSchema = z.object({
    workloadProfile: z.object({
        type: z.enum(['web', 'api', 'batch', 'stream', 'hybrid']),
        metrics: z.object({
            requestsPerSecond: z.number().min(0).optional(),
            avgResponseTime: z.number().min(0).optional(),
            errorRate: z.number().min(0).max(1).optional(),
            concurrency: z.number().int().min(1).optional(),
        }).optional(),
        constraints: z.object({
            maxLatency: z.number().min(0).optional(),
            maxMemory: z.number().min(0).optional(),
            maxCpu: z.number().min(0).max(100).optional(),
            maxCost: z.number().min(0).optional(),
        }).optional(),
    }),
    configSpace: z.record(z.string(), z.object({
        type: z.string(),
        range: z.array(z.unknown()).optional(),
        current: z.unknown(),
    })),
    objective: z.enum(['latency', 'throughput', 'cost', 'balanced']),
});
// ============================================================================
// Error Codes
// ============================================================================
export const PerfOptimizerErrorCodes = {
    BRIDGE_NOT_INITIALIZED: 'PO_BRIDGE_NOT_INITIALIZED',
    INVALID_INPUT: 'PO_INVALID_INPUT',
    TRACE_PARSE_ERROR: 'PO_TRACE_PARSE_ERROR',
    ANALYSIS_FAILED: 'PO_ANALYSIS_FAILED',
    TIMEOUT: 'PO_TIMEOUT',
    RATE_LIMITED: 'PO_RATE_LIMITED',
};
// ============================================================================
// Helper Functions
// ============================================================================
export function successResult(data) {
    return {
        content: [{
                type: 'text',
                text: JSON.stringify(data, null, 2),
            }],
    };
}
export function errorResult(error) {
    const message = error instanceof Error ? error.message : error;
    return {
        content: [{
                type: 'text',
                text: JSON.stringify({
                    error: true,
                    message,
                    timestamp: new Date().toISOString(),
                }, null, 2),
            }],
        isError: true,
    };
}
//# sourceMappingURL=types.js.map