# Blueprint — V0 Product & Technical Plan

---

## Part 1: Product Plan

### Vision

A product and market research tool for B2C software. A PM or founder describes what they want to build or explore, and gets structured competitive intelligence, market gap analysis, and a focused problem statement — in minutes instead of days.

### Target Users

- Product managers (B2C, Growth, 0-to-1)
- Founders exploring new markets
- Anyone doing competitive research on software products

### MVP Scope (V0)

#### Module B1 — Intent Classifier + Clarifier

- User inputs: any natural language prompt (e.g., "I want to build a note taking app", "Notion", "tell me about edtech in India", "how are you?")
- System classifies intent into one of 5 types: `build`, `explore`, `improve`, `small_talk`, `off_topic`
- For `small_talk` / `off_topic`: respond immediately, no journey created
- For `improve`: redirect to `explore` flow with the product as anchor (full "improve" pipeline deferred to V1)
- For `build` / `explore`: generate multi-question clarification (platform, audience, positioning, etc.) and present as structured UI (chips, multi-select)

#### Module B2 — Competitor Finder

- Given clarified context, find 5-10 competitors via web search + Reddit (site-search via Tavily/Serper)
- For each competitor: name, one-line description, URL, category, estimated pricing model
- Present as a selectable list (checkboxes) — user picks which ones to explore further

#### Module B2.5 — Deep Explorer + Gap Analyzer

- "Explore" triggers a deeper profile for selected competitors: features summary, pricing tiers, target audience, strengths/weaknesses, user sentiment from Reddit
- Data sources: product websites (Jina/BS4 scraping) + Reddit threads (via site-search `site:reddit.com` through Tavily/Serper)
- For `build` intent only: after profiles, generate a gap analysis identifying underserved/unserved market needs
- User selects problem areas from the gap analysis → system generates a focused problem statement

### User Flow (V0 — Build Intent, Full Path)

```
1. User lands on homepage
2. Types a prompt: "I want to build a note taking app"
3. System classifies: intent = "build", domain = "note-taking"
4. System shows multi-question clarification:
   - Platform? [Mobile] [Desktop] [Web] [Cross-platform] (multi-select)
   - Content type? [Text] [Audio] [Visual] [All-in-one] (multi-select)
   - Closest to your vision? [Simple & fast] [Power tool] [All-in-one workspace] [Specialized] (single-select)
5. User selects: Mobile + Web, Text, Power tool
6. System searches web + Reddit, finds 8-10 competitors
7. User selects 3-4 to explore, clicks "Explore Selected"
8. System shows structured profiles for each (from websites + Reddit):
   - Summary, features, pricing, target audience, strengths, weaknesses
   - User sentiment from Reddit threads
   - Links to source pages
9. System shows gap analysis: "Market Gaps & Opportunities"
   - Gap 1: No power tool has a good mobile-first experience
   - Gap 2: Offline-first sync is solved poorly across tools
   - Gap 3: No tool handles text + audio transcription well
10. User selects Gap 1 + Gap 2
11. System generates problem statement:
    "Build a mobile-first power note-taking tool that makes graph-based
     knowledge management feel native on phones, with reliable
     offline-first sync that doesn't require a separate paid service."
12. Journey is complete. Everything is saved.
```

### User Flow (V0 — Explore Intent)

```
1. User types: "Tell me about edtech in India"
2. System classifies: intent = "explore"
3. Clarification: What area? [K-12] [Test prep] [Professional upskilling] [Language learning]
4. User selects "Test prep"
5. System finds competitors (Byju's, Unacademy, PhysicsWallah, etc.)
6. User selects 3 to explore → gets profiles
7. Research complete (no gap analysis, no problem statement for explore intent)
```

### User Flow (V0 — Quick Response)

```
1. User types: "How are you?"
2. System classifies: intent = "small_talk"
3. Immediate response: "I'm Blueprint, a product research assistant. What would you like to explore?"
4. No journey created. No LLM pipeline.
```

### Product Principles

