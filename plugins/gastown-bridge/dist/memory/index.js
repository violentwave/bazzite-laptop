/**
 * Memory Management Module for Gas Town Bridge Plugin
 *
 * Provides comprehensive memory optimization through:
 * - Object pooling for frequently allocated objects (Bead, Formula, Step, Convoy, Molecule)
 * - Arena allocators for batch operations with O(1) reset
 * - Memory monitoring with pressure callbacks
 * - Lazy loading for deferred resource initialization
 *
 * Target: 75% memory reduction, <10MB heap for 10k beads
 *
 * @module gastown-bridge/memory
 */
// ============================================================================
// Object Pooling
// ============================================================================
export { 
// Core pool class
ObjectPool, 
// Pooled object classes
PooledBead, PooledStep, PooledFormula, PooledConvoy, PooledMolecule, 
// Pre-configured pool instances
beadPool, formulaPool, stepPool, convoyPool, moleculePool, getAllPoolStats, getTotalMemorySaved, clearAllPools, preWarmAllPools, getPoolEfficiencySummary, } from './pool.js';
// ============================================================================
// Arena Allocator
// ============================================================================
export { 
// Core arena class
Arena, 
// Scoped arena utilities
scopedArena, withArena, withArenaSync, 
// Arena management
ArenaManager, arenaManager, } from './arena.js';
// ============================================================================
// Memory Monitoring
// ============================================================================
export { 
// Core monitor class
MemoryMonitor, 
// Convenience functions
getMemoryUsage, setMemoryLimit, onMemoryPressure, getDefaultMonitor, disposeDefaultMonitor, 
// Memory budget management
MemoryBudgetManager, memoryBudget, } from './monitor.js';
// ============================================================================
// Lazy Loading
// ============================================================================
export { 
// Core lazy class
Lazy, 
// Singleton management
getLazySingleton, disposeLazySingleton, disposeAllLazySingletons, 
// Specialized lazy loaders
LazyModule, LazyBridge, LazyWasm, LazyObserver, 
// Utilities
createLazyProperty, } from './lazy.js';
// ============================================================================
// Integrated Memory Management
// ============================================================================
import { clearAllPools, preWarmAllPools, getAllPoolStats, getPoolEfficiencySummary, } from './pool.js';
import { arenaManager } from './arena.js';
import { MemoryMonitor } from './monitor.js';
import { disposeAllLazySingletons } from './lazy.js';
const state = {
    initialized: false,
    monitor: null,
    config: {},
};
/**
 * Initialize the memory management system
 *
 * @example
 * ```typescript
 * import { initializeMemorySystem, getSystemMemoryStats } from './memory/index.js';
 *
 * await initializeMemorySystem({
 *   memoryLimit: 10 * 1024 * 1024, // 10MB
 *   autoCleanup: true,
 *   preWarmPools: true,
 * });
 *
 * // Monitor memory usage
 * const stats = getSystemMemoryStats();
 * console.log('Heap used:', stats.heapUsed);
 * ```
 */
export function initializeMemorySystem(config) {
    if (state.initialized) {
        console.warn('[memory] Memory system already initialized');
        return;
    }
    state.config = {
        memoryLimit: config?.memoryLimit ?? 10 * 1024 * 1024, // 10MB default
        autoCleanup: config?.autoCleanup ?? true,
        preWarmPools: config?.preWarmPools ?? false,
        pollInterval: config?.pollInterval ?? 5000,
    };
    // Create and start monitor
    state.monitor = new MemoryMonitor({
        memoryLimit: state.config.memoryLimit,
        autoCleanup: state.config.autoCleanup,
        pollInterval: state.config.pollInterval,
    });
    state.monitor.start();
    // Pre-warm pools if requested
    if (state.config.preWarmPools) {
        preWarmAllPools();
    }
    state.initialized = true;
    console.log('[memory] Memory system initialized', {
        limit: `${(state.config.memoryLimit / (1024 * 1024)).toFixed(2)}MB`,
        autoCleanup: state.config.autoCleanup,
        preWarmed: state.config.preWarmPools,
    });
}
/**
 * Get system memory statistics
 */
export function getSystemMemoryStats() {
    return state.monitor?.getMemoryUsage() ?? null;
}
/**
 * Get comprehensive memory report
 */
export function getMemoryReport() {
    return {
        system: getSystemMemoryStats(),
        pools: getAllPoolStats(),
        poolEfficiency: getPoolEfficiencySummary(),
        arenas: arenaManager.getStats(),
        config: state.config,
    };
}
/**
 * Trigger manual memory cleanup
 */
export function triggerMemoryCleanup() {
    // Clear all object pools
    clearAllPools();
    // Reset all arenas
    arenaManager.resetAll();
    // Dispose lazy singletons
    disposeAllLazySingletons().catch(console.error);
    // Trigger monitor cleanup
    state.monitor?.triggerCleanup();
    console.log('[memory] Manual cleanup completed');
}
/**
 * Shutdown the memory system
 */
export async function shutdownMemorySystem() {
    if (!state.initialized)
        return;
    // Stop monitor
    state.monitor?.stop();
    state.monitor = null;
    // Clear pools
    clearAllPools();
    // Dispose arenas
    arenaManager.disposeAll();
    // Dispose lazy singletons
    await disposeAllLazySingletons();
    state.initialized = false;
    console.log('[memory] Memory system shut down');
}
/**
 * Check if memory system is initialized
 */
export function isMemorySystemInitialized() {
    return state.initialized;
}
/**
 * Get memory system monitor
 */
export function getMemoryMonitor() {
    return state.monitor;
}
// ============================================================================
// Quick-access utilities for common operations
// ============================================================================
import { beadPool, stepPool, formulaPool, convoyPool, moleculePool, PooledBead, PooledStep, PooledFormula, PooledConvoy, PooledMolecule, } from './pool.js';
/**
 * Acquire a pooled bead
 */
export function acquireBead() {
    return beadPool.acquire();
}
/**
 * Release a pooled bead
 */
export function releaseBead(bead) {
    beadPool.release(bead);
}
/**
 * Acquire a pooled step
 */
export function acquireStep() {
    return stepPool.acquire();
}
/**
 * Release a pooled step
 */
export function releaseStep(step) {
    stepPool.release(step);
}
/**
 * Acquire a pooled formula
 */
export function acquireFormula() {
    return formulaPool.acquire();
}
/**
 * Release a pooled formula
 */
export function releaseFormula(formula) {
    formulaPool.release(formula);
}
/**
 * Acquire a pooled convoy
 */
export function acquireConvoy() {
    return convoyPool.acquire();
}
/**
 * Release a pooled convoy
 */
export function releaseConvoy(convoy) {
    convoyPool.release(convoy);
}
/**
 * Acquire a pooled molecule
 */
export function acquireMolecule() {
    return moleculePool.acquire();
}
/**
 * Release a pooled molecule
 */
export function releaseMolecule(molecule) {
    moleculePool.release(molecule);
}
//# sourceMappingURL=index.js.map