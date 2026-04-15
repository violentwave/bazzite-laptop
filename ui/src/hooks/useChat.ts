"use client";

import { useReducer, useCallback, useRef, useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Message, Conversation, Attachment, ContextPin, TokenUsage } from '@/types/chat';
import { streamChatCompletion } from '@/lib/llm-client';
import { checkLLMProxyHealth } from '@/lib/llm-client';
import { checkMCPBridgeHealth, executeTool, formatToolResult } from '@/lib/mcp-client';

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  attachedFiles: Attachment[];
  contextPins: ContextPin[];
  tokenUsage: TokenUsage;
  error: string | null;
  currentModel: string;
}

type ChatAction =
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'UPDATE_MESSAGE'; payload: { id: string; updates: Partial<Message> } }
  | { type: 'SET_STREAMING'; payload: boolean }
  | { type: 'SET_STREAMING_CONTENT'; payload: string }
  | { type: 'APPEND_STREAMING_CONTENT'; payload: string }
  | { type: 'CLEAR_STREAMING_CONTENT' }
  | { type: 'ADD_ATTACHMENT'; payload: Attachment }
  | { type: 'REMOVE_ATTACHMENT'; payload: string }
  | { type: 'ADD_CONTEXT_PIN'; payload: ContextPin }
  | { type: 'REMOVE_CONTEXT_PIN'; payload: string }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_MODEL'; payload: string }
  | { type: 'CLEAR_MESSAGES' };

const initialState: ChatState = {
  messages: [],
  isStreaming: false,
  streamingContent: '',
  attachedFiles: [],
  contextPins: [],
  tokenUsage: { input: 0, output: 0, total: 0 },
  error: null,
  currentModel: 'fast',
};

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'ADD_MESSAGE':
      return {
        ...state,
        messages: [...state.messages, action.payload],
      };
    case 'UPDATE_MESSAGE':
      return {
        ...state,
        messages: state.messages.map((msg) =>
          msg.id === action.payload.id ? { ...msg, ...action.payload.updates } : msg
        ),
      };
    case 'SET_STREAMING':
      return { ...state, isStreaming: action.payload };
    case 'SET_STREAMING_CONTENT':
      return { ...state, streamingContent: action.payload };
    case 'APPEND_STREAMING_CONTENT':
      return { ...state, streamingContent: state.streamingContent + action.payload };
    case 'CLEAR_STREAMING_CONTENT':
      return { ...state, streamingContent: '' };
    case 'ADD_ATTACHMENT':
      return {
        ...state,
        attachedFiles: [...state.attachedFiles, action.payload],
      };
    case 'REMOVE_ATTACHMENT':
      return {
        ...state,
        attachedFiles: state.attachedFiles.filter((f) => f.id !== action.payload),
      };
    case 'ADD_CONTEXT_PIN':
      return {
        ...state,
        contextPins: [...state.contextPins, action.payload],
      };
    case 'REMOVE_CONTEXT_PIN':
      return {
        ...state,
        contextPins: state.contextPins.filter((p) => p.id !== action.payload),
      };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_MODEL':
      return { ...state, currentModel: action.payload };
    case 'CLEAR_MESSAGES':
      return { ...state, messages: [] };
    default:
      return state;
  }
}

