/**
 * Retry utilities for TeammateTool operations
 *
 * Provides exponential backoff retry logic with
 * configurable delays and error filtering.
 *
 * @module @claude-flow/teammate-plugin/utils/retry
 */
import type { RetryConfig, RetryState } from '../types.js';
/**
 * Execute a function with retry logic
 *
 * @param fn - Function to execute
 * @param config - Retry configuration
 * @param isRetryable - Optional function to determine if error is retryable
 * @returns Promise resolving to function result
 * @throws Last error if all retries exhausted
 */
export declare function withRetry<T>(fn: () => Promise<T>, config: RetryConfig, isRetryable?: (error: Error) => boolean): Promise<T>;
/**
 * Create a retry state tracker
 */
export declare function createRetryState(): RetryState;
/**
 * Calculate delay for a specific attempt using exponential backoff
 */
export declare function calculateBackoffDelay(attempt: number, config: RetryConfig): number;
/**
 * Sleep for a specified duration
 */
export declare function sleep(ms: number): Promise<void>;
/**
 * Execute with timeout
 */
export declare function withTimeout<T>(fn: () => Promise<T>, timeoutMs: number, timeoutError?: Error): Promise<T>;
//# sourceMappingURL=retry.d.ts.map