/**
 * Reinforcement Learning Bridge
 *
 * Bridge to ruvector-learning-wasm for RL algorithms including
 * Q-Learning, SARSA, Actor-Critic, PPO, DQN, and Decision Transformer.
 */
import type { WasmBridge, WasmModuleStatus, LearningConfig } from '../types.js';
/**
 * Learning experience tuple
 */
export interface Experience {
    state: Float32Array;
    action: number;
    reward: number;
    nextState: Float32Array;
    done: boolean;
}
/**
 * Learning trajectory
 */
export interface Trajectory {
    experiences: Experience[];
    totalReward: number;
    metadata?: Record<string, unknown>;
}
/**
 * Learning WASM module interface
 */
interface LearningModule {
    train(trajectories: Trajectory[], config: LearningConfig): number;
    predict(state: Float32Array): {
        action: number;
        qValues: Float32Array;
    };
    evaluate(state: Float32Array): number;
    getPolicy(): Float32Array;
    setPolicy(weights: Float32Array): void;
    addExperience(experience: Experience): void;
    sampleBatch(batchSize: number): Experience[];
    sequencePredict(states: Float32Array[], actions: number[], rewards: number[], targetReturn: number): number;
}
/**
 * Reinforcement Learning Bridge implementation
 */
export declare class LearningBridge implements WasmBridge<LearningModule> {
    readonly name = "ruvector-learning-wasm";
    readonly version = "0.1.0";
    private _status;
    private _module;
    private config;
    constructor(config?: Partial<LearningConfig>);
    get status(): WasmModuleStatus;
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    getModule(): LearningModule | null;
    /**
     * Train on trajectories
     */
    train(trajectories: Trajectory[], config?: Partial<LearningConfig>): number;
    /**
     * Predict action for state
     */
    predict(state: Float32Array): {
        action: number;
        qValues: Float32Array;
    };
    /**
     * Evaluate state value
     */
    evaluate(state: Float32Array): number;
    /**
     * Add experience to replay buffer
     */
    addExperience(experience: Experience): void;
    /**
     * Decision Transformer sequence prediction
     */
    sequencePredict(states: Float32Array[], actions: number[], rewards: number[], targetReturn: number): number;
    /**
     * Create mock module for development
     */
    private createMockModule;
}
/**
 * Create a new learning bridge
 */
export declare function createLearningBridge(config?: Partial<LearningConfig>): LearningBridge;
export {};
//# sourceMappingURL=learning.d.ts.map