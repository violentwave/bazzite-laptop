/**
 * Arena Allocator for Gas Town Bridge Plugin
 *
 * Provides bulk memory allocation with single-operation deallocation.
 * Ideal for batch operations where many objects are created and then
 * discarded together (e.g., convoy graph operations, formula parsing).
 *
 * Benefits:
 * - O(1) reset/clear operation
 * - Reduced GC pressure for batch operations
 * - Better memory locality
 * - Predictable memory usage
 *
 * @module gastown-bridge/memory/arena
 */
import { ObjectPool, PooledBead, PooledStep, PooledFormula, PooledConvoy, PooledMolecule, } from './pool.js';
// ============================================================================
// Arena Implementation
// ============================================================================
/**
 * Arena Allocator
 *
 * Manages bulk allocations that are reset together. Uses underlying
 * object pools when available for maximum efficiency.
 *
 * @example
 * ```typescript
 * const arena = new Arena('convoy-analysis');
 *
 * // Allocate objects for batch operation
 * const beads = arena.allocateMany('bead', 100);
 * const steps = arena.allocateMany('step', 50);
 *
 * // Process...
 *
 * // Single O(1) reset clears everything
 * arena.reset();
 * ```
 */
export class Arena {
    name;
    config;
    allocations = [];
    stats = {
        totalAllocations: 0,
        currentAllocations: 0,
        resetCount: 0,
        peakAllocations: 0,
        memoryUsed: 0,
        memorySaved: 0,
    };
    // Type-specific pools for arena allocations
    beadPool;
    stepPool;
    formulaPool;
    convoyPool;
    moleculePool;
    constructor(name, config) {
        this.name = name ?? config?.name ?? 'arena';
        this.config = {
            name: this.name,
            initialCapacity: config?.initialCapacity ?? 100,
            maxAllocations: config?.maxAllocations ?? 0,
            returnToPool: config?.returnToPool ?? true,
        };
        // Create arena-specific pools (separate from global pools)
        this.beadPool = new ObjectPool(() => new PooledBead(), {
            initialSize: 0,
            maxSize: 10000,
            objectSizeBytes: 512,
        });
        this.stepPool = new ObjectPool(() => new PooledStep(), {
            initialSize: 0,
            maxSize: 5000,
            objectSizeBytes: 256,
        });
        this.formulaPool = new ObjectPool(() => new PooledFormula(), {
            initialSize: 0,
            maxSize: 500,
            objectSizeBytes: 1024,
        });
        this.convoyPool = new ObjectPool(() => new PooledConvoy(), {
            initialSize: 0,
            maxSize: 200,
            objectSizeBytes: 768,
        });
        this.moleculePool = new ObjectPool(() => new PooledMolecule(), {
            initialSize: 0,
            maxSize: 5000,
            objectSizeBytes: 384,
        });
        // Pre-allocate array capacity
        if (this.config.initialCapacity > 0) {
            this.allocations = new Array(this.config.initialCapacity);
            this.allocations.length = 0;
        }
    }
    /**
     * Allocate an object from the arena
     *
     * Uses pooled objects when available for the given type.
     */
    allocate(factory, sizeBytes = 256) {
        this.checkMaxAllocations();
        const obj = factory();
        this.trackAllocation(obj, 'generic', sizeBytes);
        return obj;
    }
    /**
     * Allocate a typed object from the arena pools
     */
    allocateTyped(type) {
        this.checkMaxAllocations();
        let obj;
        let sizeBytes;
        switch (type) {
            case 'bead':
                obj = this.beadPool.acquire();
                sizeBytes = 512;
                break;
            case 'step':
                obj = this.stepPool.acquire();
                sizeBytes = 256;
                break;
            case 'formula':
                obj = this.formulaPool.acquire();
                sizeBytes = 1024;
                break;
            case 'convoy':
                obj = this.convoyPool.acquire();
                sizeBytes = 768;
                break;
            case 'molecule':
                obj = this.moleculePool.acquire();
                sizeBytes = 384;
                break;
            default:
                throw new Error(`Unknown allocatable type: ${type}`);
        }
        this.trackAllocation(obj, type, sizeBytes);
        return obj;
    }
    /**
     * Allocate multiple typed objects
     */
    allocateMany(type, count) {
        const results = new Array(count);
        for (let i = 0; i < count; i++) {
            results[i] = this.allocateTyped(type);
        }
        return results;
    }
    /**
     * Reset the arena, returning all objects to their pools
     *
     * This is an O(n) operation where n is the number of allocations,
     * but it's a single operation instead of n individual deallocations.
     */
    reset() {
        if (this.config.returnToPool) {
            // Return objects to their respective pools
            for (const allocation of this.allocations) {
                this.returnToPool(allocation);
            }
        }
        // Track stats before reset
        const memoryFreed = this.stats.memoryUsed;
        this.stats.memorySaved += memoryFreed;
        this.stats.resetCount++;
        if (this.stats.currentAllocations > this.stats.peakAllocations) {
            this.stats.peakAllocations = this.stats.currentAllocations;
        }
        // Clear allocations array (reuse the array itself)
        this.allocations.length = 0;
        this.stats.currentAllocations = 0;
        this.stats.memoryUsed = 0;
    }
    /**
     * Get arena statistics
     */
    getStats() {
        return { ...this.stats };
    }
    /**
     * Get current allocation count
     */
    get allocationCount() {
        return this.stats.currentAllocations;
    }
    /**
     * Get arena name
     */
    get arenaName() {
        return this.name;
    }
    /**
     * Dispose the arena and all its resources
     */
    dispose() {
        this.reset();
        this.beadPool.clear();
        this.stepPool.clear();
        this.formulaPool.clear();
        this.convoyPool.clear();
        this.moleculePool.clear();
    }
    // =========================================================================
    // Private Methods
    // =========================================================================
    trackAllocation(obj, type, sizeBytes) {
        this.allocations.push({ object: obj, type, sizeBytes });
        this.stats.totalAllocations++;
        this.stats.currentAllocations++;
        this.stats.memoryUsed += sizeBytes;
    }
    checkMaxAllocations() {
        if (this.config.maxAllocations > 0 &&
            this.stats.currentAllocations >= this.config.maxAllocations) {
            // Auto-reset when limit reached
            console.warn(`[${this.name}] Max allocations reached, auto-resetting`);
            this.reset();
        }
    }
    returnToPool(allocation) {
        switch (allocation.type) {
            case 'bead':
                this.beadPool.release(allocation.object);
                break;
            case 'step':
                this.stepPool.release(allocation.object);
                break;
            case 'formula':
                this.formulaPool.release(allocation.object);
                break;
            case 'convoy':
                this.convoyPool.release(allocation.object);
                break;
            case 'molecule':
                this.moleculePool.release(allocation.object);
                break;
            // Generic objects are not pooled
        }
    }
}
// ============================================================================
// Scoped Arena
// ============================================================================
/**
 * Scoped arena that auto-resets when disposed
 *
 * Useful for RAII-style memory management with try/finally patterns.
 *
 * @example
 * ```typescript
 * using arena = scopedArena('batch-operation');
 * const beads = arena.allocateMany('bead', 100);
 * // ... process beads ...
 * // Arena automatically resets when scope exits
 * ```
 */
