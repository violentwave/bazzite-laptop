/**
 * Gas Town Bridge Plugin - Unified Cache System
 *
 * High-performance caching with:
 * - O(1) LRU cache with Map + doubly linked list
 * - WeakMap for formula AST caching (GC-friendly)
 * - Result memoization for expensive operations
 * - Batch deduplication for concurrent requests
 *
 * Performance targets:
 * - 50% memory reduction via eviction
 * - 3x faster cold start via preloading
 *
 * @module gastown-bridge/cache
 * @version 0.1.0
 */
/**
 * LRU Cache with O(1) operations
 *
 * Uses Map for O(1) lookups and doubly linked list for O(1) eviction.
 * Supports TTL, size limits, and access tracking.
 *
 * @example
 * ```typescript
 * const cache = new LRUCache<string, Formula>({ maxSize: 1000, ttlMs: 60000 });
 * cache.set('formula-1', parsedFormula);
 * const formula = cache.get('formula-1');
 * ```
 */
export declare class LRUCache<K, V> {
    private readonly cache;
    private head;
    private tail;
    private currentSize;
    private readonly maxSize;
    private readonly maxEntries;
    private readonly ttlMs;
    private readonly onEvict?;
    constructor(options?: {
        maxSize?: number;
        maxEntries?: number;
        ttlMs?: number;
        onEvict?: (key: K, value: V) => void;
    });
    /**
     * Get value from cache - O(1)
     */
    get(key: K): V | undefined;
    /**
     * Set value in cache - O(1)
     */
    set(key: K, value: V, sizeBytes?: number): void;
    /**
     * Check if key exists - O(1)
     */
    has(key: K): boolean;
    /**
     * Delete from cache - O(1)
     */
    delete(key: K): boolean;
    /**
     * Clear all entries
     */
    clear(): void;
    /**
     * Get cache stats
     */
    stats(): {
        entries: number;
        sizeBytes: number;
        maxEntries: number;
        maxSizeBytes: number;
        hitRate: number;
    };
    /**
     * Get all keys (for iteration)
     */
    keys(): IterableIterator<K>;
    /**
     * Get size
     */
    get size(): number;
    private moveToFront;
    private removeNode;
    private evictLRU;
    private estimateSize;
}
/**
 * Formula AST cache using WeakMap for automatic GC
 *
 * Stores parsed ASTs keyed by source string reference.
 * When the source string is no longer referenced, the AST is GC'd.
 */
export declare class FormulaASTCache {
    private readonly astCache;
    private readonly hashCache;
    constructor(maxEntries?: number);
    /**
     * Get cached AST for formula content
     */
    get(content: string): unknown | undefined;
    /**
     * Cache AST for formula content
     */
    set(content: string, ast: unknown): void;
    /**
     * Check if content has cached AST
     */
    has(content: string): boolean;
    /**
     * Clear cache
     */
    clear(): void;
    /**
     * Get stats
     */
    stats(): {
        entries: number;
        sizeBytes: number;
    };
    private hashContent;
}
/**
 * Result cache for expensive WASM operations
 *
 * Caches:
 * - Formula parse results
 * - Cook results
 * - Graph analysis results (topo sort, cycle detection)
 */
export declare class ResultCache {
    readonly formulas: LRUCache<string, unknown>;
    readonly cooked: LRUCache<string, unknown>;
    readonly beads: LRUCache<string, unknown>;
    readonly convoys: LRUCache<string, unknown>;
    readonly graphs: LRUCache<string, unknown>;
    constructor(options?: {
        maxFormulaEntries?: number;
        maxCookedEntries?: number;
        maxBeadEntries?: number;
        maxConvoyEntries?: number;
        maxGraphEntries?: number;
    });
    /**
     * Clear all caches
     */
    clearAll(): void;
    /**
     * Get combined stats
     */
    stats(): Record<string, {
        entries: number;
        sizeBytes: number;
    }>;
}
/**
 * Batch deduplicator for concurrent identical requests
 *
 * When multiple callers request the same operation simultaneously,
 * only one actual execution occurs and all callers receive the same result.
 *
 * @example
 * ```typescript
 * const dedup = new BatchDeduplicator<Formula>();
 *
 * // These concurrent calls will only execute once
 * const [r1, r2, r3] = await Promise.all([
 *   dedup.dedupe('formula-1', () => parseFormula(content)),
 *   dedup.dedupe('formula-1', () => parseFormula(content)),
 *   dedup.dedupe('formula-1', () => parseFormula(content)),
 * ]);
 * ```
 */
