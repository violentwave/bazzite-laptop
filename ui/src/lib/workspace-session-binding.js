/**
 * Workspace session binding helpers.
 * Keep runtime selection truthful between UI and request pipeline.
 * Includes project hydration state tracking.
 */

const BLOCKED_PROVIDER_STATUSES = new Set(['blocked', 'unavailable', 'not_configured']);
const HYDRATION_STATES = new Set(['selected', 'hydrating', 'hydrated', 'unavailable', 'invalid']);

function normalizeString(value) {
  return typeof value === 'string' ? value.trim() : '';
}

export function modelsForProvider(models, providerId) {
  const normalizedProvider = normalizeString(providerId);
  if (!normalizedProvider) {
    return [];
  }
  return (models || []).filter(
    (model) => model?.provider === normalizedProvider && model?.is_available !== false
  );
}

/**
 * Determine project hydration state based on project availability and binding status.
 * Returns canonical hydration state for UI rendering.
 */
export function getProjectHydrationState(projectId, projects, isBindingPending) {
  if (!projectId) {
    return 'selected'; // No project selected yet
  }
  
  if (isBindingPending) {
    return 'hydrating'; // Loading project metadata
  }
  
  const project = (projects || []).find((p) => p?.id === projectId);
  if (!project) {
    return 'unavailable'; // Project no longer exists
  }
  
  // Project found and fully loaded
  return 'hydrated';
}

export function validateWorkspaceSessionBinding(session, providers, models, projects) {
  const providerId = normalizeString(session?.provider);
  const modelId = normalizeString(session?.model);
  const mode = normalizeString(session?.mode);
  const projectId = normalizeString(session?.project_id);

  if (!mode) {
    return { valid: false, error: 'Select a workspace mode before sending.' };
  }

  const provider = (providers || []).find((item) => item?.id === providerId);
  if (!provider) {
    return {
      valid: false,
      error: providerId
        ? `Provider '${providerId}' is not available from live runtime discovery.`
        : 'Select a provider before sending.',
    };
  }

  if (BLOCKED_PROVIDER_STATUSES.has(provider.status)) {
    return {
      valid: false,
      error: `Provider '${provider.name || provider.id}' is ${provider.status} and cannot be used.`,
    };
  }

  if (!modelId) {
    return { valid: false, error: 'Select a model before sending.' };
  }

  const model = (models || []).find((item) => item?.id === modelId);
  if (!model) {
    return {
      valid: false,
      error: `Model '${modelId}' is not available from live provider runtime data.`,
    };
  }

  if (model.provider !== providerId) {
    return {
      valid: false,
      error: `Model '${model.id}' does not belong to provider '${providerId}'.`,
    };
  }

  if (model.is_available === false) {
    return {
      valid: false,
      error: `Model '${model.name || model.id}' is currently unavailable.`,
    };
  }

  return {
    valid: true,
    session: {
      ...session,
      provider: provider.id,
      model: model.id,
      mode,
      project_id: projectId,
    },
    provider,
    model,
  };
}

export function buildRuntimeMetadata(session, projects, projectHydrationState) {
  return {
    provider: normalizeString(session?.provider),
    model: normalizeString(session?.model),
    mode: normalizeString(session?.mode),
    project_id: normalizeString(session?.project_id),
    project_hydration_state: projectHydrationState || 'selected',
    memory_policy: normalizeString(session?.memory_policy),
    tool_policy: normalizeString(session?.tool_policy),
    attached_context_sources: Array.isArray(session?.attached_context_sources)
      ? session.attached_context_sources.filter((item) => typeof item === 'string' && item.trim())
      : [],
    bound_at: normalizeString(session?.bound_at),
  };
}

/**
 * Determine if a project context is degraded (unavailable or invalid).
 */
export function isProjectContextDegraded(hydrationState) {
  return hydrationState === 'unavailable' || hydrationState === 'invalid';
}
