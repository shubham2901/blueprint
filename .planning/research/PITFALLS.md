# Domain Pitfalls: Figma-to-Code & AI-Assisted Prototyping

**Domain:** PM prototyping / Figma-to-code / AI code generation  
**Researched:** 2025-02-19  
**Confidence:** MEDIUM (WebSearch + official docs; some findings from 2023–2024)

---

## Critical Pitfalls

### Pitfall 1: Treating Codegen as Full Automation Instead of Augmentation

**What goes wrong:**  
Teams expect Figma-to-code or LLM code generation to produce production-ready, paste-and-ship code. In practice, generated code rarely matches team conventions, design tokens, or existing component APIs. Figma itself pivoted away from automated design-to-code for Dev Mode because developers didn't find the output useful.

**Why it happens:**  
Design tools simulate intent but don't encode feasibility. A finished design creates the illusion that "the hard part is over," when translating design intent to executable code remains heavily manual. LLMs lack project-specific context (component library, tokens, naming conventions).

**Consequences:**  
- Generated code requires significant manual rework; "paste in" updates overwrite prior edits  
- Design-code drift accumulates; subsequent Figma changes can't be cleanly re-applied  
- PMs lose trust when previews break or output doesn't match expectations  

**How to avoid:**  
- Position codegen as "0 to 0.5"—a starting point, not a finished artifact  
- Provide design tokens and component mapping (Code Connect–style) to the LLM  
- Use semantic layer names in Figma; avoid `Frame1268`, `Group5`  
- Store and expose "last working version" for fallback when generation fails  

**Warning signs:**  
- Promising "one-click export" or "fully automated handoff"  
- No fallback path when preview breaks  
- LLM prompts lack design system context (tokens, component names)  

**Phase to address:** Phase 1 (Import) + Phase 2 (Code Generation). Establish design-system context and fallback behavior from day one.

---

### Pitfall 2: Figma Import Without Structure Requirements

**What goes wrong:**  
Importing arbitrary Figma frames yields poor code. Plugins like Builder.io and Anima struggle with complex designs: hardcoded pixels, `position: absolute` for auto-layout, broken component variants, vendor-specific classes. Generated code often breaks on mobile due to hardcoded breakpoints.

**Why it happens:**  
Figma files vary wildly. Default layer names (`Frame1268`), missing components, no Auto Layout, and lack of variables/tokens give the LLM no semantic signal. The MCP/API returns raw structure; AI must guess intent.

**Consequences:**  
- Brittle, non-responsive output  
- No reusable components—repetitive markup  
- Preview breaks on resize or different viewports  

**How to avoid:**  
- Document and enforce Figma structure: components, Auto Layout, variables, semantic names  
- Validate imported frame before generation (e.g., check for components, variables)  
- Use Figma Variables for spacing/color/radius; map to Tailwind or design tokens  
- Prefer single-frame import in V1; avoid multi-frame complexity until structure is solid  

**Warning signs:**  
- Accepting any frame URL without structure checks  
- No guidance for PMs on "what makes a good Figma frame"  
- Absolute positioning and hardcoded px in generated code  

**Phase to address:** Phase 1 (Figma Import). Add structure validation and PM-facing import guidelines.

---

### Pitfall 3: LLM Code Output Without Validation or Fallback

**What goes wrong:**  
LLM-generated code frequently has non-syntactic bugs: wrong input types, hallucinated objects, missing corner cases, incomplete generation. Models struggle to detect their own mistakes (low F1 on error detection). Code may compile but crash at runtime or behave incorrectly.

**Why it happens:**  
Specification misunderstanding, incomplete examples, external dependency confusion, knowledge gaps between similar APIs. LLMs optimize for plausibility, not correctness.

**Consequences:**  
- Live preview breaks; PM sees blank or error state  
- No recovery path; session feels "lost"  
- Repeated failures erode trust in the tool  

**How to avoid:**  
- Implement retry-then-fallback: on preview error, retry generation once; if still broken, restore last working version  
- Persist last working code per session; never lose work on bad generation  
- Validate LLM output (syntax, basic structure) before sending to Sandpack  
- Surface friendly error + ref code; never raw stack traces or provider names  

**Warning signs:**  
- Preview breaks and stays broken  
- No "last working version" storage  
- Raw LLM errors shown to user  

**Phase to address:** Phase 3 (Chat & Live Preview). Retry + fallback is a V1 requirement per PROJECT.md.

---

### Pitfall 4: Design Token Drift and Primitive-Only Tokens

**What goes wrong:**  
Design tokens are often implemented halfway: Figma variables exist but aren't integrated into codegen. AI receives only primitive tokens (`red-6`, `space-4`) without semantic intent, leading to wrong usage (e.g., `blue-5` instead of `color-feedback-error`).

**Why it happens:**  
Designers want Figma as source of truth; developers prefer code. Token naming differs between design and dev. Most token systems are human-oriented, not AI-readable.

**Consequences:**  
- Generated code uses wrong colors, spacing, typography  
- Inconsistent UI; design system violations  
- Manual fixes required for every generation  

