# Blueprint — Agent Instructions

Rules and context for coding agents working on this codebase. Read this file before making any changes.

---

## Project Overview

Blueprint is a product/market research tool. Users type a prompt describing what they want to build or explore, get intent-based structured competitive intelligence via SSE streaming — including competitor profiles, market gap analysis, and problem statements. Two-service monorepo: Next.js frontend + FastAPI backend, deployed on Railway.

## Key Documents

| Document | Purpose |
|----------|---------|
| `PLAN.md` | Product scope, tech stack, DB schema, build phases |
| `ARCHITECTURE.md` | Technical decisions, data flows, SSE protocol, error handling |
| `MODULE_SPEC.md` | Detailed file-by-file specs (function signatures, types, logic) |
| `DESIGN_GUIDE.md` | Visual design system (Cozy Sand theme: colors, typography, spacing) |
| `TECH_DEBT.md` | Everything intentionally deferred from V0 |
| `FOUNDER_TASKS.md` | Tasks for the founder: prompts to write, API keys to get, infra to set up |

**Read `MODULE_SPEC.md` before implementing any file.** It contains the exact function signatures, Pydantic models, and TypeScript types to use.

---

## Source of Truth Rules

- **Backend types**: `backend/app/models.py` is the single source of truth for all Pydantic models (requests, responses, SSE events, internal types).
- **Frontend types**: `frontend/lib/types.ts` mirrors `models.py`. When you change a model in `models.py`, update `types.ts` to match.
- **Design tokens**: `frontend/tailwind.config.ts` contains all Cozy Sand theme values. Do not hardcode hex colors or pixel values in components — use the Tailwind token names (e.g., `bg-sand`, `text-terracotta`, `rounded-card`).
- **Prompts**: `backend/app/prompts.py` contains all LLM prompt templates. Do not inline prompt strings in other files. **Important**: The actual prompt text is authored by the founder — implement the function signatures and wiring, but mark prompt text as `# TODO: Replace with founder-authored prompt` until provided.
- **Classify prompt**: The classify prompt (`build_classify_prompt`) generates both intent classification AND clarification questions in a single LLM call. This is the most complex prompt — its text comes from the founder.
- **Config**: `backend/app/config.py` contains all environment variables and LLM configuration. Do not read `os.environ` anywhere else.
- **DB schema**: Defined in `PLAN.md` Part 5. JSONB column schemas are defined in `ARCHITECTURE.md` Section 6.

---

## SSE Protocol Rules

The research flow uses a 2-endpoint pattern. **Do NOT attempt to send data over SSE connections.**

1. `POST /api/research` — classifies intent, creates journey (for build/explore), returns SSE stream
2. `POST /api/research/{journey_id}/selection` — sends user selection, returns NEW SSE stream

**Intent-based pipeline branching**: The first step always classifies intent. The pipeline then branches:
- `small_talk` / `off_topic` → quick response, stream closes, NO journey created
- `improve` → redirected to `explore` flow (full improve pipeline deferred to V1)
- `explore` → classify → clarify → competitors → explore → DONE (3 streams)
- `build` → classify → clarify → competitors → explore + gap analysis → problem select → problem statement → DONE (4 streams)

**7 step types** (stored in `journey_steps.step_type`): `classify`, `clarify`, `find_competitors`, `select_competitors`, `explore`, `select_problems` (build only), `define_problem` (build only).

Each SSE stream runs until it either:
- Sends a `quick_response` (no journey), then closes
- Needs user input: sends `waiting_for_selection`, then closes
- Completes: sends `research_complete`, then closes
- Fails: sends `error`, then closes

See `ARCHITECTURE.md` Section 5 for the full event type definitions and sequence diagrams.

---

## File Structure

```
backend/app/
  main.py           ← App factory, CORS, rate limiting, router setup
  config.py          ← Pydantic Settings + LLM_CONFIG dict
  models.py          ← ALL Pydantic models (source of truth for types)
  prompts.py         ← ALL LLM prompt templates (text authored by founder, wiring by agent)
  llm.py             ← litellm calls, fallback chain, output validation
  search.py          ← Serper API + DuckDuckGo last-resort fallback + search_reddit() via Serper
  scraper.py         ← Jina Reader + BS4 fallback, with semaphore
  alternatives.py    ← AlternativeTo scraper + CLI seeder for alternatives_cache table
  app_stores.py      ← Google Play + App Store scrapers (V0-EXPERIMENTAL)
  db.py              ← Supabase client, product cache, alternatives cache, journey CRUD
  api/
    research.py      ← POST /api/research + POST /api/research/{id}/selection (intent-based pipeline)
    journeys.py      ← GET /api/journeys, GET /api/journeys/{id}

frontend/
  app/
    layout.tsx       ← Root layout, fonts, global styles
    page.tsx         ← Landing page (Screen 1)
    explore/[journeyId]/page.tsx  ← Two-panel workspace (Screens 2-6)
    dashboard/page.tsx            ← Session list (Screen 7)
  components/
    ui/              ← shadcn/ui base components (installed + themed)
    Sidebar.tsx      ← Right panel: progress steps, prompt input, chat
    Workspace.tsx    ← Left panel: research blocks OR blueprint view
    PromptInput.tsx  ← Floating input with RUN button
    ResearchBlock.tsx ← Single research result card
    ProgressSteps.tsx ← Vertical step indicator (dynamic: 3 steps for explore, 5 for build)
    ClarificationPanel.tsx ← Multi-question clarification with chips + "Continue" button
    CompetitorSelector.tsx ← Checkbox list of competitors
    ProblemSelector.tsx ← Checkbox list of problem areas from gap analysis (build intent only)
    BlueprintView.tsx ← Curated document view
    SessionCard.tsx  ← Dashboard session card
    AuthModal.tsx    ← Signup modal (UI shell only in V0)
  lib/
    api.ts           ← Fetch client + SSE event handling
    types.ts         ← All TypeScript types (mirrors models.py)
  tailwind.config.ts ← Cozy Sand design tokens
```

