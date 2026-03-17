/**
 * Gas Town Bridge Plugin - Type Definitions
 *
 * Core types for Gas Town integration including:
 * - Beads: Git-backed issue tracking with graph semantics
 * - Formulas: TOML-defined workflows (convoy, workflow, expansion, aspect)
 * - Convoys: Work-order tracking for slung work
 * - Steps/Legs: Workflow components
 * - Variables: Template substitution
 *
 * @module gastown-bridge/types
 * @version 0.1.0
 */
import { z } from 'zod';
/**
 * Default configuration values
 */
export const DEFAULT_CONFIG = {
    townRoot: '~/gt',
    enableBeadsSync: true,
    syncInterval: 60000,
    nativeFormulas: true,
    enableConvoys: true,
    autoCreateBeads: false,
    enableGUPP: false,
    guppCheckInterval: 5000,
    cliTimeout: 30000,
};
// ============================================================================
// Error Types
// ============================================================================
/**
 * Gas Town Bridge error codes
 */
export const GasTownErrorCodes = {
    CLI_NOT_FOUND: 'GT_CLI_NOT_FOUND',
    CLI_TIMEOUT: 'GT_CLI_TIMEOUT',
    CLI_ERROR: 'GT_CLI_ERROR',
    BEAD_NOT_FOUND: 'GT_BEAD_NOT_FOUND',
    CONVOY_NOT_FOUND: 'GT_CONVOY_NOT_FOUND',
    FORMULA_NOT_FOUND: 'GT_FORMULA_NOT_FOUND',
    FORMULA_PARSE_ERROR: 'GT_FORMULA_PARSE_ERROR',
    WASM_NOT_INITIALIZED: 'GT_WASM_NOT_INITIALIZED',
    SYNC_ERROR: 'GT_SYNC_ERROR',
    DEPENDENCY_CYCLE: 'GT_DEPENDENCY_CYCLE',
    INVALID_SLING_TARGET: 'GT_INVALID_SLING_TARGET',
};
// ============================================================================
// Zod Schemas
// ============================================================================
/**
 * Bead status schema
 */
export const BeadStatusSchema = z.enum(['open', 'in_progress', 'closed']);
/**
 * Bead schema
 */
export const BeadSchema = z.object({
    id: z.string().min(1),
    title: z.string().min(1),
    description: z.string(),
    status: BeadStatusSchema,
    priority: z.number().int().min(0),
    labels: z.array(z.string()),
    parentId: z.string().optional(),
    createdAt: z.coerce.date(),
    updatedAt: z.coerce.date(),
    assignee: z.string().optional(),
    rig: z.string().optional(),
    blockedBy: z.array(z.string()).optional(),
    blocks: z.array(z.string()).optional(),
});
/**
 * Create bead options schema
 */
export const CreateBeadOptionsSchema = z.object({
    title: z.string().min(1),
    description: z.string().optional(),
    priority: z.number().int().min(0).optional(),
    labels: z.array(z.string()).optional(),
    parent: z.string().optional(),
    rig: z.string().optional(),
    assignee: z.string().optional(),
});
/**
 * Formula type schema
 */
export const FormulaTypeSchema = z.enum(['convoy', 'workflow', 'expansion', 'aspect']);
/**
 * Step schema
 */
export const StepSchema = z.object({
    id: z.string().min(1),
    title: z.string().min(1),
    description: z.string(),
    needs: z.array(z.string()).optional(),
    duration: z.number().optional(),
    requires: z.array(z.string()).optional(),
    metadata: z.record(z.unknown()).optional(),
});
/**
 * Leg schema
 */
export const LegSchema = z.object({
    id: z.string().min(1),
    title: z.string().min(1),
    focus: z.string(),
    description: z.string(),
    agent: z.string().optional(),
    order: z.number().optional(),
});
/**
 * Variable schema
 */
export const VarSchema = z.object({
    name: z.string().min(1),
    description: z.string().optional(),
    default: z.string().optional(),
    required: z.boolean().optional(),
    pattern: z.string().optional(),
    enum: z.array(z.string()).optional(),
});
/**
 * Synthesis schema
 */
export const SynthesisSchema = z.object({
    strategy: z.enum(['merge', 'sequential', 'parallel']),
    format: z.string().optional(),
    description: z.string().optional(),
});
/**
 * Template schema
 */
