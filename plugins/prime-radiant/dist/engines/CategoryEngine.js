/**
 * Category Engine - Functors and Morphisms
 *
 * Implements category theory operations for type-safe transformations:
 * - Morphism application and composition
 * - Natural transformations
 * - Functor mappings
 *
 * Used for agent type transformations and workflow composition.
 */
/**
 * CategoryEngine - WASM wrapper for category theory operations
 */
export class CategoryEngine {
    wasmModule = null;
    morphismRegistry = new Map();
    functorRegistry = new Map();
    constructor(wasmModule) {
        this.wasmModule = wasmModule ?? null;
        this.initializeBuiltinFunctors();
    }
    /**
     * Set the WASM module after initialization
     */
    setWasmModule(module) {
        this.wasmModule = module;
    }
    /**
     * Apply a functor/morphism to transform data
     *
     * @param morphism - Morphism specification
     * @returns MorphismResult with transformed data
     */
    async applyFunctor(morphism) {
        // Validate morphism
        const valid = this.validateMorphism(morphism.data ?? null, null, morphism.name);
        if (!valid) {
            return {
                valid: false,
                result: null,
                naturalTransformation: false
            };
        }
        // Apply the morphism
        const functor = this.functorRegistry.get(morphism.name);
        if (!functor) {
            // Attempt identity morphism
            return {
                valid: true,
                result: morphism.data,
                naturalTransformation: false
            };
        }
        try {
            const result = functor(morphism.data);
            const isNatural = this.isNaturalTransformation(morphism.name);
            return {
                valid: true,
                result,
                naturalTransformation: isNatural
            };
        }
        catch {
            return {
                valid: false,
                result: null,
                naturalTransformation: false
            };
        }
    }
    /**
     * Compose two morphisms: g . f (apply f then g)
     *
     * @param f - First morphism
     * @param g - Second morphism
     * @returns Composed morphism
     */
    async compose(f, g) {
        // Verify composability: f.target === g.source
        if (f.target !== g.source) {
            throw new Error(`Cannot compose morphisms: ${f.name} (target: ${f.target}) and ${g.name} (source: ${g.source}) - ` +
                `target of first must equal source of second`);
        }
        // Create composed morphism
        const composedName = `${g.name} . ${f.name}`;
        // Register the composed functor
        const fFunctor = this.functorRegistry.get(f.name);
        const gFunctor = this.functorRegistry.get(g.name);
        if (fFunctor && gFunctor) {
            this.functorRegistry.set(composedName, (input) => {
                const intermediate = fFunctor(input);
                return gFunctor(intermediate);
            });
        }
        const composed = {
            source: f.source,
            target: g.target,
            name: composedName,
            data: f.data
        };
        this.morphismRegistry.set(composedName, composed);
        return composed;
    }
    /**
     * Validate that a morphism is well-defined
     *
     * @param source - Source object
     * @param target - Target object
     * @param morphism - Morphism name
     * @returns Whether the morphism is valid
     */
    validateMorphism(source, target, morphism) {
        // Check if morphism is registered
        if (this.functorRegistry.has(morphism)) {
            return true;
        }
        // Check built-in morphisms
        const builtins = [
            'identity', 'map', 'filter', 'reduce', 'flatten',
            'embed', 'project', 'lift', 'lower'
        ];
        if (builtins.includes(morphism)) {
            return true;
        }
        // Check if it's a composition
        if (morphism.includes(' . ')) {
            const parts = morphism.split(' . ');
            return parts.every(part => this.validateMorphism(source, target, part.trim()));
        }
        return false;
    }
    /**
     * Check if a morphism is a natural transformation
     * (commutes with all functors)
     *
     * @param morphism - Morphism name
     * @returns Whether it's a natural transformation
     */
    isNaturalTransformation(morphism) {
        // Natural transformations preserve structure
        const naturalMorphisms = [
            'identity', 'map', 'flatten', 'embed', 'project'
        ];
        return naturalMorphisms.includes(morphism);
    }
    /**
     * Register a custom functor
     *
     * @param name - Functor name
     * @param fn - Transformation function
     * @param metadata - Optional metadata
     */
    registerFunctor(name, fn, metadata) {
        this.functorRegistry.set(name, fn);
        if (metadata) {
            this.morphismRegistry.set(name, {
                name,
                source: metadata.source ?? 'Any',
                target: metadata.target ?? 'Any',
                data: metadata
            });
        }
    }
    /**
     * Get registered morphism
     */
    getMorphism(name) {
        return this.morphismRegistry.get(name);
    }
    /**
     * List all registered functors
     */
    listFunctors() {
        return Array.from(this.functorRegistry.keys());
    }
    /**
     * Create an identity morphism for a type
     */
    identity(type) {
        return {
            source: type,
            target: type,
            name: `identity_${type}`,
            data: null
        };
    }
    /**
     * Create a lifting morphism (A -> F(A))
     */
    lift(value, functorName) {
        return {
            source: typeof value,
            target: `${functorName}<${typeof value}>`,
            name: `lift_${functorName}`,
            data: value
        };
    }
    /**
     * Initialize built-in functors
     */
    initializeBuiltinFunctors() {
        // Identity functor
        this.registerFunctor('identity', (x) => x, {
            source: 'Any',
            target: 'Any',
            natural: true
        });
        // Map functor (for arrays)
        this.registerFunctor('map', (x) => {
            if (Array.isArray(x)) {
                return x.map(item => item);
            }
            return x;
        }, {
            source: 'Array<A>',
            target: 'Array<B>',
            natural: true
        });
        // Filter functor
        this.registerFunctor('filter', (x) => {
            if (Array.isArray(x)) {
                return x.filter(Boolean);
            }
            return x;
        }, {
            source: 'Array<A>',
            target: 'Array<A>',
            natural: false
        });
        // Flatten functor
        this.registerFunctor('flatten', (x) => {
            if (Array.isArray(x)) {
                return x.flat();
            }
            return x;
        }, {
            source: 'Array<Array<A>>',
            target: 'Array<A>',
            natural: true
        });
        // Embed functor (scalar to array)
        this.registerFunctor('embed', (x) => {
            if (!Array.isArray(x)) {
                return [x];
            }
            return x;
        }, {
            source: 'A',
            target: 'Array<A>',
            natural: true
        });
        // Project functor (extract first)
        this.registerFunctor('project', (x) => {
            if (Array.isArray(x) && x.length > 0) {
                return x[0];
            }
            return x;
        }, {
            source: 'Array<A>',
            target: 'A',
            natural: true
        });
        // JSON encode functor
        this.registerFunctor('json_encode', (x) => JSON.stringify(x), {
            source: 'Any',
            target: 'String',
            natural: false
        });
        // JSON decode functor
        this.registerFunctor('json_decode', (x) => {
            if (typeof x === 'string') {
                try {
                    return JSON.parse(x);
                }
                catch {
                    return x;
                }
            }
            return x;
        }, {
            source: 'String',
            target: 'Any',
            natural: false
        });
        // Vector normalization functor
        this.registerFunctor('normalize', (x) => {
            if (x instanceof Float32Array || Array.isArray(x)) {
                const arr = Array.isArray(x) ? x : Array.from(x);
                const norm = Math.sqrt(arr.reduce((sum, v) => sum + v * v, 0));
                if (norm === 0)
                    return x;
                return arr.map(v => v / norm);
            }
            return x;
        }, {
            source: 'Vector',
            target: 'UnitVector',
            natural: false
        });
        // Agent state transformation functor
        this.registerFunctor('agent_transform', (x) => {
            if (typeof x === 'object' && x !== null && 'state' in x) {
                return {
                    ...x,
                    transformed: true,
                    timestamp: Date.now()
                };
            }
            return x;
        }, {
            source: 'AgentState',
            target: 'AgentState',
            natural: false
        });
        // Memory entry transformation
        this.registerFunctor('memory_transform', (x) => {
            if (typeof x === 'object' && x !== null && 'embedding' in x) {
                return {
                    ...x,
                    validated: true
                };
            }
            return x;
        }, {
            source: 'MemoryEntry',
            target: 'ValidatedMemoryEntry',
            natural: false
        });
    }
}
//# sourceMappingURL=CategoryEngine.js.map