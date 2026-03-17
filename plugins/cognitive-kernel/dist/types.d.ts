/**
 * Cognitive Kernel Plugin - Type Definitions
 *
 * Types for cognitive augmentation including working memory, attention control,
 * meta-cognition, scaffolding, and cognitive load management.
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
    cognitiveBridge?: CognitiveBridgeInterface;
    sonaBridge?: SonaBridgeInterface;
    config?: CognitiveKernelConfig;
    logger?: Logger;
}
export interface Logger {
    debug(message: string, meta?: Record<string, unknown>): void;
    info(message: string, meta?: Record<string, unknown>): void;
    warn(message: string, meta?: Record<string, unknown>): void;
    error(message: string, meta?: Record<string, unknown>): void;
}
export declare const WorkingMemoryActionSchema: z.ZodEnum<["allocate", "update", "retrieve", "clear", "consolidate"]>;
export type WorkingMemoryAction = z.infer<typeof WorkingMemoryActionSchema>;
export declare const ConsolidationTargetSchema: z.ZodEnum<["episodic", "semantic", "procedural"]>;
export type ConsolidationTarget = z.infer<typeof ConsolidationTargetSchema>;
export declare const MemorySlotSchema: z.ZodObject<{
    id: z.ZodOptional<z.ZodString>;
    content: z.ZodOptional<z.ZodUnknown>;
    priority: z.ZodDefault<z.ZodNumber>;
    decay: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    priority: number;
    decay: number;
    id?: string | undefined;
    content?: unknown;
}, {
    id?: string | undefined;
    content?: unknown;
    priority?: number | undefined;
    decay?: number | undefined;
}>;
export type MemorySlot = z.infer<typeof MemorySlotSchema>;
export declare const WorkingMemoryInputSchema: z.ZodObject<{
    action: z.ZodEnum<["allocate", "update", "retrieve", "clear", "consolidate"]>;
    slot: z.ZodOptional<z.ZodObject<{
        id: z.ZodOptional<z.ZodString>;
        content: z.ZodOptional<z.ZodUnknown>;
        priority: z.ZodDefault<z.ZodNumber>;
        decay: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        priority: number;
        decay: number;
        id?: string | undefined;
        content?: unknown;
    }, {
        id?: string | undefined;
        content?: unknown;
        priority?: number | undefined;
        decay?: number | undefined;
    }>>;
    capacity: z.ZodDefault<z.ZodNumber>;
    consolidationTarget: z.ZodOptional<z.ZodEnum<["episodic", "semantic", "procedural"]>>;
}, "strip", z.ZodTypeAny, {
    action: "allocate" | "update" | "retrieve" | "clear" | "consolidate";
    capacity: number;
    slot?: {
        priority: number;
        decay: number;
        id?: string | undefined;
        content?: unknown;
    } | undefined;
    consolidationTarget?: "episodic" | "semantic" | "procedural" | undefined;
}, {
    action: "allocate" | "update" | "retrieve" | "clear" | "consolidate";
    slot?: {
        id?: string | undefined;
        content?: unknown;
        priority?: number | undefined;
        decay?: number | undefined;
    } | undefined;
    capacity?: number | undefined;
    consolidationTarget?: "episodic" | "semantic" | "procedural" | undefined;
}>;
export type WorkingMemoryInput = z.infer<typeof WorkingMemoryInputSchema>;
export interface WorkingMemorySlot {
    id: string;
    content: unknown;
    priority: number;
    decay: number;
    createdAt: number;
    accessCount: number;
    lastAccessed: number;
}
export interface WorkingMemoryState {
    slots: WorkingMemorySlot[];
    capacity: number;
    utilization: number;
    avgPriority: number;
}
export interface WorkingMemoryOutput {
    action: WorkingMemoryAction;
    success: boolean;
    state: {
        slotsUsed: number;
        capacity: number;
        utilization: number;
    };
    details: {
        slotId?: string;
        content?: unknown;
        avgPriority: number;
        interpretation: string;
    };
}
export declare const AttentionModeSchema: z.ZodEnum<["focus", "diffuse", "selective", "divided", "sustained"]>;
export type AttentionMode = z.infer<typeof AttentionModeSchema>;
export declare const AttentionTargetSchema: z.ZodObject<{
    entity: z.ZodString;
    weight: z.ZodNumber;
    duration: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    entity: string;
    weight: number;
    duration: number;
}, {
    entity: string;
    weight: number;
    duration: number;
}>;
export type AttentionTarget = z.infer<typeof AttentionTargetSchema>;
export declare const AttentionFiltersSchema: z.ZodObject<{
    includePatterns: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    excludePatterns: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    noveltyBias: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    noveltyBias: number;
    includePatterns?: string[] | undefined;
    excludePatterns?: string[] | undefined;
}, {
    includePatterns?: string[] | undefined;
    excludePatterns?: string[] | undefined;
    noveltyBias?: number | undefined;
}>;
export type AttentionFilters = z.infer<typeof AttentionFiltersSchema>;
export declare const AttentionControlInputSchema: z.ZodObject<{
    mode: z.ZodEnum<["focus", "diffuse", "selective", "divided", "sustained"]>;
    targets: z.ZodOptional<z.ZodArray<z.ZodObject<{
        entity: z.ZodString;
        weight: z.ZodNumber;
        duration: z.ZodNumber;
    }, "strip", z.ZodTypeAny, {
        entity: string;
        weight: number;
        duration: number;
    }, {
        entity: string;
        weight: number;
        duration: number;
    }>, "many">>;
    filters: z.ZodOptional<z.ZodObject<{
        includePatterns: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        excludePatterns: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
        noveltyBias: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        noveltyBias: number;
        includePatterns?: string[] | undefined;
        excludePatterns?: string[] | undefined;
    }, {
        includePatterns?: string[] | undefined;
        excludePatterns?: string[] | undefined;
        noveltyBias?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    mode: "focus" | "diffuse" | "selective" | "divided" | "sustained";
    targets?: {
        entity: string;
        weight: number;
        duration: number;
    }[] | undefined;
    filters?: {
        noveltyBias: number;
        includePatterns?: string[] | undefined;
        excludePatterns?: string[] | undefined;
    } | undefined;
}, {
    mode: "focus" | "diffuse" | "selective" | "divided" | "sustained";
    targets?: {
        entity: string;
        weight: number;
        duration: number;
    }[] | undefined;
    filters?: {
        includePatterns?: string[] | undefined;
        excludePatterns?: string[] | undefined;
        noveltyBias?: number | undefined;
    } | undefined;
}>;
export type AttentionControlInput = z.infer<typeof AttentionControlInputSchema>;
export interface AttentionState {
    mode: AttentionMode;
    focus: string[];
    breadth: number;
    intensity: number;
    filters: AttentionFilters;
    distractors: string[];
}
export interface AttentionControlOutput {
    mode: AttentionMode;
    state: {
        focus: string[];
        breadth: number;
        intensity: number;
    };
    details: {
        targetsActive: number;
        filterPatterns: number;
        interpretation: string;
    };
}
export declare const MonitoringTypeSchema: z.ZodEnum<["confidence_calibration", "reasoning_coherence", "goal_tracking", "cognitive_load", "error_detection", "uncertainty_estimation"]>;
export type MonitoringType = z.infer<typeof MonitoringTypeSchema>;
export declare const ReflectionTriggerSchema: z.ZodEnum<["periodic", "on_error", "on_uncertainty"]>;
export type ReflectionTrigger = z.infer<typeof ReflectionTriggerSchema>;
export declare const ReflectionDepthSchema: z.ZodEnum<["shallow", "medium", "deep"]>;
export type ReflectionDepth = z.infer<typeof ReflectionDepthSchema>;
export declare const ReflectionSchema: z.ZodObject<{
    trigger: z.ZodOptional<z.ZodEnum<["periodic", "on_error", "on_uncertainty"]>>;
    depth: z.ZodOptional<z.ZodEnum<["shallow", "medium", "deep"]>>;
}, "strip", z.ZodTypeAny, {
    trigger?: "periodic" | "on_error" | "on_uncertainty" | undefined;
    depth?: "shallow" | "medium" | "deep" | undefined;
}, {
    trigger?: "periodic" | "on_error" | "on_uncertainty" | undefined;
    depth?: "shallow" | "medium" | "deep" | undefined;
}>;
export type Reflection = z.infer<typeof ReflectionSchema>;
export declare const MetaMonitorInputSchema: z.ZodObject<{
    monitoring: z.ZodOptional<z.ZodArray<z.ZodEnum<["confidence_calibration", "reasoning_coherence", "goal_tracking", "cognitive_load", "error_detection", "uncertainty_estimation"]>, "many">>;
    reflection: z.ZodOptional<z.ZodObject<{
        trigger: z.ZodOptional<z.ZodEnum<["periodic", "on_error", "on_uncertainty"]>>;
        depth: z.ZodOptional<z.ZodEnum<["shallow", "medium", "deep"]>>;
    }, "strip", z.ZodTypeAny, {
        trigger?: "periodic" | "on_error" | "on_uncertainty" | undefined;
        depth?: "shallow" | "medium" | "deep" | undefined;
    }, {
        trigger?: "periodic" | "on_error" | "on_uncertainty" | undefined;
        depth?: "shallow" | "medium" | "deep" | undefined;
    }>>;
    interventions: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    interventions: boolean;
    monitoring?: ("confidence_calibration" | "reasoning_coherence" | "goal_tracking" | "cognitive_load" | "error_detection" | "uncertainty_estimation")[] | undefined;
    reflection?: {
        trigger?: "periodic" | "on_error" | "on_uncertainty" | undefined;
        depth?: "shallow" | "medium" | "deep" | undefined;
    } | undefined;
}, {
    monitoring?: ("confidence_calibration" | "reasoning_coherence" | "goal_tracking" | "cognitive_load" | "error_detection" | "uncertainty_estimation")[] | undefined;
    reflection?: {
        trigger?: "periodic" | "on_error" | "on_uncertainty" | undefined;
        depth?: "shallow" | "medium" | "deep" | undefined;
    } | undefined;
    interventions?: boolean | undefined;
}>;
export type MetaMonitorInput = z.infer<typeof MetaMonitorInputSchema>;
export interface MetaCognitiveAssessment {
    confidence: number;
    uncertainty: number;
    coherence: number;
    cognitiveLoad: number;
    errorsDetected: number;
    knowledgeGaps: string[];
    suggestedStrategies: string[];
}
export interface MetaMonitorOutput {
    assessment: {
        confidence: number;
        uncertainty: number;
        coherence: number;
        cognitiveLoad: number;
    };
    interventions: string[];
    details: {
        monitoringTypes: MonitoringType[];
        reflectionDepth: ReflectionDepth | null;
        errorsDetected: number;
        interpretation: string;
    };
}
export declare const TaskComplexitySchema: z.ZodEnum<["simple", "moderate", "complex", "expert"]>;
export type TaskComplexity = z.infer<typeof TaskComplexitySchema>;
export declare const ScaffoldTypeSchema: z.ZodEnum<["decomposition", "analogy", "worked_example", "socratic", "metacognitive_prompting", "chain_of_thought"]>;
export type ScaffoldType = z.infer<typeof ScaffoldTypeSchema>;
export declare const TaskSchema: z.ZodObject<{
    description: z.ZodString;
    complexity: z.ZodEnum<["simple", "moderate", "complex", "expert"]>;
    domain: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    description: string;
    complexity: "simple" | "moderate" | "complex" | "expert";
    domain?: string | undefined;
}, {
    description: string;
    complexity: "simple" | "moderate" | "complex" | "expert";
    domain?: string | undefined;
}>;
export type Task = z.infer<typeof TaskSchema>;
export declare const AdaptivitySchema: z.ZodObject<{
    fading: z.ZodDefault<z.ZodBoolean>;
    monitoring: z.ZodDefault<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    monitoring: boolean;
    fading: boolean;
}, {
    monitoring?: boolean | undefined;
    fading?: boolean | undefined;
}>;
export type Adaptivity = z.infer<typeof AdaptivitySchema>;
export declare const ScaffoldInputSchema: z.ZodObject<{
    task: z.ZodObject<{
        description: z.ZodString;
        complexity: z.ZodEnum<["simple", "moderate", "complex", "expert"]>;
        domain: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        description: string;
        complexity: "simple" | "moderate" | "complex" | "expert";
        domain?: string | undefined;
    }, {
        description: string;
        complexity: "simple" | "moderate" | "complex" | "expert";
        domain?: string | undefined;
    }>;
    scaffoldType: z.ZodEnum<["decomposition", "analogy", "worked_example", "socratic", "metacognitive_prompting", "chain_of_thought"]>;
    adaptivity: z.ZodOptional<z.ZodObject<{
        fading: z.ZodDefault<z.ZodBoolean>;
        monitoring: z.ZodDefault<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        monitoring: boolean;
        fading: boolean;
    }, {
        monitoring?: boolean | undefined;
        fading?: boolean | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    task: {
        description: string;
        complexity: "simple" | "moderate" | "complex" | "expert";
        domain?: string | undefined;
    };
    scaffoldType: "decomposition" | "analogy" | "worked_example" | "socratic" | "metacognitive_prompting" | "chain_of_thought";
    adaptivity?: {
        monitoring: boolean;
        fading: boolean;
    } | undefined;
}, {
    task: {
        description: string;
        complexity: "simple" | "moderate" | "complex" | "expert";
        domain?: string | undefined;
    };
    scaffoldType: "decomposition" | "analogy" | "worked_example" | "socratic" | "metacognitive_prompting" | "chain_of_thought";
    adaptivity?: {
        monitoring?: boolean | undefined;
        fading?: boolean | undefined;
    } | undefined;
}>;
export type ScaffoldInput = z.infer<typeof ScaffoldInputSchema>;
export interface ScaffoldStep {
    step: number;
    instruction: string;
    hints: string[];
    checkpoints: string[];
}
export interface ScaffoldOutput {
    scaffoldType: ScaffoldType;
    steps: ScaffoldStep[];
    details: {
        taskComplexity: TaskComplexity;
        stepCount: number;
        fadingEnabled: boolean;
        interpretation: string;
    };
}
export declare const LoadOptimizationSchema: z.ZodEnum<["reduce_extraneous", "chunk_intrinsic", "maximize_germane", "balanced"]>;
export type LoadOptimization = z.infer<typeof LoadOptimizationSchema>;
export declare const LoadAssessmentSchema: z.ZodObject<{
    intrinsic: z.ZodOptional<z.ZodNumber>;
    extraneous: z.ZodOptional<z.ZodNumber>;
    germane: z.ZodOptional<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    intrinsic?: number | undefined;
    extraneous?: number | undefined;
    germane?: number | undefined;
}, {
    intrinsic?: number | undefined;
    extraneous?: number | undefined;
    germane?: number | undefined;
}>;
export type LoadAssessment = z.infer<typeof LoadAssessmentSchema>;
export declare const CognitiveLoadInputSchema: z.ZodObject<{
    assessment: z.ZodOptional<z.ZodObject<{
        intrinsic: z.ZodOptional<z.ZodNumber>;
        extraneous: z.ZodOptional<z.ZodNumber>;
        germane: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        intrinsic?: number | undefined;
        extraneous?: number | undefined;
        germane?: number | undefined;
    }, {
        intrinsic?: number | undefined;
        extraneous?: number | undefined;
        germane?: number | undefined;
    }>>;
    optimization: z.ZodDefault<z.ZodEnum<["reduce_extraneous", "chunk_intrinsic", "maximize_germane", "balanced"]>>;
    threshold: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    optimization: "reduce_extraneous" | "chunk_intrinsic" | "maximize_germane" | "balanced";
    threshold: number;
    assessment?: {
        intrinsic?: number | undefined;
        extraneous?: number | undefined;
        germane?: number | undefined;
    } | undefined;
}, {
    assessment?: {
        intrinsic?: number | undefined;
        extraneous?: number | undefined;
        germane?: number | undefined;
    } | undefined;
    optimization?: "reduce_extraneous" | "chunk_intrinsic" | "maximize_germane" | "balanced" | undefined;
    threshold?: number | undefined;
}>;
export type CognitiveLoadInput = z.infer<typeof CognitiveLoadInputSchema>;
export interface CognitiveLoadState {
    intrinsic: number;
    extraneous: number;
    germane: number;
    total: number;
    overloaded: boolean;
}
export interface CognitiveLoadOutput {
    currentLoad: {
        intrinsic: number;
        extraneous: number;
        germane: number;
        total: number;
    };
    overloaded: boolean;
    recommendations: string[];
    details: {
        optimization: LoadOptimization;
        threshold: number;
        interpretation: string;
    };
}
export interface CognitiveKernelConfig {
    workingMemory: {
        defaultCapacity: number;
        decayRate: number;
        consolidationInterval: number;
    };
    attention: {
        defaultMode: AttentionMode;
        sustainedDuration: number;
        noveltyBias: number;
    };
    metaCognition: {
        reflectionInterval: number;
        confidenceThreshold: number;
        interventionEnabled: boolean;
    };
    scaffolding: {
        fadingRate: number;
        adaptationEnabled: boolean;
    };
    cognitiveLoad: {
        maxLoad: number;
        warningThreshold: number;
    };
}
export declare const DEFAULT_CONFIG: CognitiveKernelConfig;
export interface CognitiveItem {
    id: string;
    content: Float32Array;
    salience: number;
    decay: number;
    associations: string[];
    metadata?: Record<string, unknown>;
}
export interface CognitiveBridgeInterface {
    initialized: boolean;
    store(item: CognitiveItem): boolean;
    retrieve(id: string): CognitiveItem | null;
    search(query: Float32Array, k: number): CognitiveItem[];
    decay(deltaTime: number): void;
    consolidate(): void;
    focus(ids: string[]): {
        focus: string[];
        breadth: number;
        intensity: number;
    };
    assess(): MetaCognitiveAssessment;
    scaffold(task: string, difficulty: number): string[];
}
export interface SonaPattern {
    id: string;
    embedding: Float32Array;
    successRate: number;
    usageCount: number;
    domain: string;
}
export interface SonaBridgeInterface {
    initialized: boolean;
    learn(trajectories: unknown[], config: unknown): number;
    predict(state: Float32Array): {
        action: string;
        confidence: number;
    };
    storePattern(pattern: SonaPattern): void;
    findPatterns(query: Float32Array, k: number): SonaPattern[];
}
/**
 * Create a successful MCP tool result
 */
export declare function successResult(data: unknown): MCPToolResult;
/**
 * Create an error MCP tool result
 */
export declare function errorResult(error: Error | string): MCPToolResult;
/**
 * Calculate cognitive load from components
 */
export declare function calculateTotalLoad(intrinsic: number, extraneous: number, germane: number): number;
/**
 * Generate scaffolding steps based on complexity
 */
export declare function generateScaffoldSteps(complexity: TaskComplexity, scaffoldType: ScaffoldType): number;
//# sourceMappingURL=types.d.ts.map