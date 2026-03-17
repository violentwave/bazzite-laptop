/**
 * Financial Risk Plugin - Type Definitions
 *
 * Core types for financial risk analysis including portfolio risk,
 * anomaly detection, market regime classification, compliance checking,
 * and stress testing.
 */
import { z } from 'zod';
/**
 * MCP Tool definition
 */
export interface MCPTool {
    name: string;
    description: string;
    category: string;
    version: string;
    tags: string[];
    cacheable: boolean;
    cacheTTL: number;
    inputSchema: {
        type: 'object';
        properties: Record<string, unknown>;
        required: string[];
    };
    handler: (input: Record<string, unknown>, context?: ToolContext) => Promise<MCPToolResult>;
}
/**
 * MCP Tool result
 */
export interface MCPToolResult {
    success: boolean;
    data?: unknown;
    error?: string;
    metadata?: {
        durationMs?: number;
        cached?: boolean;
        wasmUsed?: boolean;
    };
}
/**
 * Tool execution context
 */
export interface ToolContext {
    logger?: Logger;
    config?: FinancialConfig;
    bridge?: FinancialBridge;
    userId?: string;
    userRoles?: FinancialRole[];
    auditLogger?: FinancialAuditLogger;
}
/**
 * Simple logger interface
 */
export interface Logger {
    debug: (msg: string, meta?: Record<string, unknown>) => void;
    info: (msg: string, meta?: Record<string, unknown>) => void;
    warn: (msg: string, meta?: Record<string, unknown>) => void;
    error: (msg: string, meta?: Record<string, unknown>) => void;
}
/**
 * Portfolio holding
 */
export interface PortfolioHolding {
    symbol: string;
    quantity: number;
    assetClass?: string;
    sector?: string;
    currency?: string;
    marketValue?: number;
    costBasis?: number;
}
/**
 * Portfolio
 */
export interface Portfolio {
    id: string;
    name?: string;
    holdings: PortfolioHolding[];
    totalValue?: number;
    currency?: string;
    asOfDate?: string;
}
/**
 * Risk metric types
 */
export type RiskMetricType = 'var' | 'cvar' | 'sharpe' | 'sortino' | 'max_drawdown' | 'beta' | 'volatility';
/**
 * Time horizon for risk calculations
 */
export type TimeHorizon = '1d' | '1w' | '1m' | '3m' | '1y';
/**
 * Risk metrics result
 */
export interface RiskMetrics {
    var?: number;
    cvar?: number;
    sharpe?: number;
    sortino?: number;
    maxDrawdown?: number;
    beta?: number;
    volatility?: number;
    confidenceLevel: number;
    horizon: TimeHorizon;
}
/**
 * Portfolio risk result
 */
export interface PortfolioRiskResult {
    portfolio: Portfolio;
    metrics: RiskMetrics;
    concentrationRisk: {
        topHoldings: Array<{
            symbol: string;
            weight: number;
        }>;
        sectorExposure: Record<string, number>;
        geographicExposure?: Record<string, number>;
    };
    recommendations: string[];
    analysisTime: number;
    modelVersion: string;
}
/**
 * Financial transaction
 */
export interface FinancialTransaction {
    id: string;
    amount: number;
    timestamp: string;
    parties: string[];
    type?: string;
    currency?: string;
    metadata?: Record<string, unknown>;
}
/**
 * Anomaly context types
 */
export type AnomalyContext = 'fraud' | 'aml' | 'market_manipulation' | 'all';
/**
 * Anomaly severity
 */
export type AnomalySeverity = 'critical' | 'high' | 'medium' | 'low';
/**
 * Detected anomaly
 */
export interface DetectedAnomaly {
    transactionId: string;
    score: number;
    severity: AnomalySeverity;
    type: string;
    description: string;
    indicators: string[];
    relatedTransactions?: string[];
    recommendedAction: string;
}
/**
 * Anomaly detection result
 */
