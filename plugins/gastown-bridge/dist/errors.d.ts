/**
 * Gas Town Bridge Plugin - Typed Error Classes
 *
 * Provides a hierarchy of typed error classes for the Gas Town Bridge Plugin:
 * - GasTownError: Base error class for all Gas Town errors
 * - BeadsError: Errors related to bead operations
 * - ValidationError: Input validation failures
 * - CLIExecutionError: CLI command execution failures
 *
 * All errors include:
 * - Typed error codes for programmatic handling
 * - Stack traces for debugging
 * - Contextual information about the failure
 *
 * @module gastown-bridge/errors
 * @version 0.1.0
 */
/**
 * Gas Town error codes enumeration
 */
export declare const GasTownErrorCode: {
    readonly UNKNOWN: "GT_UNKNOWN";
    readonly INITIALIZATION_FAILED: "GT_INITIALIZATION_FAILED";
    readonly NOT_INITIALIZED: "GT_NOT_INITIALIZED";
    readonly CONFIGURATION_ERROR: "GT_CONFIGURATION_ERROR";
    readonly VALIDATION_FAILED: "GT_VALIDATION_FAILED";
    readonly INVALID_INPUT: "GT_INVALID_INPUT";
    readonly INVALID_BEAD_ID: "GT_INVALID_BEAD_ID";
    readonly INVALID_FORMULA_NAME: "GT_INVALID_FORMULA_NAME";
    readonly INVALID_CONVOY_ID: "GT_INVALID_CONVOY_ID";
    readonly INVALID_ARGUMENTS: "GT_INVALID_ARGUMENTS";
    readonly COMMAND_INJECTION_DETECTED: "GT_COMMAND_INJECTION_DETECTED";
    readonly PATH_TRAVERSAL_DETECTED: "GT_PATH_TRAVERSAL_DETECTED";
    readonly BEAD_NOT_FOUND: "GT_BEAD_NOT_FOUND";
    readonly BEAD_CREATE_FAILED: "GT_BEAD_CREATE_FAILED";
    readonly BEAD_UPDATE_FAILED: "GT_BEAD_UPDATE_FAILED";
    readonly BEAD_DELETE_FAILED: "GT_BEAD_DELETE_FAILED";
    readonly BEAD_PARSE_FAILED: "GT_BEAD_PARSE_FAILED";
    readonly FORMULA_NOT_FOUND: "GT_FORMULA_NOT_FOUND";
    readonly FORMULA_PARSE_FAILED: "GT_FORMULA_PARSE_FAILED";
    readonly FORMULA_COOK_FAILED: "GT_FORMULA_COOK_FAILED";
    readonly FORMULA_INVALID_TYPE: "GT_FORMULA_INVALID_TYPE";
    readonly CONVOY_NOT_FOUND: "GT_CONVOY_NOT_FOUND";
    readonly CONVOY_CREATE_FAILED: "GT_CONVOY_CREATE_FAILED";
    readonly CLI_NOT_FOUND: "GT_CLI_NOT_FOUND";
    readonly CLI_TIMEOUT: "GT_CLI_TIMEOUT";
    readonly CLI_EXECUTION_FAILED: "GT_CLI_EXECUTION_FAILED";
    readonly CLI_INVALID_OUTPUT: "GT_CLI_INVALID_OUTPUT";
    readonly WASM_NOT_AVAILABLE: "GT_WASM_NOT_AVAILABLE";
    readonly WASM_EXECUTION_FAILED: "GT_WASM_EXECUTION_FAILED";
    readonly SYNC_FAILED: "GT_SYNC_FAILED";
    readonly SYNC_CONFLICT: "GT_SYNC_CONFLICT";
    readonly DEPENDENCY_CYCLE: "GT_DEPENDENCY_CYCLE";
    readonly GRAPH_ERROR: "GT_GRAPH_ERROR";
};
export type GasTownErrorCodeType = (typeof GasTownErrorCode)[keyof typeof GasTownErrorCode];
/**
 * Base error class for all Gas Town Bridge errors
 *
 * @example
 * ```typescript
 * throw new GasTownError(
 *   'Failed to initialize plugin',
 *   GasTownErrorCode.INITIALIZATION_FAILED,
 *   { configPath: '/path/to/config' }
 * );
 * ```
 */
export declare class GasTownError extends Error {
    /** Error code for programmatic handling */
    readonly code: GasTownErrorCodeType;
    /** Timestamp when error occurred */
    readonly timestamp: Date;
    /** Additional context about the error */
    readonly context?: Record<string, unknown>;
    /** Original error if this wraps another error */
    readonly cause?: Error;
    constructor(message: string, code?: GasTownErrorCodeType, context?: Record<string, unknown>, cause?: Error);
    /**
     * Convert error to JSON for logging/serialization
     */
    toJSON(): Record<string, unknown>;
    /**
     * Create a human-readable string representation
     */
    toString(): string;
}
/**
 * Error class for bead-related operations
 *
 * @example
 * ```typescript
 * throw new BeadsError(
 *   'Bead not found',
 *   GasTownErrorCode.BEAD_NOT_FOUND,
 *   { beadId: 'gt-abc12' }
 * );
 * ```
 */
export declare class BeadsError extends GasTownError {
    /** Bead ID if applicable */
    readonly beadId?: string;
    /** Operation being performed */
    readonly operation?: string;
    constructor(message: string, code?: GasTownErrorCodeType, context?: Record<string, unknown>, cause?: Error);
    /**
     * Create a BeadsError for a not found scenario
     */
    static notFound(beadId: string): BeadsError;
    /**
     * Create a BeadsError for a create failure
     */
    static createFailed(reason: string, cause?: Error): BeadsError;
    /**
     * Create a BeadsError for a parse failure
     */
    static parseFailed(rawOutput: string, cause?: Error): BeadsError;
}
/**
 * Validation constraint that was violated
 */
