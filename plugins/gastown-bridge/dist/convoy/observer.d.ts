/**
 * Convoy Observer
 *
 * Monitors convoy completion by observing issue state changes
 * and detecting when all tracked issues are complete. Uses
 * WASM-accelerated graph analysis for dependency resolution.
 *
 * Features:
 * - Watch convoys for completion
 * - Detect blocking issues
 * - Identify ready-to-work issues
 * - WASM-accelerated dependency graph analysis
 * - Configurable polling intervals
 *
 * @module gastown-bridge/convoy/observer
 */
import { EventEmitter } from 'events';
import type { Convoy, ConvoyProgress } from '../types.js';
import { BdBridge } from '../bridges/bd-bridge.js';
import { ConvoyTracker } from './tracker.js';
import { LazyObserver } from '../memory/index.js';
/**
 * WASM graph module interface
 */
export interface WasmGraphModule {
    /** Check if dependency graph has cycles */
    has_cycle(beadsJson: string): boolean;
    /** Find nodes participating in cycles */
    find_cycle_nodes(beadsJson: string): string;
    /** Get beads with no unresolved dependencies */
    get_ready_beads(beadsJson: string): string;
    /** Compute execution levels for parallel processing */
    compute_levels(beadsJson: string): string;
    /** Topological sort of beads */
    topo_sort(beadsJson: string): string;
    /** Critical path analysis */
    critical_path(beadsJson: string): string;
}
/**
 * Completion callback signature
 */
export type CompletionCallback = (convoy: Convoy, allComplete: boolean) => void;
/**
 * Observer watch handle
 */
export interface WatchHandle {
    /** Convoy ID being watched */
    convoyId: string;
    /** Stop watching */
    stop(): void;
    /** Check if still watching */
    isActive(): boolean;
}
/**
 * Observer configuration
 */
export interface ConvoyObserverConfig {
    /** BD bridge instance */
    bdBridge: BdBridge;
    /** Convoy tracker instance */
    tracker: ConvoyTracker;
    /** Optional WASM graph module */
    wasmModule?: WasmGraphModule;
    /** Initial polling interval in milliseconds */
    pollInterval?: number;
    /** Maximum poll attempts before giving up */
    maxPollAttempts?: number;
    /** Enable WASM acceleration (falls back to JS if unavailable) */
    useWasm?: boolean;
    /** Enable exponential backoff for polling */
    useExponentialBackoff?: boolean;
    /** Maximum backoff interval in milliseconds */
    maxBackoffInterval?: number;
    /** Backoff multiplier (default: 1.5) */
    backoffMultiplier?: number;
    /** Enable delta-based updates (only emit on changes) */
    deltaUpdatesOnly?: boolean;
    /** Debounce interval for progress updates in milliseconds */
    progressDebounceMs?: number;
}
/**
 * Blocker information
 */
export interface BlockerInfo {
    /** Issue ID that is blocked */
    blockedIssue: string;
    /** Issue IDs that are blocking */
    blockers: string[];
    /** True if blockers are from within the convoy */
    internalBlockers: boolean;
}
/**
 * Ready issue information
 */
export interface ReadyIssueInfo {
    /** Issue ID */
    id: string;
    /** Issue title */
    title: string;
    /** Priority */
    priority: number;
    /** Execution level (for parallel processing) */
    level: number;
}
/**
 * Completion check result
 */
export interface CompletionCheckResult {
    /** True if all issues are complete */
    allComplete: boolean;
    /** Progress statistics */
    progress: ConvoyProgress;
    /** Issues that are still open */
    openIssues: string[];
    /** Issues that are in progress */
    inProgressIssues: string[];
    /** Issues that are blocked */
    blockedIssues: BlockerInfo[];
    /** Issues ready to work on */
    readyIssues: ReadyIssueInfo[];
    /** True if there are dependency cycles */
    hasCycles: boolean;
    /** Issues involved in cycles */
    cycleIssues: string[];
}
/**
 * Logger interface
 */
export interface ObserverLogger {
    debug: (msg: string, meta?: Record<string, unknown>) => void;
    info: (msg: string, meta?: Record<string, unknown>) => void;
    warn: (msg: string, meta?: Record<string, unknown>) => void;
    error: (msg: string, meta?: Record<string, unknown>) => void;
}
/**
 * Convoy Observer
 *
 * Monitors convoys for completion and provides dependency analysis.
 *
 * @example
 * ```typescript
 * const observer = new ConvoyObserver({
 *   bdBridge,
 *   tracker,
 *   pollInterval: 5000,
 *   useWasm: true,
 * });
 *
 * // Watch for completion
 * const handle = observer.watch(convoyId, (convoy, complete) => {
 *   if (complete) {
 *     console.log('Convoy complete!');
 *   }
 * });
 *
 * // Check blockers
 * const blockers = await observer.getBlockers(convoyId);
 *
 * // Get ready issues
 * const ready = await observer.getReadyIssues(convoyId);
 *
 * // Stop watching
 * handle.stop();
 * ```
 */
