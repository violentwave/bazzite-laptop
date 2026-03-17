/**
 * Prime Radiant MCP Tools Index
 *
 * Exports all Prime Radiant mathematical AI interpretability tools.
 *
 * Tools:
 * - pr_coherence_check: Check coherence using Sheaf Laplacian
 * - pr_spectral_analyze: Spectral stability analysis
 * - pr_causal_infer: Do-calculus causal inference
 * - pr_consensus_verify: Multi-agent consensus verification
 * - pr_quantum_topology: Quantum topology (Betti numbers, persistence)
 * - pr_memory_gate: Pre-storage coherence gate
 */
export { coherenceCheckTool, default as CoherenceCheck } from './coherence-check.js';
export { spectralAnalyzeTool, default as SpectralAnalyze } from './spectral-analyze.js';
export { causalInferTool, default as CausalInfer } from './causal-infer.js';
export { consensusVerifyTool, default as ConsensusVerify } from './consensus-verify.js';
export { quantumTopologyTool, default as QuantumTopology } from './quantum-topology.js';
export { memoryGateTool, default as MemoryGate } from './memory-gate.js';
export * from './types.js';
import type { MCPTool } from './types.js';
/**
 * All Prime Radiant MCP Tools
 */
export declare const primeRadiantTools: MCPTool[];
/**
 * Tool name to handler map for quick lookup
 */
export declare const toolHandlers: Map<string, (input: Record<string, unknown>, context?: import("./types.js").ToolContext) => Promise<import("./types.js").MCPToolResult>>;
/**
 * Get a tool by name
 */
export declare function getTool(name: string): MCPTool | undefined;
/**
 * Get all tool names
 */
export declare function getToolNames(): string[];
/**
 * Get tools by category
 */
export declare function getToolsByCategory(category: string): MCPTool[];
/**
 * Tool categories
 */
export declare const toolCategories: {
    readonly coherence: readonly [MCPTool, MCPTool];
    readonly spectral: readonly [MCPTool];
    readonly causal: readonly [MCPTool];
    readonly consensus: readonly [MCPTool];
    readonly topology: readonly [MCPTool];
    readonly memory: readonly [MCPTool];
};
export default primeRadiantTools;
//# sourceMappingURL=index.d.ts.map