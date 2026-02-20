"""
Blueprint Backend — Shared Test Fixtures

Provides mocked versions of external services (LLM, search, DB, scraper)
for deterministic, fast unit tests.
"""

import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

# Ensure app module is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# -----------------------------------------------------------------------------
# Environment Setup (before importing app modules)
# -----------------------------------------------------------------------------

# Set test environment variables before importing app modules
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("SERPER_API_KEY", "test-serper-key")
os.environ.setdefault("JINA_API_KEY", "test-jina-key")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-supabase-key")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")


# -----------------------------------------------------------------------------
# Mock Response Classes
# -----------------------------------------------------------------------------


@dataclass
class MockLLMMessage:
    """Mock message from LLM response."""
    content: str
    reasoning_content: Optional[str] = None


@dataclass
class MockLLMChoice:
    """Mock choice from LLM response."""
    message: MockLLMMessage


@dataclass
class MockLLMUsage:
    """Mock usage stats from LLM response."""
    total_tokens: int = 100
    prompt_tokens: int = 50
    completion_tokens: int = 50


@dataclass
class MockLLMResponse:
    """Mock LLM completion response."""
    choices: list[MockLLMChoice]
    usage: MockLLMUsage = None

    def __post_init__(self):
        if self.usage is None:
            self.usage = MockLLMUsage()


def create_mock_llm_response(content: str) -> MockLLMResponse:
    """Create a mock LLM response with given content."""
    return MockLLMResponse(
        choices=[MockLLMChoice(message=MockLLMMessage(content=content))]
    )


# -----------------------------------------------------------------------------
# Mock Data Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_classify_response() -> dict:
    """Sample classify response for build intent."""
    return {
        "intent_type": "build",
        "domain": "Note-taking",
        "clarification_questions": [
            {
                "id": "target-platform",
                "label": "What platform are you targeting?",
                "options": [
                    {"id": "mobile", "label": "Mobile", "description": "Native iOS/Android app"},
                    {"id": "web", "label": "Web", "description": "Browser-based application"},
                ],
                "allow_multiple": True,
                "allow_other": False,
            }
        ],
        "quick_response": None,
    }


@pytest.fixture
def mock_classify_small_talk_response() -> dict:
    """Sample classify response for small talk."""
    return {
        "intent_type": "small_talk",
        "domain": None,
        "clarification_questions": None,
        "quick_response": "Hello! I'm Blueprint, your product research assistant.",
    }


@pytest.fixture
def mock_competitors_response() -> dict:
    """Sample competitors list response."""
    return {
        "competitors": [
            {
                "id": "notion",
                "name": "Notion",
                "description": "All-in-one workspace for notes, docs, and collaboration.",
                "url": "https://notion.so",
                "category": "Note-taking",
                "pricing_model": "Freemium",
            },
            {
                "id": "obsidian",
                "name": "Obsidian",
                "description": "Local-first markdown knowledge base with graph view.",
                "url": "https://obsidian.md",
                "category": "Note-taking",
                "pricing_model": "Free with paid sync",
            },
        ],
        "sources": ["https://alternativeto.net/software/notion/"],
    }


@pytest.fixture
def mock_product_profile_response() -> dict:
    """Sample product profile response."""
    return {
        "name": "Notion",
        "content": "Notion is an all-in-one workspace that combines notes, docs, and databases.",
        "features_summary": ["Rich text editing", "Database views", "Team collaboration"],
        "pricing_tiers": "Free for personal, Plus $10/user/mo, Business $15/user/mo",
        "target_audience": "Teams and knowledge workers who need flexible documentation",
        "strengths": ["Flexible block system", "Good collaboration features"],
        "weaknesses": ["Can be slow with large workspaces", "Requires internet"],
        "reddit_sentiment": "Users love the flexibility but complain about performance issues.",
        "sources": ["https://notion.so", "https://reddit.com/r/Notion"],
    }


@pytest.fixture
def mock_search_results():
    """Sample search results."""
    from app.search import SearchResult
    return [
        SearchResult(
            title="Notion vs Obsidian: Which is better?",
            url="https://example.com/notion-vs-obsidian",
            snippet="A comprehensive comparison of Notion and Obsidian for note-taking.",
        ),
        SearchResult(
            title="Best note-taking apps 2024",
            url="https://example.com/best-note-apps",
            snippet="Top 10 note-taking apps including Notion, Obsidian, and more.",
        ),
    ]


# -----------------------------------------------------------------------------
# LLM Mocking Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_llm(monkeypatch):
    """
    Mock litellm.acompletion to return predictable responses.
    
    Returns the mock function so tests can customize responses.
    """
    async def mock_acompletion(*args, **kwargs) -> MockLLMResponse:
        # Default response - tests can override via mock_acompletion.return_value
        return create_mock_llm_response('{"intent_type": "build", "domain": "test"}')
    
    mock = AsyncMock(side_effect=mock_acompletion)
    monkeypatch.setattr("litellm.acompletion", mock)
    return mock


