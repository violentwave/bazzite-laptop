/**
 * HoTT Engine - Homotopy Type Theory
 *
 * Implements Homotopy Type Theory operations:
 * - Path equivalence checking
 * - Transport along paths
 * - Type inference and normalization
 * - Proof verification
 *
 * Used for type-level reasoning and proof verification in agent systems.
 */
import type { IHottEngine, Path, TypedValue, WasmModule } from '../types.js';
/**
 * HottEngine - WASM wrapper for Homotopy Type Theory operations
 */
export declare class HottEngine implements IHottEngine {
    private wasmModule;
    private typeEnvironment;
    private proofCache;
    constructor(wasmModule?: WasmModule);
    /**
     * Set the WASM module after initialization
     */
    setWasmModule(module: WasmModule): void;
    /**
     * Check if two paths are equivalent (homotopic)
     *
     * @param path1 - First path
     * @param path2 - Second path
     * @returns Whether the paths are equivalent
     */
    checkPathEquivalence(path1: Path, path2: Path): Promise<boolean>;
    /**
     * Transport a value along a path
     * If P: A -> Type and p: x = y, transport P p: P(x) -> P(y)
     *
     * @param path - Path to transport along
     * @param value - Value to transport
     * @returns Transported value
     */
    transportAlong(path: Path, value: TypedValue): Promise<TypedValue>;
    /**
     * Verify a proof of a proposition
     *
     * @param proposition - Proposition to verify
     * @param proof - Proof term
     * @returns Whether the proof is valid
     */
    verifyProof(proposition: string, proof: string): Promise<boolean>;
    /**
     * Infer the type of a term
     *
     * @param term - Term to type
     * @returns Inferred type
     */
    inferType(term: string): Promise<string>;
    /**
     * Normalize a term to its canonical form
     *
     * @param term - Term to normalize
     * @returns Normalized term
     */
    normalize(term: string): Promise<string>;
    /**
     * Create a reflexivity path (x = x)
     */
    refl<T>(x: T, type: string): Path;
    /**
     * Create a symmetry path (if p: x = y, then sym(p): y = x)
     */
    sym(path: Path): Path;
    /**
     * Create a transitivity path (if p: x = y and q: y = z, then trans(p,q): x = z)
     */
    trans(path1: Path, path2: Path): Path;
    /**
     * Apply a function to a path (ap)
     */
    ap<A, B>(f: (a: A) => B, path: Path): Path;
    /**
     * Initialize base types
     */
    private initializeBaseTypes;
    /**
     * Check value equality
     */
    private equalValues;
    /**
     * Pure JS proof verification
     */
    private verifyProofJS;
    /**
     * Parse a proposition string
     */
    private parseProposition;
    /**
     * Parse a proof term
     */
    private parseProof;
    /**
     * Parse comma-separated arguments
     */
    private parseArgs;
    /**
     * Check if proof matches proposition
     */
    private checkProofMatches;
    /**
     * Pure JS type inference
     */
    private inferTypeJS;
    /**
     * Pure JS term normalization
     */
    private normalizeJS;
    /**
     * Apply transport transformation
     */
    private applyTransport;
    /**
     * Substitute occurrences in a value
     */
    private substituteInValue;
    private allocString;
    private freeString;
    private readString;
    private allocPath;
    private freePath;
    private allocValue;
    private freeValue;
    private readValue;
}
//# sourceMappingURL=HottEngine.d.ts.map