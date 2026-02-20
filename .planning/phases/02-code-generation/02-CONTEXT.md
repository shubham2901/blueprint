# Phase 2: Code Generation - Context

**Gathered:** 2026-02-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Given Figma design context (node tree, components, styles, thumbnail image), produce React + Tailwind code for a single frame. Single-shot generation — no chat iteration yet (that's Phase 4). No live preview yet (that's Phase 3). Code is stored in the DB and a success state is shown.

</domain>

<decisions>
## Implementation Decisions

### Generation Trigger & Flow
- Code generation starts **automatically** after Figma import completes — no manual trigger needed
- While generating (10-30s), show a **skeleton in the preview area** with **quirky progress storytelling** messages (playful tone, not generic "Loading...")
- On failure: **auto-retry once silently**, then show friendly error with option to retry manually
- After generation: show **success state with Figma thumbnail** and "Your prototype is ready" — code is not displayed (preview comes in Phase 3)
- **Regenerate button** appears only after first generation completes, shown in preview/workspace toolbar
- Send the **Figma thumbnail image** to the LLM alongside structured design context for better visual understanding (vision-capable model)
- Build a **server-side Figma context extraction** that mirrors Figma MCP `get_design_context` quality — structured, code-ready context from Figma REST API, not raw API dump

### Output Quality
- **Near pixel-perfect fidelity** — exact colors, spacing, fonts, sizing from the design
- **Actual text content** from the Figma frame preserved in generated code (no lorem ipsum)
- **Images**: export actual images from Figma if feasible; fall back to placeholder.com URLs with correct sizing if export is complex
- **Icons**: export as **inline SVG** from Figma and embed directly in the code
- Visual verification (rendered code vs Figma thumbnail comparison) deferred to **Phase 3** when Sandpack exists

### Code Storage & Lifecycle
- Generated code stored in **Supabase immediately** — survives page refresh
- User does **not see raw code** in Phase 2 — just success state; code viewer/preview comes later
- **Regenerate overwrites** previous code (V1) — version history deferred to future version
- Success state: Figma thumbnail displayed alongside confirmation message

### LLM Strategy
- **V1 model: Gemini 2.5 Pro** (founder has subscription) — good vision + code + long context
- **Post-V1**: Claude's discretion to pick the ideal model for design-to-code quality
- **Prompt approach**: Claude's discretion — optimize for quality and accuracy (two-step analysis+generation if it yields better results, single-shot if sufficient)
- **Output format**: Claude's discretion — optimize for stability, quality, and reliability (single component likely simpler for Sandpack in Phase 3)
- **Validation in Phase 2**: syntax check only (valid JSX parse). Visual comparison added in Phase 3.

### Claude's Discretion
- Prompt structure (single-shot vs two-step) — choose based on what produces best design-to-code output
- Output format (single component vs multi-file) — choose based on Sandpack compatibility and reliability
- Long-term model choice for post-V1
- Server-side design context extraction implementation details (how to structure the Figma API data for LLM consumption)

</decisions>

<specifics>
## Specific Ideas

- Progress storytelling during generation should have a **quirky, playful tone** — not generic loading messages
- The Figma thumbnail is already fetched during import (Phase 1) — reuse it for the success state display and as LLM input
- Server-side context extraction should produce output similar to Figma MCP's `get_design_context` — structured component tree, styles, layout info ready for code generation

</specifics>

<deferred>
## Deferred Ideas

- **Version history for regenerated code** — keep previous generations, allow rollback (future version)
- **Visual verification pipeline** — render generated code to screenshot, compare with Figma thumbnail via LLM vision, auto-iterate on poor match (Phase 3)

</deferred>

---

*Phase: 02-code-generation*
*Context gathered: 2026-02-20*
