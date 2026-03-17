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
import { PooledBead, PooledStep, PooledFormula, PooledConvoy, PooledMolecule } from './pool.js';
/**
 * Arena statistics
 */
export interface ArenaStats {
    /** Total allocations since creation */
    totalAllocations: number;
    /** Current allocations (not yet reset) */
    currentAllocations: number;
    /** Number of reset operations */
    resetCount: number;
    /** Peak allocations before reset */
    peakAllocations: number;
    /** Estimated memory in use (bytes) */
    memoryUsed: number;
    /** Total memory saved via bulk reset (bytes) */
    memorySaved: number;
}
/**
 * Arena configuration
 */
export interface ArenaConfig {
    /** Name for debugging */
    name?: string;
    /** Initial capacity hint */
    initialCapacity?: number;
    /** Maximum allocations before forced reset */
    maxAllocations?: number;
    /** Enable automatic pool return on reset */
    returnToPool?: boolean;
}
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
export declare class Arena {
    private name;
    private config;
    private allocations;
    private stats;
    private beadPool;
    private stepPool;
    private formulaPool;
    private convoyPool;
    private moleculePool;
    constructor(name?: string, config?: ArenaConfig);
    /**
     * Allocate an object from the arena
     *
     * Uses pooled objects when available for the given type.
     */
    allocate<T>(factory: () => T, sizeBytes?: number): T;
    /**
     * Allocate a typed object from the arena pools
     */
    allocateTyped<K extends AllocatableType>(type: K): TypeMap[K];
    /**
     * Allocate multiple typed objects
     */
    allocateMany<K extends AllocatableType>(type: K, count: number): TypeMap[K][];
    /**
     * Reset the arena, returning all objects to their pools
     *
     * This is an O(n) operation where n is the number of allocations,
     * but it's a single operation instead of n individual deallocations.
     */
    reset(): void;
    /**
     * Get arena statistics
     */
    getStats(): Readonly<ArenaStats>;
    /**
     * Get current allocation count
     */
    get allocationCount(): number;
    /**
     * Get arena name
     */
    get arenaName(): string;
    /**
     * Dispose the arena and all its resources
     */
    dispose(): void;
    private trackAllocation;
    private checkMaxAllocations;
    private returnToPool;
}
/**
 * Allocatable type names
 */
export type AllocatableType = 'bead' | 'step' | 'formula' | 'convoy' | 'molecule';
/**
 * Type map for allocatable types
 */
export interface TypeMap {
    bead: PooledBead;
    step: PooledStep;
    formula: PooledFormula;
    convoy: PooledConvoy;
    molecule: PooledMolecule;
}
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
export declare function scopedArena(name: string, config?: ArenaConfig): Arena & Disposable;
/**
 * Execute a function with a scoped arena
 *
 * The arena is automatically reset after the function completes.
 */
export declare function withArena<T>(name: string, fn: (arena: Arena) => T | Promise<T>, config?: ArenaConfig): Promise<T>;
/**
 * Synchronous version of withArena
 */
export declare function withArenaSync<T>(name: string, fn: (arena: Arena) => T, config?: ArenaConfig): T;
/**
 * Manages multiple arenas for different operation types
 */
export declare class ArenaManager {
    private arenas;
    private stats;
    /**
     * Get or create an arena by name
     */
    getArena(name: string, config?: ArenaConfig): Arena;
    /**
     * Reset a specific arena
     */
    resetArena(name: string): void;
    /**
     * Reset all arenas
     */
    resetAll(): void;
    /**
     * Dispose an arena
     */
    disposeArena(name: string): void;
    /**
     * Dispose all arenas
     */
    disposeAll(): void;
    /**
     * Get manager statistics
     */
    getStats(): typeof this.stats & {
        arenaStats: Record<string, ArenaStats>;
    };
}
/**
 * Global arena manager instance
 */
export declare const arenaManager: ArenaManager;
export default Arena;
//# sourceMappingURL=arena.d.ts.map