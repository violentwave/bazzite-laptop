/**
 * SONA Bridge
 *
 * Bridge to SONA (Self-Optimizing Neural Architecture) for continuous
 * learning with LoRA fine-tuning and EWC++ memory preservation.
 */
import { SonaConfigSchema } from '../types.js';
/**
 * SONA Bridge implementation
 */
export class SonaBridge {
    name = 'sona';
    version = '0.1.0';
    _status = 'unloaded';
    _module = null;
    config;
    constructor(config) {
        this.config = SonaConfigSchema.parse(config ?? {});
    }
    get status() {
        return this._status;
    }
    async init() {
        if (this._status === 'ready')
            return;
        if (this._status === 'loading')
            return;
        this._status = 'loading';
        try {
            const wasmModule = await import('@ruvector/sona').catch(() => null);
            if (wasmModule) {
                this._module = wasmModule;
            }
            else {
                this._module = this.createMockModule();
            }
            this._module.setMode(this.config.mode);
            this._status = 'ready';
        }
        catch (error) {
            this._status = 'error';
            throw error;
        }
    }
    async destroy() {
        this._module = null;
        this._status = 'unloaded';
    }
    isReady() {
        return this._status === 'ready';
    }
    getModule() {
        return this._module;
    }
    /**
     * Learn from trajectories
     */
    learn(trajectories, config) {
        if (!this._module)
            throw new Error('SONA module not initialized');
        const mergedConfig = { ...this.config, ...config };
        return this._module.learn(trajectories, mergedConfig);
    }
    /**
     * Predict next action
     */
    predict(state) {
        if (!this._module)
            throw new Error('SONA module not initialized');
        return this._module.predict(state);
    }
    /**
     * Store a pattern
     */
    storePattern(pattern) {
        if (!this._module)
            throw new Error('SONA module not initialized');
        this._module.storePattern(pattern);
    }
    /**
     * Find similar patterns
     */
    findPatterns(query, k) {
        if (!this._module)
            throw new Error('SONA module not initialized');
        return this._module.findPatterns(query, k);
    }
    /**
     * Apply LoRA transformation
     */
    applyLoRA(input, weights) {
        if (!this._module)
            throw new Error('SONA module not initialized');
        return this._module.applyLoRA(input, weights);
    }
    /**
     * Consolidate memory with EWC
     */
    consolidate(ewcState) {
        if (!this._module)
            throw new Error('SONA module not initialized');
        this._module.consolidate(ewcState);
    }
    /**
     * Set operating mode
     */
    setMode(mode) {
        if (!this._module)
            throw new Error('SONA module not initialized');
        this._module.setMode(mode);
        this.config.mode = mode;
    }
    /**
     * Get current mode
     */
    getMode() {
        return this._module?.getMode() ?? this.config.mode;
    }
    /**
     * Create mock module for development
     */
    createMockModule() {
        const patterns = new Map();
        let currentMode = 'balanced';
        let loraWeights = {
            A: new Map(),
            B: new Map(),
            rank: 4,
            alpha: 0.1,
        };
        return {
            learn(trajectories, config) {
                if (trajectories.length === 0)
                    return 0;
                const goodTrajectories = trajectories.filter(t => t.qualityScore >= 0.5);
                if (goodTrajectories.length === 0)
                    return 0;
                // Extract patterns from good trajectories
                for (const trajectory of goodTrajectories) {
                    if (trajectory.steps.length > 0) {
                        const lastStep = trajectory.steps[trajectory.steps.length - 1];
                        const patternId = `pattern_${patterns.size}`;
                        patterns.set(patternId, {
                            id: patternId,
                            embedding: new Float32Array(lastStep.stateAfter),
                            successRate: trajectory.qualityScore,
                            usageCount: 1,
                            domain: trajectory.domain,
                        });
                    }
                }
                const avgQuality = goodTrajectories.reduce((s, t) => s + t.qualityScore, 0) / goodTrajectories.length;
                return Math.max(0, avgQuality - 0.5);
            },
            predict(state) {
                // Find most similar pattern
                let bestPattern = null;
                let bestSim = -1;
                for (const pattern of patterns.values()) {
                    const sim = cosineSimilarity(state, pattern.embedding);
                    if (sim > bestSim) {
                        bestSim = sim;
                        bestPattern = pattern;
                    }
                }
                if (bestPattern && bestSim > 0.5) {
                    return {
                        action: bestPattern.domain,
                        confidence: bestSim * bestPattern.successRate,
                    };
                }
                return { action: 'explore', confidence: 0.3 };
            },
            storePattern(pattern) {
                patterns.set(pattern.id, pattern);
            },
            findPatterns(query, k) {
                const results = [];
                for (const pattern of patterns.values()) {
                    const sim = cosineSimilarity(query, pattern.embedding);
                    results.push({ pattern, sim });
                }
                results.sort((a, b) => b.sim - a.sim);
                return results.slice(0, k).map(r => r.pattern);
            },
            updatePatternSuccess(patternId, success) {
                const pattern = patterns.get(patternId);
                if (pattern) {
                    pattern.usageCount++;
                    const alpha = 1 / pattern.usageCount;
                    pattern.successRate = pattern.successRate * (1 - alpha) + (success ? 1 : 0) * alpha;
                }
            },
            applyLoRA(input, weights) {
                const output = new Float32Array(input.length);
                output.set(input);
                // Apply LoRA: output = input + alpha * B @ A @ input
                for (const [module, A] of weights.A) {
                    const B = weights.B.get(module);
                    if (!B)
                        continue;
                    // Simplified LoRA application
                    let intermediate = 0;
                    for (let i = 0; i < Math.min(input.length, A.length); i++) {
                        intermediate += A[i] * input[i];
                    }
                    for (let i = 0; i < Math.min(output.length, B.length); i++) {
                        output[i] += weights.alpha * B[i] * intermediate;
                    }
                }
                return output;
            },
            updateLoRA(gradients, config) {
                // Update LoRA weights based on gradients
                const dim = gradients.length;
                const rank = config.loraRank;
                const A = new Float32Array(rank * dim);
                const B = new Float32Array(dim * rank);
                // Initialize with small random values scaled by gradients
                for (let i = 0; i < A.length; i++) {
                    A[i] = (Math.random() - 0.5) * 0.01 * (gradients[i % dim] || 1);
                }
                for (let i = 0; i < B.length; i++) {
                    B[i] = (Math.random() - 0.5) * 0.01 * (gradients[i % dim] || 1);
                }
                loraWeights.A.set('default', A);
                loraWeights.B.set('default', B);
                loraWeights.rank = rank;
                return loraWeights;
            },
            computeFisher(trajectories) {
                const fisher = new Map();
                for (const trajectory of trajectories) {
                    for (const step of trajectory.steps) {
                        const key = trajectory.domain;
                        let f = fisher.get(key);
                        if (!f) {
                            f = new Float32Array(step.stateAfter.length);
                            fisher.set(key, f);
                        }
                        // Approximate Fisher information
                        for (let i = 0; i < step.stateAfter.length; i++) {
                            const grad = step.stateAfter[i] * step.reward;
                            f[i] += grad * grad;
                        }
                    }
                }
                // Normalize
                for (const f of fisher.values()) {
                    const sum = f.reduce((s, v) => s + v, 0);
                    if (sum > 0) {
                        for (let i = 0; i < f.length; i++) {
                            f[i] /= sum;
                        }
                    }
                }
                return fisher;
            },
            consolidate(ewcState) {
                // Apply EWC penalty to prevent catastrophic forgetting
                // This modifies the learning in future updates
            },
            setMode(mode) {
                currentMode = mode;
            },
            getMode() {
                return currentMode;
            },
        };
    }
}
/**
 * Cosine similarity helper
 */
function cosineSimilarity(a, b) {
    if (a.length !== b.length)
        return 0;
    let dot = 0;
    let normA = 0;
    let normB = 0;
    for (let i = 0; i < a.length; i++) {
        dot += a[i] * b[i];
        normA += a[i] * a[i];
        normB += b[i] * b[i];
    }
    const denom = Math.sqrt(normA) * Math.sqrt(normB);
    return denom > 0 ? dot / denom : 0;
}
/**
 * Create a new SONA bridge
 */
export function createSonaBridge(config) {
    return new SonaBridge(config);
}
//# sourceMappingURL=sona.js.map