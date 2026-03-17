/**
 * Gas Town Bridge Plugin - Input Validators
 *
 * Provides comprehensive input validation for the Gas Town Bridge Plugin:
 * - validateBeadId: Validate bead IDs (alphanumeric only)
 * - validateFormulaName: Validate formula names (safe path characters)
 * - validateConvoyId: Validate convoy IDs (UUID format)
 * - validateGtArgs: Validate and escape CLI arguments
 *
 * Security Features:
 * - Allowlist-based validation (only permit known-safe patterns)
 * - Command injection prevention
 * - Path traversal prevention
 * - Null byte injection prevention
 * - Shell metacharacter blocking
 *
 * All validators follow OWASP guidelines for input validation.
 *
 * @module gastown-bridge/validators
 * @version 0.1.0
 */
import { z } from 'zod';
/**
 * Shell metacharacters that are never allowed in any input
 */
declare const SHELL_METACHARACTERS: RegExp;
/**
 * Path traversal patterns
 */
declare const PATH_TRAVERSAL_PATTERNS: RegExp[];
/**
 * Allowed bead ID formats
 * - gt-{4-16 alphanumeric chars}
 * - Numeric IDs (1-10 digits)
 */
declare const BEAD_ID_PATTERN: RegExp;
/**
 * Allowed formula name format
 * - Starts with letter
 * - Contains only alphanumeric, dash, underscore
 * - 1-64 characters
 */
declare const FORMULA_NAME_PATTERN: RegExp;
/**
 * UUID v4 pattern for convoy IDs
 */
declare const UUID_PATTERN: RegExp;
/**
 * Alternative convoy ID format (conv-{hash})
 */
declare const CONVOY_HASH_PATTERN: RegExp;
/**
 * Maximum lengths for inputs
 */
declare const MAX_LENGTHS: {
    readonly beadId: 32;
    readonly formulaName: 64;
    readonly convoyId: 36;
    readonly argument: 512;
    readonly stringValue: 4096;
    readonly arrayLength: 100;
};
/**
 * Schema for bead ID validation
 */
export declare const BeadIdSchema: z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>, string, string>, string, string>;
/**
 * Schema for formula name validation
 */
export declare const FormulaNameSchema: z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>, string, string>, string, string>;
/**
 * Schema for convoy ID validation (UUID format)
 */
export declare const ConvoyIdSchema: z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>, string, string>;
/**
 * Schema for a single CLI argument
 */
export declare const GtArgumentSchema: z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>, string, string>;
/**
 * Schema for CLI arguments array
 */
export declare const GtArgsSchema: z.ZodArray<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>, string, string>, "many">;
/**
 * Schema for safe string values
 */
export declare const SafeStringSchema: z.ZodEffects<z.ZodString, string, string>;
/**
 * Schema for formula type
 */
export declare const FormulaTypeSchema: z.ZodEnum<["convoy", "workflow", "expansion", "aspect"]>;
/**
 * Schema for bead status
 */
export declare const BeadStatusSchema: z.ZodEnum<["open", "in_progress", "closed"]>;
/**
 * Schema for convoy status
 */
export declare const ConvoyStatusSchema: z.ZodEnum<["active", "landed", "failed", "paused"]>;
/**
 * Schema for sling target
 */
export declare const SlingTargetSchema: z.ZodEnum<["polecat", "crew", "mayor"]>;
/**
 * Schema for rig name
 */
export declare const RigNameSchema: z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>, string, string>;
/**
 * Schema for priority
 */
export declare const PrioritySchema: z.ZodNumber;
/**
 * Schema for labels array
 */
export declare const LabelsSchema: z.ZodArray<z.ZodEffects<z.ZodString, string, string>, "many">;
/**
 * Validate a bead ID
 *
 * Accepts:
 * - gt-{4-16 alphanumeric chars} (e.g., "gt-abc12", "gt-a1b2c3d4")
 * - Numeric IDs (e.g., "123", "9999999999")
 *
 * Rejects:
 * - Empty strings
 * - Shell metacharacters
 * - Path traversal sequences
 * - Invalid formats
 *
 * @param id - The bead ID to validate
 * @returns The validated and trimmed bead ID
 * @throws {ValidationError} If validation fails
 *
 * @example
 * ```typescript
 * const validId = validateBeadId('gt-abc12');  // Returns 'gt-abc12'
 * validateBeadId('gt-abc; rm -rf /');          // Throws ValidationError
 * ```
 */
export declare function validateBeadId(id: string): string;
/**
 * Validate a formula name
 *
 * Accepts:
 * - Starts with letter
 * - Contains only alphanumeric, dash, underscore
 * - 1-64 characters
 *
 * Rejects:
 * - Starting with number
 * - Shell metacharacters
 * - Path traversal sequences
 *
 * @param name - The formula name to validate
 * @returns The validated and trimmed formula name
 * @throws {ValidationError} If validation fails
 *
 * @example
 * ```typescript
 * const validName = validateFormulaName('my-formula');  // Returns 'my-formula'
 * validateFormulaName('../etc/passwd');                  // Throws ValidationError
 * ```
 */
