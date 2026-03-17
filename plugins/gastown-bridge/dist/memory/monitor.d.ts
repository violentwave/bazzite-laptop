/**
 * Memory Monitoring for Gas Town Bridge Plugin
 *
 * Provides comprehensive memory monitoring, limits, and pressure callbacks.
 * Integrates with object pools and arena allocators to track memory usage.
 *
 * Target: <10MB heap for 10k beads
 *
 * Features:
 * - Real-time memory usage tracking
 * - Configurable memory limits
 * - Memory pressure callbacks
 * - Automatic cleanup triggers
 * - Integration with V8 GC hooks (when available)
 *
 * @module gastown-bridge/memory/monitor
 */
import { EventEmitter } from 'events';
import { type PoolStats } from './pool.js';
/**
 * Memory statistics snapshot
 */
export interface MemoryStats {
    /** Heap memory used (bytes) */
    heapUsed: number;
    /** Heap memory total (bytes) */
    heapTotal: number;
    /** External memory (bytes) */
    external: number;
    /** Array buffers memory (bytes) */
    arrayBuffers: number;
    /** RSS (Resident Set Size) in bytes */
    rss: number;
    /** Pool memory stats */
    pools: {
        totalMemorySaved: number;
        hitRate: number;
        objectsInUse: number;
        objectsAvailable: number;
    };
    /** Arena memory stats */
    arenas: {
        activeArenas: number;
        totalMemoryUsed: number;
        totalMemorySaved: number;
    };
    /** Timestamp of snapshot */
    timestamp: Date;
    /** Whether under memory pressure */
    underPressure: boolean;
}
/**
 * Memory pressure levels
 */
export type MemoryPressureLevel = 'none' | 'low' | 'medium' | 'high' | 'critical';
/**
 * Memory pressure callback
 */
export type MemoryPressureCallback = (level: MemoryPressureLevel, stats: MemoryStats) => void;
/**
 * Memory monitor configuration
 */
export interface MemoryMonitorConfig {
    /** Memory limit in bytes (0 = no limit) */
    memoryLimit?: number;
    /** Low pressure threshold (0-1 of limit) */
    lowPressureThreshold?: number;
    /** Medium pressure threshold (0-1 of limit) */
    mediumPressureThreshold?: number;
    /** High pressure threshold (0-1 of limit) */
    highPressureThreshold?: number;
    /** Critical pressure threshold (0-1 of limit) */
    criticalPressureThreshold?: number;
    /** Polling interval in ms (0 = manual only) */
    pollInterval?: number;
    /** Enable automatic cleanup on pressure */
    autoCleanup?: boolean;
    /** Enable GC hints when available */
    gcHints?: boolean;
}
/**
 * Memory monitor events
 */
export interface MemoryMonitorEvents {
    'pressure:none': (stats: MemoryStats) => void;
    'pressure:low': (stats: MemoryStats) => void;
    'pressure:medium': (stats: MemoryStats) => void;
    'pressure:high': (stats: MemoryStats) => void;
    'pressure:critical': (stats: MemoryStats) => void;
    'limit:exceeded': (stats: MemoryStats) => void;
    'cleanup:triggered': (beforeStats: MemoryStats, afterStats: MemoryStats) => void;
    'snapshot': (stats: MemoryStats) => void;
}
/**
 * Memory Monitor
 *
 * Tracks memory usage and triggers pressure callbacks when thresholds
 * are exceeded. Integrates with object pools and arenas.
 *
 * @example
 * ```typescript
 * const monitor = new MemoryMonitor({
 *   memoryLimit: 10 * 1024 * 1024, // 10MB
 *   pollInterval: 1000,
 *   autoCleanup: true,
 * });
 *
 * monitor.onMemoryPressure((level, stats) => {
 *   console.log(`Memory pressure: ${level}`, stats);
 * });
 *
 * monitor.start();
 * ```
 */
export declare class MemoryMonitor extends EventEmitter {
    private config;
    private pollTimer?;
    private pressureCallbacks;
    private lastPressureLevel;
    private running;
    private statsHistory;
    private maxHistorySize;
    constructor(config?: MemoryMonitorConfig);
    /**
     * Get current memory usage statistics
     */
    getMemoryUsage(): MemoryStats;
    /**
     * Set memory limit
     */
    setMemoryLimit(bytes: number): void;
    /**
     * Get current memory limit
     */
    getMemoryLimit(): number;
    /**
     * Register a memory pressure callback
     */
    onMemoryPressure(callback: MemoryPressureCallback): () => void;
    /**
     * Check current pressure level
     */
    checkPressure(): MemoryPressureLevel;
    /**
     * Start monitoring
     */
    start(): void;
    /**
     * Stop monitoring
     */
    stop(): void;
    /**
     * Manual poll (also called automatically if pollInterval > 0)
     */
    poll(): void;
    /**
     * Trigger memory cleanup
     */
    triggerCleanup(): void;
    /**
     * Get memory trend (bytes/second)
     */
    getMemoryTrend(): number;
    /**
     * Estimate time until limit reached (ms)
     */
    estimateTimeToLimit(): number | null;
    /**
     * Get pool-specific statistics
     */
    getPoolStats(): Record<string, PoolStats>;
    /**
     * Get historical stats
     */
    getHistory(): MemoryStats[];
    /**
     * Clear historical stats
     */
    clearHistory(): void;
    /**
     * Check if running
     */
    isRunning(): boolean;
    /**
     * Get configuration
     */
    getConfig(): Readonly<Required<MemoryMonitorConfig>>;
    /**
     * Update configuration
     */
    updateConfig(config: Partial<MemoryMonitorConfig>): void;
}
/**
 * Get current memory usage (simple API)
 */
export declare function getMemoryUsage(): MemoryStats;
/**
 * Set a memory limit and callback (simple API)
 */
export declare function setMemoryLimit(bytes: number, onPressure?: MemoryPressureCallback): MemoryMonitor;
export declare function onMemoryPressure(callback: MemoryPressureCallback): () => void;
/**
 * Get the default monitor instance
 */
export declare function getDefaultMonitor(): MemoryMonitor | null;
/**
 * Stop and dispose the default monitor
 */
export declare function disposeDefaultMonitor(): void;
/**
 * Memory budget for component-level tracking
 */
export interface MemoryBudget {
    name: string;
    allocated: number;
    used: number;
    limit: number;
}
/**
 * Memory budget manager
 */
export declare class MemoryBudgetManager {
    private budgets;
    private totalLimit;
    constructor(totalLimit?: number);
    /**
     * Allocate a budget for a component
     */
    allocateBudget(name: string, limit: number): boolean;
    /**
     * Update usage for a budget
     */
    updateUsage(name: string, used: number): void;
    /**
     * Check if a budget is exceeded
     */
    isExceeded(name: string): boolean;
    /**
     * Get budget for a component
     */
    getBudget(name: string): MemoryBudget | undefined;
    /**
     * Get all budgets
     */
    getAllBudgets(): MemoryBudget[];
    /**
     * Get total allocated budget
     */
    getTotalAllocated(): number;
    /**
     * Get total used
     */
    getTotalUsed(): number;
    /**
     * Free a budget
     */
    freeBudget(name: string): void;
    /**
     * Get total limit
     */
    getTotalLimit(): number;
    /**
     * Set total limit
     */
    setTotalLimit(limit: number): void;
}
/**
 * Global memory budget manager for 10MB target
 */
export declare const memoryBudget: MemoryBudgetManager;
export default MemoryMonitor;
//# sourceMappingURL=monitor.d.ts.map