# Feature Landscape

**Domain:** PM prototyping / design-to-code tools  
**Researched:** 2025-02-19  
**Confidence:** MEDIUM

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Figma import** | Every design-to-code tool supports Figma; PMs live in Figma. Frame URL or plugin export is baseline. | MEDIUM | OAuth + REST API or plugin export. Single-frame import is sufficient for V1. |
| **Live preview** | Users need to see output immediately. No preview = broken experience. | LOW | Sandpack, CodeSandbox, or similar. Client-side only for V1. |
| **Chat / conversation interface** | AI prototyping is conversational by default (v0, Bolt, Lovable, Figma Make). Text prompts are table stakes. | LOW | Streaming responses expected. Full conversation context for edits. |
| **Code export** | PMs hand off to engineers. Copy to clipboard is minimum; full project zip is nice-to-have. | LOW | Clipboard first; GitHub sync / PR is differentiator. |
| **Responsive output** | Designs are viewed on multiple devices. Non-responsive output feels broken. | MEDIUM | AI Auto-Layout (Builder.io) or Tailwind responsive classes. |
| **React output** | React/Next.js dominates frontend. HTML-only or Vue-only limits handoff. | MEDIUM | React + Tailwind is standard. shadcn/ui common for quality. |
| **Component recognition** | Buttons, forms, cards must map to real components, not div soup. | MEDIUM | LLM + design context. Design tokens help but not required for V1. |
| **Asset export** | Images, icons from design must appear in preview. | LOW | Extract from Figma API; inline or CDN. |
| **Session persistence** | PMs return to work. Losing context on refresh is unacceptable. | MEDIUM | Session cookie + DB. No login required for V1. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **PM-first, zero design skills** | PMs validate ideas without design queues. Capture-based (Alloy) or chat-first (Blueprint) vs design-tool-first. | HIGH | Natural language only; no Figma expertise. Competitors assume design context. |
| **Figma frame + chat in one flow** | Import frame, then define feature via chat — not design-then-code. Combines visual anchor with conversational refinement. | HIGH | Figma Make does this; Builder.io separates. Blueprint PM's core flow. |
| **Design system preservation** | Output matches existing product branding. Capture-based tools (Alloy) inherit CSS; others use generic Tailwind. | HIGH | Defer for V1; start with frame → React. Design language extraction is V2+. |
| **Git / PR workflow** | Code goes to repo as PR, not just clipboard. v0, Lovable, Builder.io Fusion support this. | MEDIUM | Enterprise differentiator. Defer for Blueprint V1. |
| **Multi-screen / navigation** | Add screens, switch via tabs. Single-frame is limiting for real flows. | MEDIUM | Blueprint V1: add screens, tabs. Competitors vary. |
| **Structured refinement (GSD-style)** | Guided questioning vs freeform chat. Reduces ambiguity, improves output. | HIGH | Blueprint V4. Most tools are freeform. |
| **Integration with product context** | Jira, Linear, Notion (Lovable). Research + prototype in one place (Blueprint). | MEDIUM | Blueprint has research tool; PM prototype can reference journey. |
| **Annotate on elements** | Hover annotations for handoff. V2 for Blueprint. | MEDIUM | Builder.io, Zeplin. Improves designer→dev communication. |
| **Share link / demo** | Frictionless sharing. One link, no account. | LOW | Figma Make, Bolt, Lovable. Blueprint V3. |
| **Backend / database** | Lovable, Bolt have Supabase; v0 added AWS. PM prototyping often visual-only. | HIGH | Blueprint V1: visual only. Backend is optional differentiator. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Production-ready code promise** | PMs want to ship directly. | Design-to-code output requires refinement. Promising production-ready creates trust issues when engineers refactor. | Position as "prototype for validation"; copy to clipboard for handoff. |
| **Full design system extraction** | Match brand exactly. | Complex, brittle. Design tokens, component mapping take significant engineering. | Start with frame → React; add design language extraction in V2 if validated. |
| **Real-time multi-user collaboration** | Teams work together. | Adds sync, conflict resolution, presence. Figma Make has it; most PM tools don't. | Defer. Single-user session is sufficient for V1. |
| **Multi-framework from day one** | Vue, Angular, Svelte users. | Each framework needs separate prompts, validation, testing. React-first is 80% of market. | React + Tailwind only for V1. |
| **Preview interactivity (forms, clicks)** | Prototypes should "work." | Requires state, validation, routing. Sandpack has limits. | V1: visual only. Add interactivity when core flow is validated. |
| **Full backend / auth** | Complete MVP in one tool. | Scope creep. Lovable/Bolt do this; Blueprint PM is prototype-focused. | Defer. Visual prototype communicates intent. |
| **Design handoff specs (Zeplin-style)** | Developers need specs. | Different product category. Design-to-code replaces specs with code. | Code + comments; annotations in V2. |
| **Mobile app output** | PMs think mobile. | React Native, Flutter add complexity. Web preview is sufficient for most validation. | Web preview first. Mobile is future consideration. |

## Feature Dependencies

