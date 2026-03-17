/**
 * Gas Town Bridge Plugin - WASM Loader
 *
 * Provides lazy-loading and caching for WASM modules with graceful
 * JavaScript fallback. Includes typed wrapper functions for all WASM exports
 * and performance timing for benchmarks.
 *
 * WASM Modules:
 * - gastown-formula-wasm: TOML parsing and formula cooking (352x faster)
 * - ruvector-gnn-wasm: Graph operations and neural network (150x faster)
 *
 * @module gastown-bridge/wasm-loader
 * @version 0.1.0
 */
import type { Formula, TopoSortResult, CriticalPathResult } from './types.js';
import { type LazyStats } from './memory/lazy.js';
/**
 * Performance timing result
 */
export interface PerformanceTiming {
    /** Operation name */
    readonly operation: string;
    /** Duration in milliseconds */
    readonly durationMs: number;
    /** Whether WASM was used */
    readonly usedWasm: boolean;
    /** Timestamp when operation started */
    readonly startedAt: number;
}
/**
 * WASM module exports for gastown-formula-wasm
 */
interface FormulaWasmExports {
    /** Initialize the WASM module */
    default?: () => Promise<void>;
    /** Parse TOML content to Formula AST */
    parse_toml: (content: string) => string;
    /** Cook a formula with variable substitution */
    cook_formula: (formulaJson: string, varsJson: string) => string;
    /** Batch cook multiple formulas */
    cook_batch: (formulasJson: string, varsArrayJson: string) => string;
    /** Get WASM version */
    version: () => string;
}
/**
 * WASM module exports for ruvector-gnn-wasm
 */
interface GnnWasmExports {
    /** Initialize the WASM module */
    default?: () => Promise<void>;
    /** Topological sort of dependency graph */
    topo_sort: (nodesJson: string, edgesJson: string) => string;
    /** Detect cycles in dependency graph */
    detect_cycles: (nodesJson: string, edgesJson: string) => string;
    /** Calculate critical path */
    critical_path: (nodesJson: string, edgesJson: string, weightsJson: string) => string;
    /** Get WASM version */
    version: () => string;
}
/**
 * Graph edge representation
 */
export interface GraphEdge {
    readonly from: string;
    readonly to: string;
}
/**
 * Node weight for critical path calculation
 */
export interface NodeWeight {
    readonly nodeId: string;
    readonly weight: number;
}
/**
 * Cycle detection result
 */
export interface CycleDetectionResult {
    readonly hasCycle: boolean;
    readonly cycleNodes: string[];
}
/**
 * Check if WASM is available in the current environment.
 *
 * @returns True if WASM is supported, false otherwise
 *
 * @example
 * ```typescript
 * if (isWasmAvailable()) {
 *   console.log('WASM acceleration enabled');
 * } else {
 *   console.log('Using JavaScript fallback');
 * }
 * ```
 */
export declare function isWasmAvailable(): boolean;
/**
 * Get performance log for benchmarking.
 *
 * @returns Array of performance timing records
 *
 * @example
 * ```typescript
 * const timings = getPerformanceLog();
 * const avgWasmTime = timings
 *   .filter(t => t.usedWasm)
 *   .reduce((acc, t) => acc + t.durationMs, 0) / timings.length;
 * ```
 */
export declare function getPerformanceLog(): readonly PerformanceTiming[];
/**
 * Clear performance log.
 */
export declare function clearPerformanceLog(): void;
/**
 * Lazy-load the gastown-formula-wasm module.
 * Uses LazyWasm for true lazy loading - only loads when first accessed.
 * Includes idle timeout for automatic memory cleanup.
 *
 * @returns The loaded WASM module exports, or null if unavailable
 *
 * @example
 * ```typescript
 * const formulaWasm = await loadFormulaWasm();
 * if (formulaWasm) {
 *   const result = formulaWasm.parse_toml(tomlContent);
 * }
 * ```
 */
export declare function loadFormulaWasm(): Promise<FormulaWasmExports | null>;
/**
 * Lazy-load the ruvector-gnn-wasm module.
 * Uses LazyWasm for true lazy loading - only loads when first accessed.
 * Includes idle timeout for automatic memory cleanup.
 *
 * @returns The loaded WASM module exports, or null if unavailable
 *
 * @example
 * ```typescript
 * const gnnWasm = await loadGnnWasm();
 * if (gnnWasm) {
 *   const result = gnnWasm.topo_sort(nodesJson, edgesJson);
 * }
 * ```
 */
