/**
 * WASM Module Registry
 *
 * Centralized registry for all RuVector WASM modules.
 * Handles lazy loading, caching, and lifecycle management.
 */
import type { WasmBridge, WasmModuleStatus } from './types.js';
/**
 * WASM Module Registry
 */
export declare class WasmRegistry {
    private modules;
    private initPromises;
    /**
     * Register a WASM bridge
     */
    register(name: string, bridge: WasmBridge): void;
    /**
     * Get a WASM bridge by name
     */
    get<T = unknown>(name: string): Promise<WasmBridge<T> | null>;
    /**
     * Ensure a module is initialized (with deduplication)
     */
    private ensureInitialized;
    /**
     * Check if a module is registered
     */
    has(name: string): boolean;
    /**
     * Get module status
     */
    getStatus(name: string): WasmModuleStatus | null;
    /**
     * List all registered modules
     */
    list(): Array<{
        name: string;
        status: WasmModuleStatus;
        version: string;
        useCount: number;
    }>;
    /**
     * Unload a module to free memory
     */
    unload(name: string): Promise<void>;
    /**
     * Unload all modules
     */
    unloadAll(): Promise<void>;
    /**
     * Get registry statistics
     */
    getStats(): {
        totalModules: number;
        loadedModules: number;
        totalUseCount: number;
        memoryEstimateMb: number;
    };
}
/**
 * Get the global WASM registry instance
 */
export declare function getWasmRegistry(): WasmRegistry;
//# sourceMappingURL=registry.d.ts.map