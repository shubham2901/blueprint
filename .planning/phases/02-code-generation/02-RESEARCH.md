# Phase 2: Code Generation - Research

**Researched:** 2026-02-20
**Domain:** Design-to-code, Figma API, LLM vision, React/Tailwind code generation
**Confidence:** HIGH

## Summary

Phase 2 adds automatic React + Tailwind code generation from Figma design context after import. The current codebase has a working Figma import (OAuth, nodes fetch, thumbnail) but returns raw Figma REST API data. The gap: (1) no server-side design context extraction that mirrors Figma MCP quality, (2) no code generation pipeline, (3) no DB storage for generated code, (4) no "generating" UI state with progress storytelling. Research recommends: build a design-context transformer that produces LLM-ready structured output from raw Figma nodes; use Gemini 2.5 Pro with base64 thumbnail for vision; validate JSX via esbuild-py; store code in a new `prototype_sessions` table.

**Primary recommendation:** Implement a single-shot generation flow: import → transform design context → call Gemini 2.5 Pro (vision + structured context) → validate JSX → persist to Supabase → show success state. Use a single React component output format for Sandpack compatibility in Phase 3.

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Code generation starts **automatically** after Figma import completes
- While generating: skeleton in preview area + **quirky progress storytelling** (playful tone)
- On failure: **auto-retry once silently**, then friendly error with manual retry
- After generation: success state with Figma thumbnail + "Your prototype is ready" — code not displayed
- **Regenerate button** only after first generation completes
- Send **Figma thumbnail image** to LLM (vision-capable model)
- Build **server-side Figma context extraction** mirroring Figma MCP `get_design_context` quality
- **Near pixel-perfect fidelity** — exact colors, spacing, fonts, sizing
- **Actual text content** from Figma preserved (no lorem ipsum)
- **Images**: export from Figma if feasible; fallback to placeholder.com with correct sizing
- **Icons**: export as **inline SVG** from Figma, embed in code
- Generated code stored in **Supabase immediately**
- User does **not** see raw code in Phase 2
- **Regenerate overwrites** previous code (V1)
- **V1 model: Gemini 2.5 Pro**
- **Validation**: syntax check only (valid JSX parse)

### Claude's Discretion
- Prompt structure (single-shot vs two-step)
- Output format (single component vs multi-file)
- Long-term model choice
- Server-side design context extraction implementation details

### Deferred Ideas (OUT OF SCOPE)
- Version history for regenerated code
- Visual verification pipeline (Phase 3)

</user_constraints>

---

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CODE-01 | System generates React code from Figma design context (Tailwind, functional components) | Design context transformer, Gemini 2.5 Pro vision + structured prompt, JSX validation, single-component output format |

</phase_requirements>

---

## Current Codebase State

### Backend

| File | Purpose | Phase 2 Relevance |
|------|---------|-------------------|
| `api/figma.py` | OAuth + `POST /api/figma/import` | Returns `design_context` (raw Figma API), `thumbnail_url`, frame metadata. **Gap:** No code generation endpoint; design_context is raw, not code-ready |
| `db.py` | Supabase, journeys, figma_tokens | **Gap:** No table for prototype sessions / generated code |
| `models.py` | Pydantic models | **Gap:** No `CodeGenerationRequest`, `CodeGenerationResponse`, or session models |
| `llm.py` | `call_llm`, `call_llm_structured` | Supports text messages. **Gap:** No vision/multimodal support; Gemini 2.5 Pro not in fallback_chain |
| `config.py` | Settings, LLM_CONFIG | Fallback chain: gemini-3-flash, gemini-2.5-flash, etc. **Gap:** Need Gemini 2.5 Pro for vision |
| `prompts.py` | Research prompts | **Gap:** No design-to-code prompt |

### Figma Import Response Shape

```python
# From figma.py — design_context is the raw Figma API response
FigmaImportResponse(
    design_context={
        "nodes": {
            "123:456": {
                "document": {
                    "id": "...",
                    "name": "Frame 1",
                    "type": "FRAME",
                    "children": [...],
                    "absoluteBoundingBox": {"x", "y", "width", "height"},
                    "layoutMode": "HORIZONTAL" | "VERTICAL" | None,
                    "itemSpacing": 10,
                    "paddingLeft", "paddingRight", "paddingTop", "paddingBottom",
                    "fills": [...],
                    "strokes": [...],
                    "effects": [...],
                    # TEXT nodes: characters, style (fontFamily, fontSize, fontWeight, etc.)
                    # RECTANGLE, ELLIPSE, VECTOR, etc.
                }
            }
        },
        "components": {...},  # Component definitions
        "styles": {...}     # Shared styles
    },
    thumbnail_url="https://...",  # PNG from GET /v1/images/:key?ids=...&format=png
    frame_name, frame_width, frame_height, child_count, warnings
)
```

