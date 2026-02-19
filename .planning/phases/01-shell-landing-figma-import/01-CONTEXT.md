# Phase 1: Shell + Landing + Figma Import — Context

**Gathered:** 2025-02-19
**Status:** Ready for planning

## Phase Boundary

User sees the Blueprint PM shell (layout from designs), connects Figma via OAuth, pastes frame URL, and system imports design context. No code generation or preview yet — that's Phase 2–3.

## Implementation Decisions

### Design & Layout

- **Primary color:** `#C27B66` (Cozy Sand). Single source of truth in `frontend/app/globals.css` — change `--primary-hex` in `:root` to update app-wide.
- **Design reference:** `designs/screen-01.html` through `designs/screen-04.html`. Match layout and structure; colors come from globals.css.
- **Tabs:** Research | Blueprint | Build
  - **Research** — Opens research tab. Research is the existing app (competitive intelligence). Blueprint is a sub-tab within Research (blueprint view of research results).
  - **Build** — PM prototyping tool we're building. Active tab for this phase.
  - Research tab navigates to existing research routes; Build shows the PM tool.

### Connect vs Paste Order

- **Prompt "Connect to import"** — If user pastes URL before connecting Figma, show prompt: "Connect with Figma to import this frame." User must complete OAuth before import proceeds.
- Flow: User can paste URL first → we detect no Figma connection → show Connect CTA. After OAuth, import runs (or user clicks Import again).

### Error Handling

- **User-facing:** Friendly message only. Never raw errors, stack traces, or provider names.
- **Technical ref:** Every error includes `error_code` (e.g. `BP-3F8A2C`) from `generate_error_code()`.
- **Internal doc:** `docs/ERROR_CODES.md` maps scenarios to user messages and internal details. Grep logs by `error_code` to correlate user reports.
- **Pattern:** `log("ERROR", ..., error_code=code)` + include `error_code` in response. Frontend shows `(Ref: BP-XXXXXX)` in small muted text.

## Specific Ideas

- Layout: main area (65%) + sidebar (35%), Cursor-like. Sidebar has chat placeholder "What are you building today?"
- Landing: "Turn your Figma into a working prototype" + "Connect with Figma" CTA
- Import: "Paste your Figma frame URL" + input + Import button. "Need help? Learn how to find your frame URL" link
- Importing: URL readonly, loading skeleton, "Building your prototype..." (Phase 1 ends at design context returned; "Building" is aspirational for later phases)

## Deferred Ideas

- "How it works" link — content TBD
- "Learn how to find your frame URL" — can link to Figma docs or internal help
- Sign up / session count in sidebar — V1 uses session cookie, no login; can show "1 session" as placeholder or hide

---
*Phase: 01-shell-landing-figma-import*
*Context gathered: 2025-02-19*