export declare function validateFormulaName(name: string): string;
/**
 * Validate a convoy ID
 *
 * Accepts:
 * - UUID v4 format (e.g., "550e8400-e29b-41d4-a716-446655440000")
 * - conv-{hash} format (e.g., "conv-abc123def")
 *
 * Rejects:
 * - Invalid UUID format
 * - Shell metacharacters
 * - Path traversal sequences
 *
 * @param id - The convoy ID to validate
 * @returns The validated and normalized convoy ID (lowercase)
 * @throws {ValidationError} If validation fails
 *
 * @example
 * ```typescript
 * const validId = validateConvoyId('550e8400-e29b-41d4-a716-446655440000');
 * validateConvoyId('not-a-uuid');  // Throws ValidationError
 * ```
 */
export declare function validateConvoyId(id: string): string;
/**
 * Validate and escape CLI arguments
 *
 * Validates each argument in the array:
 * - No null bytes
 * - No shell metacharacters
 * - No path traversal sequences
 * - Maximum length enforced
 *
 * @param args - Array of CLI arguments to validate
 * @returns Array of validated arguments
 * @throws {ValidationError} If any argument fails validation
 *
 * @example
 * ```typescript
 * const validArgs = validateGtArgs(['beads', 'list', '--limit', '10']);
 * validateGtArgs(['rm', '-rf', '/']);  // Throws ValidationError
 * ```
 */
export declare function validateGtArgs(args: string[]): string[];
/**
 * Schema for CreateBeadOptions
 */
export declare const CreateBeadOptionsSchema: z.ZodObject<{
    title: z.ZodEffects<z.ZodString, string, string>;
    description: z.ZodOptional<z.ZodString>;
    priority: z.ZodDefault<z.ZodOptional<z.ZodNumber>>;
    labels: z.ZodDefault<z.ZodOptional<z.ZodArray<z.ZodEffects<z.ZodString, string, string>, "many">>>;
    parent: z.ZodOptional<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>, string, string>, string, string>>;
    rig: z.ZodOptional<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>, string, string>>;
    assignee: z.ZodOptional<z.ZodEffects<z.ZodString, string, string>>;
}, "strip", z.ZodTypeAny, {
    title: string;
    priority: number;
    labels: string[];
    description?: string | undefined;
    assignee?: string | undefined;
    rig?: string | undefined;
    parent?: string | undefined;
}, {
    title: string;
    description?: string | undefined;
    priority?: number | undefined;
    labels?: string[] | undefined;
    assignee?: string | undefined;
    rig?: string | undefined;
    parent?: string | undefined;
}>;
/**
 * Schema for CreateConvoyOptions
 */
export declare const CreateConvoyOptionsSchema: z.ZodObject<{
    name: z.ZodEffects<z.ZodString, string, string>;
    issues: z.ZodArray<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>, string, string>, string, string>, "many">;
    description: z.ZodOptional<z.ZodString>;
    formula: z.ZodOptional<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>, string, string>, string, string>>;
}, "strip", z.ZodTypeAny, {
    name: string;
    issues: string[];
    description?: string | undefined;
    formula?: string | undefined;
}, {
    name: string;
    issues: string[];
    description?: string | undefined;
    formula?: string | undefined;
}>;
/**
 * Schema for SlingOptions
 */
export declare const SlingOptionsSchema: z.ZodObject<{
    beadId: z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>, string, string>, string, string>;
    target: z.ZodEnum<["polecat", "crew", "mayor"]>;
    formula: z.ZodOptional<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>, string, string>, string, string>>;
    priority: z.ZodOptional<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    beadId: string;
    target: "mayor" | "polecat" | "crew";
    priority?: number | undefined;
    formula?: string | undefined;
}, {
    beadId: string;
    target: "mayor" | "polecat" | "crew";
    priority?: number | undefined;
    formula?: string | undefined;
}>;
/**
 * Validate CreateBeadOptions
 */
export declare function validateCreateBeadOptions(options: unknown): z.infer<typeof CreateBeadOptionsSchema>;
/**
 * Validate CreateConvoyOptions
 */
export declare function validateCreateConvoyOptions(options: unknown): z.infer<typeof CreateConvoyOptionsSchema>;
/**
 * Validate SlingOptions
 */
export declare function validateSlingOptions(options: unknown): z.infer<typeof SlingOptionsSchema>;
/**
 * Check if a string contains shell metacharacters
 */
export declare function containsShellMetacharacters(input: string): boolean;
/**
 * Check if a string contains path traversal sequences
 */
export declare function containsPathTraversal(input: string): boolean;
/**
 * Check if a string is safe for use in CLI arguments
 */
export declare function isSafeArgument(input: string): boolean;
/**
 * Check if a bead ID is valid
 */
export declare function isValidBeadId(id: string): boolean;
/**
 * Check if a formula name is valid
 */
export declare function isValidFormulaName(name: string): boolean;
/**
 * Check if a convoy ID is valid
 */
export declare function isValidConvoyId(id: string): boolean;
export { MAX_LENGTHS, SHELL_METACHARACTERS, PATH_TRAVERSAL_PATTERNS, BEAD_ID_PATTERN, FORMULA_NAME_PATTERN, UUID_PATTERN, CONVOY_HASH_PATTERN, };
//# sourceMappingURL=validators.d.ts.map