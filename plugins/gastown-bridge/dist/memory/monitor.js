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
import { getAllPoolStats, getPoolEfficiencySummary, clearAllPools, } from './pool.js';
import { arenaManager } from './arena.js';
// ============================================================================
// Memory Monitor Implementation
// ============================================================================
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
export class MemoryMonitor extends EventEmitter {
    config;
    pollTimer;
    pressureCallbacks = [];
    lastPressureLevel = 'none';
    running = false;
    // Historical stats for trend analysis
    statsHistory = [];
    maxHistorySize = 60; // 1 minute at 1s intervals
    constructor(config) {
        super();
        this.config = {
            memoryLimit: config?.memoryLimit ?? 0,
            lowPressureThreshold: config?.lowPressureThreshold ?? 0.5,
            mediumPressureThreshold: config?.mediumPressureThreshold ?? 0.7,
            highPressureThreshold: config?.highPressureThreshold ?? 0.85,
            criticalPressureThreshold: config?.criticalPressureThreshold ?? 0.95,
            pollInterval: config?.pollInterval ?? 0,
            autoCleanup: config?.autoCleanup ?? false,
            gcHints: config?.gcHints ?? true,
        };
    }
    /**
     * Get current memory usage statistics
     */
    getMemoryUsage() {
        const memUsage = process.memoryUsage();
        const poolSummary = getPoolEfficiencySummary();
        const arenaStats = arenaManager.getStats();
        // Calculate arena memory
        let arenaMemory = 0;
        for (const stats of Object.values(arenaStats.arenaStats)) {
            arenaMemory += stats.memoryUsed;
        }
        const stats = {
            heapUsed: memUsage.heapUsed,
            heapTotal: memUsage.heapTotal,
            external: memUsage.external,
            arrayBuffers: memUsage.arrayBuffers,
            rss: memUsage.rss,
            pools: {
                totalMemorySaved: poolSummary.totalMemorySavedKB * 1024,
                hitRate: poolSummary.totalHitRate,
                objectsInUse: poolSummary.totalObjectsInUse,
                objectsAvailable: poolSummary.totalObjectsAvailable,
            },
            arenas: {
                activeArenas: arenaStats.activeArenas,
                totalMemoryUsed: arenaMemory,
                totalMemorySaved: arenaStats.totalMemorySaved,
            },
            timestamp: new Date(),
            underPressure: this.lastPressureLevel !== 'none',
        };
        return stats;
    }
    /**
     * Set memory limit
     */
    setMemoryLimit(bytes) {
        this.config.memoryLimit = bytes;
    }
    /**
     * Get current memory limit
     */
    getMemoryLimit() {
        return this.config.memoryLimit;
    }
    /**
     * Register a memory pressure callback
     */
    onMemoryPressure(callback) {
        this.pressureCallbacks.push(callback);
        return () => {
            const index = this.pressureCallbacks.indexOf(callback);
            if (index !== -1) {
                this.pressureCallbacks.splice(index, 1);
            }
        };
    }
    /**
     * Check current pressure level
     */
    checkPressure() {
        if (this.config.memoryLimit === 0) {
            return 'none';
        }
        const stats = this.getMemoryUsage();
        const usage = stats.heapUsed / this.config.memoryLimit;
        if (usage >= this.config.criticalPressureThreshold) {
            return 'critical';
        }
        if (usage >= this.config.highPressureThreshold) {
            return 'high';
        }
        if (usage >= this.config.mediumPressureThreshold) {
            return 'medium';
        }
        if (usage >= this.config.lowPressureThreshold) {
            return 'low';
        }
        return 'none';
    }
    /**
     * Start monitoring
     */
    start() {
        if (this.running)
            return;
        this.running = true;
        if (this.config.pollInterval > 0) {
            this.pollTimer = setInterval(() => {
                this.poll();
            }, this.config.pollInterval);
        }
    }
    /**
     * Stop monitoring
     */
    stop() {
        this.running = false;
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = undefined;
        }
    }
    /**
     * Manual poll (also called automatically if pollInterval > 0)
     */
    poll() {
        const stats = this.getMemoryUsage();
        const level = this.checkPressure();
        // Add to history
        this.statsHistory.push(stats);
        if (this.statsHistory.length > this.maxHistorySize) {
            this.statsHistory.shift();
        }
        // Emit snapshot event
        this.emit('snapshot', stats);
        // Check for pressure level changes
        if (level !== this.lastPressureLevel) {
            this.lastPressureLevel = level;
            stats.underPressure = level !== 'none';
            // Emit pressure event
            this.emit(`pressure:${level}`, stats);
            // Call callbacks
            for (const callback of this.pressureCallbacks) {
                try {
                    callback(level, stats);
                }
                catch (error) {
                    console.error('[MemoryMonitor] Pressure callback error:', error);
                }
            }
            // Auto cleanup on high/critical pressure
            if (this.config.autoCleanup && (level === 'high' || level === 'critical')) {
                this.triggerCleanup();
            }
        }
        // Check if limit exceeded
        if (this.config.memoryLimit > 0 && stats.heapUsed > this.config.memoryLimit) {
            this.emit('limit:exceeded', stats);
        }
    }
    /**
     * Trigger memory cleanup
     */
    triggerCleanup() {
        const beforeStats = this.getMemoryUsage();
        // Clear object pools
        clearAllPools();
        // Reset all arenas
        arenaManager.resetAll();
        // Request GC if available and hints enabled
        if (this.config.gcHints && typeof global.gc === 'function') {
            global.gc();
        }
        const afterStats = this.getMemoryUsage();
        this.emit('cleanup:triggered', beforeStats, afterStats);
    }
    /**
     * Get memory trend (bytes/second)
     */
    getMemoryTrend() {
        if (this.statsHistory.length < 2) {
            return 0;
        }
        const oldest = this.statsHistory[0];
        const newest = this.statsHistory[this.statsHistory.length - 1];
        const timeDiff = newest.timestamp.getTime() - oldest.timestamp.getTime();
        if (timeDiff === 0)
            return 0;
        const memoryDiff = newest.heapUsed - oldest.heapUsed;
        return (memoryDiff / timeDiff) * 1000; // bytes per second
    }
    /**
     * Estimate time until limit reached (ms)
     */
    estimateTimeToLimit() {
        if (this.config.memoryLimit === 0) {
            return null;
        }
        const trend = this.getMemoryTrend();
        if (trend <= 0) {
            return null; // Memory is stable or decreasing
        }
        const stats = this.getMemoryUsage();
        const remaining = this.config.memoryLimit - stats.heapUsed;
        return (remaining / trend) * 1000;
    }
    /**
     * Get pool-specific statistics
     */
    getPoolStats() {
        return getAllPoolStats();
    }
    /**
     * Get historical stats
     */
    getHistory() {
        return [...this.statsHistory];
    }
    /**
     * Clear historical stats
     */
    clearHistory() {
        this.statsHistory.length = 0;
    }
    /**
     * Check if running
     */
    isRunning() {
        return this.running;
    }
    /**
     * Get configuration
     */
    getConfig() {
        return { ...this.config };
    }
    /**
     * Update configuration
     */
    updateConfig(config) {
        Object.assign(this.config, config);
        // Restart polling if interval changed
        if (config.pollInterval !== undefined && this.running) {
            this.stop();
            this.start();
        }
    }
}
// ============================================================================
// Convenience Functions
// ============================================================================
/**
 * Get current memory usage (simple API)
 */
