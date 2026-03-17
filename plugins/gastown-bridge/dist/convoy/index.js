/**
 * Convoy Module Exports
 *
 * Provides convoy tracking and observation capabilities for the
 * Gas Town Bridge Plugin. Convoys are work-order groups that track
 * related beads (issues) through their lifecycle.
 *
 * @module gastown-bridge/convoy
 */
// Convoy Tracker
export { ConvoyTracker, createConvoyTracker, } from './tracker.js';
// Convoy Observer
export { ConvoyObserver, createConvoyObserver, 
// Lazy loading support (defers observer initialization until first watch)
createLazyConvoyObserver, getLazyObserverStats, } from './observer.js';
//# sourceMappingURL=index.js.map