export declare function loadGnnWasm(): Promise<GnnWasmExports | null>;
/**
 * Check if formula WASM module is currently loaded.
 * Does not trigger loading.
 */
export declare function isFormulaWasmLoaded(): boolean;
/**
 * Check if GNN WASM module is currently loaded.
 * Does not trigger loading.
 */
export declare function isGnnWasmLoaded(): boolean;
/**
 * Get lazy loading statistics for WASM modules.
 */
export declare function getWasmLazyStats(): {
    formulaWasm: LazyStats;
    gnnWasm: LazyStats;
};
/**
 * Parse TOML formula content to a Formula object.
 * Uses WASM if available (352x faster), falls back to JavaScript.
 *
 * @param content - TOML string content to parse
 * @returns Parsed Formula object
 *
 * @example
 * ```typescript
 * const formula = await parseFormula(`
 * name = "my-workflow"
 * type = "workflow"
 * version = 1
 *
 * [[steps]]
 * id = "step-1"
 * title = "First step"
 * `);
 * ```
 */
export declare function parseFormula(content: string): Promise<Formula>;
/**
 * Cook a formula by substituting variables.
 * Uses WASM if available (352x faster), falls back to JavaScript.
 *
 * @param formula - Formula to cook
 * @param vars - Variables to substitute
 * @returns Cooked formula with variables substituted
 *
 * @example
 * ```typescript
 * const cooked = await cookFormula(formula, {
 *   projectName: 'my-project',
 *   author: 'developer'
 * });
 * ```
 */
export declare function cookFormula(formula: Formula, vars: Record<string, string>): Promise<Formula>;
/**
 * Batch cook multiple formulas with corresponding variables.
 * Uses WASM if available (352x faster), falls back to JavaScript.
 *
 * @param formulas - Array of formulas to cook
 * @param varsArray - Array of variable objects (one per formula)
 * @returns Array of cooked formulas
 *
 * @example
 * ```typescript
 * const cooked = await cookBatch(
 *   [formula1, formula2],
 *   [{ name: 'a' }, { name: 'b' }]
 * );
 * ```
 */
export declare function cookBatch(formulas: Formula[], varsArray: Record<string, string>[]): Promise<Formula[]>;
/**
 * Perform topological sort on a dependency graph.
 * Uses WASM if available (150x faster), falls back to JavaScript.
 *
 * @param nodes - Array of node identifiers
 * @param edges - Array of edges (from -> to dependencies)
 * @returns Topological sort result with sorted order and cycle detection
 *
 * @example
 * ```typescript
 * const result = await topoSort(
 *   ['a', 'b', 'c'],
 *   [{ from: 'a', to: 'b' }, { from: 'b', to: 'c' }]
 * );
 * console.log(result.sorted); // ['a', 'b', 'c']
 * ```
 */
export declare function topoSort(nodes: string[], edges: GraphEdge[]): Promise<TopoSortResult>;
/**
 * Detect cycles in a dependency graph.
 * Uses WASM if available (150x faster), falls back to JavaScript.
 *
 * @param nodes - Array of node identifiers
 * @param edges - Array of edges (from -> to dependencies)
 * @returns Cycle detection result
 *
 * @example
 * ```typescript
 * const result = await detectCycles(
 *   ['a', 'b', 'c'],
 *   [{ from: 'a', to: 'b' }, { from: 'b', to: 'a' }]
 * );
 * console.log(result.hasCycle); // true
 * console.log(result.cycleNodes); // ['a', 'b']
 * ```
 */
