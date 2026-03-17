/**
 * Rate Limiter for TeammateTool operations
 *
 * Implements sliding window rate limiting to prevent abuse
 * and ensure fair resource distribution across teammates.
 *
 * @module @claude-flow/teammate-plugin/utils/rate-limiter
 */
import type { RateLimitConfig, RateLimitState } from '../types.js';
/**
 * Rate limiter with configurable per-operation limits
 */
export declare class RateLimiter {
    private config;
    private windows;
    private readonly windowMs;
    constructor(config: RateLimitConfig);
    /**
     * Check if operation is allowed under rate limit
     */
    checkLimit(operation: keyof RateLimitConfig): boolean;
    /**
     * Get current state for an operation
     */
    getState(operation: string): RateLimitState | undefined;
    /**
     * Reset rate limit for an operation
     */
    reset(operation?: string): void;
    /**
     * Get remaining quota for an operation
     */
    getRemaining(operation: keyof RateLimitConfig): number;
    /**
     * Get window duration in milliseconds
     */
    getWindowMs(): number;
    /**
     * Check if an operation is currently blocked
     */
    isBlocked(operation: keyof RateLimitConfig): boolean;
    /**
     * Get time until rate limit resets for an operation
     */
    getTimeUntilReset(operation: keyof RateLimitConfig): number;
}
//# sourceMappingURL=rate-limiter.d.ts.map