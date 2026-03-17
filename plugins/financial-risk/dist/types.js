/**
 * Financial Risk Plugin - Type Definitions
 *
 * Core types for financial risk analysis including portfolio risk,
 * anomaly detection, market regime classification, compliance checking,
 * and stress testing.
 */
import { z } from 'zod';
/**
 * Role-based access control mapping
 */
export const FinancialRolePermissions = {
    TRADER: ['portfolio-risk', 'market-regime'],
    RISK_MANAGER: ['portfolio-risk', 'anomaly-detect', 'stress-test', 'market-regime'],
    COMPLIANCE_OFFICER: ['compliance-check', 'anomaly-detect'],
    AUDITOR: ['compliance-check'],
    QUANT: ['portfolio-risk', 'market-regime', 'stress-test'],
    ADMIN: ['portfolio-risk', 'anomaly-detect', 'market-regime', 'compliance-check', 'stress-test'],
};
/**
 * Rate limits per tool
 */
export const FinancialRateLimits = {
    'portfolio-risk': { requestsPerMinute: 60, maxConcurrent: 5 },
    'anomaly-detect': { requestsPerMinute: 100, maxConcurrent: 10 },
    'stress-test': { requestsPerMinute: 10, maxConcurrent: 2 },
    'market-regime': { requestsPerMinute: 120, maxConcurrent: 10 },
    'compliance-check': { requestsPerMinute: 30, maxConcurrent: 3 },
};
/**
 * Default configuration
 */
export const DEFAULT_FINANCIAL_CONFIG = {
    compliance: {
        auditEnabled: true,
        retentionYears: 7,
        realTimeMonitoring: true,
    },
    risk: {
        defaultConfidenceLevel: 0.95,
        defaultHorizon: '1d',
        maxPositions: 10000,
        varMethod: 'historical',
    },
    anomaly: {
        defaultThreshold: 0.8,
        maxTransactions: 100000,
        windowSize: 30,
    },
    stressTest: {
        maxScenarios: 20,
        defaultSimulations: 10000,
    },
    cache: {
        enabled: true,
        ttl: 60000,
        maxSize: 500,
    },
};
// ============================================================================
// Zod Schemas for Input Validation
// ============================================================================
/**
 * Stock symbol validation
 */
const StockSymbolSchema = z.string().regex(/^[A-Z0-9.]{1,10}$/, 'Invalid stock symbol format').max(10);
/**
 * Portfolio risk input schema
 */
export const PortfolioRiskInputSchema = z.object({
    holdings: z.array(z.object({
        symbol: StockSymbolSchema,
        quantity: z.number().finite().min(-1e9).max(1e9),
        assetClass: z.string().max(50).optional(),
        sector: z.string().max(50).optional(),
        currency: z.string().max(3).optional(),
    })).min(1).max(10000),
    riskMetrics: z.array(z.enum(['var', 'cvar', 'sharpe', 'sortino', 'max_drawdown', 'beta', 'volatility'])).optional(),
    confidenceLevel: z.number().min(0.9).max(0.999).default(0.95),
    horizon: z.enum(['1d', '1w', '1m', '3m', '1y']).default('1d'),
});
/**
 * Anomaly detection input schema
 */
export const AnomalyDetectInputSchema = z.object({
    transactions: z.array(z.object({
        id: z.string().uuid(),
        amount: z.number().finite().min(-1e12).max(1e12),
        timestamp: z.string().datetime(),
        parties: z.array(z.string().max(200)).max(10),
        type: z.string().max(50).optional(),
        currency: z.string().max(3).optional(),
        metadata: z.record(z.string(), z.unknown()).optional(),
    })).min(1).max(100000),
    sensitivity: z.number().min(0).max(1).default(0.8),
    context: z.enum(['fraud', 'aml', 'market_manipulation', 'all']).default('all'),
});
/**
 * Market regime input schema
 */
export const MarketRegimeInputSchema = z.object({
    marketData: z.object({
        prices: z.array(z.number().finite()).min(10).max(10000),
        volumes: z.array(z.number().finite().min(0)).optional(),
        volatility: z.array(z.number().finite().min(0)).optional(),
        timestamps: z.array(z.string()).optional(),
    }),
    lookbackPeriod: z.number().int().min(10).max(1000).default(252),
    regimeTypes: z.array(z.enum(['bull', 'bear', 'sideways', 'high_vol', 'crisis', 'recovery'])).optional(),
});
/**
 * Compliance check input schema
 */
export const ComplianceCheckInputSchema = z.object({
    entity: z.string().max(200),
    regulations: z.array(z.enum(['basel3', 'mifid2', 'dodd_frank', 'aml', 'kyc', 'fatca', 'gdpr'])).min(1),
    scope: z.enum(['positions', 'transactions', 'capital', 'reporting', 'all']).default('all'),
    asOfDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
});
/**
 * Stress test input schema
 */
export const StressTestInputSchema = z.object({
    portfolio: z.object({
        id: z.string().optional(),
        holdings: z.array(z.object({
            symbol: StockSymbolSchema,
            quantity: z.number().finite(),
            assetClass: z.string().optional(),
        })).min(1).max(10000),
    }),
    scenarios: z.array(z.object({
        name: z.string().max(100),
        type: z.enum(['historical', 'hypothetical', 'reverse']),
        description: z.string().max(500).optional(),
        shocks: z.object({
            equityShock: z.number().min(-1).max(1).optional(),
            interestRateShock: z.number().min(-0.1).max(0.1).optional(),
            creditSpreadShock: z.number().min(-0.1).max(0.1).optional(),
            fxShock: z.record(z.string(), z.number().min(-1).max(1)).optional(),
            commodityShock: z.record(z.string(), z.number().min(-1).max(1)).optional(),
            volatilityShock: z.number().min(-1).max(5).optional(),
        }),
        historicalReference: z.string().optional(),
    })).min(1).max(20),
    metrics: z.array(z.string().max(50)).optional(),
});
// ============================================================================
// Result Helpers
// ============================================================================
/**
 * Create a success result
 */
export function successResult(data, metadata) {
    return {
        success: true,
        data,
        metadata,
    };
}
/**
 * Create an error result
 */
export function errorResult(error, metadata) {
    return {
        success: false,
        error: error instanceof Error ? error.message : error,
        metadata,
    };
}
// ============================================================================
// Error Codes
// ============================================================================
/**
 * Financial plugin error codes
 */
export const FinancialErrorCodes = {
    UNAUTHORIZED_ACCESS: 'FIN_UNAUTHORIZED_ACCESS',
    INVALID_PORTFOLIO: 'FIN_INVALID_PORTFOLIO',
    INVALID_TRANSACTION: 'FIN_INVALID_TRANSACTION',
    COMPLIANCE_VIOLATION: 'FIN_COMPLIANCE_VIOLATION',
    RATE_LIMIT_EXCEEDED: 'FIN_RATE_LIMIT_EXCEEDED',
    WASM_NOT_INITIALIZED: 'FIN_WASM_NOT_INITIALIZED',
    CALCULATION_FAILED: 'FIN_CALCULATION_FAILED',
    MARKET_DATA_UNAVAILABLE: 'FIN_MARKET_DATA_UNAVAILABLE',
    AUDIT_FAILED: 'FIN_AUDIT_FAILED',
    SCENARIO_INVALID: 'FIN_SCENARIO_INVALID',
};
//# sourceMappingURL=types.js.map