export declare function detectCycles(nodes: string[], edges: GraphEdge[]): Promise<CycleDetectionResult>;
/**
 * Calculate the critical path through a weighted dependency graph.
 * Uses WASM if available (150x faster), falls back to JavaScript.
 *
 * @param nodes - Array of node identifiers
 * @param edges - Array of edges (from -> to dependencies)
 * @param weights - Array of node weights (durations)
 * @returns Critical path result with path, duration, and slack times
 *
 * @example
 * ```typescript
 * const result = await criticalPath(
 *   ['a', 'b', 'c'],
 *   [{ from: 'a', to: 'b' }, { from: 'b', to: 'c' }],
 *   [
 *     { nodeId: 'a', weight: 5 },
 *     { nodeId: 'b', weight: 3 },
 *     { nodeId: 'c', weight: 2 }
 *   ]
 * );
 * console.log(result.path); // ['a', 'b', 'c']
 * console.log(result.totalDuration); // 10
 * ```
 */
export declare function criticalPath(nodes: string[], edges: GraphEdge[], weights: NodeWeight[]): Promise<CriticalPathResult>;
/**
 * Preload all WASM modules.
 * Call this during initialization for best performance.
 *
 * @returns Object indicating which modules were loaded
 *
 * @example
 * ```typescript
 * const status = await preloadWasmModules();
 * console.log(status);
 * // { formulaWasm: true, gnnWasm: true }
 * ```
 */
export declare function preloadWasmModules(): Promise<{
    formulaWasm: boolean;
    gnnWasm: boolean;
}>;
/**
 * Get WASM module versions.
 *
 * @returns Object with version strings, or null if module not loaded
 */
export declare function getWasmVersions(): Promise<{
    formulaWasm: string | null;
    gnnWasm: string | null;
}>;
/**
 * Reset the WASM module cache.
 * Clears lazy loader cache and forces reload on next access.
 * Useful for testing or when modules need to be reloaded.
 */
export declare function resetWasmCache(): void;
/**
 * Schedule idle-time preloading of WASM modules.
 * Uses requestIdleCallback in browser, setImmediate in Node.
 * Does not block the main thread.
 *
 * @example
 * ```typescript
 * // Call during app initialization
 * scheduleIdlePreload();
 * ```
 */
export declare function scheduleIdlePreload(): void;
/**
 * Get cache statistics for performance monitoring.
 *
 * @returns Object with cache stats for each cache type
 *
 * @example
 * ```typescript
 * const stats = getCacheStats();
 * console.log(`Parse cache: ${stats.parseCache.entries} entries`);
 * console.log(`Cook cache hit rate: ${stats.cookCache.hitRate}`);
 * ```
 */
export declare function getCacheStats(): {
    parseCache: {
        entries: number;
        sizeBytes: number;
        hitRate: number;
    };
    cookCache: {
        entries: number;
        sizeBytes: number;
        hitRate: number;
    };
    topoSortCache: {
        entries: number;
        sizeBytes: number;
        hitRate: number;
    };
    astCache: {
        entries: number;
        sizeBytes: number;
    };
    preloader: {
        queued: number;
        loaded: number;
        errors: number;
        isPreloading: boolean;
    };
    deduplicator: {
        parsePending: number;
        cookPending: number;
        graphPending: number;
    };
};
/**
 * Clear all result caches.
 * Useful for testing or when formulas have been modified.
 */
export declare function clearAllCaches(): void;
declare const _default: {
    isWasmAvailable: typeof isWasmAvailable;
    loadFormulaWasm: typeof loadFormulaWasm;
    parseFormula: typeof parseFormula;
    cookFormula: typeof cookFormula;
    cookBatch: typeof cookBatch;
    loadGnnWasm: typeof loadGnnWasm;
    topoSort: typeof topoSort;
    detectCycles: typeof detectCycles;
    criticalPath: typeof criticalPath;
    preloadWasmModules: typeof preloadWasmModules;
    getWasmVersions: typeof getWasmVersions;
    resetWasmCache: typeof resetWasmCache;
    isFormulaWasmLoaded: typeof isFormulaWasmLoaded;
    isGnnWasmLoaded: typeof isGnnWasmLoaded;
    getWasmLazyStats: typeof getWasmLazyStats;
    scheduleIdlePreload: typeof scheduleIdlePreload;
    getCacheStats: typeof getCacheStats;
    clearAllCaches: typeof clearAllCaches;
    getPerformanceLog: typeof getPerformanceLog;
    clearPerformanceLog: typeof clearPerformanceLog;
};
export default _default;
//# sourceMappingURL=wasm-loader.d.ts.map