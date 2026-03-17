/**
 * Sparse Bridge - Financial Risk Plugin
 *
 * Provides sparse inference capabilities for efficient processing
 * of high-dimensional financial data. Integrates with
 * ruvector-sparse-inference-wasm for anomaly detection and
 * market regime classification.
 *
 * Features:
 * - Efficient sparse feature processing
 * - Transaction anomaly detection
 * - Market regime classification
 * - Real-time fraud detection
 */
import type { SparseBridge, SparseConfig, FinancialTransaction, DetectedAnomaly, MarketRegimeType, Logger } from '../types.js';
/**
 * Anomaly detection using Isolation Forest-like approach
 */
export declare class AnomalyDetector {
    constructor(_numTrees?: number, _sampleSize?: number, _maxDepth?: number);
    /**
     * Calculate anomaly scores for transactions
     */
    calculateAnomalyScores(transactions: FinancialTransaction[]): Map<string, number>;
    /**
     * Detect anomalies above threshold
     */
    detectAnomalies(transactions: FinancialTransaction[], threshold?: number): DetectedAnomaly[];
    private extractFeatures;
    private isolationScore;
    private medianAbsoluteDeviation;
    private scoresToSeverity;
    private classifyAnomalyType;
    private generateDescription;
    private identifyIndicators;
    private recommendAction;
}
/**
 * Market regime classifier
 */
export declare class MarketRegimeClassifier {
    private readonly windowSize;
    constructor(windowSize?: number);
    /**
     * Classify current market regime
     */
    classify(prices: number[], _volumes?: number[]): {
        regime: MarketRegimeType;
        confidence: number;
    };
    /**
     * Get regime probabilities
     */
    getRegimeProbabilities(prices: number[]): Record<MarketRegimeType, number>;
    private calculateReturns;
    private calculateVolatility;
    private calculateTrend;
    private calculateMomentum;
    private determineRegime;
    private calculateConfidence;
}
/**
 * Financial Sparse Bridge implementation
 */
export declare class FinancialSparseBridge implements SparseBridge {
    private wasmModule;
    private modelPtr;
    private config;
    private logger;
    private anomalyDetector;
    private regimeClassifier;
    initialized: boolean;
    constructor(config?: Partial<SparseConfig>, logger?: Logger);
    /**
     * Initialize the sparse bridge
     */
    initialize(config?: SparseConfig): Promise<void>;
    /**
     * Perform sparse inference on features
     */
    sparseInference(features: Float32Array, indices: Uint32Array): Promise<Float32Array>;
    /**
     * Detect anomalies in transactions
     */
    detectAnomalies(transactions: Float32Array[], threshold: number): Promise<Uint32Array>;
    /**
     * Classify market regime from market data
     */
    classifyRegime(marketData: Float32Array): Promise<{
        regime: number;
        confidence: number;
    }>;
    /**
     * Detect anomalies in financial transactions
     */
    detectTransactionAnomalies(transactions: FinancialTransaction[], threshold?: number): Promise<DetectedAnomaly[]>;
    /**
     * Classify market regime from price data
     */
    classifyMarketRegime(prices: number[], volumes?: number[]): Promise<{
        regime: MarketRegimeType;
        confidence: number;
        probabilities: Record<MarketRegimeType, number>;
    }>;
    /**
     * Cleanup resources
     */
    destroy(): void;
    private resolveWasmPath;
    private loadWasmModule;
    private regimeToCode;
}
/**
 * Create a new sparse bridge instance
 */
export declare function createSparseBridge(config?: Partial<SparseConfig>, logger?: Logger): FinancialSparseBridge;
export default FinancialSparseBridge;
//# sourceMappingURL=sparse-bridge.d.ts.map