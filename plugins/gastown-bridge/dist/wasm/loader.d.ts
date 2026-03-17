/**
 * WASM Lazy Loader for Gas Town Bridge
 *
 * Provides on-demand loading of WASM modules with:
 * - Lazy initialization (modules loaded only when needed)
 * - Gzip decompression support
 * - Caching to prevent re-initialization
 * - Graceful fallback to JS implementations
 *
 * Bundle impact: <5KB (loader only, WASM loaded separately)
 *
 * @module v3/plugins/gastown-bridge/wasm
 */
export interface FormulaWasm {
    parse_toml: (input: string) => unknown;
    cook_formula: (formula: unknown, variables: Record<string, unknown>) => unknown;
    generate_molecule: (formula: unknown) => unknown;
    memory: WebAssembly.Memory;
}
export interface GnnWasm {
    create_dag: () => unknown;
    add_node: (dag: unknown, id: string, data: unknown) => void;
    add_edge: (dag: unknown, from: string, to: string) => void;
    topological_sort: (dag: unknown) => string[];
    detect_cycles: (dag: unknown) => boolean;
    critical_path: (dag: unknown) => string[];
    memory: WebAssembly.Memory;
}
export interface WasmModule<T> {
    instance: T;
    memory: WebAssembly.Memory;
    ready: boolean;
}
/**
 * WASM loading options
 */
export interface WasmLoadOptions {
    /**
     * Base path for WASM files
     * @default './wasm'
     */
    basePath?: string;
    /**
     * Prefer gzipped WASM files
     * @default true
     */
    preferGzip?: boolean;
    /**
     * Custom fetch function (for Node.js or custom loaders)
     */
    fetch?: typeof globalThis.fetch;
    /**
     * Abort signal for cancellation
     */
    signal?: AbortSignal;
}
/**
 * Load the Formula WASM module
 *
 * Features:
 * - TOML parsing (352x faster than JavaScript)
 * - Variable cooking/substitution
 * - Molecule generation
 *
 * @example
 * ```typescript
 * const formula = await loadFormulaWasm();
 * const parsed = formula.instance.parse_toml(tomlString);
 * ```
 */
export declare function loadFormulaWasm(options?: WasmLoadOptions): Promise<WasmModule<FormulaWasm>>;
/**
 * Load the GNN WASM module
 *
 * Features:
 * - DAG construction and traversal (150x faster)
 * - Topological sorting
 * - Cycle detection
 * - Critical path analysis
 *
 * @example
 * ```typescript
 * const gnn = await loadGnnWasm();
 * const dag = gnn.instance.create_dag();
 * gnn.instance.add_node(dag, 'task1', { name: 'Build' });
 * ```
 */
export declare function loadGnnWasm(options?: WasmLoadOptions): Promise<WasmModule<GnnWasm>>;
/**
 * Preload all WASM modules
 *
 * Use this during application startup to avoid latency
 * on first use.
 */
export declare function preloadAllWasm(options?: WasmLoadOptions): Promise<void>;
/**
 * Check if WASM modules are loaded
 */
export declare function isWasmLoaded(): {
    formula: boolean;
    gnn: boolean;
    all: boolean;
};
/**
 * Clear cached WASM modules
 *
 * Useful for testing or memory management
 */
export declare function clearWasmCache(): void;
/**
 * Get WASM memory statistics
 */
export declare function getWasmMemoryStats(): {
    formula: {
        pages: number;
        bytes: number;
    } | null;
    gnn: {
        pages: number;
        bytes: number;
    } | null;
    total: number;
};
//# sourceMappingURL=loader.d.ts.map