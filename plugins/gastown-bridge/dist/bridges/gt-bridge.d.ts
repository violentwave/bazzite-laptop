/**
 * Gas Town CLI Bridge
 *
 * Provides a secure wrapper around the `gt` (Gas Town) CLI tool.
 * Implements command execution with proper input sanitization,
 * argument validation, and error handling.
 *
 * Security Features:
 * - All inputs validated with Zod schemas
 * - No shell execution (uses execFile)
 * - Command allowlist enforcement
 * - Argument sanitization
 *
 * @module v3/plugins/gastown-bridge/bridges/gt-bridge
 */
import { z } from 'zod';
/**
 * Safe string pattern - no shell metacharacters
 */
declare const SafeStringSchema: z.ZodEffects<z.ZodString, string, string>;
/**
 * Safe identifier pattern - alphanumeric with underscore/hyphen
 */
declare const IdentifierSchema: z.ZodString;
/**
 * Gas price schema
 */
declare const GasPriceSchema: z.ZodNumber;
/**
 * Gas limit schema
 */
declare const GasLimitSchema: z.ZodNumber;
/**
 * Transaction hash schema (0x prefixed hex)
 */
declare const TxHashSchema: z.ZodString;
/**
 * Address schema (0x prefixed hex)
 */
declare const AddressSchema: z.ZodString;
/**
 * Network schema
 */
declare const NetworkSchema: z.ZodEnum<["mainnet", "goerli", "sepolia", "polygon", "arbitrum", "optimism", "base", "local"]>;
/**
 * GT command argument schema
 */
declare const GtArgumentSchema: z.ZodEffects<z.ZodEffects<z.ZodString, string, string>, string, string>;
/**
 * Gas Town executor configuration
 */
export interface GtBridgeConfig {
    /**
     * Path to gt executable
     * Default: 'gt' (assumes in PATH)
     */
    gtPath?: string;
    /**
     * Working directory for execution
     */
    cwd?: string;
    /**
     * Execution timeout in milliseconds
     * Default: 30000 (30 seconds)
     */
    timeout?: number;
    /**
     * Maximum buffer size for output
     * Default: 10MB
     */
    maxBuffer?: number;
    /**
     * Environment variables
     */
    env?: NodeJS.ProcessEnv;
    /**
     * Default network
     */
    defaultNetwork?: z.infer<typeof NetworkSchema>;
}
/**
 * Gas estimation result
 */
export interface GasEstimate {
    gasLimit: number;
    gasPrice: string;
    maxFeePerGas?: string;
    maxPriorityFeePerGas?: string;
    estimatedCost: string;
    estimatedCostUsd?: number;
}
/**
 * Transaction status
 */
export interface TxStatus {
    hash: string;
    status: 'pending' | 'confirmed' | 'failed' | 'dropped';
    blockNumber?: number;
    confirmations?: number;
    gasUsed?: number;
    effectiveGasPrice?: string;
    error?: string;
}
/**
 * Network status
 */
export interface NetworkStatus {
    network: string;
    chainId: number;
    blockNumber: number;
    baseFee?: string;
    gasPrice?: string;
    connected: boolean;
}
/**
 * GT execution result
 */
export interface GtResult<T = unknown> {
    success: boolean;
    data?: T;
    error?: string;
    command: string;
    args: string[];
    durationMs: number;
}
/**
 * Logger interface
 */
export interface GtLogger {
    debug: (msg: string, meta?: Record<string, unknown>) => void;
    info: (msg: string, meta?: Record<string, unknown>) => void;
    warn: (msg: string, meta?: Record<string, unknown>) => void;
    error: (msg: string, meta?: Record<string, unknown>) => void;
}
/**
 * Gas Town bridge error codes
 */
export type GtErrorCode = 'COMMAND_NOT_FOUND' | 'EXECUTION_FAILED' | 'TIMEOUT' | 'INVALID_ARGUMENT' | 'INVALID_OUTPUT' | 'NETWORK_ERROR' | 'VALIDATION_ERROR';
/**
 * Gas Town bridge error
 */
