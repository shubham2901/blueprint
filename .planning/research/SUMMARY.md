# Research Summary: Blueprint PM

**Domain:** PM prototyping / Figma-to-code / chat-driven design iteration  
**Researched:** 2025-02-19  
**Overall confidence:** HIGH (Stack, Architecture) / MEDIUM (Features, Pitfalls)

## Executive Summary

Blueprint PM fits a well-established pattern: design context extraction → LLM code generation → live preview → chat iteration. The recommended stack is Figma REST API (OAuth 2) for import, litellm for code gen, Sandpack vanilla React for preview, and Vercel AI SDK for streaming chat. Use the vanilla `react` Sandpack template — Nodebox-based templates (Vite, Next.js) have commercial licensing restrictions.

The main risk is overpromising: position codegen as "0 to 0.5," not production-ready. Implement retry-then-fallback on preview errors and persist last working code. Figma API rate limits (Tier 1) require caching design context by (file_key, node_id).

## Key Findings

**Stack:** Figma REST API v1 + OAuth 2, Sandpack `@codesandbox/sandpack-react` ^2.20 (vanilla React template), Vercel AI SDK `ai` ^6.x + `@ai-sdk/react` ^3.x, litellm (existing). Avoid Sandpack Nodebox templates, Figma MCP for backend, Builder.io.

**Architecture:** Five component boundaries: Figma Auth vs Design Import, Design Import vs Code Gen, Code Gen vs Preview, Chat vs Code Gen, Session Store vs Workspace. Data flows unidirectionally: User → Auth → Import → Code Gen → Preview. Build order: Auth + Import → Code Gen → Preview → Chat → Session Persistence.

**Table stakes:** Figma import, live preview, chat interface, code export (clipboard), React output, session persistence, component recognition, asset export.

**Critical pitfall:** LLM output without validation/fallback — implement retry-then-fallback, persist last working version, never show raw errors.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Figma OAuth + Design Import
**Rationale:** Foundation; no other phase can start without it.  
**Delivers:** User connects Figma; pastes frame URL; backend returns design context.  
**Addresses:** Figma import (table stakes).  
**Avoids:** Figma import without structure (validate components, Auto Layout, semantic names).

### Phase 2: Code Generation (Single-Shot)
**Rationale:** Design context enables code gen; chat comes later.  
**Delivers:** Given design context, produce React code. No chat yet.  
**Uses:** litellm, design context JSON.  
**Implements:** Code Gen component.

### Phase 3: Sandpack Preview
**Rationale:** Code must be visible before chat iteration.  
**Delivers:** Live React preview; retry on compile error.  
**Uses:** Sandpack vanilla React template.  
**Avoids:** Sandpack race conditions (debounce updates).

### Phase 4: Chat Iteration
**Rationale:** Core PM flow — chat drives code changes.  
**Delivers:** Multi-turn chat; each message triggers regenerate; preview updates.  
**Uses:** Vercel AI SDK useChat, full message history.  
**Avoids:** LLM output without fallback (retry-then-fallback, last working code).

### Phase 5: Session Persistence
**Rationale:** Sessions survive browser close.  
**Delivers:** Session cookie + DB; restore on return.  
**Uses:** Supabase prototype_sessions table.  
**Avoids:** Session persistence without clear state boundaries.

### Phase Ordering Rationale

- Phase 1 is the base; Figma OAuth and design context are prerequisites.
- Phases 2–4 form the core loop: Import → Generate → Preview → Chat.
- Phase 5 can parallelize with Phase 4 polish but is logically last.
- Figma API rate limits (Tier 1) — cache design context by (file_key, node_id) to reduce calls.

### Research Flags

- **Phase 1:** Figma OAuth flow — verify callback, token storage, CORS. Figma structure validation — document "what makes a good frame."
- **Phase 3:** Sandpack debounce — check race condition #1181; plan CSP for `unsafe-eval` if needed.
- **Phase 4:** litellm + Text Stream Protocol — verify format for useChat compatibility.

Phases with standard patterns (skip research-phase): Phase 2 (LLM code gen), Phase 5 (Supabase CRUD).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Figma REST, Sandpack, AI SDK verified via official docs |
| Features | MEDIUM | Competitor analysis, PM-focused articles |
| Architecture | HIGH | Figma API, Sandpack docs, MCP guide |
| Pitfalls | MEDIUM | WebSearch + official docs; some 2023–2024 sources |

### Gaps to Address

- **Design token mapping:** Defer for V1; start with frame → React. Add token context in V2 if validated.
- **Sandpack race conditions:** Implement debounce; monitor upstream issues.
- **litellm stream format:** Verify Text Stream Protocol compatibility with useChat during Phase 4 planning.

## Sources

### Primary (HIGH confidence)
- Figma REST API — Authentication, File Endpoints
- Sandpack — FAQ, npm v2.20, licensing
- Vercel AI SDK — useChat, Stream Protocol

### Secondary (MEDIUM confidence)
- Builder.io, Figma Make, v0, Lovable — feature comparison
- LLM code generation pitfalls — arXiv papers

### Tertiary (LOW confidence)
- Community posts on design-to-code failures

---
*Research completed: 2025-02-19*  
*Ready for roadmap: yes*
