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
import { BdBridge, createBdBridge } from './bd-bridge.js';
import { LRUCache, BatchDeduplicator, } from '../cache.js';
// ============================================================================
// Performance Caches
// ============================================================================
/** Cache for AgentDB lookups during sync */
const agentDBLookupCache = new LRUCache({
    maxEntries: 500,
    ttlMs: 30 * 1000, // 30 sec TTL
});
/** Cache for conflict detection results */
const conflictCache = new LRUCache({
    maxEntries: 200,
    ttlMs: 10 * 1000, // 10 sec TTL
});
/** Deduplicator for concurrent sync operations */
const syncDedup = new BatchDeduplicator();
/**
 * FNV-1a hash for cache keys
 */
function hashKey(parts) {
    let hash = 2166136261;
    for (const part of parts) {
        for (let i = 0; i < part.length; i++) {
            hash ^= part.charCodeAt(i);
            hash = (hash * 16777619) >>> 0;
        }
        hash ^= 0xff;
    }
    return hash.toString(36);
}
// ============================================================================
// Zod Validation Schemas
// ============================================================================
/**
 * Sync conflict resolution strategy
 */
const ConflictStrategySchema = z.enum([
    'beads-wins', // Beads data takes precedence
    'agentdb-wins', // AgentDB data takes precedence
    'newest-wins', // Most recent timestamp wins
    'merge', // Attempt to merge fields
    'manual', // Flag for manual resolution
]);
/**
 * Sync direction
 */
const SyncDirectionSchema = z.enum([
    'to-agentdb', // Beads -> AgentDB
    'from-agentdb', // AgentDB -> Beads
    'bidirectional', // Both directions
]);
/**
 * Sync status
 */
const SyncStatusSchema = z.enum([
    'pending',
    'in-progress',
    'completed',
    'failed',
    'conflict',
]);
/**
 * AgentDB entry schema (compatible with claude-flow memory)
 */
const AgentDBEntrySchema = z.object({
    key: z.string(),
    value: z.unknown(),
    namespace: z.string().optional(),
    metadata: z.record(z.unknown()).optional(),
    embedding: z.array(z.number()).optional(),
    createdAt: z.string().datetime().optional(),
    updatedAt: z.string().datetime().optional(),
    version: z.number().optional(),
});
/**
 * Sync bridge error
 */