1. **Intent-first design**: System understands what the user wants (build, explore, learn) and tailors the pipeline accordingly.
2. **User-led exploration**: System proposes, user chooses. No runaway research.
3. **Structured UI over chat**: Radio buttons, cards, checkboxes — not "type 1 or 2".
4. **Links to sources**: Every claim has a source link. Tool gives summaries, user can go deeper.
5. **Saved journeys**: Every exploration path is saved. User can revisit or continue.
6. **Learn from choices**: Log what users select to improve suggestions over time.

### Future Modules (post-V0, in order)

| Priority | Module | Description |
|----------|--------|-------------|
| Next | "Improve" Flow | Single-product deep dive without competitor analysis (V1) |
| Next | B3: Feature Extractor | Deep feature lists per product |
| Next | B4: Pricing Extractor | Detailed pricing tiers and breakdowns |
| Next | B5: Sentiment Analyzer | Quantitative scoring from G2, Reddit, app stores |
| Next | App Store Integration | Play Store + App Store scraping for reviews, screenshots |
| Later | B6: Feature Comparator | Side-by-side feature matrix |
| Later | B7: Pricing Comparator | Side-by-side pricing table |
| Later | B8: Market Landscaper | Full categorized market map |
| Future | Persona Generator | User personas from public data |
| Future | JTBD Identifier | Jobs-to-be-done framework |
| Future | PRD Writer | Auto-generate PRDs from accumulated research |

---

## Part 2: Technical Stack

| Layer | Technology | Cost |
|-------|-----------|------|
| Frontend | Next.js 15 (App Router, TypeScript) + shadcn/ui + Tailwind | $0 |
| Backend | FastAPI (Python 3.12, async, Pydantic v2) | $0 |
| Database | Supabase (PostgreSQL only — no Auth in V0) | $0 (free tier) |
| LLM | Gemini 2.0 Flash via litellm | $0 (free tier) |
| Search | Tavily Search API (primary) + Serper (fallback) + DuckDuckGo (last-resort) | $0 |
| Scraping | Jina Reader API (20 RPM free) + httpx + BeautifulSoup fallback | $0 |
| Hosting | Railway (two services in one project) | $5/mo |
| UI Components | shadcn/ui (Radix + Tailwind) | $0 |
| **Total** | | **$5/month** |

---

## Part 3: V0 Scope and Constraints

### What V0 includes

- Fully anonymous — no auth, no user accounts, no session tracking
- Single LLM tier — free only (Gemini 2.0 Flash with fallback chain)
- Intent classification (5 types: `build`, `explore`, `improve`, `small_talk`, `off_topic`)
- Multi-question clarification (platform, audience, positioning, etc.)
- Reddit data via site-search (`site:reddit.com {query}` through Tavily/Serper)
- Basic gap analysis (build intent only) — LLM-synthesized market gaps from competitor profiles
- Problem statement generation (build intent only) — actionable problem definition from selected gaps
- Global product cache with 7-day TTL (shared across all visitors)
- SSE streaming for progressive research results
- Linear journey model (step_number, not tree/graph)
- Partial results on failure (never a full error page)
- Request deduplication (frontend button disable + backend active-research tracking)
- All data flows through the backend (frontend never calls Supabase directly)
- Design tokens embedded in tailwind.config.ts (single file for entire Cozy Sand theme)

### What V0 does NOT include

- "Improve" flow (single-product deep dive without competitors) — V1
- Play Store / App Store scraping — V1
- App screenshots (image scraping, storage, rendering) — V1
- Quantitative sentiment scoring (numeric review aggregation) — V1
- Product Hunt / G2 / Hacker News integration — V1
- Full problem discovery (quantitative gap scoring, cross-referencing at scale) — V1
- Authentication (Google OAuth, session limits) — V1
- LLM tiers (free/smart/advanced subscriptions) — V1
- LLM budget tracking (per-provider spend monitoring) — V1
- Infinite canvas / branching journeys — V2+
- Mobile responsive design — V1
- Payments / Stripe — V1
- CI/CD pipeline — V1
- Monitoring / Sentry — V1

Full list of deferred items in [TECH_DEBT.md](TECH_DEBT.md).

