/**
 * DAG Bridge for Obligation Tracking
 *
 * Provides directed acyclic graph operations for obligation dependency
 * tracking using ruvector-dag-wasm for high-performance graph algorithms.
 *
 * Features:
 * - Obligation dependency graph construction
 * - Critical path analysis
 * - Topological sorting
 * - Cycle detection
 * - Float/slack calculation
 *
 * Based on ADR-034: Legal Contract Analysis Plugin
 *
 * @module v3/plugins/legal-contracts/bridges/dag-bridge
 */
import type { IDAGBridge, Obligation, ObligationTrackingResult } from '../types.js';
/**
 * DAG Bridge Implementation
 */
export declare class DAGBridge implements IDAGBridge {
    private wasmModule;
    private initialized;
    /**
     * Initialize the WASM module
     */
    initialize(): Promise<void>;
    /**
     * Check if initialized
     */
    isInitialized(): boolean;
    /**
     * Build obligation dependency graph
     */
    buildDependencyGraph(obligations: Obligation[]): Promise<ObligationTrackingResult['graph']>;
    /**
     * Find critical path through obligations
     */
    findCriticalPath(graph: ObligationTrackingResult['graph']): Promise<string[]>;
    /**
     * Perform topological sort of obligations
     */
    topologicalSort(obligations: Obligation[]): Promise<Obligation[]>;
    /**
     * Detect cycles in dependency graph
     */
    detectCycles(graph: ObligationTrackingResult['graph']): Promise<string[][]>;
    /**
     * Calculate slack/float for each obligation
     */
    calculateFloat(graph: ObligationTrackingResult['graph'], projectEnd: Date): Promise<Map<string, number>>;
    /**
     * Load WASM module dynamically
     */
    private loadWasmModule;
    /**
     * Find critical path internally
     */
    private findCriticalPathInternal;
    /**
     * Calculate schedule (earliest start, latest finish, float)
     */
    private calculateSchedule;
    /**
     * Estimate duration in days for an obligation
     */
    private estimateDuration;
}
/**
 * Create and export default bridge instance
 */
export declare function createDAGBridge(): IDAGBridge;
export default DAGBridge;
//# sourceMappingURL=dag-bridge.d.ts.map