# External Integrations

**Analysis Date:** 2025-02-19

## APIs & External Services

**LLM Providers (via litellm):**
- Google Gemini - Primary (gemini-3-flash-preview, gemini-2.5-flash, gemini-2.0-flash)
- OpenAI - Fallback (gpt-4o-mini)
- Anthropic - Fallback (claude-3-haiku)
- SDK/Client: `litellm` in `backend/app/llm.py`
- Auth: `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

**Search:**
- Tavily - Primary web + Reddit search
  - Endpoint: `https://api.tavily.com/search`
  - Auth: `TAVILY_API_KEY`
  - Implementation: `backend/app/search.py` (`_tavily_search`)
- Serper - Fallback search
  - Endpoint: `https://google.serper.dev/search`
  - Auth: `SERPER_API_KEY`
  - Implementation: `backend/app/search.py` (`_serper_search`)
- DuckDuckGo - Last-resort (no API key)
  - Implementation: `duckduckgo_search.DDGS` in `backend/app/search.py`

**Scraping:**
- Jina Reader - Primary URL-to-markdown
  - Endpoint: `https://r.jina.ai/{url}`
  - Auth: `JINA_API_KEY` (optional, higher rate without)
  - Implementation: `backend/app/scraper.py` (`_jina_scrape`)
- BeautifulSoup - Fallback HTML parsing (no external call)

**AlternativeTo (planned/deferred):**
- `alternativeto.net`, `get.alternative.to` - Curated alternatives
- Seeding script: `backend/scripts/dry_run_alternativeto.py` (uses Jina for scraping)
- `alternatives.py` and `app_stores.py` referenced in `MODULE_SPEC.md` but not present in repo; app store scrapers commented out in `backend/requirements.txt` due to dependency conflicts

## Data Storage

**Databases:**
- Supabase (PostgreSQL)
  - Connection: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
  - Client: `supabase` Python SDK in `backend/app/db.py`
  - Tables: `journeys`, `journey_steps`, `products`, `alternatives_cache`, `llm_state`, `user_choices_log`

**File Storage:**
- Local filesystem only (no S3/Supabase Storage)

**Caching:**
- In-memory: `_active_researches` dedup in `backend/app/api/research.py`
- DB cache: `products` (7-day TTL), `alternatives_cache` (30-day TTL)

## Authentication & Identity

**Auth Provider:**
- Custom / None - V0 is anonymous
- `user_id` column exists as stub for V1 migration
- No OAuth, no session auth

## Monitoring & Observability

**Error Tracking:**
- None - Structured `log()` in `backend/app/config.py` (print-based in V0)

**Logs:**
- Structured print: `[ISO_TIMESTAMP] [LEVEL] message | key=value`
- Request ID: `X-Request-Id` header logged via `RequestIdMiddleware` in `backend/app/main.py`
- Error codes: `BP-XXXXXX` via `generate_error_code()` for user-facing refs

## CI/CD & Deployment

**Hosting:**
- Railway - Backend and frontend as separate services
- `backend/railway.toml`: Dockerfile, uvicorn, `/api/health`
- `frontend/railway.toml`: Dockerfile, npm start, `/` healthcheck

**CI Pipeline:**
- GitHub Actions: `.github/workflows/test.yml`
- Jobs: unit-tests (pytest), prompt-evals (on schedule/prompts.py change), lint (ruff), type-check (pyright)
- Python 3.12, pip cache

## Environment Configuration

**Required env vars:**
- `GEMINI_API_KEY` - LLM primary
- `TAVILY_API_KEY` - Search primary
- `SUPABASE_URL` - Database
- `SUPABASE_SERVICE_KEY` - Database

**Optional env vars:**
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` - LLM fallbacks
- `SERPER_API_KEY` - Search fallback
- `JINA_API_KEY` - Scraper (higher rate limit)
- `CORS_ORIGINS` - Comma-separated origins (default: `http://localhost:3000`)
- `ENVIRONMENT` - development | production
- `NEXT_PUBLIC_API_URL` - Frontend API base (default: `http://localhost:8000`)

**Secrets location:**
- `backend/.env` - Local dev (never committed)
- Railway project env vars - Production
- GitHub Secrets - CI (GEMINI_API_KEY, TAVILY_API_KEY, etc. for prompt evals)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

---

*Integration audit: 2025-02-19*
