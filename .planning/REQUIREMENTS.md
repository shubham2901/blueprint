# Requirements: Blueprint PM

**Defined:** 2025-02-19
**Core Value:** The PM talks, the system builds. A working prototype that stakeholders can see and click through communicates intent better than any PRD.

## v1 Requirements

Requirements for V1: Import, Discuss, Build. Each maps to roadmap phases.

### Figma Import

- [ ] **FIGMA-01**: PM can connect Figma via OAuth ("Connect with Figma")
- [ ] **FIGMA-02**: PM can paste a Figma frame URL to select what to import
- [ ] **FIGMA-03**: System imports a single frame and returns design context (document subtree, components, styles)
- [ ] **FIGMA-04**: System validates or warns on frame structure (components, Auto Layout, semantic names) before generation

### Code Generation

- [x] **CODE-01**: System generates React code from Figma design context (Tailwind, functional components)
- [ ] **CODE-02**: System modifies generated code based on chat messages (full conversation context)
- [ ] **CODE-03**: PM can request new screens via chat; system generates new components and adds to navigation
- [ ] **CODE-04**: System outputs full updated file per message (not diff); code is source of truth for preview

### Preview

- [ ] **PREV-01**: PM sees live React preview rendered in Sandpack (vanilla React template)
- [ ] **PREV-02**: Preview updates when generated code changes (debounced to avoid race conditions)
- [ ] **PREV-03**: Preview is visual only — no form submission, clicks, or routing in V1
- [ ] **PREV-04**: On preview compile error: retry generation once with "fix the code" prompt; if still broken, restore last working version and show friendly error
- [ ] **PREV-05**: System persists last working code per session; never lose work on bad generation

### Chat

- [ ] **CHAT-01**: PM defines feature via freeform chat (no structured questioning in V1)
- [ ] **CHAT-02**: Chat uses full conversation context for each code generation request
- [ ] **CHAT-03**: Chat streams responses (Vercel AI SDK useChat or equivalent)
- [ ] **CHAT-04**: PM can say "done" or "thank you" to signal session end (no Share/Demo button in V1)

### Session

- [ ] **SESS-01**: Session is identified by session cookie (anonymous; no login in V1)
- [ ] **SESS-02**: Session data (design context, code, messages) persists in DB (Supabase prototype_sessions)
- [ ] **SESS-03**: PM can return later and resume session (restore code, chat, preview)
- [ ] **SESS-04**: Session save is debounced on message or code change

### Layout & Navigation

- [ ] **UI-01**: Chat in side panel, preview on other side (Cursor-like layout)
- [ ] **UI-02**: Prototype is default at `/`; research tool at separate route (e.g. `/research`)
- [ ] **UI-03**: PM can switch between multiple screens via tabs or nav when multiple screens exist

### Export

- [ ] **EXPORT-01**: PM can copy generated code to clipboard

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Annotations

- **ANNOT-01**: PM can hover on any element and see functional annotation (what it does, edge cases, acceptance criteria)
- **ANNOT-02**: System auto-generates annotations from chat history; asks for missing details

### Share

- **SHARE-01**: PM can share prototype via link (V3)
- **SHARE-02**: PM can use "Demo" button to present (V3)

### Refinement

- **REFINE-01**: GSD-style structured questioning to refine problem-solution (V4)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Login / auth | V1 uses session cookie; auth in later version |
| Design language extraction | Defer; start with frame → React conversion |
| mem0 / persistent memory | Later versions |
| Preview interactivity (forms, clicks) | V1 visual only; add when core validated |
| Production-ready code promise | Position as prototype for validation; engineers refine |
| Full design system extraction | Complex, brittle; defer to V2+ |
| Multi-framework (Vue, Angular) | React-first is 80% of market |
| Real-time collaboration | Single-user sufficient for V1 |
| GitHub PR / code to repo | Clipboard sufficient for V1 |
| Mobile app output | Web preview first |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIGMA-01 | Phase 1 | Pending |
| FIGMA-02 | Phase 1 | Pending |
| FIGMA-03 | Phase 1 | Pending |
| FIGMA-04 | Phase 1 | Pending |
| UI-01 (partial) | Phase 1 | Pending |
| UI-02 | Phase 1 | Pending |
| CODE-01 | Phase 2 | Complete |
| PREV-01 | Phase 3 | Pending |
| PREV-02 | Phase 3 | Pending |
| PREV-03 | Phase 3 | Pending |
| PREV-04 | Phase 3 | Pending |
| PREV-05 | Phase 3 | Pending |
| CHAT-01 | Phase 4 | Pending |
| CHAT-02 | Phase 4 | Pending |
| CHAT-03 | Phase 4 | Pending |
| CHAT-04 | Phase 4 | Pending |
| CODE-02 | Phase 4 | Pending |
| CODE-03 | Phase 4 | Pending |
| CODE-04 | Phase 4 | Pending |
| UI-03 | Phase 4 | Pending |
| EXPORT-01 | Phase 4 | Pending |
| SESS-01 | Phase 5 | Pending |
| SESS-02 | Phase 5 | Pending |
| SESS-03 | Phase 5 | Pending |
| SESS-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0 ✓

---
*Requirements defined: 2025-02-19*
*Last updated: 2025-02-19 after initial definition*
