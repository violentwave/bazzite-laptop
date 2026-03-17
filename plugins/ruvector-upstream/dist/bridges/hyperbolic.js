/**
 * Hyperbolic Embeddings Bridge
 *
 * Bridge to ruvector-hyperbolic-hnsw-wasm for hierarchical data representation
 * using Poincaré ball model, Lorentz model, or Klein model.
 */
import { HyperbolicConfigSchema } from '../types.js';
/**
 * Hyperbolic Embeddings Bridge implementation
 */
export class HyperbolicBridge {
    name = 'ruvector-hyperbolic-hnsw-wasm';
    version = '0.1.0';
    _status = 'unloaded';
    _module = null;
    config;
    constructor(config) {
        this.config = HyperbolicConfigSchema.parse(config ?? {});
    }
    get status() {
        return this._status;
    }
    async init() {
        if (this._status === 'ready')
            return;
        if (this._status === 'loading')
            return;
        this._status = 'loading';
        try {
            const wasmModule = await import('@ruvector/hyperbolic-hnsw-wasm').catch(() => null);
            if (wasmModule) {
                this._module = wasmModule;
            }
            else {
                this._module = this.createMockModule();
            }
            this._status = 'ready';
        }
        catch (error) {
            this._status = 'error';
            throw error;
        }
    }
    async destroy() {
        this._module = null;
        this._status = 'unloaded';
    }
    isReady() {
        return this._status === 'ready';
    }
    getModule() {
        return this._module;
    }
    /**
     * Embed a vector into hyperbolic space
     */
    embed(vector, config) {
        if (!this._module)
            throw new Error('Hyperbolic module not initialized');
        const mergedConfig = { ...this.config, ...config };
        return this._module.embed(vector, mergedConfig);
    }
    /**
     * Project hyperbolic point to Euclidean space
     */
    project(point) {
        if (!this._module)
            throw new Error('Hyperbolic module not initialized');
        return this._module.project(point);
    }
    /**
     * Compute hyperbolic distance
     */
    distance(a, b) {
        if (!this._module)
            throw new Error('Hyperbolic module not initialized');
        return this._module.distance(a, b);
    }
    /**
     * Compute hyperbolic similarity
     */
    similarity(a, b) {
        if (!this._module)
            throw new Error('Hyperbolic module not initialized');
        return this._module.similarity(a, b);
    }
    /**
     * Check if one point is ancestor of another (hierarchy)
     */
    isAncestor(parent, child, threshold = 0.1) {
        if (!this._module)
            throw new Error('Hyperbolic module not initialized');
        return this._module.isAncestor(parent, child, threshold);
    }
    /**
     * Get hierarchy depth of a point
     */
    hierarchyDepth(point) {
        if (!this._module)
            throw new Error('Hyperbolic module not initialized');
        return this._module.hierarchyDepth(point);
    }
    /**
     * Add point to HNSW index
     */
    addToIndex(id, point) {
        if (!this._module)
            throw new Error('Hyperbolic module not initialized');
        this._module.addToIndex(id, point);
    }
    /**
     * Search in hyperbolic HNSW index
     */
    search(query, k) {
        if (!this._module)
            throw new Error('Hyperbolic module not initialized');
        return this._module.search(query, k);
    }
    /**
     * Create mock module for development
     */
    createMockModule() {
        const index = new Map();
        return {
            embed(vector, config) {
                // Map to Poincaré ball (simplified)
                const norm = Math.sqrt(vector.reduce((s, v) => s + v * v, 0));
                const scale = Math.tanh(norm) / (norm || 1);
                const coords = new Float32Array(config.dimensions);
                for (let i = 0; i < config.dimensions; i++) {
                    coords[i] = (vector[i % vector.length] || 0) * scale * 0.9;
                }
                return { coordinates: coords, curvature: config.curvature };
            },
            project(point) {
                // Inverse of embedding
                const coords = point.coordinates;
                const norm = Math.sqrt(coords.reduce((s, v) => s + v * v, 0));
                const scale = Math.atanh(Math.min(norm, 0.99)) / (norm || 1);
                const result = new Float32Array(coords.length);
                for (let i = 0; i < coords.length; i++) {
                    result[i] = coords[i] * scale;
                }
                return result;
            },
            distance(a, b) {
                // Poincaré distance approximation
                const c = Math.abs(a.curvature);
                const diffSq = a.coordinates.reduce((s, v, i) => s + Math.pow(v - b.coordinates[i], 2), 0);
                const normA = a.coordinates.reduce((s, v) => s + v * v, 0);
                const normB = b.coordinates.reduce((s, v) => s + v * v, 0);
                const delta = 2 * diffSq / ((1 - normA) * (1 - normB));
                return (1 / Math.sqrt(c)) * Math.acosh(1 + delta);
            },
            similarity(a, b) {
                const dist = this.distance(a, b);
                return Math.exp(-dist);
            },
            midpoint(a, b) {
                const mid = new Float32Array(a.coordinates.length);
                for (let i = 0; i < mid.length; i++) {
                    mid[i] = (a.coordinates[i] + b.coordinates[i]) / 2;
                }
                return { coordinates: mid, curvature: a.curvature };
            },
            geodesic(a, b, steps) {
                const result = [];
                for (let i = 0; i <= steps; i++) {
                    const t = i / steps;
                    const coords = new Float32Array(a.coordinates.length);
                    for (let j = 0; j < coords.length; j++) {
                        coords[j] = a.coordinates[j] * (1 - t) + b.coordinates[j] * t;
                    }
                    result.push({ coordinates: coords, curvature: a.curvature });
                }
                return result;
            },
            isAncestor(parent, child, threshold) {
                const parentNorm = Math.sqrt(parent.coordinates.reduce((s, v) => s + v * v, 0));
                const childNorm = Math.sqrt(child.coordinates.reduce((s, v) => s + v * v, 0));
                return parentNorm < childNorm - threshold;
            },
            hierarchyDepth(point) {
                const norm = Math.sqrt(point.coordinates.reduce((s, v) => s + v * v, 0));
                return Math.atanh(Math.min(norm, 0.99));
            },
            addToIndex(id, point) {
                index.set(id, point);
            },
            search(query, k) {
                const results = [];
                for (const [id, point] of index) {
                    const distance = this.distance(query, point);
                    results.push({ id, distance });
                }
                results.sort((a, b) => a.distance - b.distance);
                return results.slice(0, k);
            },
        };
    }
}
/**
 * Create a new hyperbolic bridge
 */
export function createHyperbolicBridge(config) {
    return new HyperbolicBridge(config);
}
//# sourceMappingURL=hyperbolic.js.map