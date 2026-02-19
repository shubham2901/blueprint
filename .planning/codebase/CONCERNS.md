# Codebase Concerns

**Analysis Date:** 2025-02-19

## Tech Debt

**In-memory state (single-instance assumption):**
- Issue: All critical runtime state lives in module-level dicts/variables. Lost on restart. Breaks with multiple workers.
- Files: `backend/app/api/research.py` (`_active_researches`), `backend/app/llm.py` (`_active_provider`, `_rate_limited_until`), `backend/app/scraper.py` (`_scrape_semaphore`)
- Impact: Request deduplication ineffective across restarts; LLM provider state resets; semaphore is per-process (N workers = N×2 concurrent Jina calls).
- Fix approach: Move dedup to Redis or DB; persist LLM state in DB; use distributed semaphore for scraper. See TECH_DEBT.md "Multi-Instance Support".

**Rate limiting not applied:**
- Issue: slowapi limiter is configured in `backend/app/main.py` but no endpoint uses `@limiter.limit()`. Research, journeys, and health endpoints are unprotected.
- Files: `backend/app/main.py`, `backend/app/api/research.py`, `backend/app/api/journeys.py`
- Impact: No per-IP throttling. Single client can exhaust LLM/search API quotas. Abuse risk before public launch.
- Fix approach: Add `@limiter.limit("10/minute")` (or similar) to POST /api/research and POST /api/research/{id}/selection. Apply to journeys endpoints when implemented.

**Journeys API stub:**
- Issue: `backend/app/api/journeys.py` defines router but has no implemented endpoints. GET /api/journeys and GET /api/journeys/{id} return 404.
- Files: `backend/app/api/journeys.py`
- Impact: Dashboard cannot list or load journeys. Frontend `getJourneys()` and `getJourney()` will fail. Session list (Screen 7) non-functional.
- Fix approach: Implement GET /api/journeys (list) and GET /api/journeys/{id} (detail) per MODULE_SPEC.md. Query `journeys` and `journey_steps` via `db.py`.

**competitor_relationships table unused:**
- Issue: ARCHITECTURE.md and PLAN.md describe a 14-day competitor relationship cache. No code reads or writes this table.
- Files: `backend/app/db.py`, `backend/app/api/research.py`
- Impact: Documented caching strategy is incomplete. Competitor discovery always hits live search; no relationship reuse.
- Fix approach: Add `get_cached_competitor_relationships()` and `store_competitor_relationships()` in db.py. Wire into competitor pipeline when relationships are discovered.

**Alternatives seed script missing:**
- Issue: Docs reference `python -m app.seed_alternatives` to populate `alternatives_cache`. No `app.seed_alternatives` or `app.alternatives` module exists.
- Files: `backend/app/` (missing), `backend/scripts/dry_run_alternativeto.py` (dry run only)
- Impact: `alternatives_cache` is empty unless manually populated. Competitor pipeline always passes `alternatives_data=None` to prompts; no AlternativeTo pre-seeding benefit.
- Fix approach: Create `backend/app/alternatives.py` with `seed_alternatives()` CLI entry point. Reuse parsing logic from `backend/scripts/dry_run_alternativeto.py`. Call `db.store_alternatives()`.

**App store scrapers deferred:**
- Issue: `backend/requirements.txt` has app-store-scraper and google-play-scraper commented out due to dependency conflicts (requests pin). ARCHITECTURE.md describes app_stores.py integration; no such file exists.
- Files: `backend/requirements.txt`, `backend/app/api/research.py` (always passes `app_store_results=None`)
- Impact: Competitor discovery lacks app store data (ratings, similar apps). Pipeline works but with reduced signal.
- Fix approach: Resolve dependency conflicts (e.g., fork, use alternative libs, or isolate in subprocess). Create `backend/app/app_stores.py` per AGENTS.md. Wire into competitor pipeline.

