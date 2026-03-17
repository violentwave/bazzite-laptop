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
// ============================================================================
// Error Codes
// ============================================================================
/**
 * Gas Town error codes enumeration
 */
export const GasTownErrorCode = {
    // General errors
    UNKNOWN: 'GT_UNKNOWN',
    INITIALIZATION_FAILED: 'GT_INITIALIZATION_FAILED',
    NOT_INITIALIZED: 'GT_NOT_INITIALIZED',
    CONFIGURATION_ERROR: 'GT_CONFIGURATION_ERROR',
    // Validation errors
    VALIDATION_FAILED: 'GT_VALIDATION_FAILED',
    INVALID_INPUT: 'GT_INVALID_INPUT',
    INVALID_BEAD_ID: 'GT_INVALID_BEAD_ID',
    INVALID_FORMULA_NAME: 'GT_INVALID_FORMULA_NAME',
    INVALID_CONVOY_ID: 'GT_INVALID_CONVOY_ID',
    INVALID_ARGUMENTS: 'GT_INVALID_ARGUMENTS',
    COMMAND_INJECTION_DETECTED: 'GT_COMMAND_INJECTION_DETECTED',
    PATH_TRAVERSAL_DETECTED: 'GT_PATH_TRAVERSAL_DETECTED',
    // Beads errors
    BEAD_NOT_FOUND: 'GT_BEAD_NOT_FOUND',
    BEAD_CREATE_FAILED: 'GT_BEAD_CREATE_FAILED',
    BEAD_UPDATE_FAILED: 'GT_BEAD_UPDATE_FAILED',
    BEAD_DELETE_FAILED: 'GT_BEAD_DELETE_FAILED',
    BEAD_PARSE_FAILED: 'GT_BEAD_PARSE_FAILED',
    // Formula errors
    FORMULA_NOT_FOUND: 'GT_FORMULA_NOT_FOUND',
    FORMULA_PARSE_FAILED: 'GT_FORMULA_PARSE_FAILED',
    FORMULA_COOK_FAILED: 'GT_FORMULA_COOK_FAILED',
    FORMULA_INVALID_TYPE: 'GT_FORMULA_INVALID_TYPE',
    // Convoy errors
    CONVOY_NOT_FOUND: 'GT_CONVOY_NOT_FOUND',
    CONVOY_CREATE_FAILED: 'GT_CONVOY_CREATE_FAILED',
    // CLI errors
    CLI_NOT_FOUND: 'GT_CLI_NOT_FOUND',
    CLI_TIMEOUT: 'GT_CLI_TIMEOUT',
    CLI_EXECUTION_FAILED: 'GT_CLI_EXECUTION_FAILED',
    CLI_INVALID_OUTPUT: 'GT_CLI_INVALID_OUTPUT',
    // WASM errors
    WASM_NOT_AVAILABLE: 'GT_WASM_NOT_AVAILABLE',
    WASM_EXECUTION_FAILED: 'GT_WASM_EXECUTION_FAILED',
    // Sync errors
    SYNC_FAILED: 'GT_SYNC_FAILED',
    SYNC_CONFLICT: 'GT_SYNC_CONFLICT',
    // Graph errors
    DEPENDENCY_CYCLE: 'GT_DEPENDENCY_CYCLE',
    GRAPH_ERROR: 'GT_GRAPH_ERROR',
};
// ============================================================================
// Base Error Class
// ============================================================================
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
export class GasTownError extends Error {
    /** Error code for programmatic handling */
    code;
    /** Timestamp when error occurred */
    timestamp;
    /** Additional context about the error */
    context;
    /** Original error if this wraps another error */
    cause;
    constructor(message, code = GasTownErrorCode.UNKNOWN, context, cause) {
        super(message);
        this.name = 'GasTownError';
        this.code = code;
        this.timestamp = new Date();
        this.context = context;
        this.cause = cause;
        // Maintain proper stack trace in V8 environments
        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, GasTownError);
        }
    }
    /**
     * Convert error to JSON for logging/serialization
     */
    toJSON() {
        return {
            name: this.name,
            message: this.message,
            code: this.code,
            timestamp: this.timestamp.toISOString(),
            context: this.context,
            cause: this.cause?.message,
            stack: this.stack,
        };
    }
    /**
     * Create a human-readable string representation
     */
    toString() {
        let str = `[${this.code}] ${this.message}`;
        if (this.context) {
            str += ` | Context: ${JSON.stringify(this.context)}`;
        }
        if (this.cause) {
            str += ` | Caused by: ${this.cause.message}`;
        }
        return str;
    }
}
// ============================================================================
// Beads Error Class
// ============================================================================
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
export class BeadsError extends GasTownError {
    /** Bead ID if applicable */
    beadId;
    /** Operation being performed */
    operation;
    constructor(message, code = GasTownErrorCode.BEAD_NOT_FOUND, context, cause) {
        super(message, code, context, cause);
        this.name = 'BeadsError';
        // Extract beadId from context if present
        if (context?.beadId && typeof context.beadId === 'string') {
            this.beadId = context.beadId;
        }
        if (context?.operation && typeof context.operation === 'string') {
            this.operation = context.operation;
        }
        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, BeadsError);
        }
    }
    /**
     * Create a BeadsError for a not found scenario
     */
    static notFound(beadId) {
        return new BeadsError(`Bead not found: ${beadId}`, GasTownErrorCode.BEAD_NOT_FOUND, { beadId, operation: 'get' });
    }
    /**
     * Create a BeadsError for a create failure
     */
    static createFailed(reason, cause) {
        return new BeadsError(`Failed to create bead: ${reason}`, GasTownErrorCode.BEAD_CREATE_FAILED, { operation: 'create' }, cause);
    }
    /**
     * Create a BeadsError for a parse failure
     */
    static parseFailed(rawOutput, cause) {
        // Truncate raw output for safety
        const truncated = rawOutput.length > 200 ? rawOutput.slice(0, 200) + '...' : rawOutput;
        return new BeadsError('Failed to parse bead output', GasTownErrorCode.BEAD_PARSE_FAILED, { operation: 'parse', outputLength: rawOutput.length, outputPreview: truncated }, cause);
    }
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
export class ValidationError extends GasTownError {
    /** Validation constraints that were violated */
    constraints;
    constructor(message, code = GasTownErrorCode.VALIDATION_FAILED, constraints = [], cause) {
        super(message, code, { constraints }, cause);
        this.name = 'ValidationError';
        this.constraints = constraints;
        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, ValidationError);
        }
    }
    /**
     * Create a ValidationError for an invalid bead ID
     */
    static invalidBeadId(beadId) {
        // Sanitize the bead ID for safe logging
        const sanitized = beadId.replace(/[^\w\s-]/g, '?').slice(0, 32);
        return new ValidationError('Invalid bead ID format', GasTownErrorCode.INVALID_BEAD_ID, [{
                field: 'beadId',
                constraint: 'alphanumeric with gt- prefix',
                actual: sanitized,
                expected: 'gt-{4-16 alphanumeric} or numeric',
            }]);
    }
    /**
     * Create a ValidationError for an invalid formula name
     */
    static invalidFormulaName(name) {
        const sanitized = name.replace(/[^\w\s-]/g, '?').slice(0, 32);
        return new ValidationError('Invalid formula name format', GasTownErrorCode.INVALID_FORMULA_NAME, [{
                field: 'formulaName',
                constraint: 'alphanumeric with dash/underscore, starting with letter',
                actual: sanitized,
                expected: '[a-zA-Z][a-zA-Z0-9_-]{0,63}',
            }]);
    }
    /**
     * Create a ValidationError for an invalid convoy ID
     */
    static invalidConvoyId(convoyId) {
        const sanitized = convoyId.replace(/[^\w\s-]/g, '?').slice(0, 32);
        return new ValidationError('Invalid convoy ID format', GasTownErrorCode.INVALID_CONVOY_ID, [{
                field: 'convoyId',
                constraint: 'UUID format',
                actual: sanitized,
                expected: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
            }]);
    }
    /**
     * Create a ValidationError for command injection attempt
     */
    static commandInjection(field, detected) {
        // Never include the actual malicious content
        return new ValidationError(`Command injection detected in ${field}`, GasTownErrorCode.COMMAND_INJECTION_DETECTED, [{
                field,
                constraint: 'no shell metacharacters',
                actual: '[REDACTED]',
                expected: 'safe characters only',
            }]);
    }
    /**
     * Create a ValidationError for path traversal attempt
     */
    static pathTraversal(field) {
        return new ValidationError(`Path traversal detected in ${field}`, GasTownErrorCode.PATH_TRAVERSAL_DETECTED, [{
                field,
                constraint: 'no parent directory references',
                actual: '[REDACTED]',
                expected: 'safe path characters only',
            }]);
    }
    /**
     * Combine multiple validation errors
     */
    static combine(errors) {
        const allConstraints = errors.flatMap(e => e.constraints);
        return new ValidationError(`Multiple validation errors: ${errors.map(e => e.message).join('; ')}`, GasTownErrorCode.VALIDATION_FAILED, allConstraints);
    }
}
// ============================================================================
// CLI Execution Error Class
// ============================================================================
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
export class CLIExecutionError extends GasTownError {
    /** CLI command that was executed */
    command;
    /** Arguments passed to the command (sanitized) */
    args;
    /** Exit code from the process */
    exitCode;
    /** Standard error output (truncated) */
    stderr;
    /** Execution duration in milliseconds */
    durationMs;
    constructor(message, code = GasTownErrorCode.CLI_EXECUTION_FAILED, details, cause) {
        // Sanitize args for context
        const sanitizedArgs = (details.args ?? []).map(arg => arg.length > 50 ? arg.slice(0, 50) + '...' : arg);
        // Truncate stderr for safety
        const truncatedStderr = details.stderr && details.stderr.length > 500
            ? details.stderr.slice(0, 500) + '...'
            : details.stderr;
        super(message, code, {
            command: details.command,
            args: sanitizedArgs,
            exitCode: details.exitCode,
            durationMs: details.durationMs,
        }, cause);
        this.name = 'CLIExecutionError';
        this.command = details.command;
        this.args = sanitizedArgs;
        this.exitCode = details.exitCode;
        this.stderr = truncatedStderr;
        this.durationMs = details.durationMs;
        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, CLIExecutionError);
        }
    }
    /**
     * Create a CLIExecutionError for command not found
     */
    static notFound(command) {
        return new CLIExecutionError(`CLI command not found: ${command}`, GasTownErrorCode.CLI_NOT_FOUND, { command });
    }
    /**
     * Create a CLIExecutionError for timeout
     */
    static timeout(command, args, timeoutMs) {
        return new CLIExecutionError(`CLI command timed out after ${timeoutMs}ms`, GasTownErrorCode.CLI_TIMEOUT, { command, args, durationMs: timeoutMs });
    }
    /**
     * Create a CLIExecutionError for execution failure
     */
    static failed(command, args, exitCode, stderr, durationMs) {
        return new CLIExecutionError(`CLI command failed with exit code ${exitCode}`, GasTownErrorCode.CLI_EXECUTION_FAILED, { command, args, exitCode, stderr, durationMs });
    }
    /**
     * Create a CLIExecutionError for invalid output
     */
    static invalidOutput(command, reason) {
        return new CLIExecutionError(`CLI command produced invalid output: ${reason}`, GasTownErrorCode.CLI_INVALID_OUTPUT, { command });
    }
}
// ============================================================================
// Formula Error Class
// ============================================================================
/**
 * Error class for formula-related operations
 */
