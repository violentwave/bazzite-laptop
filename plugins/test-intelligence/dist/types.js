/**
 * Test Intelligence Plugin - Type Definitions
 *
 * Types for predictive test selection, flaky detection, coverage analysis,
 * mutation testing optimization, and test generation.
 */
import { z } from 'zod';
export const DEFAULT_CONFIG = {
    selection: {
        defaultStrategy: 'balanced',
        defaultConfidence: 0.95,
        maxTests: 10000,
    },
    flaky: {
        historyDepth: 100,
        threshold: 0.1,
        quarantineEnabled: true,
    },
    coverage: {
        minCoverage: 80,
        prioritization: 'risk',
    },
    mutation: {
        defaultBudget: 1000,
        strategy: 'ml_guided',
    },
};
// ============================================================================
// Test Selection Types
// ============================================================================
export const SelectPredictiveInputSchema = z.object({
    changes: z.object({
        files: z.array(z.string().max(500)).max(1000).optional(),
        gitDiff: z.string().max(1_000_000).optional(),
        gitRef: z.string().max(100).optional(),
    }),
    strategy: z.enum(['fast_feedback', 'high_coverage', 'risk_based', 'balanced']).default('balanced'),
    budget: z.object({
        maxTests: z.number().int().min(1).max(100000).optional(),
        maxDuration: z.number().min(1).max(86400).optional(),
        confidence: z.number().min(0.5).max(1.0).default(0.95),
    }).optional(),
});
// ============================================================================
// Flaky Detection Types
// ============================================================================
export const FlakyDetectInputSchema = z.object({
    scope: z.object({
        testSuite: z.string().max(500).optional(),
        historyDepth: z.number().int().min(10).max(10000).default(100),
    }).optional(),
    analysis: z.array(z.enum([
        'intermittent_failures',
        'timing_sensitive',
        'order_dependent',
        'resource_contention',
        'environment_sensitive',
    ])).optional(),
    threshold: z.number().min(0.01).max(0.5).default(0.1),
});
// ============================================================================
// Coverage Gap Types
// ============================================================================
export const CoverageGapsInputSchema = z.object({
    targetPaths: z.array(z.string().max(500)).max(100).optional(),
    coverageType: z.enum(['line', 'branch', 'function', 'semantic']).default('semantic'),
    prioritization: z.enum(['risk', 'complexity', 'churn', 'recency']).default('risk'),
    minCoverage: z.number().min(0).max(100).default(80),
});
// ============================================================================
// Mutation Testing Types
// ============================================================================
export const MutationOptimizeInputSchema = z.object({
    targetPath: z.string().max(500),
    budget: z.number().int().min(1).max(10000).optional(),
    strategy: z.enum(['random', 'coverage_guided', 'ml_guided', 'historical']).default('ml_guided'),
    mutationTypes: z.array(z.enum([
        'arithmetic',
        'logical',
        'boundary',
        'null_check',
        'return_value',
    ])).optional(),
});
// ============================================================================
// Test Generation Types
// ============================================================================
export const GenerateSuggestInputSchema = z.object({
    targetFunction: z.string().max(500),
    testStyle: z.enum(['unit', 'integration', 'property_based', 'snapshot']).default('unit'),
    framework: z.enum(['jest', 'vitest', 'pytest', 'junit', 'mocha']).default('vitest'),
    edgeCases: z.boolean().default(true),
    mockStrategy: z.enum(['minimal', 'full', 'none']).optional(),
});
// ============================================================================
// Error Codes
// ============================================================================
export const TestIntelligenceErrorCodes = {
    BRIDGE_NOT_INITIALIZED: 'TI_BRIDGE_NOT_INITIALIZED',
    INVALID_INPUT: 'TI_INVALID_INPUT',
    NO_TEST_HISTORY: 'TI_NO_TEST_HISTORY',
    ANALYSIS_FAILED: 'TI_ANALYSIS_FAILED',
    TIMEOUT: 'TI_TIMEOUT',
    RATE_LIMITED: 'TI_RATE_LIMITED',
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