**How to avoid:**  
- Use Figma Variables for tokens; ensure they're exposed in API/MCP context  
- Provide semantic token descriptions to LLM (e.g., `color-feedback-error` for error states)  
- Single source of truth: `tokens.json` or Tailwind config; reference in prompts  
- Document token usage in design system; include in LLM system prompt  

**Warning signs:**  
- Hardcoded hex/spacing in generated code  
- No token mapping in Figma import or LLM context  
- Design and code use different naming  

**Phase to address:** Phase 1 (Import) + Phase 2 (Code Generation). Token mapping must be part of import and prompt design.

---

### Pitfall 5: Live Preview Race Conditions and Sandpack Limitations

**What goes wrong:**  
Sandpack has race conditions when files update during recompile—updates can be ignored, preview shows stale content. Sandpack 2.0's Nodebox and `eval("this")` require `unsafe-eval` in CSP, weakening security. Blank preview panels and auto-update interference are reported.

**Why it happens:**  
Async code generation + synchronous bundler; rapid chat-driven updates; iframe isolation constraints.

**Consequences:**  
- Preview out of sync with latest code  
- CSP conflicts in production  
- PM confusion: "I asked for X but see Y"  

**How to avoid:**  
- Debounce or queue updates to Sandpack; avoid rapid-fire replacements  
- Use Sandpack's recommended update patterns; check for open issues (e.g., race condition #1181)  
- Plan CSP strategy early; consider Sandpack's `unsafe-eval` requirement  
- Show loading/compiling state; don't flash stale then new  

**Warning signs:**  
- Updates during compile get dropped  
- CSP errors in console  
- No debouncing of LLM stream → preview pipeline  

**Phase to address:** Phase 3 (Chat & Live Preview). Debounce and update ordering must be designed in.

---

### Pitfall 6: Session Persistence Without Clear State Boundaries

**What goes wrong:**  
Sessions mix ephemeral UI state (current chat, scroll position) with durable artifacts (generated code, Figma frame ref). On reload or new visit, users lose context or get inconsistent state. Transcript-based architectures (e.g., Goa-AI) treat transcripts as source of truth; ad-hoc state management causes bugs.

**Why it happens:**  
State types are conflated: business data (server-owned), UI state (ephemeral), cross-session state (durable). Without separation, persistence logic becomes brittle.

**Consequences:**  
- "I came back and my prototype was gone"  
- Chat history and code out of sync  
- Duplicate or orphaned sessions  

**How to avoid:**  
- Separate: (1) session metadata + code + Figma ref (persist), (2) chat transcript (persist), (3) UI state (ephemeral)  
- Session cookie + DB storage; fetch session on load; restore code and chat  
- Store last working code; restore on session resume  
- Define "session end" (e.g., "done"/"thank you") and persist final state  

**Warning signs:**  
- No clear persistence contract  
- UI state mixed with persisted data  
- Session resume doesn't restore code/preview  

**Phase to address:** Phase 4 (Session Persistence). State boundaries must be defined before implementation.

---

## Moderate Pitfalls

### Pitfall 7: Overpromising Responsive Behavior

**What goes wrong:**  
Generated code uses hardcoded breakpoints, absolute positioning, or desktop-only layout. Mobile Safari and smaller viewports break. Design-to-code tools often ignore responsive requirements.

**Prevention:**  
Use Auto Layout in Figma; generate mobile-first Tailwind (e.g., `md:`, `lg:`). Test preview at multiple widths. Document responsive expectations for PMs.

**Phase to address:** Phase 2 (Code Generation).

---

### Pitfall 8: Figma API and Plugin Constraints Underestimated

**What goes wrong:**  
100 KB plugin data limit; CORS and `origin: null` for network requests; no direct DOM/XMLHttpRequest. OAuth flows are clunky. Large files hit 413 on Code Connect uploads.

**Prevention:**  
Use Figma REST API (not plugin) for import where possible. Chunk large exports; use `--batch-size` for Code Connect. Plan OAuth and CORS early.

**Phase to address:** Phase 1 (Figma Import).

---

### Pitfall 9: No Component Mapping (Code Connect Gap)

**What goes wrong:**  
Without Code Connect or equivalent, the LLM guesses component usage. Output doesn't match real component APIs, props, or variants. "The model is guessing."

**Prevention:**  
If Code Connect isn't available, provide explicit component docs/props to LLM. Use semantic Figma names that map to code. Custom instructions for team conventions.

