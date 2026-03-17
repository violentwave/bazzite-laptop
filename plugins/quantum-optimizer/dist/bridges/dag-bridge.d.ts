/**
 * DAG Bridge - Directed Acyclic Graph Operations
 *
 * Bridge to @ruvector/dag-wasm for dependency graph analysis,
 * topological sorting, and cycle detection.
 */
import type { PackageDescriptor, DependencyConstraints, DependencyResult, ScheduleTask, ScheduleResource, ScheduleResult, ScheduleObjective } from '../types.js';
/**
 * WASM module status
 */
export type WasmModuleStatus = 'unloaded' | 'loading' | 'ready' | 'error';
/**
 * DAG node
 */
export interface DagNode {
    readonly id: string;
    readonly data?: Record<string, unknown>;
}
/**
 * DAG edge
 */
export interface DagEdge {
    readonly from: string;
    readonly to: string;
    readonly weight?: number;
}
/**
 * DAG structure
 */
export interface Dag {
    readonly nodes: ReadonlyArray<DagNode>;
    readonly edges: ReadonlyArray<DagEdge>;
}
/**
 * Topological sort result
 */
export interface TopologicalSortResult {
    readonly order: ReadonlyArray<string>;
    readonly hasCycle: boolean;
    readonly cycleNodes?: ReadonlyArray<string>;
}
/**
 * Critical path result
 */
export interface CriticalPathResult {
    readonly path: ReadonlyArray<string>;
    readonly length: number;
    readonly slack: Map<string, number>;
}
/**
 * DAG Bridge for dependency graph operations
 */
export declare class DagBridge {
    readonly name = "quantum-dag-bridge";
    readonly version = "0.1.0";
    private _status;
    private _module;
    get status(): WasmModuleStatus;
    get initialized(): boolean;
    /**
     * Initialize the WASM module
     */
    initialize(): Promise<void>;
    /**
     * Dispose of resources
     */
    dispose(): Promise<void>;
    /**
     * Perform topological sort on a DAG
     */
    topologicalSort(dag: Dag): TopologicalSortResult;
    /**
     * Find critical path in a DAG with durations
     */
    criticalPath(dag: Dag, durations: Map<string, number>): CriticalPathResult;
    /**
     * Resolve package dependencies using quantum-inspired optimization
     */
    resolveDependencies(packages: ReadonlyArray<PackageDescriptor>, constraints: DependencyConstraints): Promise<DependencyResult>;
    /**
     * Optimize task schedule using DAG analysis
     */
    optimizeSchedule(tasks: ReadonlyArray<ScheduleTask>, resources: ReadonlyArray<ScheduleResource>, objective: ScheduleObjective): Promise<ScheduleResult>;
    private versionSatisfies;
    private compareVersions;
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new DagBridge instance
 */
export declare function createDagBridge(): DagBridge;
//# sourceMappingURL=dag-bridge.d.ts.map