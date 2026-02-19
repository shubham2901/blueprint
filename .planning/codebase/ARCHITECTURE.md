# Architecture

**Analysis Date:** 2025-02-19

## Pattern Overview

**Overall:** Two-service monorepo with REST + SSE streaming. Backend-centric data flow — frontend never calls external services directly.

**Key Characteristics:**
- FastAPI backend + Next.js 15 App Router frontend, deployed on Railway
- SSE (Server-Sent Events) for progressive research results; user input via separate POST requests
- Intent-based pipeline branching: classify → clarify → competitors → explore → (build-only: gap analysis → problem select → problem statement)
- Plain async functions for services; no class-based service layer
- Pydantic v2 models in `backend/app/models.py` as single source of truth; `frontend/lib/types.ts` mirrors them

## Layers

**API Layer:**
- Purpose: HTTP endpoints, SSE streaming, request validation
- Location: `backend/app/api/`
- Contains: `research.py` (POST /api/research, POST /api/research/{id}/selection), `journeys.py` (GET /api/journeys, GET /api/journeys/{id})
- Depends on: db, llm, prompts, scraper, search, models
- Used by: Frontend via fetch + SSE

**Pipeline/Orchestration Layer:**
- Purpose: Intent-based research flow orchestration
- Location: `backend/app/api/research.py` (inline pipeline functions: `_run_classify_pipeline`, `_run_competitor_pipeline`, `_run_explore_pipeline`, `_run_problem_pipeline`)
- Contains: Step sequencing, SSE event emission, error handling, deduplication
- Depends on: llm, prompts, db, scraper, search
- Used by: API endpoints

**Service Layer (plain functions):**
- Purpose: LLM calls, web search, scraping, DB operations
- Location: `backend/app/llm.py`, `backend/app/search.py`, `backend/app/scraper.py`, `backend/app/db.py`, `backend/app/alternatives.py`, `backend/app/app_stores.py`
- Contains: Async functions; no classes. Fallback chains (Tavily→Serper→DDG for search; Jina→BS4 for scraping; LLM provider chain)
- Depends on: config, models
- Used by: Pipeline layer

**Prompt Layer:**
- Purpose: LLM prompt templates
- Location: `backend/app/prompts.py`
- Contains: `build_classify_prompt`, `build_competitors_prompt`, `build_explore_prompt`, `build_gap_analysis_prompt`, `build_problem_statement_prompt`, etc.
- Depends on: models (for schema hints in prompts)
- Used by: llm.py (via pipeline)

**Data/Models Layer:**
- Purpose: Request/response and SSE event types
- Location: `backend/app/models.py`
- Contains: Pydantic models for ResearchRequest, SelectionRequest, ClassifyResult, CompetitorList, ProductProfile, GapAnalysis, ProblemStatement, all SSE event types
- Depends on: pydantic
- Used by: All backend modules

**Frontend State Layer:**
- Purpose: Research state, SSE event handling, API calls
- Location: `frontend/app/explore/[journeyId]/page.tsx` (single SSE orchestration owner), `frontend/lib/api.ts`, `frontend/lib/types.ts`
- Contains: useReducer for ResearchState, parseSSEStream, startResearch, sendSelection, getJourneys, getJourney
- Depends on: types
- Used by: Workspace, Sidebar, ClarificationPanel, CompetitorSelector, ProblemSelector

**UI Layer:**
- Purpose: Pages and components
- Location: `frontend/app/`, `frontend/components/`
- Contains: page.tsx (landing), explore/[journeyId]/page.tsx (workspace), dashboard/page.tsx, Sidebar, Workspace, ResearchBlock, ClarificationPanel, CompetitorSelector, ProblemSelector, ProgressSteps, PromptInput, BlockErrorCard
- Depends on: lib/api, lib/types
- Used by: User

## Data Flow

**Research Flow (Build Intent — 4 streams):**

