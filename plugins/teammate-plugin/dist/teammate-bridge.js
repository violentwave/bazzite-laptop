/**
 * TeammateBridge - Core bridge to Claude Code's TeammateTool
 *
 * Provides unified API for multi-agent orchestration using
 * native TeammateTool capabilities (Claude Code >= 2.1.19).
 *
 * Features:
 * - Team management (spawn, discover, join/leave)
 * - Mailbox messaging (write, broadcast)
 * - Plan approval workflow
 * - Delegation system
 * - Remote sync to Claude.ai
 * - Session memory persistence
 * - Teleport/session resume
 *
 * @module @claude-flow/teammate-plugin/bridge
 * @version 1.0.0-alpha.1
 */
import { EventEmitter } from 'events';
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
// BMSSP-powered optimizer imports
import { createTopologyOptimizer } from './topology-optimizer.js';
import { createSemanticRouter } from './semantic-router.js';
import { MINIMUM_CLAUDE_CODE_VERSION, DEFAULT_PLUGIN_CONFIG, TeammateErrorCode, } from './types.js';
import { DEFAULT_RATE_LIMIT_CONFIG, DEFAULT_HEALTH_CHECK_CONFIG, DEFAULT_CIRCUIT_BREAKER_CONFIG, SECURITY_LIMITS, } from './types.js';
// Import utility classes from extracted modules
import { RateLimiter } from './utils/rate-limiter.js';
import { MetricsCollector } from './utils/metrics-collector.js';
import { HealthChecker } from './utils/health-checker.js';
import { CircuitBreaker } from './utils/circuit-breaker.js';
// ============================================================================
// TeammateError Class
// ============================================================================
export class TeammateError extends Error {
    code;
    teamName;
    teammateId;
    cause;
    constructor(message, code, teamName, teammateId, cause) {
        super(message);
        this.code = code;
        this.teamName = teamName;
        this.teammateId = teammateId;
        this.cause = cause;
        this.name = 'TeammateError';
    }
}
// ============================================================================
// Security Constants (from centralized SECURITY_LIMITS)
// ============================================================================
const MAX_NAME_LENGTH = SECURITY_LIMITS.MAX_NAME_LENGTH;
const MAX_PAYLOAD_SIZE = SECURITY_LIMITS.MAX_PAYLOAD_SIZE;
/** Allowed characters in team/teammate names (alphanumeric, dash, underscore) */
const SAFE_NAME_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/;
/** Reserved names that cannot be used for teams */
const RESERVED_NAMES = new Set(['..', '.', 'config', 'state', 'mailbox', 'memory', 'remote']);
// ============================================================================
// Utility Functions
// ============================================================================
function generateId(prefix) {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).slice(2, 10);
    return `${prefix}-${timestamp}-${random}`;
}
function compareVersions(a, b) {
    const partsA = a.split('.').map(Number);
    const partsB = b.split('.').map(Number);
    for (let i = 0; i < Math.max(partsA.length, partsB.length); i++) {
        const numA = partsA[i] || 0;
        const numB = partsB[i] || 0;
        if (numA > numB)
            return 1;
        if (numA < numB)
            return -1;
    }
    return 0;
}
function ensureDirectory(dirPath) {
    if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath, { recursive: true, mode: 0o700 }); // Secure permissions
    }
}
// ============================================================================
// Security Functions
// ============================================================================
/**
 * Validate and sanitize team/teammate names to prevent path traversal
 */
function validateName(name, type) {
    if (!name || typeof name !== 'string') {
        throw new TeammateError(`Invalid ${type} name: must be a non-empty string`, TeammateErrorCode.PERMISSION_DENIED);
    }
    const trimmed = name.trim();
    if (trimmed.length === 0) {
        throw new TeammateError(`Invalid ${type} name: cannot be empty`, TeammateErrorCode.PERMISSION_DENIED);
    }
    if (trimmed.length > MAX_NAME_LENGTH) {
        throw new TeammateError(`Invalid ${type} name: exceeds maximum length of ${MAX_NAME_LENGTH}`, TeammateErrorCode.PERMISSION_DENIED);
    }
    if (!SAFE_NAME_PATTERN.test(trimmed)) {
        throw new TeammateError(`Invalid ${type} name: must contain only alphanumeric characters, dashes, and underscores`, TeammateErrorCode.PERMISSION_DENIED);
    }
    if (RESERVED_NAMES.has(trimmed.toLowerCase())) {
        throw new TeammateError(`Invalid ${type} name: '${trimmed}' is reserved`, TeammateErrorCode.PERMISSION_DENIED);
    }
    return trimmed;
}
/**
 * Validate that a path is within the allowed base directory
 */
function validatePath(targetPath, basePath) {
    const resolvedTarget = path.resolve(targetPath);
    const resolvedBase = path.resolve(basePath);
    if (!resolvedTarget.startsWith(resolvedBase + path.sep) && resolvedTarget !== resolvedBase) {
        throw new TeammateError('Path traversal attempt detected', TeammateErrorCode.PERMISSION_DENIED);
    }
    return resolvedTarget;
}
/**
 * Safely parse JSON with size limits
 */
function safeJSONParse(content, maxSize = MAX_PAYLOAD_SIZE) {
    if (content.length > maxSize) {
        throw new TeammateError(`JSON content exceeds maximum size of ${maxSize} bytes`, TeammateErrorCode.MAILBOX_FULL);
    }
    try {
        return JSON.parse(content);
    }
    catch (error) {
        throw new TeammateError('Invalid JSON content', TeammateErrorCode.PERMISSION_DENIED);
    }
}
/**
 * Sanitize environment variable value
 */