@pytest.fixture
def mock_llm_with_response(monkeypatch):
    """
    Factory fixture to mock LLM with a specific response.
    
    Usage:
        def test_example(mock_llm_with_response):
            mock = mock_llm_with_response({"key": "value"})
            # ... test code
    """
    def _create_mock(response_data: dict):
        async def mock_acompletion(*args, **kwargs) -> MockLLMResponse:
            return create_mock_llm_response(json.dumps(response_data))
        
        mock = AsyncMock(side_effect=mock_acompletion)
        monkeypatch.setattr("litellm.acompletion", mock)
        return mock
    
    return _create_mock


@pytest.fixture
def mock_llm_failure(monkeypatch):
    """Mock LLM to simulate all providers failing."""
    async def mock_acompletion(*args, **kwargs):
        raise Exception("Rate limit exceeded")
    
    mock = AsyncMock(side_effect=mock_acompletion)
    monkeypatch.setattr("litellm.acompletion", mock)
    return mock


@pytest.fixture
def mock_llm_rate_limit_then_success(monkeypatch):
    """Mock LLM to fail with rate limit once, then succeed."""
    call_count = 0
    
    async def mock_acompletion(*args, **kwargs) -> MockLLMResponse:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("429 rate_limit_exceeded")
        return create_mock_llm_response('{"intent_type": "build", "domain": "test"}')
    
    mock = AsyncMock(side_effect=mock_acompletion)
    monkeypatch.setattr("litellm.acompletion", mock)
    return mock


# -----------------------------------------------------------------------------
# Search Mocking Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_search(monkeypatch, mock_search_results):
    """Mock search module to return predictable results."""
    async def mock_search_fn(query: str, num_results: int = 10, journey_id: str | None = None):
        return mock_search_results[:num_results]
    
    mock = AsyncMock(side_effect=mock_search_fn)
    monkeypatch.setattr("app.search.search", mock)
    monkeypatch.setattr("app.search.search_reddit", mock)
    return mock


@pytest.fixture
def mock_search_failure(monkeypatch):
    """Mock search to return empty results (simulates all providers failing)."""
    async def mock_search_fn(*args, **kwargs):
        return []
    
    mock = AsyncMock(side_effect=mock_search_fn)
    monkeypatch.setattr("app.search.search", mock)
    monkeypatch.setattr("app.search.search_reddit", mock)
    return mock


# -----------------------------------------------------------------------------
# Database Mocking Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_db(monkeypatch):
    """
    Mock all database operations with in-memory storage.
    
    Returns a dict containing the mock functions and storage for inspection.
    """
    # In-memory storage
    storage = {
        "journeys": {},
        "steps": {},
        "products": {},
        "alternatives": {},
        "llm_state": {"active_provider": "gemini/gemini-3-flash-preview"},
        "prototype_sessions": {},
    }
    journey_counter = 0
    step_counter = 0
    
    async def mock_create_journey(prompt: str, intent_type: str = "explore") -> str:
        nonlocal journey_counter
        journey_counter += 1
        journey_id = f"test-journey-{journey_counter}"
        storage["journeys"][journey_id] = {
            "id": journey_id,
            "title": prompt[:100],
            "status": "active",
            "intent_type": intent_type,
            "initial_prompt": prompt,
            "steps": [],
        }
        return journey_id
    
    async def mock_get_journey(journey_id: str) -> Optional[dict]:
        journey = storage["journeys"].get(journey_id)
        if journey:
            journey["steps"] = [
                s for s in storage["steps"].values() 
                if s.get("journey_id") == journey_id
            ]
        return journey
    
    async def mock_save_journey_step(
        journey_id: str,
        step_number: int,
        step_type: str,
        input_data: Any = None,
        output_data: Any = None,
        user_selection: Any = None,
    ) -> str:
        nonlocal step_counter
        step_counter += 1
        step_id = f"test-step-{step_counter}"
        storage["steps"][step_id] = {
            "id": step_id,
            "journey_id": journey_id,
            "step_number": step_number,
            "step_type": step_type,
            "input_data": input_data,
            "output_data": output_data,
            "user_selection": user_selection,
        }
        return step_id
    
    async def mock_get_last_step(journey_id: str) -> Optional[dict]:
        journey_steps = [
            s for s in storage["steps"].values()
            if s.get("journey_id") == journey_id
        ]
        if journey_steps:
            return max(journey_steps, key=lambda s: s["step_number"])
        return None
    
    async def mock_get_next_step_number(journey_id: str) -> int:
        journey_steps = [
            s for s in storage["steps"].values()
            if s.get("journey_id") == journey_id
        ]
        if journey_steps:
            return max(s["step_number"] for s in journey_steps) + 1
        return 1
    
    async def mock_update_journey_status(journey_id: str, status: str) -> None:
        if journey_id in storage["journeys"]:
            storage["journeys"][journey_id]["status"] = status
    
    async def mock_get_llm_state() -> str:
        return storage["llm_state"]["active_provider"]
    
    async def mock_update_llm_state(provider: str, reason: str) -> None:
        storage["llm_state"]["active_provider"] = provider
    
    async def mock_get_cached_product(normalized_name: str) -> Optional[dict]:
        return storage["products"].get(normalized_name)
    
    async def mock_get_cached_alternatives(normalized_name: str) -> Optional[list[dict]]:
        return storage["alternatives"].get(normalized_name)
    
    async def mock_list_journeys() -> list[dict]:
        return list(storage["journeys"].values())
    
    async def mock_log_user_choice(*args, **kwargs) -> None:
        pass
    
    # Apply mocks
    monkeypatch.setattr("app.db.create_journey", AsyncMock(side_effect=mock_create_journey))
    monkeypatch.setattr("app.db.get_journey", AsyncMock(side_effect=mock_get_journey))
    monkeypatch.setattr("app.db.save_journey_step", AsyncMock(side_effect=mock_save_journey_step))
    monkeypatch.setattr("app.db.get_last_step", AsyncMock(side_effect=mock_get_last_step))
    monkeypatch.setattr("app.db.get_next_step_number", AsyncMock(side_effect=mock_get_next_step_number))
    monkeypatch.setattr("app.db.update_journey_status", AsyncMock(side_effect=mock_update_journey_status))
    monkeypatch.setattr("app.db.get_llm_state", AsyncMock(side_effect=mock_get_llm_state))
    monkeypatch.setattr("app.db.update_llm_state", AsyncMock(side_effect=mock_update_llm_state))
    monkeypatch.setattr("app.db.get_cached_product", AsyncMock(side_effect=mock_get_cached_product))
    monkeypatch.setattr("app.db.get_cached_alternatives", AsyncMock(side_effect=mock_get_cached_alternatives))
    monkeypatch.setattr("app.db.list_journeys", AsyncMock(side_effect=mock_list_journeys))
    monkeypatch.setattr("app.db.log_user_choice", AsyncMock(side_effect=mock_log_user_choice))
    monkeypatch.setattr(
        "app.db.create_prototype_session",
        AsyncMock(side_effect=mock_create_prototype_session),
    )
    monkeypatch.setattr(
        "app.db.update_prototype_session",
        AsyncMock(side_effect=mock_update_prototype_session),
    )
    monkeypatch.setattr(
        "app.db.get_prototype_session",
        AsyncMock(side_effect=mock_get_prototype_session),
    )

    return storage


