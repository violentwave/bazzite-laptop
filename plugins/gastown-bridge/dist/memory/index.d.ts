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
export { ObjectPool, type Poolable, type PoolStats, type PoolConfig, PooledBead, PooledStep, PooledFormula, PooledConvoy, PooledMolecule, beadPool, formulaPool, stepPool, convoyPool, moleculePool, type PoolType, getAllPoolStats, getTotalMemorySaved, clearAllPools, preWarmAllPools, getPoolEfficiencySummary, } from './pool.js';
export { Arena, type ArenaStats, type ArenaConfig, type AllocatableType, type TypeMap, scopedArena, withArena, withArenaSync, ArenaManager, arenaManager, } from './arena.js';
export { MemoryMonitor, type MemoryStats, type MemoryPressureLevel, type MemoryPressureCallback, type MemoryMonitorConfig, type MemoryMonitorEvents, getMemoryUsage, setMemoryLimit, onMemoryPressure, getDefaultMonitor, disposeDefaultMonitor, MemoryBudgetManager, type MemoryBudget, memoryBudget, } from './monitor.js';
export { Lazy, type LazyState, type LazyOptions, type LazyStats, getLazySingleton, disposeLazySingleton, disposeAllLazySingletons, LazyModule, LazyBridge, LazyWasm, LazyObserver, createLazyProperty, } from './lazy.js';
import { getAllPoolStats, getPoolEfficiencySummary } from './pool.js';
import { arenaManager } from './arena.js';
import { MemoryMonitor, type MemoryStats } from './monitor.js';
/**
 * Memory system configuration
 */
export interface MemorySystemConfig {
    /** Memory limit in bytes (default: 10MB) */
    memoryLimit?: number;
    /** Enable auto-cleanup on pressure */
    autoCleanup?: boolean;
    /** Pre-warm pools on init */
    preWarmPools?: boolean;
    /** Polling interval for monitor (ms) */
    pollInterval?: number;
}
/**
 * Memory system state
 */
export interface MemorySystemState {
    initialized: boolean;
    monitor: MemoryMonitor | null;
    config: MemorySystemConfig;
}
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
export declare function initializeMemorySystem(config?: MemorySystemConfig): void;
/**
 * Get system memory statistics
 */
export declare function getSystemMemoryStats(): MemoryStats | null;
/**
 * Get comprehensive memory report
 */
export declare function getMemoryReport(): {
    system: MemoryStats | null;
    pools: ReturnType<typeof getAllPoolStats>;
    poolEfficiency: ReturnType<typeof getPoolEfficiencySummary>;
    arenas: ReturnType<typeof arenaManager.getStats>;
    config: MemorySystemConfig;
};
/**
 * Trigger manual memory cleanup
 */
export declare function triggerMemoryCleanup(): void;
/**
 * Shutdown the memory system
 */
export declare function shutdownMemorySystem(): Promise<void>;
/**
 * Check if memory system is initialized
 */
export declare function isMemorySystemInitialized(): boolean;
/**
 * Get memory system monitor
 */
export declare function getMemoryMonitor(): MemoryMonitor | null;
import { PooledBead, PooledStep, PooledFormula, PooledConvoy, PooledMolecule } from './pool.js';
/**
 * Acquire a pooled bead
 */
export declare function acquireBead(): PooledBead;
/**
 * Release a pooled bead
 */
export declare function releaseBead(bead: PooledBead): void;
/**
 * Acquire a pooled step
 */
export declare function acquireStep(): PooledStep;
/**
 * Release a pooled step
 */
export declare function releaseStep(step: PooledStep): void;
/**
 * Acquire a pooled formula
 */
export declare function acquireFormula(): PooledFormula;
/**
 * Release a pooled formula
 */
export declare function releaseFormula(formula: PooledFormula): void;
/**
 * Acquire a pooled convoy
 */
export declare function acquireConvoy(): PooledConvoy;
/**
 * Release a pooled convoy
 */
export declare function releaseConvoy(convoy: PooledConvoy): void;
/**
 * Acquire a pooled molecule
 */
export declare function acquireMolecule(): PooledMolecule;
/**
 * Release a pooled molecule
 */
export declare function releaseMolecule(molecule: PooledMolecule): void;
//# sourceMappingURL=index.d.ts.map