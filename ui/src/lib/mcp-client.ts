/**
 * MCP Bridge HTTP Client
 * Communicates with MCP Bridge at 127.0.0.1:8766
 */

import { MCPRequest, MCPResponse } from '@/types/chat';

const MCP_BRIDGE_URL = 'http://127.0.0.1:8766';

interface MCPBridgePayload {
  name: string;
  arguments?: Record<string, unknown>;
}

/**
 * Execute a tool via MCP Bridge
 */
export async function executeTool(
  toolName: string,
  params: Record<string, unknown> = {}
): Promise<MCPResponse> {
  const startTime = performance.now();
  
  try {
    // MCP Bridge uses a simplified JSON-RPC-like interface
    const payload: MCPBridgePayload = {
      name: toolName,
      arguments: params,
    };

    const response = await fetch(`${MCP_BRIDGE_URL}/tools/call`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`MCP Bridge error: ${response.status} - ${errorText}`);
    }

    const result = await response.json();
    const duration = performance.now() - startTime;

    return {
      success: true,
      result: result,
      duration: Math.round(duration),
    };
  } catch (error) {
    const duration = performance.now() - startTime;
    
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      duration: Math.round(duration),
    };
  }
}

/**
 * Get list of available tools from MCP Bridge
 */
export async function listTools(): Promise<string[]> {
  try {
    const response = await fetch(`${MCP_BRIDGE_URL}/tools/list`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to list tools: ${response.status}`);
    }

    const result = await response.json();
    return result.tools || [];
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
