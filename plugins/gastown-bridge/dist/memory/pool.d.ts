/**
 * Object Pooling for Gas Town Bridge Plugin
 *
 * Provides high-performance object pooling to minimize GC pressure
 * and reduce memory allocations for frequently created objects.
 *
 * Target: 75% memory reduction, <10MB heap for 10k beads
 *
 * Pooled object types:
 * - Bead: Git-backed issue tracking objects
 * - Formula: TOML-defined workflow definitions
 * - Step: Individual workflow steps
 * - Convoy: Work-order tracking containers
 * - Molecule: Generated work units
 *
 * @module gastown-bridge/memory/pool
 */
import type { Bead, Formula, Step, Convoy, FormulaType, BeadStatus, ConvoyStatus } from '../types.js';
import type { Molecule } from '../formula/executor.js';
/**
 * Poolable object interface - objects that can be reset and reused
 */
export interface Poolable {
    /** Reset object to initial state for reuse */
    reset?(): void;
}
/**
 * Pool statistics for monitoring
 */
export interface PoolStats {
    /** Total objects created (including pooled) */
    created: number;
    /** Objects currently in pool (available) */
    available: number;
    /** Objects currently in use */
    inUse: number;
    /** Number of times pool was empty on acquire */
    misses: number;
    /** Number of successful pool acquisitions */
    hits: number;
    /** Peak pool size reached */
    peakSize: number;
    /** Memory saved (estimated bytes) */
    memorySaved: number;
}
/**
 * Pool configuration
 */
export interface PoolConfig {
    /** Initial pool size */
    initialSize?: number;
    /** Maximum pool size (0 = unlimited) */
    maxSize?: number;
    /** Estimated object size in bytes (for memory tracking) */
    objectSizeBytes?: number;
    /** Whether to pre-warm the pool */
    preWarm?: boolean;
}
/**
 * High-performance generic object pool
 *
 * Uses a simple array-based free list for O(1) acquire/release.
 * Supports both factory functions and prototype-based object creation.
 *
 * @example
 * ```typescript
 * const beadPool = new ObjectPool<PooledBead>({
 *   factory: () => new PooledBead(),
 *   reset: (bead) => bead.reset(),
 *   initialSize: 100,
 *   maxSize: 10000,
 * });
 *
 * const bead = beadPool.acquire();
 * // ... use bead ...
 * beadPool.release(bead);
 * ```
 */
export declare class ObjectPool<T extends object> {
    private pool;
    private factory;
    private resetFn?;
    private config;
    private stats;
    constructor(factory: () => T, options?: PoolConfig & {
        reset?: (obj: T) => void;
    });
    /**
     * Acquire an object from the pool
     *
     * Returns a pooled object if available, otherwise creates a new one.
     * O(1) operation using array pop.
     */
    acquire(): T;
    /**
     * Release an object back to the pool
     *
     * Resets the object and returns it to the pool for reuse.
     * O(1) operation using array push.
     *
     * @param obj - Object to release
     */
    release(obj: T): void;
    /**
     * Release multiple objects at once (batch operation)
     */
    releaseAll(objects: T[]): void;
    /**
     * Pre-warm the pool with objects
     */
    preWarm(count: number): void;
    /**
     * Clear the pool and release all objects
     */
    clear(): void;
    /**
     * Get pool statistics
     */
    getStats(): Readonly<PoolStats>;
    /**
     * Get current pool size
     */
    get size(): number;
    /**
     * Get hit rate (percentage of successful pool acquisitions)
     */
    get hitRate(): number;
}
/**
 * Pooled Bead object with reset capability
 */
export declare class PooledBead implements Bead, Poolable {
    id: string;
    title: string;
    description: string;
    status: BeadStatus;
    priority: number;
    labels: string[];
    createdAt: Date;
    updatedAt: Date;
    parentId?: string;
    assignee?: string;
    rig?: string;
    blockedBy?: string[];
    blocks?: string[];
    reset(): void;
    /**
     * Initialize from a Bead-like object
     */
    initFrom(source: Partial<Bead>): this;
}
/**
 * Pooled Step object with reset capability
 */
export declare class PooledStep implements Step, Poolable {
    id: string;
    title: string;
    description: string;
    needs?: string[];
    duration?: number;
    requires?: string[];
    metadata?: Record<string, unknown>;
    reset(): void;
    initFrom(source: Partial<Step>): this;
}
/**
 * Pooled Formula object with reset capability
 */
export declare class PooledFormula implements Formula, Poolable {
    name: string;
    description: string;
    type: FormulaType;
    version: number;
    steps?: Step[];
    legs?: Formula['legs'];
    vars?: Formula['vars'];
    metadata?: Formula['metadata'];
    reset(): void;
    initFrom(source: Partial<Formula>): this;
}
/**
 * Pooled Convoy object with reset capability
 */
export declare class PooledConvoy implements Convoy, Poolable {
    id: string;
    name: string;
    trackedIssues: string[];
    status: ConvoyStatus;
    startedAt: Date;
    completedAt?: Date;
    progress: {
        total: number;
        closed: number;
        inProgress: number;
        blocked: number;
    };
    formula?: string;
    description?: string;
    reset(): void;
    initFrom(source: Partial<Convoy>): this;
}
/**
 * Pooled Molecule object with reset capability
 */
export declare class PooledMolecule implements Molecule, Poolable {
    id: string;
    formulaName: string;
    title: string;
    description: string;
    type: FormulaType;
    sourceId: string;
    agent?: string;
    dependencies: string[];
    order: number;
    metadata: Record<string, unknown>;
    createdAt: Date;
    reset(): void;
    initFrom(source: Partial<Molecule>): this;
}
/**
 * Global Bead pool - optimized for 10k beads target
 * Estimated size per bead: ~512 bytes
 */
export declare const beadPool: ObjectPool<PooledBead>;
/**
 * Global Formula pool
 * Estimated size per formula: ~1KB
 */
export declare const formulaPool: ObjectPool<PooledFormula>;
/**
 * Global Step pool
 * Estimated size per step: ~256 bytes
 */
export declare const stepPool: ObjectPool<PooledStep>;
/**
 * Global Convoy pool
 * Estimated size per convoy: ~768 bytes
 */
export declare const convoyPool: ObjectPool<PooledConvoy>;
/**
 * Global Molecule pool
 * Estimated size per molecule: ~384 bytes
 */
export declare const moleculePool: ObjectPool<PooledMolecule>;
/**
 * All managed pools
 */
declare const allPools: {
    readonly bead: ObjectPool<PooledBead>;
    readonly formula: ObjectPool<PooledFormula>;
    readonly step: ObjectPool<PooledStep>;
    readonly convoy: ObjectPool<PooledConvoy>;
    readonly molecule: ObjectPool<PooledMolecule>;
};
export type PoolType = keyof typeof allPools;
/**
 * Get statistics for all pools
 */
export declare function getAllPoolStats(): Record<PoolType, PoolStats>;
/**
 * Get total memory saved across all pools
 */
export declare function getTotalMemorySaved(): number;
/**
 * Clear all pools
 */
export declare function clearAllPools(): void;
/**
 * Pre-warm all pools with default sizes
 */
export declare function preWarmAllPools(): void;
/**
 * Get a summary of pool efficiency
 */
export declare function getPoolEfficiencySummary(): {
    totalHitRate: number;
    totalMemorySavedKB: number;
    totalObjectsInUse: number;
    totalObjectsAvailable: number;
};
export default ObjectPool;
//# sourceMappingURL=pool.d.ts.map