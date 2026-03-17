/**
 * Prime Radiant Plugin - Engine Interfaces
 *
 * Interfaces for the 6 mathematical engines:
 * - ICohomologyEngine: Sheaf Laplacian for coherence detection
 * - ISpectralEngine: Stability and eigenvalue analysis
 * - ICausalEngine: Do-calculus causal inference
 * - IQuantumEngine: Quantum topology operations
 * - ICategoryEngine: Category theory functors/morphisms
 * - IHottEngine: Homotopy Type Theory proofs
 *
 * @module prime-radiant/interfaces
 * @version 0.1.3
 */
// ============================================================================
// Plugin System Interfaces
// ============================================================================
/**
 * Hook priority levels
 */
export var HookPriority;
(function (HookPriority) {
    HookPriority[HookPriority["LOW"] = 0] = "LOW";
    HookPriority[HookPriority["NORMAL"] = 50] = "NORMAL";
    HookPriority[HookPriority["HIGH"] = 100] = "HIGH";
    HookPriority[HookPriority["CRITICAL"] = 200] = "CRITICAL";
})(HookPriority || (HookPriority = {}));
//# sourceMappingURL=interfaces.js.map