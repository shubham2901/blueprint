# Codebase Structure

**Analysis Date:** 2025-02-19

## Directory Layout

```
[project-root]/
├── backend/                 # FastAPI backend
│   ├── app/                  # Application code
│   │   ├── api/              # HTTP endpoints
│   │   │   ├── research.py   # POST /api/research, POST /api/research/{id}/selection
│   │   │   └── journeys.py   # GET /api/journeys, GET /api/journeys/{id}
│   │   ├── main.py           # App factory, CORS, middleware, routers
│   │   ├── config.py          # Settings, LLM_CONFIG, log, generate_error_code
│   │   ├── models.py         # All Pydantic models (source of truth)
│   │   ├── db.py             # Supabase client, product/alternatives cache, journey CRUD
│   │   ├── llm.py            # litellm calls, fallback chain, validation
│   │   ├── prompts.py        # All LLM prompt templates
│   │   ├── search.py         # Tavily, Serper, DuckDuckGo, search_reddit
│   │   ├── scraper.py        # Jina Reader + BS4 fallback
│   │   ├── alternatives.py   # AlternativeTo scraper, alternatives_cache
│   │   └── app_stores.py     # Google Play + App Store scrapers (V0-EXPERIMENTAL)
│   ├── tests/                # pytest tests
│   │   ├── conftest.py       # Fixtures
│   │   ├── test_api.py       # API/SSE tests
│   │   ├── test_llm.py       # LLM tests
│   │   ├── test_search.py    # Search tests
│   │   ├── test_pipeline.py  # Pipeline tests
│   │   ├── test_prompts.py   # Prompt tests
│   │   └── evals/            # Evaluation tests
│   │       └── datasets/     # classify_cases.json, competitors_cases.json, refine_cases.json
│   ├── scripts/              # CLI scripts
│   ├── requirements.txt
│   ├── pytest.ini
│   └── Dockerfile
├── frontend/                 # Next.js 15 App Router
│   ├── app/
│   │   ├── layout.tsx        # Root layout, fonts, globals
│   │   ├── page.tsx          # Landing (Screen 1)
│   │   ├── explore/
│   │   │   └── [journeyId]/
│   │   │       └── page.tsx  # Two-panel workspace (Screens 2-6, 9)
│   │   ├── dashboard/
│   │   │   └── page.tsx      # Session list (Screen 7)
│   │   ├── login/
│   │   │   └── page.tsx      # Login (Screen 8 — UI shell)
│   │   └── edu-dashboard/    # Edu dashboard variant
│   ├── components/
│   │   ├── ui/               # shadcn/ui base components
│   │   ├── Sidebar.tsx       # Right panel: progress, prompt, chat
│   │   ├── Workspace.tsx     # Left panel: research blocks
│   │   ├── PromptInput.tsx   # Floating input + RUN button
│   │   ├── ResearchBlock.tsx # Single research card
│   │   ├── ProgressSteps.tsx # Step indicator (3 for explore, 5 for build)
│   │   ├── ClarificationPanel.tsx # Multi-question chips + Continue
│   │   ├── CompetitorSelector.tsx  # Checkbox list
│   │   ├── ProblemSelector.tsx    # Gap selection (build only)
│   │   ├── BlockErrorCard.tsx     # Error display
│   │   ├── BlueprintView.tsx # Curated document view
│   │   └── SessionCard.tsx    # Dashboard card
│   ├── lib/
│   │   ├── api.ts            # Fetch client, SSE parsing, startResearch, sendSelection
│   │   ├── types.ts          # TypeScript types (mirrors models.py)
│   │   └── utils.ts          # clsx, twMerge
│   ├── tailwind.config.ts    # Cozy Sand design tokens
│   ├── next.config.ts
│   └── package.json
├── .planning/codebase/       # GSD codebase analysis docs
├── designs/                  # HTML mockups, screenshots
├── Archive/                  # Earlier iterations
├── ARCHITECTURE.md            # Technical architecture (project doc)
├── PLAN.md                   # Product + technical plan
├── MODULE_SPEC.md            # File-by-file specs
├── AGENTS.md                 # Agent instructions
├── DESIGN_GUIDE.md           # Cozy Sand theme
├── TECH_DEBT.md              # Deferred decisions
└── FOUNDER_TASKS.md          # Founder-authored tasks
```

## Directory Purposes

**backend/app:**
- Purpose: Core backend logic
- Contains: config, models, db, llm, prompts, search, scraper, alternatives, app_stores, api
- Key files: `main.py`, `models.py`, `config.py`, `api/research.py`

