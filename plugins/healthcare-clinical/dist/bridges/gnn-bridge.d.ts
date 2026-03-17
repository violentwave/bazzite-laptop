/**
 * GNN Bridge - Healthcare Clinical Plugin
 *
 * Provides Graph Neural Network capabilities for clinical pathway
 * analysis and drug interaction detection. Integrates with
 * ruvector-gnn-wasm for efficient graph-based reasoning.
 *
 * Use Cases:
 * - Clinical pathway recommendations
 * - Drug interaction network analysis
 * - Comorbidity pattern detection
 * - Treatment outcome prediction
 */
import type { GNNBridge, GNNConfig, GNNNode, GNNEdge, GNNPathResult, GNNInteractionResult, DrugInteraction, ClinicalPathway, Logger } from '../types.js';
/**
 * Healthcare GNN Bridge implementation
 */
export declare class HealthcareGNNBridge implements GNNBridge {
    private wasmModule;
    private graphPtr;
    private config;
    private logger;
    private nodes;
    private edges;
    private nodeIdToIndex;
    private drugInteractionGraph;
    private clinicalPathwayGraph;
    initialized: boolean;
    constructor(config?: Partial<GNNConfig>, logger?: Logger);
    /**
     * Initialize the GNN bridge
     */
    initialize(config?: GNNConfig): Promise<void>;
    /**
     * Load a graph into the GNN
     */
    loadGraph(nodes: GNNNode[], edges: GNNEdge[]): Promise<void>;
    /**
     * Predict optimal pathway between nodes
     */
    predictPathway(startNode: string, endNode: string, constraints?: Record<string, unknown>): Promise<GNNPathResult>;
    /**
     * Analyze interactions between nodes
     */
    analyzeInteractions(nodeIds: string[]): Promise<GNNInteractionResult>;
    /**
     * Get clinical pathway for a diagnosis
     */
    getClinicalPathway(diagnosis: string): ClinicalPathway | undefined;
    /**
     * Check drug interactions
     */
    checkDrugInteractions(medications: string[], severityFilter?: string): DrugInteraction[];
    /**
     * Cleanup resources
     */
    destroy(): void;
    private resolveWasmPath;
    private loadWasmModule;
    private getNodeIdByIndex;
    private bfsPath;
    private calculatePathRisk;
    private severityToStrength;
}
/**
 * Create a new GNN bridge instance
 */
export declare function createGNNBridge(config?: Partial<GNNConfig>, logger?: Logger): HealthcareGNNBridge;
export default HealthcareGNNBridge;
//# sourceMappingURL=gnn-bridge.d.ts.map