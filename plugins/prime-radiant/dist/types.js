/**
 * Prime Radiant Plugin - Type Definitions
 *
 * Core types for mathematical AI interpretability engines including
 * sheaf cohomology, spectral analysis, causal inference, quantum topology,
 * category theory, and homotopy type theory.
 */
/**
 * Default configuration values
 */
export const DEFAULT_CONFIG = {
    coherence: {
        warnThreshold: 0.3,
        rejectThreshold: 0.7,
        cacheEnabled: true,
        cacheTTL: 60000,
    },
    spectral: {
        stabilityThreshold: 0.1,
        maxMatrixSize: 1000,
    },
    causal: {
        maxBackdoorPaths: 10,
        confidenceThreshold: 0.8,
    },
};
// ============================================================================
// Error Types
// ============================================================================
/**
 * Prime Radiant specific error codes
 */
export const PrimeRadiantErrorCodes = {
    WASM_NOT_INITIALIZED: 'PR_WASM_NOT_INITIALIZED',
    COHERENCE_VIOLATION: 'PR_COHERENCE_VIOLATION',
    INVALID_VECTORS: 'PR_INVALID_VECTORS',
    INVALID_CAUSAL_GRAPH: 'PR_INVALID_CAUSAL_GRAPH',
    MATRIX_SIZE_EXCEEDED: 'PR_MATRIX_SIZE_EXCEEDED',
    ENGINE_NOT_AVAILABLE: 'PR_ENGINE_NOT_AVAILABLE',
};
//# sourceMappingURL=types.js.map