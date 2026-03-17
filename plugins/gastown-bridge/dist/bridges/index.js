/**
 * Gas Town Bridge Layer Exports
 *
 * CLI bridge modules for Gas Town (gt) and Beads (bd) integration.
 * Provides secure command execution with input validation and
 * AgentDB synchronization.
 *
 * @module v3/plugins/gastown-bridge/bridges
 */
// Gas Town CLI Bridge
export { GtBridge, createGtBridge, GtBridgeError, 
// Schemas
SafeStringSchema as GtSafeStringSchema, IdentifierSchema as GtIdentifierSchema, GasPriceSchema, GasLimitSchema, TxHashSchema, AddressSchema, NetworkSchema, GtArgumentSchema, } from './gt-bridge.js';
// Beads CLI Bridge
export { BdBridge, createBdBridge, BdBridgeError, 
// Schemas - renamed to avoid conflicts
BeadSchema as CliBeadSchema, BeadIdSchema, BeadTypeSchema as CliBeadTypeSchema, BdArgumentSchema, } from './bd-bridge.js';
// Sync Bridge
export { SyncBridge, createSyncBridge, SyncBridgeError, 
// Schemas - renamed to avoid conflicts
ConflictStrategySchema, SyncDirectionSchema as CliSyncDirectionSchema, SyncStatusSchema, AgentDBEntrySchema, } from './sync-bridge.js';
//# sourceMappingURL=index.js.map