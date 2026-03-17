/**
 * GUPP Module - Gastown Universal Propulsion Principle
 *
 * GUPP principle: "If work is on your hook, YOU MUST RUN IT"
 *
 * This module provides session persistence and work tracking
 * for the Gas Town Bridge plugin, ensuring work continuity
 * across session restarts and crashes.
 *
 * @module gastown-bridge/gupp
 * @version 0.1.0
 */
export { GuppAdapter, createGuppAdapter, default, type SessionManager, type GuppAdapterConfig, type ResumptionResult, type SessionStartCallback, type SessionEndCallback, type WorkSlungCallback, type WorkCompleteCallback, } from './adapter.js';
export { createEmptyState, createSession, createHookedWorkItem, saveState, loadState, deleteState, saveStateToAgentDB, loadStateFromAgentDB, mergeStates, validateState, getPendingWork, getWorkNeedingResumption, touchSession, endSession, DEFAULT_STATE_PATH, AGENTDB_NAMESPACE, GuppStateSchema, HookedWorkItemSchema, SessionInfoSchema, WorkItemStatusSchema, type GuppState, type HookedWorkItem, type SessionInfo, type WorkItemStatus, type MergeStrategy, type AgentDBInterface, } from './state.js';
//# sourceMappingURL=index.d.ts.map