The raw `document` tree has all layout, style, and text data but is verbose and not optimized for LLM consumption. Figma MCP `get_design_context` produces a transformed, code-ready structure (layout props, typography, colors, component tree).

### Frontend

| File | Purpose | Phase 2 Relevance |
|------|---------|-------------------|
| `page.tsx` | Build shell, view state machine | States: `landing` \| `paste` \| `importing` \| `success` \| `error`. **Gap:** Need `generating` state; success must show "Your prototype is ready" + Regenerate |
| `ImportingView.tsx` | Skeleton + "Importing your frame..." | **Gap:** Need `GeneratingView` with quirky progress messages |
| `FramePreview.tsx` | Success: thumbnail, metadata, "Import another" | **Gap:** Add "Your prototype is ready", Regenerate button; remove "Code generation coming in Phase 2" |
| `api.ts` | `importFigmaFrame`, `getFigmaStatus` | **Gap:** Need `generateCode(importId?)`, `regenerateCode(sessionId)` or similar |

### DB Schema Gap

No table exists for prototype sessions. REQUIREMENTS.md SESS-02 references `prototype_sessions`. Phase 2 needs at minimum:

- `session_id` (or `import_id`) — links to a single import
- `design_context` (JSONB)
- `generated_code` (TEXT)
- `thumbnail_url`, `frame_name`, `frame_width`, `frame_height`
- `created_at`, `updated_at`
- Owner: `session_id` (cookie) or `user_id` (when auth exists)

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| litellm | ≥1.55 | LLM calls, multimodal | Already in use; supports Gemini vision with base64 images |
| httpx | ≥0.28 | HTTP client | Already used for Figma API |
| Pydantic v2 | ≥2.10 | Models, validation | Already in use |
| supabase | ≥2.11 | DB client | Already in use |

### New for Phase 2

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| esbuild-py | latest | JSX syntax validation | Validate generated React code before persisting |

**Installation:**
```bash
pip install esbuild-py
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| esbuild-py | subprocess npx esbuild | esbuild-py is pure Python; subprocess requires Node in backend container |
| esbuild-py | @babel/parser via Node | Babel requires Node; esbuild-py keeps validation in Python |
| Gemini 2.5 Pro | GPT-4V / Claude Vision | Founder has Gemini subscription; litellm supports all |

---

## Architecture Patterns

### Recommended Flow

```
1. Frontend: importFigmaFrame() → success
2. Frontend: immediately POST /api/code/generate { design_context, thumbnail_url, frame_metadata }
3. Backend: transform design_context → code-ready format
4. Backend: fetch thumbnail → base64
5. Backend: call_llm_vision(messages with image + structured context)
6. Backend: validate JSX (esbuild-py)
7. Backend: on valid → upsert prototype_sessions; on invalid → retry once, then error
8. Backend: return { session_id, status: "ready" } or { status: "error", error_code }
9. Frontend: polling or SSE for progress (Phase 2: polling simpler; 10–30s is acceptable)
```

### Design Context Transformer

**What:** Convert raw Figma `nodes` + `document` tree into a compact, LLM-friendly structure.

**When:** Before every code generation call.

**Structure to produce (example):**
```json
{
  "frame": { "width": 375, "height": 812, "name": "Login" },
  "tree": [
    {
      "id": "1",
      "type": "FRAME",
      "name": "Login",
      "layout": { "mode": "VERTICAL", "gap": 16, "padding": 24 },
      "children": [
        {
          "id": "2",
          "type": "TEXT",
          "content": "Welcome back",
          "style": { "fontFamily": "Inter", "fontSize": 24, "fontWeight": 700, "color": "#1a1a1a" }
        },
        {
          "id": "3",
          "type": "RECTANGLE",
          "style": { "fill": "#e07c4c", "cornerRadius": 8, "width": 200, "height": 44 }
        }
      ]
    }
  ],
  "components": {},
  "styles": {}
}
```

**Key extractions:** `absoluteBoundingBox`, `layoutMode`, `itemSpacing`, padding, `fills`, `characters` (text), `fontFamily`, `fontSize`, `fontWeight`, `lineHeightPx`, color from fills. Flatten deep nesting for readability; preserve hierarchy for layout.

### LLM Vision Message Format (litellm)

Gemini via `gemini/` prefix requires base64 for images (not URLs). Message format:

```python
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "Generate React + Tailwind code for this design..."},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
            }
        ]
    }
]
```

Source: litellm docs, Gemini provider. Use `content` as list of parts for multimodal.

### Anti-Patterns to Avoid

- **Raw Figma dump to LLM:** Do not send the full `design_context` JSON. It is huge and noisy. Transform first.
- **Skipping thumbnail:** Vision models perform better with the image. Always include it.
- **No retry on failure:** Context requires one silent retry before surfacing error.
- **Showing code in Phase 2:** User sees success state only; code viewer is Phase 3.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSX parsing | Custom regex or AST | esbuild-py | JSX has many edge cases; esbuild handles them |
| Figma design parsing | Custom traversal from scratch | Structured transformer over existing nodes | Figma schema is complex; reuse known structure |
| Image export from Figma | Custom renderer | Figma REST `GET /v1/images/:key` | Official API returns PNG/SVG URLs |
| Multimodal LLM calls | Custom Gemini client | litellm | Handles provider differences, fallbacks |

**Key insight:** Design-to-code is a well-studied problem. Use existing parsers and APIs; focus effort on prompt engineering and context quality.

---

## Figma Image/SVG Export

### REST API

**Endpoint:** `GET https://api.figma.com/v1/images/:file_key`

