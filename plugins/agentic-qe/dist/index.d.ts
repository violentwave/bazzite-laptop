/**
 * Agentic-QE Plugin Entry Point
 * Plugin exports for claude-flow V3 integration
 *
 * @module v3/plugins/agentic-qe
 * @version 3.2.3
 */
export { AQEPlugin } from './plugin.js';
import { AQEPlugin } from './plugin.js';
export declare const agenticQEPlugin: AQEPlugin;
export default agenticQEPlugin;
export type { TestType, TDDStyle, TestFramework, SecurityLevel, ModelTier, ContractType, ChaosFailureType, ComplianceStandard, SecurityScanType, Severity, QualityGateOperator, CoverageGapType, CoverageAlgorithm, BoundedContext, V3Domain, TestGenerationRequest, CoverageConfig, TestGenerationResult, GeneratedTestFile, TestGenerationStats, TestPattern, TDDCycleRequest, TDDCycleResult, TDDCycleStep, ImplementationArtifact, RefactoringSuggestion, CoverageAnalysisRequest, CoverageReport, CoverageMetrics, FileCoverage, BranchInfo, CoverageGap, CoverageTrend, QualityGate, QualityGateRequest, QualityGateResult, GateEvaluationResult, ReadinessAssessment, DefectPredictionRequest, DefectPredictionResult, DefectPrediction, DefectHotspot, RootCauseAnalysis, SecurityScanRequest, SecurityScanResult, SecurityFinding, ComplianceStatus, ComplianceCheck, SecuritySummary, ContractValidationRequest, ContractValidationResult, ContractError, ContractWarning, BreakingChange, ChaosInjectionRequest, ChaosInjectionResult, ChaosObservation, ResilienceAssessment, TestExecutionResult, TestResult, AQEPluginConfig, SandboxConfig, ModelRoutingConfig, QEPerformanceTargets, HNSWConfig, QEMemoryNamespace, SchemaField, QEWorkerType, QEWorkerDefinition, QEWorkerStatus, QEHookEvent, HookPriority, QEHookDefinition, QEAgentId, QEAgentStatus, QEAgentDefinition, ContextMapping, QEResult, QEError, } from './types.js';
export type { IQEMemoryBridge, LearningTrajectory, LearningStep, TestPattern as ITestPattern, PatternFilters, CoverageGap as ICoverageGap, QEMemoryStats, IQESecurityBridge, ValidatedPath, DASTProbe, DASTResult, AuditEvent, SignedAuditEntry, PIIType, PIIDetection, SecurityPolicy, IQECoreBridge, TestSuite, TestCase, TestSuiteConfig, ExecutorConfig, AgentHandle, TaskHandle, TaskResult, TaskProgress, QualityGate as IQualityGate, QualityGateCriteria, QualityMetrics, WorkflowResult, StepResult, Priority, IQEHiveBridge, HiveRole, QESwarmTask, QESwarmResult, AgentTaskResult, ConsensusResult, IQEModelRoutingAdapter, QETask, ModelTier as IModelTier, ModelSelection, QERouteResult, QEPluginContext, QELogger, QEPluginConfig, TestPatternType, } from './interfaces.js';
export { TestTypeSchema, TDDStyleSchema, TestFrameworkSchema, SecurityLevelSchema, ModelTierSchema, ContractTypeSchema, ChaosFailureTypeSchema, ComplianceStandardSchema, SecurityScanTypeSchema, SeveritySchema, QualityGateOperatorSchema, CoverageAlgorithmSchema, BoundedContextSchema, TestGenerationRequestSchema, TDDCycleRequestSchema, CoverageAnalysisRequestSchema, QualityGateRequestSchema, DefectPredictionRequestSchema, SecurityScanRequestSchema, ContractValidationRequestSchema, ChaosInjectionRequestSchema, VisualRegressionRequestSchema, AccessibilityCheckRequestSchema, PluginConfigSchema, SandboxConfigSchema, ModelRoutingConfigSchema, HNSWConfigSchema, MemoryNamespaceSchema, GenerateTestsInputSchema, AnalyzeCoverageInputSchema, SecurityScanInputSchema, ValidateContractInputSchema, ChaosInjectInputSchema, EvaluateQualityGateInputSchema, PredictDefectsInputSchema, TDDCycleInputSchema, validateInput, parseOrThrow, parseWithDefaults, } from './schemas.js';
export type { TestGenerationInput, TDDCycleInput, CoverageAnalysisInput, QualityGateInput, DefectPredictionInput, SecurityScanInput, ContractValidationInput, ChaosInjectionInput, VisualRegressionInput, AccessibilityCheckInput, PluginConfig, SandboxConfig as SandboxConfigType, ModelRoutingConfig as ModelRoutingConfigType, MemoryNamespace, WorkerDefinition, HookDefinition, AgentDefinition, } from './schemas.js';
/**
 * Plugin metadata for registration
 */
export declare const PLUGIN_METADATA: {
    readonly name: "agentic-qe";
    readonly version: "3.2.3";
    readonly description: "Quality Engineering plugin with 51 specialized agents across 12 DDD bounded contexts";
    readonly author: "rUv";
    readonly license: "MIT";
    readonly homepage: "https://github.com/ruvnet/agentic-qe";
    readonly repository: "https://github.com/ruvnet/agentic-qe";
    readonly minClaudeFlowVersion: "3.0.0-alpha.50";
    readonly capabilities: readonly ["test-generation", "test-execution", "coverage-analysis", "quality-assessment", "defect-intelligence", "requirements-validation", "code-intelligence", "security-compliance", "contract-testing", "visual-accessibility", "chaos-resilience", "learning-optimization"];
    readonly dependencies: {
        readonly required: readonly ["@claude-flow/plugins", "@claude-flow/memory", "@claude-flow/security", "@claude-flow/embeddings"];
        readonly optional: readonly ["@claude-flow/browser", "@ruvector/attention", "@ruvector/gnn", "@ruvector/sona"];
    };
};
/**
 * Plugin performance targets
 */
export declare const PERFORMANCE_TARGETS: {
    readonly testGenerationLatency: "<2s";
    readonly coverageAnalysis: "O(log n)";
    readonly qualityGateEvaluation: "<500ms";
    readonly securityScanPerKLOC: "<10s";
    readonly mcpToolResponse: "<100ms";
    readonly memoryPerContext: "<50MB";
};
/**
 * Bounded context agent counts
 */
export declare const CONTEXT_AGENT_COUNTS: {
    readonly 'test-generation': 12;
    readonly 'test-execution': 8;
    readonly 'coverage-analysis': 6;
    readonly 'quality-assessment': 5;
    readonly 'defect-intelligence': 4;
    readonly 'requirements-validation': 3;
    readonly 'code-intelligence': 5;
    readonly 'security-compliance': 4;
    readonly 'contract-testing': 3;
    readonly 'visual-accessibility': 3;
    readonly 'chaos-resilience': 4;
    readonly 'learning-optimization': 2;
    readonly tdd: 7;
};
/**
 * Total agent count
 */
export declare const TOTAL_AGENT_COUNT: number;
//# sourceMappingURL=index.d.ts.map