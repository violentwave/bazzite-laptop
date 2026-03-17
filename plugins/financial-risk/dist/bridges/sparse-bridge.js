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
/**
 * Default logger
 */
const defaultLogger = {
    debug: (msg, meta) => console.debug(`[sparse-bridge] ${msg}`, meta),
    info: (msg, meta) => console.info(`[sparse-bridge] ${msg}`, meta),
    warn: (msg, meta) => console.warn(`[sparse-bridge] ${msg}`, meta),
    error: (msg, meta) => console.error(`[sparse-bridge] ${msg}`, meta),
};
/**
 * Anomaly detection using Isolation Forest-like approach
 */
export class AnomalyDetector {
    constructor(_numTrees = 100, _sampleSize = 256, _maxDepth = 8) {
        // Parameters reserved for future Isolation Forest implementation
    }
    /**
     * Calculate anomaly scores for transactions
     */
    calculateAnomalyScores(transactions) {
        const scores = new Map();
        const features = this.extractFeatures(transactions);
        for (let i = 0; i < transactions.length; i++) {
            const txn = transactions[i];
            const featureVector = features[i];
            const score = this.isolationScore(featureVector, features);
            scores.set(txn.id, score);
        }
        return scores;
    }
    /**
     * Detect anomalies above threshold
     */
    detectAnomalies(transactions, threshold = 0.8) {
        const scores = this.calculateAnomalyScores(transactions);
        const anomalies = [];
        for (const txn of transactions) {
            const score = scores.get(txn.id) ?? 0;
            if (score >= threshold) {
                anomalies.push({
                    transactionId: txn.id,
                    score,
                    severity: this.scoresToSeverity(score),
                    type: this.classifyAnomalyType(txn, score),
                    description: this.generateDescription(txn, score),
                    indicators: this.identifyIndicators(txn),
                    recommendedAction: this.recommendAction(score),
                });
            }
        }
        // Sort by score descending
        anomalies.sort((a, b) => b.score - a.score);
        return anomalies;
    }
    extractFeatures(transactions) {
        return transactions.map(txn => {
            const hour = new Date(txn.timestamp).getHours();
            const dayOfWeek = new Date(txn.timestamp).getDay();
            return [
                Math.log(Math.abs(txn.amount) + 1), // Log-scaled amount
                txn.amount < 0 ? 1 : 0, // Debit indicator
                txn.parties.length, // Number of parties
                hour / 24, // Normalized hour
                dayOfWeek / 7, // Normalized day of week
                txn.amount > 10000 ? 1 : 0, // Large transaction flag
                txn.amount > 100000 ? 1 : 0, // Very large transaction flag
            ];
        });
    }
    isolationScore(point, allPoints) {
        // Simplified isolation score based on distance from median
        const numFeatures = point.length;
        let totalDeviation = 0;
        for (let f = 0; f < numFeatures; f++) {
            const values = allPoints.map(p => p[f]).sort((a, b) => a - b);
            const median = values[Math.floor(values.length / 2)];
            const mad = this.medianAbsoluteDeviation(values, median);
            if (mad > 0) {
                totalDeviation += Math.abs(point[f] - median) / mad;
            }
        }
        // Normalize score to [0, 1]
        const normalizedScore = 1 - Math.exp(-totalDeviation / (numFeatures * 3));
        return Math.min(Math.max(normalizedScore, 0), 1);
    }
    medianAbsoluteDeviation(values, median) {
        const deviations = values.map(v => Math.abs(v - median));
        deviations.sort((a, b) => a - b);
        return deviations[Math.floor(deviations.length / 2)] ?? 1;
    }
    scoresToSeverity(score) {
        if (score >= 0.95)
            return 'critical';
        if (score >= 0.85)
            return 'high';
        if (score >= 0.7)
            return 'medium';
        return 'low';
    }
    classifyAnomalyType(txn, score) {
        if (Math.abs(txn.amount) > 100000)
            return 'large_transaction';
        if (txn.parties.length > 5)
            return 'multi_party';
        if (score > 0.9)
            return 'pattern_deviation';
        return 'unusual_activity';
    }
    generateDescription(txn, score) {
        const amount = Math.abs(txn.amount).toLocaleString('en-US', { style: 'currency', currency: 'USD' });
        return `Transaction ${txn.id} with amount ${amount} has anomaly score ${(score * 100).toFixed(1)}%`;
    }
    identifyIndicators(txn) {
        const indicators = [];
        if (Math.abs(txn.amount) > 10000)
            indicators.push('large_amount');
        if (txn.parties.length > 3)
            indicators.push('multiple_parties');
        const hour = new Date(txn.timestamp).getHours();
        if (hour < 6 || hour > 22)
            indicators.push('unusual_time');
        const dayOfWeek = new Date(txn.timestamp).getDay();
        if (dayOfWeek === 0 || dayOfWeek === 6)
            indicators.push('weekend_transaction');
        return indicators;
    }
    recommendAction(score) {
        if (score >= 0.95)
            return 'Immediate escalation to compliance team required';
        if (score >= 0.85)
            return 'Flag for manual review within 24 hours';
        if (score >= 0.7)
            return 'Add to monitoring watchlist';
        return 'Continue standard monitoring';
    }
}
/**
 * Market regime classifier
 */