---

## Part 4: Project Structure

### Backend (~15 core files)

```
backend/
  app/
    main.py              # FastAPI app, CORS, rate limiting middleware
    config.py            # Pydantic Settings (env vars) + LLM_CONFIG dict (persona, models, fallback chain)
    llm.py               # litellm calls, persona injection, reactive fallback, provider state persistence
    search.py            # tavily_search() (primary) + serper_search() (fallback) + duckduckgo_search() (last-resort) + search_reddit()
    scraper.py           # jina_scrape() + bs4_scrape() with try/except fallback
    alternatives.py      # AlternativeTo scraper + CLI seeder for alternatives_cache table
    app_stores.py        # Google Play + Apple App Store scrapers (V0-EXPERIMENTAL)
    prompts.py           # All prompt templates: classify, clarify, competitors, explore, gap_analysis, problem_statement
    models.py            # All Pydantic models: requests, responses, SSE events
    db.py                # Supabase client, product cache, alternatives cache, journey CRUD
    api/
      research.py        # POST /api/research — SSE streaming endpoint (intent-based pipeline orchestration)
      journeys.py        # GET /api/journeys — list journeys
  seed_alternatives.py   # CLI script: python -m app.seed_alternatives
  requirements.txt
  Dockerfile
  tests/
    __init__.py
    test_llm.py
    test_search.py
    test_api.py
```

### Frontend (~18 core files)

```
frontend/
  app/
    layout.tsx           # Root layout: fonts (Newsreader + Inter), global styles
    page.tsx             # Landing page (Screen 1)
    explore/
      [journeyId]/
        page.tsx         # Two-panel workspace (Screens 2-6, 9)
    dashboard/
      page.tsx           # Session list (Screen 7)
  components/
    ui/                  # shadcn/ui components: Button, Card, Input, Badge, Dialog (installed, themed)
    Sidebar.tsx          # Right panel: chat history, progress steps, prompt input
    Workspace.tsx        # Left panel: research blocks OR blueprint view
    PromptInput.tsx      # Floating input card with RUN button
    ResearchBlock.tsx    # Single research result card with edit/add-to-blueprint/delete
    ProgressSteps.tsx    # Vertical step indicator — dynamic steps based on intent_type (3 for explore, 5 for build)
    ProblemSelector.tsx  # Checkbox list of problem areas from gap analysis (build intent only)
    ClarificationPanel.tsx # Multi-question clarification UI with chips and "Continue" button
    BlueprintView.tsx    # Curated document with terracotta accent entries
    SessionCard.tsx      # Dashboard session card
    AuthModal.tsx        # Signup modal (Screen 8) — UI shell only, wiring deferred to V1
  lib/
    api.ts               # Fetch client + SSE event handler
    types.ts             # All TypeScript types (ResearchEvent, Block, Journey, etc.)
  tailwind.config.ts     # Cozy Sand design tokens embedded directly here
  next.config.ts
  package.json
  Dockerfile
```

### Root

```
product-research-tool/
  frontend/
  backend/
  railway.toml           # Multi-service Railway config
  .env.example           # Template for all env vars
  TECH_DEBT.md           # Deferred decisions and known shortcuts
  ARCHITECTURE.md        # Detailed technical architecture and decisions
  DESIGN_GUIDE.md        # Visual design system (Cozy Sand theme)
  PLAN.md                # This file
  README.md
  designs/               # HTML mockups from Stitch
  Archive/               # Earlier iterations
```

---

## Part 5: Database Schema

