/**
 * TeammateBridge - Core bridge to Claude Code's TeammateTool
 *
 * Provides unified API for multi-agent orchestration using
 * native TeammateTool capabilities (Claude Code >= 2.1.19).
 *
 * Features:
 * - Team management (spawn, discover, join/leave)
 * - Mailbox messaging (write, broadcast)
 * - Plan approval workflow
 * - Delegation system
 * - Remote sync to Claude.ai
 * - Session memory persistence
 * - Teleport/session resume
 *
 * @module @claude-flow/teammate-plugin/bridge
 * @version 1.0.0-alpha.1
 */
import { EventEmitter } from 'events';
import type { TeamConfig, TeammateSpawnConfig, TeamState, TeammateInfo, MailboxMessage, TeamPlan, TeamContext, DelegationRecord, RemoteSession, SyncResult, TeammateMemory, TeleportTarget, TeleportResult, AgentInput, ExitPlanModeInput, VersionInfo, PluginConfig, MessageType, BackendStatus } from './types.js';
import type { PathResult, TopologyStats, OptimizationResult } from './topology-optimizer.js';
import type { RoutingDecision } from './semantic-router.js';
import { TeammateErrorCode } from './types.js';
import type { RateLimitConfig, MetricSnapshot, TeammateHealthCheck, TeamHealthReport, CircuitBreakerState } from './types.js';
export declare class TeammateError extends Error {
    readonly code: TeammateErrorCode;
    readonly teamName?: string | undefined;
    readonly teammateId?: string | undefined;
    readonly cause?: Error | undefined;
    constructor(message: string, code: TeammateErrorCode, teamName?: string | undefined, teammateId?: string | undefined, cause?: Error | undefined);
}
export declare class TeammateBridge extends EventEmitter {
    private claudeCodeVersion;
    private teammateToolAvailable;
    private initialized;
    private activeTeams;
    private mailboxPollers;
    private memoryPersistTimers;
    private teammateMemories;
    private pendingWrites;
    private readonly writeDebounceMs;
    private teamConfigCache;
    private readonly cacheMaxAgeMs;
    private rateLimiter;
    private metrics;
    private healthChecker;
    private circuitBreaker;
    private messageTTLTimer;
    private readonly messageTTLCheckIntervalMs;
    private topologyOptimizers;
    private semanticRouter;
    private optimizersEnabled;
    private readonly config;
    private readonly teamsDir;
    constructor(config?: Partial<PluginConfig>);
    /**
     * Handle health status changes
     */
    private onHealthStatusChange;
    /**
     * Initialize the bridge
     * Detects Claude Code version and TeammateTool availability
     */
    initialize(): Promise<VersionInfo>;
    /**
     * Get version information
     */
    getVersionInfo(): VersionInfo;
    /**
     * Check if TeammateTool is available
     */
    isAvailable(): boolean;
    /**
     * Get current metrics snapshot
     */
    getMetrics(): MetricSnapshot;
    /**
     * Get latency percentile for an operation
     */
    getLatencyPercentile(operation: 'spawnLatency' | 'messageLatency' | 'planApprovalLatency', percentile: number): number;
    /**
     * Reset metrics
     */
    resetMetrics(): void;
    /**
     * Get health check for a specific teammate
     */
    getTeammateHealth(teammateId: string): TeammateHealthCheck | undefined;
    /**
     * Get health report for a team
     */
    getTeamHealth(teamName: string): TeamHealthReport;
    /**
     * Get remaining rate limit quota for an operation
     */
    getRateLimitRemaining(operation: keyof RateLimitConfig): number;
    /**
     * Check if an operation is rate limited
     */
    isRateLimited(operation: keyof RateLimitConfig): boolean;
    /**
     * Reset rate limits
     */
    resetRateLimits(operation?: string): void;
    /**
     * Get circuit breaker state
     */
    getCircuitBreakerState(): CircuitBreakerState;
    /**
     * Reset circuit breaker
     */
    resetCircuitBreaker(): void;
    /**
     * Get Claude Code version
     */
    getClaudeCodeVersion(): string | null;
    /**
     * Enable BMSSP-powered optimizers
     * @returns true if WASM acceleration available, false if using fallback
     */
    enableOptimizers(): Promise<boolean>;
    /**
     * Check if optimizers are enabled
     */
    areOptimizersEnabled(): boolean;
    /**
     * Find optimal message routing path using BMSSP
     */
    findOptimalPath(teamName: string, fromId: string, toId: string): Promise<PathResult | null>;
    /**
     * Get topology statistics for a team
     */
    getTopologyStats(teamName: string): TopologyStats | null;
    /**
     * Get optimization suggestions for team topology
     */
    getTopologyOptimizations(teamName: string): OptimizationResult | null;
    /**
     * Find best teammate for a task using semantic routing
     */
    findBestTeammateForTask(teamName: string, task: {
        id: string;
        description: string;
        requiredSkills: string[];
        priority?: 'urgent' | 'high' | 'normal' | 'low';
    }): Promise<RoutingDecision | null>;
    /**
     * Batch route multiple tasks to teammates
     */
    batchRouteTasksToTeammates(teamName: string, tasks: Array<{
        id: string;
        description: string;
        requiredSkills: string[];
        priority?: 'urgent' | 'high' | 'normal' | 'low';
    }>): Promise<Map<string, RoutingDecision>>;
    /**
     * Update teammate performance for learning
     */
    updateTeammatePerformance(teammateId: string, taskSuccess: boolean, latencyMs: number): void;
    /**
     * Get semantic distance between two teammates
     */
    getTeammateSemanticDistance(id1: string, id2: string): number;
    /**
     * Initialize optimizer for a team
     */
    private initializeTeamOptimizer;
    /**
     * Spawn a new team
     */
    spawnTeam(config: Partial<TeamConfig> & {
        name: string;
    }): Promise<TeamState>;
    /**
     * Discover existing teams
     */
    discoverTeams(): Promise<string[]>;
    /**
     * Load an existing team
     */
    loadTeam(teamName: string): Promise<TeamState>;
    /**
     * Request to join an existing team
     */
    requestJoin(teamName: string, agentInfo: Partial<TeammateInfo> & {
        id: string;
        name: string;
        role: string;
    }): Promise<void>;
    /**
     * Approve a join request
     */
    approveJoin(teamName: string, agentId: string): Promise<void>;
    /**
     * Reject a join request
     */
    rejectJoin(teamName: string, agentId: string, reason?: string): Promise<void>;
    /**
     * Spawn a teammate using native AgentInput
     */
    spawnTeammate(config: TeammateSpawnConfig): Promise<TeammateInfo>;
    /**
     * Build AgentInput for Claude Code Task tool
     */
    buildAgentInput(config: TeammateSpawnConfig): AgentInput;
    /**
     * Send message to a specific teammate
     */
    sendMessage(teamName: string, fromId: string, toId: string, message: {
        type: MessageType;
        payload: unknown;
        priority?: MailboxMessage['priority'];
    }): Promise<MailboxMessage>;
    /**
     * Broadcast message to all teammates
     */
    broadcast(teamName: string, fromId: string, message: {
        type: MessageType;
        payload: unknown;
        priority?: MailboxMessage['priority'];
    }): Promise<MailboxMessage>;
    /**
     * Read messages from mailbox
     */
    readMailbox(teamName: string, teammateId: string): Promise<MailboxMessage[]>;
    /**
     * Submit a plan for approval
     */
    submitPlan(teamName: string, plan: Omit<TeamPlan, 'id' | 'approvals' | 'rejections' | 'status' | 'createdAt'>): Promise<TeamPlan>;
    /**
     * Approve a plan
     */
    approvePlan(teamName: string, planId: string, approverId: string): Promise<void>;
    /**
     * Reject a plan
     */
    rejectPlan(teamName: string, planId: string, rejecterId: string, reason?: string): Promise<void>;
    /**
     * Pause plan execution
     */
    pausePlan(teamName: string, planId: string): Promise<void>;
    /**
     * Resume plan execution
     */
    resumePlan(teamName: string, planId: string, fromStep?: number): Promise<void>;
    /**
     * Launch swarm to execute approved plan
     */
    launchSwarm(teamName: string, planId: string, teammateCount?: number): Promise<ExitPlanModeInput>;
    /**
     * Delegate authority to a teammate
     */
    delegateToTeammate(teamName: string, fromId: string, toId: string, permissions: string[]): Promise<DelegationRecord>;
    /**
     * Revoke delegation from a teammate
     */
    revokeDelegation(teamName: string, fromId: string, toId: string): Promise<void>;
    /**
     * Update team context
     */
    updateTeamContext(teamName: string, updates: Partial<TeamContext>): Promise<TeamContext>;
    /**
     * Get team context
     */
    getTeamContext(teamName: string): TeamContext;
    /**
     * Update teammate permissions
     */
    updateTeammatePermissions(teamName: string, teammateId: string, changes: {
        add?: string[];
        remove?: string[];
    }): Promise<string[]>;
    /**
     * Push team to Claude.ai remote
     */
    pushTeamToRemote(teamName: string): Promise<RemoteSession>;
    /**
     * Sync with remote
     */
    syncWithRemote(teamName: string): Promise<SyncResult>;
    /**
     * Save teammate memory
     */
    saveTeammateMemory(teamName: string, teammateId: string): Promise<void>;
    /**
     * Load teammate memory
     */
    loadTeammateMemory(teamName: string, teammateId: string): Promise<TeammateMemory | null>;
    /**
     * Share transcript between teammates
     */
    shareTranscript(teamName: string, fromId: string, toId: string, options?: {
        start?: number;
        end?: number;
    }): Promise<void>;
    /**
     * Check if team can teleport
     */
    canTeleport(teamName: string, target: TeleportTarget): Promise<{
        canTeleport: boolean;
        blockers: string[];
    }>;
    /**
     * Teleport team to new context
     */
    teleportTeam(teamName: string, target: TeleportTarget): Promise<TeleportResult>;
    /**
     * Request teammate shutdown
     */
    requestShutdown(teamName: string, teammateId: string, reason?: string): Promise<void>;
    /**
     * Approve teammate shutdown
     */
    approveShutdown(teamName: string, teammateId: string): Promise<void>;
    /**
     * Reject teammate shutdown
     */
    rejectShutdown(teamName: string, teammateId: string): Promise<void>;
    /**
     * Cleanup team resources
     */
    cleanup(teamName: string): Promise<void>;
    /**
     * Get team state
     */
    getTeamState(teamName: string): TeamState | undefined;
    /**
     * Get all active teams
     */
    getAllTeams(): Map<string, TeamState>;
    /**
     * Get backend status
     */
    getBackendStatus(): Promise<BackendStatus[]>;
    private ensureAvailable;
    private getTeamOrThrow;
    private getPlanOrThrow;
    private getMailboxPath;
    private writeToMailbox;
    private startMailboxPoller;
    private startMemoryPersistence;
    private saveTeamState;
    /**
     * Performance: Debounced file write to reduce I/O
     */
    private debouncedWrite;
    /**
     * Performance: Flush all pending writes immediately
     */
    private flushPendingWrites;
    /**
     * Performance: Get cached team config or load from disk
     */
    private getCachedTeamConfig;
    /**
     * Performance: Invalidate team config cache
     */
    private invalidateConfigCache;
    private getDelegationChain;
    private getCurrentGitBranch;
    private getCurrentGitRepo;
}
/**
 * Create and initialize a TeammateBridge instance
 */
export declare function createTeammateBridge(config?: Partial<PluginConfig>): Promise<TeammateBridge>;
export default TeammateBridge;
//# sourceMappingURL=teammate-bridge.d.ts.map