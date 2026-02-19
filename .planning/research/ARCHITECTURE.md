# Architecture Research: Figma-to-Code & AI Prototyping Systems

**Domain:** Figma-to-code, AI prototyping, chat-driven code generation  
**Researched:** 2025-02-19  
**Confidence:** HIGH (Figma REST API, Sandpack docs, MCP guide) / MEDIUM (ecosystem patterns from multiple sources)

---

## Executive Summary

Figma-to-code and AI prototyping systems share a common architecture: **design context extraction → LLM code generation → live preview → chat iteration**. The key components are: (1) Figma OAuth + REST API for design access, (2) design context extraction (file JSON + node subtree), (3) LLM code generation with chat history, (4) Sandpack for client-side React preview, and (5) session persistence for multi-turn iteration. Data flows unidirectionally: User → Auth → Design Import → Code Gen → Preview. For Blueprint PM, build order should be: Auth → Design Import → Code Gen → Preview → Chat Iteration → Session Persistence.

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Chat Panel   │  │ Preview      │  │ Frame URL    │  │ Session / Nav        │  │
│  │ (Vercel AI   │  │ (Sandpack    │  │ Input        │  │ (tabs, copy code)    │  │
│  │  SDK)        │  │  iframe)     │  │              │  │                      │  │
│  └──────┬───────┘  └──────▲───────┘  └──────┬───────┘  └──────────────────────┘  │
│         │                 │                 │                                      │
├─────────┴─────────────────┴─────────────────┴──────────────────────────────────────┤
│                           ORCHESTRATION LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │  PM Workspace (Next.js page)                                                  ││
│  │  - Owns chat state, preview state, session state                             ││
│  │  - Coordinates: paste URL → import → generate → preview → chat → regenerate   ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────────┤
│                           SERVICE LAYER                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│  │ Figma Auth  │  │ Design      │  │ Code Gen    │  │ Session Store        │    │
│  │ (OAuth)     │  │ Import       │  │ (LLM)       │  │ (Supabase)           │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────────────────────┘    │
│         │                │                │                                        │
├─────────┴────────────────┴────────────────┴────────────────────────────────────────┤
│                           EXTERNAL SERVICES                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                              │
│  │ Figma REST  │  │ LLM Provider │  │ Supabase     │                              │
│  │ API         │  │ (litellm)    │  │ (Postgres)   │                              │
│  └─────────────┘  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|--------------------------|
| **Figma Auth** | OAuth 2 flow; token exchange, refresh, storage | Next.js API route `/api/auth/figma/callback`; store access_token server-side (httpOnly cookie or encrypted session) |
| **Design Import** | Parse frame URL → extract file_key + node_id → fetch design context | Backend: `GET /v1/files/:key/nodes?ids=:id` (Figma REST API); returns document subtree, components, styles |
| **Code Gen** | Design context + chat history → React code | Backend: LLM call (litellm) with structured prompt; stream tokens or return full code block |
| **Preview** | Render generated React code in browser | Sandpack: SandpackProvider → SandpackClient → Bundler → iframe; files + template passed as props |
| **Chat Orchestration** | Multi-turn conversation; route messages to code gen | Vercel AI SDK: `useChat`; append design context to system message; stream responses |
| **Session Store** | Persist prototype sessions across visits | Supabase: `prototype_sessions` table; session cookie links anonymous user to session |

---

## Recommended Project Structure (Blueprint PM)