export class FormulaError extends GasTownError {
    /** Formula name if applicable */
    formulaName;
    /** Formula type if applicable */
    formulaType;
    constructor(message, code = GasTownErrorCode.FORMULA_PARSE_FAILED, context, cause) {
        super(message, code, context, cause);
        this.name = 'FormulaError';
        if (context?.formulaName && typeof context.formulaName === 'string') {
            this.formulaName = context.formulaName;
        }
        if (context?.formulaType && typeof context.formulaType === 'string') {
            this.formulaType = context.formulaType;
        }
        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, FormulaError);
        }
    }
    /**
     * Create a FormulaError for not found
     */
    static notFound(formulaName) {
        return new FormulaError(`Formula not found: ${formulaName}`, GasTownErrorCode.FORMULA_NOT_FOUND, { formulaName });
    }
    /**
     * Create a FormulaError for parse failure
     */
    static parseFailed(formulaName, reason, cause) {
        return new FormulaError(`Failed to parse formula ${formulaName}: ${reason}`, GasTownErrorCode.FORMULA_PARSE_FAILED, { formulaName, parseError: reason }, cause);
    }
    /**
     * Create a FormulaError for cook failure
     */
    static cookFailed(formulaName, reason, cause) {
        return new FormulaError(`Failed to cook formula ${formulaName}: ${reason}`, GasTownErrorCode.FORMULA_COOK_FAILED, { formulaName, cookError: reason }, cause);
    }
}
// ============================================================================
// Convoy Error Class
// ============================================================================
/**
 * Error class for convoy-related operations
 */