export interface AnomalyDetectionResult {
    transactions: FinancialTransaction[];
    anomalies: DetectedAnomaly[];
    riskScore: number;
    patterns: Array<{
        type: string;
        frequency: number;
        description: string;
    }>;
    networkAnalysis?: {
        clusters: number;
        suspiciousNodes: string[];
        graphDensity: number;
    };
    analysisTime: number;
}
/**
 * Market regime types
 */
export type MarketRegimeType = 'bull' | 'bear' | 'sideways' | 'high_vol' | 'crisis' | 'recovery';
/**
 * Market data for regime classification
 */
export interface MarketData {
    prices: number[];
    volumes?: number[];
    volatility?: number[];
    timestamps?: string[];
}
/**
 * Regime classification
 */
export interface RegimeClassification {
    regime: MarketRegimeType;
    confidence: number;
    probability: number;
    duration?: number;
    characteristics: string[];
}
/**
 * Market regime result
 */
export interface MarketRegimeResult {
    currentRegime: RegimeClassification;
    historicalRegimes: RegimeClassification[];
    transitionProbabilities: Record<MarketRegimeType, Record<MarketRegimeType, number>>;
    similarHistoricalPeriods: Array<{
        startDate: string;
        endDate: string;
        regime: MarketRegimeType;
        similarity: number;
    }>;
    outlook: {
        shortTerm: MarketRegimeType;
        mediumTerm: MarketRegimeType;
        confidence: number;
    };
    analysisTime: number;
}
/**
 * Regulation types
 */
export type RegulationType = 'basel3' | 'mifid2' | 'dodd_frank' | 'aml' | 'kyc' | 'fatca' | 'gdpr';
/**
 * Compliance scope
 */
export type ComplianceScope = 'positions' | 'transactions' | 'capital' | 'reporting' | 'all';
/**
 * Compliance violation
 */
export interface ComplianceViolation {
    id: string;
    regulation: RegulationType;
    severity: 'critical' | 'major' | 'minor' | 'warning';
    description: string;
    affectedItems: string[];
    remediation: string;
    deadline?: string;
}
/**
 * Capital adequacy metrics (Basel III)
 */
export interface CapitalAdequacy {
    cet1Ratio: number;
    tier1Ratio: number;
    totalCapitalRatio: number;
    leverageRatio: number;
    liquidity: {
        lcr: number;
        nsfr: number;
    };
    rwa: number;
}
/**
 * Compliance check result
 */
export interface ComplianceCheckResult {
    entity: string;
    regulations: RegulationType[];
    scope: ComplianceScope;
    compliant: boolean;
    violations: ComplianceViolation[];
    warnings: ComplianceViolation[];
    capitalAdequacy?: CapitalAdequacy;
    recommendations: string[];
    asOfDate: string;
    analysisTime: number;
}
/**
 * Stress test scenario type
 */
export type ScenarioType = 'historical' | 'hypothetical' | 'reverse';
/**
 * Market shocks for stress testing
 */
export interface MarketShocks {
    equityShock?: number;
    interestRateShock?: number;
    creditSpreadShock?: number;
    fxShock?: Record<string, number>;
    commodityShock?: Record<string, number>;
    volatilityShock?: number;
}
/**
 * Stress test scenario
 */
export interface StressScenario {
    name: string;
    type: ScenarioType;
    description?: string;
    shocks: MarketShocks;
    historicalReference?: string;
}
/**
 * Scenario impact result
 */
export interface ScenarioImpact {
    scenario: StressScenario;
    portfolioImpact: {
        pnl: number;
        percentChange: number;
        worstHolding: {
            symbol: string;
            loss: number;
        };
        bestHolding: {
            symbol: string;
            gain: number;
        };
    };
    riskMetrics: {
        varBreach: boolean;
        capitalImpact: number;
        liquidityImpact: number;
    };
    breaches: string[];
}
/**
 * Stress test result
 */
export interface StressTestResult {
    portfolio: Portfolio;
    scenarios: ScenarioImpact[];
    aggregateImpact: {
        worstCase: {
            scenario: string;
            pnl: number;
        };
        expectedLoss: number;
        tailRisk: number;
    };
    capitalRecommendation: number;
    recommendations: string[];
    analysisTime: number;
}
/**
 * Financial roles for RBAC
 */