**Query params:**
- `ids`: Comma-separated node IDs (e.g. `123:456,123:457`)
- `format`: `png` | `jpg` | `svg` | `pdf`
- `scale`: 1, 2, 3, 4 (for raster)
- `svg_include_id`: boolean (SVG)
- `svg_simplify_stroke`: boolean (SVG)

**Response:**
```json
{
  "err": null,
  "images": {
    "123:456": "https://s3-us-west-2.amazonaws.com/figma-alpha-api/...",
    "123:457": "https://..."
  }
}
```

**Current usage:** `figma.py` already calls this for PNG thumbnail at scale 2. Same endpoint supports `format=svg` for icons.

**Strategy for icons:**
1. Traverse document tree, identify nodes with `type: "VECTOR"` or `type: "BOOLEAN_OPERATION"` (icons)
2. Call `GET /v1/images/:key?ids=id1,id2,...&format=svg` for those node IDs
3. Fetch each SVG URL, embed as inline string in generated code

**Strategy for images:**
1. Identify nodes with `fills` containing `type: "IMAGE"` and `imageRef`
2. Use `GET /v1/files/:key/images` (image fills endpoint) to resolve imageRef → URL, or export node as PNG
3. Fallback: use `placeholder.com/widthxheight` with correct dimensions from `absoluteBoundingBox`

**Rate limits:** Figma API has rate limits; batch node exports where possible. One images request per frame is typical for thumbnail; additional requests for icons/images add latency.

---

## Design-to-Code LLM Best Practices

### Single-Shot vs Two-Step

| Approach | Pros | Cons |
|----------|------|------|
| Single-shot | Simpler, faster, one round-trip | May miss nuances on complex frames |
| Two-step (analyze → generate) | Can improve layout/structure | 2x latency, 2x cost; marginal gain for simple frames |

**Recommendation:** Start with single-shot. Design2Code benchmark (2024) shows GPT-4V can replace designs in ~49% of cases with one pass. For Phase 2 scope (single frame, Tailwind, functional components), single-shot is sufficient. Revisit two-step if quality is inadequate.

### Prompt Structure

Include:
1. **Role:** "You are a design-to-code expert. Generate React + Tailwind code that matches the provided design."
2. **Constraints:** Tailwind only, functional components, no lorem ipsum, preserve exact text, use inline SVG for icons, placeholder.com for images if needed.
3. **Output format:** Single React component, default export, valid JSX.
4. **Design context:** The transformed structured JSON (not raw Figma).
5. **Image:** The Figma thumbnail (base64).

### Output Format

**Single component preferred** for Phase 2:
- Simpler for Sandpack in Phase 3 (one file)
- Easier validation (one parse)
- Regenerate overwrites one blob

