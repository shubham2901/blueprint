# Blueprint — Module Specifications

Detailed file-by-file specifications for all backend and frontend modules. This document defines function signatures, class definitions, type shapes, and key logic for each file. Coding agents should implement files according to these specs.

Cross-references: [PLAN.md](PLAN.md) (product scope, DB schema), [ARCHITECTURE.md](ARCHITECTURE.md) (decisions, protocols, data flows), [DESIGN_GUIDE.md](DESIGN_GUIDE.md) (visual design), [AGENTS.md](AGENTS.md) (coding rules).

---

## Table of Contents

### Backend
1. [config.py](#1-backendappconfigpy)
2. [models.py](#2-backendappmodelspy)
3. [db.py](#3-backendappdbpy)
4. [llm.py](#4-backendappllmpy)
5. [search.py](#5-backendappsearchpy)
6. [scraper.py](#6-backendappscraperpy)
7. [prompts.py](#7-backendapppromptspy)
8. [api/research.py](#8-backendappapiresearchpy)
9. [api/journeys.py](#9-backendappapijourneyspy)
10. [main.py](#10-backendappmainpy)

### Frontend
11. [lib/types.ts](#11-frontendlibtypests)
12. [lib/api.ts](#12-frontendlibapits)
13. [Components](#13-frontend-components)
14. [Pages](#14-frontend-pages)

---

# Backend

---

## 1. `backend/app/config.py`

**Purpose**: Central configuration — environment variables and LLM settings.

**Dependencies**: `pydantic_settings`

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All environment variables. Loaded from .env or Railway env vars."""

    # LLM Providers
    gemini_api_key: str
    openai_api_key: str = ""          # Optional fallback
    anthropic_api_key: str = ""       # Optional fallback

    # Search
    serper_api_key: str              # Serper API for web + Reddit search

    # Scraping
    jina_api_key: str = ""            # Optional — Jina works without key at lower rate

    # Database
    supabase_url: str
    supabase_service_key: str

    # App
    environment: str = "development"  # "development" | "production"
    cors_origins: str = "http://localhost:3000"  # Comma-separated for multiple origins

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton — import this everywhere
settings = Settings()


# LLM Configuration (see ARCHITECTURE.md ADR-2 and ADR-3)
LLM_CONFIG = {
    "persona": {
        "name": "Blueprint",
        "system_prompt": (
            "You are Blueprint, a product research assistant. You help product managers "
            "and founders understand competitive landscapes. Be concise, structured, "
            "and always cite sources. Use bullet points for features and comparisons. "
            "Never fabricate data — if unsure, say so."
        ),
    },
    "temperature": 0.3,
    "max_tokens": 2000,
    "fallback_chain": [
        "gemini/gemini-2.0-flash",       # Primary — free tier
        "openai/gpt-4o-mini",            # Fallback 1 — cheap
        "anthropic/claude-3-haiku",      # Fallback 2 — cheap
    ],
}
```

**Notes**:
- `settings` is a module-level singleton. Import it directly: `from app.config import settings`.
- `LLM_CONFIG` is a plain dict, not a Pydantic model. It's read-only at runtime.
- `cors_origins` is a comma-separated string, split in `main.py` when configuring CORS middleware.

---

## 2. `backend/app/models.py`

**Purpose**: All Pydantic models — requests, responses, SSE events, and internal types. Single source of truth for all data shapes.

**Dependencies**: `pydantic`, `uuid`, `datetime`, `enum`

### Request Models

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class ResearchRequest(BaseModel):
    """Body for POST /api/research"""
    prompt: str = Field(..., min_length=1, max_length=500, description="User's research query")


class SelectionRequest(BaseModel):
    """Body for POST /api/research/{journey_id}/selection"""
    step_type: str = Field(..., description="'clarify' | 'select_competitors' | 'select_problems'")
    selection: dict = Field(..., description="Selection payload — shape depends on step_type")
    # For clarify:             { "answers": [{ "question_id": "platform", "selected_options": ["Mobile", "Web"] }, ...] }
    # For select_competitors:  { "competitor_ids": ["notion", "obsidian"] }
    # For select_problems:     { "problem_ids": ["gap-mobile-first", "gap-offline-sync"] }
```

### SSE Event Models

```python
class JourneyStartedEvent(BaseModel):
    type: str = "journey_started"
    journey_id: str
    intent_type: str    # "build" | "explore"


class QuickResponseEvent(BaseModel):
    """For small_talk / off_topic intents — no journey created."""
    type: str = "quick_response"
    message: str


class IntentRedirectEvent(BaseModel):
    """When improve intent is redirected to explore in V0."""
    type: str = "intent_redirect"
    original_intent: str
    redirected_to: str
    message: str


class StepStartedEvent(BaseModel):
    type: str = "step_started"
    step: str       # "classifying" | "clarifying" | "finding_competitors" | "exploring" | "gap_analyzing" | "defining_problem"
    label: str      # Human-readable label, e.g., "Understanding your query"


class StepCompletedEvent(BaseModel):
    type: str = "step_completed"
    step: str


class BlockReadyEvent(BaseModel):
    type: str = "block_ready"
    block: "ResearchBlock"


class BlockErrorEvent(BaseModel):
    type: str = "block_error"
    block_name: str
    error: str


class ClarificationNeededEvent(BaseModel):
    type: str = "clarification_needed"
    questions: list["ClarificationQuestion"]


class WaitingForSelectionEvent(BaseModel):
    type: str = "waiting_for_selection"
    selection_type: str  # "clarification" | "competitors" | "problems"


class ResearchCompleteEvent(BaseModel):
    type: str = "research_complete"
    journey_id: str
    summary: str         # e.g., "Research complete"


class ErrorEvent(BaseModel):
    type: str = "error"
    message: str
    recoverable: bool
```

### Block Models

```python
class ResearchBlock(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str              # "market_overview" | "competitor_list" | "product_profile" | "gap_analysis" | "problem_statement"
    title: str
    content: str           # Markdown-formatted content
    sources: list[str] = []
    cached: bool = False
    cached_at: Optional[datetime] = None


class ClarificationQuestion(BaseModel):
    id: str
    label: str             # e.g., "What platform are you targeting?"
    options: list["ClarificationOption"]
    allow_multiple: bool = False   # true = multi-select chips, false = single-select radio


class ClarificationOption(BaseModel):
    label: str
    description: str = ""              # Brief description shown as sublabel under chip
```

### LLM Response Models (for structured output validation)

```python
class ClassifyResult(BaseModel):
    """
    Validated output from the classify prompt.

    Note: The LLM returns question field as "text" — the backend maps it to "label"
    after parsing. Options come as [{label, description}] from the LLM directly.
    """
    intent_type: str           # "build" | "explore" | "improve" | "small_talk" | "off_topic"
    domain: Optional[str] = None       # e.g., "note-taking" (present for build/explore/improve)
    quick_response: Optional[str] = None  # Present for small_talk/off_topic — the reply text
    clarification_questions: Optional[list["ClarificationQuestion"]] = None  # Present for build/explore


class CompetitorList(BaseModel):
    """Validated output from the competitors prompt."""
    competitors: list["CompetitorInfo"]
    sources: list[str] = []


class CompetitorInfo(BaseModel):
    id: str                    # Slug: lowercase, hyphenated (e.g., "notion", "google-docs")
    name: str
    description: str
    url: Optional[str] = None
    category: Optional[str] = None
    pricing_model: Optional[str] = None


class ProductProfile(BaseModel):
    """Validated output from the explore prompt."""
    name: str
    content: str               # Full markdown analysis
    features_summary: list[str] = []
    pricing_tiers: Optional[str] = None
    target_audience: Optional[str] = None
    strengths: list[str] = []
    weaknesses: list[str] = []
    reddit_sentiment: Optional[str] = None  # Summary of Reddit user sentiment
    sources: list[str] = []


class MarketOverview(BaseModel):
    """Validated output from the market overview prompt."""
    title: str
    content: str               # Full markdown overview
    sources: list[str] = []


class GapAnalysis(BaseModel):
    """Validated output from the gap analysis prompt (build intent only)."""
    title: str                 # e.g., "Market Gaps & Opportunities"
    problems: list["ProblemArea"]
    sources: list[str] = []


class ProblemArea(BaseModel):
    """A single market gap / problem area identified by gap analysis."""
    id: str                    # Slug, e.g., "gap-mobile-first"
    title: str
    description: str
    evidence: list[str] = []   # Supporting evidence from research
    opportunity_size: Optional[str] = None  # "high" | "medium" | "low"


class ProblemStatement(BaseModel):
    """Validated output from the problem statement prompt (build intent only)."""
    title: str                 # e.g., "Your Problem Statement"
    content: str               # The problem statement text
    target_user: Optional[str] = None
    key_differentiators: list[str] = []
    validation_questions: list[str] = []
```

### Journey Response Models (for API responses)

```python
class JourneySummary(BaseModel):
    """Single journey in the list response."""
    id: str
    title: Optional[str] = None
    status: str
    intent_type: str           # "build" | "explore"
    initial_prompt: str
    created_at: datetime
    updated_at: datetime
    step_count: int


class JourneyDetail(BaseModel):
    """Full journey with all steps."""
    id: str
    title: Optional[str] = None
    status: str
    intent_type: str           # "build" | "explore"
    initial_prompt: str
    steps: list["JourneyStepDetail"]
    created_at: datetime
    updated_at: datetime


class JourneyStepDetail(BaseModel):
    """Single step within a journey."""
    id: str
    step_number: int
    step_type: str
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    user_selection: Optional[dict] = None
    created_at: datetime


class JourneyListResponse(BaseModel):
    journeys: list[JourneySummary]


class JourneyDetailResponse(BaseModel):
    journey: JourneyDetail
```

**Notes**:
- All models use `str` for UUIDs (not `uuid.UUID`) to simplify JSON serialization.
- Forward references (e.g., `"ResearchBlock"`) require `model_rebuild()` or `from __future__ import annotations`.
- The LLM response models (`ClassifyResult`, `CompetitorList`, `ProductProfile`, `GapAnalysis`, `ProblemStatement`) are used by `llm.py` for structured output validation. They match the JSON schemas embedded in the prompts.

---

## 3. `backend/app/db.py`

**Purpose**: All database operations — Supabase client, product cache CRUD, journey CRUD, LLM state management.

**Dependencies**: `supabase` (Python client), `app.config.settings`, `app.models`, `datetime`

### Supabase Client

```python
from supabase import create_client, Client
from app.config import settings

# Module-level singleton
_supabase: Client | None = None


def get_supabase() -> Client:
    """Return the Supabase client singleton. Creates it on first call."""
    global _supabase
    if _supabase is None:
        _supabase = create_client(settings.supabase_url, settings.supabase_service_key)
    return _supabase
```

### Product Cache Functions

```python
from app.models import ProductProfile
from typing import Optional
from datetime import datetime, timedelta, timezone


async def get_cached_product(normalized_name: str) -> Optional[dict]:
    """
    Check the products table for a cached entry.

    Args:
        normalized_name: Lowercase, trimmed product name (cache key).

    Returns:
        Product row as dict if found AND last_scraped_at is within 7 days.
        None if not found or expired.
    """
    # Query: SELECT * FROM products WHERE normalized_name = ? AND last_scraped_at > (now - 7 days)
    # Return the row dict or None


async def store_product(product_data: dict) -> str:
    """
    Upsert a product into the cache.

    Args:
        product_data: Dict with keys matching the products table columns:
            name, normalized_name, url, description, category, pricing_model,
            features_summary (JSONB), strengths (JSONB), weaknesses (JSONB),
            sources (JSONB), last_scraped_at.

    Returns:
        The product id (UUID string).

    Behavior:
        - If normalized_name exists: UPDATE all fields + set last_scraped_at = now()
        - If not: INSERT new row
    """


async def store_competitor_relationship(product_id: str, competitor_id: str, relationship_type: str = "direct") -> None:
    """
    Store a competitor relationship. Upsert on (product_id, competitor_id).
    """


def normalize_product_name(name: str) -> str:
    """
    Normalize a product name for cache key lookup.

    Rules:
        - Lowercase
        - Strip leading/trailing whitespace
        - Collapse multiple spaces to one

    Examples:
        "Notion" → "notion"
        "  Google Docs  " → "google docs"
    """
    return " ".join(name.lower().strip().split())
```

### Alternatives Cache Functions

```python
from typing import Optional


async def get_cached_alternatives(normalized_name: str) -> Optional[list[dict]]:
    """
    Check the alternatives_cache table for a cached entry.

    Args:
        normalized_name: Lowercase, trimmed product name (lookup key).

    Returns:
        List of alternative dicts if found AND scraped_at is within 30 days.
        None if not found or expired.

    Query:
        SELECT alternatives FROM alternatives_cache
        WHERE normalized_name = ? AND scraped_at > (now - 30 days)
    """


async def store_alternatives(
    product_name: str,
    alternatives: list[dict],
    source_url: str = "",
) -> str:
    """
    Upsert alternatives into the alternatives_cache table.

    Args:
        product_name: Original product name (e.g., "Notion")
        alternatives: List of alternative dicts from scraping
            [{"name": "Obsidian", "description": "...", "platforms": [...]}]
        source_url: The alternativeto.net URL that was scraped

    Returns:
        The row id (UUID string).

    Behavior:
        - normalized_name = normalize_product_name(product_name)
        - If normalized_name exists: UPDATE alternatives, source_url, scraped_at = now()
        - If not: INSERT new row
    """
```

### Journey Functions

```python
async def create_journey(prompt: str, intent_type: str = "explore") -> str:
    """
    Create a new journey row.

    Args:
        prompt: The user's initial research prompt.
        intent_type: "build" or "explore" (improve redirects to explore before this is called).

    Returns:
        The journey id (UUID string).

    Sets:
        title = first 100 chars of prompt
        status = "active"
        intent_type = intent_type
        initial_prompt = prompt
    """


async def get_journey(journey_id: str) -> Optional[dict]:
    """
    Get a journey with all its steps.

    Returns:
        Dict with journey fields + "steps" list ordered by step_number.
        None if journey not found.
    """


async def list_journeys() -> list[dict]:
    """
    List all journeys, ordered by updated_at desc.

    Returns:
        List of journey summary dicts (id, title, status, initial_prompt,
        created_at, updated_at, step_count).
        step_count is computed via a subquery or separate query.
    """


async def update_journey_status(journey_id: str, status: str) -> None:
    """Update journey status. Also sets updated_at = now()."""


async def save_journey_step(
    journey_id: str,
    step_number: int,
    step_type: str,
    input_data: Optional[dict] = None,
    output_data: Optional[dict] = None,
    user_selection: Optional[dict] = None,
) -> str:
    """
    Insert a new step into journey_steps.

    Returns:
        The step id (UUID string).
    """


async def get_last_step(journey_id: str) -> Optional[dict]:
    """
    Get the most recent step for a journey (highest step_number).

    Used by the selection endpoint to determine where the pipeline left off.
    """


async def get_next_step_number(journey_id: str) -> int:
    """
    Get the next step_number for a journey.

    Returns:
        max(step_number) + 1, or 1 if no steps exist.
    """
```

### LLM State Functions

```python
async def get_llm_state() -> str:
    """
    Get the currently active LLM provider from the llm_state table.

    Returns:
        Provider string, e.g., "gemini/gemini-2.0-flash".
        If no row exists, returns the first provider in LLM_CONFIG fallback_chain.
    """


async def update_llm_state(provider: str, reason: str) -> None:
    """
    Update the active LLM provider (upsert on id=1).

    Sets: active_provider, switched_at = now(), switch_reason, updated_at = now().
    """
```

### User Choice Logging

```python
async def log_user_choice(
    journey_id: str,
    step_id: str,
    options_presented: dict,
    options_selected: dict,
) -> None:
    """
    Insert into user_choices_log. Fire-and-forget — errors are logged but do not
    propagate. This data is for future ML/improvement, not critical path.
    """
```

**Notes**:
- All functions are `async` even though the Supabase Python client is synchronous. This keeps the interface consistent and allows migration to an async client later. Use `asyncio.to_thread()` to wrap synchronous Supabase calls if blocking is an issue.
- The Supabase client uses the **service role key** (full access, bypasses RLS). This is safe because only the backend calls Supabase.
- All functions return plain dicts (not Pydantic models) for flexibility. Callers convert to models as needed.

---

## 4. `backend/app/llm.py`

**Purpose**: All LLM interactions — calling providers via litellm, fallback chain, output validation, provider state caching.

**Dependencies**: `litellm`, `json`, `pydantic`, `app.config`, `app.db`, `app.models`

### Module-Level State

```python
import litellm
import json
from pydantic import BaseModel, ValidationError
from app.config import LLM_CONFIG, settings
from app.models import ClassifyResult, CompetitorList, ProductProfile, MarketOverview, GapAnalysis, ProblemStatement

# Cached active provider — loaded from DB on first call, updated on fallback
_active_provider: str | None = None
_initialized: bool = False
```

### Core Functions

```python
async def call_llm(messages: list[dict]) -> str:
    """
    Call the active LLM provider with the given messages.

    Steps:
        1. Ensure provider state is initialized (load from DB on first call)
        2. Prepend the persona system prompt from LLM_CONFIG
        3. Call litellm.acompletion() with the active provider
        4. On success: return the response content string
        5. On failure (429/quota/5xx/timeout): trigger fallback

    Args:
        messages: List of message dicts [{"role": "user", "content": "..."}].
                  Do NOT include the system prompt — it's injected here.

    Returns:
        Raw response content string from the LLM.

    Raises:
        LLMError: If all providers in the fallback chain fail.
    """


async def call_llm_structured(messages: list[dict], response_model: type[BaseModel]) -> BaseModel:
    """
    Call LLM and validate the response against a Pydantic model.

    Steps:
        1. Call call_llm(messages) to get raw response
        2. Strip markdown code fences if present (```json ... ```)
        3. json.loads() the response
        4. Validate with response_model(**parsed_json)
        5. On JSONDecodeError or ValidationError:
           a. Build a "fix JSON" prompt with the broken output + expected schema
           b. Retry call_llm() once with the fix prompt
           c. Parse and validate the retry response
           d. If retry also fails: raise LLMValidationError
        6. Return the validated Pydantic model instance

    Args:
        messages: Chat messages (without system prompt).
        response_model: The Pydantic model class to validate against.

    Returns:
        An instance of response_model.

    Raises:
        LLMValidationError: If validation fails after retry.
    """


async def _ensure_initialized() -> None:
    """
    Load the active provider from the DB on first call.
    Sets _active_provider and _initialized.
    Called automatically by call_llm().
    """
    global _active_provider, _initialized
    if not _initialized:
        _active_provider = await db.get_llm_state()
        _initialized = True


async def _handle_fallback(error: Exception, messages: list[dict]) -> str:
    """
    Walk the fallback chain when the active provider fails.

    Steps:
        1. Find current provider's index in fallback_chain
        2. Try each subsequent provider
        3. On first success: persist the switch (update DB + in-memory cache)
        4. If all fail: raise LLMError

    Side effects:
        - Updates _active_provider module variable
        - Calls db.update_llm_state() to persist the switch
    """
```

### Helper Functions

```python
def _inject_system_prompt(messages: list[dict]) -> list[dict]:
    """
    Prepend the persona system prompt to the message list.
    Returns a new list (does not mutate the input).
    """
    system_msg = {"role": "system", "content": LLM_CONFIG["persona"]["system_prompt"]}
    return [system_msg] + messages


def _strip_code_fences(text: str) -> str:
    """
    Remove markdown code fences from LLM output.
    Handles: ```json\n...\n```, ```\n...\n```, and plain text.
    """


def _get_provider_index(provider: str) -> int:
    """Get the index of a provider in the fallback chain. Returns 0 if not found."""
```

### Custom Exceptions

```python
class LLMError(Exception):
    """All providers in the fallback chain failed."""
    pass


class LLMValidationError(Exception):
    """LLM output failed Pydantic validation even after retry."""
    def __init__(self, raw_output: str, expected_schema: str, error: str):
        self.raw_output = raw_output
        self.expected_schema = expected_schema
        super().__init__(f"LLM validation failed: {error}")
```

**Notes**:
- `_active_provider` is module-level state (single-instance assumption). See ARCHITECTURE.md Section 7.
- The persona system prompt is injected in `_inject_system_prompt`, NOT in `prompts.py`. This keeps persona management centralized.
- litellm handles API key routing automatically based on the provider prefix (e.g., `gemini/...` uses `GEMINI_API_KEY`).

---

## 5. `backend/app/search.py`

**Purpose**: Web search — Serper API (primary) with DuckDuckGo as last-resort emergency fallback.

**Dependencies**: `httpx`, `app.config.settings`

```python
import httpx
from dataclasses import dataclass
from app.config import settings


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


async def search(query: str, num_results: int = 10) -> list[SearchResult]:
    """
    Search the web for the given query.

    Steps:
        1. Try Serper API
        2. On failure (network error, invalid API key): try DuckDuckGo (last-resort)
        3. If both fail: return empty list (caller handles gracefully)

    Args:
        query: Search query string, e.g., "personal note-taking app competitors 2026"
        num_results: Max results to return (default 10).

    Returns:
        List of SearchResult. May be empty if all providers fail.
    """


async def _serper_search(query: str, num_results: int = 10) -> list[SearchResult]:
    """
    Call Serper API for web search.

    Endpoint: POST https://google.serper.dev/search
    Headers: X-API-KEY: {serper_api_key}, Content-Type: application/json
    Body: { "q": query, "num": num_results }
    Rate limit: 2,500 queries/month (free tier); paid plans scale

    Returns:
        List of SearchResult parsed from response["organic"].
        Each organic result has: title, link, snippet.

    Raises:
        SearchError on non-200 response or network error.
    """


async def _duckduckgo_search(query: str, num_results: int = 10) -> list[SearchResult]:
    """
    Last-resort emergency fallback search via DuckDuckGo.

    Only used when Serper is completely down (network error, API key invalid).
    Uses the `duckduckgo_search` Python package (DDGS).
    No API key needed, no hard rate limit.

    Returns:
        List of SearchResult.

    Raises:
        SearchError on failure.
    """


async def search_reddit(query: str, num_results: int = 5) -> list[SearchResult]:
    """
    Search Reddit for the given query using Serper site-search.

    Wraps the standard search() function with a site:reddit.com prefix.

    Args:
        query: Search query string, e.g., "Notion note taking review"
        num_results: Max Reddit results to return (default 5).

    Returns:
        List of SearchResult from Reddit threads. May be empty.

    Usage:
        Called during the explore phase for each product to gather user sentiment.
        Also called during competitor finding to enrich competitor discovery with Reddit discussions.
    """
    return await search(f"site:reddit.com {query}", num_results=num_results)


class SearchError(Exception):
    """A search provider failed."""
    pass
```

**Notes**:
- Serper API provides structured JSON results (organic, knowledgeGraph, relatedSearches). We use `organic[]` for search results.
- DuckDuckGo is a last-resort emergency fallback — only used when Serper is completely unavailable (network error, invalid key). Not a co-primary provider.
- Search results are raw — the LLM processes them into structured competitor data in `prompts.py` + `llm.py`.
- `httpx.AsyncClient` is used for Serper API calls. Timeout: 10 seconds.
- `search_reddit()` is a thin wrapper — it reuses the same Serper/DuckDuckGo fallback chain with a `site:reddit.com` prefix. This keeps Reddit search cost-shared with regular search.

---

## 5a. `backend/app/alternatives.py`

**Purpose**: AlternativeTo scraper + CLI seeder — pre-scrapes `alternativeto.net` and `get.alternative.to` into the `alternatives_cache` DB table. Pipeline checks this table first for instant, free competitor discovery.

**Dependencies**: `httpx`, `bs4` (BeautifulSoup4), `app.scraper`, `app.db`, `app.config`

```python
import httpx
from bs4 import BeautifulSoup
from typing import Optional


async def scrape_alternatives(product_name: str) -> list[dict]:
    """
    Scrape alternativeto.net for a single product's alternatives.

    Steps:
        1. Build URL: https://alternativeto.net/software/{slug}/
           where slug = product_name.lower().replace(" ", "-")
        2. Fetch page via scraper.scrape() (uses Jina/BS4 chain)
        3. Parse the HTML for structured data:
            - Each alternative: name, description, platforms, license info
        4. Return list of alternative dicts

    Args:
        product_name: The product to find alternatives for (e.g., "Notion")

    Returns:
        List of dicts: [{"name": "Obsidian", "description": "...", "platforms": ["Windows", "Mac", "Linux"]}]
        Empty list if product not found or scraping fails.

    Error handling:
        Returns empty list on any failure (404, scraping error, parse error).
        Logs warning but does not raise.
    """


async def scrape_alternative_to(product_name: str) -> list[dict]:
    """
    Scrape get.alternative.to for a single product's alternatives.

    Steps:
        1. Build URL: https://get.alternative.to/{slug}/alternatives
        2. Fetch and parse the page
        3. Extract alternative names, descriptions, platforms

    Args:
        product_name: The product to find alternatives for

    Returns:
        List of alternative dicts. Empty list on failure.
    """


async def seed_popular_categories() -> dict:
    """
    Bulk scraper for CLI seeding — crawls top products in key categories.

    Called by: python -m app.seed_alternatives

    Steps:
        1. Define seed categories: ["note-taking", "project-management", "crm",
           "design-tools", "video-conferencing", "email-marketing", "analytics",
           "e-commerce", "social-media-management", "customer-support"]
        2. For each category:
            a. Fetch alternativeto.net/browse/all/?q={category} or category page
            b. Extract top 20-30 product names
            c. For each product: call scrape_alternatives()
            d. Store results via db.store_alternatives()
        3. Log progress: "Seeded {n} products in {category}"

    Returns:
        Summary dict: {"total_products": int, "total_alternatives": int, "categories_completed": int}

    Rate limiting:
        Add 1-2 second delays between requests to avoid being blocked.
    """


def _build_slug(product_name: str) -> str:
    """
    Build a URL slug from a product name.

    Rules:
        - Lowercase
        - Replace spaces with hyphens
        - Remove non-alphanumeric characters (except hyphens)

    Examples:
        "Notion" → "notion"
        "Google Docs" → "google-docs"
        "VS Code" → "vs-code"
    """
```

**Notes**:
- `scrape_alternatives()` is called live during the competitor pipeline if the product is not in `alternatives_cache`.
- `seed_popular_categories()` is a one-time/periodic CLI command — not called during normal request flow.
- Both AlternativeTo sites have different HTML structures. The parsing logic must handle both.
- Results are stored in `alternatives_cache` with a 30-day TTL. The pipeline calls `db.get_cached_alternatives()` first.
- Requests to AlternativeTo should include a reasonable User-Agent header.

---

## 5b. `backend/app/app_stores.py`

**Purpose**: Google Play + Apple App Store scrapers for competitor discovery. Uses Python libraries that scrape directly (no API keys needed). Marked V0-EXPERIMENTAL — if flaky, wrapped in try/except and pipeline continues without app store data.

**Dependencies**: `google_play_scraper`, `app_store_scraper`

```python
# V0-EXPERIMENTAL — If these libraries are flaky, rate-limited, or slow (>5s per query),
# wrap all functions in try/except and return empty lists. Pipeline continues without app store data.
# If problematic, defer full implementation to V1.

from typing import Optional


async def search_play_store(query: str, num_results: int = 10) -> list[dict]:
    """
    Search Google Play Store for apps matching the query.

    Uses: google-play-scraper Python library (no API key needed)

    Steps:
        1. Call google_play_scraper.search(query, n_hits=num_results)
        2. Extract: app_id, title, developer, score, description, genre
        3. Return normalized list of dicts

    Args:
        query: Search query (e.g., "note taking app")
        num_results: Max results to return (default 10)

    Returns:
        List of dicts: [{"name": "...", "app_id": "...", "developer": "...",
                         "rating": float, "description": "...", "category": "...",
                         "store": "play_store"}]
        Empty list on any failure.

    Error handling:
        Wrapped in try/except. Returns empty list on failure. Logs warning.
    """


async def search_app_store(query: str, num_results: int = 10) -> list[dict]:
    """
    Search Apple App Store for apps matching the query.

    Uses: app-store-scraper Python library (no API key needed)

    Steps:
        1. Call app_store_scraper search for the query
        2. Extract: app_id, title, developer, score, description, genre
        3. Return normalized list of dicts

    Args:
        query: Search query (e.g., "note taking app")
        num_results: Max results to return (default 10)

    Returns:
        List of dicts: [{"name": "...", "app_id": "...", "developer": "...",
                         "rating": float, "description": "...", "category": "...",
                         "store": "app_store"}]
        Empty list on any failure.

    Error handling:
        Wrapped in try/except. Returns empty list on failure. Logs warning.
    """


async def get_similar_apps(app_id: str, store: str = "play_store") -> list[dict]:
    """
    Get "Similar apps" / "You might also like" for a known app.
    These ARE competitor lists — app stores curate them as alternatives.

    Args:
        app_id: The app identifier (e.g., "com.notion.android" for Play Store)
        store: "play_store" or "app_store"

    Returns:
        List of similar app dicts (same structure as search results).
        Empty list on failure.

    Error handling:
        Wrapped in try/except. Returns empty list on failure. Logs warning.
    """
```

**Notes**:
- Both libraries are synchronous — wrap calls in `asyncio.to_thread()` if they block the event loop.
- V0 decision: if either library takes >5s per query, is unreliable, or gets rate-limited, mark the entire module as deferred and return empty lists from all functions. The competitor pipeline handles empty app store results gracefully.
- The `similar_apps` endpoint is the most valuable data source — it provides curated alternatives directly from the stores.
- `google-play-scraper` and `app-store-scraper` are community-maintained and may break if stores change their HTML. This is why they're V0-EXPERIMENTAL.

---

## 6. `backend/app/scraper.py`

**Purpose**: Web scraping — Jina Reader API with BeautifulSoup fallback, gated by a concurrency semaphore.

**Dependencies**: `httpx`, `bs4` (BeautifulSoup4), `asyncio`, `app.config.settings`

```python
import asyncio
import httpx
from bs4 import BeautifulSoup
from app.config import settings

# Concurrency limiter — max 2 concurrent Jina calls to respect 20 RPM free tier
_scrape_semaphore = asyncio.Semaphore(2)


async def scrape(url: str) -> str:
    """
    Scrape a URL and return its text content.

    Steps:
        1. Acquire semaphore slot (blocks if 2 scrapes already in progress)
        2. Try Jina Reader API
        3. On failure: try httpx + BeautifulSoup
        4. If both fail: raise ScraperError

    Args:
        url: The URL to scrape (e.g., "https://notion.so").

    Returns:
        Extracted text content (markdown from Jina, or cleaned text from BS4).
        Content is truncated to ~15,000 characters to fit LLM context windows.

    Raises:
        ScraperError: If both Jina and BS4 fail.
    """
    async with _scrape_semaphore:
        try:
            return await _jina_scrape(url)
        except ScraperError:
            return await _bs4_scrape(url)


async def _jina_scrape(url: str) -> str:
    """
    Scrape via Jina Reader API.

    Endpoint: GET https://r.jina.ai/{url}
    Headers: Authorization: Bearer {jina_api_key} (optional), Accept: text/markdown
    Rate limit: 20 RPM (free tier)
    Timeout: 30 seconds

    Returns:
        Markdown-formatted content from Jina.

    Raises:
        ScraperError on non-200 response, timeout, or network error.
    """


async def _bs4_scrape(url: str) -> str:
    """
    Fallback scraper using httpx + BeautifulSoup.

    Steps:
        1. GET the URL with httpx (timeout: 15 seconds, follow redirects)
        2. Parse HTML with BeautifulSoup
        3. Remove script, style, nav, footer, header tags
        4. Extract text with get_text(separator='\\n')
        5. Clean up whitespace
        6. Truncate to ~15,000 characters

    Returns:
        Cleaned text content.

    Raises:
        ScraperError on non-200 response, timeout, or parsing failure.
    """


def _truncate_content(content: str, max_chars: int = 15000) -> str:
    """Truncate content to max_chars, cutting at the last complete sentence."""


class ScraperError(Exception):
    """A scraper provider failed."""
    pass
```

**Notes**:
- The semaphore is module-level (single-instance assumption). With 2 slots and 20 RPM, each scrape can take up to ~6 seconds before hitting the rate limit.
- Content is truncated to ~15,000 chars because LLM context windows have limits and longer content degrades quality.
- BS4 output is lower quality than Jina (no markdown formatting, may include navigation text) but functional.

---

## 7. `backend/app/prompts.py`

**Purpose**: All LLM prompt templates. Each function returns a list of message dicts ready for `llm.call_llm()` or `llm.call_llm_structured()`.

**Dependencies**: `json`, `app.models` (for schema references)

**Design rule**: The persona system prompt is NOT included here — it's injected by `llm.py`. These functions only build the user messages with task-specific instructions.

**Important**: The actual prompt text is authored by the founder (see [FOUNDER_TASKS.md](FOUNDER_TASKS.md)). The coding agent implements the function signatures, schema embedding, and wiring. Placeholder prompt text should be clearly marked as `# TODO: Replace with founder-authored prompt`.

```python
from app.models import ClassifyResult, CompetitorList, ProductProfile, MarketOverview, GapAnalysis, ProblemStatement


def build_classify_prompt(user_input: str) -> list[dict]:
    """
    Build prompt to classify user intent AND generate clarification questions.

    This is a two-in-one prompt: the LLM determines the intent type AND generates
    appropriate clarification questions in a single call.

    Expected output schema: ClassifyResult
    Post-processing: backend maps LLM's "text" field → "label" on each question.

    Returns:
        [{"role": "user", "content": "..."}]
    """
    # ── ACTUAL PROMPT TEXT (founder-authored) ──────────────────────────
    #
    # Note: The persona system prompt is prepended by llm.py — not included here.
    # This prompt focuses purely on the classification and clarification task.
    #
    CLASSIFY_PROMPT = """
# Role
You are the "Gatekeeper" AI for a product research tool called Blueprint. Your goal is to analyze user input, classify their intent, extract the relevant domain, and generate necessary follow-up data.

# Input Processing
You will receive a raw string: `user_input`.

# Classification Rules
Analyze the input and assign one of the following `intent_type` labels.

**CRITICAL CONSTRAINT:** Your focus is strictly **Product Strategy & Market Research**.
- **ALLOWED:** Conceptualization, Feature Specs, Market Analysis, Technical Architecture/Stack Strategy.
- **FORBIDDEN:** Writing actual code, solving math homework, creative writing, or general chatbot conversation.

1. **build**: The user wants to conceptualize, design, or spec out a specific product or feature.
   - *Valid:* "I want to build a note-taking app", "What tech stack is best for a high-scale dating app?", "Design an onboarding flow."
   - *Invalid:* "Write the Python code for this", "Debug my React component", "How do I install Node.js?" → `off_topic`
2. **explore**: The user wants to learn about a market, competitor, or product category.
   - *Trigger:* Information-seeking phrasing or standalone entity names.
   - *Example:* "Tell me about EdTech in India", "Notion", "Tinder vs Bumble".
3. **improve**: The user has an existing product/project concept and wants to enhance it.
   - *Trigger:* Words like "fix", "optimize", "critique", "differentiate".
   - *Example:* "How do I make my CRM better than Salesforce?"
4. **small_talk**: Greetings, compliments, or conversational filler.
   - *Example:* "Hi there", "Good morning".
5. **off_topic**: Requests unrelated to product strategy.
   - *Example:* "What is the capital of France?", "Write a poem", "Python code for Fibonacci", "Solve this equation".

# Field Extraction Rules

## 1. Domain
Identify the business or research domain.
- If `small_talk` or `off_topic`: Set `domain` to null.
- If the input is specific (e.g., "Tinder"), map it to the broader category (e.g., "Entertainment & Media" or "Dating").
- **Reference Hierarchy & Examples:**
  - **Commerce & Retail:**
    - mCommerce (Nike, Zara)
    - Multi-Vendor Marketplaces (Amazon, Etsy)
    - Social Commerce (TikTok Shop, Pinterest)
    - Re-commerce/Second-hand (Depop, Vinted)
    - Direct-to-Consumer/DTC (Dollar Shave Club, Warby Parker)
  - **On-Demand & Gig Economy:**
    - Food Delivery (UberEats, DoorDash)
    - Ride-Hailing (Uber, Lyft)
    - Grocery Delivery (Instacart, Gopuff)
    - Home Services (TaskRabbit, Urban Company)
  - **FinTech:**
    - Neobanking (Chime, Revolut)
    - Peer-to-Peer Payments (Venmo, Cash App)
    - Investment & Trading (Robinhood, Coinbase)
    - Personal Finance (Mint, YNAB)
  - **Health & Wellness:**
    - Telehealth (Teladoc, Zocdoc)
    - Fitness & Training (Strava, Peloton)
    - Mental Health (Headspace, Calm)
    - FemTech (Flo, Clue)
  - **Education (EdTech):**
    - Language Learning (Duolingo, Babbel)
    - Skill Development (MasterClass, Udemy)
    - K-12 Support (Khan Academy, Photomath)
    - Test Prep (Magoosh, Kaplan)
  - **Travel & Hospitality:**
    - Booking Aggregators (Booking.com, Skyscanner)
    - Home Sharing (Airbnb, Vrbo)
    - Travel Planning (TripIt, Wanderlog)
    - Experience Booking (Viator, Eventbrite)
  - **Entertainment & Media:**
    - Video Streaming (Netflix, Disney+)
    - Audio Streaming (Spotify, Audible)
    - Dating (Tinder, Bumble)
    - Social Networking (Instagram, Discord)
  - **Real Estate (PropTech):**
    - Listing Platforms (Zillow, Rightmove)
    - Rental/Roommate Finders (SpareRoom, PadMapper)
  - **Lifestyle & Niche:**
    - Pet Services (Rover, Chewy)
    - Astrology (Co-Star, The Pattern)
    - Recipe & Cooking (Yummly, Tasty)

## 2. Clarification Questions
If (and ONLY if) intent is `build`, `explore`, or `improve`, generate 2-4 multiple-choice questions to refine the user's request.
- **Format:** Question text, 3-5 distinct options (each with a label and brief description), and a boolean `allow_multiple` flag.
- **Logic:** `allow_multiple: true` for features/platforms; `false` for primary goals.

## 3. Quick Response
- If `intent_type` is `build`, `explore`, or `improve`: Set to null.
- If `small_talk`: A polite, brief conversational reply (<15 words).
- If `off_topic`: A polite refusal (<20 words) explaining that you only help with product research and strategy (not code generation or general tasks).

# Output Schema
You must output strictly valid JSON. Do not include markdown formatting (like ```json).

{
  "intent_type": "string",
  "domain": "string or null",
  "clarification_questions": [
    {
      "id": "string",
      "text": "string",
      "options": [
        { "label": "string", "description": "string" }
      ],
      "allow_multiple": boolean
    }
  ],
  "quick_response": "string or null"
}
"""
    return [{"role": "user", "content": CLASSIFY_PROMPT + f"\n\nUser input: \"{user_input}\""}]


def build_competitors_prompt(
    domain: str,
    clarification_context: dict,
    alternatives_data: list[dict] | None = None,
    app_store_results: list[dict] | None = None,
    search_results: list[dict] | None = None,
    reddit_results: list[dict] | None = None,
) -> list[dict]:
    """
    Build prompt to extract a structured competitor list from multiple data sources.

    The LLM receives data from up to 4 sources and synthesizes them, plus its own knowledge.

    Input:
        domain: The research domain (e.g., "note-taking")
        clarification_context: Dict of user's clarification answers
            (e.g., {"platform": ["Mobile", "Web"], "content_type": ["Text notes"], "positioning": ["Power tool"]})
        alternatives_data: Cached alternatives from alternativeto.net (may be None if cache miss)
        app_store_results: Results from Play Store + App Store scrapers (may be None or empty)
        search_results: Serper web search results (title, url, snippet)
        reddit_results: Serper Reddit site-search results (title, url, snippet)

    Instructions to LLM:
        - "Here are competitor candidates from multiple sources: AlternativeTo database,
           app store results, web search, and Reddit discussions."
        - "Use these results AND your own knowledge of the space to identify 5-10 competitors."
        - "Prioritize competitors confirmed by multiple sources."
        - "You MAY include well-known competitors you are confident about even if not in any source."
        - For each: name, one-line description, URL, category, pricing model
        - Generate a slug ID (lowercase, hyphenated) for each
        - Include source URLs
        - Weight results toward products matching the clarification context

    Expected output schema: CompetitorList

    Returns:
        [{"role": "user", "content": "..."}]
    """


def build_explore_prompt(product_name: str, scraped_content: str, reddit_content: str = "") -> list[dict]:
    """
    Build prompt to analyze scraped product content + Reddit sentiment into a structured profile.

    Input:
        product_name: Name of the product being analyzed
        scraped_content: Text content from scraper.py (truncated to ~15k chars)
        reddit_content: Concatenated Reddit thread snippets for this product (from search_reddit)

    Instructions to LLM:
        - Generate a comprehensive markdown analysis
        - Include: summary, key features, pricing tiers, target audience, strengths, weaknesses
        - Include a reddit_sentiment field summarizing user sentiment from Reddit
        - Cite specific features and pricing from the scraped content
        - If information is missing from scraped content, say "Not available" (don't fabricate)

    Expected output schema: ProductProfile

    Returns:
        [{"role": "user", "content": "..."}]
    """


def build_market_overview_prompt(domain: str, competitors: list[dict]) -> list[dict]:
    """
    Build prompt to generate a market overview from collected competitor data.

    Input:
        domain: The research domain (e.g., "note-taking")
        competitors: List of competitor info dicts (name, description, category, pricing)

    Instructions to LLM:
        - Provide a high-level market landscape summary
        - Key trends, market size indicators (qualitative), competitive dynamics
        - Group competitors by sub-categories if applicable
        - Keep it concise (300-500 words)

    Expected output schema: MarketOverview

    Returns:
        [{"role": "user", "content": "..."}]
    """


def build_gap_analysis_prompt(profiles: list[dict], clarification_context: dict) -> list[dict]:
    """
    Build prompt to identify market gaps from competitor profiles (build intent only).

    Input:
        profiles: List of ProductProfile dicts (all analyzed competitors)
        clarification_context: The user's clarification answers (platform, audience, etc.)

    Instructions to LLM:
        - Analyze all competitor profiles for underserved/unserved needs
        - Identify 3-6 problem areas / market gaps
        - For each gap: title, description, supporting evidence from profiles, opportunity size
        - Generate a slug ID for each gap
        - Prioritize gaps relevant to the user's stated preferences
        - Ground all gaps in evidence from the competitor data (no fabrication)

    Expected output schema: GapAnalysis

    Returns:
        [{"role": "user", "content": "..."}]
    """


def build_problem_statement_prompt(selected_gaps: list[dict], context: dict) -> list[dict]:
    """
    Build prompt to generate an actionable problem statement (build intent only).

    Input:
        selected_gaps: List of ProblemArea dicts the user selected
        context: Dict with domain, competitors_analyzed, clarification_context

    Instructions to LLM:
        - Synthesize the selected gaps into a focused, actionable problem statement
        - Include: target user, key differentiators, validation questions
        - The statement should be specific enough to guide a product brief
        - Ground the statement in the research context

    Expected output schema: ProblemStatement

    Returns:
        [{"role": "user", "content": "..."}]
    """


def build_fix_json_prompt(broken_output: str, expected_schema: dict) -> list[dict]:
    """
    Build prompt to fix malformed LLM JSON output.

    Input:
        broken_output: The raw string that failed JSON parsing or validation
        expected_schema: The JSON schema dict (from Pydantic model.model_json_schema())

    Instructions to LLM:
        - The previous output had a JSON formatting error
        - Here is the broken output and the expected schema
        - Return ONLY valid JSON matching the schema, nothing else

    Returns:
        [{"role": "user", "content": "..."}]
    """
```

**Notes**:
- Each prompt function embeds the expected JSON schema inline (using `Model.model_json_schema()`) so the LLM knows exactly what shape to return.
- Prompts use concrete examples where possible to improve LLM output quality.
- The `build_fix_json_prompt` is called by `llm.call_llm_structured()` when the first attempt fails validation.
- `build_classify_prompt` is the most complex prompt — it must handle all 5 intent types and generate appropriate clarification questions. The founder writes the actual text; the coding agent wires the schema and function.

---

## 8. `backend/app/api/research.py`

**Purpose**: The core research endpoints — SSE streaming for research execution and user selection handling. Orchestrates the full pipeline.

**Dependencies**: `fastapi`, `asyncio`, `sse_starlette` (for SSE responses), `app.llm`, `app.search`, `app.scraper`, `app.prompts`, `app.db`, `app.models`

### Request Deduplication

```python
import asyncio
from hashlib import sha256

# In-memory active research tracker (single-instance assumption)
_active_researches: dict[str, bool] = {}


def _make_dedup_key(journey_id: str | None, prompt: str | None) -> str:
    """
    Generate a deduplication key.
    - If journey_id is provided: use journey_id
    - If not: use sha256 hash of the prompt
    """
    if journey_id:
        return f"journey:{journey_id}"
    return f"prompt:{sha256((prompt or '').encode()).hexdigest()[:16]}"
```

### Endpoints

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models import ResearchRequest, SelectionRequest

router = APIRouter(prefix="/api/research", tags=["research"])


@router.post("")
async def start_research(request: ResearchRequest) -> StreamingResponse:
    """
    POST /api/research

    Classify intent and start a new research session.

    Steps:
        1. Generate dedup key from prompt hash
        2. Check _active_researches — if key exists, return 409 Conflict
        3. Add key to _active_researches
        4. Call classify prompt → get intent_type
        5. If small_talk / off_topic:
            - Yield quick_response event
            - Stream closes. No journey created. Remove dedup key.
        6. If improve: set intent_type to "explore" (redirect)
        7. Create journey via db.create_journey(prompt, intent_type)
        8. Yield journey_started event (with intent_type)
        9. If improve: yield intent_redirect event
        10. Save classify step to DB
        11. Yield clarification_needed + waiting_for_selection("clarification")
        12. Stream closes. Remove dedup key.

    Request body: ResearchRequest { prompt: str }
    Response: SSE stream (Content-Type: text/event-stream)

    SSE events emitted:
        For small_talk/off_topic: quick_response only
        For build/explore/improve:
            - journey_started (with journey_id, intent_type)
            - intent_redirect (if improve)
            - step_started("classifying")
            - step_completed("classifying")
            - clarification_needed (multi-question)
            - waiting_for_selection("clarification")
    """


@router.post("/{journey_id}/selection")
async def submit_selection(journey_id: str, request: SelectionRequest) -> StreamingResponse:
    """
    POST /api/research/{journey_id}/selection

    Submit a user selection and continue the research pipeline.

    Steps:
        1. Validate journey exists via db.get_journey()
        2. Get last step via db.get_last_step()
        3. Generate dedup key from journey_id
        4. Check _active_researches — if key exists, return 409 Conflict
        5. Add key to _active_researches
        6. Save the user's selection to journey_steps
        7. Based on step_type, continue the pipeline:
           - "clarify": save answers, run competitor search → waiting_for_selection("competitors")
           - "select_competitors": run explore + gap analysis (if build) → waiting_for_selection("problems") or research_complete
           - "select_problems": run problem statement (build only) → research_complete
        8. On stream completion/error: remove key from _active_researches

    Path params: journey_id (UUID string)
    Request body: SelectionRequest { step_type, selection }
    Response: SSE stream (Content-Type: text/event-stream)

    Returns 404 if journey not found.
    Returns 409 if research already in progress for this journey.
    """
```

### Pipeline Functions

```python
async def _run_classify_pipeline(prompt: str):
    """
    Generator that yields SSE events for the classify + clarify phase.
    Called by start_research().

    Steps:
        1. Yield step_started("classifying")
        2. Call llm.call_llm_structured() with build_classify_prompt()
        3. Yield step_completed("classifying")
        4. If intent_type is small_talk / off_topic:
            a. Yield quick_response event
            b. Return (stream ends, no journey created)
        5. If intent_type is improve: set to explore, yield intent_redirect
        6. Create journey via db.create_journey(prompt, intent_type)
        7. Yield journey_started(journey_id, intent_type)
        8. Save classify step to DB
        9. Yield clarification_needed with generated questions
        10. Yield waiting_for_selection("clarification")
        11. Return (stream ends)

    Yields:
        SSE event dicts
    """


async def _run_competitor_pipeline(journey_id: str, clarification_context: dict, domain: str):
    """
    Generator that yields SSE events for the competitor finding phase.
    Called after user submits clarification answers.

    Uses the layered competitor source priority:
        1. Check alternatives_cache DB (instant, free)
        2. Fan out to live sources in parallel:
            a. App Store + Play Store search (V0-EXPERIMENTAL)
            b. Serper web search
            c. Serper Reddit site-search
        3. Merge all results and pass to LLM (synthesize + augment from own knowledge)

    Steps:
        1. Save clarify step to DB (with user's answers)
        2. Yield step_started("finding_competitors")
        3. Build search query from domain + clarification context
        4. Check db.get_cached_alternatives(normalized_name):
            - If found: add to alternatives_data
            - If not found: alternatives_data = None
        5. Fan out live search in parallel (asyncio.gather):
            a. app_stores.search_play_store(query) + app_stores.search_app_store(query)
            b. search.search(query) for Serper web results
            c. search.search_reddit(query) for Reddit results
        6. Call llm.call_llm_structured() with build_competitors_prompt(
               domain, clarification_context,
               alternatives_data, app_store_results, search_results, reddit_results
           )
        7. Build block_ready event with competitor_list block
        8. Save find_competitors step to DB (input_data includes all sources used)
        9. Yield block_ready(competitor_list)
        10. Yield step_completed("finding_competitors")
        11. Yield waiting_for_selection("competitors")

    Yields:
        SSE event dicts
    """


async def _run_explore_pipeline(journey_id: str, selected_competitors: list[dict], intent_type: str):
    """
    Generator that yields SSE events for the explore phase.
    Called after user selects competitors to explore.

    Steps:
        1. Save select_competitors step to DB
        2. Yield step_started("exploring")
        3. For each selected competitor (in parallel via asyncio.gather):
            a. Check product cache via db.get_cached_product()
            b. If cache miss:
                - scraper.scrape() product website
                - search.search_reddit(product_name + domain) for Reddit content
                - llm.call_llm_structured() with build_explore_prompt(product, scraped, reddit)
            c. Store to product cache via db.store_product()
            d. Yield block_ready(product_profile) for each completed product
            e. On scraper/LLM failure for one product: yield block_error, continue others
        4. Generate market overview (concurrent with product profiles):
            a. llm.call_llm_structured() with build_market_overview_prompt()
            b. Yield block_ready(market_overview)
        5. Yield step_completed("exploring")
        6. If intent_type == "build":
            a. Run _run_gap_analysis() inline
            b. Yield waiting_for_selection("problems")
            c. Return (stream ends, user selects problems)
        7. If intent_type == "explore":
            a. Save explore step to DB
            b. Update journey status to "completed"
            c. Yield research_complete event
            d. Return (stream ends)

    Concurrency:
        Products are explored in parallel using asyncio.gather(return_exceptions=True).
        Failed products emit block_error events but don't stop other products.

    Yields:
        SSE event dicts
    """


async def _run_gap_analysis(journey_id: str, profiles: list[dict], clarification_context: dict):
    """
    Yields SSE events for gap analysis (build intent only).
    Called inline by _run_explore_pipeline when intent is "build".

    Steps:
        1. Yield step_started("gap_analyzing")
        2. Call llm.call_llm_structured() with build_gap_analysis_prompt()
        3. Build block_ready event with gap_analysis block
        4. Save explore step to DB (includes gap_analysis in output_data)
        5. Yield block_ready(gap_analysis)
        6. Yield step_completed("gap_analyzing")

    Yields:
        SSE event dicts
    """


async def _run_problem_pipeline(journey_id: str, selected_problems: list[dict], context: dict):
    """
    Generator that yields SSE events for problem statement generation (build intent only).
    Called after user selects problem areas from gap analysis.

    Steps:
        1. Save select_problems step to DB
        2. Yield step_started("defining_problem")
        3. Call llm.call_llm_structured() with build_problem_statement_prompt()
        4. Build block_ready event with problem_statement block
        5. Save define_problem step to DB
        6. Yield block_ready(problem_statement)
        7. Yield step_completed("defining_problem")
        8. Update journey status to "completed"
        9. Yield research_complete event

    Yields:
        SSE event dicts
    """


def _format_sse_event(event: dict) -> str:
    """
    Format a dict as an SSE event string.

    Format: "data: {json}\n\n"
    """
    return f"data: {json.dumps(event)}\n\n"
```

**Notes**:
- SSE streaming uses `sse-starlette` or a manual `StreamingResponse` with `media_type="text/event-stream"`.
- Pipeline functions are async generators that `yield` SSE event strings.
- The dedup key is removed in a `finally` block to ensure cleanup even on errors.
- Each pipeline function handles its own errors internally — it never lets exceptions propagate past the generator. Errors become SSE events.

---

## 9. `backend/app/api/journeys.py`

**Purpose**: Journey CRUD endpoints — list and retrieve journeys.

**Dependencies**: `fastapi`, `app.db`, `app.models`

```python
from fastapi import APIRouter, HTTPException
from app.models import JourneyListResponse, JourneyDetailResponse
from app import db

router = APIRouter(prefix="/api/journeys", tags=["journeys"])


@router.get("")
async def list_journeys() -> JourneyListResponse:
    """
    GET /api/journeys

    List all journeys, ordered by updated_at desc.

    Returns:
        JourneyListResponse { journeys: [JourneySummary, ...] }

    Notes:
        - V0 returns ALL journeys (no user filtering — anonymous).
        - V1 will filter by user_id from auth context.
        - No pagination in V0 (acceptable for <100 journeys).
    """
    journeys = await db.list_journeys()
    return JourneyListResponse(journeys=journeys)


@router.get("/{journey_id}")
async def get_journey(journey_id: str) -> JourneyDetailResponse:
    """
    GET /api/journeys/{journey_id}

    Get a journey with all its steps, ordered by step_number.

    Returns:
        JourneyDetailResponse { journey: JourneyDetail }

    Raises:
        404 if journey not found.
    """
    journey = await db.get_journey(journey_id)
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    return JourneyDetailResponse(journey=journey)
```

**Notes**:
- These endpoints are simple CRUD — no business logic, no streaming.
- The dashboard page calls `GET /api/journeys` on load.
- The explore page calls `GET /api/journeys/{id}` when loading a saved journey.

---

## 10. `backend/app/main.py`

**Purpose**: FastAPI application factory — app creation, middleware, router registration.

**Dependencies**: `fastapi`, `fastapi.middleware.cors`, `slowapi`, `app.config`, `app.api.research`, `app.api.journeys`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.api import research, journeys

# Rate limiter — global, per-IP
limiter = Limiter(key_func=get_remote_address)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Steps:
        1. Create FastAPI instance with title, version, description
        2. Add CORS middleware (origins from settings.cors_origins)
        3. Add rate limiting (slowapi)
        4. Register routers (research, journeys)
        5. Add health check endpoint
        6. Return the app

    Returns:
        Configured FastAPI application instance.
    """


app = create_app()


@app.get("/api/health")
async def health_check():
    """
    GET /api/health

    Returns: { "status": "ok", "version": "0.1.0" }
    """
    return {"status": "ok", "version": "0.1.0"}
```

### CORS Configuration

```python
# In create_app():
origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Rate Limiting

```python
# Global rate limit: 20 requests/minute per IP
# Applied to research endpoints only (journey reads are lightweight)
@app.state.limiter  # or via decorator on individual endpoints
# Rate: "20/minute"
```

**Notes**:
- The app is created via `create_app()` factory pattern, but the `app` variable is module-level for uvicorn: `uvicorn app.main:app`.
- CORS origins: `http://localhost:3000` in development, Railway frontend domain in production.
- Rate limiting is applied only to `POST /api/research` and `POST /api/research/{id}/selection` — the expensive endpoints. GET endpoints are not rate limited.
- The `__init__.py` files in `app/` and `app/api/` can be empty.

---

# Frontend

---

## 11. `frontend/lib/types.ts`

**Purpose**: All TypeScript types — mirrors `backend/app/models.py`. Single source of truth for frontend type safety.

**Dependencies**: None (pure type definitions)

```typescript
// ──────────────────────────────────────────────────────
// SSE Event Types
// ──────────────────────────────────────────────────────

export type IntentType = "build" | "explore";
export type StepName = "classifying" | "clarifying" | "finding_competitors" | "exploring" | "gap_analyzing" | "defining_problem";
export type SelectionType = "clarification" | "competitors" | "problems";
export type BlockType = "market_overview" | "competitor_list" | "product_profile" | "gap_analysis" | "problem_statement";

export type ResearchEvent =
  | JourneyStartedEvent
  | QuickResponseEvent
  | IntentRedirectEvent
  | StepStartedEvent
  | StepCompletedEvent
  | BlockReadyEvent
  | BlockErrorEvent
  | ClarificationNeededEvent
  | WaitingForSelectionEvent
  | ResearchCompleteEvent
  | ErrorEvent;

export interface JourneyStartedEvent {
  type: "journey_started";
  journey_id: string;
  intent_type: IntentType;
}

export interface QuickResponseEvent {
  type: "quick_response";
  message: string;
}

export interface IntentRedirectEvent {
  type: "intent_redirect";
  original_intent: string;
  redirected_to: string;
  message: string;
}

export interface StepStartedEvent {
  type: "step_started";
  step: StepName;
  label: string;
}

export interface StepCompletedEvent {
  type: "step_completed";
  step: StepName;
}

export interface BlockReadyEvent {
  type: "block_ready";
  block: ResearchBlock;
}

export interface BlockErrorEvent {
  type: "block_error";
  block_name: string;
  error: string;
}

export interface ClarificationNeededEvent {
  type: "clarification_needed";
  questions: ClarificationQuestion[];
}

export interface WaitingForSelectionEvent {
  type: "waiting_for_selection";
  selection_type: SelectionType;
}

export interface ResearchCompleteEvent {
  type: "research_complete";
  journey_id: string;
  summary: string;
}

export interface ErrorEvent {
  type: "error";
  message: string;
  recoverable: boolean;
}

// ──────────────────────────────────────────────────────
// Block Types
// ──────────────────────────────────────────────────────

export interface ResearchBlock {
  id: string;
  type: BlockType;
  title: string;
  content: string;        // Markdown-formatted
  sources: string[];
  cached: boolean;
  cached_at?: string;     // ISO date string
}

export interface ClarificationQuestion {
  id: string;
  label: string;
  options: ClarificationOption[];
  allow_multiple: boolean;
}

export interface ClarificationOption {
  label: string;
  description: string;
}

// ──────────────────────────────────────────────────────
// Competitor Types (from competitor_list block)
// ──────────────────────────────────────────────────────

export interface CompetitorInfo {
  id: string;             // Slug: "notion", "google-docs"
  name: string;
  description: string;
  url?: string;
  category?: string;
  pricing_model?: string;
}

// ──────────────────────────────────────────────────────
// Journey Types (from journey endpoints)
// ──────────────────────────────────────────────────────

export interface JourneySummary {
  id: string;
  title: string | null;
  status: string;         // "active" | "completed" | "archived"
  intent_type: IntentType;
  initial_prompt: string;
  created_at: string;     // ISO date string
  updated_at: string;
  step_count: number;
}

export interface JourneyDetail {
  id: string;
  title: string | null;
  status: string;
  intent_type: IntentType;
  initial_prompt: string;
  steps: JourneyStep[];
  created_at: string;
  updated_at: string;
}

export interface JourneyStep {
  id: string;
  step_number: number;
  step_type: string;      // "classify" | "clarify" | "find_competitors" | "select_competitors" | "explore" | "select_problems" | "define_problem"
  input_data: Record<string, unknown> | null;
  output_data: Record<string, unknown> | null;
  user_selection: Record<string, unknown> | null;
  created_at: string;
}

// ──────────────────────────────────────────────────────
// API Response Types
// ──────────────────────────────────────────────────────

export interface JourneyListResponse {
  journeys: JourneySummary[];
}

export interface JourneyDetailResponse {
  journey: JourneyDetail;
}

// ──────────────────────────────────────────────────────
// Request Types
// ──────────────────────────────────────────────────────

export interface ResearchRequest {
  prompt: string;
}

export interface ClarificationAnswer {
  question_id: string;
  selected_options: string[];   // Label strings, e.g., ["Mobile", "Web"]
}

export interface ClarificationSelection {
  answers: ClarificationAnswer[];
}

export interface CompetitorSelection {
  competitor_ids: string[];
}

export interface ProblemSelection {
  problem_ids: string[];
}

export interface SelectionRequest {
  step_type: "clarify" | "select_competitors" | "select_problems";
  selection: ClarificationSelection | CompetitorSelection | ProblemSelection;
}

// ──────────────────────────────────────────────────────
// UI State Types (frontend-only, not from backend)
// ──────────────────────────────────────────────────────

export type ResearchPhase =
  | "idle"                     // No research in progress
  | "streaming"                // SSE stream is active
  | "waiting_for_clarification" // Multi-question clarification shown, waiting for user
  | "waiting_for_competitors"  // Competitor checkboxes shown, waiting for user
  | "waiting_for_problems"     // Problem checkboxes shown (build intent), waiting for user
  | "completed"                // Research done
  | "error";                   // Fatal error

export interface ResearchState {
  phase: ResearchPhase;
  journeyId: string | null;
  intentType: IntentType | null;
  blocks: ResearchBlock[];
  errors: BlockErrorEvent[];
  clarificationQuestions: ClarificationQuestion[] | null;
  competitorList: CompetitorInfo[] | null;
  selectedCompetitors: string[];   // IDs of checked competitors
  problemAreas: ProblemArea[] | null;  // From gap_analysis block (build intent)
  selectedProblems: string[];      // IDs of selected problems
  currentStep: StepName | null;
  completedSteps: StepName[];
  summary: string | null;
  quickResponse: string | null;    // For small_talk/off_topic (no journey)
}

// Problem area from gap analysis (extracted from gap_analysis block content)
export interface ProblemArea {
  id: string;
  title: string;
  description: string;
  evidence: string[];
  opportunity_size?: string;
}
```

**Notes**:
- `ResearchState` is the main state object for the explore page. It tracks everything the UI needs to render.
- All date fields are `string` (ISO format), not `Date` objects — avoids serialization issues with React state.
- `Record<string, unknown>` is used for JSONB fields that have step-type-dependent schemas.

---

## 12. `frontend/lib/api.ts`

**Purpose**: API client functions and SSE event handling. All backend communication goes through this file.

**Dependencies**: `lib/types.ts`

### Configuration

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

### REST API Functions

```typescript
import type {
  JourneyListResponse,
  JourneyDetailResponse,
  ResearchRequest,
  SelectionRequest,
} from "./types";


export async function getJourneys(): Promise<JourneyListResponse> {
  /**
   * GET /api/journeys
   *
   * Fetches all journeys for the dashboard.
   * Throws on non-200 response.
   */
  const res = await fetch(`${API_URL}/api/journeys`);
  if (!res.ok) throw new Error(`Failed to fetch journeys: ${res.status}`);
  return res.json();
}


export async function getJourney(journeyId: string): Promise<JourneyDetailResponse> {
  /**
   * GET /api/journeys/{journeyId}
   *
   * Fetches a single journey with all steps.
   * Used when loading a saved journey from the dashboard.
   * Throws on non-200 response.
   */
  const res = await fetch(`${API_URL}/api/journeys/${journeyId}`);
  if (!res.ok) throw new Error(`Failed to fetch journey: ${res.status}`);
  return res.json();
}
```

### SSE Streaming Functions

```typescript
import type { ResearchEvent } from "./types";

type EventCallback = (event: ResearchEvent) => void;
type ErrorCallback = (error: Error) => void;
type CompleteCallback = () => void;

export interface SSEConnection {
  close: () => void;  // Abort the stream
}


export function startResearch(
  prompt: string,
  onEvent: EventCallback,
  onError: ErrorCallback,
  onComplete: CompleteCallback,
): SSEConnection {
  /**
   * POST /api/research
   *
   * Starts a new research session and streams SSE events.
   *
   * Implementation:
   *   1. Use fetch() with POST method (not EventSource — EventSource only supports GET)
   *   2. Read the response body as a ReadableStream
   *   3. Use a TextDecoder to read chunks
   *   4. Parse SSE format: lines starting with "data: " contain JSON events
   *   5. For each parsed event, call onEvent(event)
   *   6. On stream end (reader.done), call onComplete()
   *   7. On error, call onError(error)
   *
   * Returns:
   *   SSEConnection with a close() method to abort the stream (calls AbortController.abort())
   *
   * Why not EventSource:
   *   EventSource only supports GET requests. Our research endpoint is POST
   *   (it has a request body). We use fetch + ReadableStream instead.
   */
}


export function sendSelection(
  journeyId: string,
  selection: SelectionRequest,
  onEvent: EventCallback,
  onError: ErrorCallback,
  onComplete: CompleteCallback,
): SSEConnection {
  /**
   * POST /api/research/{journeyId}/selection
   *
   * Sends user selection and streams the continuation.
   * Same SSE reading logic as startResearch().
   *
   * Implementation:
   *   1. POST to /api/research/{journeyId}/selection with SelectionRequest body
   *   2. Read SSE stream from response body
   *   3. Parse and dispatch events via callbacks
   */
}
```

### SSE Parsing Helper

```typescript
function parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: EventCallback,
  onError: ErrorCallback,
  onComplete: CompleteCallback,
): void {
  /**
   * Internal helper to parse an SSE stream from a ReadableStream.
   *
   * SSE format:
   *   data: {"type":"step_started","step":"identifying","label":"Understanding your query"}\n\n
   *
   * Steps:
   *   1. Read chunks from the reader
   *   2. Accumulate text in a buffer (chunks may split mid-event)
   *   3. Split on "\n\n" to get complete events
   *   4. For each event line starting with "data: ":
   *      a. Strip the "data: " prefix
   *      b. JSON.parse the payload
   *      c. Call onEvent(parsed)
   *   5. On reader.done: call onComplete()
   *   6. On error: call onError(error)
   */
}
```

**Notes**:
- We use `fetch()` + `ReadableStream` instead of `EventSource` because our SSE endpoints use POST (EventSource only supports GET).
- `AbortController` is used for cancellation — `close()` calls `controller.abort()`.
- The buffer in `parseSSEStream` handles partial chunks correctly (a single SSE event may be split across multiple network chunks).
- All callbacks are synchronous — the caller (typically a React hook) updates state synchronously in the callback.

---

## 13. Frontend Components

All components use the Cozy Sand design tokens from `tailwind.config.ts`. See [DESIGN_GUIDE.md](DESIGN_GUIDE.md) for visual specs.

---

### `components/PromptInput.tsx`

**Purpose**: Floating input card with text area and RUN button. Used on the landing page and in the sidebar.

```typescript
"use client";

interface PromptInputProps {
  onSubmit: (prompt: string) => void;
  disabled?: boolean;        // True while research is streaming
  placeholder?: string;      // Default: "What product or market do you want to explore?"
  compact?: boolean;         // True when used in sidebar (smaller padding, no toolbar)
}
```

**State**: `prompt: string` (controlled textarea)

**Behavior**:
- Textarea with placeholder text, RUN button on the right
- RUN button: charcoal background (`bg-charcoal`), white text, disabled state grays out
- On submit: calls `onSubmit(prompt)`, clears the input
- Enter key submits (Shift+Enter for newline) — V0 uses onClick only, keyboard shortcuts deferred
- When `disabled=true`: textarea is read-only, RUN button is grayed with a loading spinner
- Compact mode: smaller height, no left-side toolbar icons

**Styling**: White card, `rounded-input` border radius, hairline border, `shadow-subtle`

---

### `components/ProgressSteps.tsx`

**Purpose**: Vertical step indicator showing research pipeline progress. Dynamic based on intent type.

```typescript
interface ProgressStepsProps {
  intentType: IntentType | null;
  currentStep: StepName | null;
  completedSteps: StepName[];
  waitingForSelection: boolean;
}

// Renders a vertical list of steps based on intent_type:
//
// For "explore" intent (3 steps):
// 1. "Understanding your query" (classifying)
// 2. "Finding competitors" (finding_competitors)
// 3. "Analyzing products" (exploring)
//
// For "build" intent (5 steps):
// 1. "Understanding your query" (classifying)
// 2. "Finding competitors" (finding_competitors)
// 3. "Analyzing products" (exploring)
// 4. "Finding market gaps" (gap_analyzing)
// 5. "Defining your problem" (defining_problem)
//
// When intentType is null (before classify), show a single "Understanding your query" step.
```

**Behavior**:
- Each step renders as a row: icon + label
- **Completed**: Green checkmark icon (`text-success`), muted gray label
- **Current (active)**: Terracotta pulsing dot, charcoal text (slightly bold)
- **Pending**: Gray circle outline, placeholder gray text
- **Waiting**: Current step shows "Waiting for your selection..." sublabel
- Steps appear progressively — a step only renders after its `step_started` event
- The step list dynamically adjusts when `intentType` becomes known

**Styling**: Vertical list inside the sidebar, `font-sans` labels, `text-sm`

---

### `components/ResearchBlock.tsx`

**Purpose**: Single research result card (market overview, competitor list, or product profile).

```typescript
interface ResearchBlockProps {
  block: ResearchBlock;
  onAddToBlueprint?: (block: ResearchBlock) => void;
  onRefresh?: (block: ResearchBlock) => void;  // Re-scrape this product
}
```

**Behavior**:
- White card with `rounded-card` border radius, hairline border
- **Title**: Inter semibold, charcoal text
- **Content**: Rendered as markdown (use `react-markdown` or similar). Body text in Inter regular.
- **Sources**: Listed below content as small clickable links (`text-terracotta`, `text-xs`)
- **Cache indicator**: If `cached=true`, show "Last updated X days ago" badge in muted text
- **Actions** (shown on hover): "Add to Blueprint" button, "Refresh" button (if cached)
- **Block type variations**:
  - `market_overview`: Full-width card, no special treatment
  - `competitor_list`: Contains checkboxes for each competitor (see CompetitorSelector)
  - `product_profile`: Standard card with features, pricing, strengths, weaknesses sections

**Styling**: `bg-workspace`, `border-border`, `p-card-padding`, hover: `shadow-hover`

---

### `components/CompetitorSelector.tsx`

**Purpose**: Checkbox list of competitors for user selection. Rendered inside a `competitor_list` block.

```typescript
"use client";

interface CompetitorSelectorProps {
  competitors: CompetitorInfo[];
  selectedIds: string[];
  onSelectionChange: (selectedIds: string[]) => void;
  onExplore: (selectedIds: string[]) => void;
  disabled?: boolean;        // True while streaming
}
```

**State**: Managed by parent (selectedIds is controlled)

**Behavior**:
- List of competitor rows, each with: checkbox, name (bold), one-line description, pricing badge
- Checkbox uses shadcn/ui Checkbox component, themed with terracotta accent
- "Explore Selected" button at the bottom — terracotta background, white text
- Button disabled if no competitors selected or if `disabled=true`
- Shows count: "2 of 6 selected"

**Styling**: Each row has `py-3`, hairline border between rows, `font-sans`

---

### `components/ProblemSelector.tsx`

**Purpose**: Checkbox list of problem areas from gap analysis. User selects which problems to focus on. Only rendered for build intent.

```typescript
"use client";

interface ProblemSelectorProps {
  problems: ProblemArea[];
  selectedIds: string[];
  onSelectionChange: (selectedIds: string[]) => void;
  onDefine: (selectedIds: string[]) => void;  // Called when user clicks "Define Problem"
  disabled?: boolean;
}
```

**State**: Managed by parent (selectedIds is controlled)

**Behavior**:
- List of problem rows, each with: checkbox, title (bold), description, evidence bullets
- Checkbox uses shadcn/ui Checkbox component, themed with terracotta accent
- Opportunity size badge: "high" (terracotta), "medium" (muted), "low" (light gray)
- "Define Problem" button at the bottom — terracotta background, white text
- Button disabled if no problems selected or if `disabled=true`
- Shows count: "2 of 4 selected"

**Styling**: Each row has `py-3`, hairline border between rows, `font-sans`. Evidence shown as small `text-muted` bullets.

---

### `components/ClarificationPanel.tsx`

**Purpose**: Multi-question clarification UI with chips and a "Continue" button. Replaces the old single-question ClarificationChips.

```typescript
"use client";

interface ClarificationPanelProps {
  questions: ClarificationQuestion[];
  onSubmit: (answers: ClarificationAnswer[]) => void;   // Called when user clicks "Continue"
  disabled?: boolean;
}
```

**State**: `answers: Record<string, string[]>` (questionId → selected optionIds)

**Behavior**:
- Renders ALL questions vertically with spacing between them
- For each question: render the label as a heading (`font-sans`, `text-sm`, `text-charcoal`), then options as clickable chips
- Chips: rounded pills, hairline border, white fill
- Selected chip: terracotta border + terracotta-light fill
- If `allow_multiple=false`: selecting one deselects the previous (radio behavior)
- If `allow_multiple=true`: toggle each chip independently
- Each chip shows the option label + description (if present) as a sublabel
- **"Continue" button** at the bottom: terracotta background, white text
  - Disabled until at least one option is selected per question
  - On click: builds `ClarificationAnswer[]` from state and calls `onSubmit(answers)`
  - Does NOT auto-submit on chip selection — user must explicitly click "Continue"
- Shows a subtle progress indicator: "2 of 3 answered" below the Continue button

**Styling**: Chips use `rounded-chip`, `border-border`, selected: `border-terracotta bg-terracotta-light`. Questions separated by `mb-section-gap`.

---

### `components/Sidebar.tsx`

**Purpose**: Right panel — contains header, progress steps, clarification UI, chat history, and prompt input.

```typescript
"use client";

interface SidebarProps {
  researchState: ResearchState;
  onSubmitPrompt: (prompt: string) => void;
  onSubmitClarification: (answers: ClarificationAnswer[]) => void;
  onSelectCompetitors: (competitorIds: string[]) => void;
  onSelectProblems: (problemIds: string[]) => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}
```

**Layout** (top to bottom):
1. **Header**: Logo ("B" in circle), "1 SESSION LEFT" status pill, "Sign up" text button
2. **Progress Steps**: `<ProgressSteps />` component (dynamic based on intentType)
3. **Interaction Area** (conditional):
   - If `phase === "waiting_for_clarification"`: render `<ClarificationPanel />`
   - If `phase === "waiting_for_competitors"`: render "Select competitors to explore" heading + "Explore Selected" button reference
   - If `phase === "waiting_for_problems"`: render "Select problem areas" heading + "Define Problem" button reference
   - If `phase === "idle"`: render welcome message + suggested research pills
4. **Prompt Input**: `<PromptInput compact />` pinned at the bottom

**Collapsed state** (Screen 9): Thin strip with logo icon + expand button. All content hidden.

**Styling**: `bg-sand` background, inner content area in `bg-workspace rounded-panel`. Width: ~30% of viewport (min 320px).

---

### `components/Workspace.tsx`

**Purpose**: Left panel — contains tab navigation and renders either research blocks or blueprint view.

```typescript
"use client";

interface WorkspaceProps {
  blocks: ResearchBlock[];
  blockErrors: BlockErrorEvent[];
  activeTab: "research" | "blueprint";
  onTabChange: (tab: "research" | "blueprint") => void;
  blueprintEntries: BlueprintEntry[];
  onAddToBlueprint: (block: ResearchBlock) => void;
  onRemoveFromBlueprint: (entryId: string) => void;
  onEditBlueprint: (entryId: string, newContent: string) => void;
}

interface BlueprintEntry {
  id: string;
  block: ResearchBlock;
  editedContent?: string;   // If user has edited the content
  addedAt: string;
}
```

**Layout**:
1. **Tab bar**: "Research" | "Blueprint" text links, terracotta underline on active
2. **Content area** (based on active tab):
   - **Research tab**: vertical list of `<ResearchBlock />` components + inline `<BlockErrorCard />` for errors
   - **Blueprint tab**: `<BlueprintView />` component

**Empty state** (Research tab, no blocks): Centered empty state with serif heading "Begin your inquiry." and muted description.

**Styling**: `bg-workspace`, `rounded-panel`, full left panel width (~70% viewport)

---

### `components/BlueprintView.tsx`

**Purpose**: Curated document view — user's selected research blocks with editing capability.

```typescript
"use client";

interface BlueprintViewProps {
  entries: BlueprintEntry[];
  onRemove: (entryId: string) => void;
  onEdit: (entryId: string, newContent: string) => void;
}
```

**Behavior**:
- Document-style layout: title at top ("Your Blueprint" in Newsreader serif), entries below
- Each entry: terracotta left border accent (4px), content area (editable), source links
- **Edit mode**: click "Edit" → content becomes a textarea with done/cancel buttons
- **Remove**: "Remove" button (ghost, muted red text)
- Entries ordered by `addedAt`
- Empty state: "Add research blocks to build your blueprint."

**Styling**: `font-serif` for title, `font-sans` for content, terracotta left border on entries

---

### `components/SessionCard.tsx`

**Purpose**: Card for a single journey in the dashboard list.

```typescript
interface SessionCardProps {
  journey: JourneySummary;
  onClick: (journeyId: string) => void;
}
```

**Behavior**:
- White card with title (journey title or truncated prompt), status badge, date
- Status badge: "Active" (terracotta), "Completed" (success green), "Archived" (muted gray)
- Step count: "3 steps" in muted text
- Click navigates to `/explore/{journeyId}`
- Hover: `shadow-hover` lift effect

**Styling**: `bg-workspace`, `rounded-card`, `border-border`, `p-card-padding`

---

### `components/BlockErrorCard.tsx`

**Purpose**: Inline warning card for a failed research block.

```typescript
interface BlockErrorCardProps {
  blockName: string;
  error: string;
  onRetry: () => void;       // Re-runs the full research pipeline
}
```

**Behavior**:
- Amber/yellow tinted card with warning icon, block name, error message
- "Try again" button (secondary style) — triggers full research re-run
- Compact layout, same width as research blocks

**Styling**: `bg-amber-50`, `border-amber-200`, `text-amber-800` (standard warning palette from Tailwind)

---

### `components/AuthModal.tsx`

**Purpose**: Signup/login modal — UI shell only, no backend wiring in V0.

```typescript
"use client";

interface AuthModalProps {
  open: boolean;
  onClose: () => void;
}
```

**Behavior**:
- Dialog overlay with "Sign up to save your research" heading
- Google sign-in button (styled, non-functional in V0)
- Email input + "Send magic link" button (styled, non-functional in V0)
- Close button in top-right
- On any action: show a toast "Coming soon!" and close

**Styling**: Uses shadcn/ui Dialog component. White background, `rounded-card`.

---

## 14. Frontend Pages

---

### `app/layout.tsx`

**Purpose**: Root layout — font loading, global styles, metadata.

```typescript
// Server Component (no "use client")

import { Newsreader, Inter } from "next/font/google";

// Load fonts with Next.js font optimization
const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

// Apply font CSS variables to <html>
// className={`${newsreader.variable} ${inter.variable}`}
```

**Metadata**: Title: "Blueprint — Product Research", Description, favicon.

**Styling**: `bg-sand min-h-screen` on the body. Font variables applied globally.

---

### `app/page.tsx` (Landing Page — Screen 1)

**Purpose**: Landing page with centered prompt input. Entry point for new research.

```typescript
"use client";

// State: prompt string
// On submit: call startResearch() → navigate to /explore/{journeyId} once journey_started event arrives
```

**Layout**:
- Full-screen `bg-sand` background
- Centered content: Logo, heading ("What would you like to research?" in Newsreader serif), `<PromptInput />`
- Below input: row of suggested research pills (clickable chips that pre-fill the prompt)
- Suggested pills: "Market Analysis", "Competitor Research", "Product Deep Dive", etc.

**Navigation**:
- On `journey_started` event: `router.push(/explore/${journeyId})`
- The SSE stream continues — the explore page picks it up (via shared state or by reconnecting)

**Approach for SSE handoff**: Two options:
- **Option A**: Start the stream on the landing page, store the stream reference + accumulated events in a context provider, navigate, explore page reads from context.
- **Option B**: On the landing page, just call `POST /api/research` to create the journey (non-streaming), get the `journey_id` from the response, navigate, then the explore page opens the SSE stream.

**Recommended (Option B simplified)**: The landing page starts the SSE stream. On `journey_started`, navigate to `/explore/{journeyId}`. The explore page re-fetches the journey state from `GET /api/journeys/{id}` and continues listening for new events. If the stream is still running, events continue on the same stream (pass via React context or state management). If the stream ended (waiting_for_selection), the explore page reconstructs state from the saved journey steps.

---

### `app/explore/[journeyId]/page.tsx` (Workspace — Screens 2-6, 9)

**Purpose**: Main two-panel workspace. Renders research blocks, handles SSE events, manages research state.

```typescript
"use client";

// This is the core page of the application.
// It manages the full ResearchState and orchestrates all interactions.
```

**State**: `ResearchState` (from `types.ts`) managed via `useReducer`

**Layout**: Two-panel flex layout:
- Left: `<Workspace />` (~70% width)
- Right: `<Sidebar />` (~30% width)

**Data flow**:
1. On mount: load journey via `getJourney(journeyId)`
2. Reconstruct `ResearchState` from saved journey steps:
   - Parse `output_data` of each step to rebuild blocks
   - Determine current phase from the last step's type and whether it has `user_selection`
3. If journey status is "active" and last step needs selection: show selection UI
4. If journey status is "completed": show all blocks, summary, no input

**SSE handling** (via callbacks from `api.ts`):
- `onEvent(event)`: dispatch to reducer, update state
- Reducer handles each event type:
  - `quick_response`: set quickResponse, set phase to "completed" (no journey)
  - `journey_started`: set journeyId and intentType
  - `intent_redirect`: show info banner
  - `step_started`: set currentStep, add to active steps
  - `step_completed`: add to completedSteps
  - `block_ready`: append to blocks array. If block.type === "gap_analysis", extract problemAreas from block content.
  - `block_error`: append to errors array
  - `clarification_needed`: set questions, set phase to "waiting_for_clarification"
  - `waiting_for_selection`: set phase based on selection_type ("clarification" → "waiting_for_clarification", "competitors" → "waiting_for_competitors", "problems" → "waiting_for_problems")
  - `research_complete`: set phase to "completed", set summary
  - `error`: set phase to "error"

**Selection handlers**:
- `handleClarificationSubmit(answers)`: call `sendSelection(journeyId, { step_type: "clarify", selection: { answers } })`, reset to streaming phase
- `handleCompetitorExplore(competitorIds)`: call `sendSelection(journeyId, { step_type: "select_competitors", selection: { competitor_ids } })`, reset to streaming phase
- `handleProblemSelect(problemIds)`: call `sendSelection(journeyId, { step_type: "select_problems", selection: { problem_ids } })`, reset to streaming phase

---

### `app/dashboard/page.tsx` (Dashboard — Screen 7)

**Purpose**: List of all saved research sessions.

```typescript
"use client";

// State: journeys: JourneySummary[], loading: boolean
// On mount: call getJourneys()
```

**Layout**:
- `bg-sand` background, centered content area (max-width ~900px)
- Header: "Your Sessions" in Newsreader serif, "New Research" button
- Grid/list of `<SessionCard />` components, ordered by date (newest first)
- Empty state: "No sessions yet. Start your first research above."

**Navigation**:
- Click "New Research": navigate to `/` (landing page)
- Click a session card: navigate to `/explore/{journeyId}`

---

### `tailwind.config.ts`

**Purpose**: Tailwind configuration with all Cozy Sand design tokens.

See [DESIGN_GUIDE.md](DESIGN_GUIDE.md) and [ARCHITECTURE.md](ARCHITECTURE.md) Section 10 for the complete token values. The config is already fully specified in those documents — implement it exactly as shown.

---

## Related Documents

- [PLAN.md](PLAN.md) — Product scope, DB schema, build phases
- [ARCHITECTURE.md](ARCHITECTURE.md) — Technical decisions, SSE protocol, error handling, JSONB schemas
- [DESIGN_GUIDE.md](DESIGN_GUIDE.md) — Visual design system
- [TECH_DEBT.md](TECH_DEBT.md) — Deferred decisions
- [AGENTS.md](AGENTS.md) — Coding agent rules
- [FOUNDER_TASKS.md](FOUNDER_TASKS.md) — Tasks on the founder (prompts, API keys, infra)