export type FinancialRole = 'TRADER' | 'RISK_MANAGER' | 'COMPLIANCE_OFFICER' | 'AUDITOR' | 'QUANT' | 'ADMIN';
/**
 * Financial audit log entry (SOX/MiFID II compliant)
 */
export interface FinancialAuditLogEntry {
    timestamp: string;
    userId: string;
    toolName: string;
    transactionIds: string[];
    portfolioHash: string;
    riskMetricsComputed: string[];
    modelVersion: string;
    inputHash: string;
    outputHash: string;
    executionTimeMs: number;
    regulatoryFlags: string[];
}
/**
 * Financial audit logger interface
 */
export interface FinancialAuditLogger {
    log: (entry: FinancialAuditLogEntry) => Promise<void>;
    query: (filter: Partial<FinancialAuditLogEntry>) => Promise<FinancialAuditLogEntry[]>;
}
/**
 * Role-based access control mapping
 */
export declare const FinancialRolePermissions: Record<FinancialRole, string[]>;
/**
 * Rate limits per tool
 */
export declare const FinancialRateLimits: Record<string, {
    requestsPerMinute: number;
    maxConcurrent: number;
}>;
/**
 * Economy Bridge interface for token economics
 */
export interface EconomyBridge {
    initialized: boolean;
    calculateVar: (returns: Float32Array, confidence: number) => Promise<number>;
    calculateCvar: (returns: Float32Array, confidence: number) => Promise<number>;
    optimizePortfolio: (returns: Float32Array[], constraints: Record<string, number>) => Promise<Float32Array>;
    simulateMonteCarlo: (portfolio: Float32Array, scenarios: number, horizon: number) => Promise<Float32Array>;
    initialize: (config?: EconomyConfig) => Promise<void>;
}
/**
 * Economy bridge configuration
 */
export interface EconomyConfig {
    precision?: number;
    randomSeed?: number;
    defaultScenarios?: number;
}
/**
 * Sparse Bridge interface for efficient risk calculations
 */
export interface SparseBridge {
    initialized: boolean;
    sparseInference: (features: Float32Array, indices: Uint32Array) => Promise<Float32Array>;
    detectAnomalies: (transactions: Float32Array[], threshold: number) => Promise<Uint32Array>;
    classifyRegime: (marketData: Float32Array) => Promise<{
        regime: number;
        confidence: number;
    }>;
    initialize: (config?: SparseConfig) => Promise<void>;
}
/**
 * Sparse bridge configuration
 */
export interface SparseConfig {
    sparsityThreshold?: number;
    maxFeatures?: number;
    compressionLevel?: number;
}
/**
 * Combined financial bridge interface
 */
export interface FinancialBridge {
    economy?: EconomyBridge;
    sparse?: SparseBridge;
    initialized: boolean;
}
/**
 * Financial plugin configuration
 */
export interface FinancialConfig {
    compliance: {
        auditEnabled: boolean;
        retentionYears: number;
        realTimeMonitoring: boolean;
    };
    risk: {
        defaultConfidenceLevel: number;
        defaultHorizon: TimeHorizon;
        maxPositions: number;
        varMethod: 'historical' | 'parametric' | 'monte_carlo';
    };
    anomaly: {
        defaultThreshold: number;
        maxTransactions: number;
        windowSize: number;
    };
    stressTest: {
        maxScenarios: number;
        defaultSimulations: number;
    };
    cache: {
        enabled: boolean;
        ttl: number;
        maxSize: number;
    };
}
/**
 * Default configuration
 */
export declare const DEFAULT_FINANCIAL_CONFIG: FinancialConfig;
/**
 * Portfolio risk input schema
 */
