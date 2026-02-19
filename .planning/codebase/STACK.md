# Technology Stack

**Analysis Date:** 2025-02-19

## Languages

**Primary:**
- Python 3.12 - Backend: FastAPI app, LLM, search, scraper, DB, API routes
- TypeScript 5 - Frontend: Next.js app, components, lib

**Secondary:**
- JSON - Config, SSE event payloads, Pydantic schemas

## Runtime

**Environment:**
- Node.js 20 - Frontend (from `frontend/Dockerfile`)
- Python 3.12 - Backend (from `backend/requirements.txt`, `backend/Dockerfile`)

**Package Manager:**
- pip - Backend (`backend/requirements.txt`)
- npm - Frontend (`frontend/package.json`, `frontend/package-lock.json`)
- Lockfile: present for both (requirements.txt pins versions; package-lock.json)

## Frameworks

**Core:**
- FastAPI >=0.115.0 - Backend API, SSE streaming, middleware
- Next.js 16.1.6 - Frontend App Router, SSR, routing
- React 19.2.3 - UI components

**Testing:**
- pytest >=8.3.0 - Backend unit and integration tests (`backend/tests/`)
- pytest-asyncio >=0.24.0 - Async test support
- deepeval >=2.0.0 - LLM prompt evaluation (`backend/tests/evals/`)

**Build/Dev:**
- Vite (via Next.js) - Frontend bundling
- uvicorn >=0.34.0 - ASGI server for FastAPI
- Tailwind CSS 4 - Styling (`frontend/app/globals.css`, `@tailwindcss/postcss`)
- PostCSS - CSS processing (`frontend/postcss.config.mjs`)

## Key Dependencies

**Critical:**
- litellm >=1.55.0 - LLM abstraction (Gemini, OpenAI, Anthropic fallback chain)
- pydantic >=2.10.0 - Request/response models, LLM output validation
- supabase >=2.11.0 - PostgreSQL client, DB operations
- tavily-python >=0.5.0 - Primary web search (Tavily API)
- duckduckgo-search >=7.0.0 - Last-resort search fallback

**Infrastructure:**
- httpx >=0.28.0 - Async HTTP client (Tavily, Serper, Jina)
- beautifulsoup4 >=4.12.0 - HTML parsing fallback for scraper
- slowapi >=0.1.9 - Rate limiting
- pydantic-settings >=2.7.0 - Environment config

**Frontend:**
- shadcn/ui (radix-ui) - Base UI components
- lucide-react - Icons
- tailwind-merge, clsx, class-variance-authority - Styling utilities

## Configuration

**Environment:**
- Backend: `backend/app/config.py` via pydantic-settings; loads from `.env` or Railway env vars
- Frontend: `NEXT_PUBLIC_API_URL` in env; `frontend/lib/api.ts` reads `process.env.NEXT_PUBLIC_API_URL`
- Config: `backend/app/config.py` (Settings class, LLM_CONFIG dict)

**Build:**
- `frontend/next.config.ts` - Next.js config
- `frontend/tsconfig.json` - TypeScript (paths: `@/*` → `./*`)
- `frontend/postcss.config.mjs` - PostCSS with `@tailwindcss/postcss`
- `backend/pytest.ini` - pytest asyncio mode, markers (eval, slow)

## Platform Requirements

**Development:**
- Python 3.12, Node 20
- API keys: GEMINI_API_KEY, TAVILY_API_KEY (required); OPENAI_API_KEY, ANTHROPIC_API_KEY, SERPER_API_KEY, JINA_API_KEY (optional)
- Supabase: SUPABASE_URL, SUPABASE_SERVICE_KEY

**Production:**
- Railway - Two services: backend (Dockerfile), frontend (Dockerfile)
- `backend/railway.toml`, `frontend/railway.toml` - Deploy config

---

*Stack analysis: 2025-02-19*