```sql
-- Research journeys (anonymous in V0, user_id stub for V1 auth migration)
CREATE TABLE journeys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID DEFAULT NULL,     -- NULL in V0 (anonymous). Will FK to auth.users in V1.
    intent_type TEXT DEFAULT 'explore',  -- 'build', 'explore' (V0). 'improve' redirects to explore.
    title TEXT,
    initial_prompt TEXT,
    status TEXT DEFAULT 'active',  -- active, completed, archived
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Linear steps within a journey
CREATE TABLE journey_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journey_id UUID REFERENCES journeys(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    step_type TEXT NOT NULL,       -- 'classify', 'clarify', 'find_competitors', 'select_competitors', 'explore', 'select_problems', 'define_problem'
    input_data JSONB,              -- what was sent to the API (schema varies by step_type — see ARCHITECTURE.md Section 6)
    output_data JSONB,             -- what the API returned (schema varies by step_type — see ARCHITECTURE.md Section 6)
    user_selection JSONB,          -- what the user chose from the options (null for non-selection steps)
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(journey_id, step_number)  -- prevent duplicate step numbers within a journey
);

-- Global product cache (shared across all visitors, 7-day TTL)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,  -- lowercase, trimmed (cache key)
    url TEXT,
    description TEXT,
    category TEXT,
    pricing_model TEXT,
    features_summary JSONB,
    strengths JSONB,
    weaknesses JSONB,
    sources JSONB,                         -- array of source URLs
    last_scraped_at TIMESTAMPTZ,           -- used for TTL check
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Competitor relationships (cached)
CREATE TABLE competitor_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    competitor_id UUID REFERENCES products(id) ON DELETE CASCADE,
    relationship_type TEXT DEFAULT 'direct',  -- 'direct', 'indirect', 'substitute'
    discovered_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(product_id, competitor_id)
);

-- AlternativeTo alternatives cache (pre-seeded, 30-day TTL)
CREATE TABLE alternatives_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,           -- lowercase, trimmed (lookup key)
    alternatives JSONB NOT NULL,             -- [{"name": "Obsidian", "description": "...", "platforms": [...]}]
    source_url TEXT,                         -- alternativeto.net URL that was scraped
    scraped_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(normalized_name)
);

-- LLM provider state (single row — tracks which provider is active after fallback)
CREATE TABLE llm_state (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),  -- enforces single row
    active_provider TEXT NOT NULL,
    switched_at TIMESTAMPTZ,
    switch_reason TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- User choice logs (for future ML/improvement — no user_id in V0)
CREATE TABLE user_choices_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journey_id UUID REFERENCES journeys(id),
    step_id UUID REFERENCES journey_steps(id),
    options_presented JSONB,
    options_selected JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Figma OAuth tokens
-- Logged-in users: stored by user_id (FK to auth.users when auth enabled)
-- Anonymous users: stored by session_id (from cookie)
CREATE TABLE figma_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NULL,           -- when logged in; FK to auth.users(id) in V1
    session_id TEXT NULL,        -- when anonymous (from bp_session cookie)
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT figma_tokens_owner_check CHECK (user_id IS NOT NULL OR session_id IS NOT NULL)
);
CREATE UNIQUE INDEX figma_tokens_user_id_key ON figma_tokens(user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX figma_tokens_session_id_key ON figma_tokens(session_id) WHERE session_id IS NOT NULL;

-- Prototype sessions (code generation — one active session per bp_session cookie)
-- Regenerate overwrites previous code (upsert by session_id)
CREATE TABLE prototype_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL UNIQUE,
    design_context JSONB NOT NULL,
    generated_code TEXT,
    thumbnail_url TEXT,
    frame_name TEXT,
    frame_width INTEGER,
    frame_height INTEGER,
    status TEXT DEFAULT 'pending',
    error_code TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Migration (if you have the old schema with session_id as PK):
-- ALTER TABLE figma_tokens ADD COLUMN user_id UUID NULL;
-- ALTER TABLE figma_tokens ADD COLUMN id UUID DEFAULT gen_random_uuid();
-- ALTER TABLE figma_tokens ALTER COLUMN id SET NOT NULL;
-- ALTER TABLE figma_tokens DROP CONSTRAINT figma_tokens_pkey;
-- ALTER TABLE figma_tokens ADD PRIMARY KEY (id);
-- ALTER TABLE figma_tokens ALTER COLUMN session_id DROP NOT NULL;
-- CREATE UNIQUE INDEX figma_tokens_user_id_key ON figma_tokens(user_id) WHERE user_id IS NOT NULL;
-- CREATE UNIQUE INDEX figma_tokens_session_id_key ON figma_tokens(session_id) WHERE session_id IS NOT NULL;
-- ALTER TABLE figma_tokens ADD CONSTRAINT figma_tokens_owner_check CHECK (user_id IS NOT NULL OR session_id IS NOT NULL);
```

