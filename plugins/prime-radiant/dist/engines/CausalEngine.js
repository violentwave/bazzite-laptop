/**
 * Causal Engine - Do-Calculus Inference
 *
 * Implements causal inference using Pearl's do-calculus.
 * Supports interventional queries, confounder identification,
 * and backdoor path analysis.
 *
 * Based on: https://arxiv.org/abs/1305.5506 (Do-Calculus)
 */
/**
 * CausalEngine - WASM wrapper for causal inference operations
 */
export class CausalEngine {
    wasmModule = null;
    significanceThreshold = 0.1;
    constructor(wasmModule) {
        this.wasmModule = wasmModule ?? null;
    }
    /**
     * Set the WASM module after initialization
     */
    setWasmModule(module) {
        this.wasmModule = module;
    }
    /**
     * Perform causal inference using do-calculus
     *
     * @param intervention - Intervention specification
     * @returns CausalResult with effect estimation
     */
    async infer(intervention) {
        const { treatment, outcome, graph } = intervention;
        // Identify confounders using backdoor criterion
        const confounders = this.identifyConfounders(graph, treatment, outcome);
        // Find all backdoor paths
        const backdoorPaths = this.findBackdoorPaths(graph, treatment, outcome);
        // Check if intervention is valid (all backdoor paths blocked)
        const interventionValid = this.validateIntervention(graph, treatment, confounders);
        // Estimate causal effect
        const effect = await this.computeDoCalculus(graph, treatment, outcome);
        return {
            effect: effect.value,
            confounders,
            interventionValid,
            backdoorPaths
        };
    }
    /**
     * Compute causal effect using do-calculus
     * P(Y | do(X)) estimation
     *
     * @param graph - Causal graph
     * @param treatment - Treatment variable
     * @param outcome - Outcome variable
     * @returns CausalEffect with confidence
     */
    async computeDoCalculus(graph, treatment, outcome) {
        if (this.wasmModule) {
            // Convert graph to adjacency matrix for WASM
            const { adjMatrix, nodeIndex } = this.graphToAdjMatrix(graph);
            const treatmentIdx = nodeIndex.get(treatment);
            const outcomeIdx = nodeIndex.get(outcome);
            if (treatmentIdx === undefined || outcomeIdx === undefined) {
                return this.createCausalEffect(0, 0);
            }
            const effect = this.wasmModule.causal_estimate_effect(treatmentIdx, outcomeIdx, adjMatrix, graph.nodes.length);
            // Confidence based on graph structure
            const confidence = this.computeConfidence(graph, treatment, outcome);
            return this.createCausalEffect(effect, confidence);
        }
        // Pure JS implementation
        return this.computeEffectJS(graph, treatment, outcome);
    }
    /**
     * Identify confounders between treatment and outcome
     *
     * @param graph - Causal graph
     * @param treatment - Treatment variable
     * @param outcome - Outcome variable
     * @returns Array of confounder variable names
     */
    identifyConfounders(graph, treatment, outcome) {
        const confounders = [];
        const treatmentParents = this.getParents(graph, treatment);
        const outcomeAncestors = this.getAncestors(graph, outcome);
        // A confounder is a common cause of treatment and outcome
        for (const parent of treatmentParents) {
            if (outcomeAncestors.has(parent) ||
                this.hasPathTo(graph, parent, outcome, new Set([treatment]))) {
                confounders.push(parent);
            }
        }
        // Also check for any node that causes both
        for (const node of graph.nodes) {
            if (node === treatment || node === outcome)
                continue;
            const causesT = this.hasPathTo(graph, node, treatment, new Set());
            const causesO = this.hasPathTo(graph, node, outcome, new Set([treatment]));
            if (causesT && causesO && !confounders.includes(node)) {
                confounders.push(node);
            }
        }
        return confounders;
    }
    /**
     * Find all backdoor paths from treatment to outcome
     *
     * @param graph - Causal graph
     * @param treatment - Treatment variable
     * @param outcome - Outcome variable
     * @returns Array of paths (each path is array of node names)
     */
    findBackdoorPaths(graph, treatment, outcome) {
        const backdoorPaths = [];
        const treatmentParents = this.getParents(graph, treatment);
        // Find all paths from parents of treatment to outcome
        for (const parent of treatmentParents) {
            const paths = this.findAllPaths(graph, parent, outcome, new Set([treatment]));
            for (const path of paths) {
                backdoorPaths.push([treatment, ...path]);
            }
        }
        return backdoorPaths;
    }
    /**
     * Create CausalEffect value object
     */
    createCausalEffect(value, confidence) {
        const clampedConfidence = Math.max(0, Math.min(1, confidence));
        let direction;
        if (value > this.significanceThreshold) {
            direction = 'positive';
        }
        else if (value < -this.significanceThreshold) {
            direction = 'negative';
        }
        else {
            direction = 'neutral';
        }
        return {
            value,
            confidence: clampedConfidence,
            significant: Math.abs(value) > this.significanceThreshold && clampedConfidence > 0.8,
            direction
        };
    }
    /**
     * Validate if an intervention is valid (backdoor criterion satisfied)
     */
    validateIntervention(graph, treatment, confounders) {
        // Intervention is valid if we can block all confounding paths
        // by conditioning on a sufficient set
        // Check if confounders form an adjustment set
        // (no descendant of treatment that is also an ancestor of outcome)
        const treatmentDescendants = this.getDescendants(graph, treatment);
        for (const confounder of confounders) {
            if (treatmentDescendants.has(confounder)) {
                // Confounder is a descendant of treatment - invalid adjustment
                return false;
            }
        }
        return true;
    }
    /**
     * Pure JS implementation of causal effect estimation
     */
    async computeEffectJS(graph, treatment, outcome) {
        // Check if there's a direct path from treatment to outcome
        const hasDirect = this.hasDirectEdge(graph, treatment, outcome);
        // Check for indirect paths
        const indirectPaths = this.findAllPaths(graph, treatment, outcome, new Set());
        // Compute effect based on path structure
        let effect = 0;
        if (hasDirect) {
            effect += 0.5; // Direct effect contribution
        }
        // Indirect effects (simplified - each path contributes)
        effect += Math.min(indirectPaths.length * 0.1, 0.5);
        // Adjust for confounders
        const confounders = this.identifyConfounders(graph, treatment, outcome);
        const confoundingBias = confounders.length * 0.1;
        effect = Math.max(0, effect - confoundingBias);
        const confidence = this.computeConfidence(graph, treatment, outcome);
        return this.createCausalEffect(effect, confidence);
    }
    /**
     * Compute confidence based on graph structure
     */
    computeConfidence(graph, treatment, outcome) {
        // Higher confidence when:
        // 1. Direct connection exists
        // 2. Fewer confounders
        // 3. Shorter paths
        let confidence = 0.5;
        if (this.hasDirectEdge(graph, treatment, outcome)) {
            confidence += 0.3;
        }
        const confounders = this.identifyConfounders(graph, treatment, outcome);
        confidence -= confounders.length * 0.1;
        const paths = this.findAllPaths(graph, treatment, outcome, new Set());
        if (paths.length > 0) {
            const avgPathLength = paths.reduce((sum, p) => sum + p.length, 0) / paths.length;
            confidence += Math.max(0, 0.2 - avgPathLength * 0.05);
        }
        return Math.max(0, Math.min(1, confidence));
    }
    /**
     * Convert graph to adjacency matrix
     */
    graphToAdjMatrix(graph) {
        const n = graph.nodes.length;
        const adjMatrix = new Float32Array(n * n);
        const nodeIndex = new Map();
        graph.nodes.forEach((node, idx) => {
            nodeIndex.set(node, idx);
        });
        for (const [from, to] of graph.edges) {
            const fromIdx = nodeIndex.get(from);
            const toIdx = nodeIndex.get(to);
            if (fromIdx !== undefined && toIdx !== undefined) {
                adjMatrix[fromIdx * n + toIdx] = 1;
            }
        }
        return { adjMatrix, nodeIndex };
    }
    /**
     * Get parent nodes (direct causes)
     */
    getParents(graph, node) {
        return graph.edges
            .filter(([, to]) => to === node)
            .map(([from]) => from);
    }
    /**
     * Get ancestors (all causes)
     */
    getAncestors(graph, node) {
        const ancestors = new Set();
        const queue = this.getParents(graph, node);
        while (queue.length > 0) {
            const current = queue.shift();
            if (!ancestors.has(current)) {
                ancestors.add(current);
                queue.push(...this.getParents(graph, current));
            }
        }
        return ancestors;
    }
    /**
     * Get descendants (all effects)
     */
    getDescendants(graph, node) {
        const descendants = new Set();
        const children = graph.edges
            .filter(([from]) => from === node)
            .map(([, to]) => to);
        const queue = [...children];
        while (queue.length > 0) {
            const current = queue.shift();
            if (!descendants.has(current)) {
                descendants.add(current);
                const nextChildren = graph.edges
                    .filter(([from]) => from === current)
                    .map(([, to]) => to);
                queue.push(...nextChildren);
            }
        }
        return descendants;
    }
    /**
     * Check if there's a direct edge from source to target
     */
    hasDirectEdge(graph, source, target) {
        return graph.edges.some(([from, to]) => from === source && to === target);
    }
    /**
     * Check if there's a path from source to target
     */
    hasPathTo(graph, source, target, blocked) {
        if (source === target)
            return true;
        const visited = new Set(blocked);
        const queue = [source];
        while (queue.length > 0) {
            const current = queue.shift();
            if (visited.has(current))
                continue;
            visited.add(current);
            const children = graph.edges
                .filter(([from]) => from === current)
                .map(([, to]) => to);
            for (const child of children) {
                if (child === target)
                    return true;
                if (!visited.has(child)) {
                    queue.push(child);
                }
            }
        }
        return false;
    }
    /**
     * Find all paths from source to target
     */
    findAllPaths(graph, source, target, blocked, currentPath = [], allPaths = []) {
        if (blocked.has(source))
            return allPaths;
        const newPath = [...currentPath, source];
        if (source === target) {
            allPaths.push(newPath);
            return allPaths;
        }
        const children = graph.edges
            .filter(([from]) => from === source)
            .map(([, to]) => to);
        const newBlocked = new Set(blocked);
        newBlocked.add(source);
        for (const child of children) {
            if (!blocked.has(child) && !currentPath.includes(child)) {
                this.findAllPaths(graph, child, target, newBlocked, newPath, allPaths);
            }
        }
        return allPaths;
    }
}
//# sourceMappingURL=CausalEngine.js.map