export function useChat() {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const abortControllerRef = useRef<(() => void) | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamingContentRef = useRef('');
  const assistantIdRef = useRef<string | null>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.messages, state.streamingContent]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() && state.attachedFiles.length === 0) return;

      const [llmHealthy, mcpHealthy] = await Promise.all([
        checkLLMProxyHealth(),
        checkMCPBridgeHealth(),
      ]);

      if (!llmHealthy) {
        dispatch({
          type: 'SET_ERROR',
          payload: 'LLM proxy unavailable. Ensure bazzite-llm-proxy.service is running on 127.0.0.1:8767.',
        });
        return;
      }

      if (!mcpHealthy) {
        dispatch({
          type: 'SET_ERROR',
          payload: 'MCP bridge unavailable. Tool execution will fail until bazzite-mcp-bridge.service is running on 127.0.0.1:8766.',
        });
      }

      // Create user message
      const userMessage: Message = {
        id: uuidv4(),
        role: 'user',
        content,
        timestamp: new Date(),
        attachments: state.attachedFiles.length > 0 ? [...state.attachedFiles] : undefined,
      };

      dispatch({ type: 'ADD_MESSAGE', payload: userMessage });
      dispatch({ type: 'SET_ERROR', payload: null });
      
      // Clear attachments after sending
      state.attachedFiles.forEach((file) => {
        dispatch({ type: 'REMOVE_ATTACHMENT', payload: file.id });
      });

      // Create placeholder for assistant message
      const assistantMessageId = uuidv4();
      assistantIdRef.current = assistantMessageId;
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };

      dispatch({ type: 'ADD_MESSAGE', payload: assistantMessage });
      dispatch({ type: 'SET_STREAMING', payload: true });
      dispatch({ type: 'CLEAR_STREAMING_CONTENT' });
      streamingContentRef.current = '';

      try {
        // Get all messages for context
        const allMessages = [...state.messages, userMessage];
        
        // Start streaming
        const abort = await streamChatCompletion(
          allMessages,
          {
            onChunk: (chunk) => {
              streamingContentRef.current += chunk;
              dispatch({ type: 'APPEND_STREAMING_CONTENT', payload: chunk });
            },
            onComplete: (fullResponse) => {
              streamingContentRef.current = '';
              dispatch({ type: 'SET_STREAMING', payload: false });
              dispatch({
                type: 'UPDATE_MESSAGE',
                payload: {
                  id: assistantMessageId,
                  updates: {
                    content: fullResponse,
                    isStreaming: false,
                  },
                },
              });
              dispatch({ type: 'CLEAR_STREAMING_CONTENT' });
              
              // Check for tool calls in the response
              checkAndExecuteTools(fullResponse, assistantMessageId);
            },
            onError: (error) => {
              const partialContent = streamingContentRef.current;
              streamingContentRef.current = '';
              dispatch({ type: 'SET_STREAMING', payload: false });
              dispatch({
                type: 'UPDATE_MESSAGE',
                payload: {
                  id: assistantMessageId,
                  updates: {
                    content: partialContent || 'Error: Failed to get response',
                    isStreaming: false,
                    error: error.message,
                  },
                },
              });
              dispatch({ type: 'SET_ERROR', payload: error.message });
            },
            onToolCall: async (toolName, args) => {
              // Execute tool automatically
              await executeToolCall(toolName, args, assistantMessageId);
            },
          },
          { model: state.currentModel }
        );

        abortControllerRef.current = abort;
      } catch (error) {
        dispatch({ type: 'SET_STREAMING', payload: false });
        dispatch({
          type: 'UPDATE_MESSAGE',
          payload: {
            id: assistantMessageId,
            updates: {
              content: 'Error: Failed to start streaming',
              isStreaming: false,
              error: error instanceof Error ? error.message : 'Unknown error',
            },
          },
        });
      }
    },
    [state.messages, state.attachedFiles, state.currentModel]
  );

  const checkAndExecuteTools = useCallback(
    async (content: string, parentMessageId: string) => {
      // Check for explicit tool call syntax: <tool>name(args)</tool>
      const toolRegex = /<tool>(\w+)\((.*?)\)<\/tool>/g;
      let match;
      
      while ((match = toolRegex.exec(content)) !== null) {
        const toolName = match[1];
        const argsStr = match[2];
        
        try {
          const args = argsStr ? JSON.parse(argsStr) : {};
          await executeToolCall(toolName, args, parentMessageId);
        } catch {
          // Ignore parsing errors
        }
      }
    },
    []
  );

  const executeToolCall = useCallback(
    async (toolName: string, args: Record<string, unknown>, parentMessageId: string) => {
      // Create tool message
      const toolMessage: Message = {
        id: uuidv4(),
        role: 'tool',
        content: `Running ${toolName}...`,
        timestamp: new Date(),
        toolCalls: [
          {
            id: uuidv4(),
            name: toolName,
            arguments: args,
            status: 'pending',
            timestamp: new Date(),
          },
        ],
      };

      dispatch({ type: 'ADD_MESSAGE', payload: toolMessage });

      // Execute the tool
      const result = await executeTool(toolName, args);

      // Update tool message with result
      dispatch({
        type: 'UPDATE_MESSAGE',
        payload: {
          id: toolMessage.id,
          updates: {
            content: result.success
              ? formatToolResult(result.result)
              : `Error: ${result.error}`,
            toolCalls: [
              {
                ...toolMessage.toolCalls![0],
                 result: {
                   output: (result.result as string | Record<string, unknown>) || result.error || 'No output',
                   duration: result.duration,
                   error: result.error,
                 },
                status: result.success ? 'success' : 'error',
              },
            ],
          },
        },
      });

      return result;
    },
    []
  );

  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current();
      abortControllerRef.current = null;
    }
    // Finalize the current assistant message with whatever content was streamed
    const partialContent = streamingContentRef.current;
    if (partialContent && assistantIdRef.current) {
      dispatch({
        type: 'UPDATE_MESSAGE',
        payload: {
          id: assistantIdRef.current,
          updates: {
            content: partialContent,
            isStreaming: false,
          },
        },
      });
      streamingContentRef.current = '';
      assistantIdRef.current = null;
    }
    dispatch({ type: 'SET_STREAMING', payload: false });
    dispatch({ type: 'CLEAR_STREAMING_CONTENT' });
  }, []);

  const addAttachment = useCallback((file: File) => {
    const attachment: Attachment = {
      id: uuidv4(),
      name: file.name,
      type: file.type,
      size: file.size,
    };

    // For images, create a preview
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        attachment.previewUrl = e.target?.result as string;
        dispatch({ type: 'ADD_ATTACHMENT', payload: attachment });
      };
      reader.readAsDataURL(file);
    } else {
      dispatch({ type: 'ADD_ATTACHMENT', payload: attachment });
    }
  }, []);

  const removeAttachment = useCallback((id: string) => {
    dispatch({ type: 'REMOVE_ATTACHMENT', payload: id });
  }, []);

  const clearMessages = useCallback(() => {
    dispatch({ type: 'CLEAR_MESSAGES' });
  }, []);

  const setModel = useCallback((model: string) => {
    dispatch({ type: 'SET_MODEL', payload: model });
  }, []);

  return {
    messages: state.messages,
    isStreaming: state.isStreaming,
    streamingContent: state.streamingContent,
    attachedFiles: state.attachedFiles,
    contextPins: state.contextPins,
    tokenUsage: state.tokenUsage,
    error: state.error,
    currentModel: state.currentModel,
    sendMessage,
    stopGeneration,
    addAttachment,
    removeAttachment,
    clearMessages,
    setModel,
    messagesEndRef,
  };
}