export declare const PortfolioRiskInputSchema: z.ZodObject<{
    holdings: z.ZodArray<z.ZodObject<{
        symbol: z.ZodString;
        quantity: z.ZodNumber;
        assetClass: z.ZodOptional<z.ZodString>;
        sector: z.ZodOptional<z.ZodString>;
        currency: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        symbol: string;
        quantity: number;
        assetClass?: string | undefined;
        sector?: string | undefined;
        currency?: string | undefined;
    }, {
        symbol: string;
        quantity: number;
        assetClass?: string | undefined;
        sector?: string | undefined;
        currency?: string | undefined;
    }>, "many">;
    riskMetrics: z.ZodOptional<z.ZodArray<z.ZodEnum<["var", "cvar", "sharpe", "sortino", "max_drawdown", "beta", "volatility"]>, "many">>;
    confidenceLevel: z.ZodDefault<z.ZodNumber>;
    horizon: z.ZodDefault<z.ZodEnum<["1d", "1w", "1m", "3m", "1y"]>>;
}, "strip", z.ZodTypeAny, {
    holdings: {
        symbol: string;
        quantity: number;
        assetClass?: string | undefined;
        sector?: string | undefined;
        currency?: string | undefined;
    }[];
    confidenceLevel: number;
    horizon: "1d" | "1w" | "1m" | "3m" | "1y";
    riskMetrics?: ("var" | "cvar" | "sharpe" | "sortino" | "max_drawdown" | "beta" | "volatility")[] | undefined;
}, {
    holdings: {
        symbol: string;
        quantity: number;
        assetClass?: string | undefined;
        sector?: string | undefined;
        currency?: string | undefined;
    }[];
    riskMetrics?: ("var" | "cvar" | "sharpe" | "sortino" | "max_drawdown" | "beta" | "volatility")[] | undefined;
    confidenceLevel?: number | undefined;
    horizon?: "1d" | "1w" | "1m" | "3m" | "1y" | undefined;
}>;
/**
 * Anomaly detection input schema
 */
export declare const AnomalyDetectInputSchema: z.ZodObject<{
    transactions: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        amount: z.ZodNumber;
        timestamp: z.ZodString;
        parties: z.ZodArray<z.ZodString, "many">;
        type: z.ZodOptional<z.ZodString>;
        currency: z.ZodOptional<z.ZodString>;
        metadata: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        amount: number;
        timestamp: string;
        parties: string[];
        type?: string | undefined;
        currency?: string | undefined;
        metadata?: Record<string, unknown> | undefined;
    }, {
        id: string;
        amount: number;
        timestamp: string;
        parties: string[];
        type?: string | undefined;
        currency?: string | undefined;
        metadata?: Record<string, unknown> | undefined;
    }>, "many">;
    sensitivity: z.ZodDefault<z.ZodNumber>;
    context: z.ZodDefault<z.ZodEnum<["fraud", "aml", "market_manipulation", "all"]>>;
}, "strip", z.ZodTypeAny, {
    transactions: {
        id: string;
        amount: number;
        timestamp: string;
        parties: string[];
        type?: string | undefined;
        currency?: string | undefined;
        metadata?: Record<string, unknown> | undefined;
    }[];
    sensitivity: number;
    context: "fraud" | "aml" | "market_manipulation" | "all";
}, {
    transactions: {
        id: string;
        amount: number;
        timestamp: string;
        parties: string[];
        type?: string | undefined;
        currency?: string | undefined;
        metadata?: Record<string, unknown> | undefined;
    }[];
    sensitivity?: number | undefined;
    context?: "fraud" | "aml" | "market_manipulation" | "all" | undefined;
}>;
/**
 * Market regime input schema
 */