---

## Coding Conventions

### Backend (Python)

- **Python 3.12**, async throughout
- **Pydantic v2** for all models (use `model_validator`, not `validator`)
- **Type hints** on all function signatures
- **No classes for services** — use plain async functions. No AbstractBaseClass patterns.
- **Error handling**: try/except with fallback, never let exceptions propagate to the SSE stream unhandled. Always send `block_error` or `error` SSE events.
- **Logging**: Use `print()` in V0 (structlog is a V1 item). Always include `journey_id` and context in log messages.
- **LLM calls**: Always go through `llm.py` functions. Never call `litellm` directly from other modules.
- **Database calls**: Always go through `db.py` functions. Never instantiate the Supabase client elsewhere.

### Frontend (TypeScript)

- **Next.js 15** App Router, TypeScript strict mode
- **shadcn/ui** for base components. Do not install other UI libraries.
- **Tailwind CSS** only — no CSS modules, no styled-components, no inline `style` props
- **Use design tokens**: `bg-sand`, `text-charcoal`, `rounded-card`, etc. Never hardcode colors.
- **Fonts**: Newsreader (serif, for headings) + Inter (sans, for UI text). Applied via `font-serif` and `font-sans`.
- **Server Components by default**. Only add `"use client"` when the component needs state, effects, or event handlers.
- **State management**: React useState/useReducer. No Redux, no Zustand in V0.

---

## Common Pitfalls to Avoid

1. **Do not use SSE for bidirectional communication.** SSE is server → client only. User input goes via POST requests.
2. **Do not hardcode provider strings.** Always read from `config.py` LLM_CONFIG fallback_chain.
3. **Do not skip Pydantic validation for LLM output.** LLMs return malformed JSON frequently. Always validate. See `ARCHITECTURE.md` Section 4 (LLM Output Validation).
4. **Do not use `backend.railway.internal` in NEXT_PUBLIC_API_URL.** Browsers cannot reach Railway internal hostnames. Use the backend's public URL.
5. **Do not create multiple Supabase clients.** Use the singleton from `db.py`.
6. **Do not add `user_id` logic beyond the NULL column.** V0 is anonymous. The `user_id` column exists as a stub for V1 migration only.
7. **Do not persist LLM provider switch per-request.** The switch is permanent (see ADR-3 in ARCHITECTURE.md). Only update `llm_state` when actually switching providers due to failure.
8. **Do not forget the scraper semaphore.** All Jina calls must go through the `asyncio.Semaphore(2)` to respect rate limits.
9. **Do not create a journey for small_talk/off_topic intents.** These get a `quick_response` event and the stream closes. No DB writes.
10. **Do not run gap analysis for explore intent.** Gap analysis and problem statement generation are build-intent-only features. Check `journey.intent_type` before running these pipeline stages.
11. **Reddit search uses Serper site-search, not a Reddit API.** Use `search_reddit(query)` from `search.py`, which wraps `search(f"site:reddit.com {query}")` via Serper API. No Reddit API key needed.
12. **Do not write prompt text.** The founder writes prompt text (see `FOUNDER_TASKS.md`). Implement function signatures and schema wiring. Use `# TODO: Replace with founder-authored prompt` as placeholder.
13. **Do not use Google Custom Search API.** Serper API has replaced Google CSE for all web search. Use `SERPER_API_KEY` env var, not `GOOGLE_SEARCH_API_KEY`.
14. **App store scrapers are V0-EXPERIMENTAL.** `app_stores.py` uses `google-play-scraper` and `app-store-scraper` libraries. If they are flaky, rate-limited, or slow (>5s per query), wrap all functions in try/except and return empty lists. The competitor pipeline must handle empty app store results gracefully.
15. **Competitor pipeline checks alternatives_cache first.** Before running any live search for competitors, check `db.get_cached_alternatives()`. The pipeline order is: DB cache → live search (app stores + Serper + Reddit) in parallel → LLM synthesis.

---

## Testing Conventions (V0)

- Tests live in `backend/tests/`
- Use `pytest` + `pytest-asyncio`
- Mock external services (litellm, Serper, Jina, Supabase, app store scrapers) — never make real API calls in tests
- Test files: `test_llm.py`, `test_search.py`, `test_api.py`
- Frontend: no tests in V0 (deferred to V1 with Playwright)

---

## When Changing the Schema

If you modify the database schema (tables, columns, constraints):

1. Update the SQL in `PLAN.md` Part 5
2. Update the JSONB schemas in `ARCHITECTURE.md` Section 6 (if JSONB columns changed)
3. Update `backend/app/models.py` Pydantic models
4. Update `frontend/lib/types.ts` TypeScript types
5. Run the updated SQL in Supabase SQL editor (no migration tool in V0)
