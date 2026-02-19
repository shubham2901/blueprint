# Phase 1: Shell + Landing + Figma Import — Research

**Researched:** 2025-02-19
**Domain:** Figma OAuth + REST API, Next.js shell, route restructure
**Confidence:** HIGH (Figma docs verified); MEDIUM (OAuth callback + token storage patterns)

## Summary

Phase 1 delivers the Blueprint PM shell (layout from designs), Figma OAuth connection, and design context import for a single frame. The technical path is clear: Figma REST API v1 with OAuth 2 for user-scoped access, `GET /v1/files/:key?ids=...` or `GET /v1/files/:key/nodes?ids=...` for frame JSON, and URL parsing for `file_key` and `node_id` from `https://figma.com/design/:file_key/:file_name?node-id=X-Y`. The backend must host the OAuth callback (token exchange within 30 seconds); tokens are exchanged server-side. Frontend route restructure: Build at `/`, Research at `/research` (existing explore/dashboard move under `/research`).

**Primary recommendation:** Use Figma OAuth 2 with backend callback; store tokens in Supabase (or session cookie for V0); parse Figma URLs with regex; use `httpx` for REST calls (no figmapy needed). Implement OAuth flow and import endpoint before wiring UI.

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Primary color:** `#C27B66` (Cozy Sand). Single source of truth in `frontend/app/globals.css` — change `--primary-hex` in `:root` to update app-wide.
- **Design reference:** `designs/screen-01.html` through `designs/screen-04.html`. Match layout and structure; colors come from globals.css.
- **Tabs:** Research | Blueprint | Build
  - Research — Opens research tab. Research is the existing app (competitive intelligence). Blueprint is a sub-tab within Research.
  - Build — PM prototyping tool. Active tab for this phase.
  - Research tab navigates to existing research routes; Build shows the PM tool.
- **Connect vs Paste Order:** If user pastes URL before connecting Figma, show prompt: "Connect with Figma to import this frame." User must complete OAuth before import proceeds. Flow: paste URL first → detect no connection → show Connect CTA. After OAuth, import runs (or user clicks Import again).
- **Error Handling:** User-facing friendly message only. Every error includes `error_code` (e.g. `BP-3F8A2C`) from `generate_error_code()`. Internal doc: `docs/ERROR_CODES.md`. Pattern: `log("ERROR", ..., error_code=code)` + include in response. Frontend shows `(Ref: BP-XXXXXX)`.

### Claude's Discretion

- Layout: main area (65%) + sidebar (35%), Cursor-like. Sidebar has chat placeholder "What are you building today?"
- Landing: "Turn your Figma into a working prototype" + "Connect with Figma" CTA
- Import: "Paste your Figma frame URL" + input + Import button. "Need help? Learn how to find your frame URL" link
- Importing: URL readonly, loading skeleton, "Building your prototype..." (Phase 1 ends at design context returned)

### Deferred Ideas (OUT OF SCOPE)

- "How it works" link — content TBD
- "Learn how to find your frame URL" — can link to Figma docs or internal help
- Sign up / session count in sidebar — V1 uses session cookie, no login; can show "1 session" as placeholder or hide

</user_constraints>

---

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 (partial) | Chat in side panel, preview on other side (Cursor-like layout) | Shell layout from designs: main 65% + sidebar 35%; sidebar has chat placeholder |
| UI-02 | Prototype is default at `/`; research tool at separate route (e.g. `/research`) | Next.js route restructure: move current `/` content to `/research`, Build shell at `/` |
| FIGMA-01 | PM can connect Figma via OAuth ("Connect with Figma") | Figma OAuth 2: auth URL → user consent → callback → token exchange (POST to api.figma.com/v1/oauth/token). Scopes: `file_content:read`, `file_metadata:read` |
| FIGMA-02 | PM can paste a Figma frame URL to select what to import | Parse URL: `https://figma.com/design/:file_key/:file_name?node-id=X-Y`. Extract file_key, node_id (convert hyphen to colon for API) |
| FIGMA-03 | System imports a single frame and returns design context (document subtree, components, styles) | `GET /v1/files/:key?ids=...` or `GET /v1/files/:key/nodes?ids=...` with Bearer token. Returns document, components, styles |
| FIGMA-04 | System validates or warns on frame structure (components, Auto Layout, semantic names) before generation | Post-import validation: check for components, variables, Auto Layout in returned JSON. Warn if missing; Phase 1 can return warnings in response |