**Phase to address:** Phase 1 (Import) + Phase 2 (Code Generation).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip design token mapping | Faster V1 ship | Every generation wrong; manual fixes | Never for production-quality output |
| Accept any Figma structure | No import validation | Poor code; constant breakage | Never; add minimal validation |
| No last-working-version fallback | Simpler state | Lost work on LLM failure | Never; V1 requirement |
| Hardcode Tailwind/component lib | Quick start | Lock-in; hard to change | V1 only; plan abstraction |
| Single retry, no fallback | Less code | Poor UX on transient failures | Never; retry + fallback required |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Figma API | Assuming plugin storage for large data | Use REST API; 100 KB limit for plugin data |
| Figma OAuth | Manual token passing, no refresh | Use standard OAuth flow; handle token refresh |
| Sandpack | Rapid file updates during compile | Debounce; queue updates; check race condition issues |
| LLM (Vercel AI SDK) | Streaming raw output to preview | Validate output; apply only when valid |
| Supabase session | Mixing UI state with persisted | Separate session/artifacts from ephemeral UI |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Unbounded chat context | Slow responses; token limit | Summarize or truncate; limit turns | ~20+ turns with full history |
| Large Figma frame import | Timeout; 413 | Single frame; validate size; chunk if needed | Frames with many layers |
| No debounce on chat → code | Preview flicker; race conditions | Debounce 300–500 ms | Rapid successive messages |
| Storing full code history | DB bloat; slow load | Store only current + last working | 100+ sessions |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Raw error on preview break | Confusion; loss of trust | "Preview couldn't load. We've restored your last version. (Ref: BP-XXXXX)" |
| No feedback during generation | "Is it working?" | Streaming progress; "Generating…" state |
| Session lost on refresh | "I lost everything" | Persist session; restore on load |
| Copy code fails silently | Frustration | Confirm copy; show snippet preview |

---

## "Looks Done But Isn't" Checklist

- [ ] **Figma Import:** Often missing structure validation — verify components, Auto Layout, variables before generation
- [ ] **Code Generation:** Often missing design token context — verify tokens in LLM prompt
- [ ] **Live Preview:** Often missing fallback — verify last-working-version restore on error
- [ ] **Session Persistence:** Often missing state boundaries — verify chat + code + metadata all persist correctly
- [ ] **Retry Logic:** Often missing — verify retry-then-fallback, not just retry
- [ ] **Error Display:** Often shows raw errors — verify friendly message + ref code only

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Preview breaks (LLM bad output) | LOW | Retry once; restore last working version; log error_code |
| Session lost | MEDIUM | Restore from DB by session cookie; re-fetch Figma if needed |
| Figma structure poor | MEDIUM | Re-import with guidelines; or prompt PM to fix frame |
| Token drift | HIGH | Re-establish token mapping; regenerate with correct context |
| Sandpack race condition | LOW | Debounce; ensure update order; file issue if upstream |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Codegen as automation | Phase 1–2 | PM docs say "starting point"; fallback exists |
| Figma structure | Phase 1 | Import validates components/variables or warns |
| LLM validation + fallback | Phase 3 | Preview error → retry → restore last working |
| Design token drift | Phase 1–2 | Tokens in prompt; no hardcoded hex in output |
| Sandpack race conditions | Phase 3 | Debounce in place; no dropped updates |
| Session persistence | Phase 4 | Reload restores code + chat; state boundaries clear |
| Responsive behavior | Phase 2 | Auto Layout in Figma; mobile-first in output |
| Figma API limits | Phase 1 | Single frame; no 413; OAuth tested |
| Component mapping | Phase 1–2 | Code Connect or explicit component docs to LLM |

---

## Sources

- [Figma: What Codegen Is (Actually) Good For](https://www.figma.com/blog/what-codegen-is-actually-good-for) — Figma's official stance: codegen as augmentation, not automation
- [Figma Developer Docs: Structure Your Figma File](https://developers.figma.com/docs/figma-mcp-server/structure-figma-file/) — Components, variables, Auto Layout, semantic names
- [Figma Developer Docs: Code Connect Common Issues](https://developers.figma.com/docs/code-connect/common-issues/) — 413 errors, batch size, connectivity
- [Figma to Tailwind: Common Mistakes](https://code.devpractical.com/blog/figma-to-tailwind-common-mistakes-designers-make/) — Utility-first, spacing scale, component structure
- [LLM Code Generation Mistakes (arXiv 2411.01414)](https://arxiv.org/abs/2411.01414) — Seven error categories; self-detection limitations
- [Bugs in LLM-Generated Code (arXiv 2403.08937)](https://arxiv.org/abs/2403.08937) — 10 bug patterns: hallucination, wrong types, incomplete
- [Design Tokens That AI Can Read](https://learn.thedesignsystem.guide/p/design-tokens-that-ai-can-actually) — Semantic vs primitive tokens
- [Sandpack Race Condition #1181](https://github.com/codesandbox/sandpack/issues/1181) — Updates during recompile ignored
- [Sandpack CSP / unsafe-eval](https://github.com/codesandbox/sandpack/issues/1221) — Security concern
- [Why Design-to-Code Often Fails](https://codingit.dev/2025/05/16/why-design-to-code-often-fails/) — Overpromise, hidden complexity
- [Figma Plugin Constraints](https://noteui.blog/posts/hidden-headaches-building-figma-plugins) — 100 KB limit, CORS, network
- PROJECT.md — Blueprint PM requirements (retry + fallback, session persistence, V1 scope)

---
*Pitfalls research for: Figma-to-code + AI-assisted PM prototyping*  
*Researched: 2025-02-19*
