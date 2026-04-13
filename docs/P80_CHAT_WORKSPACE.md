# P80 — Chat Workspace

**Status**: Complete  
**Dependencies**: P79  
**Risk Tier**: High  
**Backend**: opencode  

## Objective

Implement the primary AI interaction surface for the Bazzite Control Console. Create a fully functional chat workspace with real-time streaming, markdown rendering, inline tool results, file upload, and conversation management.

## Summary / Scope

This phase delivers the Chat Workspace — the core interaction surface for AI assistance. The implementation includes real-time streaming from LLM Proxy, MCP tool execution with inline results, markdown rendering with syntax highlighting, file upload with drag-drop, and conversation state management.

**Key Features**:
- Real-time streaming chat with SSE (Server-Sent Events)
- Markdown rendering with code syntax highlighting
- Inline tool execution and result display
- File upload with drag-drop support
- Welcome screen with suggestion prompts
- Motion-safe animations throughout

## Technical Stack

### Dependencies Added
```json
{
  "react-markdown": "^9.0.0",
  "remark-gfm": "^4.0.0",
  "rehype-highlight": "^7.0.0",
  "uuid": "^9.0.0",
  "@types/uuid": "^9.0.0"
}
```

### Architecture Decisions

**Why Not Vercel AI SDK?**
- Adds ~50KB+ bundle size
- LLM Proxy already provides OpenAI-compatible API
- Direct fetch with streaming gives more control
- Consistent with existing Python backend architecture

**Why react-markdown?**
- Battle-tested security (XSS protection)
- Plugin ecosystem (GFM, syntax highlighting)
- Customizable components
- Maintained by reputable team

**Why SSE over WebSockets?**
- LLM Proxy uses HTTP streaming
- Simpler connection management
- Works with existing infrastructure
- No additional server needed

## Implementation

### Files Created

#### Types (`ui/src/types/chat.ts`)
- `Message` — Chat message with role, content, attachments, tool calls
- `ToolCall` — Tool execution with status and result
- `ToolResult` — Tool output with duration and error
- `Attachment` — File attachment with preview support
- `Conversation` — Full conversation with messages and metadata
- `TokenUsage` — Token counting for cost tracking
- `ContextPin` — Pinned context items
- `MCPRequest/MCPResponse` — MCP communication types

#### Library (`ui/src/lib/`)
- `mcp-client.ts` — HTTP client for MCP Bridge (:8766)
  - `executeTool()` — Execute MCP tool with error handling
  - `listTools()` — Get available tools
  - `checkMCPBridgeHealth()` — Health check
  - `formatToolResult()` — Format result for display
  - `parseToolCalls()` — Parse tool calls from content

- `llm-client.ts` — HTTP client for LLM Proxy (:8767)
  - `streamChatCompletion()` — Stream responses with SSE
  - `chatCompletion()` — Non-streaming completion
  - `checkLLMProxyHealth()` — Health check

#### Hooks (`ui/src/hooks/`)
- `useChat.ts` — Core chat state management
  - Message sending and receiving
  - Streaming state tracking
  - File attachment management
  - Tool execution orchestration
  - Auto-scroll to bottom

#### Components (`ui/src/components/chat/`)
- `ChatContainer.tsx` — Main chat panel with message list and input
- `ChatMessage.tsx` — Individual message with user/assistant/tool variants
- `ChatInput.tsx` — Message input with drag-drop file upload
- `ToolResultCard.tsx` — Collapsible tool execution results
- `index.ts` — Component exports

### Component Details

#### ChatMessage Variants

