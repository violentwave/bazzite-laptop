/**
 * @claude-flow/plugin-quantum-optimizer
 *
 * Quantum-inspired optimization plugin for Claude Flow V3.
 *
 * Provides MCP tools for:
 * - Simulated quantum annealing (QUBO, Ising, SAT, Max-Cut)
 * - QAOA variational optimization
 * - Grover-inspired search with quadratic speedup
 * - Dependency resolution using quantum optimization
 * - Task scheduling with DAG analysis
 *
 * @module @claude-flow/plugin-quantum-optimizer
 * @version 3.0.0-alpha.1
 */
export type { QUBOProblem, QUBOSolution, TemperatureSchedule, AnnealingConfig, AnnealingResult, ProblemGraph, QAOACircuit, QAOAResult, SearchSpace, AmplificationConfig, GroverResult, PackageDescriptor, DependencyConstraints, DependencyResult, ScheduleTask, ScheduleResource, ScheduleObjective, ScheduledTask, ScheduleResult, MCPTool, MCPToolResult, MCPToolInputSchema, ToolContext, Logger, QuantumOptimizerConfig, QuantumOptimizerBridge, } from './types.js';
export { AnnealingSolveInputSchema, QAOAOptimizeInputSchema, GroverSearchInputSchema, DependencyResolveInputSchema, ScheduleOptimizeInputSchema, TemperatureScheduleSchema, successResult, errorResult, RESOURCE_LIMITS, ALLOWED_ORACLE_OPS, } from './types.js';
export { ExoticBridge, createExoticBridge } from './bridges/exotic-bridge.js';
export { DagBridge, createDagBridge } from './bridges/dag-bridge.js';
export type { WasmModuleStatus } from './bridges/exotic-bridge.js';
export type { Dag, DagNode, DagEdge, TopologicalSortResult, CriticalPathResult } from './bridges/dag-bridge.js';
export { quantumOptimizerTools, toolHandlers, getTool, getToolNames, annealingSolveTool, qaoaOptimizeTool, groverSearchTool, dependencyResolveTool, scheduleOptimizeTool, } from './mcp-tools.js';
export { default } from './mcp-tools.js';
/**
 * Plugin metadata
 */
export declare const pluginMetadata: {
    readonly name: "@claude-flow/plugin-quantum-optimizer";
    readonly version: "3.0.0-alpha.1";
    readonly description: "Quantum-inspired optimization for combinatorial problems";
    readonly category: "exotic";
    readonly author: "rUv";
    readonly license: "MIT";
    readonly repository: "https://github.com/ruvnet/claude-flow";
    readonly tools: readonly ["quantum_annealing_solve", "quantum_qaoa_optimize", "quantum_grover_search", "quantum_dependency_resolve", "quantum_schedule_optimize"];
    readonly bridges: readonly ["exotic-bridge", "dag-bridge"];
    readonly wasmPackages: readonly ["@ruvector/exotic-wasm", "@ruvector/dag-wasm", "@ruvector/sparse-inference-wasm"];
};
/**
 * Initialize the plugin
 */
export declare function initializePlugin(): Promise<void>;
/**
 * Plugin configuration validator
 */
export declare function validateConfig(config: unknown): config is QuantumOptimizerConfig;
/**
 * Default plugin configuration
 */
export declare const defaultConfig: QuantumOptimizerConfig;
import type { QuantumOptimizerConfig } from './types.js';
//# sourceMappingURL=index.d.ts.map