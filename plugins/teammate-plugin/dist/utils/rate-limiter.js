/**
 * Rate Limiter for TeammateTool operations
 *
 * Implements sliding window rate limiting to prevent abuse
 * and ensure fair resource distribution across teammates.
 *
 * @module @claude-flow/teammate-plugin/utils/rate-limiter
 */
/**
 * Rate limiter with configurable per-operation limits
 */
export class RateLimiter {
    config;
    windows = new Map();
    windowMs = 60000; // 1 minute window
    constructor(config) {
        this.config = config;
    }
    /**
     * Check if operation is allowed under rate limit
     */
    checkLimit(operation) {
        const limit = this.config[operation];
        const now = Date.now();
        const state = this.windows.get(operation);
        if (!state || now - state.windowStart >= this.windowMs) {
            // New window
            this.windows.set(operation, {
                operation,
                count: 1,
                windowStart: now,
                blocked: false,
            });
            return true;
        }
        if (state.count >= limit) {
            state.blocked = true;
            state.nextAllowedAt = state.windowStart + this.windowMs;
            return false;
        }
        state.count++;
        return true;
    }
    /**
     * Get current state for an operation
     */
    getState(operation) {
        return this.windows.get(operation);
    }
    /**
     * Reset rate limit for an operation
     */
    reset(operation) {
        if (operation) {
            this.windows.delete(operation);
        }
        else {
            this.windows.clear();
        }
    }
    /**
     * Get remaining quota for an operation
     */
    getRemaining(operation) {
        const limit = this.config[operation];
        const state = this.windows.get(operation);
        if (!state)
            return limit;
        return Math.max(0, limit - state.count);
    }
    /**
     * Get window duration in milliseconds
     */
    getWindowMs() {
        return this.windowMs;
    }
    /**
     * Check if an operation is currently blocked
     */
    isBlocked(operation) {
        const state = this.windows.get(operation);
        return state?.blocked ?? false;
    }
    /**
     * Get time until rate limit resets for an operation
     */
    getTimeUntilReset(operation) {
        const state = this.windows.get(operation);
        if (!state)
            return 0;
        const remaining = (state.windowStart + this.windowMs) - Date.now();
        return Math.max(0, remaining);
    }
}
//# sourceMappingURL=rate-limiter.js.map