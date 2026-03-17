/**
 * Learning Bridge for Test Intelligence
 *
 * Provides RL-based test selection and prioritization using
 * ruvector-learning-wasm for Q-Learning, PPO, and Decision Transformer.
 */
import type { LearningBridgeInterface, LearningConfig, TestHistoryEntry, CodeChange, PredictedTest, TestFeedback } from '../types.js';
/**
 * Learning Bridge Implementation for Test Intelligence
 *
 * Uses reinforcement learning to optimize test selection based on:
 * - Historical test execution patterns
 * - Code change characteristics
 * - Test failure correlations
 */
export declare class TestLearningBridge implements LearningBridgeInterface {
    readonly name = "test-intelligence-learning";
    readonly version = "0.1.0";
    private status;
    private config;
    private replayBuffer;
    private policyWeights;
    private testEmbeddings;
    private fileTestMapping;
    constructor(config?: Partial<LearningConfig>);
    init(): Promise<void>;
    destroy(): Promise<void>;
    isReady(): boolean;
    /**
     * Train on test execution history
     *
     * Uses temporal difference learning to update the test selection policy
     * based on historical outcomes.
     */
    trainOnHistory(history: TestHistoryEntry[], config?: LearningConfig): Promise<number>;
    /**
     * Predict which tests are likely to fail given code changes
     *
     * Uses the learned policy to rank tests by failure probability.
     */
    predictFailingTests(changes: CodeChange[], topK: number): Promise<PredictedTest[]>;
    /**
     * Update policy with feedback from actual test results
     */
    updatePolicyWithFeedback(feedback: TestFeedback): Promise<void>;
    private initializeMockWeights;
    private computeTestEmbedding;
    private computeChangeEmbedding;
    private combineEmbeddings;
    private computeQValues;
    private createExperiencesFromHistory;
    private computeTDError;
    private updatePolicyWeights;
    private batchUpdate;
    private computeReward;
    private computeHistoricalReward;
    private generateReason;
    private sigmoid;
    private hashString;
}
/**
 * Create a new learning bridge instance
 */
export declare function createTestLearningBridge(config?: Partial<LearningConfig>): TestLearningBridge;
//# sourceMappingURL=learning-bridge.d.ts.map