</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| Figma REST API | v1 | File/nodes JSON, OAuth token exchange | Official API. OAuth 2 for user-scoped access. `file_content:read`, `file_metadata:read` scopes. |
| httpx | (existing) | REST calls to Figma API | Already in backend. No figmapy needed. Bearer token in header. |
| Next.js | 15+ (existing) | Frontend, routing | App Router. Restructure: `/` = Build shell, `/research` = research tool. |
| FastAPI | (existing) | Backend, OAuth callback | Handles token exchange (must be server-side; code expires in 30s). |
| Supabase | (existing) | Token storage (V1) | Store access_token, refresh_token per session. V0: can use encrypted cookie. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| secrets / uuid | stdlib | state param for OAuth | Generate random state; validate on callback to prevent CSRF |
| base64 | stdlib | Basic auth for token exchange | `client_id:client_secret` Base64 for Authorization header |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | figmapy | figmapy is unofficial; httpx is sufficient for 2–3 endpoints |
| Backend OAuth callback | Next.js API route | Token exchange must be server-side; FastAPI already handles secrets. Use backend. |
| Supabase for tokens (V0) | Encrypted cookie | Cookie simpler for anonymous V0; Supabase ready for V1 user_id |

**Installation:**

```bash
# No new packages for Phase 1. Backend uses httpx (existing).
# Frontend: no new deps for shell/landing.
```

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/app/
├── page.tsx              # Build shell (new) — tabs, main area, sidebar
├── layout.tsx            # Root layout
├── research/             # Research tool (moved from /)
│   ├── page.tsx          # Research landing (current page.tsx content)
│   ├── explore/[journeyId]/page.tsx
│   └── dashboard/page.tsx
├── globals.css           # --primary-hex, design tokens

backend/app/
├── api/
│   ├── research.py       # Existing
│   ├── journeys.py      # Existing
│   └── figma.py         # NEW: OAuth + import
├── config.py             # Add FIGMA_CLIENT_ID, FIGMA_CLIENT_SECRET, FIGMA_REDIRECT_URI
```

### Pattern 1: Figma OAuth 2 Flow

**What:** Standard authorization code flow. User clicks "Connect with Figma" → redirect to Figma auth URL → user consents → Figma redirects to backend callback with `code` and `state` → backend exchanges code for tokens within 30 seconds.

**When to use:** Any user-scoped Figma API access.

**Example:**

```python
# 1. Generate auth URL (frontend or backend)
auth_url = (
    "https://www.figma.com/oauth?"
    f"client_id={FIGMA_CLIENT_ID}&"
    f"redirect_uri={redirect_uri}&"
    f"scope=file_content:read,file_metadata:read&"
    f"state={state}&"
    "response_type=code"
)

# 2. Callback handler (backend) — MUST exchange within 30 seconds
# POST https://api.figma.com/v1/oauth/token
# Authorization: Basic base64(client_id:client_secret)
# Body: redirect_uri=...&code=...&grant_type=authorization_code
```

Source: [Figma REST API — Authentication](https://developers.figma.com/docs/rest-api/authentication/)

### Pattern 2: Figma URL Parsing

**What:** Extract `file_key` and `node_id` from Figma design URLs. URL format: `https://figma.com/design/:file_key/:file_name?node-id=X-Y`. API expects `ids` as `X:Y` (colon, not hyphen).

**When to use:** User pastes frame URL; validate and extract before import.

**Example:**

