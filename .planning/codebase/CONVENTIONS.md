# Coding Conventions

**Analysis Date:** 2025-02-19

## Naming Patterns

**Files:**
- Backend: `snake_case.py` — e.g. `backend/app/llm.py`, `backend/app/search.py`, `backend/app/config.py`
- Frontend: `PascalCase.tsx` for components — e.g. `Sidebar.tsx`, `Workspace.tsx`, `ResearchBlock.tsx`
- Frontend: `camelCase.ts` for lib/utilities — e.g. `api.ts`, `types.ts`
- Test files: `test_<module>.py` — e.g. `test_api.py`, `test_llm.py`, `test_search.py`, `test_pipeline.py`, `test_prompts.py`

**Functions:**
- Backend: `snake_case` for all functions — e.g. `call_llm`, `call_llm_structured`, `_tavily_search`, `generate_error_code`
- Private helpers: prefix with `_` — e.g. `_strip_code_fences`, `_inject_system_prompt`, `_run_classify_pipeline`
- Frontend: `camelCase` — e.g. `startResearch`, `sendSelection`, `parseSSEStream`, `generateRequestId`

**Variables:**
- Backend: `snake_case` — e.g. `journey_id`, `intent_type`, `clarification_questions`
- Frontend: `camelCase` — e.g. `journeyId`, `intentType`, `quickResponse`, `selectedCompetitors`

**Types:**
- Backend: `PascalCase` for Pydantic models and classes — e.g. `ResearchRequest`, `ClassifyResult`, `CompetitorList`, `SearchResult`
- Backend: Custom exceptions: `PascalCase` + `Error` suffix — e.g. `SearchError`, `ScraperError`, `LLMError`, `LLMValidationError`
- Frontend: `PascalCase` for types/interfaces — e.g. `ResearchState`, `ResearchEvent`, `ClarificationAnswer`, `CompetitorInfo`

## Code Style

**Formatting:**
- Backend: Ruff (format + check). CI runs `ruff check .` and `ruff format --check .` — see `.github/workflows/test.yml`
- Frontend: ESLint via `eslint-config-next` (core-web-vitals + TypeScript) — config in `frontend/eslint.config.mjs`
- No Prettier config detected; Next.js/ESLint handle formatting

**Linting:**
- Backend: Ruff for Python. Pyright for type checking (`pyright app` in CI)
- Frontend: ESLint with Next.js presets. Run: `npm run lint` in `frontend/`

## Import Organization

**Backend order:**
1. Standard library (e.g. `json`, `asyncio`, `time`, `uuid`, `datetime`)
2. Third-party (e.g. `httpx`, `litellm`, `pydantic`, `fastapi`)
3. Local app modules (e.g. `from app.config import log, generate_error_code`)

**Example from `backend/app/search.py`:**
```python
import asyncio
import time
from dataclasses import dataclass

import httpx
from duckduckgo_search import DDGS

from app.config import settings, log, generate_error_code
```

**Frontend:**
- React/Next imports first, then `@/lib/*`, then `@/components/*`
- Use `@/` path alias for `frontend/` root

**Example from `frontend/app/explore/[journeyId]/page.tsx`:**
```typescript
import { useEffect, useReducer, useRef, useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { startResearch, sendSelection, sendRefine, type SSEConnection } from "@/lib/api";
import type { ResearchState, ResearchEvent, ... } from "@/lib/types";
import { Sidebar } from "@/components/Sidebar";
import { Workspace } from "@/components/Workspace";
```

## Error Handling

**Backend:**
- Use try/except with fallback chains. Never let exceptions propagate to SSE stream unhandled.
- Always send `block_error` or `error` SSE events on failure.
- Every user-facing error MUST include an `error_code` from `generate_error_code()` in `backend/app/config.py`.
- Error code format: `BP-` + 6 uppercase hex chars (e.g. `BP-3F8A2C`).
- Custom exceptions: `SearchError`, `ScraperError`, `LLMError`, `LLMValidationError` — defined in respective modules.
- Pattern: try primary → catch → try fallback → catch → generate error code, log, return/send error event.

**Example from `backend/app/search.py`:**
```python
try:
    results = await _tavily_search(query, num_results)
    return results
except SearchError as e:
    last_error = e
    log("WARN", "search provider failed, trying fallback", provider="tavily", error=str(e))
# ... fallback chain ...
code = generate_error_code()
log("ERROR", "search failed", provider="all", error=str(last_error), error_code=code)
return []
```

**Example from `backend/app/api/research.py`:**
```python
except (LLMError, LLMValidationError) as e:
    code = generate_error_code()
    log("ERROR", "sse error event sent", error_code=code, error=str(e), recoverable=False)
    evt = ErrorEvent(
        message="We're having trouble generating results right now. Please try again in a moment.",
        recoverable=False,
        error_code=code,
    )
    yield _serialize_event(evt)
```

**Frontend:**
- Never show raw error strings, stack traces, HTTP status codes, or provider names.
- Use friendly messages + `(Ref: BP-XXXXXX)` for all user-facing errors.
- REST fetch: use `X-Request-Id` header (UUID) as ref code. See `frontend/lib/api.ts`.
- SSE: use `error_code` from backend `ErrorEvent` or `BlockErrorEvent`.

## Logging

**Framework:** Custom `log()` in `backend/app/config.py` (structured print in V0; structlog in V1).

**Usage:**
- Import: `from app.config import log, generate_error_code`
- Never use bare `print()`.
- Format: `log(level, message, **context)` — levels: `"INFO"`, `"WARN"`, `"ERROR"`.
- Always include `journey_id` when available.

**Mandatory log points (per `AGENTS.md`):**
- Pipeline: `log("INFO", "pipeline started", ...)` and `log("INFO", "pipeline completed", ...)`
- LLM: before call, on success, on failure, on fallback, on validation failure
- Search: before, on success, on failure
- Scraper: before, on success, on fallback, on both fail
- DB: on write/read failure
- SSE: every event sent; error events with `error_code`

## Comments

**When to Comment:**
- Module docstrings at top of each file — e.g. `"""Blueprint Backend — Web Search"""`
- Docstrings for public functions with Args/Returns where relevant
- Section dividers: `# -----------------------------------------------------------------------------` for logical blocks

**JSDoc/TSDoc:**
- Used for exported API functions in `frontend/lib/api.ts` — e.g. `/** GET /api/journeys — list all journeys. */`

## Function Design

**Size:** Prefer focused functions. Pipeline logic in `backend/app/api/research.py` is split into `_run_*_pipeline` and `_run_*` helpers.

**Parameters:**
- Backend: `journey_id: str | None = None` for optional correlation — pass through for logging.
- Type hints on all function signatures.

**Return Values:**
- Async generators for SSE: `async def _run_classify_pipeline(...) -> AsyncGenerator[str, None]` — yield serialized events.
- Plain async functions return `list`, `dict`, `str`, or `None` as appropriate.

## Module Design

**Exports:**
- Backend: No barrel files. Import directly from `app.llm`, `app.search`, `app.db`, etc.
- Backend services: plain async functions only — no classes for services.

**Barrel Files:**
- Frontend: `@/lib/api` and `@/lib/types` export types and functions.

**Source of Truth:**
- `backend/app/models.py` — all Pydantic models (requests, responses, SSE events, internal types).
- `frontend/lib/types.ts` — mirrors `models.py`; update when models change.
- `backend/app/config.py` — all env vars; do not read `os.environ` elsewhere.
- `backend/app/prompts.py` — all LLM prompt templates; do not inline prompts.

---

*Convention analysis: 2025-02-19*
