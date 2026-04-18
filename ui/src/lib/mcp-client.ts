/**
 * MCP Bridge HTTP Client
 * Communicates with FastMCP streamable-http at 127.0.0.1:8766/mcp
 */

import { MCPResponse } from '@/types/chat';

const MCP_BRIDGE_URL = 'http://127.0.0.1:8766';
const MCP_ENDPOINT = `${MCP_BRIDGE_URL}/mcp`;
const MCP_RPC_TIMEOUT_MS = 10000;

let mcpSessionId: string | null = null;
let initializePromise: Promise<void> | null = null;
let rpcId = 1;

type JsonRpcMessage = {
  jsonrpc?: string;
  id?: number | string;
  result?: unknown;
  error?: { code?: number; message?: string; data?: unknown };
};

function nextRpcId(): number {
  rpcId += 1;
  return rpcId;
}

function buildHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    Accept: 'application/json, text/event-stream',
    'Content-Type': 'application/json',
  };
  if (mcpSessionId) {
    headers['mcp-session-id'] = mcpSessionId;
  }
  return headers;
}

function parseStreamableResponse(raw: string): JsonRpcMessage {
  const dataLines = raw
    .split('\n')
    .filter((line) => line.startsWith('data: '))
    .map((line) => line.slice(6).trim())
    .filter(Boolean);

  if (dataLines.length === 0) {
    throw new Error('MCP returned no data payload');
  }

  for (let i = dataLines.length - 1; i >= 0; i -= 1) {
    try {
      return JSON.parse(dataLines[i]) as JsonRpcMessage;
    } catch {
      // keep scanning backwards
    }
  }

  throw new Error('MCP returned unparseable payload');
}

async function initializeSession(): Promise<void> {
  if (mcpSessionId) {
    return;
  }
  if (initializePromise) {
    await initializePromise;
    return;
  }

  initializePromise = (async () => {
    const initId = nextRpcId();
    const initPayload = {
      jsonrpc: '2.0',
      id: initId,
      method: 'initialize',
      params: {
        protocolVersion: '2025-03-26',
        capabilities: {},
        clientInfo: {
          name: 'bazzite-console-ui',
          version: '0.1.0',
        },
      },
    };

    const initResponse = await fetch(MCP_ENDPOINT, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify(initPayload),
      signal: AbortSignal.timeout(MCP_RPC_TIMEOUT_MS),
    });

    if (!initResponse.ok) {
      const text = await initResponse.text();
      throw new Error(`MCP initialize failed (${initResponse.status}): ${text}`);
    }

    const sessionId = initResponse.headers.get('mcp-session-id');
    if (!sessionId) {
      throw new Error('MCP initialize did not return a session id');
    }
    mcpSessionId = sessionId;

    parseStreamableResponse(await initResponse.text());

    // Best-effort initialized notification (server may reply 202 empty)
    await fetch(MCP_ENDPOINT, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'notifications/initialized',
        params: {},
      }),
      signal: AbortSignal.timeout(MCP_RPC_TIMEOUT_MS),
    });
  })();

  try {
    await initializePromise;
  } finally {
    initializePromise = null;
  }
}

async function callRpc(method: string, params: Record<string, unknown>): Promise<unknown> {
  await initializeSession();

  const id = nextRpcId();
  const payload = {
    jsonrpc: '2.0',
    id,
    method,
    params,
  };

  const run = async (): Promise<unknown> => {
    const response = await fetch(MCP_ENDPOINT, {
      method: 'POST',
      headers: buildHeaders(),
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(MCP_RPC_TIMEOUT_MS),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`MCP ${method} failed (${response.status}): ${text}`);
    }

    const msg = parseStreamableResponse(await response.text());
    if (msg.error) {
      throw new Error(msg.error.message || `MCP ${method} returned an error`);
    }
    return msg.result;
  };

  try {
    return await run();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message.toLowerCase().includes('missing session id')) {
      mcpSessionId = null;
      await initializeSession();
      return run();
    }
    throw error;
  }
}

function parseToolContent(content: unknown): unknown {
  if (!Array.isArray(content) || content.length === 0) {
    return content;
  }

  const first = content[0] as { type?: string; text?: string };
  if (first.type !== 'text') {
    return content;
  }

  const text = first.text || '';
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function callMCPTool(
  toolName: string,
  params: Record<string, unknown> = {}
): Promise<unknown> {
  const result = (await callRpc('tools/call', {
    name: toolName,
    arguments: params,
  })) as { content?: unknown; isError?: boolean };

  const parsed = parseToolContent(result?.content);
  if (result?.isError) {
    throw new Error(
      typeof parsed === 'string' ? parsed : `Tool '${toolName}' returned an error`
    );
  }
  return parsed;
}

/**
 * Execute a tool via MCP Bridge (chat-compatible envelope)
 */
export async function executeTool(
  toolName: string,
  params: Record<string, unknown> = {}
): Promise<MCPResponse> {
  const startTime = performance.now();

  try {
    const result = await callMCPTool(toolName, params);
    return {
      success: true,
      result,
      duration: Math.round(performance.now() - startTime),
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      duration: Math.round(performance.now() - startTime),
    };
  }
}

/**
 * Get list of available tools from MCP Bridge
 */
export async function listTools(): Promise<string[]> {
  try {
    const result = (await callRpc('tools/list', {})) as {
      tools?: Array<{ name?: string }>;
    };
    return (result.tools || []).map((tool) => tool.name || '').filter(Boolean);
  } catch (error) {
    console.error('Failed to list MCP tools:', error);
    return [];
  }
}

/**
 * Check if MCP Bridge is available
 */
export async function checkMCPBridgeHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${MCP_BRIDGE_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Format tool result for display
 */
export function formatToolResult(result: unknown): string {
  if (typeof result === 'string') {
    return result;
  }
  
  if (result === null || result === undefined) {
    return 'No output';
  }
  
  // Try to format as JSON with indentation
  try {
    return JSON.stringify(result, null, 2);
  } catch {
    return String(result);
  }
}

/**
 * Parse tool calls from assistant message content
 * Looks for patterns like: <tool>tool_name(args)</tool>
 */
export function parseToolCalls(content: string): Array<{ name: string; args: Record<string, unknown> }> {
  const toolCalls: Array<{ name: string; args: Record<string, unknown> }> = [];
  
  // Match pattern: <tool>name({"arg": "value"})</tool>
  const toolRegex = /<tool>(\w+)\((.*?)\)<\/tool>/g;
  let match;
  
  while ((match = toolRegex.exec(content)) !== null) {
    const name = match[1];
    const argsStr = match[2];
    
    try {
      const args = argsStr ? JSON.parse(argsStr) : {};
      toolCalls.push({ name, args });
    } catch {
      // If JSON parsing fails, treat as string argument
      toolCalls.push({ name, args: { input: argsStr } });
    }
  }
  
  return toolCalls;
}