export const TemplateSchema = z.object({
    name: z.string().min(1),
    content: z.string(),
    outputPath: z.string().optional(),
});
/**
 * Aspect schema
 */
export const AspectSchema = z.object({
    name: z.string().min(1),
    pointcut: z.string(),
    advice: z.string(),
    type: z.enum(['before', 'after', 'around']),
});
/**
 * Formula schema
 */
export const FormulaSchema = z.object({
    name: z.string().min(1),
    description: z.string(),
    type: FormulaTypeSchema,
    version: z.number().int().min(1),
    legs: z.array(LegSchema).optional(),
    synthesis: SynthesisSchema.optional(),
    steps: z.array(StepSchema).optional(),
    vars: z.record(VarSchema).optional(),
    templates: z.array(TemplateSchema).optional(),
    aspects: z.array(AspectSchema).optional(),
    metadata: z.record(z.unknown()).optional(),
});
/**
 * Convoy status schema
 */
export const ConvoyStatusSchema = z.enum(['active', 'landed', 'failed', 'paused']);
/**
 * Convoy progress schema
 */
export const ConvoyProgressSchema = z.object({
    total: z.number().int().min(0),
    closed: z.number().int().min(0),
    inProgress: z.number().int().min(0),
    blocked: z.number().int().min(0),
});
/**
 * Convoy schema
 */
export const ConvoySchema = z.object({
    id: z.string().min(1),
    name: z.string().min(1),
    trackedIssues: z.array(z.string()),
    status: ConvoyStatusSchema,
    startedAt: z.coerce.date(),
    completedAt: z.coerce.date().optional(),
    progress: ConvoyProgressSchema,
    formula: z.string().optional(),
    description: z.string().optional(),
});
/**
 * Create convoy options schema
 */
export const CreateConvoyOptionsSchema = z.object({
    name: z.string().min(1),
    issues: z.array(z.string()).min(1),
    description: z.string().optional(),
    formula: z.string().optional(),
});
/**
 * Gas Town agent role schema
 */
export const GasTownAgentRoleSchema = z.enum([
    'mayor',
    'polecat',
    'refinery',
    'witness',
    'deacon',
    'dog',
    'crew',
]);
/**
 * Sling target schema
 */
export const SlingTargetSchema = z.enum(['polecat', 'crew', 'mayor']);
/**
 * Sling options schema
 */
export const SlingOptionsSchema = z.object({
    beadId: z.string().min(1),
    target: SlingTargetSchema,
    formula: z.string().optional(),
    priority: z.number().int().min(0).optional(),
});
/**
 * Sync direction schema
 */
export const SyncDirectionSchema = z.enum(['pull', 'push', 'both']);
/**
 * Configuration schema
 */
export const GasTownConfigSchema = z.object({
    townRoot: z.string().default('~/gt'),
    enableBeadsSync: z.boolean().default(true),
    syncInterval: z.number().int().positive().default(60000),
    nativeFormulas: z.boolean().default(true),
    enableConvoys: z.boolean().default(true),
    autoCreateBeads: z.boolean().default(false),
    enableGUPP: z.boolean().default(false),
    guppCheckInterval: z.number().int().positive().default(5000),
    cliTimeout: z.number().int().positive().default(30000),
});
// ============================================================================
// Validation Functions
// ============================================================================
/**
 * Validate bead
 */
export function validateBead(input) {
    return BeadSchema.parse(input);
}
/**
 * Validate create bead options
 */
export function validateCreateBeadOptions(input) {
    return CreateBeadOptionsSchema.parse(input);
}
/**
 * Validate formula
 */
export function validateFormula(input) {
    return FormulaSchema.parse(input);
}
/**
 * Validate convoy
 */
export function validateConvoy(input) {
    return ConvoySchema.parse(input);
}
/**
 * Validate create convoy options
 */
export function validateCreateConvoyOptions(input) {
    return CreateConvoyOptionsSchema.parse(input);
}
/**
 * Validate sling options
 */
export function validateSlingOptions(input) {
    return SlingOptionsSchema.parse(input);
}
/**
 * Validate configuration
 */
export function validateConfig(input) {
    return GasTownConfigSchema.parse(input);
}
//# sourceMappingURL=types.js.map