export function getMemoryUsage() {
    const monitor = new MemoryMonitor();
    return monitor.getMemoryUsage();
}
/**
 * Set a memory limit and callback (simple API)
 */
export function setMemoryLimit(bytes, onPressure) {
    const monitor = new MemoryMonitor({
        memoryLimit: bytes,
        pollInterval: 1000,
        autoCleanup: true,
    });
    if (onPressure) {
        monitor.onMemoryPressure(onPressure);
    }
    monitor.start();
    return monitor;
}
/**
 * Simple pressure callback registration (uses default monitor)
 */
let defaultMonitor = null;
export function onMemoryPressure(callback) {
    if (!defaultMonitor) {
        defaultMonitor = new MemoryMonitor({
            memoryLimit: 10 * 1024 * 1024, // 10MB default
            pollInterval: 1000,
            autoCleanup: true,
        });
        defaultMonitor.start();
    }
    return defaultMonitor.onMemoryPressure(callback);
}
/**
 * Get the default monitor instance
 */
export function getDefaultMonitor() {
    return defaultMonitor;
}
/**
 * Stop and dispose the default monitor
 */
export function disposeDefaultMonitor() {
    if (defaultMonitor) {
        defaultMonitor.stop();
        defaultMonitor = null;
    }
}
/**
 * Memory budget manager
 */
export class MemoryBudgetManager {
    budgets = new Map();
    totalLimit;
    constructor(totalLimit = 10 * 1024 * 1024) {
        this.totalLimit = totalLimit;
    }
    /**
     * Allocate a budget for a component
     */
    allocateBudget(name, limit) {
        const currentTotal = this.getTotalAllocated();
        if (currentTotal + limit > this.totalLimit) {
            return false;
        }
        this.budgets.set(name, {
            name,
            allocated: limit,
            used: 0,
            limit,
        });
        return true;
    }
    /**
     * Update usage for a budget
     */
    updateUsage(name, used) {
        const budget = this.budgets.get(name);
        if (budget) {
            budget.used = used;
        }
    }
    /**
     * Check if a budget is exceeded
     */
    isExceeded(name) {
        const budget = this.budgets.get(name);
        return budget ? budget.used > budget.limit : false;
    }
    /**
     * Get budget for a component
     */
    getBudget(name) {
        return this.budgets.get(name);
    }
    /**
     * Get all budgets
     */
    getAllBudgets() {
        return Array.from(this.budgets.values());
    }
    /**
     * Get total allocated budget
     */
    getTotalAllocated() {
        return Array.from(this.budgets.values()).reduce((sum, b) => sum + b.allocated, 0);
    }
    /**
     * Get total used
     */
    getTotalUsed() {
        return Array.from(this.budgets.values()).reduce((sum, b) => sum + b.used, 0);
    }
    /**
     * Free a budget
     */
    freeBudget(name) {
        this.budgets.delete(name);
    }
    /**
     * Get total limit
     */
    getTotalLimit() {
        return this.totalLimit;
    }
    /**
     * Set total limit
     */
    setTotalLimit(limit) {
        this.totalLimit = limit;
    }
}
/**
 * Global memory budget manager for 10MB target
 */
export const memoryBudget = new MemoryBudgetManager(10 * 1024 * 1024);
// Pre-allocate budgets for major components
memoryBudget.allocateBudget('beads', 5 * 1024 * 1024); // 5MB for beads
memoryBudget.allocateBudget('formulas', 1 * 1024 * 1024); // 1MB for formulas
memoryBudget.allocateBudget('convoys', 1 * 1024 * 1024); // 1MB for convoys
memoryBudget.allocateBudget('wasm', 2 * 1024 * 1024); // 2MB for WASM
memoryBudget.allocateBudget('misc', 1 * 1024 * 1024); // 1MB for misc
export default MemoryMonitor;
//# sourceMappingURL=monitor.js.map