**Dependency injection absent:**
- Issue: Direct imports for db, llm, search, scraper. No FastAPI `Depends()` layer. Testing requires monkeypatching at import sites.
- Files: `backend/app/api/research.py`, `backend/app/llm.py`, `backend/app/db.py`
- Impact: Harder to write clean unit tests with mocked dependencies. Tight coupling.
- Fix approach: Wrap `get_supabase`, `call_llm`, etc. in `Depends()` providers. Change endpoint signatures to accept injected deps. See TECH_DEBT.md "Dependency Injection".

**Structured logging deferred:**
- Issue: `backend/app/config.py` uses `print()`-based `log()` for V0. No JSON output, no correlation IDs in log aggregation.
- Files: `backend/app/config.py`
- Impact: Debugging intermittent failures (provider flakiness, scraper timeouts) is manual. No structured querying in Railway logs.
- Fix approach: Replace with structlog. Add `journey_id` as context var. Configure JSON output for production. See TECH_DEBT.md "Structured Logging".

---

## Known Bugs

**Explore page redirect on reload:**
- Symptoms: User reloads `/explore/{journeyId}` (non-"new") and is immediately redirected to `/`. No way to view a completed journey by URL.
- Files: `frontend/app/explore/[journeyId]/page.tsx`
- Trigger: Navigate to `/explore/abc-123` or refresh that page.
- Workaround: None. V0 cannot restore SSE state. User must start new research from home.

**Refine pipeline gap_step lookup wrong:**
- Symptoms: For `define_problem` refine, gap data is read from `explore` step's `output_data.gap_analysis`. Gap analysis is stored in the explore step's output, but the code looks at `gap_step = next((s for s in steps if s.get("step_type") == "explore"), None)` — explore step may not contain gap_analysis in its output_data structure depending on save logic.
- Files: `backend/app/api/research.py` (around line 271–276 in `_run_refine_pipeline`)
- Trigger: User refines "define problem" step. May get empty/missing problems.
- Workaround: Verify journey step schema stores gap_analysis in the correct step (explore vs a separate gap_analysis step).

---

## Security Considerations

**CORS configuration:**
- Risk: `settings.cors_origins` defaults to `http://localhost:3000`. If production frontend URL is not added, browser will block API calls.
- Files: `backend/app/config.py`, `backend/app/main.py`
- Current mitigation: Env var `CORS_ORIGINS` (comma-separated) configurable. No wildcard in production.
- Recommendations: Ensure Railway env includes production frontend URL. Audit for `*` in production.

**API keys in environment:**
- Risk: Keys (Gemini, Tavily, Serper, Supabase) in `.env` and Railway env. Leaked if env dumps or misconfigured logging.
- Files: `backend/app/config.py`, `backend/.env` (existence only — never read)
- Current mitigation: `.env` in `.gitignore`. Config centralizes env reads. No keys in logs.
- Recommendations: Rotate keys if ever exposed. Add key rotation procedure to runbook.

**Supabase service role key:**
- Risk: Service role key bypasses RLS. Full DB access. If leaked, attacker can read/write all data.
- Files: `backend/app/config.py`, `backend/app/db.py`
- Current mitigation: Key only on backend. Never sent to frontend.
- Recommendations: When auth arrives, add RLS. Use least-privilege service role if Supabase supports it.

**No request size limits:**
- Risk: Large prompt payloads could cause memory pressure or DoS.
- Files: `backend/app/api/research.py`, FastAPI default
- Current mitigation: None explicit.
- Recommendations: Add `Request` body size limit or validate `prompt` max length (e.g., 10KB).

---

## Performance Bottlenecks

**Sequential product profile scraping:**
- Problem: Explore pipeline scrapes each selected competitor. Semaphore limits to 2 concurrent Jina calls, but N competitors still mean N/2 batches.
- Files: `backend/app/api/research.py` (`_run_explore_pipeline`), `backend/app/scraper.py`
- Cause: `_scrape_semaphore(2)` + per-product scrape + Reddit search. No batching of similar domains.
- Improvement path: Increase semaphore to 4–5 if Jina rate limits allow. Consider caching Reddit results by query. Pre-warm product cache for popular products.