```python
import re

def parse_figma_url(url: str) -> tuple[str | None, str | None]:
    """Extract (file_key, node_id) from Figma design URL. node_id in API format (colon)."""
    # https://figma.com/design/ABC123/FileName?node-id=43777-15
    # https://www.figma.com/design/ABC123/FileName?node-id=43777-15
    match = re.match(
        r"https?://[\w.-]*figma\.com/(?:design|file)/([0-9a-zA-Z]{22,128})(?:/.*?)?(?:\?.*?node-id=(\d+-\d+))?",
        url.strip(),
    )
    if not match:
        return None, None
    file_key = match.group(1)
    node_id_raw = match.group(2)
    node_id = node_id_raw.replace("-", ":") if node_id_raw else None
    return file_key, node_id
```

Source: [Figma REST API — File Endpoints](https://developers.figma.com/docs/rest-api/file-endpoints/) (file key from URL); [Figma Forum — node-id format](https://forum.figma.com/ask-the-community-7/how-to-generate-url-to-specific-node-31893)

### Pattern 3: Figma File/Nodes Fetch

**What:** Call `GET /v1/files/:key?ids=...` or `GET /v1/files/:key/nodes?ids=...` with Bearer token. Returns document subtree, components, styles.

**When to use:** After OAuth; user has pasted URL and clicked Import.

**Example:**

```python
async def fetch_figma_frame(access_token: str, file_key: str, node_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.figma.com/v1/files/{file_key}/nodes",
            params={"ids": node_id},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        r.raise_for_status()
        return r.json()
```

Source: [Figma REST API — File Endpoints](https://developers.figma.com/docs/rest-api/file-endpoints/)

### Anti-Patterns to Avoid

- **OAuth in WebView:** Figma does not support WebView. User must use a real browser (redirect or popup).
- **Token exchange on frontend:** Code expires in 30 seconds; client_secret must never leave backend. Exchange only on backend.
- **Skipping state validation:** Always validate `state` on callback to prevent CSRF.
- **Figma MCP for backend:** MCP is for IDE agents (Cursor). Use REST API for server-side import.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|--------|-------------|-------------|-----|
| OAuth flow | Custom OAuth library | Standard HTTP: redirect + POST token exchange | Figma uses standard OAuth 2; 2 endpoints only |
| URL parsing | Ad-hoc string split | Regex (see Pattern 2) | Handles design/file, with/without node-id, www |
| Token storage (V0) | Custom encryption | Encrypted cookie or Supabase | Security; existing patterns |
| Figma API client | Full SDK | httpx + 2–3 endpoints | Only need files, nodes, token exchange |

**Key insight:** Figma integration is small surface area. Hand-rolling OAuth or a full client adds risk; use standard patterns and minimal code.

---

## Common Pitfalls

### Pitfall 1: Token Exchange Timeout (30 Seconds)

**What goes wrong:** Auth code expires 30 seconds after issue. If callback is slow or user is redirected late, exchange fails.

**Why it happens:** Figma enforces short code lifetime for security.

**How to avoid:** Ensure callback URL is fast (no heavy DB writes before exchange). Exchange first, then persist tokens. Log `log("ERROR", "figma token exchange failed", error_code=..., error=str(e))`.

**Warning signs:** "invalid_grant" or similar from token endpoint.

### Pitfall 2: Invalid Figma URL Format

**What goes wrong:** User pastes malformed URL (missing file_key, wrong domain, branch URL). Import fails with unclear error.

**Why it happens:** Figma URLs vary: design/file, with/without node-id, branch URLs.

**How to avoid:** Validate URL with regex before import. Return friendly error: "That doesn't look like a valid Figma frame URL. Check the link and try again. (Ref: BP-XXXXXX)". See `docs/ERROR_CODES.md`.

**Warning signs:** 400 from Figma API; empty or null `ids` param.

### Pitfall 3: CORS / Redirect URI Mismatch

**What goes wrong:** OAuth callback fails because redirect_uri doesn't match exactly what's registered in Figma app.

**Why it happens:** Figma validates redirect_uri character-for-character. Trailing slash, http vs https, port differences all fail.

**How to avoid:** Register exact callback URL in Figma app (e.g. `https://api.yourapp.com/api/figma/oauth/callback`). Use same URL in auth link and token exchange. For local dev: `http://localhost:8000/api/figma/oauth/callback` (if backend serves).

**Warning signs:** Redirect works but token exchange returns error; "redirect_uri_mismatch".

### Pitfall 4: Route Restructure Breaking Links

**What goes wrong:** Moving research from `/` to `/research` breaks existing links, bookmarks, or shared URLs.

**Why it happens:** Route change is breaking for any external references.

**How to avoid:** Add redirect from old paths if needed. Document change. Internal links: update all `href` and `router.push` to `/research`, `/research/explore/...`, `/research/dashboard`.

**Warning signs:** 404 on previously working routes.

### Pitfall 5: Token Storage for Anonymous Users (V0)

**What goes wrong:** V0 has no user accounts. Where to store Figma tokens?

**Why it happens:** OAuth returns tokens per user; we need to associate with "session" without login.

**How to avoid:** Use session cookie (anonymous). Store tokens server-side keyed by session_id. Cookie httpOnly, secure. When user returns, restore tokens from session. V1: migrate to user_id in Supabase.

**Warning signs:** Tokens lost on refresh; multiple tabs overwriting each other.

---

## Code Examples

Verified patterns from official sources:

### OAuth Token Exchange (Backend)

```python
# POST https://api.figma.com/v1/oauth/token
# Content-Type: application/x-www-form-urlencoded
# Authorization: Basic base64(client_id:client_secret)

import base64
import httpx

def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
    credentials = base64.b64encode(
        f"{FIGMA_CLIENT_ID}:{FIGMA_CLIENT_SECRET}".encode()
    ).decode()
    r = httpx.post(
        "https://api.figma.com/v1/oauth/token",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        },
        data={
            "redirect_uri": redirect_uri,
            "code": code,
            "grant_type": "authorization_code",
        },
    )
    r.raise_for_status()
    return r.json()  # access_token, refresh_token, expires_in
```

Source: [Figma REST API — Authentication](https://developers.figma.com/docs/rest-api/authentication/)

### Get File Nodes (Design Context)

```python
async def get_design_context(access_token: str, file_key: str, node_id: str) -> dict:
    # node_id from URL is "43777-15"; API wants "43777:15"
    ids = node_id.replace("-", ":") if "-" in node_id else node_id
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"https://api.figma.com/v1/files/{file_key}/nodes",
            params={"ids": ids},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        r.raise_for_status()
        return r.json()
```

Source: [Figma REST API — File Endpoints](https://developers.figma.com/docs/rest-api/file-endpoints/)

### Frontend: Connect CTA + Paste Flow

```tsx
// Pseudocode for Connect vs Paste order
const [figmaConnected, setFigmaConnected] = useState(false);
const [figmaUrl, setFigmaUrl] = useState("");

const handleImport = () => {
  if (!figmaConnected) {
    // Show: "Connect with Figma to import this frame."
    return;
  }
  // POST /api/figma/import with { url: figmaUrl }
};
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|-------------|------------------|--------------|--------|
| `file_read` scope | `file_content:read`, `file_metadata:read` (granular) | Nov 2025 | New OAuth apps must use granular scopes |
| Personal Access Token for multi-user | OAuth 2 per user | Recommended | PAT rate limited; OAuth is standard |
| Plugin for import | REST API from backend | N/A | Plugin runs in Figma; PM tool runs in browser |

**Deprecated/outdated:**
- Broad `file_read` scope: Use `file_content:read` + `file_metadata:read` for new apps.
- OAuth apps created before Sep 2025: Must re-publish by Nov 17, 2025 per Figma platform updates.

---

## Open Questions

1. **Session cookie vs Supabase for tokens (V0)**
   - What we know: V0 is anonymous; no user_id. Tokens must be stored somewhere.
   - What's unclear: Whether to use encrypted cookie (simpler) or Supabase table keyed by session_id (ready for V1).
   - Recommendation: Use Supabase `figma_tokens` table with `session_id` (from cookie). Enables V1 migration. Table: `session_id`, `access_token`, `refresh_token`, `expires_at`, `created_at`.

2. **Redirect after OAuth: where does user land?**
   - What we know: Callback is backend. Backend must redirect user back to frontend.
   - What's unclear: Redirect to `/` (Build) or preserve prior URL (e.g. if they had pasted URL).
   - Recommendation: Redirect to `/?figma_connected=1` or `/?figma_connected=1&return=import` so frontend can show success and optionally auto-trigger import if URL was pasted.

3. **FIGMA-04 validation depth**
   - What we know: Validate components, Auto Layout, semantic names. Phase 1 can return warnings.
   - What's unclear: How strict? Block import or just warn?
   - Recommendation: Never block. Return design context + optional `warnings: string[]` (e.g. "No components found", "Layer names may be generic"). UI can show subtle warning badge.

---

## Sources

### Primary (HIGH confidence)

- [Figma REST API — Authentication](https://developers.figma.com/docs/rest-api/authentication/) — OAuth 2 flow, token exchange, refresh
- [Figma REST API — File Endpoints](https://developers.figma.com/docs/rest-api/file-endpoints/) — GET file, GET nodes, URL parsing
- [Figma REST API — Scopes](https://developers.figma.com/docs/rest-api/scopes/) — file_content:read, file_metadata:read

### Secondary (MEDIUM confidence)

- [Figma Forum — node-id format](https://forum.figma.com/ask-the-community-7/how-to-generate-url-to-specific-node-31893) — URL vs API format (hyphen vs colon)
- `.planning/research/STACK.md` — Stack recommendations, Figma integration
- `.planning/research/PITFALLS.md` — Figma API constraints, OAuth gotchas
- `docs/ERROR_CODES.md` — Figma error scenarios, user messages

### Tertiary (LOW confidence)

- WebSearch: Figma URL parse file_key node_id — regex patterns; verify against official URL format

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Figma docs, existing backend stack
- Architecture: MEDIUM — OAuth + token storage patterns from docs; session handling is project-specific
- Pitfalls: HIGH — Documented in Figma docs and project research

**Research date:** 2025-02-19
**Valid until:** ~30 days (Figma API stable; OAuth platform updates may continue)

---

## RESEARCH COMPLETE

**Phase:** 1 - Shell + Landing + Figma Import
**Confidence:** HIGH

### Key Findings

1. **Figma OAuth 2** — Auth URL → user consent → callback with `code` + `state`. Token exchange via POST to `api.figma.com/v1/oauth/token` with Basic auth. Code expires in 30 seconds; exchange must be server-side.
2. **Figma REST API** — `GET /v1/files/:key/nodes?ids=X:Y` returns document subtree, components, styles. Bearer token in header. Parse URL for `file_key` and `node_id` (convert `node-id=43777-15` to `43777:15`).
3. **Route restructure** — Build at `/`, Research at `/research`. Move `page.tsx` (research landing), `explore/`, `dashboard/` under `research/`.
4. **Token storage (V0)** — Use Supabase table keyed by session_id (from cookie) or encrypted cookie. Enables V1 user_id migration.
5. **Error handling** — Follow `docs/ERROR_CODES.md`: friendly messages + `(Ref: BP-XXXXXX)`. Figma-specific: OAuth cancelled, OAuth failed, invalid URL, import failed.

### File Created

`.planning/phases/01-shell-landing-figma-import/01-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Figma docs, httpx, Next.js, FastAPI verified |
| Architecture | MEDIUM | OAuth flow clear; session/token storage has options |
| Pitfalls | HIGH | 30s code expiry, redirect_uri, URL parsing documented |

### Open Questions

- Session storage choice (Supabase vs cookie) — recommend Supabase for V1 path
- Post-OAuth redirect target — recommend `/?figma_connected=1`
- FIGMA-04 validation strictness — recommend warn-only, never block

### Ready for Planning

Research complete. Planner can now create PLAN.md files.
