/**
 * Reinforcement Learning Bridge
 *
 * Bridge to ruvector-learning-wasm for RL algorithms including
 * Q-Learning, SARSA, Actor-Critic, PPO, DQN, and Decision Transformer.
 */
import { LearningConfigSchema } from '../types.js';
/**
 * Reinforcement Learning Bridge implementation
 */
export class LearningBridge {
    name = 'ruvector-learning-wasm';
    version = '0.1.0';
    _status = 'unloaded';
    _module = null;
    config;
    constructor(config) {
        this.config = LearningConfigSchema.parse(config ?? {});
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
            const wasmModule = await import('@ruvector/learning-wasm').catch(() => null);
            if (wasmModule) {
                this._module = wasmModule;
            }
            else {
                this._module = this.createMockModule();
            }
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
     * Train on trajectories
     */
    train(trajectories, config) {
        if (!this._module)
            throw new Error('Learning module not initialized');
        const mergedConfig = { ...this.config, ...config };
        return this._module.train(trajectories, mergedConfig);
    }
    /**
     * Predict action for state
     */
    predict(state) {
        if (!this._module)
            throw new Error('Learning module not initialized');
        return this._module.predict(state);
    }
    /**
     * Evaluate state value
     */
    evaluate(state) {
        if (!this._module)
            throw new Error('Learning module not initialized');
        return this._module.evaluate(state);
    }
    /**
     * Add experience to replay buffer
     */
    addExperience(experience) {
        if (!this._module)
            throw new Error('Learning module not initialized');
        this._module.addExperience(experience);
    }
    /**
     * Decision Transformer sequence prediction
     */
    sequencePredict(states, actions, rewards, targetReturn) {
        if (!this._module)
            throw new Error('Learning module not initialized');
        return this._module.sequencePredict(states, actions, rewards, targetReturn);
    }
    /**
     * Create mock module for development
     */
    createMockModule() {
        const replayBuffer = [];
        let policyWeights = new Float32Array(100);
        return {
            train(trajectories, config) {
                let totalLoss = 0;
                for (const trajectory of trajectories) {
                    for (const exp of trajectory.experiences) {
                        // Simple TD update approximation
                        const tdError = exp.reward + config.gamma * 0.5 - 0.3;
                        totalLoss += Math.abs(tdError);
                    }
                }
                return totalLoss / Math.max(1, trajectories.length);
            },
            predict(state) {
                const numActions = 4;
                const qValues = new Float32Array(numActions);
                for (let i = 0; i < numActions; i++) {
                    qValues[i] = state.reduce((s, v, j) => s + v * policyWeights[(i * 10 + j) % 100], 0);
                }
                let maxIdx = 0;
                for (let i = 1; i < numActions; i++) {
                    if (qValues[i] > qValues[maxIdx])
                        maxIdx = i;
                }
                return { action: maxIdx, qValues };
            },
            evaluate(state) {
                return state.reduce((s, v) => s + v, 0) / state.length;
            },
            getPolicy() {
                return new Float32Array(policyWeights);
            },
            setPolicy(weights) {
                policyWeights = new Float32Array(weights);
            },
            addExperience(experience) {
                replayBuffer.push(experience);
                if (replayBuffer.length > 10000) {
                    replayBuffer.shift();
                }
            },
            sampleBatch(batchSize) {
                const batch = [];
                for (let i = 0; i < Math.min(batchSize, replayBuffer.length); i++) {
                    const idx = Math.floor(Math.random() * replayBuffer.length);
                    batch.push(replayBuffer[idx]);
                }
                return batch;
            },
            sequencePredict(states, actions, rewards, targetReturn) {
                // Decision Transformer: predict next action based on sequence and target return
                const avgReward = rewards.reduce((s, r) => s + r, 0) / rewards.length;
                const returnDiff = targetReturn - avgReward;
                return returnDiff > 0 ? 1 : 0; // Simplified
            },
        };
    }
}
/**
 * Create a new learning bridge
 */
export function createLearningBridge(config) {
    return new LearningBridge(config);
}
//# sourceMappingURL=learning.js.map