@pytest.fixture
def mock_llm_vision(monkeypatch):
    """
    Mock litellm.acompletion for vision (design-to-code) calls.
    Returns the mock so tests can customize responses.
    """
    from tests.conftest import create_mock_llm_response

    async def mock_acompletion(*args, **kwargs):
        return create_mock_llm_response(
            "export default function App() { return <div>Hello</div>; }"
        )

    mock = AsyncMock(side_effect=mock_acompletion)
    monkeypatch.setattr("litellm.acompletion", mock)
    return mock


@pytest.fixture
def mock_prototype_session_db(mock_db):
    """
    Extends mock_db with prototype_sessions storage.
    mock_db already includes create/update/get_prototype_session.
    """
    return mock_db


# -----------------------------------------------------------------------------
# Scraper Mocking Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_scraper(monkeypatch):
    """Mock scraper to return predictable content."""
    async def mock_scrape(url: str, journey_id: str | None = None) -> str:
        return f"Scraped content from {url}. This is a mock response with product information."
    
    mock = AsyncMock(side_effect=mock_scrape)
    monkeypatch.setattr("app.scraper.scrape_url", mock)
    return mock


@pytest.fixture
def mock_scraper_failure(monkeypatch):
    """Mock scraper to fail."""
    async def mock_scrape(*args, **kwargs) -> str:
        return ""
    
    mock = AsyncMock(side_effect=mock_scrape)
    monkeypatch.setattr("app.scraper.scrape_url", mock)
    return mock


# -----------------------------------------------------------------------------
# HTTP Client Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
async def client():
    """Async HTTP client for testing FastAPI endpoints."""
    from httpx import ASGITransport
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def app():
    """Get the FastAPI app instance."""
    from app.main import app
    return app


def create_test_client():
    """Create a test client for use in tests that need manual client creation."""
    from httpx import ASGITransport
    from app.main import app
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# -----------------------------------------------------------------------------
# LLM Module Reset Fixture
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_llm_state():
    """Reset LLM module state before each test."""
    import app.llm as llm_module
    llm_module._active_provider = None
    llm_module._initialized = False
    llm_module._rate_limited_until.clear()
    yield
    # Cleanup after test
    llm_module._active_provider = None
    llm_module._initialized = False
    llm_module._rate_limited_until.clear()


# -----------------------------------------------------------------------------
# SSE Parsing Helpers
# -----------------------------------------------------------------------------


def parse_sse_events(content: str) -> list[dict]:
    """Parse SSE event stream into list of event dicts."""
    events = []
    for line in content.split("\n"):
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                events.append(data)
            except json.JSONDecodeError:
                continue
    return events


@pytest.fixture
def parse_sse():
    """Fixture providing SSE parsing helper."""
    return parse_sse_events
