/**
 * Gas Town Formula Module Exports
 *
 * Provides formula execution with WASM acceleration:
 * - FormulaExecutor: Hybrid WASM/CLI executor
 * - Molecule generation from cooked formulas
 * - Step dependency resolution
 * - Progress tracking and cancellation
 *
 * @module v3/plugins/gastown-bridge/formula
 */
// Main executor
export { FormulaExecutor, createFormulaExecutor, } from './executor.js';
// Default export
export { default } from './executor.js';
//# sourceMappingURL=index.js.map