export class MarketRegimeClassifier {
    windowSize;
    constructor(windowSize = 20) {
        this.windowSize = windowSize;
    }
    /**
     * Classify current market regime
     */
    classify(prices, _volumes) {
        if (prices.length < this.windowSize) {
            return { regime: 'sideways', confidence: 0.5 };
        }
        const returns = this.calculateReturns(prices);
        const volatility = this.calculateVolatility(returns);
        const trend = this.calculateTrend(prices);
        const momentum = this.calculateMomentum(returns);
        // Regime classification logic
        const regime = this.determineRegime(trend, volatility, momentum);
        const confidence = this.calculateConfidence(trend, volatility, momentum);
        return { regime, confidence };
    }
    /**
     * Get regime probabilities
     */
    getRegimeProbabilities(prices) {
        const { regime, confidence } = this.classify(prices);
        // Distribute probability based on confidence
        const probs = {
            bull: 0.1,
            bear: 0.1,
            sideways: 0.3,
            high_vol: 0.2,
            crisis: 0.1,
            recovery: 0.2,
        };
        // Increase probability for detected regime
        const totalOther = 1 - confidence;
        for (const r of Object.keys(probs)) {
            if (r === regime) {
                probs[r] = confidence;
            }
            else {
                probs[r] = (totalOther * probs[r]) / (1 - probs[regime]);
            }
        }
        return probs;
    }
    calculateReturns(prices) {
        const returns = [];
        for (let i = 1; i < prices.length; i++) {
            returns.push((prices[i] - prices[i - 1]) / prices[i - 1]);
        }
        return returns;
    }
    calculateVolatility(returns) {
        if (returns.length < 2)
            return 0;
        const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
        const variance = returns.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) / (returns.length - 1);
        return Math.sqrt(variance) * Math.sqrt(252); // Annualized
    }
    calculateTrend(prices) {
        if (prices.length < 2)
            return 0;
        // Simple linear regression slope
        const n = prices.length;
        let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
        for (let i = 0; i < n; i++) {
            sumX += i;
            sumY += prices[i];
            sumXY += i * prices[i];
            sumX2 += i * i;
        }
        const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
        const avgPrice = sumY / n;
        return slope / avgPrice * 252; // Annualized trend
    }
    calculateMomentum(returns) {
        if (returns.length < this.windowSize)
            return 0;
        // Recent momentum vs historical
        const recent = returns.slice(-Math.floor(this.windowSize / 2));
        const historical = returns.slice(-this.windowSize, -Math.floor(this.windowSize / 2));
        const recentMean = recent.reduce((a, b) => a + b, 0) / recent.length;
        const historicalMean = historical.reduce((a, b) => a + b, 0) / historical.length;
        return recentMean - historicalMean;
    }
    determineRegime(trend, volatility, momentum) {
        // High volatility regimes
        if (volatility > 0.4) {
            if (trend < -0.3)
                return 'crisis';
            return 'high_vol';
        }
        // Trend-based regimes
        if (trend > 0.15) {
            return momentum > 0 ? 'bull' : 'recovery';
        }
        if (trend < -0.15) {
            return 'bear';
        }
        return 'sideways';
    }
    calculateConfidence(trend, volatility, momentum) {
        // Higher confidence for extreme values
        const trendStrength = Math.min(Math.abs(trend) / 0.3, 1);
        const volStrength = Math.min(volatility / 0.4, 1);
        const momStrength = Math.min(Math.abs(momentum) / 0.01, 1);
        return 0.4 + 0.6 * Math.max(trendStrength, volStrength, momStrength);
    }
}
/**
 * Financial Sparse Bridge implementation
 */
