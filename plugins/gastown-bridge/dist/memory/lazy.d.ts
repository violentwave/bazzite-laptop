/**
 * Lazy Loading Utilities for Gas Town Bridge Plugin
 *
 * Provides lazy initialization patterns to defer resource loading
 * until first use, reducing initial memory footprint and startup time.
 *
 * Features:
 * - Lazy WASM module loading
 * - Deferred convoy observer initialization
 * - Lazy bridge initialization
 * - Resource cleanup on idle
 *
 * @module gastown-bridge/memory/lazy
 */
/**
 * Lazy value state
 */
export type LazyState = 'uninitialized' | 'initializing' | 'initialized' | 'error' | 'disposed';
/**
 * Lazy initialization options
 */
export interface LazyOptions<T> {
    /** Factory function to create the value */
    factory: () => T | Promise<T>;
    /** Optional cleanup function */
    cleanup?: (value: T) => void | Promise<void>;
    /** Auto-dispose after idle time (ms, 0 = never) */
    idleTimeout?: number;
    /** Error handler */
    onError?: (error: Error) => void;
    /** Name for debugging */
    name?: string;
}
/**
 * Lazy loader statistics
 */
export interface LazyStats {
    name: string;
    state: LazyState;
    initCount: number;
    disposeCount: number;
    errorCount: number;
    lastInitTime?: Date;
    lastAccessTime?: Date;
    initDurationMs?: number;
}
/**
 * Lazy value wrapper with automatic initialization
 *
 * @example
 * ```typescript
 * const lazyWasm = new Lazy({
 *   name: 'wasm-module',
 *   factory: async () => await loadWasmModule(),
 *   cleanup: (wasm) => wasm.dispose(),
 *   idleTimeout: 60000, // Auto-dispose after 1 minute of inactivity
 * });
 *
 * // First access triggers initialization
 * const wasm = await lazyWasm.get();
 *
 * // Check if initialized without triggering
 * if (lazyWasm.isInitialized()) { ... }
 *
 * // Manual disposal
 * await lazyWasm.dispose();
 * ```
 */
export declare class Lazy<T> {
    private value?;
    private state;
    private initPromise?;
    private idleTimer?;
    private options;
    private stats;
    constructor(options: LazyOptions<T>);
    /**
     * Get the lazy value, initializing if necessary
     */
    get(): Promise<T>;
    /**
     * Get synchronously (throws if not initialized)
     */
    getSync(): T;
    /**
     * Check if initialized
     */
    isInitialized(): boolean;
    /**
     * Get current state
     */
    getState(): LazyState;
    /**
     * Initialize without returning value
     */
    initialize(): Promise<T>;
    /**
     * Dispose the lazy value
     */
    dispose(): Promise<void>;
    /**
     * Get statistics
     */
    getStats(): Readonly<LazyStats>;
    private resetIdleTimer;
    private clearIdleTimer;
}
/**
 * Get or create a lazy singleton
 */
export declare function getLazySingleton<T>(key: string, options: LazyOptions<T>): Lazy<T>;
/**
 * Dispose a lazy singleton
 */
export declare function disposeLazySingleton(key: string): Promise<void>;
/**
 * Dispose all lazy singletons
 */
export declare function disposeAllLazySingletons(): Promise<void>;
/**
 * Lazy module loader for dynamic imports
 *
 * @example
 * ```typescript
 * const wasmLoader = new LazyModule(() => import('./wasm-loader.js'));
 * const { parseFormula } = await wasmLoader.get();
 * ```
 */
export declare class LazyModule<T> {
    private lazy;
    constructor(importer: () => Promise<T>, options?: Omit<LazyOptions<T>, 'factory'>);
    /**
     * Get the module
     */
    get(): Promise<T>;
    /**
     * Check if loaded
     */
    isLoaded(): boolean;
    /**
     * Dispose module
     */
    dispose(): Promise<void>;
}
/**
 * Lazy bridge wrapper for Gas Town bridges
 *
 * Defers bridge initialization until first use.
 */
export declare class LazyBridge<T extends {
    initialize?: () => Promise<void>;
}> {
    private lazy;
    constructor(factory: () => T | Promise<T>, options?: Omit<LazyOptions<T>, 'factory'>);
    /**
     * Get the bridge
     */
    get(): Promise<T>;
    /**
     * Check if initialized
     */
    isInitialized(): boolean;
    /**
     * Dispose bridge
     */
    dispose(): Promise<void>;
    /**
     * Get stats
     */
    getStats(): LazyStats;
}
/**
 * Lazy WASM module loader with caching
 */
export declare class LazyWasm<T> {
    private lazy;
    private cached;
    constructor(loader: () => Promise<T>, options?: {
        name?: string;
        idleTimeout?: number;
        onError?: (error: Error) => void;
    });
    /**
     * Get the WASM module
     */
    get(): Promise<T>;
    /**
     * Check if loaded
     */
    isLoaded(): boolean;
    /**
     * Clear cache (module will be reloaded on next access)
     */
    clearCache(): void;
    /**
     * Get stats
     */
    getStats(): LazyStats;
}
/**
 * Lazy observer pattern for convoy watching
 *
 * Defers observer creation until first watch request.
 */
export declare class LazyObserver<T> {
    private lazy;
    private watchCount;
    constructor(factory: () => T | Promise<T>, options?: Omit<LazyOptions<T>, 'factory'>);
    /**
     * Start watching (initializes observer if needed)
     */
    watch(): Promise<T>;
    /**
     * Stop watching (disposes observer if no more watchers)
     */
    unwatch(): Promise<void>;
    /**
     * Get current watch count
     */
    getWatchCount(): number;
    /**
     * Check if active
     */
    isActive(): boolean;
    /**
     * Force dispose
     */
    dispose(): Promise<void>;
}
/**
 * Create a lazy property getter
 */
export declare function createLazyProperty<T>(factory: () => T | Promise<T>, options?: Omit<LazyOptions<T>, 'factory'>): {
    get: () => Promise<T>;
    isInitialized: () => boolean;
};
export default Lazy;
//# sourceMappingURL=lazy.d.ts.map