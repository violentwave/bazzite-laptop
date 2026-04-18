/**
 * LLM Proxy Client
 * Streams responses from LLM Proxy at 127.0.0.1:8767
 */

import { Message } from '@/types/chat';

const LLM_PROXY_URL = 'http://127.0.0.1:8767/v1/chat/completions';

interface LLMRequestBody {
  model: string;
  messages: Array<{
    role: 'user' | 'assistant' | 'system';
    content: string;
  }>;
  stream: boolean;
  temperature?: number;
  max_tokens?: number;
}

interface RuntimeBindingOptions {
  threadId?: string;
  projectId?: string;
  mode?: string;
  provider?: string;
  model?: string;
  memoryPolicy?: string;
  toolPolicy?: string;
  attachedContextSources?: string[];
}

interface StreamCallbacks {
  onChunk: (chunk: string) => void;
  onComplete: (fullResponse: string) => void;
  onError: (error: Error) => void;
  onToolCall?: (toolName: string, args: Record<string, unknown>) => void;
}

/**
 * Stream a chat completion from LLM Proxy
 */
export async function streamChatCompletion(
  messages: Message[],
  callbacks: StreamCallbacks,
  options: {
    model?: string;
    temperature?: number;
    maxTokens?: number;
    runtimeBinding?: RuntimeBindingOptions;
  } = {}
): Promise<() => void> {
  const { model = 'fast', temperature = 0.7, maxTokens = 4096, runtimeBinding } = options;
  
  // Convert messages to OpenAI format
  const formattedMessages = messages.map((msg) => ({
    role: msg.role === 'tool' ? 'assistant' : msg.role,
    content: msg.content,
  }));

  const requestBody: LLMRequestBody = {
    model,
    messages: formattedMessages,
    stream: true,
    temperature,
    max_tokens: maxTokens,
  };

  const abortController = new AbortController();
  let fullResponse = '';

  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (runtimeBinding?.provider) headers['x-bazzite-provider'] = runtimeBinding.provider;
    if (runtimeBinding?.mode) headers['x-bazzite-mode'] = runtimeBinding.mode;
    if (runtimeBinding?.projectId) headers['x-bazzite-project-id'] = runtimeBinding.projectId;
    if (runtimeBinding?.threadId) headers['x-bazzite-thread-id'] = runtimeBinding.threadId;
    if (runtimeBinding?.memoryPolicy) headers['x-bazzite-memory-policy'] = runtimeBinding.memoryPolicy;
    if (runtimeBinding?.toolPolicy) headers['x-bazzite-tool-policy'] = runtimeBinding.toolPolicy;

    const response = await fetch(LLM_PROXY_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestBody),
      signal: abortController.signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`LLM Proxy error: ${response.status} - ${errorText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    // Process the stream
    const processStream = async () => {
      const decoder = new TextDecoder();
      
      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            callbacks.onComplete(fullResponse);
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              
              // Stream done marker
              if (data === '[DONE]') {
                callbacks.onComplete(fullResponse);
                return;
              }

              try {
                const parsed = JSON.parse(data);
                const content = parsed.choices?.[0]?.delta?.content || '';
                
                if (content) {
                  fullResponse += content;
                  callbacks.onChunk(content);
                }

                // Check for tool calls in the response
                const toolCalls = parsed.choices?.[0]?.delta?.tool_calls;
                if (toolCalls && callbacks.onToolCall) {
                  for (const toolCall of toolCalls) {
                    if (toolCall.function?.name) {
                      callbacks.onToolCall(
                        toolCall.function.name,
                        JSON.parse(toolCall.function.arguments || '{}')
                      );
                    }
                  }
                }
              } catch {
                // Ignore parse errors for incomplete chunks
              }
            }
          }
        }
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          callbacks.onError(error);
        }
      } finally {
        reader.releaseLock();
      }
    };

    processStream();

    // Return abort function
    return () => {
      abortController.abort();
    };
  } catch (error) {
    callbacks.onError(error instanceof Error ? error : new Error(String(error)));
    return () => {};
  }
}

/**
 * Non-streaming chat completion (for simple queries)
 */
export async function chatCompletion(
  messages: Message[],
  options: {
    model?: string;
    temperature?: number;
    maxTokens?: number;
  } = {}
): Promise<string> {
  const { model = 'fast', temperature = 0.7, maxTokens = 4096 } = options;
  
  const formattedMessages = messages.map((msg) => ({
    role: msg.role === 'tool' ? 'assistant' : msg.role,
    content: msg.content,
  }));

  const requestBody: LLMRequestBody = {
    model,
    messages: formattedMessages,
    stream: false,
    temperature,
    max_tokens: maxTokens,
  };

  const response = await fetch(LLM_PROXY_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`LLM Proxy error: ${response.status} - ${errorText}`);
  }

  const result = await response.json();
  return result.choices?.[0]?.message?.content || '';
}

/**
 * Check if LLM Proxy is available
 */
export async function checkLLMProxyHealth(): Promise<boolean> {
  try {
    const response = await fetch('http://127.0.0.1:8767/health', {
      method: 'GET',
      signal: AbortSignal.timeout(5000),
    });
    return response.ok;
  } catch {
    return false;
  }
}