**Search returns empty on all-provider failure:**
- Problem: `search.search()` returns `[]` when Tavily, Serper, and DuckDuckGo all fail. Caller receives empty list; LLM gets no search context.
- Files: `backend/app/search.py` (line 69), `backend/app/api/research.py`
- Cause: Graceful degradation — avoid hard failure. But pipeline continues with empty data, producing weak competitor lists.
- Improvement path: Consider sending `block_error` for search failure when alternatives_cache also has no data, so user sees partial failure instead of low-quality output.

**LLM timeout and fallback chain:**
- Problem: Each provider has 30s timeout. Fallback chain can take 30s × 5 providers = 2.5 minutes in worst case.
- Files: `backend/app/llm.py`
- Cause: `LLM_CALL_TIMEOUT_SECONDS = 30`. No circuit breaker; each failure triggers next provider.
- Improvement path: Reduce timeout to 15s for non-primary providers. Add circuit breaker to skip known-down providers quickly.

---

## Fragile Areas

**Research pipeline (`api/research.py`):**
- Files: `backend/app/api/research.py` (~1100 lines)
- Why fragile: Monolithic. Multiple pipelines (classify, competitor, explore, gap, problem, refine) in one file. Deep nesting, many `async for` generators. Step ordering and schema assumptions are implicit.
- Safe modification: Change one pipeline at a time. Add tests for the specific pipeline. Preserve SSE event order and types.
- Test coverage: `backend/tests/test_pipeline.py` and `backend/tests/test_api.py` cover main flows. Refine pipeline and edge cases (e.g., missing steps) less covered.

**LLM output validation:**
- Files: `backend/app/llm.py`, `backend/app/models.py`
- Why fragile: LLMs return malformed JSON frequently. Pydantic validation can fail on extra fields, wrong types, or truncated output. Retry logic exists but schema drift can cause persistent failures.
- Safe modification: Add new fields as optional. Use `model_config = {"extra": "ignore"}` where appropriate. Test with real LLM output samples.
- Test coverage: `backend/tests/test_llm.py` mocks litellm. Evals in `backend/tests/evals/` use real API (optional).

**SSE event parsing (frontend):**
- Files: `frontend/lib/api.ts` (`parseSSEStream`)
- Why fragile: Buffers chunks, splits on `\n\n`. Malformed or partial JSON can cause parse errors. No schema validation of event payloads.
- Safe modification: Add try/catch around `JSON.parse`. Consider validating event `type` before dispatch. Log parse failures with truncated payload.
- Test coverage: No frontend unit tests in V0 (deferred to V1 Playwright).

**Explore page state machine:**
- Files: `frontend/app/explore/[journeyId]/page.tsx`
- Why fragile: useReducer with many event types. Phase transitions depend on SSE event order. StrictMode workaround for SSE cleanup is timing-dependent.
- Safe modification: Add explicit phase transition tests. Document valid event sequences. Avoid adding new phases without updating reducer.
- Test coverage: None (frontend tests deferred).

---

## Scaling Limits

**Single uvicorn process:**
- Current capacity: One process handles all requests. Async I/O allows many concurrent SSE streams, but CPU-bound work (JSON parsing, Pydantic validation) blocks event loop.
- Limit: ~50–100 concurrent research sessions before latency degrades. Memory grows with active streams.
- Scaling path: Add `--workers N` only after moving in-memory state to Redis/DB. See TECH_DEBT.md "Multi-Instance Support".

**Jina Reader rate limits:**
- Current capacity: Free tier ~20 RPM. With semaphore(2), 2 concurrent requests. Paid tier has higher limits.
- Limit: Popular products cause cache hits; cold cache causes many scrapes. Burst of new domains can hit rate limit.
- Scaling path: Add Jina API key for higher rate. Consider Firecrawl/Playwright fallback for critical paths.

