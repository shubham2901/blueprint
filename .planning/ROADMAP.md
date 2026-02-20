# Roadmap: Blueprint PM

## Overview

Blueprint PM V1 delivers: Import (Figma OAuth + frame URL), Discuss (freeform chat), Build (live React preview). Phases follow research: shell + landing → Figma auth + import → code gen → preview → chat iteration → session persistence. Design reference: `designs/` (Stitch screens, Cozy Sand theme).

## Phases

- [x] **Phase 1: Shell + Landing + Figma Import** — Layout from designs, Connect with Figma, paste URL, import single frame
- [ ] **Phase 2: Code Generation** — Design context → React code (single-shot, no chat yet)
- [ ] **Phase 3: Sandpack Preview** — Live React preview, retry/fallback on error
- [ ] **Phase 4: Chat Iteration** — Multi-turn chat drives code changes, preview updates
- [ ] **Phase 5: Session Persistence** — Session cookie + DB, restore on return

## Phase Details

### Phase 1: Shell + Landing + Figma Import
**Goal**: User sees the Blueprint PM shell (tabs, layout from designs), connects Figma via OAuth, pastes frame URL, and system imports design context.
**Depends on**: Nothing (first phase)
**Requirements**: UI-01 (partial), UI-02, FIGMA-01, FIGMA-02, FIGMA-03, FIGMA-04
**Success Criteria** (what must be TRUE):
  1. User lands at `/` and sees layout from designs (Research | Blueprint | Build tabs, main area, sidebar)
  2. User sees "Turn your Figma into a working prototype" and "Connect with Figma" CTA
  3. User can complete Figma OAuth and return to app
  4. User can paste Figma frame URL and trigger import
  5. System returns design context (document subtree, components, styles) for single frame
**Design Reference**: `designs/screen-01.html` through `designs/screen-04.html` (Cozy Sand: primary #C27B66, sand-light #F9F7F2, Inter + Newsreader)
**Plans**: 5 plans

Plans:
- [x] 01-01-PLAN.md — Route restructure + Build shell (tabs, layout)
- [x] 01-02-PLAN.md — Landing + Connect CTA + Paste URL UI
- [x] 01-03-PLAN.md — Figma OAuth backend (start, callback, status)
- [x] 01-04-PLAN.md — Figma Import backend (URL parse, fetch, validate)
- [x] 01-05-PLAN.md — Wire OAuth + Import (Connect CTA, Import flow)

### Phase 2: Code Generation
**Goal**: Given design context from Figma import, system produces React + Tailwind code. Single-shot generation — no chat yet. Code stored in DB.
**Depends on**: Phase 1
**Requirements**: CODE-01
**Success Criteria** (what must be TRUE):
  1. On import success, system generates React code from design context
  2. Code uses Tailwind and functional components
  3. User can trigger "Regenerate" for testing
**Plans**: 6 plans

Plans:
- [x] 02-01-PLAN.md — DB schema + models (prototype_sessions, CRUD)
- [x] 02-02-PLAN.md — Design context transformer (Figma → LLM-ready)
- [ ] 02-03-PLAN.md — LLM vision support (call_llm_vision, Gemini 2.5 Pro)
- [ ] 02-04-PLAN.md — Code generation endpoint + prompt
- [ ] 02-05-PLAN.md — Frontend: generating state + success + Regenerate
- [ ] 02-06-PLAN.md — Tests: unit (transformer, vision, fences) + integration (API endpoints)

### Phase 3: Sandpack Preview
**Goal**: Live React preview in browser. Retry on compile error; fallback to last working version.
**Depends on**: Phase 2
**Requirements**: PREV-01, PREV-02, PREV-03, PREV-04, PREV-05
**Success Criteria** (what must be TRUE):
  1. User sees generated code rendered in Sandpack preview
  2. Preview updates when code changes (debounced)
  3. On compile error: retry once, then restore last working version with friendly message
**Plans**: TBD

### Phase 4: Chat Iteration
**Goal**: User chats; each message triggers regenerate; preview updates. Full conversation context.
**Depends on**: Phase 3
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CODE-02, CODE-03, CODE-04, UI-03, EXPORT-01
**Success Criteria** (what must be TRUE):
  1. User types in chat; message streams back
  2. Each message triggers code regeneration with full history
  3. Preview updates with new code
  4. User can add new screens via chat; switch via tabs
  5. User can copy generated code to clipboard
  6. User can say "done" or "thank you" to end session
**Plans**: TBD

### Phase 5: Session Persistence
**Goal**: Session survives browser close. User returns and resumes.
**Depends on**: Phase 4
**Requirements**: SESS-01, SESS-02, SESS-03, SESS-04
**Success Criteria** (what must be TRUE):
  1. Session identified by cookie (no login)
  2. Design context, code, messages persist in DB
  3. User returns, session restores code + chat + preview
  4. Save debounced on message/code change
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Shell + Landing + Figma Import | 5/5 | Complete | 2025-02-19 |
| 2. Code Generation | 2/6 | In Progress|  |
| 3. Sandpack Preview | 0/0 | Not started | - |
| 4. Chat Iteration | 0/0 | Not started | - |
| 5. Session Persistence | 0/0 | Not started | - |