export declare class ConvoyObserver extends EventEmitter {
    private bdBridge;
    private tracker;
    private wasmModule?;
    private logger;
    private config;
    private watchers;
    private readonly beadCache;
    private readonly completionCache;
    private readonly fetchDedup;
    private readonly progressEmitters;
    private pendingSubscriptions;
    private subscriptionFlushTimer;
    constructor(config: ConvoyObserverConfig, logger?: ObserverLogger);
    /**
     * Watch a convoy for completion
     *
     * @param convoyId - Convoy ID to watch
     * @param callback - Called on each check with completion status
     * @returns Watch handle to stop watching
     */
    watch(convoyId: string, callback: CompletionCallback): WatchHandle;
    /**
     * Batch subscribe to multiple convoys
     * Subscriptions are batched and flushed together for efficiency
     *
     * @param convoyId - Convoy ID to watch
     * @param callback - Callback for completion status
     */
    batchSubscribe(convoyId: string, callback: CompletionCallback): void;
    /**
     * Flush pending subscriptions
     */
    private flushSubscriptions;
    /**
     * Check if all issues in a convoy are complete
     *
     * @param convoyId - Convoy ID
     * @returns Completion check result with detailed status
     */
    checkCompletion(convoyId: string): Promise<CompletionCheckResult>;
    /**
     * Get blockers for all issues in a convoy
     *
     * @param convoyId - Convoy ID
     * @returns Array of blocker information
     */
    getBlockers(convoyId: string): Promise<BlockerInfo[]>;
    /**
     * Get issues ready to work on (no unresolved dependencies)
     *
     * @param convoyId - Convoy ID
     * @returns Array of ready issue information
     */
    getReadyIssues(convoyId: string): Promise<ReadyIssueInfo[]>;
    /**
     * Get execution order for convoy issues
     *
     * @param convoyId - Convoy ID
     * @returns Ordered array of issue IDs
     */
    getExecutionOrder(convoyId: string): Promise<string[]>;
    /**
     * Stop watching a convoy
     */
    stopWatching(convoyId: string): void;
    /**
     * Stop all watchers
     */
    stopAll(): void;
    /**
     * Set WASM module
     */
    setWasmModule(module: WasmGraphModule): void;
    /**
     * Check if WASM is available
     */
    isWasmAvailable(): boolean;
    /**
     * Poll convoy for completion with exponential backoff
     */
    private pollConvoyWithBackoff;
    /**
     * Legacy poll convoy method (without backoff)
     * @deprecated Use pollConvoyWithBackoff instead
     */
    private pollConvoy;
    /**
     * Fetch beads by IDs with caching, batch deduplication, and object pooling.
     * Uses PooledBead from memory module for reduced allocations.
     */
    private fetchBeads;
    /**
     * Map CLI bead type to Gas Town status
     */
    private mapBeadStatus;
    /**
     * Convert beads to WASM node format
     */
    private beadsToWasmNodes;
    /**
     * Analyze dependencies with WASM
     */
    private analyzeWithWasm;
    /**
     * Analyze dependencies with JavaScript (fallback)
     */
    private analyzeWithJS;
    /**
     * Detect cycles using DFS (JavaScript)
     */
    private detectCyclesJS;
    /**
     * Find nodes in cycles (JavaScript)
     */
    private findCycleNodesJS;
    /**
     * Topological sort using Kahn's algorithm (JavaScript)
     */
    private topoSortJS;
    /**
     * Clean up resources
     */
    dispose(): void;
}
/**
 * Create a new convoy observer instance
 */
export declare function createConvoyObserver(config: ConvoyObserverConfig, logger?: ObserverLogger): ConvoyObserver;
/**
 * Create a lazy-initialized convoy observer.
 * The observer is only created when first accessed (via watch() or checkCompletion()).
 * Useful for deferring initialization until convoy monitoring is actually needed.
 *
 * @example
 * ```typescript
 * const lazyObserver = createLazyConvoyObserver(config);
 *
 * // Observer is NOT created yet
 * console.log(lazyObserver.getWatchCount()); // 0
 *
 * // First watch triggers observer creation
 * const observer = await lazyObserver.watch();
 * const handle = observer.watch(convoyId, callback);
 *
 * // When done, unwatch to potentially dispose
 * await lazyObserver.unwatch();
 * ```
 */
export declare function createLazyConvoyObserver(config: ConvoyObserverConfig, logger?: ObserverLogger): LazyObserver<ConvoyObserver>;
/**
 * Get lazy observer statistics
 */
export declare function getLazyObserverStats(lazyObserver: LazyObserver<ConvoyObserver>): {
    isActive: boolean;
    watchCount: number;
};
export default ConvoyObserver;
//# sourceMappingURL=observer.d.ts.map