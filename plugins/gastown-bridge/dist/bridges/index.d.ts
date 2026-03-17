/**
 * Gas Town Bridge Layer Exports
 *
 * CLI bridge modules for Gas Town (gt) and Beads (bd) integration.
 * Provides secure command execution with input validation and
 * AgentDB synchronization.
 *
 * @module v3/plugins/gastown-bridge/bridges
 */
export { GtBridge, createGtBridge, GtBridgeError, type GtBridgeConfig, type GasEstimate, type TxStatus, type NetworkStatus, type GtResult, type GtLogger, type GtErrorCode, SafeStringSchema as GtSafeStringSchema, IdentifierSchema as GtIdentifierSchema, GasPriceSchema, GasLimitSchema, TxHashSchema, AddressSchema, NetworkSchema, GtArgumentSchema, } from './gt-bridge.js';
export { BdBridge, createBdBridge, BdBridgeError, type Bead as CliBead, type BeadType as CliBeadType, type BdBridgeConfig, type BeadQuery, type CreateBeadParams, type BdResult, type BdStreamResult, type BdLogger, type BdErrorCode, BeadSchema as CliBeadSchema, BeadIdSchema, BeadTypeSchema as CliBeadTypeSchema, BdArgumentSchema, } from './bd-bridge.js';
export { SyncBridge, createSyncBridge, SyncBridgeError, type ConflictStrategy, type SyncDirection as CliSyncDirection, type SyncStatus, type AgentDBEntry, type SyncBridgeConfig, type SyncResult as CliSyncResult, type SyncConflict, type SyncState, type IAgentDBService, type SyncLogger, type SyncErrorCode, ConflictStrategySchema, SyncDirectionSchema as CliSyncDirectionSchema, SyncStatusSchema, AgentDBEntrySchema, } from './sync-bridge.js';
//# sourceMappingURL=index.d.ts.map