export class ConvoyError extends GasTownError {
    /** Convoy ID if applicable */
    convoyId;
    constructor(message, code = GasTownErrorCode.CONVOY_NOT_FOUND, context, cause) {
        super(message, code, context, cause);
        this.name = 'ConvoyError';
        if (context?.convoyId && typeof context.convoyId === 'string') {
            this.convoyId = context.convoyId;
        }
        if (Error.captureStackTrace) {
            Error.captureStackTrace(this, ConvoyError);
        }
    }
    /**
     * Create a ConvoyError for not found
     */
    static notFound(convoyId) {
        return new ConvoyError(`Convoy not found: ${convoyId}`, GasTownErrorCode.CONVOY_NOT_FOUND, { convoyId });
    }
    /**
     * Create a ConvoyError for create failure
     */
    static createFailed(reason, cause) {
        return new ConvoyError(`Failed to create convoy: ${reason}`, GasTownErrorCode.CONVOY_CREATE_FAILED, { operation: 'create' }, cause);
    }
}
// ============================================================================
// Error Utilities
// ============================================================================
/**
 * Type guard for GasTownError
 */
export function isGasTownError(error) {
    return error instanceof GasTownError;
}
/**
 * Type guard for ValidationError
 */
export function isValidationError(error) {
    return error instanceof ValidationError;
}
/**
 * Type guard for CLIExecutionError
 */
export function isCLIExecutionError(error) {
    return error instanceof CLIExecutionError;
}
/**
 * Type guard for BeadsError
 */
export function isBeadsError(error) {
    return error instanceof BeadsError;
}
/**
 * Wrap an unknown error as a GasTownError
 */
export function wrapError(error, code) {
    if (error instanceof GasTownError) {
        return error;
    }
    if (error instanceof Error) {
        return new GasTownError(error.message, code ?? GasTownErrorCode.UNKNOWN, undefined, error);
    }
    return new GasTownError(String(error), code ?? GasTownErrorCode.UNKNOWN);
}
/**
 * Extract error message safely
 */
export function getErrorMessage(error) {
    if (error instanceof Error) {
        return error.message;
    }
    return String(error);
}
//# sourceMappingURL=errors.js.map