export declare class BatchDeduplicator<T> {
    private pending;
    private readonly timeoutMs;
    constructor(timeoutMs?: number);
    /**
     * Deduplicate concurrent requests for the same key
     */
    dedupe(key: string, executor: () => Promise<T>): Promise<T>;
    /**
     * Get number of pending requests
     */
    get pendingCount(): number;
    /**
     * Clear all pending requests (reject with error)
     */
    clear(): void;
}
/**
 * Idle-time module preloader
 *
 * Preloads WASM modules and other resources during browser/Node idle time.
 */
export declare class ModulePreloader {
    private readonly preloadQueue;
    private readonly loaded;
    private readonly errors;
    private isPreloading;
    private preloadPromise;
    /**
     * Register a module for preloading
     */
    register(name: string, loader: () => Promise<unknown>, priority?: number): void;
    /**
     * Start preloading during idle time
     */
    startPreload(): Promise<void>;
    /**
     * Get preloaded module
     */
    get<T>(name: string): T | undefined;
    /**
     * Check if module is loaded
     */
    isLoaded(name: string): boolean;
    /**
     * Get loading error if any
     */
    getError(name: string): Error | undefined;
    /**
     * Get preload status
     */
    status(): {
        queued: number;
        loaded: number;
        errors: number;
        isPreloading: boolean;
    };
    /**
     * Wait for preloading to complete
     */
    waitForPreload(): Promise<void>;
    private runPreload;
    private scheduleIdleTask;
}
/**
 * Generic connection/resource pool
 *
 * Manages a pool of reusable resources like CLI processes or connections.
 */
export declare class ResourcePool<T> {
    private pool;
    private waitQueue;
    private readonly create;
    private readonly destroy;
    private readonly validate;
    private readonly minSize;
    private readonly maxSize;
    private readonly acquireTimeoutMs;
    private readonly idleTimeoutMs;
    constructor(options: {
        create: () => Promise<T>;
        destroy: (resource: T) => Promise<void>;
        validate?: (resource: T) => boolean;
        minSize?: number;
        maxSize?: number;
        acquireTimeoutMs?: number;
        idleTimeoutMs?: number;
    });
    /**
     * Acquire a resource from the pool
     */
    acquire(): Promise<T>;
    /**
     * Release a resource back to the pool
     */
    release(resource: T): void;
    /**
     * Execute with automatic acquire/release
     */
    withResource<R>(fn: (resource: T) => Promise<R>): Promise<R>;
    /**
     * Get pool stats
     */
    stats(): {
        total: number;
        inUse: number;
        available: number;
        waiting: number;
    };
    /**
     * Shutdown the pool
     */
    shutdown(): Promise<void>;
    private cleanupIdle;
}
/**
 * Debounced update emitter
 *
 * Batches rapid updates and emits at most once per interval.
 */
export declare class DebouncedEmitter<T> {
    private readonly emit;
    private readonly debounceMs;
    private pending;
    private timeoutId;
    private lastEmitTime;
    constructor(emit: (value: T) => void, debounceMs?: number);
    /**
     * Schedule an update (debounced)
     */
    update(value: T): void;
    /**
     * Flush pending update immediately
     */
    flush(): void;
    /**
     * Cancel pending update
     */
    cancel(): void;
}
/**
 * Lazy value wrapper - computes value on first access
 */
export declare class Lazy<T> {
    private readonly factory;
    private computed;
    private value;
    private error;
    constructor(factory: () => T);
    /**
     * Get the value (computes on first access)
     */
    get(): T;
    /**
     * Check if value has been computed
     */
    get isComputed(): boolean;
    /**
     * Reset to uncomputed state
     */
    reset(): void;
}
/**
 * Async lazy value wrapper
 */
export declare class AsyncLazy<T> {
    private readonly factory;
    private promise;
    private value;
    private resolved;
    constructor(factory: () => Promise<T>);
    /**
     * Get the value (computes on first access)
     */
    get(): Promise<T>;
    /**
     * Check if value has been resolved
     */
    get isResolved(): boolean;
    /**
     * Reset to uncomputed state
     */
    reset(): void;
}
declare const _default: {
    LRUCache: typeof LRUCache;
    FormulaASTCache: typeof FormulaASTCache;
    ResultCache: typeof ResultCache;
    BatchDeduplicator: typeof BatchDeduplicator;
    ModulePreloader: typeof ModulePreloader;
    ResourcePool: typeof ResourcePool;
    DebouncedEmitter: typeof DebouncedEmitter;
    Lazy: typeof Lazy;
    AsyncLazy: typeof AsyncLazy;
};
export default _default;
//# sourceMappingURL=cache.d.ts.map