---

## Part 6: API Endpoints

### Research Endpoints (SSE Streaming)

```
POST /api/research
  Input:  { "prompt": "I want to build a note taking app" }
  Output: SSE stream of events (see ARCHITECTURE.md Section 5 for full event protocol)
  Notes:  Classifies intent first.
          - small_talk / off_topic: returns quick_response event, NO journey created.
          - build / explore / improve: creates journey, streams classify + clarify steps.
          Stream pauses at waiting_for_selection when clarification is needed.

POST /api/research/:journey_id/selection
  Input:  { "step_type": "clarify" | "select_competitors" | "select_problems", "selection": { ... } }
  Output: SSE stream of events (continues pipeline from where it paused)
  Notes:  Loads the journey, reads the last step, and continues the research pipeline.
          - After "clarify": runs competitor search + selection
          - After "select_competitors": runs explore (+ gap analysis for build intent)
          - After "select_problems": runs problem statement generation (build intent only)
          Returns a NEW SSE stream with the same event types as POST /api/research.
```

These two endpoints together handle the full research flow. See ARCHITECTURE.md Section 3 (Data Flow) for the complete multi-stream lifecycle. Note: `classify` returning `small_talk` or `off_topic` does NOT create a journey — the quick response is returned in the initial stream and the connection closes.

### Journey Endpoints

```
GET  /api/journeys
  Output: { "journeys": [{ id, title, status, initial_prompt, created_at, updated_at, step_count }, ...] }

GET  /api/journeys/:id
  Output: { "journey": { id, title, status, initial_prompt, steps: [...], created_at, updated_at } }
```

### Utility Endpoints

```
GET  /api/health
  Output: { "status": "ok", "version": "0.1.0" }
```

---

## Part 7: Environment Variables

```bash
# Backend (.env)
GEMINI_API_KEY=...                # Primary LLM provider
OPENAI_API_KEY=...                # Fallback LLM provider
ANTHROPIC_API_KEY=...             # Fallback LLM provider
TAVILY_API_KEY=...                # Tavily Search API — primary web + Reddit search
SERPER_API_KEY=...                 # Serper API — fallback search provider
SUPABASE_URL=...                  # Supabase project URL
SUPABASE_SERVICE_KEY=...          # Supabase service role key (server-side only)
JINA_API_KEY=...                  # Optional — Jina Reader works without key at lower rate

# Frontend (.env)
NEXT_PUBLIC_API_URL=https://<backend-public-domain>.railway.app  # Backend's PUBLIC Railway URL (NOT internal URL — browsers can't reach internal hostnames)
```

Note: Frontend has only ONE env var — the backend URL. All secrets live on the backend. Frontend never calls external services directly.

---

## Part 8: Build Order (Feature-First, Vertical Slices)

Each phase produces something testable in the browser.

### Phase 0 — Scaffold (Day 1)

- Monorepo: `frontend/` + `backend/` + Dockerfiles + `railway.toml` + `.env.example`
- Backend: `main.py` (FastAPI with CORS + health check) + `config.py` (env vars + LLM config dict)
- Frontend: `layout.tsx` + `tailwind.config.ts` (Cozy Sand tokens) + shadcn/ui install + fonts (Newsreader + Inter)
- Create `TECH_DEBT.md`, `ARCHITECTURE.md`
- Verify both services start locally (`uvicorn` + `next dev`)

### Phase 1 — "Classify + Clarify + Competitors" (Core Pipeline)