export declare const MarketRegimeInputSchema: z.ZodObject<{
    marketData: z.ZodObject<{
        prices: z.ZodArray<z.ZodNumber, "many">;
        volumes: z.ZodOptional<z.ZodArray<z.ZodNumber, "many">>;
        volatility: z.ZodOptional<z.ZodArray<z.ZodNumber, "many">>;
        timestamps: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
    }, "strip", z.ZodTypeAny, {
        prices: number[];
        volatility?: number[] | undefined;
        volumes?: number[] | undefined;
        timestamps?: string[] | undefined;
    }, {
        prices: number[];
        volatility?: number[] | undefined;
        volumes?: number[] | undefined;
        timestamps?: string[] | undefined;
    }>;
    lookbackPeriod: z.ZodDefault<z.ZodNumber>;
    regimeTypes: z.ZodOptional<z.ZodArray<z.ZodEnum<["bull", "bear", "sideways", "high_vol", "crisis", "recovery"]>, "many">>;
}, "strip", z.ZodTypeAny, {
    marketData: {
        prices: number[];
        volatility?: number[] | undefined;
        volumes?: number[] | undefined;
        timestamps?: string[] | undefined;
    };
    lookbackPeriod: number;
    regimeTypes?: ("bull" | "bear" | "sideways" | "high_vol" | "crisis" | "recovery")[] | undefined;
}, {
    marketData: {
        prices: number[];
        volatility?: number[] | undefined;
        volumes?: number[] | undefined;
        timestamps?: string[] | undefined;
    };
    lookbackPeriod?: number | undefined;
    regimeTypes?: ("bull" | "bear" | "sideways" | "high_vol" | "crisis" | "recovery")[] | undefined;
}>;
/**
 * Compliance check input schema
 */
export declare const ComplianceCheckInputSchema: z.ZodObject<{
    entity: z.ZodString;
    regulations: z.ZodArray<z.ZodEnum<["basel3", "mifid2", "dodd_frank", "aml", "kyc", "fatca", "gdpr"]>, "many">;
    scope: z.ZodDefault<z.ZodEnum<["positions", "transactions", "capital", "reporting", "all"]>>;
    asOfDate: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    entity: string;
    regulations: ("aml" | "basel3" | "mifid2" | "dodd_frank" | "kyc" | "fatca" | "gdpr")[];
    scope: "all" | "positions" | "transactions" | "capital" | "reporting";
    asOfDate?: string | undefined;
}, {
    entity: string;
    regulations: ("aml" | "basel3" | "mifid2" | "dodd_frank" | "kyc" | "fatca" | "gdpr")[];
    scope?: "all" | "positions" | "transactions" | "capital" | "reporting" | undefined;
    asOfDate?: string | undefined;
}>;
/**
 * Stress test input schema
 */