```
[Figma Import]
    └──requires──> [Figma OAuth or API key]
    └──enables──> [Frame → React conversion]

[Frame → React conversion]
    └──requires──> [LLM + design context]
    └──enables──> [Live preview]

[Chat interface]
    └──requires──> [Streaming AI responses]
    └──enables──> [Iterative refinement]

[Live preview]
    └──requires──> [Sandpack or equivalent]
    └──enables──> [Code export] (user sees what they're copying)

[Session persistence]
    └──requires──> [Session cookie + DB]
    └──enhances──> [Chat interface] (return to conversation)

[Multi-screen / tabs]
    └──requires──> [Live preview]
    └──enhances──> [Chat interface] (add screen via chat)
```

### Dependency Notes

- **Figma import requires OAuth or API key:** Figma REST API needs auth. OAuth is preferred for PMs (no key management).
- **Frame → React requires LLM + design context:** Use Figma node metadata (get_design_context) or plugin export. LLM interprets layout, generates React.
- **Multi-screen enhances chat:** "Add a settings screen" is a chat command; system generates new component, adds to nav.
- **Code export depends on live preview:** User copies what they see. No separate "export" step if clipboard is primary.

## MVP Definition

### Launch With (V1 — Blueprint PM)

Minimum viable product — what's needed to validate the concept.

- [x] **Figma import** — Single frame via URL. OAuth for file access.
- [x] **Frame → React** — Generate React code from Figma frame. Tailwind/shadcn-style output.
- [x] **Chat interface** — Freeform chat with full context. Streaming responses.
- [x] **Live preview** — Sandpack. Visual only (no form submission, no routing).
- [x] **Iterative refinement** — Chat modifies code; preview updates.
- [x] **Session persistence** — Session cookie + DB. Return to work.
- [x] **Copy to clipboard** — Export generated code.
- [x] **Multi-screen** — Add screens via chat; tabs to switch.
- [x] **Side panel layout** — Chat + preview visible (Cursor-like).
- [x] **Retry / fallback** — Preview breaks → retry, then fallback to last working version.

### Add After Validation (V1.x)

Features to add once core is working.

- [ ] **Share link** — One-click share for stakeholders (V3 in Blueprint).
- [ ] **Annotate** — Hover annotations on elements (V2).
- [ ] **Design language hints** — Optional: extract colors/fonts from frame for better fidelity.

### Future Consideration (V2+)

Features to defer until product-market fit is established.

- [ ] **GSD questioning** — Structured refinement (V4).
- [ ] **GitHub sync / PR** — Code to repo as PR.
- [ ] **Preview interactivity** — Forms, clicks, validation.
- [ ] **Research integration** — Link prototype to Blueprint research journey.
- [ ] **Design system extraction** — Match existing product branding.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Figma import | HIGH | MEDIUM | P1 |
| Chat + streaming | HIGH | LOW | P1 |
| Live preview | HIGH | LOW | P1 |
| Frame → React | HIGH | MEDIUM | P1 |
| Session persistence | HIGH | MEDIUM | P1 |
| Copy to clipboard | HIGH | LOW | P1 |
| Multi-screen / tabs | MEDIUM | MEDIUM | P1 |
| Retry / fallback | MEDIUM | LOW | P1 |
| Share link | MEDIUM | LOW | P2 |
| Annotate | MEDIUM | MEDIUM | P2 |
| GitHub PR | MEDIUM | HIGH | P3 |
| Design system extraction | MEDIUM | HIGH | P3 |
| GSD questioning | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Figma Make | Builder.io | v0 | Bolt | Lovable | Blueprint PM |
|---------|------------|------------|-----|------|---------|--------------|
| Figma import | ✅ Native | ✅ Plugin | ✅ (recent) | ✅ | ✅ (Builder) | P1 |
| Chat interface | ✅ | ✅ Fusion | ✅ | ✅ | ✅ | P1 |
| Live preview | ✅ | ✅ | ✅ | ✅ | ✅ | P1 |
| Code export | ✅ Publish | ✅ PR | ✅ PR | ✅ | ✅ GitHub | Clipboard (P1) |
| Multi-screen | ✅ | ✅ | ✅ | ✅ | ✅ | P1 |
| Backend/DB | ✅ (beta) | ❌ | ✅ (AWS) | ✅ | ✅ Supabase | ❌ V1 |
| PM-first | Partial | Dev-focused | Dev-focused | Dev-focused | Prototype-focused | ✅ Core |
| Share link | ✅ | ✅ | ✅ | ✅ | ✅ | V3 |
| Design system | Templates | ✅ | shadcn | Generic | Generic | Defer |
| Annotate | Edit tool | ✅ | ❌ | ❌ | ❌ | V2 |

## Sources

- [AIMultiple: Best Design to Code Tools Compared](https://research.aimultiple.com/design-to-code/) — Feb 2026, feature matrix across 13 tools
- [Alloy: AI Prototyping Tools for PMs](https://alloy.app/library/ai-prototyping-tools-for-pms) — Dec 2025, PM-specific evaluation, capture vs new-app builders
- [Builder.io: AI-Powered Figma to Code](https://www.builder.io/figma-to-code) — Visual Copilot, framework support
- [Figma Help: Figma Make](https://help.figma.com/hc/en-us/articles/31304412302231-Explore-Figma-Make) — Chat, import, publish, collaborate
- [Figma Dev Mode](https://figma.com/dev-mode) — Codegen plugins, inspect, handoff
- [Blueprint PM PROJECT.md](.planning/PROJECT.md) — V1–V4 scope, constraints

---
*Feature research for: PM prototyping / design-to-code*
*Researched: 2025-02-19*