export function scopedArena(name, config) {
    const arena = new Arena(name, config);
    return Object.assign(arena, {
        [Symbol.dispose]() {
            arena.reset();
        },
    });
}
/**
 * Execute a function with a scoped arena
 *
 * The arena is automatically reset after the function completes.
 */
export async function withArena(name, fn, config) {
    const arena = new Arena(name, config);
    try {
        return await fn(arena);
    }
    finally {
        arena.reset();
    }
}
/**
 * Synchronous version of withArena
 */
export function withArenaSync(name, fn, config) {
    const arena = new Arena(name, config);
    try {
        return fn(arena);
    }
    finally {
        arena.reset();
    }
}
// ============================================================================
// Arena Pool Manager
// ============================================================================
/**
 * Manages multiple arenas for different operation types
 */
export class ArenaManager {
    arenas = new Map();
    stats = {
        totalArenas: 0,
        activeArenas: 0,
        totalMemorySaved: 0,
    };
    /**
     * Get or create an arena by name
     */
    getArena(name, config) {
        let arena = this.arenas.get(name);
        if (!arena) {
            arena = new Arena(name, config);
            this.arenas.set(name, arena);
            this.stats.totalArenas++;
            this.stats.activeArenas++;
        }
        return arena;
    }
    /**
     * Reset a specific arena
     */
    resetArena(name) {
        const arena = this.arenas.get(name);
        if (arena) {
            const saved = arena.getStats().memoryUsed;
            arena.reset();
            this.stats.totalMemorySaved += saved;
        }
    }
    /**
     * Reset all arenas
     */
    resetAll() {
        for (const arena of this.arenas.values()) {
            const saved = arena.getStats().memoryUsed;
            arena.reset();
            this.stats.totalMemorySaved += saved;
        }
    }
    /**
     * Dispose an arena
     */
    disposeArena(name) {
        const arena = this.arenas.get(name);
        if (arena) {
            arena.dispose();
            this.arenas.delete(name);
            this.stats.activeArenas--;
        }
    }
    /**
     * Dispose all arenas
     */
    disposeAll() {
        for (const arena of this.arenas.values()) {
            arena.dispose();
        }
        this.arenas.clear();
        this.stats.activeArenas = 0;
    }
    /**
     * Get manager statistics
     */
    getStats() {
        const arenaStats = {};
        for (const [name, arena] of this.arenas) {
            arenaStats[name] = arena.getStats();
        }
        return { ...this.stats, arenaStats };
    }
}
/**
 * Global arena manager instance
 */
export const arenaManager = new ArenaManager();
export default Arena;
//# sourceMappingURL=arena.js.map