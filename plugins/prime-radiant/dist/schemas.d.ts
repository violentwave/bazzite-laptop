/**
 * Prime Radiant Plugin - Zod Validation Schemas
 *
 * Provides runtime validation for all plugin inputs:
 * - MCP tool inputs
 * - Configuration options
 * - Engine inputs
 *
 * Uses Zod for type-safe validation with automatic TypeScript inference.
 *
 * @module prime-radiant/schemas
 * @version 0.1.3
 */
import { z } from 'zod';
/**
 * Schema for embedding vectors (array of numbers)
 */
export declare const EmbeddingVectorSchema: z.ZodArray<z.ZodNumber, "many">;
/**
 * Schema for multiple embedding vectors
 */
export declare const EmbeddingVectorsSchema: z.ZodArray<z.ZodArray<z.ZodNumber, "many">, "many">;
/**
 * Schema for adjacency matrix (2D array of numbers)
 */
export declare const AdjacencyMatrixSchema: z.ZodArray<z.ZodArray<z.ZodNumber, "many">, "many">;
/**
 * Schema for coherence energy (0-1)
 */
export declare const CoherenceEnergySchema: z.ZodNumber;
/**
 * Schema for threshold values (0-1)
 */
export declare const ThresholdSchema: z.ZodNumber;
/**
 * Schema for coherence check input
 */
export declare const CoherenceCheckInputSchema: z.ZodObject<{
    vectors: z.ZodArray<z.ZodArray<z.ZodNumber, "many">, "many">;
    threshold: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    vectors: number[][];
    threshold: number;
}, {
    vectors: number[][];
    threshold?: number | undefined;
}>;
export type CoherenceCheckInput = z.infer<typeof CoherenceCheckInputSchema>;
/**
 * Schema for coherence check result
 */
export declare const CoherenceCheckResultSchema: z.ZodObject<{
    coherent: z.ZodBoolean;
    energy: z.ZodNumber;
    violations: z.ZodArray<z.ZodString, "many">;
    confidence: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    coherent: boolean;
    energy: number;
    violations: string[];
    confidence: number;
}, {
    coherent: boolean;
    energy: number;
    violations: string[];
    confidence: number;
}>;
export type CoherenceCheckResult = z.infer<typeof CoherenceCheckResultSchema>;
/**
 * Schema for coherence thresholds configuration
 */
export declare const CoherenceThresholdsSchema: z.ZodObject<{
    reject: z.ZodDefault<z.ZodNumber>;
    warn: z.ZodDefault<z.ZodNumber>;
    allow: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    allow: number;
    warn: number;
    reject: number;
}, {
    allow?: number | undefined;
    warn?: number | undefined;
    reject?: number | undefined;
}>;
export type CoherenceThresholds = z.infer<typeof CoherenceThresholdsSchema>;
/**
 * Schema for spectral analysis type
 */
export declare const SpectralAnalysisTypeSchema: z.ZodEnum<["stability", "clustering", "connectivity"]>;
export type SpectralAnalysisType = z.infer<typeof SpectralAnalysisTypeSchema>;
/**
 * Schema for spectral analysis input
 */
export declare const SpectralAnalyzeInputSchema: z.ZodObject<{
    adjacencyMatrix: z.ZodArray<z.ZodArray<z.ZodNumber, "many">, "many">;
    analyzeType: z.ZodDefault<z.ZodEnum<["stability", "clustering", "connectivity"]>>;
}, "strip", z.ZodTypeAny, {
    adjacencyMatrix: number[][];
    analyzeType: "stability" | "clustering" | "connectivity";
}, {
    adjacencyMatrix: number[][];
    analyzeType?: "stability" | "clustering" | "connectivity" | undefined;
}>;
export type SpectralAnalyzeInput = z.infer<typeof SpectralAnalyzeInputSchema>;
/**
 * Schema for spectral analysis result
 */
export declare const SpectralAnalysisResultSchema: z.ZodObject<{
    stable: z.ZodBoolean;
    eigenvalues: z.ZodArray<z.ZodNumber, "many">;
    spectralGap: z.ZodNumber;
    stabilityIndex: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    stable: boolean;
    eigenvalues: number[];
    spectralGap: number;
    stabilityIndex: number;
}, {
    stable: boolean;
    eigenvalues: number[];
    spectralGap: number;
    stabilityIndex: number;
}>;
export type SpectralAnalysisResult = z.infer<typeof SpectralAnalysisResultSchema>;
/**
 * Schema for causal graph
 */