export declare class GtBridgeError extends Error {
    readonly code: GtErrorCode;
    readonly command?: string | undefined;
    readonly args?: string[] | undefined;
    readonly cause?: Error | undefined;
    constructor(message: string, code: GtErrorCode, command?: string | undefined, args?: string[] | undefined, cause?: Error | undefined);
}
/**
 * Gas Town CLI Bridge
 *
 * Secure wrapper around the `gt` CLI tool for gas estimation
 * and transaction management.
 *
 * @example
 * ```typescript
 * const gtBridge = new GtBridge({ gtPath: '/usr/local/bin/gt' });
 * await gtBridge.initialize();
 *
 * const estimate = await gtBridge.estimateGas({
 *   to: '0x...',
 *   data: '0x...',
 *   network: 'mainnet',
 * });
 * ```
 */
export declare class GtBridge {
    private config;
    private logger;
    private initialized;
    /** Commands that can be cached (read-only, no side effects) */
    private static readonly CACHEABLE_COMMANDS;
    /** Commands that should use longer cache (static data) */
    private static readonly STATIC_COMMANDS;
    constructor(config?: GtBridgeConfig, logger?: GtLogger);
    /**
     * Initialize the bridge and verify gt is available
     */
    initialize(): Promise<void>;
    /**
     * Execute a gt command with validated arguments
     *
     * @param args - Command arguments (validated and sanitized)
     * @returns Command output
     */
    execGt(args: string[], skipCache?: boolean): Promise<GtResult<string>>;
    /**
     * Parse JSON output from gt command
     *
     * @param output - Raw command output
     * @returns Parsed JSON object
     */
    parseGtOutput<T>(output: string): T;
    /**
     * Estimate gas for a transaction
     */
    estimateGas(params: {
        to: string;
        data?: string;
        value?: string;
        from?: string;
        network?: z.infer<typeof NetworkSchema>;
    }): Promise<GasEstimate>;
    /**
     * Get transaction status
     */
    getTxStatus(txHash: string, network?: z.infer<typeof NetworkSchema>): Promise<TxStatus>;
    /**
     * Get network status
     */
    getNetworkStatus(network?: z.infer<typeof NetworkSchema>): Promise<NetworkStatus>;
    /**
     * Get current gas price
     */
    getGasPrice(network?: z.infer<typeof NetworkSchema>): Promise<{
        gasPrice: string;
        maxFeePerGas?: string;
        maxPriorityFeePerGas?: string;
        baseFee?: string;
    }>;
    /**
     * Simulate a transaction
     */
    simulate(params: {
        to: string;
        data: string;
        value?: string;
        from?: string;
        network?: z.infer<typeof NetworkSchema>;
        blockNumber?: number;
    }): Promise<{
        success: boolean;
        returnData?: string;
        gasUsed?: number;
        logs?: unknown[];
        error?: string;
    }>;
    /**
     * Decode transaction data
     */
    decode(data: string, abi?: string): Promise<{
        method: string;
        args: unknown[];
        signature: string;
    }>;
    /**
     * Validate and sanitize command arguments
     */
    private validateAndSanitizeArgs;
    /**
     * Ensure bridge is initialized
     */
    private ensureInitialized;
    /**
     * Check if bridge is initialized
     */
    isInitialized(): boolean;
    /**
     * Get current configuration
     */
    getConfig(): Readonly<Required<GtBridgeConfig>>;
    /**
     * Get cache statistics for performance monitoring
     */
    getCacheStats(): {
        resultCache: {
            entries: number;
            sizeBytes: number;
        };
        staticCache: {
            entries: number;
            sizeBytes: number;
        };
        parsedCache: {
            entries: number;
            sizeBytes: number;
        };
    };
    /**
     * Clear all caches (useful for testing or memory pressure)
     */
    clearCaches(): void;
}
/**
 * Create a new Gas Town bridge instance
 */
export declare function createGtBridge(config?: GtBridgeConfig, logger?: GtLogger): GtBridge;
export { SafeStringSchema, IdentifierSchema, GasPriceSchema, GasLimitSchema, TxHashSchema, AddressSchema, NetworkSchema, GtArgumentSchema, };
export default GtBridge;
//# sourceMappingURL=gt-bridge.d.ts.map