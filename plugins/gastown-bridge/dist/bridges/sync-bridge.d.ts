/**
 * Beads-AgentDB Sync Bridge
 *
 * Provides bidirectional synchronization between Beads (bd)
 * and AgentDB. Implements conflict resolution strategies
 * and maintains consistency between the two systems.
 *
 * Features:
 * - Bidirectional sync (Beads <-> AgentDB)
 * - Conflict resolution strategies
 * - Incremental sync support
 * - Transaction-safe operations
 * - Embedding preservation
 *
 * @module v3/plugins/gastown-bridge/bridges/sync-bridge
 */
import { z } from 'zod';
import { BdBridge, type Bead, type BdBridgeConfig } from './bd-bridge.js';
/**
 * Sync conflict resolution strategy
 */
declare const ConflictStrategySchema: z.ZodEnum<["beads-wins", "agentdb-wins", "newest-wins", "merge", "manual"]>;
/**
 * Sync direction
 */
declare const SyncDirectionSchema: z.ZodEnum<["to-agentdb", "from-agentdb", "bidirectional"]>;
/**
 * Sync status
 */
declare const SyncStatusSchema: z.ZodEnum<["pending", "in-progress", "completed", "failed", "conflict"]>;
/**
 * AgentDB entry schema (compatible with claude-flow memory)
 */
declare const AgentDBEntrySchema: z.ZodObject<{
    key: z.ZodString;
    value: z.ZodUnknown;
    namespace: z.ZodOptional<z.ZodString>;
    metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    embedding: z.ZodOptional<z.ZodArray<z.ZodNumber, "many">>;
    createdAt: z.ZodOptional<z.ZodString>;
    updatedAt: z.ZodOptional<z.ZodString>;
    version: z.ZodOptional<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    key: string;
    value?: unknown;
    createdAt?: string | undefined;
    updatedAt?: string | undefined;
    metadata?: Record<string, unknown> | undefined;
    version?: number | undefined;
    embedding?: number[] | undefined;
    namespace?: string | undefined;
}, {
    key: string;
    value?: unknown;
    createdAt?: string | undefined;
    updatedAt?: string | undefined;
    metadata?: Record<string, unknown> | undefined;
    version?: number | undefined;
    embedding?: number[] | undefined;
    namespace?: string | undefined;
}>;
/**
 * Conflict resolution strategy type
 */
export type ConflictStrategy = z.infer<typeof ConflictStrategySchema>;
/**
 * Sync direction type
 */
export type SyncDirection = z.infer<typeof SyncDirectionSchema>;
/**
 * Sync status type
 */
export type SyncStatus = z.infer<typeof SyncStatusSchema>;
/**
 * AgentDB entry type
 */
export type AgentDBEntry = z.infer<typeof AgentDBEntrySchema>;
/**
 * Sync bridge configuration
 */
export interface SyncBridgeConfig {
    /**
     * Beads bridge configuration
     */
    beadsBridge?: BdBridgeConfig;
    /**
     * AgentDB namespace for beads
     * Default: 'beads'
     */
    agentdbNamespace?: string;
    /**
     * Conflict resolution strategy
     * Default: 'newest-wins'
     */
    conflictStrategy?: ConflictStrategy;
    /**
     * Batch size for sync operations
     * Default: 100
     */
    batchSize?: number;
    /**
     * Whether to preserve embeddings during sync
     * Default: true
     */
    preserveEmbeddings?: boolean;
    /**
     * Whether to sync metadata
     * Default: true
     */
    syncMetadata?: boolean;
}
/**
 * Sync operation result
 */
export interface SyncResult {
    success: boolean;
    direction: SyncDirection;
    synced: number;
    created: number;
    updated: number;
    deleted: number;
    conflicts: number;
    errors: Array<{
        id: string;
        error: string;
    }>;
    durationMs: number;
    timestamp: string;
}
/**
 * Conflict record
 */
export interface SyncConflict {
    beadId: string;
    beadData: Bead;
    agentdbData: AgentDBEntry;
    conflictType: 'update' | 'delete' | 'create';
    resolution?: 'beads' | 'agentdb' | 'merged' | 'pending';
    resolvedAt?: string;
}
/**
 * Sync state for incremental sync
 */
export interface SyncState {
    lastSyncTime: string;
    lastBeadId?: string;
    lastAgentDBKey?: string;
    pendingConflicts: string[];
    version: number;
}
/**
 * AgentDB interface (to be provided by claude-flow)
 */
export interface IAgentDBService {
    store(key: string, value: unknown, namespace?: string, metadata?: Record<string, unknown>): Promise<void>;
    retrieve(key: string, namespace?: string): Promise<AgentDBEntry | null>;
    search(query: string, namespace?: string, limit?: number): Promise<AgentDBEntry[]>;
    list(namespace?: string, limit?: number, offset?: number): Promise<AgentDBEntry[]>;
    delete(key: string, namespace?: string): Promise<void>;
    getNamespaceStats(namespace: string): Promise<{
        count: number;
        lastUpdated?: string;
    }>;
}
/**
 * Logger interface
 */
