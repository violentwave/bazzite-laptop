/**
 * Metrics Collector for TeammateTool operations
 *
 * Collects and aggregates metrics for monitoring and
 * observability of teammate bridge operations.
 *
 * @module @claude-flow/teammate-plugin/utils/metrics-collector
 */
import type { BridgeMetrics, MetricSnapshot } from '../types.js';
/**
 * Metrics collector with counters, gauges, and histograms
 */
export declare class MetricsCollector {
    private metrics;
    private readonly maxHistogramSize;
    constructor();
    private createEmptyMetrics;
    /**
     * Increment a counter metric
     */
    increment(metric: keyof BridgeMetrics, amount?: number): void;
    /**
     * Decrement a counter metric
     */
    decrement(metric: keyof BridgeMetrics, amount?: number): void;
    /**
     * Set a gauge metric to a specific value
     */
    set(metric: keyof BridgeMetrics, value: number): void;
    /**
     * Record a latency measurement
     */
    recordLatency(metric: 'spawnLatency' | 'messageLatency' | 'planApprovalLatency', ms: number): void;
    /**
     * Get a snapshot of current metrics
     */
    getSnapshot(): MetricSnapshot;
    /**
     * Calculate percentile for latency metrics
     */
    getPercentile(metric: 'spawnLatency' | 'messageLatency' | 'planApprovalLatency', percentile: number): number;
    /**
     * Get average latency for a metric
     */
    getAverageLatency(metric: 'spawnLatency' | 'messageLatency' | 'planApprovalLatency'): number;
    /**
     * Reset all metrics
     */
    reset(): void;
    /**
     * Get raw metrics object (for testing)
     */
    getRawMetrics(): BridgeMetrics;
}
//# sourceMappingURL=metrics-collector.d.ts.map