export declare const CausalGraphSchema: z.ZodObject<{
    nodes: z.ZodArray<z.ZodString, "many">;
    edges: z.ZodArray<z.ZodTuple<[z.ZodString, z.ZodString], null>, "many">;
}, "strip", z.ZodTypeAny, {
    nodes: string[];
    edges: [string, string][];
}, {
    nodes: string[];
    edges: [string, string][];
}>;
export type CausalGraph = z.infer<typeof CausalGraphSchema>;
/**
 * Schema for causal inference input
 */
export declare const CausalInferInputSchema: z.ZodObject<{
    treatment: z.ZodString;
    outcome: z.ZodString;
    graph: z.ZodObject<{
        nodes: z.ZodArray<z.ZodString, "many">;
        edges: z.ZodArray<z.ZodTuple<[z.ZodString, z.ZodString], null>, "many">;
    }, "strip", z.ZodTypeAny, {
        nodes: string[];
        edges: [string, string][];
    }, {
        nodes: string[];
        edges: [string, string][];
    }>;
}, "strip", z.ZodTypeAny, {
    treatment: string;
    outcome: string;
    graph: {
        nodes: string[];
        edges: [string, string][];
    };
}, {
    treatment: string;
    outcome: string;
    graph: {
        nodes: string[];
        edges: [string, string][];
    };
}>;
export type CausalInferInput = z.infer<typeof CausalInferInputSchema>;
/**
 * Schema for causal inference result
 */
export declare const CausalInferenceResultSchema: z.ZodObject<{
    effect: z.ZodNumber;
    confounders: z.ZodArray<z.ZodString, "many">;
    interventionValid: z.ZodBoolean;
    backdoorPaths: z.ZodArray<z.ZodString, "many">;
}, "strip", z.ZodTypeAny, {
    effect: number;
    confounders: string[];
    interventionValid: boolean;
    backdoorPaths: string[];
}, {
    effect: number;
    confounders: string[];
    interventionValid: boolean;
    backdoorPaths: string[];
}>;
export type CausalInferenceResult = z.infer<typeof CausalInferenceResultSchema>;
/**
 * Schema for agent state
 */
export declare const AgentStateSchema: z.ZodObject<{
    agentId: z.ZodString;
    embedding: z.ZodArray<z.ZodNumber, "many">;
    vote: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodBoolean]>>;
    metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
}, "strip", z.ZodTypeAny, {
    agentId: string;
    embedding: number[];
    vote?: string | boolean | undefined;
    metadata?: Record<string, unknown> | undefined;
}, {
    agentId: string;
    embedding: number[];
    vote?: string | boolean | undefined;
    metadata?: Record<string, unknown> | undefined;
}>;
export type AgentState = z.infer<typeof AgentStateSchema>;
/**
 * Schema for consensus verification input
 */
export declare const ConsensusVerifyInputSchema: z.ZodObject<{
    agentStates: z.ZodArray<z.ZodObject<{
        agentId: z.ZodString;
        embedding: z.ZodArray<z.ZodNumber, "many">;
        vote: z.ZodOptional<z.ZodUnion<[z.ZodString, z.ZodBoolean]>>;
        metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    }, "strip", z.ZodTypeAny, {
        agentId: string;
        embedding: number[];
        vote?: string | boolean | undefined;
        metadata?: Record<string, unknown> | undefined;
    }, {
        agentId: string;
        embedding: number[];
        vote?: string | boolean | undefined;
        metadata?: Record<string, unknown> | undefined;
    }>, "many">;
    consensusThreshold: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    agentStates: {
        agentId: string;
        embedding: number[];
        vote?: string | boolean | undefined;
        metadata?: Record<string, unknown> | undefined;
    }[];
    consensusThreshold: number;
}, {
    agentStates: {
        agentId: string;
        embedding: number[];
        vote?: string | boolean | undefined;
        metadata?: Record<string, unknown> | undefined;
    }[];
    consensusThreshold?: number | undefined;
}>;
export type ConsensusVerifyInput = z.infer<typeof ConsensusVerifyInputSchema>;
/**
 * Schema for consensus result
 */
