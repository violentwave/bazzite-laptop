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
import { TeammateErrorCode } from '../types.js';
/**
 * Error thrown when circuit breaker is open
 */
export class CircuitBreakerOpenError extends Error {
    code;
    nextAttemptAt;
    constructor(message, code = TeammateErrorCode.BACKEND_UNAVAILABLE, nextAttemptAt) {
        super(message);
        this.code = code;
        this.nextAttemptAt = nextAttemptAt;
        this.name = 'CircuitBreakerOpenError';
    }
}
/**
 * Circuit breaker with configurable thresholds and timeouts
 */
export class CircuitBreaker {
    config;
    state;
    constructor(config) {
        this.config = config;
        this.state = this.createInitialState();
    }
    createInitialState() {
        return {
            state: 'closed',
            failures: 0,
            successes: 0,
            lastFailure: null,
            lastSuccess: null,
            openedAt: null,
            nextAttemptAt: null,
        };
    }
    /**
     * Execute a function with circuit breaker protection
     */
    async execute(fn) {
        if (!this.config.enabled) {
            return fn();
        }
        if (this.state.state === 'open') {
            if (this.state.nextAttemptAt && Date.now() >= this.state.nextAttemptAt.getTime()) {
                this.state.state = 'half-open';
            }
            else {
                throw new CircuitBreakerOpenError('Circuit breaker is open', TeammateErrorCode.BACKEND_UNAVAILABLE, this.state.nextAttemptAt ?? undefined);
            }
        }
        try {
            const result = await Promise.race([
                fn(),
                new Promise((_, reject) => setTimeout(() => reject(new Error('Circuit breaker timeout')), this.config.timeoutMs)),
            ]);
            this.recordSuccess();
            return result;
        }
        catch (error) {
            this.recordFailure();
            throw error;
        }
    }
    /**
     * Record a successful operation
     */
    recordSuccess() {
        this.state.failures = 0;
        this.state.successes++;
        this.state.lastSuccess = new Date();
        if (this.state.state === 'half-open' && this.state.successes >= this.config.successThreshold) {
            this.state.state = 'closed';
            this.state.openedAt = null;
            this.state.nextAttemptAt = null;
        }
    }
    /**
     * Record a failed operation
     */
    recordFailure() {
        this.state.failures++;
        this.state.successes = 0;
        this.state.lastFailure = new Date();
        if (this.state.failures >= this.config.failureThreshold) {
            this.state.state = 'open';
            this.state.openedAt = new Date();
            this.state.nextAttemptAt = new Date(Date.now() + this.config.resetTimeMs);
        }
    }
    /**
     * Get current circuit breaker state
     */
    getState() {
        return { ...this.state };
    }
    /**
     * Check if circuit is open
     */
    isOpen() {
        return this.state.state === 'open';
    }
    /**
     * Check if circuit is closed
     */
    isClosed() {
        return this.state.state === 'closed';
    }
    /**
     * Check if circuit is half-open
     */
    isHalfOpen() {
        return this.state.state === 'half-open';
    }
    /**
     * Reset circuit breaker to initial state
     */
    reset() {
        this.state = this.createInitialState();
    }
    /**
     * Force circuit to open state (for testing)
     */
    forceOpen() {
        this.state.state = 'open';
        this.state.openedAt = new Date();
        this.state.nextAttemptAt = new Date(Date.now() + this.config.resetTimeMs);
    }
    /**
     * Force circuit to half-open state (for testing)
     */
    forceHalfOpen() {
        this.state.state = 'half-open';
    }
}
//# sourceMappingURL=circuit-breaker.js.map