1. User submits prompt on landing → navigates to `/explore/new` with prompt in sessionStorage
2. Explore page loads → calls `POST /api/research` with prompt
3. Backend: classify intent → create journey (build) → SSE: journey_started, step_started, step_completed, clarification_needed, waiting_for_selection → stream closes
4. User answers clarification → clicks Continue → `POST /api/research/{id}/selection` with step_type: clarify
5. Backend: competitor search (alternatives_cache → app stores + Tavily/Serper + Reddit → LLM synthesis) → SSE: block_ready (competitor_list), waiting_for_selection → stream closes
6. User selects competitors → `POST /api/research/{id}/selection` with step_type: select_competitors
7. Backend: explore (scrape + Reddit per product, product cache check) → gap analysis → SSE: block_ready (market_overview, product_profile, gap_analysis), waiting_for_selection → stream closes
8. User selects problems → `POST /api/research/{id}/selection` with step_type: select_problems
9. Backend: problem statement generation → SSE: block_ready (problem_statement), research_complete → stream closes

**State Management:**
- Backend: In-memory `_active_researches` dict for dedup; `_active_provider` in llm.py; `_scrape_semaphore` in scraper.py (single-instance assumption)
- Frontend: useReducer in explore page for ResearchState; no global store (useState/useReducer only)

## Key Abstractions

**ResearchBlock:**
- Purpose: Typed research result (market_overview, competitor_list, product_profile, gap_analysis, problem_statement)
- Examples: `backend/app/models.py` (ResearchBlock), `frontend/lib/types.ts` (ResearchBlock)
- Pattern: Discriminated union by `type` field; `output_data` holds typed structured data per block type

**SSE Event Types:**
- Purpose: Contract between backend and frontend for streaming
- Examples: `backend/app/models.py` (JourneyStartedEvent, BlockReadyEvent, WaitingForSelectionEvent, etc.)
- Pattern: Pydantic models serialized to `data: {json}\n\n`; frontend parses via parseSSEStream in `frontend/lib/api.ts`

**Journey + Steps:**
- Purpose: Linear research session container
- Examples: `backend/app/db.py` (create_journey, get_journey, save_step), `journey_steps` table with step_type, input_data, output_data, user_selection
- Pattern: 7 step types: classify, clarify, find_competitors, select_competitors, explore, select_problems, define_problem

**Fallback Chains:**
- Purpose: Resilience when primary provider fails
- Examples: `backend/app/search.py` (Tavily→Serper→DDG), `backend/app/llm.py` (fallback_chain from config), `backend/app/scraper.py` (Jina→BS4)
- Pattern: try primary, catch, try next; log and persist provider switch for LLM

## Entry Points

**Backend:**
- Location: `backend/app/main.py`
- Triggers: uvicorn `app.main:app`
- Responsibilities: create_app(), CORS, RequestIdMiddleware, rate limiting (slowapi), router registration (research, journeys), GET /api/health

**Frontend:**
- Location: `frontend/app/layout.tsx`, `frontend/app/page.tsx`
- Triggers: Next.js dev/build
- Responsibilities: Root layout (fonts, globals), landing page with prompt input; navigates to `/explore/new` on submit

**SSE Orchestration:**
- Location: `frontend/app/explore/[journeyId]/page.tsx`
- Triggers: User navigates to /explore/new or /explore/{id}
- Responsibilities: Single owner of all SSE streams; manages ResearchState via reducer; dispatches events to Workspace, Sidebar, ClarificationPanel, CompetitorSelector, ProblemSelector

## Error Handling

**Strategy:** Partial results over full failures. Block-level errors (block_error) allow other blocks to complete. Fatal errors (error event) close stream.

**Patterns:**
- Backend: try/except with fallback chains; `generate_error_code()` for every user-facing error; log with error_code; SSE BlockErrorEvent or ErrorEvent with error_code
- Frontend: Never show raw errors; map to friendly messages + `(Ref: BP-XXXXXX)`; BlockErrorCard for block errors; toast for recoverable; modal for non-recoverable

## Cross-Cutting Concerns

**Logging:** `log(level, message, **context)` from `backend/app/config.py`; structured print format; always include journey_id when available. Mandatory log points in AGENTS.md.

**Validation:** Pydantic for all API inputs and LLM outputs. LLM output: parse JSON → validate against model → retry with "fix JSON" prompt on failure.

**Authentication:** V0 anonymous; no auth. user_id column exists as stub for V1.

---

*Architecture analysis: 2025-02-19*