export declare const ConsensusResultSchema: z.ZodObject<{
    consensusAchieved: z.ZodBoolean;
    agreementRatio: z.ZodNumber;
    coherenceEnergy: z.ZodNumber;
    spectralStability: z.ZodBoolean;
    spectralGap: z.ZodNumber;
    violations: z.ZodArray<z.ZodString, "many">;
    recommendation: z.ZodString;
}, "strip", z.ZodTypeAny, {
    violations: string[];
    spectralGap: number;
    consensusAchieved: boolean;
    agreementRatio: number;
    coherenceEnergy: number;
    spectralStability: boolean;
    recommendation: string;
}, {
    violations: string[];
    spectralGap: number;
    consensusAchieved: boolean;
    agreementRatio: number;
    coherenceEnergy: number;
    spectralStability: boolean;
    recommendation: string;
}>;
export type ConsensusResult = z.infer<typeof ConsensusResultSchema>;
/**
 * Schema for point cloud (array of points)
 */
export declare const PointCloudSchema: z.ZodArray<z.ZodArray<z.ZodNumber, "many">, "many">;
/**
 * Schema for quantum topology input
 */
export declare const QuantumTopologyInputSchema: z.ZodObject<{
    points: z.ZodArray<z.ZodArray<z.ZodNumber, "many">, "many">;
    maxDimension: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    points: number[][];
    maxDimension: number;
}, {
    points: number[][];
    maxDimension?: number | undefined;
}>;
export type QuantumTopologyInput = z.infer<typeof QuantumTopologyInputSchema>;
/**
 * Schema for persistence point
 */
export declare const PersistencePointSchema: z.ZodTuple<[z.ZodNumber, z.ZodNumber], null>;
/**
 * Schema for topology result
 */
export declare const TopologyResultSchema: z.ZodObject<{
    bettiNumbers: z.ZodArray<z.ZodNumber, "many">;
    persistenceDiagram: z.ZodArray<z.ZodTuple<[z.ZodNumber, z.ZodNumber], null>, "many">;
    homologyClasses: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    bettiNumbers: number[];
    persistenceDiagram: [number, number][];
    homologyClasses: number;
}, {
    bettiNumbers: number[];
    persistenceDiagram: [number, number][];
    homologyClasses: number;
}>;
export type TopologyResult = z.infer<typeof TopologyResultSchema>;
/**
 * Schema for memory entry
 */
export declare const MemoryEntrySchema: z.ZodObject<{
    key: z.ZodString;
    content: z.ZodString;
    embedding: z.ZodArray<z.ZodNumber, "many">;
    metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
}, "strip", z.ZodTypeAny, {
    embedding: number[];
    key: string;
    content: string;
    metadata?: Record<string, unknown> | undefined;
}, {
    embedding: number[];
    key: string;
    content: string;
    metadata?: Record<string, unknown> | undefined;
}>;
export type MemoryEntry = z.infer<typeof MemoryEntrySchema>;
/**
 * Schema for memory gate input
 */
