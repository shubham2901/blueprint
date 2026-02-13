# Blueprint — Technical Architecture

This document contains all architecture decisions, data flow details, error handling strategies, and protocol specifications for Blueprint V0. It is the single source of truth for how the system works technically.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Decision Records (ADRs)](#architecture-decision-records)
3. [Data Flow](#data-flow)
4. [LLM Architecture](#llm-architecture)
5. [SSE Streaming Protocol](#sse-streaming-protocol)
6. [Journey Step Schemas](#journey-step-schemas)
7. [Error Handling Strategy](#error-handling-strategy)
8. [Caching Strategy](#caching-strategy)
9. [Request Deduplication](#request-deduplication)
10. [Design Token Architecture](#design-token-architecture)
11. [Deployment Architecture](#deployment-architecture)
12. [Security Considerations](#security-considerations)
13. [Future Extensibility](#future-extensibility)

---

## 1. System Overview

Blueprint is a two-service monorepo deployed on Railway. The frontend (Next.js) and backend (FastAPI) are cleanly separated — they communicate only via REST API + Server-Sent Events (SSE). The frontend has a single environment variable pointing to the backend URL. All business logic, external API calls, and database access happen on the backend.

### Architecture Diagram

```
                           ┌─────────────────────────────────────────┐
                           │            Railway Project               │
                           │                                          │
  User's Browser           │  ┌──────────────┐   ┌────────────────┐ │
  ┌──────────────┐         │  │  Service 1:   │   │  Service 2:    │ │
  │              │  HTTPS   │  │  Next.js FE   │──▶│  FastAPI BE    │ │
  │  Next.js App │◄────────┤  │  (port 3000)  │SSE│  (port 8000)   │ │
  │  (browser)   │         │  │               │   │                │ │
  │              │         │  │  - Pages       │   │  - llm.py      │ │
  └──────────────┘         │  │  - Components  │   │  - search.py   │ │
                           │  │  - API client  │   │  - scraper.py  │ │
                           │  │  - No secrets  │   │  - prompts.py  │ │
                           │  │  - No DB calls │   │  - db.py       │ │
                           │  └──────────────┘   │  - models.py   │ │
                           │                      └───────┬────────┘ │
                           └──────────────────────────────┼──────────┘
                                                          │
                              ┌───────────────────────────┼───────────────────┐
                              │                           │                    │
                         ┌────▼─────┐            ┌───────▼───────┐    ┌──────▼───────┐
                         │ Supabase │            │ LLM Providers │    │ External APIs│
                         │ (Postgres│            │               │    │              │
                         │  only,   │            │ - Gemini Flash│    │ - Tavily     │
                         │  no Auth │            │ - GPT-4o-mini │    │ - Serper     │
                         │  in V0)  │            │ - Claude Haiku│    │ - DuckDuckGo │
                         └──────────┘            └───────────────┘    │ - Jina Reader│
                                                                      └──────────────┘
```

### Key Principle: All Data Flows Through Backend

The frontend communicates exclusively with the FastAPI backend. It never calls Supabase, LLM APIs, search APIs, or scraping APIs directly. This means:

- All API keys live on the backend only
- The frontend has a single env var: `NEXT_PUBLIC_API_URL`
- Swapping any external service requires zero frontend changes
- The backend is the only source of truth for data

---

## 2. Architecture Decision Records

### ADR-1: Fully Anonymous V0

**Status**: Accepted

**Context**: V0 is for validating the product concept. Auth adds complexity (OAuth flows, session management, token refresh, RLS policies) that slows vibecoding velocity without adding product value at this stage.

**Decision**: V0 has no authentication, no user accounts, no session tracking, and no IP-based limits. Every visitor gets full unrestricted access.

**Consequences**:
- Anyone can use the tool without friction — good for testing and feedback
- No way to limit abuse (addressed by global rate limiting via slowapi)
- Journeys are anonymous — no way to associate them with a returning user
- When auth is added in V1, anonymous journeys become orphaned (acceptable — V0 data is test data)
- Auth migration path: add `user_id` column to `journeys` table, add Supabase Auth, add JWT middleware. No schema breaking changes needed.

**Deferred to V1**: Google OAuth, magic link email, anonymous session migration, session limits, Row Level Security.

---

### ADR-2: Free Tier Only

**Status**: Accepted

**Context**: V0 needs one working LLM integration, not a tier system. The tier architecture (free/smart/advanced with different models per tier) is a V1 concern tied to monetization.

**Decision**: V0 uses a single model: Gemini 2.0 Flash via litellm, with a fallback chain to other free/cheap models. The LLM configuration is a Python dict in `config.py`, not a YAML file.

**Config structure (V0)**:
```python
LLM_CONFIG = {
    "persona": {
        "name": "Blueprint",
        "system_prompt": (
            "You are Blueprint, a product and market research assistant for B2C software. "
            "You help product managers and founders explore competitive landscapes, identify market gaps, "
            "and define focused problem statements.\n\n"
            "Guidelines:\n"
            "- Be concise and structured. Use bullet points for features and comparisons.\n"
            "- Always cite sources when referencing specific data. If information is unavailable, say so — never fabricate.\n"
            "- Output strictly valid JSON when instructed. No markdown code fences, no explanation text outside the JSON.\n"
            "- Stay within your domain: product strategy, market research, and competitive analysis. "
            "Decline requests for code generation, homework, creative writing, or general knowledge.\n"
            "- When analyzing products, be balanced — acknowledge both strengths and weaknesses.\n"
            "- Ground all claims in provided data. Do not speculate beyond what the evidence supports."
        ),
    },
    "temperature": 0.3,
    "max_tokens": 2000,
    "fallback_chain": [
        "gemini/gemini-2.0-flash",      # Primary — free tier
        "openai/gpt-4o-mini",            # Fallback 1 — cheap
        "anthropic/claude-3-haiku",      # Fallback 2 — cheap
    ],
}
```

**Migration path to V1 tiers**: Replace the single `fallback_chain` with a dict of tiers, each with its own chain. Move from Python dict to YAML if complexity warrants it. No structural changes to `llm.py` — it already supports chain-based fallback.

**Deferred to V1**: Multiple tiers, YAML config, per-query model selector, budget tracking.

---

### ADR-3: Reactive LLM Fallback with Persistence

**Status**: Accepted

**Context**: The founder's requirements include: (a) automatic fallback when a provider's quota is exhausted, (b) the fallback should persist for all future requests (not just the current one), and (c) restoring the original provider should require manual intervention. Additionally, pre-call budget checks add latency (a DB read before every LLM call) and were explicitly rejected.

**Decision**: Use reactive (not proactive) fallback. Call the active provider directly. If it fails with 429/quota-exhausted/5xx, catch the error, try the next provider in the chain, and persist the switch.

**How it works**:

1. On backend startup, `llm.py` reads the `llm_state` table to get the currently active provider
2. The active provider is cached in-memory (module-level variable) — no DB read per request
3. On each LLM call, use the in-memory active provider
4. If the call succeeds: return response, no DB interaction
5. If the call fails (429 / quota / timeout / 5xx):
   a. Log the error with provider name and error type
   b. Move to the next provider in the fallback chain
   c. Retry the same request with the new provider
   d. If retry succeeds: update `llm_state` table AND in-memory cache with new provider
   e. If retry fails: try next provider in chain, repeat
   f. If ALL providers fail: return error event in SSE stream
6. The switch is **permanent** — all future requests use the new provider
7. To restore the original provider: manually update the `llm_state` row in Supabase or change `config.py`

**Why permanent switch**: If Gemini returns "quota exhausted", it won't recover until the next billing cycle. Retrying on every request wastes time and gives users errors. A permanent switch with manual restore is the correct behavior.

**Database table**:
```sql
CREATE TABLE llm_state (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),  -- single row constraint
    active_provider TEXT NOT NULL,                       -- e.g., "gemini/gemini-2.0-flash"
    switched_at TIMESTAMPTZ,                             -- when the switch happened
    switch_reason TEXT,                                   -- e.g., "429 quota exhausted"
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

**Latency impact**: Zero on the happy path. No pre-call DB read. The only DB write happens on provider failure — which is rare and acceptable.

**Deferred to V1**: Per-provider budget tracking, automatic provider restoration on billing cycle reset.

---

### ADR-4: Global Product Cache with 7-Day TTL

**Status**: Accepted

**Context**: Product research involves expensive operations (web search, scraping, LLM analysis). If User A researches "Notion" and User B researches "Notion" the next day, there's no reason to repeat the entire pipeline. Product data (features, pricing, strengths) doesn't change daily.

**Decision**: Cache all product profiles in a shared `products` table. Before scraping/analyzing a product, check if a cached version exists with `last_scraped_at` within the last 7 days. If yes, return cached data. If no, run the full pipeline and update the cache.

**Cache behavior**:
- Cache key: `normalized_name` (lowercase, trimmed product name)
- TTL: 7 days (from `last_scraped_at`)
- Scope: global — shared across all anonymous visitors
- Refresh: manual "Refresh" button per block in the UI, which forces a re-scrape regardless of TTL
- UI indicator: "Last updated X days ago" shown on cached result blocks

**Cache layers (V0)**:

| What's Cached | TTL | Storage | Cache Key |
|--------------|-----|---------|-----------|
| Product profiles | 7 days | `products` table | `normalized_name` |
| Competitor relationships | 14 days | `competitor_relationships` table | `product_id + competitor_id` |

**Deferred to V1**: Search result caching (3-day TTL), Redis in-memory cache for hot data.

---

### ADR-5: Linear Journey Model

**Status**: Accepted

**Context**: Infinite canvas (branching, forking from any step) was considered but rejected for V0. It requires a tree/graph data model with recursive queries, which adds significant complexity to every journey-related operation. The founder confirmed this can be deferred indefinitely until proper developers are available.

**Decision**: Use a simple linear `step_number INTEGER` model. Steps are ordered sequentially within a journey. Queries use `ORDER BY step_number`.

**Schema**:
```sql
CREATE TABLE journey_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journey_id UUID REFERENCES journeys(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    step_type TEXT NOT NULL,
    input_data JSONB,
    output_data JSONB,
    user_selection JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

**Migration path to tree model (V2+)**: Add `parent_step_id UUID` column, drop `step_number`, update queries to use recursive CTEs. This is a schema migration but not a fundamental redesign — the JSONB columns for input/output/selection remain unchanged.

**Deferred to V2+**: Tree/graph journey model, infinite canvas, branching.

---

### ADR-6: SSE Streaming for Research Results

**Status**: Accepted

**Context**: Research takes 30-90 seconds (search + scrape + LLM for multiple products). The user should see progressive results, not stare at a spinner for 60 seconds. Three options were evaluated: (a) synchronous SSE streaming, (b) async job with polling, (c) hybrid.

**Decision**: Synchronous SSE streaming. The `POST /api/research` endpoint returns an SSE event stream. The connection stays open while research runs. Each research block is sent as an event the moment it completes. The frontend renders blocks progressively.

**Why SSE over WebSockets**: SSE is unidirectional (server → client), simpler to implement, works over HTTP/2, auto-reconnects natively, and matches the use case perfectly. WebSockets are bidirectional — not needed here. WebSockets are deferred to V2+ for infinite canvas / real-time collaboration.

**Why SSE over polling**: Polling creates unnecessary requests, adds latency (limited by poll interval), and complicates the frontend with polling loops, retry logic, and state reconciliation. SSE gives instant updates with zero polling overhead.

**UX benefit**: A 60-second research feels like 15 seconds because the user is reading Block 1 while Block 3 is still being generated. Progressive rendering is the biggest "snappy" lever in the product.

**Deferred to V2+**: WebSocket support, background job queue.

---

### ADR-7: All Data Flows Through Backend

**Status**: Accepted

**Context**: The frontend could call Supabase directly (it has a client SDK). This was rejected because: (a) it leaks the Supabase URL and anon key to the browser, (b) it creates a dual-dependency where the frontend talks to both the backend and Supabase, complicating debugging, and (c) it prevents the backend from being the single source of truth.

**Decision**: The frontend communicates exclusively with the FastAPI backend. No Supabase client SDK in the frontend. No `NEXT_PUBLIC_SUPABASE_URL` env var.

**Consequences**:
- All data reads/writes go through backend API endpoints
- Backend uses the Supabase service role key (server-side only, not exposed to browser)
- Adding auth in V1: frontend gets a Supabase client for auth ONLY (login/signup flow). The JWT from Supabase Auth is passed to the backend in the `Authorization` header. Backend validates the JWT and uses the user_id for data access.

---

### ADR-8: Design Tokens in tailwind.config.ts

**Status**: Accepted

**Context**: The Cozy Sand design system has specific values for colors, typography, spacing, radii, and shadows. These need to live in a single file so changing the theme requires editing one place.

**Decision**: All design tokens are embedded directly in `tailwind.config.ts` as the Tailwind theme configuration. No separate `tokens.ts`, no CSS variables layer, no Tailwind preset file.

**Rationale for single file (vibecoding)**: Three files (tokens.ts → preset.ts → tailwind.config.ts) is correct architecture but adds indirection. For vibecoding, one file is faster to work with and easier for AI assistants to reason about.

**Token values** (from [DESIGN_GUIDE.md](DESIGN_GUIDE.md)):

```typescript
// tailwind.config.ts — Cozy Sand theme tokens
theme: {
  extend: {
    colors: {
      sand: '#F9F7F2',           // page/sidebar background
      workspace: '#FFFFFF',       // card/panel background
      charcoal: '#1F1F1F',       // primary text, headings
      muted: '#737373',          // secondary text
      placeholder: '#A3A3A3',    // input placeholders, hints
      terracotta: '#A65D47',     // accent: active states, buttons, links
      'terracotta-light': 'rgba(166, 93, 71, 0.08)',  // selected chip fill
      border: '#E5E5E5',         // hairline borders
      success: '#5C8A5E',        // completed step checkmarks
      error: '#C45C5C',          // destructive actions
    },
    fontFamily: {
      serif: ['Newsreader', 'Fraunces', 'EB Garamond', 'Georgia', 'serif'],
      sans: ['Inter', 'Geist', 'Public Sans', 'system-ui', 'sans-serif'],
    },
    borderRadius: {
      panel: '24px',
      card: '16px',
      button: '8px',
      chip: '20px',
      input: '12px',
    },
    boxShadow: {
      subtle: '0 1px 3px rgba(0,0,0,0.04)',
      hover: '0 2px 8px rgba(0,0,0,0.06)',
    },
    spacing: {
      'block-gap': '16px',
      'section-gap': '24px',
      'card-padding': '20px',
    },
  },
}
```

**Migration path**: When the design system grows (dark mode, multiple themes), extract tokens into a separate `tokens.ts` file that feeds the Tailwind config. Import paths don't change — only the config file is refactored.

---

### ADR-9: Layered Competitor Discovery with AlternativeTo Seeding

**Status**: Accepted (Updated: Tavily replaces Serper as primary search)

**Context**: The original design relied on Google Custom Search API (100 free queries/day) to find competitors, with the LLM extracting competitor names from raw search snippets. This was brittle — Google CSE's free tier is severely limited, search snippets don't always contain competitor names, and the LLM had to "guess" competitors from noisy input. G2.com was considered but requires sign-in and has aggressive anti-scraping. A more robust, multi-source approach is needed.

**Decision**: Replace Google CSE with a layered, multi-source competitor discovery pipeline:

1. **AlternativeTo seeding (DB-first, instant, free)**: Pre-scrape `alternativeto.net` and `get.alternative.to` into a local `alternatives_cache` table. The pipeline checks this table first via `db.get_cached_alternatives()`. AlternativeTo is the highest-quality source — it provides curated alternative lists maintained by users.

2. **Live search (parallel, costs API quota)**:
   - **App/Play Store scrapers** — `google-play-scraper` and `app-store-scraper` Python libraries (no API key needed). The "similar apps" sections are effectively competitor lists. Marked V0-EXPERIMENTAL; deferred to V1 if flaky.
   - **Tavily web search** — AI-optimized search API (primary). Returns structured results with extracted content. 1,000 queries/month free tier.
   - **Serper web search** — structured JSON API (fallback). 2,500 queries/month free tier. Used when Tavily fails.
   - **Reddit search** — `site:reddit.com` queries via Tavily (primary) or Serper (fallback) for community discussions and recommendations.

3. **LLM synthesis (always runs last)**: The LLM receives data from ALL available sources AND is instructed to augment from its own knowledge. It prioritizes competitors confirmed by multiple sources but MAY include well-known competitors it's confident about.

**Priority logic**: DB first (instant, free) → live search (costs quota) → LLM always last (synthesize + fill gaps).

**Search provider hierarchy**: Tavily (primary) → Serper (fallback) → DuckDuckGo (last-resort emergency). DuckDuckGo is only used when both Tavily and Serper are completely unavailable (network error, invalid API keys).

**G2**: Dropped entirely. Requires sign-in, has aggressive anti-bot measures, and scraping it reliably is not feasible.

**Google CSE**: Dropped entirely. Replaced by Tavily + Serper.

**Consequences**:
- Competitor discovery is significantly more robust — multiple data sources reduce single-point-of-failure risk
- AlternativeTo cache provides instant results for popular products (no search API cost)
- App store scrapers are experimental and may need to be deferred — pipeline handles empty results gracefully
- Tavily is the primary search provider; Serper is the first fallback; DuckDuckGo is the last-resort emergency fallback
- The `alternatives_cache` table adds a new DB table and a one-time seeding step

**Seeding**: Run `python -m app.seed_alternatives` after backend deployment. This is a founder task (see FOUNDER_TASKS.md). The script crawls popular categories on AlternativeTo and stores product-to-alternatives mappings with a 30-day TTL.

**Env var change**: `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID` replaced by `TAVILY_API_KEY` (required) + `SERPER_API_KEY` (recommended fallback).

---

## 3. Data Flow

### Journey Lifecycle

A journey is the container for an entire research exploration. Here is the exact lifecycle:

1. **Classification**: Backend receives `POST /api/research`, classifies intent. For `small_talk`/`off_topic`, a `quick_response` event is returned — **no journey is created**, connection closes immediately.
2. **Creation**: For `build`/`explore`/`improve` intents, backend creates a new `journeys` row with `intent_type`. The journey `id` is returned as the first SSE event (`journey_started`).
3. **Progression**: The frontend stores the `journey_id` and uses it for all follow-up `POST /api/research/{journey_id}/selection` calls.
4. **Completion**: When all research is done, the backend updates the journey status to `completed` and sends `research_complete`.
5. **Resumption**: If a user returns to a journey from the dashboard, the frontend loads the journey via `GET /api/journeys/{id}` and reconstructs the UI from saved steps.

### Two-Endpoint Research Protocol

The research pipeline uses exactly two endpoints:

- **`POST /api/research`** — Starts a new research session. Classifies intent. Either returns a quick response (no journey) or creates a journey and begins the pipeline. Returns an SSE stream.
- **`POST /api/research/{journey_id}/selection`** — Sends a user's selection (clarification answers, competitor picks, or problem selection). Returns a **new** SSE stream that continues the pipeline from where it paused.

**Critical rule**: SSE is server-to-client only. The frontend NEVER sends data over an SSE connection. User input always goes via a separate POST request. Each SSE stream runs until it needs user input (sends `waiting_for_selection` then closes) or completes (sends `research_complete` then closes).

**SSE ownership**: The landing page (`page.tsx`) does NOT handle SSE streams. It only collects the prompt and navigates to `/explore/new?prompt={encoded}`. The explore page (`explore/[journeyId]/page.tsx`) is the **single SSE orchestration owner** — it opens all streams, processes all events, and manages all research state. This avoids ambiguous stream ownership across route changes.

### Intent-Based Pipeline Branching

The first step in every research request is intent classification. The backend calls the classify prompt, which returns both the intent type and (for build/explore) a set of multi-question clarification questions. The pipeline then branches:

```
POST /api/research { "prompt": "..." }
    │
    ▼
classify(prompt) → intent_type
    │
    ├── small_talk → quick_response event → stream closes (no journey)
    ├── off_topic  → quick_response event → stream closes (no journey)
    ├── improve    → redirect to explore flow (journey.intent_type = "explore")
    ├── explore    → clarify → competitors → explore → DONE
    └── build      → clarify → competitors → explore + gap analysis → problem select → problem statement → DONE
```

### Research Pipeline: Build Intent (4 streams)

```
── Stream 1 (POST /api/research) ──────────────────────────────────

Frontend: POST /api/research { "prompt": "I want to build a note taking app" }
    │
    ▼
Backend: classifies intent, creates journey (intent_type: "build"), begins SSE stream
    │
    ├─ SSE → { type: "journey_started", journey_id: "uuid-abc", intent_type: "build" }
    │
    ├─ SSE → { type: "step_started", step: "classifying", label: "Understanding your query" }
    │   ├─ prompts.py → build_classify_prompt(user_input)
    │   ├─ llm.py → calls Gemini Flash
    │   ├─ LLM returns: { intent_type: "build", domain: "note-taking",
    │   │     clarification_questions: [ { id: "platform", ... }, { id: "content_type", ... } ] }
    │   └─ db.py → save classify step
    ├─ SSE → { type: "step_completed", step: "classifying" }
    │
    ├─ SSE → { type: "clarification_needed", questions: [
    │     { id: "platform", label: "What platform?", options: [...], allow_multiple: true },
    │     { id: "content_type", label: "Content type?", options: [...], allow_multiple: true },
    │     { id: "positioning", label: "Positioning?", options: [...], allow_multiple: false }
    │   ] }
    ├─ SSE → { type: "waiting_for_selection", selection_type: "clarification" }
    │
    └─ Stream closes.

── User answers all clarification questions, clicks "Continue" ────

── Stream 2 (POST /api/research/uuid-abc/selection) ───────────────

Frontend: POST /api/research/uuid-abc/selection {
    "step_type": "clarify",
    "selection": {
        "answers": [
            { "question_id": "platform", "selected_option_ids": ["mobile", "web"] },
            { "question_id": "content_type", "selected_option_ids": ["text-notes"] },
            { "question_id": "positioning", "selected_option_ids": ["power-tool"] }
        ]
    }
}
    │
    ▼
Backend: loads journey, saves clarify step, runs competitor search
    │
    ├─ SSE → { type: "step_started", step: "finding_competitors", label: "Finding competitors" }
    │   ├─ db.py → check alternatives_cache for "note-taking" products
    │   │   └─ If found: add to alternatives_data
    │   ├─ (parallel fan-out via asyncio.gather):
    │   │   ├─ app_stores.py → search_play_store("note taking") + search_app_store("note taking")  [V0-EXPERIMENTAL]
    │   │   ├─ search.py → Tavily web search "mobile web note-taking power tool competitors"
    │   │   │   └─ On failure: try Serper → then DuckDuckGo (last-resort)
    │   │   └─ search.py → search_reddit("note taking app mobile power tool") via Tavily/Serper
    │   ├─ llm.py → synthesize competitor list from all sources + LLM's own knowledge
    │   └─ db.py → save step
    ├─ SSE → { type: "block_ready", block: { type: "competitor_list", ... } }
    ├─ SSE → { type: "step_completed", step: "finding_competitors" }
    │
    ├─ SSE → { type: "waiting_for_selection", selection_type: "competitors" }
    │
    └─ Stream closes.

── User checks 3-4 competitors, clicks "Explore Selected" ────────

── Stream 3 (POST /api/research/uuid-abc/selection) ───────────────

Frontend: POST /api/research/uuid-abc/selection {
    "step_type": "select_competitors",
    "selection": { "competitor_ids": ["notion", "obsidian", "bear"] }
}
    │
    ▼
Backend: loads journey, begins explore phase
    │
    ├─ SSE → { type: "step_started", step: "exploring", label: "Analyzing selected products" }
    │
    │   Runs in parallel (asyncio.gather) for each selected product:
    │
    │   ├─ For "Notion":
    │   │   ├─ db.py → check product cache (last_scraped_at < 7 days?)
    │   │   │   ├─ Cache HIT → return cached profile
    │   │   │   └─ Cache MISS:
    │   │   │       ├─ scraper.py → scrape product website (Jina/BS4)
    │   │   │       ├─ search.py → search_reddit("Notion note taking review")
    │   │   │       └─ llm.py → analyze website + Reddit content into profile
    │   │   ├─ db.py → store/update product in cache
    │   │   └─ SSE → { type: "block_ready", block: { type: "product_profile", ... } }
    │   │
    │   ├─ For "Obsidian", "Bear": (same flow, concurrent)
    │   │   └─ SSE → { type: "block_ready", block: { type: "product_profile", ... } }
    │   │
    │   └─ Market Overview (concurrent with product profiles):
    │       ├─ llm.py → generate market overview from all collected data
    │       └─ SSE → { type: "block_ready", block: { type: "market_overview", ... } }
    │
    ├─ SSE → { type: "step_completed", step: "exploring" }
    │
    │   === BUILD INTENT ONLY: Gap Analysis ===
    │
    ├─ SSE → { type: "step_started", step: "gap_analyzing", label: "Finding market gaps" }
    │   ├─ prompts.py → build_gap_analysis_prompt(domain, all_profiles, clarification_context, market_overview)
    │   ├─ llm.py → synthesize market gaps from competitor profiles
    │   └─ db.py → save explore step (includes gap_analysis in output_data)
    ├─ SSE → { type: "block_ready", block: { type: "gap_analysis", ... } }
    ├─ SSE → { type: "step_completed", step: "gap_analyzing" }
    │
    ├─ SSE → { type: "waiting_for_selection", selection_type: "problems" }
    │
    └─ Stream closes.

── User selects 2 problem areas, clicks "Define Problem" ─────────

── Stream 4 (POST /api/research/uuid-abc/selection) ───────────────

Frontend: POST /api/research/uuid-abc/selection {
    "step_type": "select_problems",
    "selection": { "problem_ids": ["gap-mobile-first", "gap-offline-sync"] }
}
    │
    ▼
Backend: loads journey, generates problem statement
    │
    ├─ SSE → { type: "step_started", step: "defining_problem", label: "Crafting your problem statement" }
    │   ├─ prompts.py → build_problem_statement_prompt(selected_gaps, competitor_context)
    │   ├─ llm.py → generate actionable problem statement
    │   └─ db.py → save define_problem step
    ├─ SSE → { type: "block_ready", block: { type: "problem_statement", ... } }
    ├─ SSE → { type: "step_completed", step: "defining_problem" }
    │
    ├─ SSE → { type: "research_complete", journey_id: "uuid-abc", summary: "Research complete" }
    │
    └─ Stream closes. Journey status updated to "completed".
```

### Research Pipeline: Explore Intent (3 streams)

```
── Stream 1 (POST /api/research) ──────────────────────────────────

Frontend: POST /api/research { "prompt": "Tell me about edtech in India" }
    │
    ▼
Backend: classifies intent = "explore", creates journey, begins SSE stream
    │
    ├─ SSE → { type: "journey_started", journey_id: "uuid-xyz", intent_type: "explore" }
    ├─ SSE → { type: "step_started", step: "classifying", ... }
    ├─ SSE → { type: "step_completed", step: "classifying" }
    ├─ SSE → { type: "clarification_needed", questions: [
    │     { id: "area", label: "What area of edtech?", options: ["K-12", "Test prep", ...] }
    │   ] }
    ├─ SSE → { type: "waiting_for_selection", selection_type: "clarification" }
    └─ Stream closes.

── Stream 2 (after clarification) ─────────────────────────────────
    ├─ Competitor search + selection → waiting_for_selection
    └─ Stream closes.

── Stream 3 (after competitor selection) ───────────────────────────
    ├─ Explore (profiles + market overview)
    ├─ NO gap analysis, NO problem selection
    ├─ research_complete
    └─ Stream closes. Journey status = "completed".
```

### Research Pipeline: Quick Response (no journey)

```
── Single Stream (POST /api/research) ─────────────────────────────

Frontend: POST /api/research { "prompt": "How are you?" }
    │
    ▼
Backend: classifies intent = "small_talk" → NO journey created
    │
    ├─ SSE → { type: "quick_response", message: "I'm Blueprint, a product research assistant. What would you like to explore?" }
    │
    └─ Stream closes immediately. No journey_started event. No DB writes.
```

### Research Pipeline: Improve Intent (V0 Redirect)

```
── Stream 1 (POST /api/research) ──────────────────────────────────

Frontend: POST /api/research { "prompt": "I want to improve my Notion competitor" }
    │
    ▼
Backend: classifies intent = "improve" → redirects to explore flow
    │
    ├─ SSE → { type: "journey_started", journey_id: "uuid-def", intent_type: "explore" }
    ├─ SSE → { type: "intent_redirect", original_intent: "improve", redirected_to: "explore",
    │          message: "Improve flow coming soon. Starting an explore session for your product." }
    ├─ (continues as explore flow)
```

### Data Storage Flow

```
Research results → db.py
    │
    ├─ Product profiles       → products table (global cache, shared, 7-day TTL)
    ├─ Competitor links       → competitor_relationships table (global cache, shared, 14-day TTL)
    ├─ AlternativeTo data     → alternatives_cache table (pre-seeded, 30-day TTL)
    ├─ Journey metadata       → journeys table (per-journey, includes intent_type)
    ├─ Step results           → journey_steps table (per-journey, linear order)
    ├─ User selections        → user_choices_log table (for future ML)
    └─ LLM provider state     → llm_state table (single row)
```

---

## 4. LLM Architecture

### Module: `llm.py`

This single file handles all LLM interactions:

1. **Config loading**: Reads `LLM_CONFIG` from `config.py` at import time
2. **Provider state**: Reads `llm_state` from Supabase on startup, caches in module-level variable
3. **Persona injection**: Prepends the system prompt from `LLM_CONFIG["persona"]` to every call
4. **litellm calls**: Uses `litellm.acompletion()` for async calls with streaming support
5. **Fallback handling**: On provider failure, walks the fallback chain and persists the switch
6. **Streaming**: Yields tokens/chunks via async generator for SSE

### Prompt Architecture: `prompts.py`

All prompt templates live in one file. Each function returns a list of messages (system + user) ready for litellm:

```python
def build_classify_prompt(user_input: str) -> list[dict]:
    """Classify intent (build/explore/improve/small_talk/off_topic) + generate clarification questions."""
    ...

def build_competitors_prompt(domain: str, clarification_context: dict) -> list[dict]:
    """Find competitors given domain and clarified user preferences."""
    ...

def build_explore_prompt(product_name: str, scraped_content: str, reddit_content: str) -> list[dict]:
    """Analyze scraped website + Reddit content into a structured product profile."""
    ...

def build_gap_analysis_prompt(domain: str, profiles: list[dict], clarification_context: dict, market_overview: dict | None = None) -> list[dict]:
    """Synthesize market gaps from all competitor profiles + market context (build intent only)."""
    ...

def build_problem_statement_prompt(selected_gaps: list[dict], context: dict) -> list[dict]:
    """Generate actionable problem statement from user-selected gaps."""
    ...
```

The persona system prompt is injected by `llm.py`, not by `prompts.py`. This keeps persona management centralized.

**Important**: Prompt text is authored by the founder, not the coding agent. The coding agent implements the function signatures and wiring. Actual prompt content will be provided via `FOUNDER_TASKS.md`.

### LLM Output Validation

All LLM calls that expect structured JSON go through a validation pipeline:

1. **Parse**: Attempt `json.loads()` on the raw LLM response. Strip markdown code fences (` ```json ... ``` `) if present.
2. **Validate**: Parse the JSON into the expected Pydantic model for that step (e.g., `ClassifyResult`, `CompetitorList`, `ProductProfile`, `GapAnalysis`, `ProblemStatement`).
3. **Retry on failure**: If `JSONDecodeError` or Pydantic `ValidationError`:
   a. Send a one-shot "fix JSON" prompt: include the broken output + the expected schema + "Fix the JSON and return only valid JSON."
   b. Parse and validate the retry response.
   c. If retry also fails: return a structured error (never crash). The SSE stream sends a `block_error` for that step.
4. **No silent failures**: Every validation failure is logged with the raw LLM output, the expected schema, and the error message.

```python
# Pseudocode for the validation flow in llm.py
async def call_llm_structured(messages: list[dict], response_model: type[BaseModel]) -> BaseModel:
    raw = await call_llm(messages)
    try:
        return parse_and_validate(raw, response_model)
    except (json.JSONDecodeError, ValidationError) as e:
        log.warning(f"LLM output validation failed: {e}")
        fix_messages = build_fix_json_prompt(raw, response_model.model_json_schema())
        retry_raw = await call_llm(fix_messages)
        return parse_and_validate(retry_raw, response_model)  # raises on second failure
```

### Prompt Design Principles

- **Structured output**: All prompts request JSON output with a specific schema. This makes parsing reliable. Each prompt includes the expected JSON schema inline so the LLM knows the exact shape.
- **Source citing**: Prompts explicitly instruct the LLM to include source URLs for every claim.
- **No fabrication**: System prompt includes "Never fabricate data — if unsure, say so."
- **Temperature 0.3**: Low temperature for factual research. Not creative writing.

---

## 5. SSE Streaming Protocol

### Event Types

Both `POST /api/research` and `POST /api/research/{journey_id}/selection` return SSE streams. The event types are identical across both endpoints, with two exceptions noted below:

```typescript
// All possible SSE events
type ResearchEvent =
  // Journey initialization (only from POST /api/research, only for build/explore intents)
  | { type: "journey_started"; journey_id: string; intent_type: IntentType }

  // Quick response (only from POST /api/research, for small_talk/off_topic — no journey)
  | { type: "quick_response"; message: string }

  // Intent redirect (only when improve → explore in V0)
  | { type: "intent_redirect"; original_intent: string; redirected_to: string; message: string }

  // Pipeline progress
  | { type: "step_started"; step: StepName; label: string }
  | { type: "step_completed"; step: StepName }

  // Research results (each block is independent)
  | { type: "block_ready"; block: ResearchBlock }
  | { type: "block_error"; block_name: string; error: string; error_code: string }

  // User interaction needed (stream will close after this)
  | { type: "clarification_needed"; questions: ClarificationQuestion[] }
  | { type: "waiting_for_selection"; selection_type: SelectionType }

  // Terminal events (stream closes after these)
  | { type: "research_complete"; journey_id: string; summary: string }
  | { type: "error"; message: string; recoverable: boolean; error_code: string }

type IntentType = "build" | "explore";  // stored on journey (improve redirects to explore)

type StepName = "classifying" | "clarifying" | "finding_competitors" | "exploring" | "gap_analyzing" | "defining_problem";

type SelectionType = "clarification" | "competitors" | "problems";

// Block types
type ResearchBlock = {
  id: string;
  type: "market_overview" | "competitor_list" | "product_profile" | "gap_analysis" | "problem_statement";
  title: string;
  content: string;          // Markdown-formatted content (for display)
  output_data?: Record<string, unknown>;  // Typed structured data (for programmatic use by components)
  // output_data shape depends on block type:
  //   competitor_list:    { competitors: CompetitorInfo[] }
  //   gap_analysis:       { problems: ProblemArea[] }
  //   product_profile:    { profile: ProductProfile }
  //   problem_statement:  { statement: ProblemStatement }
  //   market_overview:    { overview: MarketOverview }
  sources: string[];         // Source URLs
  cached: boolean;           // Was this from cache?
  cached_at?: string;        // ISO date if cached
}

// Clarification questions (rendered as multi-question panel with chips + "Continue" button)
type ClarificationQuestion = {
  id: string;
  label: string;             // "What platform are you targeting?"
  options: { id: string; label: string; description: string }[];  // id = stable slug for selection tracking
  allow_multiple: boolean;   // true = multi-select chips, false = single-select radio
}
```

### Stream Lifecycle Rules

Each SSE stream has exactly one of these endings:

1. **Quick response**: sends `quick_response` as the only event, then closes. No journey created. Only for `small_talk`/`off_topic`.
2. **Needs user input**: sends `waiting_for_selection` as the last event, then closes. The frontend shows the selection UI and waits for the user. When the user makes a choice, the frontend calls `POST /api/research/{journey_id}/selection`, which opens a new stream.
3. **Research complete**: sends `research_complete` as the last event, then closes. The journey is done.
4. **Fatal error**: sends `error` with `recoverable: false` as the last event, then closes.

A `clarification_needed` event is always followed by `waiting_for_selection`. The two events are separate so the frontend can render the questions (from `clarification_needed`) and know to wait (from `waiting_for_selection`).

### Event Sequence: Build Intent (4 streams)

```
── Stream 1 (POST /api/research) ─────────────────────────────────
→ { type: "journey_started", journey_id: "uuid-abc", intent_type: "build" }
→ { type: "step_started", step: "classifying", label: "Understanding your query" }
→ { type: "step_completed", step: "classifying" }
→ { type: "clarification_needed", questions: [
    { id: "platform", label: "What platform?", options: [...], allow_multiple: true },
    { id: "content_type", label: "Content type?", options: [...], allow_multiple: true },
    { id: "positioning", label: "Positioning?", options: [...], allow_multiple: false }
  ] }
→ { type: "waiting_for_selection", selection_type: "clarification" }
   [stream closes]

── Stream 2 (after user answers clarification) ────────────────────
→ { type: "step_started", step: "finding_competitors", label: "Finding competitors" }
→ { type: "block_ready", block: { type: "competitor_list", ... } }
→ { type: "step_completed", step: "finding_competitors" }
→ { type: "waiting_for_selection", selection_type: "competitors" }
   [stream closes]

── Stream 3 (after competitor selection) ───────────────────────────
→ { type: "step_started", step: "exploring", label: "Analyzing selected products" }
→ { type: "block_ready", block: { type: "market_overview", ... } }
→ { type: "block_ready", block: { type: "product_profile", title: "Notion", ... } }
→ { type: "block_ready", block: { type: "product_profile", title: "Obsidian", ... } }
→ { type: "step_completed", step: "exploring" }
→ { type: "step_started", step: "gap_analyzing", label: "Finding market gaps" }
→ { type: "block_ready", block: { type: "gap_analysis", title: "Market Gaps & Opportunities", ... } }
→ { type: "step_completed", step: "gap_analyzing" }
→ { type: "waiting_for_selection", selection_type: "problems" }
   [stream closes]

── Stream 4 (after problem selection) ─────────────────────────────
→ { type: "step_started", step: "defining_problem", label: "Crafting your problem statement" }
→ { type: "block_ready", block: { type: "problem_statement", title: "Your Problem Statement", ... } }
→ { type: "step_completed", step: "defining_problem" }
→ { type: "research_complete", journey_id: "uuid-abc", summary: "Research complete" }
   [stream closes]
```

### Event Sequence: Explore Intent (3 streams)

```
── Stream 1 (POST /api/research) ─────────────────────────────────
→ { type: "journey_started", journey_id: "uuid-xyz", intent_type: "explore" }
→ { type: "step_started", step: "classifying", label: "Understanding your query" }
→ { type: "step_completed", step: "classifying" }
→ { type: "clarification_needed", questions: [...] }
→ { type: "waiting_for_selection", selection_type: "clarification" }
   [stream closes]

── Stream 2 (after clarification) ─────────────────────────────────
→ { type: "step_started", step: "finding_competitors", label: "Finding competitors" }
→ { type: "block_ready", block: { type: "competitor_list", ... } }
→ { type: "step_completed", step: "finding_competitors" }
→ { type: "waiting_for_selection", selection_type: "competitors" }
   [stream closes]

── Stream 3 (after competitor selection) ───────────────────────────
→ { type: "step_started", step: "exploring", label: "Analyzing selected products" }
→ { type: "block_ready", block: { type: "market_overview", ... } }
→ { type: "block_ready", block: { type: "product_profile", ... } }
→ { type: "step_completed", step: "exploring" }
→ { type: "research_complete", journey_id: "uuid-xyz", summary: "Research complete" }
   [stream closes — NO gap analysis, NO problem statement for explore]
```

### Event Sequence: Quick Response (1 event, no journey)

```
── Single Stream (POST /api/research) ─────────────────────────────
→ { type: "quick_response", message: "I'm Blueprint, a product research assistant. ..." }
   [stream closes immediately — no journey_started, no DB writes]
```

### Event Sequence: Partial Failure

```
→ { type: "step_started", step: "exploring", label: "Analyzing selected products" }
→ { type: "block_ready", block: { type: "market_overview", ... } }
→ { type: "block_ready", block: { type: "product_profile", title: "Notion", ... } }
→ { type: "block_error", block_name: "Obsidian", error: "Could not scrape obsidian.md", error_code: "BP-7A2F1D" }
→ { type: "step_completed", step: "exploring" }
→ { type: "research_complete", journey_id: "uuid-abc", summary: "2 of 3 blocks completed" }
   [stream closes — partial results are still shown]
```

### Frontend SSE Handling

The frontend manages the multi-stream lifecycle:

1. **Starting research**: calls `POST /api/research`, opens SSE stream, processes events
2. On `quick_response`: show the message in the workspace, no journey state needed. Done.
3. On `journey_started`: stores `journey_id` and `intent_type` in component state. `intent_type` determines the number of progress steps (3 for explore, 5 for build).
4. On `intent_redirect`: show an info banner explaining the redirect
5. On `step_started` / `step_completed`: updates the ProgressSteps component in the Sidebar
6. On `block_ready`: appends the block to the Workspace panel
7. On `block_error`: renders an inline warning card in the Workspace with "Try again" button
8. On `clarification_needed`: renders multi-question clarification panel (chips per question + "Continue" button). User must answer all questions before submitting.
9. On `waiting_for_selection`: marks the stream as waiting, enables selection UI, disables RUN button
10. **Sending selection**: when user submits, calls `POST /api/research/{journey_id}/selection`, opens a NEW SSE stream, continues processing events from step 5
11. On `research_complete`: finalizes progress indicator, re-enables RUN button, marks journey done
12. On `error`: shows toast (recoverable) or modal (non-recoverable)

---

## 6. Journey Step Schemas

Each row in `journey_steps` has `input_data`, `output_data`, and `user_selection` as JSONB columns. The schema for each column depends on the `step_type`. These schemas are the contract between the backend pipeline and the frontend rendering.

There are 7 step types: `classify`, `clarify`, `find_competitors`, `select_competitors`, `explore`, `select_problems` (build only), `define_problem` (build only).

### step_type: "classify"

Classifies the user's intent and generates clarification questions. This is always the first step.

```json
// input_data
{
  "prompt": "I want to build a note taking app"
}

// output_data
{
  "intent_type": "build",
  "domain": "note-taking",
  "clarification_questions": [
    {
      "id": "platform",
      "label": "What platform are you targeting?",
      "options": [
        { "id": "mobile", "label": "Mobile", "description": "iOS and/or Android" },
        { "id": "desktop", "label": "Desktop", "description": "macOS, Windows, Linux" },
        { "id": "web", "label": "Web", "description": "Browser-based" },
        { "id": "cross-platform", "label": "Cross-platform", "description": "All devices" }
      ],
      "allow_multiple": true
    },
    {
      "id": "content_type",
      "label": "What type of content?",
      "options": [
        { "id": "text-notes", "label": "Text notes", "description": "Written notes, markdown, documents" },
        { "id": "audio-voice", "label": "Audio / voice", "description": "Voice memos, transcription" },
        { "id": "visual-drawings", "label": "Visual / drawings", "description": "Sketches, diagrams, whiteboards" },
        { "id": "all-in-one", "label": "All-in-one", "description": "Text + audio + visual combined" }
      ],
      "allow_multiple": true
    },
    {
      "id": "positioning",
      "label": "Closest to your vision?",
      "options": [
        { "id": "simple-fast", "label": "Simple & fast", "description": "Minimal, quick capture" },
        { "id": "power-tool", "label": "Power tool", "description": "Advanced features, graph views" },
        { "id": "all-in-one-workspace", "label": "All-in-one workspace", "description": "Notes + docs + projects" },
        { "id": "specialized-niche", "label": "Specialized / niche", "description": "Domain-specific tool" }
      ],
      "allow_multiple": false
    }
  ]
}

// output_data — for small_talk / off_topic (NO journey created, returned as quick_response SSE event)
{
  "intent_type": "small_talk",
  "quick_response": "I'm Blueprint, a product research assistant. What would you like to explore?"
}

// user_selection — null (classify itself has no user selection; see clarify)
```

### step_type: "clarify"

User's answers to all clarification questions. Always follows classify for build/explore intents.

```json
// input_data
{
  "questions_presented": [
    { "id": "platform", "label": "What platform are you targeting?", "options": [...] },
    { "id": "content_type", "label": "What type of content?", "options": [...] },
    { "id": "positioning", "label": "Closest to your vision?", "options": [...] }
  ]
}

// output_data — null (purely a user selection step, no backend processing)

// user_selection
{
  "answers": [
    { "question_id": "platform", "selected_option_ids": ["mobile", "web"] },
    { "question_id": "content_type", "selected_option_ids": ["text-notes"] },
    { "question_id": "positioning", "selected_option_ids": ["power-tool"] }
  ]
}
```

### step_type: "find_competitors"

Finds competitors using a layered multi-source pipeline (AlternativeTo cache → App Stores + Tavily/Serper + Reddit → LLM synthesis), informed by clarification context.

```json
// input_data
{
  "domain": "note-taking",
  "clarification_context": {
    "platform": ["Mobile", "Web"],
    "content_type": ["Text notes"],
    "positioning": ["Power tool"]
  },
  "sources_used": {
    "alternatives_cache": true,
    "app_store": true,
    "play_store": true,
    "tavily_web": true,
    "tavily_reddit": true
  },
  "alternatives_data": [
    { "name": "Obsidian", "description": "A powerful knowledge base", "platforms": ["Windows", "Mac", "Linux", "iOS", "Android"] }
  ],
  "app_store_results": [
    { "name": "Bear", "app_id": "1091189122", "store": "app_store", "rating": 4.6, "category": "Productivity" }
  ],
  "search_queries": [
    "mobile web note-taking power tool competitors 2026",
    "site:reddit.com note taking app mobile power tool"
  ]
}

// output_data
{
  "competitors": [
    {
      "id": "notion",
      "name": "Notion",
      "description": "All-in-one workspace for notes, docs, and project management",
      "url": "https://notion.so",
      "category": "Productivity",
      "pricing_model": "Freemium"
    },
    {
      "id": "obsidian",
      "name": "Obsidian",
      "description": "Local-first markdown knowledge base",
      "url": "https://obsidian.md",
      "category": "Note-taking",
      "pricing_model": "Free + paid sync"
    }
  ],
  "sources": ["https://google.com/search?q=...", "https://reddit.com/r/..."]
}

// user_selection — null (see select_competitors)
```

### step_type: "select_competitors"

User's choice of which competitors to explore in detail.

```json
// input_data
{
  "competitors_presented": [
    { "id": "notion", "name": "Notion" },
    { "id": "obsidian", "name": "Obsidian" },
    { "id": "bear", "name": "Bear" },
    { "id": "evernote", "name": "Evernote" }
  ]
}

// output_data — null (purely a user selection step)

// user_selection
{
  "selected_competitor_ids": ["notion", "obsidian"],
  "selected_names": ["Notion", "Obsidian"]
}
```

### step_type: "explore"

Deep analysis of selected competitors. Scrapes websites + Reddit. For build intent, also includes gap analysis.

```json
// input_data
{
  "products_to_explore": ["Notion", "Obsidian"],
  "product_urls": { "Notion": "https://notion.so", "Obsidian": "https://obsidian.md" },
  "intent_type": "build"
}

// output_data
{
  "market_overview": {
    "title": "Personal Note-taking Market Overview",
    "content": "## Market Overview\n\nThe personal note-taking space...",
    "sources": ["https://..."]
  },
  "product_profiles": [
    {
      "name": "Notion",
      "content": "## Notion\n\n**Summary**: All-in-one workspace...\n\n**Features**:...",
      "features_summary": ["Blocks-based editor", "Database views", "AI assistant"],
      "pricing_tiers": "Free / Plus $10/mo / Business $18/mo",
      "target_audience": "Teams, students, individual productivity enthusiasts",
      "strengths": ["Flexible block system", "Strong integrations", "Free for personal use"],
      "weaknesses": ["Can be slow with large workspaces", "Steep learning curve", "Requires internet"],
      "reddit_sentiment": "Generally positive. Users love flexibility but complain about performance.",
      "sources": ["https://notion.so/pricing", "https://reddit.com/r/Notion/..."],
      "cached": false
    },
    {
      "name": "Obsidian",
      "content": "## Obsidian\n\n**Summary**: Local-first markdown...",
      "features_summary": ["Local markdown files", "Graph view", "Community plugins"],
      "pricing_tiers": "Free / Catalyst $25 one-time / Sync $4/mo",
      "target_audience": "Developers, researchers, privacy-conscious note-takers",
      "strengths": ["Local-first", "Extremely extensible", "Markdown standard"],
      "weaknesses": ["No real-time collaboration", "Mobile app less polished", "Plugin quality varies"],
      "reddit_sentiment": "Cult following. Users praise plugin ecosystem, complain about sync costs.",
      "sources": ["https://obsidian.md", "https://reddit.com/r/ObsidianMD/..."],
      "cached": true,
      "cached_at": "2026-02-08T14:30:00Z"
    }
  ],
  "gap_analysis": {
    "title": "Market Gaps & Opportunities",
    "problems": [
      {
        "id": "gap-mobile-first",
        "title": "No power tool has a good mobile-first experience",
        "description": "Existing power tools (Notion, Obsidian) treat mobile as an afterthought. ...",
        "evidence": ["Reddit users frequently complain about Notion mobile lag", "Obsidian mobile has limited plugin support"],
        "opportunity_size": "high"
      },
      {
        "id": "gap-offline-sync",
        "title": "Offline-first sync is poorly solved",
        "description": "Most tools require constant internet or charge for sync. ...",
        "evidence": ["Obsidian Sync costs $4/mo", "Notion doesn't work offline"],
        "opportunity_size": "medium"
      }
    ],
    "sources": ["https://..."]
  }
}

// user_selection — null for explore intent (terminal step)
// For build intent, user selects problems in the next step (select_problems)

// NOTE: gap_analysis is only present when intent_type = "build"
// For explore intent, gap_analysis is omitted from output_data
```

### step_type: "select_problems" (build intent only)

User's selection of which problem areas to focus on, from the gap analysis.

```json
// input_data
{
  "problems_presented": [
    { "id": "gap-mobile-first", "title": "No power tool has a good mobile-first experience" },
    { "id": "gap-offline-sync", "title": "Offline-first sync is poorly solved" },
    { "id": "gap-audio-text", "title": "No tool handles text + audio transcription well" }
  ]
}

// output_data — null (purely a user selection step)

// user_selection
{
  "selected_problem_ids": ["gap-mobile-first", "gap-offline-sync"],
  "selected_titles": ["No power tool has a good mobile-first experience", "Offline-first sync is poorly solved"]
}
```

### step_type: "define_problem" (build intent only)

Generates a focused problem statement from the selected gaps and research context.

```json
// input_data
{
  "selected_problems": [
    { "id": "gap-mobile-first", "title": "No power tool has a good mobile-first experience", "description": "..." },
    { "id": "gap-offline-sync", "title": "Offline-first sync is poorly solved", "description": "..." }
  ],
  "competitor_context": {
    "domain": "note-taking",
    "competitors_analyzed": ["Notion", "Obsidian"],
    "clarification_context": { "platform": ["Mobile", "Web"], "content_type": ["Text notes"], "positioning": ["Power tool"] }
  }
}

// output_data
{
  "problem_statement": {
    "title": "Your Problem Statement",
    "content": "Build a mobile-first power note-taking tool that makes graph-based knowledge management feel native on phones, with reliable offline-first sync that doesn't require a separate paid service.",
    "target_user": "Power users who want Obsidian-level depth on mobile",
    "key_differentiators": [
      "Mobile-native graph navigation (not a shrunken desktop view)",
      "Offline-first with free peer-to-peer sync",
      "Markdown-compatible but with mobile-optimized input"
    ],
    "validation_questions": [
      "Would mobile power users switch from Apple Notes for graph features?",
      "Can P2P sync deliver Obsidian Sync-level reliability at zero cost?"
    ]
  }
}

// user_selection — null (this is the terminal step for build intent)
```

---

## 7. Error Handling Strategy

### Principle: Partial Results Over Full Failures

Every research request generates multiple independent blocks. If one block fails (e.g., can't scrape Obsidian's website), the others still complete. The user sees what worked and gets a clear message about what didn't. **There is never a full error page unless the initial input classification fails.**

### LLM Failures

```
Request → call active_provider (e.g., Gemini Flash)
  ├─ Success → return response
  └─ Failure (429 / quota exhausted / timeout / 5xx)
       ├─ Log: provider, error type, timestamp
       ├─ Try next provider in fallback_chain
       │    ├─ Success → persist switch to llm_state table
       │    │            update in-memory cache
       │    │            return response
       │    └─ Failure → try next provider...
       └─ All providers exhausted
            → SSE: { type: "error", message: "AI service temporarily unavailable", recoverable: false, error_code: "BP-XXXXXX" }
            → Return any partial results already collected
```

**Key behavior**: The provider switch is permanent. Once Gemini fails and the system falls to GPT-4o-mini, ALL future requests use GPT-4o-mini. The founder must manually restore Gemini by updating the `llm_state` row in Supabase or restarting with updated config.

### Search Failures

```
tavily_search(query)
  ├─ Success → return results
  └─ Failure (network error / invalid API key / quota exhausted)
       ├─ Log error
       ├─ Try serper_search(query)  [first fallback]
       │    ├─ Success → return results
       │    └─ Failure → try duckduckgo_search(query)  [last-resort emergency]
       │         ├─ Success → return results
       │         └─ Failure → return empty results with warning
       └─ SSE: { type: "block_error", block_name: "Search", error: "Search temporarily unavailable", error_code: "BP-XXXXXX" }
```

**Search provider hierarchy**: Tavily (primary) → Serper (fallback) → DuckDuckGo (last-resort emergency). DuckDuckGo is only used when both Tavily and Serper are completely unavailable. It is always free with no quota, so it almost never fails unless there's a network issue.

### App Store Scraper Failures (V0-EXPERIMENTAL)

```
search_play_store(query) / search_app_store(query)
  ├─ Success → return results
  └─ Failure (rate-limited / library error / timeout >5s)
       ├─ Log warning
       └─ Return empty list → pipeline continues without app store data
```

**App store scrapers are wrapped in try/except** — failures are silently swallowed. The competitor pipeline continues with data from other sources (AlternativeTo, Serper, Reddit). If app store scrapers prove unreliable, the entire module is deferred to V1.

### Scraper Failures

Scraper calls are gated by a concurrency semaphore to respect Jina's 20 RPM free tier limit:

```python
# In scraper.py
_scrape_semaphore = asyncio.Semaphore(2)  # max 2 concurrent Jina calls

async def scrape(url: str) -> str:
    async with _scrape_semaphore:
        return await _jina_scrape(url)
    # fallback handled inside
```

Fallback flow:

```
scrape(url) — acquires semaphore slot
  ├─ _jina_scrape(url)
  │    ├─ Success → return scraped content
  │    └─ Failure (rate limited / quota / unreachable)
  │         ├─ Log error
  │         └─ Try _bs4_scrape(url)  [httpx + BeautifulSoup]
  │              ├─ Success → return scraped content (lower quality but functional)
  │              └─ Failure → raise ScraperError
  └─ On ScraperError → skip this product
     SSE: { type: "block_error", block_name: "Product Name", error: "Could not access product website", error_code: "BP-XXXXXX" }
```

### "Try Again" Behavior

When the frontend renders a `block_error` card with a "Try again" button, clicking it re-runs the **entire research pipeline** from the beginning (new `POST /api/research` with the same prompt). V0 does not support block-level retry — the pipeline is treated as an atomic unit for simplicity.

**Deferred to V1**: Block-level retry via `POST /api/research/{journey_id}/retry-block` with a `block_id` parameter.

### Frontend Error Rendering

| Error Type | UI Treatment |
|------------|-------------|
| `block_error` | Inline warning card in Workspace: yellow/amber background, user-friendly error message, `(Ref: BP-XXXXXX)` in small muted text, "Try again" button (re-runs full research) |
| `error` (recoverable) | Toast notification at top of Sidebar with user-friendly message + ref code. Auto-dismiss after 8 seconds. |
| `error` (non-recoverable) | Modal overlay with user-friendly message, `(Ref: BP-XXXXXX)` copyable ref code, and "Start New Research" button |
| LLM provider switch | Silent — user doesn't see this. Results continue normally from new provider. |

**Error display rules**: The frontend NEVER shows raw error strings, stack traces, HTTP status codes, provider names (e.g., "Gemini failed"), internal model names, or JSON parsing errors. All user-facing errors use friendly messages. The `error_code` field (format: `BP-XXXXXX`) is always displayed so users can report it and the team can grep backend logs for the exact code. See `DESIGN_GUIDE.md` for error display styling.

### Logging Standard (V0)

V0 uses a structured `print()`-based logger defined in `backend/app/config.py`. Every log line follows the format:

```
[2026-02-12T10:30:45.123456+00:00] [INFO] pipeline started | journey_id=abc-123 pipeline=classify intent=build
```

**Components**: `[ISO_TIMESTAMP] [LEVEL] message | key1=value1 key2=value2`

**Logger API** (defined in `config.py`, see `MODULE_SPEC.md` Section 1):

```python
from app.config import log, generate_error_code

# Always include journey_id when available
log("INFO", "pipeline started", journey_id="abc-123", pipeline="classify")
log("ERROR", "llm call failed", journey_id="abc-123", provider="gemini", error_code="BP-3F8A2C", error="quota exceeded")
```

**Error codes**: Every user-facing error (sent as `BlockErrorEvent` or `ErrorEvent` via SSE) MUST have an `error_code` generated by `generate_error_code()`. The same code appears in:
1. The backend log line (`error_code=BP-XXXXXX`)
2. The SSE event payload (`error_code: "BP-XXXXXX"`)
3. The user-facing UI (`Ref: BP-XXXXXX`)

This creates a direct link: user reports ref code, team greps logs for it.

**Mandatory log points** (every backend module must log at these points):

| Module | When | Level | Example |
|--------|------|-------|---------|
| `api/research.py` | Pipeline entry | INFO | `log("INFO", "pipeline started", journey_id=..., pipeline=..., intent=...)` |
| `api/research.py` | Pipeline exit | INFO | `log("INFO", "pipeline completed", journey_id=..., pipeline=..., duration_ms=...)` |
| `api/research.py` | Every SSE event sent | INFO | `log("INFO", "sse event sent", journey_id=..., event_type=..., step_type=...)` |
| `api/research.py` | SSE error event sent | ERROR | `log("ERROR", "sse error event sent", journey_id=..., error_code=..., message=..., recoverable=...)` |
| `llm.py` | Before LLM call | INFO | `log("INFO", "llm call started", journey_id=..., provider=..., prompt_type=...)` |
| `llm.py` | After LLM success | INFO | `log("INFO", "llm call succeeded", journey_id=..., provider=..., duration_ms=..., tokens_used=...)` |
| `llm.py` | LLM call failure | ERROR | `log("ERROR", "llm call failed", journey_id=..., provider=..., error=str(e), error_code=...)` |
| `llm.py` | Fallback to next provider | WARN | `log("WARN", "llm provider fallback", journey_id=..., from_provider=..., to_provider=..., reason=...)` |
| `llm.py` | Output validation failure | ERROR | `log("ERROR", "llm output validation failed", journey_id=..., raw_output=<truncated>, schema=..., error_code=...)` |
| `search.py` | Before search | INFO | `log("INFO", "search started", journey_id=..., provider=..., query=...)` |
| `search.py` | Search success | INFO | `log("INFO", "search completed", journey_id=..., provider=..., results_count=..., duration_ms=...)` |
| `search.py` | Search failure | ERROR | `log("ERROR", "search failed", journey_id=..., provider=..., error=str(e), error_code=...)` |
| `scraper.py` | Before scrape | INFO | `log("INFO", "scrape started", journey_id=..., url=..., method=...)` |
| `scraper.py` | Scrape success | INFO | `log("INFO", "scrape completed", journey_id=..., url=..., content_length=..., duration_ms=...)` |
| `scraper.py` | Scrape fallback | WARN | `log("WARN", "scrape failed, trying fallback", journey_id=..., url=..., method="jina", error=str(e))` |
| `scraper.py` | All scrape methods failed | ERROR | `log("ERROR", "scrape failed all methods", journey_id=..., url=..., error_code=...)` |
| `db.py` | Write failure | ERROR | `log("ERROR", "db write failed", journey_id=..., operation=..., error=str(e), error_code=...)` |
| `db.py` | Read failure | ERROR | `log("ERROR", "db read failed", journey_id=..., operation=..., error=str(e), error_code=...)` |
| `app_stores.py` | Scrape failure | WARN | `log("WARN", "app store scrape failed", journey_id=..., store=..., error=str(e))` |
| `alternatives.py` | Failure | WARN | `log("WARN", "alternatives lookup failed", journey_id=..., error=str(e))` |

**Request correlation for REST calls**: The frontend includes an `X-Request-Id` header (UUID) on every fetch call. The backend logs this via FastAPI middleware so REST errors can be matched to backend logs.

**V1 migration**: Replace the `log()` function body with `structlog.get_logger()` calls. All existing call sites keep working. Add correlation IDs, JSON output, and Sentry integration. See `TECH_DEBT.md`.

### Single-Instance Assumption (V0)

V0 assumes a **single backend process** (one uvicorn worker). The following in-memory state is per-process and will not be shared across instances:

- `_active_researches` dict in `api/research.py` (request deduplication)
- `_active_provider` variable in `llm.py` (cached LLM provider state)
- `_scrape_semaphore` in `scraper.py` (concurrency limiter)

This is acceptable for V0 on Railway's single-instance deployment. If you run multiple workers (`uvicorn --workers N`), deduplication becomes ineffective and the semaphore is per-process (so actual concurrency = N * 2 Jina calls).

**Deferred to V1**: Redis-backed deduplication, DB-backed semaphore, multi-instance support. See [TECH_DEBT.md](TECH_DEBT.md).

---

## 8. Caching Strategy

### Product Cache Flow

```
Research request for "Notion"
    │
    ▼
db.py: get_cached_product("notion")  ← normalized_name lookup
    │
    ├─ Found + last_scraped_at < 7 days ago
    │   └─ Return cached data immediately (zero API calls)
    │      SSE block includes: { cached: true, cached_at: "2026-02-05T..." }
    │
    └─ Not found OR last_scraped_at > 7 days ago
        ├─ Run full pipeline: search → scrape → LLM analysis
        ├─ Store result in products table (upsert on normalized_name)
        └─ Return fresh data
            SSE block includes: { cached: false }
```

### Cache Invalidation

- **Automatic**: TTL-based. After 7 days, the next request triggers a re-scrape.
- **Manual**: User clicks "Refresh" button on a cached block → backend re-scrapes regardless of TTL.
- **No global purge**: There's no admin UI to clear the cache. If needed, DELETE from products table via Supabase SQL editor.

### Competitor Relationship Cache

Competitor relationships are cached for 14 days. The relationship "Notion competes with Obsidian" doesn't change frequently. This prevents re-running the competitor discovery pipeline for known relationships.

### AlternativeTo Alternatives Cache

```
Competitor search for "note-taking" products
    │
    ▼
db.py: get_cached_alternatives("notion")  ← normalized_name lookup
    │
    ├─ Found + scraped_at < 30 days ago
    │   └─ Return cached alternatives immediately (zero API calls)
    │      Merge with live search results before passing to LLM
    │
    └─ Not found OR scraped_at > 30 days ago
        └─ Skip cache, rely on live search sources (Tavily/Serper, App Stores, Reddit)
```

The `alternatives_cache` table is pre-seeded via `python -m app.seed_alternatives`. It stores product-to-alternatives mappings from AlternativeTo with a 30-day TTL. The pipeline checks this table FIRST before any live search — instant and free.

### Cache TTL Summary

| What's Cached | TTL | Storage | Cache Key |
|--------------|-----|---------|-----------|
| Product profiles | 7 days | `products` table | `normalized_name` |
| Competitor relationships | 14 days | `competitor_relationships` table | `product_id + competitor_id` |
| AlternativeTo alternatives | 30 days | `alternatives_cache` table | `normalized_name` |

---

## 9. Request Deduplication

### Problem

If a user double-clicks "RUN", or the frontend retries a failed SSE connection, the backend could start two identical research pipelines for the same query.

### Solution (V0 — Simple)

**Frontend**: Disable the RUN button immediately on click. Re-enable on `research_complete` or `error` event.

**Backend**: Track active research sessions in a module-level dict:
```python
# In api/research.py
_active_researches: dict[str, asyncio.Event] = {}

# On new request:
# 1. Generate a dedup key from (journey_id or prompt hash)
# 2. If key exists in _active_researches → return error "Research already in progress"
# 3. Else → add key, start research, remove key on completion
```

This is in-memory only (lost on restart), which is acceptable for V0. The frontend button disable handles 99% of cases.

**Deferred to V1**: Server-side idempotency middleware with persistent idempotency keys.

---

## 10. Design Token Architecture

See [DESIGN_GUIDE.md](DESIGN_GUIDE.md) for the full visual design system.

The Cozy Sand theme is implemented entirely in `tailwind.config.ts`. Usage in components:

```tsx
// Example: using theme tokens in components
<div className="bg-sand">                          {/* #F9F7F2 */}
  <div className="bg-workspace rounded-panel p-card-padding">  {/* white, 24px radius, 20px padding */}
    <h1 className="font-serif text-charcoal">      {/* Newsreader, #1F1F1F */}
      Begin your inquiry.
    </h1>
    <p className="font-sans text-muted">           {/* Inter, #737373 */}
      Your research notes will appear here.
    </p>
    <button className="bg-terracotta text-white rounded-button">
      Start Research
    </button>
  </div>
</div>
```

---

## 11. Deployment Architecture

### Railway Setup

```
Railway Project: "blueprint"
│
├── Service 1: frontend
│   ├── Source: /frontend directory
│   ├── Build: Dockerfile (Node.js)
│   ├── Port: 3000
│   ├── Environment:
│   │   └── NEXT_PUBLIC_API_URL=https://<backend-public-domain>.railway.app
│   └── Domain: blueprint.up.railway.app (or custom domain)
│
│   NOTE: NEXT_PUBLIC_API_URL must be the backend's PUBLIC Railway URL,
│   not the internal URL. The browser makes direct calls to the backend
│   (SSE streams, API requests) and cannot reach internal Railway hostnames.
│   The internal URL (backend.railway.internal:8000) is only usable for
│   server-to-server communication (e.g., Next.js API routes calling the backend).
│
├── Service 2: backend
│   ├── Source: /backend directory
│   ├── Build: Dockerfile (Python)
│   ├── Port: 8000
│   ├── Environment:
│   │   ├── GEMINI_API_KEY=...
│   │   ├── OPENAI_API_KEY=...
│   │   ├── ANTHROPIC_API_KEY=...
│   │   ├── TAVILY_API_KEY=...
│   │   ├── SERPER_API_KEY=...
│   │   ├── SUPABASE_URL=...
│   │   ├── SUPABASE_SERVICE_KEY=...
│   │   └── JINA_API_KEY=...
│   └── Internal URL: backend.railway.internal:8000
│
└── Shared: railway.toml

External:
└── Supabase Project: "blueprint-db"
    ├── PostgreSQL database
    ├── Tables created via SQL editor
    └── No Auth in V0 (Supabase Auth activated in V1)
```

### Local Development

```bash
# Terminal 1: Backend
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm install && npm run dev  # port 3000
```

Frontend `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Future Migration to Vercel

When ready to move frontend to Vercel:
1. Deploy `frontend/` to Vercel
2. Set `NEXT_PUBLIC_API_URL` to Railway backend's **public** URL
3. Add Railway backend's public domain to FastAPI's CORS allowed origins
4. Done — zero code changes

---

## 12. Security Considerations (V0)

V0 has minimal security surface since there's no auth and no user data:

- **API keys**: All secrets on backend only. Frontend has zero secrets.
- **CORS**: FastAPI allows only the frontend origin (Railway domain + localhost for dev).
- **Rate limiting**: `slowapi` middleware on the backend. Global rate limit (e.g., 20 req/min per IP) to prevent abuse.
- **Input validation**: Pydantic models validate all API inputs. Prompt injection is a concern — the LLM system prompt includes instructions to stay on-topic.
- **No PII**: V0 stores no personal data. Journeys are anonymous. No email, no name, no IP.
- **Supabase service key**: Used server-side only (never in frontend). If leaked, attacker gets full DB access — mitigated by Railway's env var encryption.

---

## 13. Future Extensibility

### How the V0 architecture supports V1+ features

| Future Feature | What changes | What stays the same |
|---|---|---|
| **"Improve" flow (V1)** | New pipeline branch in `research.py`, new prompts in `prompts.py` | Classify step (already detects `improve` intent), SSE protocol, frontend |
| **App Store scraping (V1 if V0-EXPERIMENTAL fails)** | Stabilize `app_stores.py` module (already exists in V0), add `app_reviews` block type | AlternativeTo pipeline, Serper search, SSE protocol |
| **Auth (V1)** | Add Supabase Auth, add `user_id` column to journeys, add JWT middleware to FastAPI | All API endpoints, all business logic, all frontend components |
| **LLM tiers (V1)** | Add tier lookup to `llm.py`, expand `LLM_CONFIG` to have per-tier chains | litellm calls, prompt templates, fallback mechanism |
| **New product modules (V1)** | Add new prompt in `prompts.py`, new block type in `models.py`, new step in `research.py` | SSE protocol, frontend block rendering (just a new block type) |
| **Infinite canvas (V2+)** | Add `parent_step_id` to journey_steps, change queries to recursive CTEs | Product cache, LLM module, scraper, search — all unchanged |
| **Mobile (V1)** | Responsive CSS in components | All backend code, all API contracts |
| **Move FE to Vercel** | Change one env var | All code |
| **Add Redis cache (V2)** | Add cache check in `db.py` before Supabase query | All API endpoints, all frontend code |

### Key extensibility decisions

1. **Flat file structure**: Adding a new module = adding functions to existing files or creating one new file. No interface inheritance to set up.
2. **SSE protocol**: New block types are automatically supported — the frontend just renders a new card type. No protocol changes needed.
3. **Pydantic models in one file**: Adding a new model = adding a class to `models.py`. When the file grows past ~300 lines, split by domain (product models, journey models, etc.).
4. **litellm abstraction**: Any LLM provider supported by litellm (100+) works by just changing the model string in config. Zero code changes.
