/**
 * Topology Optimizer - BMSSP-powered graph optimization for team communication
 *
 * Uses WebAssembly-accelerated shortest path algorithms (10-15x faster than JS)
 * to optimize message routing, delegation chains, and team topology.
 *
 * @module @claude-flow/teammate-plugin/topology
 * @version 1.0.0-alpha.1
 */
import type { TeammateInfo, TeamState, TeamTopology } from './types.js';
export interface TopologyNode {
    id: string;
    index: number;
    role: string;
    status: 'active' | 'idle' | 'busy' | 'unhealthy';
    load: number;
}
export interface TopologyEdge {
    from: string;
    to: string;
    weight: number;
    type: 'direct' | 'delegation' | 'broadcast';
    latencyMs?: number;
}
export interface PathResult {
    path: string[];
    totalWeight: number;
    hops: number;
    estimatedLatencyMs: number;
}
export interface TopologyStats {
    nodeCount: number;
    edgeCount: number;
    density: number;
    averageDegree: number;
    isFullyConnected: boolean;
    bottlenecks: string[];
}
export interface OptimizationResult {
    originalPaths: number;
    optimizedPaths: number;
    improvement: number;
    suggestedEdges: TopologyEdge[];
    removableEdges: TopologyEdge[];
}
export declare class TopologyOptimizer {
    private topology;
    private graph;
    private nodeMap;
    private reverseNodeMap;
    private edges;
    private nodeCount;
    private initialized;
    private useFallback;
    private fallbackAdjList;
    constructor(topology?: TeamTopology);
    /**
     * Initialize the optimizer with WASM support
     */
    initialize(): Promise<boolean>;
    /**
     * Build graph from team state
     */
    buildFromTeam(team: TeamState): Promise<void>;
    /**
     * Add a node to the graph
     */
    addNode(teammate: TeammateInfo): number;
    /**
     * Add an edge to the graph
     */
    addEdge(edge: TopologyEdge): boolean;
    /**
     * Find shortest path between two teammates
     */
    findShortestPath(fromId: string, toId: string): PathResult | null;
    /**
     * Find optimal message routing path considering teammate load
     */
    findOptimalRoute(fromId: string, toId: string, teammates: Map<string, TeammateInfo>): PathResult | null;
    /**
     * Find all paths from source to all other nodes
     */
    computeAllPaths(fromId: string): Map<string, PathResult>;
    /**
     * Get topology statistics
     */
    getStats(): TopologyStats;
    /**
     * Suggest topology optimizations
     */
    suggestOptimizations(): OptimizationResult;
    /**
     * Clear the graph
     */
    clear(): void;
    /**
     * Free resources
     */
    dispose(): void;
    private buildMeshTopology;
    private buildHierarchicalTopology;
    private buildFlatTopology;
    private reconstructPath;
    private dijkstraFallback;
}
export declare function createTopologyOptimizer(topology?: TeamTopology): Promise<TopologyOptimizer>;
export default TopologyOptimizer;
//# sourceMappingURL=topology-optimizer.d.ts.map