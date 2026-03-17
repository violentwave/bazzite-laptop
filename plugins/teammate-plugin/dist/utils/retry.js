/**
 * Retry utilities for TeammateTool operations
 *
 * Provides exponential backoff retry logic with
 * configurable delays and error filtering.
 *
 * @module @claude-flow/teammate-plugin/utils/retry
 */
/**
 * Execute a function with retry logic
 *
 * @param fn - Function to execute
 * @param config - Retry configuration
 * @param isRetryable - Optional function to determine if error is retryable
 * @returns Promise resolving to function result
 * @throws Last error if all retries exhausted
 */
export async function withRetry(fn, config, isRetryable) {
    let lastError = null;
    let delay = config.initialDelayMs;
    for (let attempt = 1; attempt <= config.maxRetries + 1; attempt++) {
        try {
            return await fn();
        }
        catch (error) {
            lastError = error instanceof Error ? error : new Error(String(error));
            // Check if error is retryable
            if (isRetryable && !isRetryable(lastError)) {
                throw lastError;
            }
            // Check if we've exhausted retries
            if (attempt > config.maxRetries) {
                throw lastError;
            }
            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, delay));
            // Exponential backoff
            delay = Math.min(delay * config.backoffMultiplier, config.maxDelayMs);
        }
    }
    throw lastError;
}
/**
 * Create a retry state tracker
 */
export function createRetryState() {
    return {
        attempt: 0,
        lastError: null,
        nextRetryAt: null,
        totalDelayMs: 0,
    };
}
/**
 * Calculate delay for a specific attempt using exponential backoff
 */
export function calculateBackoffDelay(attempt, config) {
    const delay = config.initialDelayMs * Math.pow(config.backoffMultiplier, attempt - 1);
    return Math.min(delay, config.maxDelayMs);
}
/**
 * Sleep for a specified duration
 */
export function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
/**
 * Execute with timeout
 */
export async function withTimeout(fn, timeoutMs, timeoutError) {
    return Promise.race([
        fn(),
        new Promise((_, reject) => setTimeout(() => reject(timeoutError ?? new Error(`Operation timed out after ${timeoutMs}ms`)), timeoutMs)),
    ]);
}
//# sourceMappingURL=retry.js.map