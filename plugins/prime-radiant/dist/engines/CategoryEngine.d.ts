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
import type { ICategoryEngine, Morphism, MorphismResult, WasmModule } from '../types.js';
/**
 * CategoryEngine - WASM wrapper for category theory operations
 */
export declare class CategoryEngine implements ICategoryEngine {
    private wasmModule;
    private morphismRegistry;
    private functorRegistry;
    constructor(wasmModule?: WasmModule);
    /**
     * Set the WASM module after initialization
     */
    setWasmModule(module: WasmModule): void;
    /**
     * Apply a functor/morphism to transform data
     *
     * @param morphism - Morphism specification
     * @returns MorphismResult with transformed data
     */
    applyFunctor(morphism: Morphism): Promise<MorphismResult>;
    /**
     * Compose two morphisms: g . f (apply f then g)
     *
     * @param f - First morphism
     * @param g - Second morphism
     * @returns Composed morphism
     */
    compose(f: Morphism, g: Morphism): Promise<Morphism>;
    /**
     * Validate that a morphism is well-defined
     *
     * @param source - Source object
     * @param target - Target object
     * @param morphism - Morphism name
     * @returns Whether the morphism is valid
     */
    validateMorphism(source: unknown, target: unknown, morphism: string): boolean;
    /**
     * Check if a morphism is a natural transformation
     * (commutes with all functors)
     *
     * @param morphism - Morphism name
     * @returns Whether it's a natural transformation
     */
    isNaturalTransformation(morphism: string): boolean;
    /**
     * Register a custom functor
     *
     * @param name - Functor name
     * @param fn - Transformation function
     * @param metadata - Optional metadata
     */
    registerFunctor(name: string, fn: (input: unknown) => unknown, metadata?: {
        source?: string;
        target?: string;
        natural?: boolean;
    }): void;
    /**
     * Get registered morphism
     */
    getMorphism(name: string): Morphism | undefined;
    /**
     * List all registered functors
     */
    listFunctors(): string[];
    /**
     * Create an identity morphism for a type
     */
    identity(type: string): Morphism;
    /**
     * Create a lifting morphism (A -> F(A))
     */
    lift<T>(value: T, functorName: string): Morphism;
    /**
     * Initialize built-in functors
     */
    private initializeBuiltinFunctors;
}
//# sourceMappingURL=CategoryEngine.d.ts.map