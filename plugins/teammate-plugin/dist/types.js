/**
 * @claude-flow/teammate-plugin Types
 *
 * Complete type definitions for TeammateTool integration.
 * Requires Claude Code >= 2.1.19
 *
 * @module @claude-flow/teammate-plugin/types
 * @version 1.0.0-alpha.1
 */
// ============================================================================
// Version Requirements
// ============================================================================
export const MINIMUM_CLAUDE_CODE_VERSION = '2.1.19';
// Security limits
export const SECURITY_LIMITS = {
    MAX_NAME_LENGTH: 64,
    MAX_PAYLOAD_SIZE: 1024 * 1024, // 1MB
    MAX_TEAMMATES_PER_TEAM: 50,
    MAX_MESSAGES_PER_MAILBOX: 1000,
    MAX_PLANS_PER_TEAM: 100,
    MAX_DELEGATION_DEPTH: 5,
};
// Rate limiting defaults
export const RATE_LIMIT_DEFAULTS = {
    SPAWN_PER_MINUTE: 10,
    MESSAGES_PER_MINUTE: 100,
    BROADCASTS_PER_MINUTE: 20,
    PLANS_PER_MINUTE: 5,
    API_CALLS_PER_MINUTE: 200,
};
// Retry configuration
export const RETRY_DEFAULTS = {
    MAX_RETRIES: 3,
    INITIAL_DELAY_MS: 100,
    MAX_DELAY_MS: 5000,
    BACKOFF_MULTIPLIER: 2,
};
// Health check configuration
export const HEALTH_CHECK_DEFAULTS = {
    INTERVAL_MS: 30000, // 30 seconds
    TIMEOUT_MS: 5000, // 5 seconds
    UNHEALTHY_THRESHOLD: 3,
    HEALTHY_THRESHOLD: 2,
};
// MCP tool parameter limits
export const MCP_PARAM_LIMITS = {
    MAX_PARAM_LENGTH: 10000,
    MAX_ARRAY_ITEMS: 100,
};
// ============================================================================
// Error Handling
// ============================================================================
export var TeammateErrorCode;
(function (TeammateErrorCode) {
    TeammateErrorCode["VERSION_INCOMPATIBLE"] = "VERSION_INCOMPATIBLE";
    TeammateErrorCode["TEAM_NOT_FOUND"] = "TEAM_NOT_FOUND";
    TeammateErrorCode["TEAMMATE_NOT_FOUND"] = "TEAMMATE_NOT_FOUND";
    TeammateErrorCode["ALREADY_IN_TEAM"] = "ALREADY_IN_TEAM";
    TeammateErrorCode["NO_TEAM_CONTEXT"] = "NO_TEAM_CONTEXT";
    TeammateErrorCode["PLAN_NOT_FOUND"] = "PLAN_NOT_FOUND";
    TeammateErrorCode["PLAN_NOT_APPROVED"] = "PLAN_NOT_APPROVED";
    TeammateErrorCode["PLAN_ALREADY_EXECUTING"] = "PLAN_ALREADY_EXECUTING";
    TeammateErrorCode["DELEGATION_DENIED"] = "DELEGATION_DENIED";
    TeammateErrorCode["DELEGATION_DEPTH_EXCEEDED"] = "DELEGATION_DEPTH_EXCEEDED";
    TeammateErrorCode["REMOTE_SYNC_FAILED"] = "REMOTE_SYNC_FAILED";
    TeammateErrorCode["TELEPORT_FAILED"] = "TELEPORT_FAILED";
    TeammateErrorCode["MAILBOX_FULL"] = "MAILBOX_FULL";
    TeammateErrorCode["PERMISSION_DENIED"] = "PERMISSION_DENIED";
    TeammateErrorCode["TIMEOUT"] = "TIMEOUT";
    TeammateErrorCode["BACKEND_UNAVAILABLE"] = "BACKEND_UNAVAILABLE";
    TeammateErrorCode["MEMORY_SAVE_FAILED"] = "MEMORY_SAVE_FAILED";
    TeammateErrorCode["MEMORY_LOAD_FAILED"] = "MEMORY_LOAD_FAILED";
})(TeammateErrorCode || (TeammateErrorCode = {}));
export const DEFAULT_PLUGIN_CONFIG = {
    autoInitialize: true,
    fallbackToMCP: true,
    recovery: {
        maxRetries: 3,
        retryDelayMs: 1000,
        exponentialBackoff: true,
        fallbackToMCP: true,
        autoCleanupOnError: true,
    },
    delegation: {
        maxDepth: 3,
        autoExpireMs: 3600000, // 1 hour
        requireApproval: false,
    },
    remoteSync: {
        enabled: false,
        autoSync: false,
        syncInterval: 30000, // 30 seconds
        preserveOnDisconnect: true,
    },
    teleport: {
        autoResume: true,
        gitAware: true,
        preserveMailbox: true,
        preserveMemory: true,
    },
    memory: {
        autoPersist: true,
        persistIntervalMs: 60000, // 1 minute
        maxSizeMb: 100,
    },
    mailbox: {
        pollingIntervalMs: 1000,
        maxMessages: 1000,
        retentionMs: 3600000, // 1 hour
    },
};
export const DEFAULT_RATE_LIMIT_CONFIG = {
    spawnPerMinute: RATE_LIMIT_DEFAULTS.SPAWN_PER_MINUTE,
    messagesPerMinute: RATE_LIMIT_DEFAULTS.MESSAGES_PER_MINUTE,
    broadcastsPerMinute: RATE_LIMIT_DEFAULTS.BROADCASTS_PER_MINUTE,
    plansPerMinute: RATE_LIMIT_DEFAULTS.PLANS_PER_MINUTE,
    apiCallsPerMinute: RATE_LIMIT_DEFAULTS.API_CALLS_PER_MINUTE,
};
export const DEFAULT_HEALTH_CHECK_CONFIG = {
    enabled: true,
    intervalMs: HEALTH_CHECK_DEFAULTS.INTERVAL_MS,
    timeoutMs: HEALTH_CHECK_DEFAULTS.TIMEOUT_MS,
    unhealthyThreshold: HEALTH_CHECK_DEFAULTS.UNHEALTHY_THRESHOLD,
    healthyThreshold: HEALTH_CHECK_DEFAULTS.HEALTHY_THRESHOLD,
    autoRemoveUnhealthy: false,
};
export const DEFAULT_RETRY_CONFIG = {
    maxRetries: RETRY_DEFAULTS.MAX_RETRIES,
    initialDelayMs: RETRY_DEFAULTS.INITIAL_DELAY_MS,
    maxDelayMs: RETRY_DEFAULTS.MAX_DELAY_MS,
    backoffMultiplier: RETRY_DEFAULTS.BACKOFF_MULTIPLIER,
    retryableErrors: [
        TeammateErrorCode.TIMEOUT,
        TeammateErrorCode.BACKEND_UNAVAILABLE,
        TeammateErrorCode.REMOTE_SYNC_FAILED,
        TeammateErrorCode.MEMORY_SAVE_FAILED,
    ],
};
export const DEFAULT_CIRCUIT_BREAKER_CONFIG = {
    enabled: true,
    failureThreshold: 5,
    successThreshold: 2,
    timeoutMs: 10000,
    resetTimeMs: 30000,
};
//# sourceMappingURL=types.js.map