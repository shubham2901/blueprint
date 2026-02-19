# Testing Patterns

**Analysis Date:** 2025-02-19

## Test Framework

**Runner:**
- pytest 8.3+ with pytest-asyncio 0.24+
- Config: `backend/pytest.ini`

**Assertion Library:**
- Built-in pytest assertions (`assert`, `pytest.raises`)

**Run Commands:**
```bash
cd backend
pytest tests -v --ignore=tests/evals --tb=short        # Run all unit tests (exclude evals)
pytest tests -v -m "not slow"                           # Exclude slow tests
pytest tests -v -m "not eval"                           # Exclude eval tests (real LLM)
pytest tests/test_api.py -v                             # Run specific file
pytest tests -v -x                                      # Stop on first failure (CI default)
```

**pytest.ini settings:**
- `asyncio_mode = auto`
- `testpaths = tests`
- `python_files = test_*.py`, `python_functions = test_*`, `python_classes = Test*`
- Markers: `eval` (requires real LLM), `slow` (deselect with `-m "not slow"`)

## Test File Organization

**Location:**
- All tests in `backend/tests/` (separate from app code)
- No frontend tests in V0 (deferred to V1 with Playwright)

**Naming:**
- `test_<module>.py` — e.g. `test_api.py`, `test_llm.py`, `test_search.py`, `test_pipeline.py`, `test_prompts.py`

**Structure:**
```
backend/tests/
├── __init__.py
├── conftest.py          # Shared fixtures (mocks, client, parse_sse)
├── test_api.py          # REST + SSE endpoint tests
├── test_llm.py          # LLM module unit tests
├── test_search.py       # Search module unit tests
├── test_pipeline.py     # E2E pipeline flow tests
├── test_prompts.py      # Prompts module unit tests
└── evals/               # Prompt evaluation tests (real LLM, optional)
```

## Test Structure

**Suite Organization:**
```python
# -----------------------------------------------------------------------------
# Section Name
# --------------------------------------------------------------------------------

class TestClassName:
    """Tests for <feature>."""

    @pytest.mark.asyncio
    async def test_descriptive_name(self, mock_db, mock_llm_with_response, parse_sse):
        """Test that <expected behavior>."""
        mock_llm_with_response({
            "intent_type": "build",
            "domain": "Note-taking",
            ...
        })
        async with get_test_client() as client:
            response = await client.post("/api/research", json={"prompt": "Build a note app"})
        events = parse_sse(response.text)
        assert len([e for e in events if e.get("type") == "journey_started"]) == 1
```

**Patterns:**
- Use `class TestClassName` for grouping related tests
- Docstrings on classes and methods describe scope
- Use `@pytest.mark.asyncio` for async tests

## Mocking

**Framework:** `unittest.mock` — `patch`, `AsyncMock`, `MagicMock`, `monkeypatch`

**Patterns:**
```python
# Patch LLM at litellm.acompletion
with patch("litellm.acompletion", AsyncMock(side_effect=mock_acompletion)):
    response = await client.post("/api/research", json={"prompt": "..."})

# Monkeypatch for module-level mocks
monkeypatch.setattr("app.search._tavily_search", AsyncMock(side_effect=mock_tavily))

# Patch httpx.AsyncClient
with patch("httpx.AsyncClient") as mock_client:
    mock_instance = MagicMock()
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=None)
    mock_instance.post = AsyncMock(side_effect=mock_post)
    mock_client.return_value = mock_instance
```

**What to Mock:**
- `litellm.acompletion` — LLM calls
- `app.db.*` — all DB functions (create_journey, get_journey, save_journey_step, etc.)
- `app.search.search`, `app.search.search_reddit` — search
- `app.search._tavily_search`, `_serper_search`, `_duckduckgo_search` — individual providers
- `httpx.AsyncClient` — HTTP requests to Tavily/Serper
- `app.search.DDGS` — DuckDuckGo
- `app.scraper.scrape_url` — scraper (note: actual module exports `scrape`. Conftest mocks `scrape_url` — may be stale; fix if scraper tests fail.)

**What NOT to Mock:**
- Pydantic models and validation
- FastAPI app and routing
- Request/response serialization

## Fixtures and Factories

**Test Data:**
```python
# From backend/tests/conftest.py
def create_mock_llm_response(content: str) -> MockLLMResponse:
    return MockLLMResponse(
        choices=[MockLLMChoice(message=MockLLMMessage(content=content))]
    )

@pytest.fixture
def mock_classify_response() -> dict:
    return {
        "intent_type": "build",
        "domain": "Note-taking",
        "clarification_questions": [...],
        "quick_response": None,
    }
```

**Location:**
- `backend/tests/conftest.py` — all shared fixtures

**Key Fixtures:**
- `mock_db` — in-memory DB; mocks `app.db.*`
- `mock_llm` — default LLM response
- `mock_llm_with_response(response_data)` — factory for configurable LLM response
- `mock_llm_failure` — all providers fail
- `mock_search` — returns `mock_search_results`
- `client` — async HTTP client (AsyncClient + ASGITransport)
- `parse_sse` — parses SSE text into list of event dicts
- `reset_llm_state` — autouse; clears LLM module state before each test

## Coverage

**Requirements:** None enforced in V0

**View Coverage:**
```bash
cd backend
pytest tests --ignore=tests/evals --cov=app --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- `test_llm.py` — helper functions, `call_llm`, `call_llm_structured`, rate limit fallback
- `test_search.py` — `search`, `_tavily_search`, `_serper_search`, `_duckduckgo_search`, `search_reddit`
- `test_prompts.py` — prompt builders return valid message format, no LLM calls

**Integration Tests (mocked):**
- `test_api.py` — POST /api/research, POST /api/research/{id}/selection, POST /api/research/{id}/refine
- `test_pipeline.py` — full SSE event sequences for small_talk, off_topic, build, explore, refine

**E2E / Evals:**
- `backend/tests/evals/` — prompt evaluation tests (real LLM, optional)
- Run on schedule, manual trigger, or when `prompts.py` changes

**Frontend:**
- No tests in V0 (deferred to V1 with Playwright)

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_example(self, mock_db, client):
    response = await client.post("/api/research", json={"prompt": "..."})
    assert response.status_code == 200
```

**Error Testing:**
```python
with pytest.raises(LLMError, match="All LLM providers failed"):
    await call_llm([{"role": "user", "content": "test"}])

# Or for SSE error events
events = parse_sse(response.text)
error_events = [e for e in events if e.get("type") == "error"]
assert len(error_events) >= 1
assert error_events[0]["error_code"].startswith("BP-")
```

**SSE Parsing:**
```python
# conftest provides parse_sse fixture
events = parse_sse(response.text)
journey_events = [e for e in events if e.get("type") == "journey_started"]
journey_id = journey_events[0]["journey_id"] if journey_events else None
```

**Environment Setup:**
- `conftest.py` sets `os.environ` for test keys before importing app modules
- Required env vars: `GEMINI_API_KEY`, `TAVILY_API_KEY`, `SUPABASE_URL`, etc. (all mocked)

**CI:**
- `.github/workflows/test.yml` runs unit tests on push/PR
- `unit-tests` job: pytest with `-x`, no evals
- `prompt-evals` job: conditional (schedule, manual, or prompts.py changes)

---

*Testing analysis: 2025-02-19*