```
frontend/
├── app/
│   ├── page.tsx                    # PM prototype (default at /)
│   ├── research/                   # Existing research tool (separate route)
│   │   └── ...
│   ├── api/
│   │   ├── auth/
│   │   │   └── figma/
│   │   │       ├── route.ts        # OAuth initiate
│   │   │       └── callback/
│   │   │           └── route.ts    # OAuth callback, token storage
│   │   └── prototype/
│   │       ├── import/
│   │       │   └── route.ts        # POST: figma_url → design context
│   │   └── generate/
│   │       └── route.ts            # POST: design_context + messages → React code
│   └── layout.tsx
├── components/
│   ├── pm/                         # PM-specific components
│   │   ├── ChatPanel.tsx           # Chat UI, useChat
│   │   ├── PreviewPanel.tsx        # Sandpack wrapper
│   │   ├── FrameUrlInput.tsx       # Paste URL, trigger import
│   │   └── SessionNav.tsx         # Tabs, copy code
│   └── ui/                         # Existing shadcn
└── lib/
    └── sandpack-templates.ts       # React template for Sandpack

backend/
├── app/
│   ├── api/
│   │   └── prototype/
│   │       ├── import.py           # Figma API client, design context fetch
│   │       └── generate.py        # LLM code gen, prompt construction
│   └── figma.py                    # Figma REST client (OAuth token from request)
```

### Structure Rationale

- **`/api/auth/figma`**: OAuth lives in Next.js because browser redirects; backend receives token via header/cookie for Figma API calls.
- **`/api/prototype/import`**: Can be Next.js route (calls Figma directly with token) or FastAPI (receives token from frontend). Prefer FastAPI to keep all external API calls in backend (AGENTS.md: "All data flows through backend").
- **`components/pm/`**: PM-specific; research tool uses `components/` (Workspace, Sidebar, etc.). Clear boundary.
- **Sandpack in frontend only**: Client-side bundling; no server execution. Matches constraint.

---

## Data Flow

### Primary Flow: Paste URL → Import → Generate → Preview

```
[User pastes Figma frame URL]
    │
    ▼
[FrameUrlInput] → parse URL → extract file_key, node_id
    │
    ▼
[Frontend] POST /api/prototype/import { figma_url }
    │  Header: Cookie (session) or Authorization (Figma token)
    ▼
[Backend] figma.py
    │  GET https://api.figma.com/v1/files/:key/nodes?ids=:id
    │  Returns: document (Node subtree), components, styles
    ▼
[Backend] → design_context JSON
    │
    ▼
[Frontend] design_context stored in state
    │
    ▼
[User types chat message] "Make the button blue"
    │
    ▼
[ChatPanel] useChat → POST /api/prototype/generate
    │  Body: { design_context, messages[], current_code? }
    ▼
[Backend] generate.py
    │  Prompt: design_context + messages + "Generate React code. Output only code."
    │  LLM (litellm) → React code string
    ▼
[Frontend] code → SandpackProvider files={{ "App.jsx": code }}
    │
    ▼
[PreviewPanel] SandpackPreview renders iframe
```

### State Management Flow

```
[Session Store (Supabase)]
    │
    ├── prototype_sessions: id, session_cookie_id, figma_url, design_context_snapshot,
    │                        current_code, messages (JSONB), created_at, updated_at
    │
    ▼ (subscribe on load)
[PM Workspace]
    │
    ├── designContext: from import or session
    ├── code: from generate or session
    ├── messages: from useChat or session
    └── sessionId: from cookie
    │
    ▼ (on message / generate)
[Actions] → save to session (debounced) → Supabase upsert
```

### Key Data Flows (Explicit Direction)

| Flow | Direction | Trigger |
|------|-----------|---------|
| **Figma OAuth** | User → Figma → Callback → Backend stores token | User clicks "Connect Figma" |
| **Design Import** | Frontend → Backend → Figma API → Backend → Frontend | User pastes URL, clicks Import |
| **Code Generation** | Frontend (messages) → Backend → LLM → Backend → Frontend | User sends chat message |
| **Preview Update** | Frontend (code state) → Sandpack → iframe | Code state changes |
| **Session Persist** | Frontend → Backend → Supabase | Debounced on message/code change |
| **Session Restore** | Supabase → Backend → Frontend | User returns, session cookie present |

---

## Component Boundaries

### Boundary 1: Figma Auth vs. Design Import

- **Figma Auth** owns: OAuth client credentials, token exchange, token storage (httpOnly cookie or server-side session).
- **Design Import** owns: Calling Figma REST API with a valid token. It does NOT own token refresh; that belongs to Auth.
- **Contract**: Design Import receives token via `Authorization: Bearer <token>` or from server-side session lookup. If token expired, return 401; Auth layer handles re-auth.

