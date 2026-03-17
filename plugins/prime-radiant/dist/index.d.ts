/**
 * Prime Radiant Plugin - Entry Point
 *
 * Mathematical AI Interpretability for Claude Flow V3
 *
 * Provides:
 * - Sheaf Laplacian coherence detection (CohomologyEngine)
 * - Spectral stability analysis (SpectralEngine)
 * - Do-calculus causal inference (CausalEngine)
 * - Quantum topology computation (QuantumEngine)
 * - Category theory morphisms (CategoryEngine)
 * - Homotopy Type Theory proofs (HottEngine)
 *
 * WASM Bundle: 92KB, zero dependencies
 *
 * @module prime-radiant
 * @version 0.1.3
 */
export { PrimeRadiantPlugin } from './plugin.js';
export { WasmBridge, createWasmBridge, initializeWasmBridge } from './wasm-bridge.js';
export { CohomologyEngine, SpectralEngine, CausalEngine, QuantumEngine, CategoryEngine, HottEngine } from './engines/index.js';
export type { CoherenceEnergy, SpectralGap, StabilityIndex, CausalEffect, BettiNumbers, PersistencePoint, PersistenceDiagram, CoherenceCheckResult, CoherenceValidationResult, CoherenceThresholds, CoherenceAction, SpectralAnalysisResult, SpectralAnalysisType, CausalInferenceResult, CausalGraph, CausalQuery, TopologyResult, BettiInterpretation, ConsensusResult, ConsensusParams, MorphismResult, FunctorContext, HottProofResult, HottVerification, AgentState, MemoryEntry, MemoryCoherenceValidation, PrimeRadiantConfig, PrimeRadiantErrorCode, } from './types.js';
export type { WasmModule, WasmBridgeConfig, WasmStatus, CoherenceResult, SpectralResult, CausalResult as WasmCausalResult, TopologyResult as WasmTopologyResult, Intervention, Sheaf, Matrix, SimplicialComplex, Filtration, Morphism, Functor, Path, TypedValue, HottResult, } from './types.js';
export { DEFAULT_CONFIG, PrimeRadiantErrorCodes } from './types.js';
export type { IPrimeRadiantBridge, ICoherenceGate, IConsensusVerifier, IStabilityAnalyzer, ICohomologyEngine, ISpectralEngine, ICausalEngine, IQuantumEngine, ICategoryEngine, IHottEngine, IPlugin, PluginContext, PluginMCPTool, PluginHook, IResultCache, PrimeRadiantEvent, PrimeRadiantEventPayload, IPrimeRadiantEventEmitter, } from './interfaces.js';
export { HookPriority } from './interfaces.js';
export { EmbeddingVectorSchema, EmbeddingVectorsSchema, AdjacencyMatrixSchema, CoherenceEnergySchema, ThresholdSchema, CoherenceCheckInputSchema, CoherenceCheckResultSchema, CoherenceThresholdsSchema, SpectralAnalysisTypeSchema, SpectralAnalyzeInputSchema, SpectralAnalysisResultSchema, CausalGraphSchema, CausalInferInputSchema, CausalInferenceResultSchema, AgentStateSchema, ConsensusVerifyInputSchema, ConsensusResultSchema, PointCloudSchema, QuantumTopologyInputSchema, PersistencePointSchema, TopologyResultSchema, MemoryEntrySchema, MemoryGateInputSchema, CoherenceActionSchema, MemoryGateResultSchema, CoherenceConfigSchema, SpectralConfigSchema, CausalConfigSchema, PrimeRadiantConfigSchema, HottVerificationInputSchema, HottProofResultSchema, MorphismInputSchema, MorphismResultSchema, validateCoherenceInput, validateSpectralInput, validateCausalInput, validateConsensusInput, validateTopologyInput, validateMemoryGateInput, validateConfig, safeValidate, } from './schemas.js';
export type { CoherenceCheckInput, SpectralAnalyzeInput, CausalInferInput, ConsensusVerifyInput, QuantumTopologyInput, MemoryGateInput, MemoryGateResult, HottVerificationInput, MorphismInput, } from './schemas.js';
import { PrimeRadiantPlugin } from './plugin.js';
import type { PrimeRadiantConfig } from './types.js';
/**
 * Create a new Prime Radiant plugin instance
 * @param config Optional configuration overrides
 * @returns Configured plugin instance
 */
export declare function createPrimeRadiantPlugin(config?: Partial<PrimeRadiantConfig>): PrimeRadiantPlugin;
/**
 * Plugin metadata for registration
 */
export declare const pluginMetadata: {
    name: string;
    version: string;
    description: string;
    author: string;
    license: string;
    repository: string;
    wasmSize: string;
    dependencies: {
        required: string[];
        optional: string[];
    };
    capabilities: string[];
    engines: {
        name: string;
        description: string;
        performance: string;
    }[];
    tools: string[];
    hooks: string[];
};
/**
 * Default export for convenience
 */
export default PrimeRadiantPlugin;
export { primeRadiantTools, coherenceCheckTool, spectralAnalyzeTool, causalInferTool, consensusVerifyTool, quantumTopologyTool, memoryGateTool, getTool, getToolNames, getToolsByCategory, toolCategories, toolHandlers, } from './tools/index.js';
export type { MCPTool as ToolMCPTool, MCPToolResult as ToolMCPToolResult, ToolContext as ToolHandlerContext, CoherenceOutput, SpectralOutput, CausalOutput, ConsensusOutput, TopologyOutput, MemoryGateOutput, PerformanceMetrics, } from './tools/types.js';
//# sourceMappingURL=index.d.ts.map