**Multi-file** deferred: adds complexity for routing, imports; not needed for single-frame scope.

### Model Choice

- **V1:** Gemini 2.5 Pro (per CONTEXT.md). Supports vision, long context (1M tokens), code generation.
- **litellm model string:** `gemini/gemini-2.5-pro` or `gemini/gemini-2.5-pro-preview` (verify exact name in litellm docs).
- Add to config as primary for code generation; can use separate config key from research fallback chain.

---

## Code Validation

### Approach: esbuild-py

```python
from esbuild import transform

def validate_jsx(code: str) -> tuple[bool, str | None]:
    """Return (valid, error_message)."""
    try:
        transform(code, loader="tsx")
        return True, None
    except Exception as e:
        return False, str(e)
```

**Loader:** Use `tsx` to support both JSX and TypeScript. Phase 2 outputs JSX; `tsx` handles it.

**Note:** esbuild-py may need the code to be a complete module (imports). If the LLM outputs a bare component, wrap: `import React from 'react'; export default function App() { return (...); }` — or instruct the LLM to output a full module.

### Alternative: Subprocess

If esbuild-py has issues:
```bash
echo "$CODE" | npx esbuild --bundle --stdin=tsx --outfile=/dev/null
```
Requires Node in backend environment. Railway backend container may not have Node by default.

---

## Common Pitfalls

### Pitfall 1: Thumbnail URL Expiry
**What goes wrong:** Figma image URLs are signed and expire (often 1 hour).
**Why:** Backend stores thumbnail_url; frontend displays it later; URL may be dead.
**How to avoid:** Either (a) re-fetch thumbnail when loading session, or (b) upload thumbnail to Supabase Storage at generation time and store that URL.
**Warning signs:** Broken image in success state after refresh.

### Pitfall 2: Design Context Too Large
**What goes wrong:** LLM context limit exceeded; truncated or failed request.
**Why:** Raw Figma document can be 100KB+ for complex frames.
**How to avoid:** Transformer must summarize and prune. Limit tree depth, collapse redundant nodes, omit verbose style objects.
**Warning signs:** Token limit errors, truncated responses.

### Pitfall 3: Gemini JSON Mode vs Vision
**What goes wrong:** `response_format: {"type": "json_object"}` can conflict with multimodal or cause empty content.
**Why:** llm.py uses `response_format` for gemini-2.5; code output is not JSON.
**How to avoid:** For code generation, do NOT use `response_format`. Use plain text output; strip markdown fences if present.
**Warning signs:** Empty content, fallback to next provider.

### Pitfall 4: Session Ownership
**What goes wrong:** Anonymous user A's session visible to user B.
**Why:** Session keyed only by cookie; cookie can be shared or lost.
**How to avoid:** Use `bp_session` cookie (already in figma.py) as session_id. Ensure code generation endpoints require same auth pattern (cookie for anonymous).
**Warning signs:** Cross-user data leakage.

---

## Code Examples

### Transform Design Context (Pseudocode)

```python
def transform_design_context(raw: dict) -> dict:
    nodes = raw.get("nodes", {})
    result = {"frame": {}, "tree": [], "components": raw.get("components", {}), "styles": raw.get("styles", {})}
    for node_id, node_data in nodes.items():
        doc = node_data.get("document", {})
        if not doc:
            continue
        result["frame"] = {
            "name": doc.get("name"),
            "width": doc.get("absoluteBoundingBox", {}).get("width"),
            "height": doc.get("absoluteBoundingBox", {}).get("height"),
        }
        result["tree"] = _flatten_node(doc, max_depth=5)
        break  # Single frame
    return result

def _flatten_node(doc: dict, max_depth: int, depth: int = 0) -> list:
    if depth >= max_depth:
        return []
    node = {"id": doc.get("id"), "type": doc.get("type"), "name": doc.get("name")}
    if doc.get("type") == "TEXT":
        node["content"] = doc.get("characters", "")
        node["style"] = _extract_text_style(doc)
    elif doc.get("type") in ("RECTANGLE", "ELLIPSE", "VECTOR"):
        node["style"] = _extract_fill_style(doc)
    if doc.get("layoutMode"):
        node["layout"] = {"mode": doc["layoutMode"], "gap": doc.get("itemSpacing"), "padding": ...}
    node["children"] = [_flatten_node(c, max_depth, depth + 1) for c in doc.get("children", [])]
    return node
```