export class FinancialSparseBridge {
    wasmModule = null;
    modelPtr = 0;
    config;
    logger;
    anomalyDetector;
    regimeClassifier;
    initialized = false;
    constructor(config, logger) {
        this.config = {
            sparsityThreshold: config?.sparsityThreshold ?? 0.9,
            maxFeatures: config?.maxFeatures ?? 1000,
            compressionLevel: config?.compressionLevel ?? 3,
        };
        this.logger = logger ?? defaultLogger;
        this.anomalyDetector = new AnomalyDetector();
        this.regimeClassifier = new MarketRegimeClassifier();
    }
    /**
     * Initialize the sparse bridge
     */
    async initialize(config) {
        if (config) {
            this.config = { ...this.config, ...config };
        }
        try {
            const wasmPath = await this.resolveWasmPath();
            if (wasmPath) {
                this.wasmModule = await this.loadWasmModule(wasmPath);
                this.modelPtr = this.wasmModule.create_sparse_model(this.config.maxFeatures ?? 1000, 256, // Hidden dimension
                this.config.sparsityThreshold ?? 0.9);
                this.logger.info('Sparse WASM module initialized', {
                    maxFeatures: this.config.maxFeatures,
                    sparsityThreshold: this.config.sparsityThreshold,
                });
            }
            else {
                this.logger.warn('WASM module not available, using JavaScript fallback');
            }
            this.initialized = true;
        }
        catch (error) {
            this.logger.warn('Failed to initialize WASM, using fallback', {
                error: error instanceof Error ? error.message : String(error),
            });
            this.initialized = true;
        }
    }
    /**
     * Perform sparse inference on features
     */
    async sparseInference(features, indices) {
        if (!this.initialized) {
            throw new Error('Sparse bridge not initialized');
        }
        if (this.wasmModule && this.modelPtr) {
            return this.wasmModule.sparse_forward(this.modelPtr, features, indices);
        }
        // Fallback: Simple linear projection
        const output = new Float32Array(128);
        for (let i = 0; i < indices.length && i < output.length; i++) {
            const idx = indices[i];
            if (idx < features.length) {
                output[i] = features[idx] * 0.1; // Simple scaling
            }
        }
        return output;
    }
    /**
     * Detect anomalies in transactions
     */
    async detectAnomalies(transactions, threshold) {
        if (!this.initialized) {
            throw new Error('Sparse bridge not initialized');
        }
        if (this.wasmModule && this.modelPtr) {
            const numSamples = transactions.length;
            const featureDim = transactions[0]?.length ?? 0;
            if (numSamples === 0 || featureDim === 0) {
                return new Uint32Array(0);
            }
            // Flatten transactions
            const flatData = new Float32Array(numSamples * featureDim);
            for (let i = 0; i < numSamples; i++) {
                flatData.set(transactions[i], i * featureDim);
            }
            return this.wasmModule.detect_anomalies(this.modelPtr, flatData, numSamples, featureDim, threshold);
        }
        // Fallback: Use JavaScript anomaly detector
        // Convert Float32Array[] to FinancialTransaction[] for the detector
        // This is a simplified fallback - in production, pass actual transactions
        const anomalyIndices = [];
        for (let i = 0; i < transactions.length; i++) {
            const txn = transactions[i];
            // Simple anomaly heuristic based on feature magnitudes
            const magnitude = Math.sqrt(txn.reduce((sum, v) => sum + v * v, 0));
            if (magnitude > threshold * 10) {
                anomalyIndices.push(i);
            }
        }
        return new Uint32Array(anomalyIndices);
    }
    /**
     * Classify market regime from market data
     */
    async classifyRegime(marketData) {
        if (!this.initialized) {
            throw new Error('Sparse bridge not initialized');
        }
        if (this.wasmModule && this.modelPtr) {
            const regimeCode = this.wasmModule.classify_regime(this.modelPtr, marketData, 20 // Window size
            );
            return {
                regime: regimeCode,
                confidence: 0.8, // WASM returns confidence separately in full implementation
            };
        }
        // Fallback: Use JavaScript classifier
        const prices = Array.from(marketData);
        const result = this.regimeClassifier.classify(prices);
        return {
            regime: this.regimeToCode(result.regime),
            confidence: result.confidence,
        };
    }
    /**
     * Detect anomalies in financial transactions
     */
    async detectTransactionAnomalies(transactions, threshold = 0.8) {
        return this.anomalyDetector.detectAnomalies(transactions, threshold);
    }
    /**
     * Classify market regime from price data
     */
    async classifyMarketRegime(prices, volumes) {
        const { regime, confidence } = this.regimeClassifier.classify(prices, volumes);
        const probabilities = this.regimeClassifier.getRegimeProbabilities(prices);
        return { regime, confidence, probabilities };
    }
    /**
     * Cleanup resources
     */
    destroy() {
        if (this.wasmModule && this.modelPtr) {
            this.wasmModule.free_model(this.modelPtr);
        }
        this.initialized = false;
    }
    // Private methods
    async resolveWasmPath() {
        try {
            const module = await import(/* webpackIgnore: true */ 'ruvector-sparse-inference-wasm');
            return module.default ?? null;
        }
        catch {
            return null;
        }
    }
    async loadWasmModule(wasmPath) {
        const module = await import(wasmPath);
        await module.default();
        return module;
    }
    regimeToCode(regime) {
        const codes = {
            bull: 0,
            bear: 1,
            sideways: 2,
            high_vol: 3,
            crisis: 4,
            recovery: 5,
        };
        return codes[regime] ?? 2;
    }
}
/**
 * Create a new sparse bridge instance
 */
export function createSparseBridge(config, logger) {
    return new FinancialSparseBridge(config, logger);
}
export default FinancialSparseBridge;
//# sourceMappingURL=sparse-bridge.js.map