export declare const MemoryGateInputSchema: z.ZodObject<{
    entry: z.ZodObject<{
        key: z.ZodString;
        content: z.ZodString;
        embedding: z.ZodArray<z.ZodNumber, "many">;
        metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    }, "strip", z.ZodTypeAny, {
        embedding: number[];
        key: string;
        content: string;
        metadata?: Record<string, unknown> | undefined;
    }, {
        embedding: number[];
        key: string;
        content: string;
        metadata?: Record<string, unknown> | undefined;
    }>;
    contextEmbeddings: z.ZodOptional<z.ZodArray<z.ZodArray<z.ZodNumber, "many">, "many">>;
    thresholds: z.ZodOptional<z.ZodObject<{
        reject: z.ZodDefault<z.ZodNumber>;
        warn: z.ZodDefault<z.ZodNumber>;
        allow: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        allow: number;
        warn: number;
        reject: number;
    }, {
        allow?: number | undefined;
        warn?: number | undefined;
        reject?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    entry: {
        embedding: number[];
        key: string;
        content: string;
        metadata?: Record<string, unknown> | undefined;
    };
    contextEmbeddings?: number[][] | undefined;
    thresholds?: {
        allow: number;
        warn: number;
        reject: number;
    } | undefined;
}, {
    entry: {
        embedding: number[];
        key: string;
        content: string;
        metadata?: Record<string, unknown> | undefined;
    };
    contextEmbeddings?: number[][] | undefined;
    thresholds?: {
        allow?: number | undefined;
        warn?: number | undefined;
        reject?: number | undefined;
    } | undefined;
}>;
export type MemoryGateInput = z.infer<typeof MemoryGateInputSchema>;
/**
 * Schema for coherence action
 */
export declare const CoherenceActionSchema: z.ZodEnum<["allow", "warn", "reject"]>;
export type CoherenceAction = z.infer<typeof CoherenceActionSchema>;
/**
 * Schema for memory gate result
 */
export declare const MemoryGateResultSchema: z.ZodObject<{
    action: z.ZodEnum<["allow", "warn", "reject"]>;
    coherent: z.ZodBoolean;
    energy: z.ZodNumber;
    violations: z.ZodArray<z.ZodString, "many">;
    confidence: z.ZodNumber;
    recommendation: z.ZodString;
}, "strip", z.ZodTypeAny, {
    coherent: boolean;
    energy: number;
    violations: string[];
    confidence: number;
    recommendation: string;
    action: "allow" | "warn" | "reject";
}, {
    coherent: boolean;
    energy: number;
    violations: string[];
    confidence: number;
    recommendation: string;
    action: "allow" | "warn" | "reject";
}>;
export type MemoryGateResult = z.infer<typeof MemoryGateResultSchema>;
/**
 * Schema for coherence configuration
 */
export declare const CoherenceConfigSchema: z.ZodObject<{
    warnThreshold: z.ZodDefault<z.ZodNumber>;
    rejectThreshold: z.ZodDefault<z.ZodNumber>;
    cacheEnabled: z.ZodDefault<z.ZodBoolean>;
    cacheTTL: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    warnThreshold: number;
    rejectThreshold: number;
    cacheEnabled: boolean;
    cacheTTL: number;
}, {
    warnThreshold?: number | undefined;
    rejectThreshold?: number | undefined;
    cacheEnabled?: boolean | undefined;
    cacheTTL?: number | undefined;
}>;
/**
 * Schema for spectral configuration
 */
export declare const SpectralConfigSchema: z.ZodObject<{
    stabilityThreshold: z.ZodDefault<z.ZodNumber>;
    maxMatrixSize: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    stabilityThreshold: number;
    maxMatrixSize: number;
}, {
    stabilityThreshold?: number | undefined;
    maxMatrixSize?: number | undefined;
}>;
/**
 * Schema for causal configuration
 */
export declare const CausalConfigSchema: z.ZodObject<{
    maxBackdoorPaths: z.ZodDefault<z.ZodNumber>;
    confidenceThreshold: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    maxBackdoorPaths: number;
    confidenceThreshold: number;
}, {
    maxBackdoorPaths?: number | undefined;
    confidenceThreshold?: number | undefined;
}>;
/**
 * Schema for full plugin configuration
 */
export declare const PrimeRadiantConfigSchema: z.ZodObject<{
    coherence: z.ZodDefault<z.ZodObject<{
        warnThreshold: z.ZodDefault<z.ZodNumber>;
        rejectThreshold: z.ZodDefault<z.ZodNumber>;
        cacheEnabled: z.ZodDefault<z.ZodBoolean>;
        cacheTTL: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        warnThreshold: number;
        rejectThreshold: number;
        cacheEnabled: boolean;
        cacheTTL: number;
    }, {
        warnThreshold?: number | undefined;
        rejectThreshold?: number | undefined;
        cacheEnabled?: boolean | undefined;
        cacheTTL?: number | undefined;
    }>>;
    spectral: z.ZodDefault<z.ZodObject<{
        stabilityThreshold: z.ZodDefault<z.ZodNumber>;
        maxMatrixSize: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        stabilityThreshold: number;
        maxMatrixSize: number;
    }, {
        stabilityThreshold?: number | undefined;
        maxMatrixSize?: number | undefined;
    }>>;
    causal: z.ZodDefault<z.ZodObject<{
        maxBackdoorPaths: z.ZodDefault<z.ZodNumber>;
        confidenceThreshold: z.ZodDefault<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        maxBackdoorPaths: number;
        confidenceThreshold: number;
    }, {
        maxBackdoorPaths?: number | undefined;
        confidenceThreshold?: number | undefined;
    }>>;
}, "strip", z.ZodTypeAny, {
    coherence: {
        warnThreshold: number;
        rejectThreshold: number;
        cacheEnabled: boolean;
        cacheTTL: number;
    };
    spectral: {
        stabilityThreshold: number;
        maxMatrixSize: number;
    };
    causal: {
        maxBackdoorPaths: number;
        confidenceThreshold: number;
    };
}, {
    coherence?: {
        warnThreshold?: number | undefined;
        rejectThreshold?: number | undefined;
        cacheEnabled?: boolean | undefined;
        cacheTTL?: number | undefined;
    } | undefined;
    spectral?: {
        stabilityThreshold?: number | undefined;
        maxMatrixSize?: number | undefined;
    } | undefined;
    causal?: {
        maxBackdoorPaths?: number | undefined;
        confidenceThreshold?: number | undefined;
    } | undefined;
}>;
export type PrimeRadiantConfig = z.infer<typeof PrimeRadiantConfigSchema>;
/**
 * Schema for HoTT verification input
 */
export declare const HottVerificationInputSchema: z.ZodObject<{
    proposition: z.ZodString;
    proof: z.ZodString;
}, "strip", z.ZodTypeAny, {
    proposition: string;
    proof: string;
}, {
    proposition: string;
    proof: string;
}>;
export type HottVerificationInput = z.infer<typeof HottVerificationInputSchema>;
/**
 * Schema for HoTT proof result
 */
export declare const HottProofResultSchema: z.ZodObject<{
    valid: z.ZodBoolean;
    type: z.ZodString;
    normalForm: z.ZodString;
}, "strip", z.ZodTypeAny, {
    valid: boolean;
    type: string;
    normalForm: string;
}, {
    valid: boolean;
    type: string;
    normalForm: string;
}>;
export type HottProofResult = z.infer<typeof HottProofResultSchema>;
/**
 * Schema for morphism input
 */
export declare const MorphismInputSchema: z.ZodObject<{
    source: z.ZodUnknown;
    target: z.ZodUnknown;
    morphism: z.ZodString;
}, "strip", z.ZodTypeAny, {
    morphism: string;
    source?: unknown;
    target?: unknown;
}, {
    morphism: string;
    source?: unknown;
    target?: unknown;
}>;
export type MorphismInput = z.infer<typeof MorphismInputSchema>;
/**
 * Schema for morphism result
 */
export declare const MorphismResultSchema: z.ZodObject<{
    valid: z.ZodBoolean;
    result: z.ZodUnknown;
    naturalTransformation: z.ZodBoolean;
}, "strip", z.ZodTypeAny, {
    valid: boolean;
    naturalTransformation: boolean;
    result?: unknown;
}, {
    valid: boolean;
    naturalTransformation: boolean;
    result?: unknown;
}>;
export type MorphismResult = z.infer<typeof MorphismResultSchema>;
/**
 * Validate coherence check input
 */
export declare function validateCoherenceInput(input: unknown): CoherenceCheckInput;
/**
 * Validate spectral analysis input
 */
export declare function validateSpectralInput(input: unknown): SpectralAnalyzeInput;
/**
 * Validate causal inference input
 */
export declare function validateCausalInput(input: unknown): CausalInferInput;
/**
 * Validate consensus verification input
 */
export declare function validateConsensusInput(input: unknown): ConsensusVerifyInput;
/**
 * Validate quantum topology input
 */
export declare function validateTopologyInput(input: unknown): QuantumTopologyInput;
/**
 * Validate memory gate input
 */
export declare function validateMemoryGateInput(input: unknown): MemoryGateInput;
/**
 * Validate plugin configuration
 */
export declare function validateConfig(config: unknown): PrimeRadiantConfig;
/**
 * Safe validation that returns result or error
 */
export declare function safeValidate<T>(schema: z.ZodSchema<T>, input: unknown): {
    success: true;
    data: T;
} | {
    success: false;
    error: z.ZodError;
};
//# sourceMappingURL=schemas.d.ts.map