### Litellm Vision Call (Conceptual)

```python
# Source: https://docs.litellm.ai/docs/completion/vision
import base64
import httpx

async def call_llm_vision(messages: list, image_url: str | None) -> str:
    if image_url:
        async with httpx.AsyncClient() as client:
            r = await client.get(image_url)
            b64 = base64.b64encode(r.content).decode()
        # litellm accepts content as list; image_url.url can be data:image/png;base64,...
        content = messages[0]["content"]
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        content.insert(0, {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
        messages = [{"role": "user", "content": content}] + messages[1:]
    return await call_llm(messages, journey_id=None)
```

Note: Gemini (gemini/ prefix) requires base64; URLs are not supported. Vertex AI supports URLs.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual design handoff | AI design-to-code | 2023–2024 | Design2Code benchmark; GPT-4V, Gemini competitive |
| Screenshot-only input | Structured context + image | 2024 | MCP, Figma API; hybrid improves accuracy |
| Single provider | litellm multi-provider | Ongoing | Fallback chain; use Gemini 2.5 Pro for vision |

**Deprecated/outdated:**
- Relying only on raw Figma JSON without transformation: too verbose for LLM.
- Image URLs for Gemini (gemini/ prefix): must use base64.

---

## Open Questions

1. **Exact litellm multimodal API for Gemini**
   - What we know: litellm supports vision; Gemini needs base64.
   - What's unclear: Exact message format for `content` array with image part.
   - Recommendation: Check litellm completion docs for "image" or "multimodal"; test with a minimal example.

2. **esbuild-py TSX loader**
   - What we know: esbuild supports JSX/TSX.
   - What's unclear: Whether esbuild-py's transform accepts `loader="tsx"` and handles React JSX.
   - Recommendation: Add esbuild-py, run a quick test with sample JSX.

3. **Prototype session table schema**
   - What we know: Need to store code, design_context, thumbnail, metadata.
   - What's unclear: Whether to key by import (ephemeral) or create session at import and update on generate.
   - Recommendation: Create session row when import succeeds; update with generated_code when ready. Session ID from cookie.

---

## Gaps: Current State → Phase 2

| Gap | Location | Action |
|-----|----------|--------|
| No code generation endpoint | Backend | Add `POST /api/code/generate` (or `/api/figma/generate-code`) |
| No design context transformer | Backend | Add `figma/context.py` or similar |
| No prototype_sessions table | DB | Migration: create table |
| No vision LLM path | llm.py | Add `call_llm_vision` or extend `call_llm` for multimodal |
| Gemini 2.5 Pro not in config | config.py | Add code-gen model config |
| No design-to-code prompt | prompts.py | Add `build_design_to_code_prompt` |
| No generating state | Frontend page.tsx | Add `generating` view mode |
| No progress storytelling | Frontend | Add `GeneratingView` with quirky messages |
| No Regenerate button | FramePreview | Add button, wire to regenerate endpoint |
| Success copy | FramePreview | Change to "Your prototype is ready" |
| No code storage/retrieval | api.ts, db | Add generate + get session endpoints |

---

## Sources

### Primary (HIGH confidence)
- Codebase: `backend/app/api/figma.py`, `db.py`, `models.py`, `llm.py`, `config.py`, `prompts.py`
- Codebase: `frontend/app/page.tsx`, `ImportingView.tsx`, `FramePreview.tsx`, `api.ts`
- CONTEXT.md, REQUIREMENTS.md, PLAN.md
- Figma REST API: GET /v1/images/:key (used in figma.py)
- Gemini 2.5 Pro: ai.google.dev, Vertex AI docs — vision, base64 support

### Secondary (MEDIUM confidence)
- litellm Gemini vision: GitHub issues, docs — base64 required for gemini/ prefix
- Design2Code benchmark (2024): single-shot viable for simple frames
- esbuild-py: GitHub — Python bindings for esbuild

### Tertiary (LOW confidence)
- Figma MCP get_design_context output structure: inferred from skill doc; exact schema not verified

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing stack + esbuild-py well-documented
- Architecture: HIGH — flow is straightforward; transformer design is informed by Figma schema
- Pitfalls: MEDIUM — thumbnail expiry, context size are known; litellm multimodal exact API needs verification

**Research date:** 2026-02-20
**Valid until:** 2026-03-20 (30 days for stable APIs)
