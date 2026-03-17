/**
 * WASM Module Registry
 *
 * Centralized registry for all RuVector WASM modules.
 * Handles lazy loading, caching, and lifecycle management.
 */
/**
 * WASM Module Registry
 */
export class WasmRegistry {
    modules = new Map();
    initPromises = new Map();
    /**
     * Register a WASM bridge
     */
    register(name, bridge) {
        if (this.modules.has(name)) {
            console.warn(`WASM module '${name}' already registered, skipping`);
            return;
        }
        this.modules.set(name, {
            bridge,
            useCount: 0,
        });
    }
    /**
     * Get a WASM bridge by name
     */
    async get(name) {
        const entry = this.modules.get(name);
        if (!entry) {
            return null;
        }
        // Initialize if needed
        if (!entry.bridge.isReady()) {
            await this.ensureInitialized(name);
        }
        // Update usage stats
        entry.lastUsed = new Date();
        entry.useCount++;
        return entry.bridge;
    }
    /**
     * Ensure a module is initialized (with deduplication)
     */
    async ensureInitialized(name) {
        // Check if already initializing
        const existing = this.initPromises.get(name);
        if (existing) {
            return existing;
        }
        const entry = this.modules.get(name);
        if (!entry) {
            throw new Error(`WASM module '${name}' not registered`);
        }
        // Start initialization
        const promise = entry.bridge.init().then(() => {
            entry.loadedAt = new Date();
            this.initPromises.delete(name);
        }).catch((error) => {
            this.initPromises.delete(name);
            throw error;
        });
        this.initPromises.set(name, promise);
        return promise;
    }
    /**
     * Check if a module is registered
     */
    has(name) {
        return this.modules.has(name);
    }
    /**
     * Get module status
     */
    getStatus(name) {
        const entry = this.modules.get(name);
        return entry?.bridge.status ?? null;
    }
    /**
     * List all registered modules
     */
    list() {
        return Array.from(this.modules.entries()).map(([name, entry]) => ({
            name,
            status: entry.bridge.status,
            version: entry.bridge.version,
            useCount: entry.useCount,
        }));
    }
    /**
     * Unload a module to free memory
     */
    async unload(name) {
        const entry = this.modules.get(name);
        if (!entry) {
            return;
        }
        await entry.bridge.destroy();
    }
    /**
     * Unload all modules
     */
    async unloadAll() {
        const promises = Array.from(this.modules.keys()).map(name => this.unload(name));
        await Promise.all(promises);
    }
    /**
     * Get registry statistics
     */
    getStats() {
        let loadedCount = 0;
        let totalUse = 0;
        for (const entry of this.modules.values()) {
            if (entry.bridge.status === 'ready') {
                loadedCount++;
            }
            totalUse += entry.useCount;
        }
        return {
            totalModules: this.modules.size,
            loadedModules: loadedCount,
            totalUseCount: totalUse,
            memoryEstimateMb: loadedCount * 2, // Rough estimate: 2MB per loaded module
        };
    }
}
// Singleton instance
let registryInstance = null;
/**
 * Get the global WASM registry instance
 */
export function getWasmRegistry() {
    if (!registryInstance) {
        registryInstance = new WasmRegistry();
    }
    return registryInstance;
}
//# sourceMappingURL=registry.js.map