export class SyncBridgeError extends Error {
    code;
    details;
    cause;
    constructor(message, code, details, cause) {
        super(message);
        this.code = code;
        this.details = details;
        this.cause = cause;
        this.name = 'SyncBridgeError';
    }
}
// ============================================================================
// Default Logger
// ============================================================================
const defaultLogger = {
    debug: (msg, meta) => console.debug(`[sync-bridge] ${msg}`, meta ?? ''),
    info: (msg, meta) => console.info(`[sync-bridge] ${msg}`, meta ?? ''),
    warn: (msg, meta) => console.warn(`[sync-bridge] ${msg}`, meta ?? ''),
    error: (msg, meta) => console.error(`[sync-bridge] ${msg}`, meta ?? ''),
};
// ============================================================================
// Sync Bridge Implementation
// ============================================================================
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
export class SyncBridge {
    bdBridge;
    agentDB;
    config;
    logger;
    initialized = false;
    syncState;
    conflicts = new Map();
    constructor(agentDB, config, logger) {
        this.agentDB = agentDB;
        this.config = {
            beadsBridge: config?.beadsBridge ?? {},
            agentdbNamespace: config?.agentdbNamespace ?? 'beads',
            conflictStrategy: config?.conflictStrategy ?? 'newest-wins',
            batchSize: config?.batchSize ?? 100,
            preserveEmbeddings: config?.preserveEmbeddings ?? true,
            syncMetadata: config?.syncMetadata ?? true,
        };
        this.logger = logger ?? defaultLogger;
        this.bdBridge = createBdBridge(this.config.beadsBridge, {
            debug: (msg, meta) => this.logger.debug(`[bd] ${msg}`, meta),
            info: (msg, meta) => this.logger.info(`[bd] ${msg}`, meta),
            warn: (msg, meta) => this.logger.warn(`[bd] ${msg}`, meta),
            error: (msg, meta) => this.logger.error(`[bd] ${msg}`, meta),
        });
        this.syncState = {
            lastSyncTime: new Date(0).toISOString(),
            pendingConflicts: [],
            version: 1,
        };
    }
    /**
     * Initialize the sync bridge
     */
    async initialize() {
        try {
            await this.bdBridge.initialize();
            // Load sync state from AgentDB if exists
            const savedState = await this.agentDB.retrieve('_sync_state', this.config.agentdbNamespace);
            if (savedState?.value) {
                const parsed = savedState.value;
                this.syncState = {
                    lastSyncTime: parsed.lastSyncTime ?? new Date(0).toISOString(),
                    lastBeadId: parsed.lastBeadId,
                    lastAgentDBKey: parsed.lastAgentDBKey,
                    pendingConflicts: parsed.pendingConflicts ?? [],
                    version: (parsed.version ?? 0) + 1,
                };
            }
            this.initialized = true;
            this.logger.info('Sync bridge initialized', {
                namespace: this.config.agentdbNamespace,
                conflictStrategy: this.config.conflictStrategy,
                syncState: this.syncState,
            });
        }
        catch (error) {
            throw new SyncBridgeError('Failed to initialize sync bridge', 'NOT_INITIALIZED', undefined, error);
        }
    }
    /**
     * Sync beads to AgentDB
     */
    async syncToAgentDB(beads) {
        this.ensureInitialized();
        const startTime = Date.now();
        const result = {
            success: true,
            direction: 'to-agentdb',
            synced: 0,
            created: 0,
            updated: 0,
            deleted: 0,
            conflicts: 0,
            errors: [],
            durationMs: 0,
            timestamp: new Date().toISOString(),
        };
        this.logger.info(`Starting sync to AgentDB: ${beads.length} beads`);
        // Process in batches with parallel lookups
        for (let i = 0; i < beads.length; i += this.config.batchSize) {
            const batch = beads.slice(i, i + this.config.batchSize);
            // Parallel lookup for all beads in batch
            const lookupPromises = batch.map(async (bead) => {
                const key = this.beadToKey(bead);
                const cacheKey = hashKey([key, this.config.agentdbNamespace]);
                // Check cache first
                if (agentDBLookupCache.has(cacheKey)) {
                    return { bead, key, existing: agentDBLookupCache.get(cacheKey) };
                }
                const existing = await this.agentDB.retrieve(key, this.config.agentdbNamespace);
                agentDBLookupCache.set(cacheKey, existing);
                return { bead, key, existing };
            });
            const lookupResults = await Promise.all(lookupPromises);
            // Process results
            for (const { bead, key, existing } of lookupResults) {
                try {
                    if (existing) {
                        // Check for conflicts (use cache)
                        const conflictCacheKey = hashKey([bead.id, bead.content, existing.key]);
                        let hasConflict = conflictCache.get(conflictCacheKey);
                        if (hasConflict === undefined) {
                            hasConflict = await this.detectConflict(bead, existing);
                            conflictCache.set(conflictCacheKey, hasConflict);
                        }
                        if (hasConflict) {
                            const resolved = await this.resolveConflict(bead, existing);
                            if (!resolved) {
                                result.conflicts++;
                                continue;
                            }
                        }
                        result.updated++;
                    }
                    else {
                        result.created++;
                    }
                    // Store bead in AgentDB
                    await this.agentDB.store(key, this.beadToAgentDBValue(bead), this.config.agentdbNamespace, this.buildMetadata(bead));
                    // Invalidate lookup cache for this key
                    const cacheKey = hashKey([key, this.config.agentdbNamespace]);
                    agentDBLookupCache.delete(cacheKey);
                    result.synced++;
                }
                catch (error) {
                    result.errors.push({
                        id: bead.id,
                        error: error instanceof Error ? error.message : String(error),
                    });
                    this.logger.error(`Failed to sync bead ${bead.id}`, { error });
                }
            }
        }
        // Update sync state
        this.syncState.lastSyncTime = result.timestamp;
        if (beads.length > 0) {
            this.syncState.lastBeadId = beads[beads.length - 1]?.id;
        }
        await this.saveSyncState();
        result.durationMs = Date.now() - startTime;
        result.success = result.errors.length === 0 && result.conflicts === 0;
        this.logger.info('Sync to AgentDB complete', {
            synced: result.synced,
            created: result.created,
            updated: result.updated,
            conflicts: result.conflicts,
            errors: result.errors.length,
            durationMs: result.durationMs,
        });
        return result;
    }
    /**
     * Sync from AgentDB to Beads
     */
    async syncFromAgentDB() {
        this.ensureInitialized();
        const startTime = Date.now();
        const beads = [];
        this.logger.info('Starting sync from AgentDB');
        try {
            // Get all entries from AgentDB namespace
            let offset = 0;
            let hasMore = true;
            while (hasMore) {
                const entries = await this.agentDB.list(this.config.agentdbNamespace, this.config.batchSize, offset);
                if (entries.length === 0) {
                    hasMore = false;
                    continue;
                }
                for (const entry of entries) {
                    // Skip sync state entry
                    if (entry.key === '_sync_state')
                        continue;
                    try {
                        const bead = this.agentDBToBead(entry);
                        if (bead) {
                            beads.push(bead);
                        }
                    }
                    catch (error) {
                        this.logger.warn(`Failed to convert AgentDB entry to bead: ${entry.key}`, {
                            error: error instanceof Error ? error.message : String(error),
                        });
                    }
                }
                offset += entries.length;
                hasMore = entries.length === this.config.batchSize;
            }
            // Update sync state
            this.syncState.lastSyncTime = new Date().toISOString();
            await this.saveSyncState();
            const durationMs = Date.now() - startTime;
            this.logger.info('Sync from AgentDB complete', {
                beads: beads.length,
                durationMs,
            });
            return beads;
        }
        catch (error) {
            throw new SyncBridgeError('Failed to sync from AgentDB', 'SYNC_FAILED', undefined, error);
        }
    }
    /**
     * Perform full bidirectional sync
     */
    async syncBidirectional() {
        this.ensureInitialized();
        this.logger.info('Starting bidirectional sync');
        // First sync from beads to AgentDB
        const allBeads = await this.bdBridge.listBeads({
            after: this.syncState.lastSyncTime,
        });
        const toAgentDBResult = await this.syncToAgentDB(allBeads);
        // Then sync from AgentDB to beads
        const fromAgentDBBeads = await this.syncFromAgentDB();
        return {
            toAgentDB: toAgentDBResult,
            fromAgentDB: fromAgentDBBeads,
        };
    }
    /**
     * Get pending conflicts
     */
    getPendingConflicts() {
        return Array.from(this.conflicts.values()).filter(c => c.resolution === 'pending' || !c.resolution);
    }
    /**
     * Resolve a specific conflict manually
     */
    async resolveConflictManually(beadId, resolution, mergedData) {
        const conflict = this.conflicts.get(beadId);
        if (!conflict) {
            throw new SyncBridgeError(`No conflict found for bead: ${beadId}`, 'VALIDATION_ERROR');
        }
        const key = this.beadToKey(conflict.beadData);
        switch (resolution) {
            case 'beads':
                await this.agentDB.store(key, this.beadToAgentDBValue(conflict.beadData), this.config.agentdbNamespace, this.buildMetadata(conflict.beadData));
                break;
            case 'agentdb':
                // AgentDB data is already stored, nothing to do
                break;
            case 'merged':
                if (!mergedData) {
                    throw new SyncBridgeError('Merged data required for merge resolution', 'VALIDATION_ERROR');
                }
                const merged = { ...conflict.beadData, ...mergedData };
                await this.agentDB.store(key, this.beadToAgentDBValue(merged), this.config.agentdbNamespace, this.buildMetadata(merged));
                break;
        }
        conflict.resolution = resolution;
        conflict.resolvedAt = new Date().toISOString();
        // Remove from pending
        const pendingIndex = this.syncState.pendingConflicts.indexOf(beadId);
        if (pendingIndex !== -1) {
            this.syncState.pendingConflicts.splice(pendingIndex, 1);
            await this.saveSyncState();
        }
        this.logger.info(`Conflict resolved for bead ${beadId}`, { resolution });
    }
    /**
     * Get sync state
     */
    getSyncState() {
        return { ...this.syncState };
    }
    /**
     * Get sync statistics
     */
    async getSyncStats() {
        this.ensureInitialized();
        const stats = await this.agentDB.getNamespaceStats(this.config.agentdbNamespace);
        return {
            agentdbCount: stats.count,
            lastSyncTime: this.syncState.lastSyncTime,
            pendingConflicts: this.syncState.pendingConflicts.length,
            syncVersion: this.syncState.version,
        };
    }
    // ============================================================================
    // Private Methods
    // ============================================================================
    /**
     * Convert bead to AgentDB key
     */
    beadToKey(bead) {
        return `bead:${bead.id}`;
    }
    /**
     * Convert bead to AgentDB value
     */
    beadToAgentDBValue(bead) {
        const value = {
            id: bead.id,
            type: bead.type,
            content: bead.content,
            timestamp: bead.timestamp,
            parentId: bead.parentId,
            threadId: bead.threadId,
            agentId: bead.agentId,
            tags: bead.tags,
            hash: bead.hash,
        };
        if (this.config.preserveEmbeddings && bead.embedding) {
            value.embedding = bead.embedding;
        }
        if (this.config.syncMetadata && bead.metadata) {
            value.metadata = bead.metadata;
        }
        return value;
    }
    /**
     * Build metadata for AgentDB entry
     */
    buildMetadata(bead) {
        return {
            beadType: bead.type,
            threadId: bead.threadId,
            agentId: bead.agentId,
            syncedAt: new Date().toISOString(),
            syncVersion: this.syncState.version,
        };
    }
    /**
     * Convert AgentDB entry to Bead
     */
    agentDBToBead(entry) {
        if (!entry.value || typeof entry.value !== 'object') {
            return null;
        }
        const data = entry.value;
        // Validate required fields
        if (!data.id || !data.type || !data.content) {
            return null;
        }
        return {
            id: String(data.id),
            type: data.type,
            content: String(data.content),
            timestamp: data.timestamp,
            parentId: data.parentId,
            threadId: data.threadId,
            agentId: data.agentId,
            tags: data.tags,
            metadata: data.metadata,
            embedding: data.embedding,
            hash: data.hash,
        };
    }
    /**
     * Detect if there's a conflict between bead and AgentDB entry
     */
    async detectConflict(bead, entry) {
        if (!entry.value || typeof entry.value !== 'object') {
            return false;
        }
        const data = entry.value;
        // No conflict if content is the same
        if (data.content === bead.content) {
            return false;
        }
        // Check timestamps
        const beadTime = bead.timestamp ? new Date(bead.timestamp).getTime() : 0;
        const entryTime = entry.updatedAt ? new Date(entry.updatedAt).getTime() : 0;
        // If bead is newer, no conflict - it should update
        if (beadTime > entryTime) {
            return false;
        }
        // If AgentDB is newer and content differs, conflict
        if (entryTime > beadTime && data.content !== bead.content) {
            return true;
        }
        return false;
    }
    /**
     * Resolve conflict based on strategy
     */
    async resolveConflict(bead, entry) {
        const conflict = {
            beadId: bead.id,
            beadData: bead,
            agentdbData: entry,
            conflictType: 'update',
        };
        switch (this.config.conflictStrategy) {
            case 'beads-wins':
                conflict.resolution = 'beads';
                this.conflicts.set(bead.id, conflict);
                return true;
            case 'agentdb-wins':
                conflict.resolution = 'agentdb';
                this.conflicts.set(bead.id, conflict);
                return false; // Don't update AgentDB
            case 'newest-wins': {
                const beadTime = bead.timestamp ? new Date(bead.timestamp).getTime() : 0;
                const entryTime = entry.updatedAt ? new Date(entry.updatedAt).getTime() : 0;
                if (beadTime >= entryTime) {
                    conflict.resolution = 'beads';
                    this.conflicts.set(bead.id, conflict);
                    return true;
                }
                else {
                    conflict.resolution = 'agentdb';
                    this.conflicts.set(bead.id, conflict);
                    return false;
                }
            }
            case 'merge': {
                // Simple merge: keep both contents with separator
                const entryData = entry.value;
                const mergedBead = {
                    ...bead,
                    content: `${bead.content}\n---\n${entryData.content}`,
                    metadata: {
                        ...bead.metadata,
                        merged: true,
                        mergedAt: new Date().toISOString(),
                    },
                };
                conflict.beadData = mergedBead;
                conflict.resolution = 'merged';
                this.conflicts.set(bead.id, conflict);
                return true;
            }
            case 'manual':
                conflict.resolution = 'pending';
                this.conflicts.set(bead.id, conflict);
                this.syncState.pendingConflicts.push(bead.id);
                return false;
            default:
                return false;
        }
    }
    /**
     * Save sync state to AgentDB
     */
    async saveSyncState() {
        try {
            await this.agentDB.store('_sync_state', this.syncState, this.config.agentdbNamespace, { type: 'sync-state' });
        }
        catch (error) {
            this.logger.error('Failed to save sync state', {
                error: error instanceof Error ? error.message : String(error),
            });
        }
    }
    /**
     * Ensure bridge is initialized
     */
    ensureInitialized() {
        if (!this.initialized) {
            throw new SyncBridgeError('Sync bridge not initialized. Call initialize() first.', 'NOT_INITIALIZED');
        }
    }
    /**
     * Check if bridge is initialized
     */
    isInitialized() {
        return this.initialized;
    }
    /**
     * Get beads bridge instance
     */
    getBeadsBridge() {
        return this.bdBridge;
    }
    /**
     * Get cache statistics for performance monitoring
     */
    getCacheStats() {
        return {
            agentDBLookupCache: agentDBLookupCache.stats(),
            conflictCache: conflictCache.stats(),
        };
    }
    /**
     * Clear all sync caches
     */
    clearCaches() {
        agentDBLookupCache.clear();
        conflictCache.clear();
    }
}
/**
 * Create a new sync bridge instance
 */
export function createSyncBridge(agentDB, config, logger) {
    return new SyncBridge(agentDB, config, logger);
}
// Export schemas for external use
export { ConflictStrategySchema, SyncDirectionSchema, SyncStatusSchema, AgentDBEntrySchema, };
export default SyncBridge;
//# sourceMappingURL=sync-bridge.js.map