export declare const StressTestInputSchema: z.ZodObject<{
    portfolio: z.ZodObject<{
        id: z.ZodOptional<z.ZodString>;
        holdings: z.ZodArray<z.ZodObject<{
            symbol: z.ZodString;
            quantity: z.ZodNumber;
            assetClass: z.ZodOptional<z.ZodString>;
        }, "strip", z.ZodTypeAny, {
            symbol: string;
            quantity: number;
            assetClass?: string | undefined;
        }, {
            symbol: string;
            quantity: number;
            assetClass?: string | undefined;
        }>, "many">;
    }, "strip", z.ZodTypeAny, {
        holdings: {
            symbol: string;
            quantity: number;
            assetClass?: string | undefined;
        }[];
        id?: string | undefined;
    }, {
        holdings: {
            symbol: string;
            quantity: number;
            assetClass?: string | undefined;
        }[];
        id?: string | undefined;
    }>;
    scenarios: z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        type: z.ZodEnum<["historical", "hypothetical", "reverse"]>;
        description: z.ZodOptional<z.ZodString>;
        shocks: z.ZodObject<{
            equityShock: z.ZodOptional<z.ZodNumber>;
            interestRateShock: z.ZodOptional<z.ZodNumber>;
            creditSpreadShock: z.ZodOptional<z.ZodNumber>;
            fxShock: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodNumber>>;
            commodityShock: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodNumber>>;
            volatilityShock: z.ZodOptional<z.ZodNumber>;
        }, "strip", z.ZodTypeAny, {
            equityShock?: number | undefined;
            interestRateShock?: number | undefined;
            creditSpreadShock?: number | undefined;
            fxShock?: Record<string, number> | undefined;
            commodityShock?: Record<string, number> | undefined;
            volatilityShock?: number | undefined;
        }, {
            equityShock?: number | undefined;
            interestRateShock?: number | undefined;
            creditSpreadShock?: number | undefined;
            fxShock?: Record<string, number> | undefined;
            commodityShock?: Record<string, number> | undefined;
            volatilityShock?: number | undefined;
        }>;
        historicalReference: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        type: "historical" | "hypothetical" | "reverse";
        name: string;
        shocks: {
            equityShock?: number | undefined;
            interestRateShock?: number | undefined;
            creditSpreadShock?: number | undefined;
            fxShock?: Record<string, number> | undefined;
            commodityShock?: Record<string, number> | undefined;
            volatilityShock?: number | undefined;
        };
        description?: string | undefined;
        historicalReference?: string | undefined;
    }, {
        type: "historical" | "hypothetical" | "reverse";
        name: string;
        shocks: {
            equityShock?: number | undefined;
            interestRateShock?: number | undefined;
            creditSpreadShock?: number | undefined;
            fxShock?: Record<string, number> | undefined;
            commodityShock?: Record<string, number> | undefined;
            volatilityShock?: number | undefined;
        };
        description?: string | undefined;
        historicalReference?: string | undefined;
    }>, "many">;
    metrics: z.ZodOptional<z.ZodArray<z.ZodString, "many">>;
}, "strip", z.ZodTypeAny, {
    portfolio: {
        holdings: {
            symbol: string;
            quantity: number;
            assetClass?: string | undefined;
        }[];
        id?: string | undefined;
    };
    scenarios: {
        type: "historical" | "hypothetical" | "reverse";
        name: string;
        shocks: {
            equityShock?: number | undefined;
            interestRateShock?: number | undefined;
            creditSpreadShock?: number | undefined;
            fxShock?: Record<string, number> | undefined;
            commodityShock?: Record<string, number> | undefined;
            volatilityShock?: number | undefined;
        };
        description?: string | undefined;
        historicalReference?: string | undefined;
    }[];
    metrics?: string[] | undefined;
}, {
    portfolio: {
        holdings: {
            symbol: string;
            quantity: number;
            assetClass?: string | undefined;
        }[];
        id?: string | undefined;
    };
    scenarios: {
        type: "historical" | "hypothetical" | "reverse";
        name: string;
        shocks: {
            equityShock?: number | undefined;
            interestRateShock?: number | undefined;
            creditSpreadShock?: number | undefined;
            fxShock?: Record<string, number> | undefined;
            commodityShock?: Record<string, number> | undefined;
            volatilityShock?: number | undefined;
        };
        description?: string | undefined;
        historicalReference?: string | undefined;
    }[];
    metrics?: string[] | undefined;
}>;
/**
 * Create a success result
 */
export declare function successResult<T>(data: T, metadata?: MCPToolResult['metadata']): MCPToolResult;
/**
 * Create an error result
 */
export declare function errorResult(error: string | Error, metadata?: MCPToolResult['metadata']): MCPToolResult;
/**
 * Financial plugin error codes
 */
export declare const FinancialErrorCodes: {
    readonly UNAUTHORIZED_ACCESS: "FIN_UNAUTHORIZED_ACCESS";
    readonly INVALID_PORTFOLIO: "FIN_INVALID_PORTFOLIO";
    readonly INVALID_TRANSACTION: "FIN_INVALID_TRANSACTION";
    readonly COMPLIANCE_VIOLATION: "FIN_COMPLIANCE_VIOLATION";
    readonly RATE_LIMIT_EXCEEDED: "FIN_RATE_LIMIT_EXCEEDED";
    readonly WASM_NOT_INITIALIZED: "FIN_WASM_NOT_INITIALIZED";
    readonly CALCULATION_FAILED: "FIN_CALCULATION_FAILED";
    readonly MARKET_DATA_UNAVAILABLE: "FIN_MARKET_DATA_UNAVAILABLE";
    readonly AUDIT_FAILED: "FIN_AUDIT_FAILED";
    readonly SCENARIO_INVALID: "FIN_SCENARIO_INVALID";
};
export type FinancialErrorCode = (typeof FinancialErrorCodes)[keyof typeof FinancialErrorCodes];
/**
 * Risk calculation proof for regulatory audits
 */
export interface RiskCalculationProof {
    inputHash: string;
    modelChecksum: string;
    randomSeed: string;
    outputHash: string;
    signature: string;
    timestamp: string;
}
//# sourceMappingURL=types.d.ts.map