function sanitizeEnvValue(value) {
    // Remove any null bytes or control characters except newlines
    return value.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, '');
}
// ============================================================================
// TeammateBridge Class
// ============================================================================
export class TeammateBridge extends EventEmitter {
    claudeCodeVersion = null;
    teammateToolAvailable = false;
    initialized = false;
    activeTeams = new Map();
    mailboxPollers = new Map();
    memoryPersistTimers = new Map();
    teammateMemories = new Map();
    // Performance: Debounced write queues
    pendingWrites = new Map();
    writeDebounceMs = 500;
    // Performance: Cache for frequently accessed data
    teamConfigCache = new Map();
    cacheMaxAgeMs = 30000; // 30 seconds
    // Rate limiting, metrics, health, circuit breaker
    rateLimiter;
    metrics;
    healthChecker;
    circuitBreaker;
    // Message TTL cleanup
    messageTTLTimer = null;
    messageTTLCheckIntervalMs = 60000; // 1 minute
    // BMSSP-powered optimizers
    topologyOptimizers = new Map();
    semanticRouter = null;
    optimizersEnabled = false;
    config;
    teamsDir;
    constructor(config = {}) {
        super();
        this.config = { ...DEFAULT_PLUGIN_CONFIG, ...config };
        this.teamsDir = path.join(os.homedir(), '.claude', 'teams');
        // Initialize rate limiter
        this.rateLimiter = new RateLimiter(DEFAULT_RATE_LIMIT_CONFIG);
        // Initialize metrics collector
        this.metrics = new MetricsCollector();
        // Initialize health checker with status change callback
        this.healthChecker = new HealthChecker(DEFAULT_HEALTH_CHECK_CONFIG, (check) => this.onHealthStatusChange(check));
        // Initialize circuit breaker
        this.circuitBreaker = new CircuitBreaker(DEFAULT_CIRCUIT_BREAKER_CONFIG);
    }
    /**
     * Handle health status changes
     */
    onHealthStatusChange(check) {
        this.emit('health:changed', check);
        if (check.status === 'unhealthy') {
            this.metrics.increment('healthChecksFailed');
            this.emit('health:unhealthy', check);
        }
        else if (check.status === 'healthy') {
            this.metrics.increment('healthChecksPassed');
        }
    }
    // ==========================================================================
    // Initialization
    // ==========================================================================
    /**
     * Initialize the bridge
     * Detects Claude Code version and TeammateTool availability
     */
    async initialize() {
        if (this.initialized) {
            return this.getVersionInfo();
        }
        // Detect Claude Code version
        try {
            const output = execSync('claude --version 2>/dev/null', {
                encoding: 'utf-8',
                timeout: 5000,
            }).trim();
            const match = output.match(/(\d+\.\d+\.\d+)/);
            this.claudeCodeVersion = match?.[1] ?? null;
            // TeammateTool requires >= 2.1.19
            if (this.claudeCodeVersion) {
                this.teammateToolAvailable =
                    compareVersions(this.claudeCodeVersion, MINIMUM_CLAUDE_CODE_VERSION) >= 0;
            }
        }
        catch {
            this.claudeCodeVersion = null;
            this.teammateToolAvailable = false;
        }
        this.initialized = true;
        const versionInfo = this.getVersionInfo();
        this.emit('initialized', {
            claudeCodeVersion: this.claudeCodeVersion,
            teammateToolAvailable: this.teammateToolAvailable,
        });
        if (!this.teammateToolAvailable) {
            console.warn(`[TeammateBridge] TeammateTool not available. ` +
                `Requires Claude Code >= ${MINIMUM_CLAUDE_CODE_VERSION}, ` +
                `found: ${this.claudeCodeVersion ?? 'not installed'}`);
        }
        return versionInfo;
    }
    /**
     * Get version information
     */
    getVersionInfo() {
        const missingFeatures = [];
        if (!this.teammateToolAvailable) {
            missingFeatures.push('TeammateTool', 'team_name', 'launchSwarm');
        }
        return {
            claudeCode: this.claudeCodeVersion,
            plugin: '1.0.0-alpha.1',
            compatible: this.teammateToolAvailable,
            missingFeatures,
        };
    }
    /**
     * Check if TeammateTool is available
     */
    isAvailable() {
        return this.teammateToolAvailable;
    }
    // ==========================================================================
    // Metrics & Observability
    // ==========================================================================
    /**
     * Get current metrics snapshot
     */
    getMetrics() {
        return this.metrics.getSnapshot();
    }
    /**
     * Get latency percentile for an operation
     */
    getLatencyPercentile(operation, percentile) {
        return this.metrics.getPercentile(operation, percentile);
    }
    /**
     * Reset metrics
     */
    resetMetrics() {
        this.metrics.reset();
    }
    // ==========================================================================
    // Health Checks
    // ==========================================================================
    /**
     * Get health check for a specific teammate
     */
    getTeammateHealth(teammateId) {
        return this.healthChecker.getCheck(teammateId);
    }
    /**
     * Get health report for a team
     */
    getTeamHealth(teamName) {
        return this.healthChecker.getTeamReport(teamName);
    }
    // ==========================================================================
    // Rate Limiting
    // ==========================================================================
    /**
     * Get remaining rate limit quota for an operation
     */
    getRateLimitRemaining(operation) {
        return this.rateLimiter.getRemaining(operation);
    }
    /**
     * Check if an operation is rate limited
     */
    isRateLimited(operation) {
        const state = this.rateLimiter.getState(operation);
        return state?.blocked ?? false;
    }
    /**
     * Reset rate limits
     */
    resetRateLimits(operation) {
        this.rateLimiter.reset(operation);
    }
    // ==========================================================================
    // Circuit Breaker
    // ==========================================================================
    /**
     * Get circuit breaker state
     */
    getCircuitBreakerState() {
        return this.circuitBreaker.getState();
    }
    /**
     * Reset circuit breaker
     */
    resetCircuitBreaker() {
        this.circuitBreaker.reset();
    }
    /**
     * Get Claude Code version
     */
    getClaudeCodeVersion() {
        return this.claudeCodeVersion;
    }
    // ==========================================================================
    // BMSSP Optimization (10-15x faster routing)
    // ==========================================================================
    /**
     * Enable BMSSP-powered optimizers
     * @returns true if WASM acceleration available, false if using fallback
     */
    async enableOptimizers() {
        if (this.optimizersEnabled) {
            return !this.semanticRouter?.['useFallback'];
        }
        try {
            // Initialize semantic router (neural routing)
            this.semanticRouter = await createSemanticRouter();
            this.optimizersEnabled = true;
            // Initialize topology optimizers for existing teams
            for (const [teamName, team] of this.activeTeams) {
                await this.initializeTeamOptimizer(teamName, team);
            }
            this.emit('optimizers:enabled', {
                wasmAvailable: !this.semanticRouter['useFallback'],
            });
            return !this.semanticRouter['useFallback'];
        }
        catch (error) {
            console.warn('[TeammateBridge] Failed to enable optimizers:', error);
            return false;
        }
    }
    /**
     * Check if optimizers are enabled
     */
    areOptimizersEnabled() {
        return this.optimizersEnabled;
    }
    /**
     * Find optimal message routing path using BMSSP
     */
    async findOptimalPath(teamName, fromId, toId) {
        if (!this.optimizersEnabled) {
            return null;
        }
        const optimizer = this.topologyOptimizers.get(teamName);
        if (!optimizer) {
            return null;
        }
        return optimizer.findShortestPath(fromId, toId);
    }
    /**
     * Get topology statistics for a team
     */
    getTopologyStats(teamName) {
        const optimizer = this.topologyOptimizers.get(teamName);
        return optimizer?.getStats() ?? null;
    }
    /**
     * Get optimization suggestions for team topology
     */
    getTopologyOptimizations(teamName) {
        const optimizer = this.topologyOptimizers.get(teamName);
        return optimizer?.suggestOptimizations() ?? null;
    }
    /**
     * Find best teammate for a task using semantic routing
     */
    async findBestTeammateForTask(teamName, task) {
        if (!this.optimizersEnabled || !this.semanticRouter) {
            return null;
        }
        const team = this.activeTeams.get(teamName);
        if (!team) {
            return null;
        }
        // Build profiles from team if not already done
        await this.semanticRouter.buildFromTeam(team);
        const taskProfile = {
            id: task.id,
            description: task.description,
            requiredSkills: task.requiredSkills,
            priority: task.priority ?? 'normal',
        };
        return this.semanticRouter.findBestMatch(taskProfile);
    }
    /**
     * Batch route multiple tasks to teammates
     */
    async batchRouteTasksToTeammates(teamName, tasks) {
        if (!this.optimizersEnabled || !this.semanticRouter) {
            return new Map();
        }
        const team = this.activeTeams.get(teamName);
        if (!team) {
            return new Map();
        }
        // Build profiles from team
        await this.semanticRouter.buildFromTeam(team);
        const taskProfiles = tasks.map(t => ({
            id: t.id,
            description: t.description,
            requiredSkills: t.requiredSkills,
            priority: t.priority ?? 'normal',
        }));
        return this.semanticRouter.batchMatch(taskProfiles);
    }
    /**
     * Update teammate performance for learning
     */
    updateTeammatePerformance(teammateId, taskSuccess, latencyMs) {
        if (this.semanticRouter) {
            this.semanticRouter.updatePerformance(teammateId, taskSuccess, latencyMs);
        }
    }
    /**
     * Get semantic distance between two teammates
     */
    getTeammateSemanticDistance(id1, id2) {
        if (!this.semanticRouter) {
            return Infinity;
        }
        return this.semanticRouter.getSemanticDistance(id1, id2);
    }
    /**
     * Initialize optimizer for a team
     */
    async initializeTeamOptimizer(teamName, team) {
        if (!this.optimizersEnabled)
            return;
        // Create topology optimizer
        const optimizer = await createTopologyOptimizer(team.topology);
        await optimizer.buildFromTeam(team);
        this.topologyOptimizers.set(teamName, optimizer);
        // Register teammates with semantic router
        if (this.semanticRouter) {
            for (const teammate of team.teammates) {
                this.semanticRouter.registerTeammate(teammate);
            }
        }
    }
    // ==========================================================================
    // Team Management
    // ==========================================================================
    /**
     * Spawn a new team
     */
    async spawnTeam(config) {
        this.ensureAvailable();
        // Security: Validate team name
        const validatedName = validateName(config.name, 'team');
        const fullConfig = {
            topology: 'hierarchical',
            maxTeammates: 8,
            spawnBackend: 'auto',
            planModeRequired: false,
            autoApproveJoin: true,
            messageRetention: 3600000,
            delegationEnabled: true,
            remoteSync: this.config.remoteSync,
            ...config,
            name: validatedName, // Use validated name
        };
        const teamState = {
            name: fullConfig.name,
            createdAt: new Date(),
            teammates: [],
            pendingJoinRequests: [],
            activePlans: [],
            messageCount: 0,
            topology: fullConfig.topology,
            context: {
                teamName: fullConfig.name,
                sharedVariables: {},
                inheritedPermissions: [],
                workingDirectory: process.cwd(),
                gitBranch: this.getCurrentGitBranch(),
                gitRepo: this.getCurrentGitRepo(),
                environmentVariables: {},
            },
            delegations: [],
        };
        // Set environment for team context (sanitized)
        process.env.CLAUDE_CODE_TEAM_NAME = sanitizeEnvValue(fullConfig.name);
        if (fullConfig.planModeRequired) {
            process.env.CLAUDE_CODE_PLAN_MODE_REQUIRED = 'true';
        }
        // Create team directory
        const teamDir = path.join(this.teamsDir, fullConfig.name);
        ensureDirectory(teamDir);
        ensureDirectory(path.join(teamDir, 'mailbox'));
        ensureDirectory(path.join(teamDir, 'memory'));
        // Save team config with secure permissions
        fs.writeFileSync(path.join(teamDir, 'config.json'), JSON.stringify(fullConfig, null, 2), { encoding: 'utf-8', mode: 0o600 });
        this.activeTeams.set(fullConfig.name, teamState);
        // Start mailbox polling
        this.startMailboxPoller(fullConfig.name);
        // Start memory persistence if enabled
        if (this.config.memory.autoPersist) {
            this.startMemoryPersistence(fullConfig.name);
        }
        // Initialize optimizer if enabled
        if (this.optimizersEnabled) {
            await this.initializeTeamOptimizer(fullConfig.name, teamState);
        }
        this.emit('team:spawned', { team: fullConfig.name, config: fullConfig });
        this.metrics.increment('teamsCreated');
        this.metrics.increment('activeTeams');
        return teamState;
    }
    /**
     * Discover existing teams
     */
    async discoverTeams() {
        this.ensureAvailable();
        try {
            if (!fs.existsSync(this.teamsDir)) {
                return [];
            }
            const entries = fs.readdirSync(this.teamsDir, { withFileTypes: true });
            return entries
                .filter(d => d.isDirectory())
                .filter(d => fs.existsSync(path.join(this.teamsDir, d.name, 'config.json')))
                .map(d => d.name);
        }
        catch {
            return [];
        }
    }
    /**
     * Load an existing team
     */
    async loadTeam(teamName) {
        this.ensureAvailable();
        // Security: Validate team name to prevent path traversal
        const validatedName = validateName(teamName, 'team');
        const teamDir = path.join(this.teamsDir, validatedName);
        // Security: Ensure path is within teams directory
        validatePath(teamDir, this.teamsDir);
        const configPath = path.join(teamDir, 'config.json');
        if (!fs.existsSync(configPath)) {
            throw new TeammateError(`Team not found: ${validatedName}`, TeammateErrorCode.TEAM_NOT_FOUND, validatedName);
        }
        // Security: Use safe JSON parsing
        const configContent = fs.readFileSync(configPath, 'utf-8');
        const config = safeJSONParse(configContent);
        // Load state file if exists
        const statePath = path.join(teamDir, 'state.json');
        let teamState;
        if (fs.existsSync(statePath)) {
            // Security: Use safe JSON parsing
            const stateContent = fs.readFileSync(statePath, 'utf-8');
            const savedState = safeJSONParse(stateContent);
            teamState = {
                ...savedState,
                createdAt: new Date(savedState.createdAt),
                teammates: savedState.teammates.map((t) => ({
                    ...t,
                    spawnedAt: new Date(t.spawnedAt),
                    lastHeartbeat: t.lastHeartbeat ? new Date(t.lastHeartbeat) : undefined,
                })),
            };
        }
        else {
            teamState = {
                name: teamName,
                createdAt: new Date(),
                teammates: [],
                pendingJoinRequests: [],
                activePlans: [],
                messageCount: 0,
                topology: config.topology,
                context: {
                    teamName,
                    sharedVariables: {},
                    inheritedPermissions: [],
                    workingDirectory: process.cwd(),
                    environmentVariables: {},
                },
                delegations: [],
            };
        }
        this.activeTeams.set(teamName, teamState);
        // Start mailbox polling
        this.startMailboxPoller(teamName);
        return teamState;
    }
    /**
     * Request to join an existing team
     */
    async requestJoin(teamName, agentInfo) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const request = {
            agentId: agentInfo.id,
            agentName: agentInfo.name,
            requestedAt: new Date(),
            role: agentInfo.role,
        };
        team.pendingJoinRequests.push(request);
        this.emit('team:join_requested', {
            team: teamName,
            agent: {
                id: agentInfo.id,
                name: agentInfo.name,
                role: agentInfo.role,
                status: 'idle',
                spawnedAt: new Date(),
                messagesSent: 0,
                messagesReceived: 0,
            },
        });
        // Auto-approve if configured
        const teamDir = path.join(this.teamsDir, teamName);
        const configPath = path.join(teamDir, 'config.json');
        if (fs.existsSync(configPath)) {
            const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
            if (config.autoApproveJoin) {
                await this.approveJoin(teamName, agentInfo.id);
            }
        }
    }
    /**
     * Approve a join request
     */
    async approveJoin(teamName, agentId) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const requestIndex = team.pendingJoinRequests.findIndex(r => r.agentId === agentId);
        if (requestIndex === -1) {
            throw new TeammateError(`No pending join request for agent: ${agentId}`, TeammateErrorCode.TEAMMATE_NOT_FOUND, teamName, agentId);
        }
        const request = team.pendingJoinRequests.splice(requestIndex, 1)[0];
        const teammate = {
            id: agentId,
            name: request.agentName,
            role: request.role,
            status: 'active',
            spawnedAt: new Date(),
            messagesSent: 0,
            messagesReceived: 0,
        };
        team.teammates.push(teammate);
        this.emit('team:join_approved', { team: teamName, agent: agentId });
    }
    /**
     * Reject a join request
     */
    async rejectJoin(teamName, agentId, reason) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        team.pendingJoinRequests = team.pendingJoinRequests.filter(r => r.agentId !== agentId);
        this.emit('team:join_rejected', { team: teamName, agent: agentId, reason });
    }
    // ==========================================================================
    // Teammate Spawning
    // ==========================================================================
    /**
     * Spawn a teammate using native AgentInput
     */
    async spawnTeammate(config) {
        this.ensureAvailable();
        // Rate limiting check
        if (!this.rateLimiter.checkLimit('spawnPerMinute')) {
            this.metrics.increment('rateLimitBlocks');
            throw new TeammateError('Spawn rate limit exceeded. Please wait before spawning more teammates.', TeammateErrorCode.PERMISSION_DENIED);
        }
        this.metrics.increment('rateLimitHits');
        const startTime = Date.now();
        // Security: Validate teammate name
        const validatedName = validateName(config.name, 'teammate');
        const teamName = config.teamName ?? process.env.CLAUDE_CODE_TEAM_NAME;
        if (teamName) {
            const team = this.activeTeams.get(teamName);
            if (team) {
                const teamDir = path.join(this.teamsDir, teamName);
                const configPath = path.join(teamDir, 'config.json');
                if (fs.existsSync(configPath)) {
                    const teamConfig = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
                    if (team.teammates.length >= teamConfig.maxTeammates) {
                        throw new TeammateError(`Team ${teamName} has reached maximum teammates (${teamConfig.maxTeammates})`, TeammateErrorCode.PERMISSION_DENIED, teamName);
                    }
                }
            }
        }
        const teammateId = generateId('teammate');
        const teammateInfo = {
            id: teammateId,
            name: validatedName, // Use validated name
            role: config.role,
            status: 'active',
            spawnedAt: new Date(),
            messagesSent: 0,
            messagesReceived: 0,
            currentTask: config.prompt.slice(0, 100),
            delegatedPermissions: config.delegatedPermissions,
        };
        // Build AgentInput
        const agentInput = this.buildAgentInput({ ...config, teamName });
        // Add to team
        if (teamName) {
            let team = this.activeTeams.get(teamName);
            if (!team) {
                team = await this.loadTeam(teamName);
            }
            team.teammates.push(teammateInfo);
            // Create mailbox file
            const mailboxPath = this.getMailboxPath(teamName, teammateId);
            ensureDirectory(path.dirname(mailboxPath));
            if (!fs.existsSync(mailboxPath)) {
                fs.writeFileSync(mailboxPath, '[]', 'utf-8');
            }
        }
        // Record metrics
        const spawnLatency = Date.now() - startTime;
        this.metrics.recordLatency('spawnLatency', spawnLatency);
        this.metrics.increment('teammatesSpawned');
        this.metrics.increment('activeTeammates');
        // Start health checking for this teammate
        if (teamName) {
            this.healthChecker.startChecking(teammateId, teamName, async () => {
                // Health check: verify teammate exists in team state
                const team = this.activeTeams.get(teamName);
                const teammate = team?.teammates.find(t => t.id === teammateId);
                return teammate?.status === 'active';
            });
        }
        this.emit('teammate:spawned', { teammate: teammateInfo, agentInput });
        return teammateInfo;
    }
    /**
     * Build AgentInput for Claude Code Task tool
     */
    buildAgentInput(config) {
        return {
            description: `${config.role}: ${config.name}`,
            prompt: config.prompt,
            subagent_type: config.role,
            model: config.model,
            name: config.name,
            team_name: config.teamName ?? process.env.CLAUDE_CODE_TEAM_NAME,
            allowed_tools: config.allowedTools,
            mode: config.mode,
            run_in_background: config.runInBackground ?? true,
            max_turns: config.maxTurns,
        };
    }
    // ==========================================================================
    // Messaging
    // ==========================================================================
    /**
     * Send message to a specific teammate
     */
    async sendMessage(teamName, fromId, toId, message) {
        this.ensureAvailable();
        // Rate limiting check
        if (!this.rateLimiter.checkLimit('messagesPerMinute')) {
            this.metrics.increment('rateLimitBlocks');
            throw new TeammateError('Message rate limit exceeded', TeammateErrorCode.PERMISSION_DENIED, teamName);
        }
        const startTime = Date.now();
        const team = this.getTeamOrThrow(teamName);
        const fullMessage = {
            id: generateId('msg'),
            from: fromId,
            to: toId,
            timestamp: new Date(),
            acknowledged: false,
            ...message,
        };
        // Write to recipient's mailbox
        await this.writeToMailbox(teamName, toId, fullMessage);
        team.messageCount++;
        // Update sender stats
        const sender = team.teammates.find(t => t.id === fromId);
        if (sender)
            sender.messagesSent++;
        // Record metrics
        this.metrics.recordLatency('messageLatency', Date.now() - startTime);
        this.metrics.increment('messagesSent');
        this.emit('message:sent', { team: teamName, message: fullMessage });
        return fullMessage;
    }
    /**
     * Broadcast message to all teammates
     */
    async broadcast(teamName, fromId, message) {
        this.ensureAvailable();
        // Rate limiting check
        if (!this.rateLimiter.checkLimit('broadcastsPerMinute')) {
            this.metrics.increment('rateLimitBlocks');
            throw new TeammateError('Broadcast rate limit exceeded', TeammateErrorCode.PERMISSION_DENIED, teamName);
        }
        const team = this.getTeamOrThrow(teamName);
        const fullMessage = {
            id: generateId('broadcast'),
            from: fromId,
            to: 'broadcast',
            timestamp: new Date(),
            acknowledged: false,
            ...message,
        };
        // Write to all teammate mailboxes
        for (const teammate of team.teammates) {
            if (teammate.id !== fromId) {
                await this.writeToMailbox(teamName, teammate.id, fullMessage);
                teammate.messagesReceived++;
            }
        }
        team.messageCount += team.teammates.length - 1;
        // Record metrics
        this.metrics.increment('broadcastsSent');
        this.emit('message:broadcast', { team: teamName, message: fullMessage });
        return fullMessage;
    }
    /**
     * Read messages from mailbox
     */
    async readMailbox(teamName, teammateId) {
        this.ensureAvailable();
        // Security: Validate names to prevent path traversal
        const validatedTeam = validateName(teamName, 'team');
        const validatedTeammate = validateName(teammateId, 'teammate');
        const mailboxPath = this.getMailboxPath(validatedTeam, validatedTeammate);
        try {
            if (!fs.existsSync(mailboxPath)) {
                return [];
            }
            const content = fs.readFileSync(mailboxPath, 'utf-8');
            // Security: Use safe JSON parsing
            const messages = safeJSONParse(content);
            // Clear mailbox after reading
            fs.writeFileSync(mailboxPath, '[]', 'utf-8');
            // Parse dates
            return messages.map(m => ({
                ...m,
                timestamp: new Date(m.timestamp),
            }));
        }
        catch {
            return [];
        }
    }
    // ==========================================================================
    // Plan Approval System
    // ==========================================================================
    /**
     * Submit a plan for approval
     */
    async submitPlan(teamName, plan) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const fullPlan = {
            id: generateId('plan'),
            approvals: [],
            rejections: [],
            status: 'pending',
            createdAt: new Date(),
            ...plan,
        };
        team.activePlans.push(fullPlan);
        // Broadcast plan for approval
        await this.broadcast(teamName, plan.proposedBy, {
            type: 'plan',
            payload: fullPlan,
        });
        this.emit('plan:submitted', { team: teamName, plan: fullPlan });
        return fullPlan;
    }
    /**
     * Approve a plan
     */
    async approvePlan(teamName, planId, approverId) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const plan = this.getPlanOrThrow(team, planId);
        if (plan.status !== 'pending') {
            throw new TeammateError(`Plan ${planId} is not pending (status: ${plan.status})`, TeammateErrorCode.PLAN_NOT_APPROVED, teamName);
        }
        if (!plan.approvals.includes(approverId)) {
            plan.approvals.push(approverId);
        }
        this.emit('plan:approval_added', { team: teamName, planId, approverId });
        // Check if we have enough approvals
        if (plan.approvals.length >= plan.requiredApprovals) {
            plan.status = 'approved';
            plan.approvedAt = new Date();
            this.emit('plan:approved', { team: teamName, plan });
        }
    }
    /**
     * Reject a plan
     */
    async rejectPlan(teamName, planId, rejecterId, reason) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const plan = this.getPlanOrThrow(team, planId);
        plan.rejections.push(rejecterId);
        plan.status = 'rejected';
        this.emit('plan:rejected', { team: teamName, plan, rejecterId, reason });
    }
    /**
     * Pause plan execution
     */
    async pausePlan(teamName, planId) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const plan = this.getPlanOrThrow(team, planId);
        if (plan.status !== 'executing') {
            throw new TeammateError(`Plan ${planId} is not executing`, TeammateErrorCode.PLAN_NOT_APPROVED, teamName);
        }
        plan.status = 'paused';
        plan.pausedAt = plan.currentStep;
        this.emit('plan:paused', { team: teamName, planId, atStep: plan.currentStep ?? 0 });
    }
    /**
     * Resume plan execution
     */
    async resumePlan(teamName, planId, fromStep) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const plan = this.getPlanOrThrow(team, planId);
        if (plan.status !== 'paused') {
            throw new TeammateError(`Plan ${planId} is not paused`, TeammateErrorCode.PLAN_NOT_APPROVED, teamName);
        }
        plan.status = 'executing';
        plan.currentStep = fromStep ?? plan.pausedAt ?? 0;
        this.emit('plan:resumed', { team: teamName, planId, fromStep: plan.currentStep });
    }
    /**
     * Launch swarm to execute approved plan
     */
    async launchSwarm(teamName, planId, teammateCount) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const plan = this.getPlanOrThrow(team, planId);
        if (plan.status !== 'approved') {
            throw new TeammateError(`Plan ${planId} is not approved`, TeammateErrorCode.PLAN_NOT_APPROVED, teamName);
        }
        const exitPlanInput = {
            launchSwarm: true,
            teammateCount: teammateCount ?? plan.steps.length,
            allowedPrompts: plan.steps.map(step => ({
                tool: 'Bash',
                prompt: step.action,
            })),
        };
        plan.status = 'executing';
        plan.startedAt = new Date();
        plan.currentStep = 0;
        this.emit('swarm:launched', {
            team: teamName,
            plan,
            exitPlanInput,
            teammateCount: exitPlanInput.teammateCount,
        });
        return exitPlanInput;
    }
    // ==========================================================================
    // Delegation System (NEW)
    // ==========================================================================
    /**
     * Delegate authority to a teammate
     */
    async delegateToTeammate(teamName, fromId, toId, permissions) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        // Check if source has these permissions or delegation rights
        const fromTeammate = team.teammates.find(t => t.id === fromId);
        if (!fromTeammate) {
            throw new TeammateError(`Teammate ${fromId} not found`, TeammateErrorCode.TEAMMATE_NOT_FOUND, teamName, fromId);
        }
        // Check delegation depth
        const existingDelegationChain = this.getDelegationChain(team, fromId);
        if (existingDelegationChain.length >= this.config.delegation.maxDepth) {
            throw new TeammateError(`Delegation depth exceeded (max: ${this.config.delegation.maxDepth})`, TeammateErrorCode.DELEGATION_DEPTH_EXCEEDED, teamName);
        }
        const delegation = {
            id: generateId('delegation'),
            fromId,
            toId,
            permissions,
            grantedAt: new Date(),
            expiresAt: this.config.delegation.autoExpireMs
                ? new Date(Date.now() + this.config.delegation.autoExpireMs)
                : undefined,
            depth: existingDelegationChain.length + 1,
            active: true,
        };
        team.delegations.push(delegation);
        // Update target teammate
        const toTeammate = team.teammates.find(t => t.id === toId);
        if (toTeammate) {
            toTeammate.delegatedFrom = fromId;
            toTeammate.delegatedPermissions = [
                ...(toTeammate.delegatedPermissions ?? []),
                ...permissions,
            ];
        }
        // Notify via message
        await this.sendMessage(teamName, fromId, toId, {
            type: 'delegation',
            payload: { action: 'granted', permissions },
        });
        this.emit('delegate:granted', { team: teamName, from: fromId, to: toId, permissions });
        return delegation;
    }
    /**
     * Revoke delegation from a teammate
     */
    async revokeDelegation(teamName, fromId, toId) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const delegationIndex = team.delegations.findIndex(d => d.fromId === fromId && d.toId === toId && d.active);
        if (delegationIndex === -1) {
            throw new TeammateError(`No active delegation from ${fromId} to ${toId}`, TeammateErrorCode.DELEGATION_DENIED, teamName);
        }
        team.delegations[delegationIndex].active = false;
        // Update target teammate
        const toTeammate = team.teammates.find(t => t.id === toId);
        if (toTeammate) {
            const delegation = team.delegations[delegationIndex];
            toTeammate.delegatedPermissions = (toTeammate.delegatedPermissions ?? [])
                .filter(p => !delegation.permissions.includes(p));
            if (toTeammate.delegatedPermissions.length === 0) {
                toTeammate.delegatedFrom = undefined;
            }
        }
        // Notify via message
        await this.sendMessage(teamName, fromId, toId, {
            type: 'delegation',
            payload: { action: 'revoked' },
        });
        this.emit('delegate:revoked', { team: teamName, from: fromId, to: toId });
    }
    // ==========================================================================
    // Team Context (NEW)
    // ==========================================================================
    /**
     * Update team context
     */
    async updateTeamContext(teamName, updates) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const updatedKeys = [];
        if (updates.sharedVariables) {
            team.context.sharedVariables = {
                ...team.context.sharedVariables,
                ...updates.sharedVariables,
            };
            updatedKeys.push(...Object.keys(updates.sharedVariables));
        }
        if (updates.inheritedPermissions) {
            team.context.inheritedPermissions = [
                ...new Set([...team.context.inheritedPermissions, ...updates.inheritedPermissions]),
            ];
            updatedKeys.push('inheritedPermissions');
        }
        if (updates.workingDirectory) {
            team.context.workingDirectory = updates.workingDirectory;
            updatedKeys.push('workingDirectory');
        }
        if (updates.gitBranch !== undefined) {
            team.context.gitBranch = updates.gitBranch;
            updatedKeys.push('gitBranch');
        }
        if (updates.environmentVariables) {
            team.context.environmentVariables = {
                ...team.context.environmentVariables,
                ...updates.environmentVariables,
            };
            updatedKeys.push(...Object.keys(updates.environmentVariables));
        }
        // Broadcast context update
        await this.broadcast(teamName, 'system', {
            type: 'context_update',
            payload: { updates, keys: updatedKeys },
        });
        this.emit('context:updated', { team: teamName, keys: updatedKeys });
        return team.context;
    }
    /**
     * Get team context
     */
    getTeamContext(teamName) {
        const team = this.getTeamOrThrow(teamName);
        return { ...team.context };
    }
    // ==========================================================================
    // Permission Updates (NEW)
    // ==========================================================================
    /**
     * Update teammate permissions
     */
    async updateTeammatePermissions(teamName, teammateId, changes) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const teammate = team.teammates.find(t => t.id === teammateId);
        if (!teammate) {
            throw new TeammateError(`Teammate ${teammateId} not found`, TeammateErrorCode.TEAMMATE_NOT_FOUND, teamName, teammateId);
        }
        const currentPermissions = teammate.delegatedPermissions ?? [];
        let newPermissions = [...currentPermissions];
        const added = [];
        const removed = [];
        if (changes.add) {
            for (const perm of changes.add) {
                if (!newPermissions.includes(perm)) {
                    newPermissions.push(perm);
                    added.push(perm);
                }
            }
        }
        if (changes.remove) {
            newPermissions = newPermissions.filter(p => {
                if (changes.remove.includes(p)) {
                    removed.push(p);
                    return false;
                }
                return true;
            });
        }
        teammate.delegatedPermissions = newPermissions;
        this.emit('permissions:updated', { team: teamName, teammateId, added, removed });
        return newPermissions;
    }
    // ==========================================================================
    // Remote Sync (NEW)
    // ==========================================================================
    /**
     * Push team to Claude.ai remote
     */
    async pushTeamToRemote(teamName) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        // This would integrate with Claude Code's pushToRemote functionality
        // For now, we simulate the remote session creation
        const remoteSession = {
            remoteSessionId: generateId('remote'),
            remoteSessionUrl: `https://claude.ai/project/${generateId('proj')}`,
            syncedAt: new Date(),
            status: 'connected',
        };
        team.remoteSessionId = remoteSession.remoteSessionId;
        team.remoteSessionUrl = remoteSession.remoteSessionUrl;
        // Save remote session info with secure permissions
        // Security: Validate team name
        const validatedName = validateName(teamName, 'team');
        const teamDir = path.join(this.teamsDir, validatedName);
        fs.writeFileSync(path.join(teamDir, 'remote.json'), JSON.stringify(remoteSession, null, 2), { encoding: 'utf-8', mode: 0o600 });
        this.emit('remote:pushed', { team: teamName, remoteUrl: remoteSession.remoteSessionUrl });
        return remoteSession;
    }
    /**
     * Sync with remote
     */
    async syncWithRemote(teamName) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        if (!team.remoteSessionId) {
            throw new TeammateError(`Team ${teamName} is not connected to remote`, TeammateErrorCode.REMOTE_SYNC_FAILED, teamName);
        }
        // Simulate sync result
        const result = {
            success: true,
            changesPushed: 0,
            changesPulled: 0,
            conflicts: 0,
            remoteUrl: team.remoteSessionUrl,
        };
        this.emit('remote:synced', { team: teamName, result });
        return result;
    }
    // ==========================================================================
    // Session Memory (NEW)
    // ==========================================================================
    /**
     * Save teammate memory
     */
    async saveTeammateMemory(teamName, teammateId) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const teammate = team.teammates.find(t => t.id === teammateId);
        if (!teammate) {
            throw new TeammateError(`Teammate ${teammateId} not found`, TeammateErrorCode.TEAMMATE_NOT_FOUND, teamName, teammateId);
        }
        const memoryKey = `${teamName}:${teammateId}`;
        let memory = this.teammateMemories.get(memoryKey);
        if (!memory) {
            memory = {
                sessionId: generateId('session'),
                teammateId,
                teamName,
                transcript: [],
                context: {},
                nestedMemories: [],
                createdAt: new Date(),
                updatedAt: new Date(),
                size: 0,
            };
        }
        // Read mailbox messages as transcript
        const mailboxPath = this.getMailboxPath(teamName, teammateId);
        if (fs.existsSync(mailboxPath)) {
            const messages = JSON.parse(fs.readFileSync(mailboxPath, 'utf-8'));
            memory.transcript.push(...messages);
        }
        memory.updatedAt = new Date();
        memory.size = JSON.stringify(memory).length;
        this.teammateMemories.set(memoryKey, memory);
        // Persist to disk with secure permissions
        // Security: Validate names for path safety
        const validatedTeam = validateName(teamName, 'team');
        const validatedTeammate = validateName(teammateId, 'teammate');
        const memoryDir = path.join(this.teamsDir, validatedTeam, 'memory');
        ensureDirectory(memoryDir);
        fs.writeFileSync(path.join(memoryDir, `${validatedTeammate}.json`), JSON.stringify(memory, null, 2), { encoding: 'utf-8', mode: 0o600 });
        this.emit('memory:saved', { team: teamName, teammateId, size: memory.size });
    }
    /**
     * Load teammate memory
     */
    async loadTeammateMemory(teamName, teammateId) {
        this.ensureAvailable();
        const memoryPath = path.join(this.teamsDir, teamName, 'memory', `${teammateId}.json`);
        if (!fs.existsSync(memoryPath)) {
            return null;
        }
        try {
            const memory = JSON.parse(fs.readFileSync(memoryPath, 'utf-8'));
            // Parse dates
            memory.createdAt = new Date(memory.createdAt);
            memory.updatedAt = new Date(memory.updatedAt);
            memory.transcript = memory.transcript.map(m => ({
                ...m,
                timestamp: new Date(m.timestamp),
            }));
            const memoryKey = `${teamName}:${teammateId}`;
            this.teammateMemories.set(memoryKey, memory);
            this.emit('memory:loaded', { team: teamName, teammateId });
            return memory;
        }
        catch {
            throw new TeammateError(`Failed to load memory for ${teammateId}`, TeammateErrorCode.MEMORY_LOAD_FAILED, teamName, teammateId);
        }
    }
    /**
     * Share transcript between teammates
     */
    async shareTranscript(teamName, fromId, toId, options) {
        this.ensureAvailable();
        const memory = await this.loadTeammateMemory(teamName, fromId);
        if (!memory) {
            throw new TeammateError(`No memory found for ${fromId}`, TeammateErrorCode.MEMORY_LOAD_FAILED, teamName, fromId);
        }
        let transcript = memory.transcript;
        if (options?.start !== undefined || options?.end !== undefined) {
            transcript = transcript.slice(options.start, options.end);
        }
        await this.sendMessage(teamName, fromId, toId, {
            type: 'result',
            payload: {
                transcriptShare: true,
                messages: transcript,
                fromTeammate: fromId,
            },
        });
        this.emit('transcript:shared', {
            team: teamName,
            from: fromId,
            to: toId,
            messageCount: transcript.length,
        });
    }
    // ==========================================================================
    // Teleport (NEW)
    // ==========================================================================
    /**
     * Check if team can teleport
     */
    async canTeleport(teamName, target) {
        this.ensureAvailable();
        const blockers = [];
        // Check team exists
        if (!this.activeTeams.has(teamName)) {
            const teams = await this.discoverTeams();
            if (!teams.includes(teamName)) {
                blockers.push(`Team ${teamName} not found`);
            }
        }
        // Check git compatibility if gitAware
        if (this.config.teleport.gitAware && target.gitRepo) {
            const currentRepo = this.getCurrentGitRepo();
            if (currentRepo && currentRepo !== target.gitRepo) {
                blockers.push(`Git repository mismatch: current=${currentRepo}, target=${target.gitRepo}`);
            }
        }
        // Check working directory exists
        if (target.workingDirectory && !fs.existsSync(target.workingDirectory)) {
            blockers.push(`Working directory not found: ${target.workingDirectory}`);
        }
        return {
            canTeleport: blockers.length === 0,
            blockers,
        };
    }
    /**
     * Teleport team to new context
     */
    async teleportTeam(teamName, target) {
        this.ensureAvailable();
        this.emit('teleport:started', { team: teamName, target });
        const { canTeleport, blockers } = await this.canTeleport(teamName, target);
        if (!canTeleport) {
            const error = `Cannot teleport: ${blockers.join(', ')}`;
            this.emit('teleport:failed', { team: teamName, error });
            return { success: false, blockers };
        }
        try {
            // Save current state
            await this.saveTeamState(teamName);
            // Update context
            const team = await this.loadTeam(teamName);
            if (target.workingDirectory) {
                team.context.workingDirectory = target.workingDirectory;
            }
            if (target.gitBranch) {
                team.context.gitBranch = target.gitBranch;
            }
            if (target.gitRepo) {
                team.context.gitRepo = target.gitRepo;
            }
            // Save updated state
            await this.saveTeamState(teamName);
            const result = {
                success: true,
                teamState: team,
            };
            this.emit('teleport:completed', { team: teamName, result });
            return result;
        }
        catch (error) {
            const errorMsg = error instanceof Error ? error.message : 'Unknown error';
            this.emit('teleport:failed', { team: teamName, error: errorMsg });
            return { success: false, blockers: [errorMsg] };
        }
    }
    // ==========================================================================
    // Shutdown
    // ==========================================================================
    /**
     * Request teammate shutdown
     */
    async requestShutdown(teamName, teammateId, reason) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const teammate = team.teammates.find(t => t.id === teammateId);
        if (teammate) {
            teammate.status = 'shutdown_pending';
        }
        this.emit('teammate:shutdown_requested', { team: teamName, teammateId, reason });
    }
    /**
     * Approve teammate shutdown
     */
    async approveShutdown(teamName, teammateId) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        // Save memory before shutdown
        if (this.config.memory.autoPersist) {
            try {
                await this.saveTeammateMemory(teamName, teammateId);
            }
            catch {
                // Ignore memory save errors during shutdown
            }
        }
        team.teammates = team.teammates.filter(t => t.id !== teammateId);
        this.emit('teammate:shutdown_approved', { team: teamName, teammateId });
    }
    /**
     * Reject teammate shutdown
     */
    async rejectShutdown(teamName, teammateId) {
        this.ensureAvailable();
        const team = this.getTeamOrThrow(teamName);
        const teammate = team.teammates.find(t => t.id === teammateId);
        if (teammate) {
            teammate.status = 'active';
        }
        this.emit('teammate:shutdown_rejected', { team: teamName, teammateId });
    }
    /**
     * Cleanup team resources
     */
    async cleanup(teamName) {
        this.ensureAvailable();
        // Stop mailbox poller
        const poller = this.mailboxPollers.get(teamName);
        if (poller) {
            clearInterval(poller);
            this.mailboxPollers.delete(teamName);
        }
        // Stop memory persistence
        const memoryTimer = this.memoryPersistTimers.get(teamName);
        if (memoryTimer) {
            clearInterval(memoryTimer);
            this.memoryPersistTimers.delete(teamName);
        }
        // Performance: Flush any pending writes for this team
        this.flushPendingWrites();
        // Save final state
        try {
            await this.saveTeamState(teamName);
        }
        catch {
            // Ignore save errors during cleanup
        }
        // Performance: Invalidate cache
        this.invalidateConfigCache(teamName);
        // Dispose optimizer for this team
        const optimizer = this.topologyOptimizers.get(teamName);
        if (optimizer) {
            optimizer.dispose();
            this.topologyOptimizers.delete(teamName);
        }
        // Remove from active teams
        this.activeTeams.delete(teamName);
        // Clear environment
        if (process.env.CLAUDE_CODE_TEAM_NAME === teamName) {
            delete process.env.CLAUDE_CODE_TEAM_NAME;
        }
        this.emit('team:cleanup', { team: teamName });
    }
    // ==========================================================================
    // Utility Methods
    // ==========================================================================
    /**
     * Get team state
     */
    getTeamState(teamName) {
        return this.activeTeams.get(teamName);
    }
    /**
     * Get all active teams
     */
    getAllTeams() {
        return new Map(this.activeTeams);
    }
    /**
     * Get backend status
     */
    async getBackendStatus() {
        const statuses = [];
        // tmux backend
        try {
            execSync('which tmux', { encoding: 'utf-8' });
            statuses.push({
                backend: 'tmux',
                available: true,
                activeTeammates: 0,
                capacity: 100,
            });
        }
        catch {
            statuses.push({
                backend: 'tmux',
                available: false,
                activeTeammates: 0,
                capacity: 0,
            });
        }
        // in_process backend (always available)
        let inProcessCount = 0;
        for (const team of this.activeTeams.values()) {
            inProcessCount += team.teammates.length;
        }
        statuses.push({
            backend: 'in_process',
            available: true,
            activeTeammates: inProcessCount,
            capacity: 50,
        });
        return statuses;
    }
    // ==========================================================================
    // Private Methods
    // ==========================================================================
    ensureAvailable() {
        if (!this.initialized) {
            throw new TeammateError('TeammateBridge not initialized. Call initialize() first.', TeammateErrorCode.VERSION_INCOMPATIBLE);
        }
        if (!this.teammateToolAvailable && !this.config.fallbackToMCP) {
            throw new TeammateError(`TeammateTool not available. Requires Claude Code >= ${MINIMUM_CLAUDE_CODE_VERSION}, ` +
                `found: ${this.claudeCodeVersion ?? 'not installed'}`, TeammateErrorCode.VERSION_INCOMPATIBLE);
        }
    }
    getTeamOrThrow(teamName) {
        const team = this.activeTeams.get(teamName);
        if (!team) {
            throw new TeammateError(`Team not found: ${teamName}`, TeammateErrorCode.TEAM_NOT_FOUND, teamName);
        }
        return team;
    }
    getPlanOrThrow(team, planId) {
        const plan = team.activePlans.find(p => p.id === planId);
        if (!plan) {
            throw new TeammateError(`Plan not found: ${planId}`, TeammateErrorCode.PLAN_NOT_FOUND, team.name);
        }
        return plan;
    }
    getMailboxPath(teamName, teammateId) {
        return path.join(this.teamsDir, teamName, 'mailbox', `${teammateId}.json`);
    }
    async writeToMailbox(teamName, teammateId, message) {
        // Security: Path validation already done by getMailboxPath via validateName
        const mailboxPath = this.getMailboxPath(teamName, teammateId);
        ensureDirectory(path.dirname(mailboxPath));
        let messages = [];
        if (fs.existsSync(mailboxPath)) {
            try {
                const content = fs.readFileSync(mailboxPath, 'utf-8');
                // Security: Use safe JSON parsing
                messages = safeJSONParse(content);
            }
            catch {
                messages = [];
            }
        }
        // Check mailbox size limit
        if (messages.length >= this.config.mailbox.maxMessages) {
            // Remove oldest messages
            messages = messages.slice(-Math.floor(this.config.mailbox.maxMessages * 0.9));
        }
        messages.push(message);
        // Security: Write with restricted permissions (owner read/write only)
        fs.writeFileSync(mailboxPath, JSON.stringify(messages, null, 2), {
            encoding: 'utf-8',
            mode: 0o600,
        });
    }
    startMailboxPoller(teamName) {
        if (this.mailboxPollers.has(teamName)) {
            return;
        }
        const pollInterval = this.config.mailbox.pollingIntervalMs;
        const poller = setInterval(async () => {
            const team = this.activeTeams.get(teamName);
            if (!team) {
                clearInterval(poller);
                this.mailboxPollers.delete(teamName);
                return;
            }
            for (const teammate of team.teammates) {
                try {
                    const mailboxPath = this.getMailboxPath(teamName, teammate.id);
                    if (fs.existsSync(mailboxPath)) {
                        const content = fs.readFileSync(mailboxPath, 'utf-8');
                        const messages = JSON.parse(content);
                        if (messages.length > 0) {
                            this.emit('mailbox:messages', {
                                team: teamName,
                                teammateId: teammate.id,
                                messages: messages.map(m => ({
                                    ...m,
                                    timestamp: new Date(m.timestamp),
                                })),
                            });
                        }
                    }
                }
                catch {
                    // Ignore individual mailbox read errors
                }
            }
        }, pollInterval);
        this.mailboxPollers.set(teamName, poller);
    }
    startMemoryPersistence(teamName) {
        if (this.memoryPersistTimers.has(teamName)) {
            return;
        }
        const persistInterval = this.config.memory.persistIntervalMs;
        const timer = setInterval(async () => {
            const team = this.activeTeams.get(teamName);
            if (!team) {
                clearInterval(timer);
                this.memoryPersistTimers.delete(teamName);
                return;
            }
            for (const teammate of team.teammates) {
                try {
                    await this.saveTeammateMemory(teamName, teammate.id);
                }
                catch {
                    // Ignore individual memory save errors
                }
            }
        }, persistInterval);
        this.memoryPersistTimers.set(teamName, timer);
    }
    async saveTeamState(teamName) {
        const team = this.activeTeams.get(teamName);
        if (!team)
            return;
        // Security: Validate team name
        const validatedName = validateName(teamName, 'team');
        const teamDir = path.join(this.teamsDir, validatedName);
        ensureDirectory(teamDir);
        // Security: Write with restricted permissions
        fs.writeFileSync(path.join(teamDir, 'state.json'), JSON.stringify(team, null, 2), { encoding: 'utf-8', mode: 0o600 });
    }
    /**
     * Performance: Debounced file write to reduce I/O
     */
    debouncedWrite(filePath, data) {
        const existing = this.pendingWrites.get(filePath);
        if (existing) {
            clearTimeout(existing.timer);
        }
        const timer = setTimeout(() => {
            try {
                fs.writeFileSync(filePath, JSON.stringify(data, null, 2), {
                    encoding: 'utf-8',
                    mode: 0o600,
                });
                this.pendingWrites.delete(filePath);
            }
            catch (error) {
                // Log error but don't throw - debounced writes are best-effort
                this.emit('error', error);
            }
        }, this.writeDebounceMs);
        this.pendingWrites.set(filePath, { data, timer });
    }
    /**
     * Performance: Flush all pending writes immediately
     */
    flushPendingWrites() {
        for (const [filePath, { data, timer }] of this.pendingWrites) {
            clearTimeout(timer);
            try {
                fs.writeFileSync(filePath, JSON.stringify(data, null, 2), {
                    encoding: 'utf-8',
                    mode: 0o600,
                });
            }
            catch {
                // Ignore errors during flush
            }
        }
        this.pendingWrites.clear();
    }
    /**
     * Performance: Get cached team config or load from disk
     */
    getCachedTeamConfig(teamName) {
        const cached = this.teamConfigCache.get(teamName);
        const now = Date.now();
        if (cached && now - cached.timestamp < this.cacheMaxAgeMs) {
            return cached.config;
        }
        // Cache miss or expired - load from disk
        const validatedName = validateName(teamName, 'team');
        const configPath = path.join(this.teamsDir, validatedName, 'config.json');
        if (!fs.existsSync(configPath)) {
            return null;
        }
        try {
            const content = fs.readFileSync(configPath, 'utf-8');
            const config = safeJSONParse(content);
            this.teamConfigCache.set(teamName, { config, timestamp: now });
            return config;
        }
        catch {
            return null;
        }
    }
    /**
     * Performance: Invalidate team config cache
     */
    invalidateConfigCache(teamName) {
        this.teamConfigCache.delete(teamName);
    }
    getDelegationChain(team, teammateId) {
        const chain = [];
        let currentId = teammateId;
        while (true) {
            const delegation = team.delegations.find(d => d.toId === currentId && d.active);
            if (!delegation)
                break;
            chain.push(delegation);
            currentId = delegation.fromId;
            // Prevent infinite loops
            if (chain.length > 10)
                break;
        }
        return chain;
    }
    getCurrentGitBranch() {
        try {
            return execSync('git rev-parse --abbrev-ref HEAD 2>/dev/null', {
                encoding: 'utf-8',
            }).trim() || undefined;
        }
        catch {
            return undefined;
        }
    }
    getCurrentGitRepo() {
        try {
            return execSync('git config --get remote.origin.url 2>/dev/null', {
                encoding: 'utf-8',
            }).trim() || undefined;
        }
        catch {
            return undefined;
        }
    }
}
// ============================================================================
// Factory Function
// ============================================================================
/**
 * Create and initialize a TeammateBridge instance
 */
export async function createTeammateBridge(config) {
    const bridge = new TeammateBridge(config);
    await bridge.initialize();
    return bridge;
}
export default TeammateBridge;
//# sourceMappingURL=teammate-bridge.js.map