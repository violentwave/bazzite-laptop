/**
 * Circuit Breaker for TeammateTool operations
 *
 * Implements the circuit breaker pattern to prevent
 * cascading failures and allow graceful degradation.
 *
 * States:
 * - closed: Normal operation, requests pass through
 * - open: Failing, requests are rejected immediately
 * - half-open: Testing if service recovered
 *
 * @module @claude-flow/teammate-plugin/utils/circuit-breaker
 */
import type { CircuitBreakerConfig, CircuitBreakerState } from '../types.js';
import { TeammateErrorCode } from '../types.js';
/**
 * Error thrown when circuit breaker is open
 */
export declare class CircuitBreakerOpenError extends Error {
    readonly code: TeammateErrorCode;
    readonly nextAttemptAt?: Date | undefined;
    constructor(message: string, code?: TeammateErrorCode, nextAttemptAt?: Date | undefined);
}
/**
 * Circuit breaker with configurable thresholds and timeouts
 */
export declare class CircuitBreaker {
    private config;
    private state;
    constructor(config: CircuitBreakerConfig);
    private createInitialState;
    /**
     * Execute a function with circuit breaker protection
     */
    execute<T>(fn: () => Promise<T>): Promise<T>;
    /**
     * Record a successful operation
     */
    recordSuccess(): void;
    /**
     * Record a failed operation
     */
    recordFailure(): void;
    /**
     * Get current circuit breaker state
     */
    getState(): CircuitBreakerState;
    /**
     * Check if circuit is open
     */
    isOpen(): boolean;
    /**
     * Check if circuit is closed
     */
    isClosed(): boolean;
    /**
     * Check if circuit is half-open
     */
    isHalfOpen(): boolean;
    /**
     * Reset circuit breaker to initial state
     */
    reset(): void;
    /**
     * Force circuit to open state (for testing)
     */
    forceOpen(): void;
    /**
     * Force circuit to half-open state (for testing)
     */
    forceHalfOpen(): void;
}
//# sourceMappingURL=circuit-breaker.d.ts.map