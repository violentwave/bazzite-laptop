/**
 * Convoy Module Exports
 *
 * Provides convoy tracking and observation capabilities for the
 * Gas Town Bridge Plugin. Convoys are work-order groups that track
 * related beads (issues) through their lifecycle.
 *
 * @module gastown-bridge/convoy
 */
export { ConvoyTracker, createConvoyTracker, type ConvoyEventType, type ConvoyEvent, type ConvoyTrackerConfig, type ConvoyLogger, } from './tracker.js';
export { ConvoyObserver, createConvoyObserver, createLazyConvoyObserver, getLazyObserverStats, type WasmGraphModule, type CompletionCallback, type WatchHandle, type ConvoyObserverConfig, type BlockerInfo, type ReadyIssueInfo, type CompletionCheckResult, type ObserverLogger, } from './observer.js';
//# sourceMappingURL=index.d.ts.map