**backend/app/api:**
- Purpose: HTTP endpoints
- Contains: research.py (SSE streaming), journeys.py (REST CRUD)
- Key files: `research.py` (pipeline orchestration)

**backend/tests:**
- Purpose: pytest unit and integration tests
- Contains: test_*.py, conftest.py, evals/ with datasets
- Key files: `test_api.py`, `test_llm.py`, `test_search.py`, `conftest.py`

**frontend/app:**
- Purpose: Next.js App Router pages
- Contains: layout, page (landing), explore/[journeyId], dashboard, login, edu-dashboard
- Key files: `explore/[journeyId]/page.tsx` (SSE owner), `page.tsx` (landing)

**frontend/components:**
- Purpose: Reusable UI components
- Contains: Sidebar, Workspace, ResearchBlock, ClarificationPanel, CompetitorSelector, ProblemSelector, ProgressSteps, PromptInput, BlockErrorCard, BlueprintView, SessionCard, ui/
- Key files: `Workspace.tsx`, `Sidebar.tsx`, `ResearchBlock.tsx`

**frontend/lib:**
- Purpose: Shared utilities, API client, types
- Contains: api.ts, types.ts, utils.ts
- Key files: `api.ts` (fetch + SSE), `types.ts` (mirrors models.py)

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: FastAPI app, uvicorn entry
- `frontend/app/layout.tsx`: Root layout
- `frontend/app/page.tsx`: Landing page
- `frontend/app/explore/[journeyId]/page.tsx`: Workspace, SSE orchestration

**Configuration:**
- `backend/app/config.py`: Settings, LLM_CONFIG, log, generate_error_code
- `frontend/tailwind.config.ts`: Cozy Sand design tokens
- `frontend/next.config.ts`: Next.js config

**Core Logic:**
- `backend/app/api/research.py`: Pipeline orchestration, SSE streaming
- `backend/app/llm.py`: LLM calls, fallback, validation
- `backend/app/db.py`: Supabase, product cache, journey CRUD
- `backend/app/search.py`: Web search with fallback
- `backend/app/scraper.py`: Jina + BS4 scraping
- `backend/app/prompts.py`: Prompt templates

**Testing:**
- `backend/tests/conftest.py`: Fixtures
- `backend/tests/test_api.py`: API/SSE tests
- `backend/tests/test_llm.py`: LLM mocks
- `backend/tests/test_search.py`: Search mocks

## Naming Conventions

**Files:**
- Python: snake_case (`research.py`, `config.py`)
- TypeScript/React: PascalCase for components (`Sidebar.tsx`, `ResearchBlock.tsx`), camelCase for lib (`api.ts`, `types.ts`)

**Directories:**
- kebab-case for routes (`[journeyId]`, `edu-dashboard`)
- lowercase for app subdirs (`api`, `explore`, `dashboard`)

## Where to Add New Code

**New API Endpoint:**
- Implementation: `backend/app/api/` (new router or add to research/journeys)
- Register router in `backend/app/main.py`
- Tests: `backend/tests/test_api.py`

**New Pipeline Step:**
- Implementation: `backend/app/api/research.py` (new _run_*_pipeline or extend existing)
- Prompts: `backend/app/prompts.py`
- Models: `backend/app/models.py` (new event/block types)
- Frontend types: `frontend/lib/types.ts`
- UI: `frontend/components/` (new selector or block renderer in Workspace)

**New Component:**
- Implementation: `frontend/components/` (PascalCase.tsx)
- Import in Workspace or Sidebar as needed

**Utilities:**
- Backend: Add to existing module or new `backend/app/utils.py`
- Frontend: `frontend/lib/utils.ts` or new `frontend/lib/*.ts`

## Special Directories

**.planning/codebase:**
- Purpose: GSD codebase analysis (ARCHITECTURE.md, STRUCTURE.md, etc.)
- Generated: By gsd-codebase-mapper
- Committed: Yes

**designs:**
- Purpose: HTML mockups, screenshots from Stitch
- Generated: External
- Committed: Yes

**Archive:**
- Purpose: Earlier iterations, deprecated docs
- Generated: Manual
- Committed: Yes

**backend/tests/evals/datasets:**
- Purpose: JSON test cases for evals (classify, competitors, refine)
- Generated: Manual or script
- Committed: Yes

---

*Structure analysis: 2025-02-19*
