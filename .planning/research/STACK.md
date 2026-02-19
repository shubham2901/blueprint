# Stack Research

**Domain:** PM prototyping tool — Figma import, chat-driven iteration, live React preview  
**Project:** Blueprint PM  
**Researched:** 2025-02-19  
**Confidence:** HIGH (Figma, Sandpack, AI SDK verified via official docs); MEDIUM (Figma-to-React pipeline)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Next.js** | 16.x (existing) | Frontend, pages, API routes | Already in monorepo. No change. |
| **FastAPI** | ≥0.115 (existing) | Backend, chat endpoint, Figma proxy | Already in monorepo. Handles OAuth callback, LLM streaming, Figma API proxy. |
| **Supabase** | ≥2.11 (existing) | Postgres, session persistence | Already in monorepo. Use for PM sessions, OAuth tokens. |
| **Figma REST API** | v1 | File JSON, node export, image render | Official API. OAuth 2 recommended for user-scoped access. `GET /v1/files/:key`, `GET /v1/files/:key/nodes`, `GET /v1/images/:key` cover frame import. |
| **Sandpack** | @codesandbox/sandpack-react ^2.20 | In-browser React preview | Industry standard for live code preview. React 19 support. Use **vanilla React** template — commercial-safe (Apache 2.0). Avoid Nodebox/Vite/Next.js templates (Sustainable Use License restricts commercial use). |
| **Vercel AI SDK** | ai ^6.x, @ai-sdk/react ^3.x | Streaming chat UI | `useChat` + `TextStreamChatTransport` or Data Stream Protocol. Works with FastAPI backend. Provider-agnostic. |

### Figma Integration

| Component | Technology | Purpose | Why |
|-----------|------------|---------|-----|
| **OAuth 2** | Figma OAuth app | User auth for file access | Required for `file_content:read`. Personal tokens have rate limits (Nov 2025). Use `file_content:read`, `file_metadata:read` scopes. |
| **File fetch** | `GET /v1/files/:key?ids=...` | Document tree for selected frame | Returns JSON with nodes, components, styles. |
| **Image export** | `GET /v1/images/:key?ids=...&format=png` | Rendered frame as image | For LLM vision input or fallback preview. PNG/JPG/SVG supported. |
| **Python client** | `httpx` (existing) or `figmapy` | REST calls from FastAPI | `figmapy` is unofficial but simplifies file/image calls. Alternative: raw `httpx` with Bearer token. |

### Figma-to-React Code Generation

| Component | Technology | Purpose | Why |
|-----------|------------|---------|-----|
| **Design context** | Figma REST API JSON + optional image | Input to LLM | File JSON + `geometry=paths` for vector data. Optionally `GET /v1/images/:key` for screenshot. |
| **LLM** | litellm (existing) | Code generation | Already in monorepo. Use structured output (Pydantic) for React/JSX. Vision models (GPT-4o, Claude, Gemini) can use frame screenshot. |
| **Prompt strategy** | System prompt + few-shot | Reliable React output | Instruct: Tailwind + functional components. No Builder.io — DIY keeps control and avoids vendor lock-in. |

### Streaming Chat

| Component | Technology | Purpose | Why |
|-----------|------------|---------|-----|
| **Frontend** | `useChat` from `@ai-sdk/react` | Chat state, streaming UI | Handles messages, status, errors. Use `TextStreamChatTransport` pointing to FastAPI `/api/pm/chat`. |
| **Backend** | litellm streaming + SSE | Stream tokens to client | litellm `acompletion(..., stream=True)` yields chunks. Format as Text Stream Protocol (plain text) or Data Stream Protocol (SSE JSON). Text Stream is simpler for code-only output. |
| **Protocol** | Text Stream Protocol | Minimal integration | `useChat({ transport: new TextStreamChatTransport({ api: '/api/pm/chat' }) })`. Backend returns `Content-Type: text/plain; charset=utf-8` with raw text chunks. |

### In-Browser React Preview

| Component | Technology | Purpose | Why |
|-----------|------------|---------|-----|
| **Runtime** | Sandpack (vanilla React template) | Execute generated React in browser | No Nodebox — uses older runtime. Commercial use allowed under Apache 2.0. |
| **Template** | `react` (not `react-ts`, not `vite-react`) | Avoid licensing traps | `react` template is Nodebox-free. Vite/Next.js templates require commercial license from CodeSandbox. |
| **Dependencies** | Inline in Sandpack files | Tailwind, etc. | Sandpack supports `package.json` in template. Add `tailwindcss` if needed. |

---

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `ai` | ^6.0 | Core AI SDK types, stream helpers | Frontend `useChat` |
| `@ai-sdk/react` | ^3.x | `useChat`, transports | Frontend chat component |
| `@codesandbox/sandpack-react` | ^2.20 | SandpackProvider, SandpackPreview, SandpackCodeEditor | Preview panel |
| `figmapy` | latest | Python Figma REST wrapper | Optional; or use `httpx` directly |
| `litellm` | ≥1.55 (existing) | LLM calls, streaming | Backend code generation |

---

## Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Figma OAuth app | Test file access | Create at figma.com/developers/apps. Use private app for dev. |
| Supabase | OAuth token storage | Store `access_token`, `refresh_token` per user/session. |

---

## Installation

```bash
# Frontend (Blueprint PM)
cd frontend
npm install ai @ai-sdk/react @codesandbox/sandpack-react

# Backend (if using figmapy)
cd backend
pip install figmapy  # optional; httpx sufficient for REST
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| Sandpack (vanilla React) | StackBlitz WebContainers | If you need full Node.js (Vite, etc.) and can accept different API. WebContainers are free for open source. |
| Sandpack | iframe + external URL | If preview must run in isolated origin. Higher latency, more infra. |
| Vercel AI SDK useChat | Custom SSE + useState | If you need full control over protocol. More code, less DX. |
| Figma REST API | Figma MCP (remote) | MCP is for IDE agents (Cursor), not programmatic backend. Requires user context. REST is correct for server-side import. |
| litellm + manual stream format | ai-sdk-python | ai-sdk-python exists but FastAPI + litellm streaming is proven. Less new surface area. |
| DIY Figma→React | Builder.io Fusion | Fusion is commercial, vendor lock-in. DIY with LLM gives control, fits existing litellm stack. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Sandpack Nodebox templates** (Vite, Next.js, Astro, Node) | Sustainable Use License v1.0 restricts commercial use. | Vanilla `react` template. |
| **Figma Plugin API for import** | Runs in Figma desktop; PM tool runs in browser. | REST API from backend. |
| **Figma MCP for backend** | MCP is for AI agents in IDE; requires Figma desktop or remote MCP. Not for server-side import. | REST API. |
| **Builder.io / Anima / similar** | Commercial, opaque. | Figma REST + LLM. |
| **Personal Access Tokens for production** | Rate limited (Nov 2025). Single-account. | OAuth 2 per user. |
| **Raw fetch for chat** | No streaming UX helpers, manual state. | `useChat` from AI SDK. |
| **Google Custom Search for Figma** | N/A to this domain. | — |

---

## Stack Patterns by Variant

**If PM tool is internal-only (no public OAuth):**
- Use Figma **private OAuth app**. No Figma review. Same scopes.
- Use **personal access token** for early prototyping only; switch to OAuth before any multi-user use.

**If you need production-grade design-to-code:**
- Consider **Figma Dev Mode** or **Code Connect** for teams with existing design systems. Out of scope for V1 PM prototyping.

**If Sandpack vanilla React is too limited:**
- Contact CodeSandbox for **commercial license** for Nodebox templates.
- Or evaluate **StackBlitz WebContainers** (different API, full Node.js).

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `@codesandbox/sandpack-react` ^2.20 | React ^16.8, ^17, ^18, ^19 | Project uses React 19. |
| `ai` ^6.0 | `@ai-sdk/react` ^3.x | AI SDK 6 uses new transport API. |
| `litellm` ≥1.55 | `openai`, `anthropic`, `google-generative-ai` | Existing fallback chain. |
| Figma REST API v1 | OAuth 2, PAT | Use `file_content:read`; `file_metadata:read` for meta. |

---

## Confidence Levels

| Area | Level | Reason |
|------|-------|--------|
| Figma REST API | HIGH | Official docs, OAuth flow, file/image endpoints verified. |
| Sandpack (vanilla React) | HIGH | Apache 2.0, npm 2.20.0, React 19 support. Licensing for Nodebox templates confirmed. |
| Vercel AI SDK | HIGH | Official docs, useChat, Text Stream Protocol, FastAPI example. |
| Figma-to-React (LLM) | MEDIUM | Pattern is standard; quality depends on prompts. Builder.io is alternative but commercial. |
| litellm + stream format | MEDIUM | litellm streams; exact Text Stream Protocol formatting needs implementation check. |

---

## Sources

- [Figma REST API — Authentication](https://developers.figma.com/docs/rest-api/authentication/) — OAuth 2, scopes
- [Figma REST API — File Endpoints](https://developers.figma.com/docs/rest-api/file-endpoints/) — GET file, nodes, images
- [Sandpack — FAQ](https://sandpack.codesandbox.io/docs/resources/faq) — Licensing, Nodebox restrictions
- [Sandpack — npm](https://www.npmjs.com/package/@codesandbox/sandpack-react) — v2.20.0, React 19
- [Vercel AI SDK — Stream Protocol](https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol) — Text vs Data stream
- [Vercel AI SDK — useChat](https://sdk.vercel.ai/docs/reference/ai-sdk-ui/use-chat) — Transport, TextStreamChatTransport
- [AI SDK — npm](https://www.npmjs.com/package/ai) — v6.0.91
- [Vercel next-fastapi example](https://github.com/vercel/ai/tree/main/examples/next-fastapi) — FastAPI + streaming
- [Figma MCP — Tools](https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/) — get_design_context (IDE-only)
- [Nodebox Sustainable Use License](https://github.com/Sandpack/nodebox-runtime/blob/main/packages/nodebox/LICENSE) — Commercial restrictions

---
*Stack research for: Blueprint PM — Figma import, chat iteration, React preview*  
*Researched: 2025-02-19*