**User Message**:
- Right-aligned
- Background: `--base-03` (#1a1a25)
- Border-radius: 8px (top-right reduced)
- Max-width: 80%
- Supports file attachments

**Assistant Message**:
- Left-aligned
- Transparent background with left accent border
- Max-width: 90%
- Markdown rendering with:
  - Syntax-highlighted code blocks
  - Tables, lists, links
  - Inline code styling
- Live streaming indicator

**Tool Message**:
- Inline within assistant message or standalone
- Shows `ToolResultCard` for each tool call

#### ToolResultCard
- Collapsible header with status icon
- Shows tool name, status (pending/success/error), duration
- Expandable content with arguments and result
- Color-coded status:
  - Success: Green border and icon
  - Error: Red border and icon
  - Pending: Amber border with spinner

#### ChatInput
- Auto-resizing textarea (max 200px)
- Drag-drop file upload with glass overlay
- File attachment chips with remove button
- Send/Stop button based on streaming state
- Keyboard shortcuts (Enter to send, Shift+Enter for newline)
- File validation (max 10MB)

#### ChatContainer
- Welcome screen with suggestion prompts
- Message list with smooth scroll
- Streaming indicator with typewriter cursor
- Error display with retry option
- Auto-scroll to new messages

### Design Compliance

All components follow P78 Midnight Glass specifications:

**Colors**:
- Base backgrounds: `--base-00` through `--base-03`
- Text hierarchy: `--text-primary`, `--text-secondary`, `--text-tertiary`
- Accents: `--accent-primary` (indigo), `--live-cyan` for streaming
- States: `--success`, `--warning`, `--danger`

**Typography**:
- Inter for UI text
- JetBrains Mono for code
- P78 type scale (xs through xl)

**Motion**:
- `motion-safe` wrapper on all animations
- Message entrance: 200ms fade + slide
- Welcome screen: Staggered 50ms delays
- Streaming: Pulse animation on cursor
- Respects `prefers-reduced-motion`

**Layout**:
- Full-height flex container
- Max-width 3xl for message content (768px)
- Responsive padding
- Proper overflow handling

## Integration

### Backend Communication

**MCP Bridge** (`http://127.0.0.1:8766`):
```typescript
// Execute tool
const result = await executeTool('security.status', {});
// Returns: { success, result, duration, error }
```

**LLM Proxy** (`http://127.0.0.1:8767/v1/chat/completions`):
```typescript
// Stream completion
await streamChatCompletion(messages, {
  onChunk: (chunk) => { /* update UI */ },
  onComplete: (fullText) => { /* finalize */ },
  onError: (error) => { /* handle error */ },
});
```

### Shell Integration

Updated `page.tsx` to render `ChatContainer` when `activePanel === 'chat'`:
```typescript
{activePanel === "chat" ? (
  <ChatContainer />
) : (
  <PanelContent panel={activePanel} />
)}
```

## File Structure

```
ui/src/
├── components/
│   └── chat/
│       ├── index.ts
│       ├── ChatContainer.tsx    # 300 lines
│       ├── ChatMessage.tsx      # 380 lines
│       ├── ChatInput.tsx        # 380 lines
│       └── ToolResultCard.tsx   # 220 lines
├── hooks/
│   └── useChat.ts               # 350 lines
├── lib/
│   ├── mcp-client.ts            # 150 lines
│   └── llm-client.ts            # 180 lines
├── types/
│   └── chat.ts                  # 110 lines
└── app/
    └── page.tsx                 # Updated for Chat integration
```

**Total New Code**: ~2,070 lines

## Validation Results

### TypeScript
```bash
cd ui && npx tsc --noEmit
```
✅ Clean (no errors)

### Dependencies
```bash
cd ui && npm install
```
✅ 104 packages added, 0 vulnerabilities

### Design Compliance
- ✅ Midnight Glass theme tokens used throughout
- ✅ `motion-safe` on all animations
- ✅ 200ms/300ms durations per P78
- ✅ Glass surfaces for overlays only
- ✅ Proper text hierarchy

## Usage

### Starting Development
```bash
cd ui
npm run dev
```

### Testing Chat
1. Open browser to `http://localhost:3000`
2. Click Chat icon in left rail
3. Type a message and press Enter
4. View streaming response from LLM
5. Try suggestions on welcome screen
6. Drag-drop a file onto the input

### Available Commands
- Type normally for chat
- Tools are executed automatically when detected
- Use Shift+Enter for multi-line messages
- Press Ctrl+K for command palette

## Deferred Features

| Feature | Phase | Reason |
|---------|-------|--------|
| Conversation history persistence | P83 | Requires backend storage |
| Conversation branching | P86 | Complex tree UI |
| Advanced search | P86 | Requires indexing |
| Voice input | P88 | Browser API complexity |
| Multi-modal (image analysis) | P82 | Model provider support |
| Context sidebar (full) | P85 | Panel integration needed |
| Message editing/deletion | P86 | UX complexity |
| Export conversations | P87 | File handling |

## Known Limitations

1. **Tool Execution**: Tools are executed automatically without user confirmation (acceptable for local-only use)
2. **File Upload**: Files are not persisted across reloads (in-memory only)
3. **Conversation History**: Not saved between sessions (P83)
4. **Mobile View**: Not optimized for mobile yet (P87)

## Troubleshooting

### Chat not responding
- Check LLM Proxy: `curl http://127.0.0.1:8767/health`
- Verify MCP Bridge: `curl http://127.0.0.1:8766/health`

### Tool execution failing
- Check tool name is correct
- Verify MCP Bridge has tool registered
- Check browser console for errors

### Streaming not working
- Ensure streaming is enabled in LLM Proxy config
- Check for CORS errors in browser
- Verify network connection to :8767

## Next Phase Ready

**P81 — Security Ops Center** can proceed immediately:
- Shell layout complete
- Panel routing functional
- Chat panel provides reference implementation

## References

- P77 — UI Architecture + Contracts Baseline
- P78 — Midnight Glass Design System
- P79 — Frontend Shell Bootstrap
- AGENT.md — System capabilities
- HANDOFF.md — Current session context

## Definition of Done

- [x] Real-time streaming chat implemented
- [x] Markdown rendering with syntax highlighting
- [x] Tool execution with inline results
- [x] File upload with drag-drop
- [x] Welcome screen with suggestions
- [x] Motion-safe animations
- [x] TypeScript types defined
- [x] MCP and LLM clients created
- [x] useChat hook for state management
- [x] All components following Midnight Glass design
- [x] TypeScript validation passing
- [x] P80 documentation created
- [x] HANDOFF.md updated

## Commit

```
SHA: <to be committed>
Message: P80: Chat Workspace with streaming, markdown, and tool integration
```