- Backend: `llm.py` + `search.py` + `scraper.py` + `prompts.py` + `models.py` + `db.py`
- Backend: `api/research.py` — SSE endpoint, intent classification + clarification flow
- Backend: classify step (intent detection), clarify step (multi-question generation), competitor search (web + Reddit)
- Frontend: `page.tsx` (landing with prompt input) + `PromptInput.tsx`
- Frontend: `explore/[journeyId]/page.tsx` + `Workspace.tsx` + `Sidebar.tsx` + `ProgressSteps.tsx`
- Frontend: `ClarificationPanel.tsx` (multi-question with chips + "Continue" button)
- Frontend: `CompetitorSelector.tsx` (checkbox list)
- **Test**: type "I want to build a note taking app" → get clarification questions → answer → see competitors

### Phase 2 — "Explore + Gap Analysis + Problem Statement" (Build Intent Full Path)

- Backend: explore pipeline (scrape websites + Reddit, generate profiles)
- Backend: gap analysis (build intent only — synthesize market gaps from profiles)
- Backend: problem selection + problem statement generation
- Frontend: `ResearchBlock.tsx` (competitor profiles with Reddit sentiment)
- Frontend: gap analysis block rendering
- Frontend: `ProblemSelector.tsx` (checkbox list of market gaps)
- Frontend: problem statement block rendering
- **Test**: select competitors → see profiles + gap analysis → select problems → get problem statement
- **Test**: explore intent stops at profiles (no gap analysis)

### Phase 3 — Blueprint Tab (Screens 5, 6)

- Frontend: "Add to Blueprint" action on research blocks → `BlueprintView.tsx` with curated entries
- Frontend: inline block editing (terracotta border, editable text, done/cancel)
- Backend: persist blueprint entries in journey steps
- **Test**: add blocks to Blueprint, edit them, see curated document

### Phase 4 — Journey Persistence + Dashboard (Screen 7)

- Backend: `api/journeys.py` — save/load/list journeys
- Frontend: `dashboard/page.tsx` + `SessionCard.tsx`
- **Test**: research saves automatically, dashboard shows past sessions, resume works

### Phase 5 — Error Handling + Polish (Screen 9)

- Backend: reactive LLM fallback with provider persistence
- Backend: search/scraper fallback chains
- Backend: partial results strategy (block_error events alongside block_ready)
- Backend: request deduplication (track active researches by journey_id)
- Backend: rate limiting via slowapi
- Frontend: inline error/warning rendering for failed blocks
- Frontend: collapsed sidebar toggle (Screen 9)
- Frontend: loading skeleton states
- Frontend: `AuthModal.tsx` — UI shell only, no backend wiring
- **Test**: simulate failures, verify partial results and fallback behavior

### Phase 6 — Product Cache

- Backend: product cache logic in `db.py` — check `last_scraped_at` TTL before scraping, store results
- Frontend: "Last updated X days ago" label + manual refresh button on blocks
- **Test**: research a product, research again — second time uses cache

### Phase 7 — Tests + Deploy

- Backend tests: `test_llm.py` (mock litellm calls), `test_search.py` (mock Tavily/Serper/DDG), `test_api.py` (SSE endpoint integration)
- Supabase: create all tables via SQL editor
- Railway: deploy both services, configure env vars
- End-to-end smoke test on production
- **Test**: full flow works on deployed URL

---

## Related Documents

- [ARCHITECTURE.md](ARCHITECTURE.md) — Detailed technical architecture, ADRs, error handling, SSE protocol, JSONB schemas, data flows
- [MODULE_SPEC.md](MODULE_SPEC.md) — Low-level module specifications: function signatures, Pydantic models, TypeScript types, component props
- [AGENTS.md](AGENTS.md) — Rules and context for coding agents working on this codebase
- [FOUNDER_TASKS.md](FOUNDER_TASKS.md) — Tasks on the founder: prompts to write, API keys to get, infrastructure to set up
- [DESIGN_GUIDE.md](DESIGN_GUIDE.md) — Visual design system ("Cozy Sand" theme)
- [TECH_DEBT.md](TECH_DEBT.md) — All deferred decisions and known shortcuts
- [Archive/STITCH_PROMPTS.md](Archive/STITCH_PROMPTS.md) — Stitch prompts used to generate screen designs
- [designs/](designs/) — HTML screen mockups