export interface SyncLogger {
    debug: (msg: string, meta?: Record<string, unknown>) => void;
    info: (msg: string, meta?: Record<string, unknown>) => void;
    warn: (msg: string, meta?: Record<string, unknown>) => void;
    error: (msg: string, meta?: Record<string, unknown>) => void;
}
/**
 * Sync bridge error codes
 */
export type SyncErrorCode = 'NOT_INITIALIZED' | 'SYNC_FAILED' | 'CONFLICT_UNRESOLVED' | 'AGENTDB_ERROR' | 'BEADS_ERROR' | 'VALIDATION_ERROR' | 'TRANSACTION_FAILED';
/**
 * Sync bridge error
 */
export declare class SyncBridgeError extends Error {
    readonly code: SyncErrorCode;
    readonly details?: Record<string, unknown> | undefined;
    readonly cause?: Error | undefined;
    constructor(message: string, code: SyncErrorCode, details?: Record<string, unknown> | undefined, cause?: Error | undefined);
}
/**
 * Beads-AgentDB Sync Bridge
 *
 * Provides bidirectional synchronization between Beads and AgentDB
 * with configurable conflict resolution.
 *
 * @example
 * ```typescript
 * const syncBridge = new SyncBridge(agentDB, {
 *   conflictStrategy: 'newest-wins',
 *   agentdbNamespace: 'conversation-beads',
 * });
 * await syncBridge.initialize();
 *
 * // Sync beads to AgentDB
 * const result = await syncBridge.syncToAgentDB(beads);
 *
 * // Sync from AgentDB back to beads
 * const beads = await syncBridge.syncFromAgentDB();
 * ```
 */
export declare class SyncBridge {
    private bdBridge;
    private agentDB;
    private config;
    private logger;
    private initialized;
    private syncState;
    private conflicts;
    constructor(agentDB: IAgentDBService, config?: SyncBridgeConfig, logger?: SyncLogger);
    /**
     * Initialize the sync bridge
     */
    initialize(): Promise<void>;
    /**
     * Sync beads to AgentDB
     */
    syncToAgentDB(beads: Bead[]): Promise<SyncResult>;
    /**
     * Sync from AgentDB to Beads
     */
    syncFromAgentDB(): Promise<Bead[]>;
    /**
     * Perform full bidirectional sync
     */
    syncBidirectional(): Promise<{
        toAgentDB: SyncResult;
        fromAgentDB: Bead[];
    }>;
    /**
     * Get pending conflicts
     */
    getPendingConflicts(): SyncConflict[];
    /**
     * Resolve a specific conflict manually
     */
    resolveConflictManually(beadId: string, resolution: 'beads' | 'agentdb' | 'merged', mergedData?: Partial<Bead>): Promise<void>;
    /**
     * Get sync state
     */
    getSyncState(): Readonly<SyncState>;
    /**
     * Get sync statistics
     */
    getSyncStats(): Promise<{
        agentdbCount: number;
        lastSyncTime: string;
        pendingConflicts: number;
        syncVersion: number;
    }>;
    /**
     * Convert bead to AgentDB key
     */
    private beadToKey;
    /**
     * Convert bead to AgentDB value
     */
    private beadToAgentDBValue;
    /**
     * Build metadata for AgentDB entry
     */
    private buildMetadata;
    /**
     * Convert AgentDB entry to Bead
     */
    private agentDBToBead;
    /**
     * Detect if there's a conflict between bead and AgentDB entry
     */
    private detectConflict;
    /**
     * Resolve conflict based on strategy
     */
    private resolveConflict;
    /**
     * Save sync state to AgentDB
     */
    private saveSyncState;
    /**
     * Ensure bridge is initialized
     */
    private ensureInitialized;
    /**
     * Check if bridge is initialized
     */
    isInitialized(): boolean;
    /**
     * Get beads bridge instance
     */
    getBeadsBridge(): BdBridge;
    /**
     * Get cache statistics for performance monitoring
     */
    getCacheStats(): {
        agentDBLookupCache: {
            entries: number;
            sizeBytes: number;
        };
        conflictCache: {
            entries: number;
            sizeBytes: number;
        };
    };
    /**
     * Clear all sync caches
     */
    clearCaches(): void;
}
/**
 * Create a new sync bridge instance
 */
export declare function createSyncBridge(agentDB: IAgentDBService, config?: SyncBridgeConfig, logger?: SyncLogger): SyncBridge;
export { ConflictStrategySchema, SyncDirectionSchema, SyncStatusSchema, AgentDBEntrySchema, };
export default SyncBridge;
//# sourceMappingURL=sync-bridge.d.ts.map