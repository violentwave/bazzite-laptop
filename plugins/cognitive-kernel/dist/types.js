/**
 * Cognitive Kernel Plugin - Type Definitions
 *
 * Types for cognitive augmentation including working memory, attention control,
 * meta-cognition, scaffolding, and cognitive load management.
 */
import { z } from 'zod';
// ============================================================================
// Working Memory Types
// ============================================================================
export const WorkingMemoryActionSchema = z.enum([
    'allocate',
    'update',
    'retrieve',
    'clear',
    'consolidate',
]);
export const ConsolidationTargetSchema = z.enum([
    'episodic',
    'semantic',
    'procedural',
]);
export const MemorySlotSchema = z.object({
    id: z.string().max(100).optional(),
    content: z.unknown().optional(),
    priority: z.number().min(0).max(1).default(0.5),
    decay: z.number().min(0).max(1).default(0.1),
});
export const WorkingMemoryInputSchema = z.object({
    action: WorkingMemoryActionSchema.describe('Memory action to perform'),
    slot: MemorySlotSchema.optional().describe('Memory slot data'),
    capacity: z.number().int().min(1).max(20).default(7)
        .describe('Working memory capacity (Miller number)'),
    consolidationTarget: ConsolidationTargetSchema.optional()
        .describe('Target memory system for consolidation'),
});
// ============================================================================
// Attention Control Types
// ============================================================================
export const AttentionModeSchema = z.enum([
    'focus',
    'diffuse',
    'selective',
    'divided',
    'sustained',
]);
export const AttentionTargetSchema = z.object({
    entity: z.string().max(500),
    weight: z.number().min(0).max(1),
    duration: z.number().min(0).max(3600),
});
export const AttentionFiltersSchema = z.object({
    includePatterns: z.array(z.string().max(200)).max(50).optional(),
    excludePatterns: z.array(z.string().max(200)).max(50).optional(),
    noveltyBias: z.number().min(0).max(1).default(0.5),
});
export const AttentionControlInputSchema = z.object({
    mode: AttentionModeSchema.describe('Attention mode'),
    targets: z.array(AttentionTargetSchema).max(50).optional()
        .describe('Attention targets with weights'),
    filters: AttentionFiltersSchema.optional()
        .describe('Attention filters'),
});
// ============================================================================
// Meta-Cognition Types
// ============================================================================
export const MonitoringTypeSchema = z.enum([
    'confidence_calibration',
    'reasoning_coherence',
    'goal_tracking',
    'cognitive_load',
    'error_detection',
    'uncertainty_estimation',
]);
export const ReflectionTriggerSchema = z.enum([
    'periodic',
    'on_error',
    'on_uncertainty',
]);
export const ReflectionDepthSchema = z.enum([
    'shallow',
    'medium',
    'deep',
]);
export const ReflectionSchema = z.object({
    trigger: ReflectionTriggerSchema.optional(),
    depth: ReflectionDepthSchema.optional(),
});
export const MetaMonitorInputSchema = z.object({
    monitoring: z.array(MonitoringTypeSchema).optional()
        .describe('Types of monitoring to perform'),
    reflection: ReflectionSchema.optional()
        .describe('Reflection configuration'),
    interventions: z.boolean().default(true)
        .describe('Allow automatic corrective interventions'),
});
// ============================================================================
// Scaffolding Types
// ============================================================================
export const TaskComplexitySchema = z.enum([
    'simple',
    'moderate',
    'complex',
    'expert',
]);
export const ScaffoldTypeSchema = z.enum([
    'decomposition',
    'analogy',
    'worked_example',
    'socratic',
    'metacognitive_prompting',
    'chain_of_thought',
]);
export const TaskSchema = z.object({
    description: z.string().max(5000),
    complexity: TaskComplexitySchema,
    domain: z.string().max(200).optional(),
});
export const AdaptivitySchema = z.object({
    fading: z.boolean().default(true),
    monitoring: z.boolean().default(true),
});
export const ScaffoldInputSchema = z.object({
    task: TaskSchema.describe('Task to scaffold'),
    scaffoldType: ScaffoldTypeSchema.describe('Type of scaffolding'),
    adaptivity: AdaptivitySchema.optional()
        .describe('Adaptivity settings'),
});
// ============================================================================
// Cognitive Load Types
// ============================================================================
export const LoadOptimizationSchema = z.enum([
    'reduce_extraneous',
    'chunk_intrinsic',
    'maximize_germane',
    'balanced',
]);
export const LoadAssessmentSchema = z.object({
    intrinsic: z.number().min(0).max(1).optional()
        .describe('Task complexity load'),
    extraneous: z.number().min(0).max(1).optional()
        .describe('Presentation complexity load'),
    germane: z.number().min(0).max(1).optional()
        .describe('Learning investment load'),
});
export const CognitiveLoadInputSchema = z.object({
    assessment: LoadAssessmentSchema.optional()
        .describe('Current load assessment'),
    optimization: LoadOptimizationSchema.default('balanced')
        .describe('Optimization strategy'),
    threshold: z.number().min(0).max(1).default(0.8)
        .describe('Maximum total load threshold'),
});
export const DEFAULT_CONFIG = {
    workingMemory: {
        defaultCapacity: 7,
        decayRate: 0.1,
        consolidationInterval: 60000,
    },
    attention: {
        defaultMode: 'focus',
        sustainedDuration: 300,
        noveltyBias: 0.5,
    },
    metaCognition: {
        reflectionInterval: 30000,
        confidenceThreshold: 0.7,
        interventionEnabled: true,
    },
    scaffolding: {
        fadingRate: 0.1,
        adaptationEnabled: true,
    },
    cognitiveLoad: {
        maxLoad: 0.8,
        warningThreshold: 0.6,
    },
};
// ============================================================================
// Helper Functions
// ============================================================================
/**
 * Create a successful MCP tool result
 */
export function successResult(data) {
    return {
        content: [{
                type: 'text',
                text: JSON.stringify(data, null, 2),
            }],
    };
}
/**
 * Create an error MCP tool result
 */
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
/**
 * Calculate cognitive load from components
 */
export function calculateTotalLoad(intrinsic, extraneous, germane) {
    // Cognitive load theory: total = intrinsic + extraneous + germane
    // But they compete for limited resources
    return Math.min(1, (intrinsic + extraneous + germane) / 2);
}
/**
 * Generate scaffolding steps based on complexity
 */
export function generateScaffoldSteps(complexity, scaffoldType) {
    const complexityMultiplier = {
        simple: 2,
        moderate: 4,
        complex: 6,
        expert: 8,
    };
    return complexityMultiplier[complexity];
}
//# sourceMappingURL=types.js.map