### Boundary 2: Design Import vs. Code Gen

- **Design Import** outputs: `{ document, components, styles }` — raw Figma JSON. No transformation.
- **Code Gen** inputs: design context + chat messages. It may transform/summarize design context for prompt (e.g., extract layout, colors) but does not call Figma.
- **Contract**: Design context is passed as JSON. Code Gen never fetches from Figma.

### Boundary 3: Code Gen vs. Preview

- **Code Gen** outputs: React code string (or `{ files: { "App.jsx": "..." } }`).
- **Preview** inputs: code string. It does not parse or validate; it passes to Sandpack. If Sandpack errors, Preview shows error UI and may trigger retry/fallback.
- **Contract**: Code is a string. Preview is dumb — it renders what it receives.

### Boundary 4: Chat vs. Code Gen

- **Chat** owns: message history, streaming UI, user input.
- **Code Gen** owns: prompt construction, LLM call, response parsing.
- **Contract**: Chat sends `{ messages, design_context, current_code? }`. Code Gen returns `{ code }` or streams tokens. Chat appends assistant message with code.

### Boundary 5: Session Store vs. Workspace

- **Session Store** owns: CRUD for `prototype_sessions`; session cookie validation.
- **Workspace** owns: UI state, when to save (debounce), what to save.
- **Contract**: Workspace calls `POST /api/prototype/sessions` or `PATCH /api/prototype/sessions/:id` with `{ design_context, code, messages }`. Store returns session id. Workspace does not query sessions directly for list view (deferred to V2).

---

## Architectural Patterns

### Pattern 1: Design Context as Immutable Snapshot

**What:** Store the raw Figma design context (document subtree, components, styles) at import time. Do not re-fetch on every chat message.

**When:** Chat iteration modifies code, not design. Design context is fixed for the session.

**Trade-offs:**  
- Pro: Fewer Figma API calls; faster iteration.  
- Con: If user changes Figma and wants to re-import, they must paste URL again or click "Re-import."

**Example:**
```typescript
// On import
const designContext = await fetch('/api/prototype/import', { body: { figma_url } });
setDesignContext(designContext); // Stored in state, passed to every generate call
```

### Pattern 2: Code-as-Source-of-Truth for Preview

**What:** The latest generated code is the source of truth for the preview. Chat messages describe desired changes; the LLM produces a full updated file, not a diff.

**When:** Simpler than diff/patch for V1. Full replacement avoids merge conflicts.

**Trade-offs:**  
- Pro: Straightforward; no AST manipulation.  
- Con: Long conversations may hit context limits; consider summarizing or truncating.

### Pattern 3: Sandpack Provider at Workspace Level

**What:** Single `SandpackProvider` wraps the preview. Pass `files` and `template` as props. On code change, update `files`; Sandpack re-bundles.

**When:** One preview per session. Multiple screens (tabs) = multiple files in one Sandpack context, switch active file.

**Example:**
```tsx
<SandpackProvider template="react" files={{ "App.jsx": code }}>
  <SandpackPreview />
</SandpackProvider>
```

### Pattern 4: Retry-Then-Fallback on Preview Error

**What:** If Sandpack fails to compile (syntax error, missing import), first retry with "fix the code" prompt. If retry fails, revert to last working code and show toast.

**When:** LLM output is often malformed. User should not lose work.

**Implementation:** Store `lastWorkingCode` in state. On Sandpack `onError`, call generate with "Fix the following code: ..." + error message. On success, update. On failure, restore `lastWorkingCode`.

---

## Anti-Patterns

### Anti-Pattern 1: Fetching Figma on Every Message

**What people do:** Call Figma API on each chat message to get "latest" design.

**Why it's wrong:** Rate limits (Tier 1: ~3 req/min); unnecessary latency; design rarely changes mid-session.

**Do this instead:** Fetch once at import; pass snapshot to Code Gen.

