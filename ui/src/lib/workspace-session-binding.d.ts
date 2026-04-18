import { ChatWorkspaceSession, RuntimeBindingMetadata } from '@/types/chat';
import { ModelInfo, ProviderInfo } from '@/types/providers';

export function modelsForProvider(models: ModelInfo[], providerId: string): ModelInfo[];

export function validateWorkspaceSessionBinding(
  session: ChatWorkspaceSession,
  providers: ProviderInfo[],
  models: ModelInfo[]
):
  | {
      valid: true;
      session: ChatWorkspaceSession;
      provider: ProviderInfo;
      model: ModelInfo;
    }
  | {
      valid: false;
      error: string;
    };

export function buildRuntimeMetadata(session: ChatWorkspaceSession): RuntimeBindingMetadata;