**Supabase connection pool:**
- Current capacity: Supabase client manages connections. Default pool size.
- Limit: High concurrency can exhaust connections. No explicit pool config.
- Scaling path: Tune Supabase pool settings. Add connection pooler (PgBouncer) if needed.

---

## Dependencies at Risk

**litellm:**
- Risk: Rapidly evolving. Provider-specific bugs (e.g., Gemini 3 Flash routing) can break. `warnings.filterwarnings` suppresses "coroutine never awaited" — masking potential async bugs.
- Files: `backend/app/llm.py`, `backend/requirements.txt`
- Impact: LLM calls fail or hang. Fallback chain mitigates.
- Migration plan: Pin litellm version. Test upgrades in staging. Consider direct provider SDKs if litellm becomes unreliable.

**duckduckgo-search:**
- Risk: Unofficial library. DuckDuckGo can change HTML structure; scraper breaks. No API key — last-resort fallback.
- Files: `backend/app/search.py`, `backend/requirements.txt`
- Impact: Search fails when Tavily and Serper both fail. Returns empty.
- Migration plan: Accept as best-effort. If it breaks, remove or replace with another free search option.

**app-store-scraper / google-play-scraper:**
- Risk: Commented out due to `requests==2.23.0` conflict with litellm/tiktoken. May have breaking changes when uncommented.
- Files: `backend/requirements.txt`
- Impact: App store data unavailable. Competitor discovery weaker.
- Migration plan: Resolve conflicts (virtualenv isolation, alternative libs). Re-enable when stable.

---

## Missing Critical Features

**Journey list and detail API:**
- Problem: GET /api/journeys and GET /api/journeys/{id} not implemented. Dashboard cannot load sessions.
- Blocks: Screen 7 (session list), "View past research" flows.

**Alternatives cache seeding:**
- Problem: No automated or manual seed path for `alternatives_cache`. Table empty by default.
- Blocks: Optimal competitor discovery. Pipeline works without it but with weaker AlternativeTo signal.

**Research cancellation:**
- Problem: No `POST /api/research/{id}/cancel`. User navigating away drops SSE; backend continues pipeline in background.
- Blocks: User control. Wastes LLM/search/scrape quota on abandoned sessions.

---

## Test Coverage Gaps

**Frontend:**
- What's not tested: All components, API client, SSE parsing, state machine, error handling.
- Files: `frontend/` (entire directory)
- Risk: Regressions in UI, SSE handling, or error display go unnoticed.
- Priority: Medium. V0 defers to V1 Playwright.

**Refine pipeline:**
- What's not tested: `_run_refine_pipeline`, `_refine_competitors`, `_refine_explore`, `_refine_gap_analysis`, `_refine_problem_statement`. Edge cases: missing steps, empty competitors.
- Files: `backend/app/api/research.py`, `backend/tests/test_pipeline.py`
- Risk: Refine produces wrong or empty output. Gap step lookup bug may persist.
- Priority: High.

**Scraper fallback:**
- What's not tested: BS4 fallback when Jina fails. Semaphore behavior under load.
- Files: `backend/app/scraper.py`, `backend/tests/`
- Risk: Scraper fails silently or blocks under concurrency.
- Priority: Medium.

**DB error paths:**
- What's not tested: Supabase timeout, connection failure, partial write failure. `get_cached_product` and `store_product` return None/empty on exception.
- Files: `backend/app/db.py`, `backend/tests/`
- Risk: Pipeline continues with missing data. User sees incomplete results without clear error.
- Priority: Medium.

**Prompt evaluation golden cases:**
- What's not tested: Edge cases in classify, competitors, refine. Golden datasets may be stale.
- Files: `backend/tests/evals/datasets/*.json`, `backend/tests/evals/`
- Risk: LLM prompt changes degrade quality. Evals require real API key; may not run in CI.
- Priority: Medium.

---

*Concerns audit: 2025-02-19*