### Anti-Pattern 2: Server-Side Code Execution for Preview

**What people do:** Run Node/bundler on server, stream HTML to client.

**Why it's wrong:** Security risk; resource intensive; conflicts with "client-side Sandpack" constraint.

**Do this instead:** Sandpack runs entirely in browser. Generated code is sent to client; client bundles.

### Anti-Pattern 3: Mixing Research and PM State

**What people do:** Single "journey" or "session" table for both research journeys and prototype sessions.

**Why it's wrong:** Different lifecycles, different schemas. Research has steps, selections; prototype has code, messages.

**Do this instead:** Separate tables: `journeys` (research), `prototype_sessions` (PM). Same Supabase, different routes.

### Anti-Pattern 4: Inline Figma Token in Frontend

**What people do:** Store Figma access token in localStorage or pass to client.

**Why it's wrong:** Token can be extracted; violates "all external API calls through backend."

**Do this instead:** Token in httpOnly cookie or server-side session. Backend reads token, calls Figma. Frontend never sees token.

---

## Integration Points

### Figma REST API

| Endpoint | Purpose | When Called |
|----------|---------|-------------|
| `GET /v1/files/:key` | Full file or subset via `?ids=1:2` | Design import: fetch node subtree |
| `GET /v1/files/:key/nodes?ids=:id` | Specific nodes + subtrees | Alternative: when only need selected nodes |
| `GET /v1/images/:key?ids=:id` | Rendered image of node | Optional: visual reference for LLM (screenshot) |

**Auth:** OAuth 2; `file_content:read` scope. Token in `Authorization: Bearer <access_token>`.

**Rate limits:** Tier 1 (file endpoints): ~3 req/min per user. Batch node requests where possible.

### Sandpack

| Component | Purpose |
|-----------|---------|
| `SandpackProvider` | Context: files, template, theme |
| `SandpackPreview` | Renders iframe |
| `useSandpack` | Access client, listen for compile errors |

**Template:** `react` for React + JSX. Add dependencies via `customSetup.dependencies` if needed (e.g., `"lucide-react": "latest"`).

### Existing Blueprint Backend

| Reuse | Notes |
|-------|-------|
| `llm.py` | Use `acompletion` for code gen; same fallback chain |
| `config.py` | Add `FIGMA_CLIENT_ID`, `FIGMA_CLIENT_SECRET` to env |
| `db.py` | Add `prototype_sessions` table; reuse Supabase client |
| `models.py` | Add Pydantic models for import/generate requests |

---

## Suggested Build Order

### Phase 1: Figma OAuth + Design Import
**Goal:** User connects Figma; pastes URL; backend returns design context.

**Order:**
1. Figma OAuth app (developer.figma.com); get client ID/secret.
2. Next.js route: `/api/auth/figma` (initiate), `/api/auth/figma/callback` (exchange, store token).
3. Backend: `figma.py` — `fetch_design_context(file_key, node_id, access_token)`.
4. Backend: `POST /api/prototype/import` — parse URL, call Figma, return JSON.
5. Frontend: `FrameUrlInput` — paste, parse, call import, display "Imported" or error.

**Dependencies:** None. Foundation for everything else.

**Deliverable:** User can paste a Figma frame URL and see "Design imported" (or raw JSON in dev).

---

### Phase 2: Code Generation (No Chat Yet)
**Goal:** Given design context, produce React code. No chat; single-shot.

**Order:**
1. Backend: `generate.py` — prompt: design context → "Generate React component. Use Tailwind. Output only code."
2. Backend: `POST /api/prototype/generate` — body: `{ design_context }`, returns `{ code }`.
3. Frontend: On import success, auto-call generate. Store code in state.
4. Add simple "Regenerate" button for testing.

**Dependencies:** Phase 1 (design context).

**Deliverable:** Paste URL → Import → Generate → see code in a pre/code block (no preview yet).

---

### Phase 3: Sandpack Preview
**Goal:** Render generated code in iframe.

