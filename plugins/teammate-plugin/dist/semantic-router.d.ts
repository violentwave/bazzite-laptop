/**
 * Semantic Router - Neural BMSSP-powered intelligent routing
 *
 * Uses WebAssembly-accelerated neural pathfinding with embeddings
 * to match tasks to the best-suited teammates based on semantic similarity.
 *
 * @module @claude-flow/teammate-plugin/semantic
 * @version 1.0.0-alpha.1
 */
import type { TeammateInfo, TeamState } from './types.js';
export interface TeammateProfile {
    id: string;
    role: string;
    skills: string[];
    embedding?: Float64Array;
    performance: {
        tasksCompleted: number;
        successRate: number;
        averageLatencyMs: number;
    };
}
export interface TaskProfile {
    id: string;
    description: string;
    requiredSkills: string[];
    embedding?: Float64Array;
    priority: 'urgent' | 'high' | 'normal' | 'low';
    estimatedDuration?: number;
}
export interface MatchResult {
    teammateId: string;
    score: number;
    semanticDistance: number;
    skillMatch: number;
    loadFactor: number;
    confidence: number;
}
export interface RoutingDecision {
    task: TaskProfile;
    matches: MatchResult[];
    selectedTeammate: string | null;
    reasoning: string;
    alternates: string[];
}
export interface SemanticRouterConfig {
    embeddingDim: number;
    skillWeight: number;
    semanticWeight: number;
    loadWeight: number;
    performanceWeight: number;
    minConfidence: number;
}
export declare const DEFAULT_SEMANTIC_CONFIG: SemanticRouterConfig;
export declare class SemanticRouter {
    private neuralGraph;
    private profiles;
    private nodeMap;
    private nodeCount;
    private initialized;
    private useFallback;
    private config;
    constructor(config?: Partial<SemanticRouterConfig>);
    /**
     * Initialize the router with WASM support
     */
    initialize(): Promise<boolean>;
    /**
     * Register a teammate with their profile
     */
    registerTeammate(teammate: TeammateInfo, skills?: string[]): TeammateProfile;
    /**
     * Build profiles from team state
     */
    buildFromTeam(team: TeamState): Promise<void>;
    /**
     * Find best teammate match for a task
     */
    findBestMatch(task: TaskProfile): RoutingDecision;
    /**
     * Batch match multiple tasks to teammates
     */
    batchMatch(tasks: TaskProfile[]): Map<string, RoutingDecision>;
    /**
     * Get semantic distance between two teammates
     */
    getSemanticDistance(id1: string, id2: string): number;
    /**
     * Update teammate performance metrics
     */
    updatePerformance(teammateId: string, taskSuccess: boolean, latencyMs: number): void;
    /**
     * Get teammate profile
     */
    getProfile(teammateId: string): TeammateProfile | undefined;
    /**
     * Get all profiles
     */
    getAllProfiles(): TeammateProfile[];
    /**
     * Clear all data
     */
    clear(): void;
    /**
     * Free resources
     */
    dispose(): void;
    private inferSkills;
    private computeEmbedding;
    private buildSemanticEdges;
    private computeMatchScore;
    private skillOverlap;
    private cosineDistance;
    private generateReasoning;
}
export declare function createSemanticRouter(config?: Partial<SemanticRouterConfig>): Promise<SemanticRouter>;
export default SemanticRouter;
//# sourceMappingURL=semantic-router.d.ts.map