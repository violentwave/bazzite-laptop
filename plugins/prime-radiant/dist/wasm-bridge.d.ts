/**
 * WASM Bridge - Prime Radiant Plugin
 *
 * Main WASM bridge for loading and managing the prime-radiant-advanced-wasm
 * module. Handles initialization for both Node.js and browser environments.
 *
 * Bundle size: ~92KB (zero dependencies)
 * Load time target: <50ms
 */
import type { WasmBridgeConfig, WasmStatus, ICohomologyEngine, ISpectralEngine, ICausalEngine, IQuantumEngine, ICategoryEngine, IHottEngine } from './types.js';
/**
 * WasmBridge - Main WASM bridge for Prime Radiant plugin
 *
 * Manages WASM module lifecycle and provides access to mathematical engines.
 */
export declare class WasmBridge {
    private wasmModule;
    private initialized;
    private initPromise;
    private loadTime;
    private bundleSize;
    private cohomologyEngine;
    private spectralEngine;
    private causalEngine;
    private quantumEngine;
    private categoryEngine;
    private hottEngine;
    private config;
    constructor(config?: WasmBridgeConfig);
    /**
     * Initialize the WASM bridge
     *
     * Loads the WASM module and creates engine instances.
     * Safe to call multiple times - only initializes once.
     */
    initialize(): Promise<void>;
    /**
     * Internal initialization logic
     */
    private doInitialize;
    /**
     * Load WASM module from path
     *
     * Supports Node.js, browser, and web worker environments.
     */
    loadWasm(wasmPath?: string): Promise<void>;
    /**
     * Load WASM in Node.js environment
     */
    private loadWasmNode;
    /**
     * Load WASM in browser environment
     */
    private loadWasmBrowser;
    /**
     * Create WASM import object for initialization
     */
    private createImportObject;
    /**
     * Read string from WASM memory
     */
    private readString;
    /**
     * Get the Cohomology Engine for coherence checking
     *
     * @returns CohomologyEngine instance
     * @throws Error if not initialized
     */
    getCohomologyEngine(): ICohomologyEngine;
    /**
     * Get the Spectral Engine for stability analysis
     *
     * @returns SpectralEngine instance
     * @throws Error if not initialized
     */
    getSpectralEngine(): ISpectralEngine;
    /**
     * Get the Causal Engine for do-calculus inference
     *
     * @returns CausalEngine instance
     * @throws Error if not initialized
     */
    getCausalEngine(): ICausalEngine;
    /**
     * Get the Quantum Engine for topology operations
     *
     * @returns QuantumEngine instance
     * @throws Error if not initialized
     */
    getQuantumEngine(): IQuantumEngine;
    /**
     * Get the Category Engine for functor operations
     *
     * @returns CategoryEngine instance
     * @throws Error if not initialized
     */
    getCategoryEngine(): ICategoryEngine;
    /**
     * Get the HoTT Engine for type theory operations
     *
     * @returns HottEngine instance
     * @throws Error if not initialized
     */
    getHottEngine(): IHottEngine;
    /**
     * Get current bridge status
     */
    getStatus(): WasmStatus;
    /**
     * Check if WASM is loaded (vs pure JS fallback)
     */
    isWasmLoaded(): boolean;
    /**
     * Check if bridge is initialized
     */
    isInitialized(): boolean;
    /**
     * Dispose of resources
     */
    dispose(): void;
    /**
     * Ensure bridge is initialized before use
     */
    private ensureInitialized;
}
/**
 * Create a pre-configured WASM bridge instance
 */
export declare function createWasmBridge(config?: WasmBridgeConfig): WasmBridge;
/**
 * Create and initialize a WASM bridge
 */
export declare function initializeWasmBridge(config?: WasmBridgeConfig): Promise<WasmBridge>;
export default WasmBridge;
//# sourceMappingURL=wasm-bridge.d.ts.map