**Order:**
1. Install `@codesandbox/sandpack-react`.
2. `PreviewPanel`: `SandpackProvider` + `SandpackPreview`; `files={{ "App.jsx": code }}`.
3. Wire code state from Phase 2 to PreviewPanel.
4. Handle compile errors: show error message in UI; implement retry (call generate with "Fix: ..." + error).

**Dependencies:** Phase 2 (code).

**Deliverable:** Paste URL → Import → Generate → Live preview. Retry on error.

---

### Phase 4: Chat Iteration
**Goal:** User chats; each message triggers regenerate; preview updates.

**Order:**
1. Add `useChat` from Vercel AI SDK.
2. `ChatPanel`: input, message list, send.
3. On send: append user message; call `POST /api/prototype/generate` with `{ design_context, messages, current_code }`.
4. Backend: include full message history in LLM prompt; return updated code.
5. On response: update code state → preview re-renders.
6. Implement "last working code" fallback on repeated failure.

**Dependencies:** Phases 2, 3.

**Deliverable:** Chat-driven iteration with live preview.

---

### Phase 5: Session Persistence
**Goal:** Session survives browser close; user can return and continue.

**Order:**
1. Supabase: `prototype_sessions` table (id, session_cookie_id, figma_url, design_context, code, messages, created_at, updated_at).
2. Backend: `POST /api/prototype/sessions` (create), `PATCH /api/prototype/sessions/:id` (update).
3. Frontend: session cookie (anonymous, no login); on load, check cookie → fetch session if exists.
4. Debounced save: on message or code change, PATCH session.
5. Optional: list recent sessions (defer to V2 if scope creep).

**Dependencies:** Phases 1–4.

**Deliverable:** Sessions persist; user returns to same prototype.

---

### Build Order Summary

```
Phase 1: Auth + Import     ← No dependencies
    ↓
Phase 2: Code Gen          ← Needs design context
    ↓
Phase 3: Preview           ← Needs code
    ↓
Phase 4: Chat              ← Needs code gen + preview
    ↓
Phase 5: Session           ← Needs full flow
```

**Critical path:** 1 → 2 → 3 → 4. Phase 5 can be parallelized with Phase 4 polish but is logically last.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0–100 users | Monolith fine. Single FastAPI + Next.js. Session in Supabase. |
| 100–1K users | Add rate limiting on Figma import (per session). Consider caching design context by (file_key, node_id) for 24h to reduce Figma calls. |
| 1K+ users | Evaluate: (a) background job for code gen if >5s, (b) Redis for session cache, (c) separate worker for LLM calls. |

**First bottleneck:** Figma API rate limits (Tier 1). Mitigation: cache design context; batch requests.

**Second bottleneck:** LLM latency. Mitigation: stream code tokens; show partial preview when possible (Sandpack supports hot reload on file change).

---

## Sources

- [Figma REST API — File Endpoints](https://developers.figma.com/docs/rest-api/file-endpoints/) — GET file, GET file nodes
- [Figma REST API — Authentication](https://developers.figma.com/docs/rest-api/authentication/) — OAuth 2
- [Figma MCP Server Guide](https://github.com/figma/mcp-server-guide) — get_design_context, design context structure
- [Sandpack Architecture Overview](https://sandpack.codesandbox.io/docs/architecture/overview) — React → Client → Bundler flow
- [Figma Blog: Figma to React](https://www.figma.com/blog/introducing-figma-to-react/) — layout, constraints, Gadgets (historical reference)
- [Builder.io: Convert Figma to React](https://www.builder.io/blog/convert-figma-to-react-code) — design system integration patterns
- [Vercel: v0 UI Generation](https://vercel.com/blog/maximizing-outputs-with-v0-from-ui-generation-to-code-creation) — Prompt → Build → Publish flow
- Blueprint AGENTS.md, ARCHITECTURE.md, .planning/PROJECT.md — existing patterns, constraints

---
*Architecture research for: Blueprint PM — Figma-to-code, chat-driven prototyping*  
*Researched: 2025-02-19*
