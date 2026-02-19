# Blueprint PM

## What This Is

Blueprint PM is a chat-first prototyping tool for product managers. PM connects Figma via OAuth, pastes a frame URL, and defines what they want to build through freeform chat. The system generates and updates a live React preview as they iterate — no code, specs, or PRDs. The prototype replaces the document. New product in the same repo as the research tool; research stays at a separate route and will be integrated later.

## Core Value

The PM talks, the system builds. A working prototype that stakeholders can see and click through communicates intent better than any PRD.

## Requirements

### Validated

<!-- Research tool — existing in codebase. -->

- ✓ Competitive intelligence via intent-based pipeline (classify → clarify → competitors → explore) — existing
- ✓ SSE streaming for progressive research results — existing
- ✓ Journey/session persistence in Supabase — existing
- ✓ Build intent: gap analysis, problem selection, problem statement — existing

### Active

<!-- V1: Import, Discuss, Build. -->

- [ ] PM connects Figma via OAuth
- [ ] PM pastes Figma frame URL; system imports single frame
- [ ] System generates React code from Figma frame
- [ ] PM defines feature via freeform chat (full conversation context)
- [ ] System modifies React code based on chat; live preview updates (Sandpack)
- [ ] PM can add new screens; switch between screens via tabs/nav
- [ ] Preview is visual only (no interactivity in V1)
- [ ] PM says "done" or "thank you" to end session
- [ ] Session persists across browser visits (session cookie, DB storage)
- [ ] Preview breaks: retry first, then fallback to last working version
- [ ] PM can copy generated code to clipboard
- [ ] Chat in side panel, preview on other side (Cursor-like layout)
- [ ] Prototype at `/` (default); research at separate route

### Out of Scope

- **Annotate** — Hover annotations on elements (V2)
- **Share** — Share link, Demo button (V3)
- **GSD-like questioning** — Structured refinement of problem-solution (V4)
- **Login** — V1 uses session cookie; auth in later version
- **Design language extraction** — Defer; start with frame → React conversion
- **mem0 / persistent memory** — Later versions
- **Preview interactivity** — Forms, clicks, validation (V1 visual only)

## Context

- Monorepo: Next.js frontend + FastAPI backend (existing). PM tool adds new routes and backend endpoints.
- Research tool remains; prototype is the default experience at `/`.
- Build slowly, test every iteration before advancing.
- Figma API for import; Sandpack for in-browser React preview; Vercel AI SDK for streaming chat.
- Existing stack: FastAPI, Next.js 15, Supabase, litellm, Pydantic v2.

## Constraints

- **Tech stack**: Same monorepo — extend existing Next.js app and FastAPI backend; no new services.
- **Figma**: OAuth + REST API for file/frame access.
- **Preview**: Sandpack or equivalent for client-side React rendering (no server-side execution).
- **Session**: Session cookie for anonymous identification; no login in V1.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| New product in same repo | Research tool stays; prototype is new. Separate routes. | — Pending |
| Prototype default at `/` | PM tool is primary; research at `/research` or similar | — Pending |
| Single frame import (V1) | Simplest path; multi-frame later | — Pending |
| Freeform chat, not GSD | Ship faster; GSD questioning in V4 | — Pending |
| Session cookie, no login | Persist across visits without auth complexity | — Pending |
| Retry then fallback on preview error | Recover from LLM mistakes; don't lose work | — Pending |
| Side panel layout | Familiar (Cursor/IDE); chat + preview visible | — Pending |
| Copy to clipboard export | Simplest export; full project zip later | — Pending |

---
*Last updated: 2025-02-19 after initialization*