export interface ValidationConstraint {
    /** Field or parameter that failed validation */
    field: string;
    /** Expected constraint (e.g., "alphanumeric", "max-length:64") */
    constraint: string;
    /** Actual value (sanitized for logging) */
    actual?: string;
    /** Expected value or pattern */
    expected?: string;
}
/**
 * Error class for input validation failures
 *
 * @example
 * ```typescript
 * throw new ValidationError(
 *   'Invalid bead ID format',
 *   GasTownErrorCode.INVALID_BEAD_ID,
 *   [{ field: 'beadId', constraint: 'alphanumeric', actual: 'abc;rm -rf' }]
 * );
 * ```
 */
export declare class ValidationError extends GasTownError {
    /** Validation constraints that were violated */
    readonly constraints: ValidationConstraint[];
    constructor(message: string, code?: GasTownErrorCodeType, constraints?: ValidationConstraint[], cause?: Error);
    /**
     * Create a ValidationError for an invalid bead ID
     */
    static invalidBeadId(beadId: string): ValidationError;
    /**
     * Create a ValidationError for an invalid formula name
     */
    static invalidFormulaName(name: string): ValidationError;
    /**
     * Create a ValidationError for an invalid convoy ID
     */
    static invalidConvoyId(convoyId: string): ValidationError;
    /**
     * Create a ValidationError for command injection attempt
     */
    static commandInjection(field: string, detected: string): ValidationError;
    /**
     * Create a ValidationError for path traversal attempt
     */
    static pathTraversal(field: string): ValidationError;
    /**
     * Combine multiple validation errors
     */
    static combine(errors: ValidationError[]): ValidationError;
}
/**
 * Error class for CLI command execution failures
 *
 * @example
 * ```typescript
 * throw new CLIExecutionError(
 *   'gt command failed',
 *   GasTownErrorCode.CLI_EXECUTION_FAILED,
 *   { command: 'gt', args: ['beads', 'list'], exitCode: 1, stderr: 'error message' }
 * );
 * ```
 */
export declare class CLIExecutionError extends GasTownError {
    /** CLI command that was executed */
    readonly command: string;
    /** Arguments passed to the command (sanitized) */
    readonly args: string[];
    /** Exit code from the process */
    readonly exitCode?: number;
    /** Standard error output (truncated) */
    readonly stderr?: string;
    /** Execution duration in milliseconds */
    readonly durationMs?: number;
    constructor(message: string, code: GasTownErrorCodeType | undefined, details: {
        command: string;
        args?: string[];
        exitCode?: number;
        stderr?: string;
        durationMs?: number;
    }, cause?: Error);
    /**
     * Create a CLIExecutionError for command not found
     */
    static notFound(command: string): CLIExecutionError;
    /**
     * Create a CLIExecutionError for timeout
     */
    static timeout(command: string, args: string[], timeoutMs: number): CLIExecutionError;
    /**
     * Create a CLIExecutionError for execution failure
     */
    static failed(command: string, args: string[], exitCode: number, stderr: string, durationMs?: number): CLIExecutionError;
    /**
     * Create a CLIExecutionError for invalid output
     */
    static invalidOutput(command: string, reason: string): CLIExecutionError;
}
/**
 * Error class for formula-related operations
 */
export declare class FormulaError extends GasTownError {
    /** Formula name if applicable */
    readonly formulaName?: string;
    /** Formula type if applicable */
    readonly formulaType?: string;
    constructor(message: string, code?: GasTownErrorCodeType, context?: Record<string, unknown>, cause?: Error);
    /**
     * Create a FormulaError for not found
     */
    static notFound(formulaName: string): FormulaError;
    /**
     * Create a FormulaError for parse failure
     */
    static parseFailed(formulaName: string, reason: string, cause?: Error): FormulaError;
    /**
     * Create a FormulaError for cook failure
     */
    static cookFailed(formulaName: string, reason: string, cause?: Error): FormulaError;
}
/**
 * Error class for convoy-related operations
 */
export declare class ConvoyError extends GasTownError {
    /** Convoy ID if applicable */
    readonly convoyId?: string;
    constructor(message: string, code?: GasTownErrorCodeType, context?: Record<string, unknown>, cause?: Error);
    /**
     * Create a ConvoyError for not found
     */
    static notFound(convoyId: string): ConvoyError;
    /**
     * Create a ConvoyError for create failure
     */
    static createFailed(reason: string, cause?: Error): ConvoyError;
}
/**
 * Type guard for GasTownError
 */
export declare function isGasTownError(error: unknown): error is GasTownError;
/**
 * Type guard for ValidationError
 */
export declare function isValidationError(error: unknown): error is ValidationError;
/**
 * Type guard for CLIExecutionError
 */
export declare function isCLIExecutionError(error: unknown): error is CLIExecutionError;
/**
 * Type guard for BeadsError
 */
export declare function isBeadsError(error: unknown): error is BeadsError;
/**
 * Wrap an unknown error as a GasTownError
 */
export declare function wrapError(error: unknown, code?: GasTownErrorCodeType): GasTownError;
/**
 * Extract error message safely
 */
export declare function getErrorMessage(error: unknown): string;
//# sourceMappingURL=errors.d.ts.map