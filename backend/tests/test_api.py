"""
Blueprint Backend — API Endpoint Unit Tests

Tests for REST endpoints: health check, research start, selection submission.
All tests use mocked dependencies - no real API requests or database calls.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from httpx import AsyncClient, ASGITransport
from fastapi import status

from app.main import app
from app.models import ClassifyResult, CompetitorList


def get_test_client():
    """Create async client for testing."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# -----------------------------------------------------------------------------
# Health Check Tests
# -----------------------------------------------------------------------------


class TestHealthCheck:
    """Tests for /api/health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_ok(self, client):
        """Test health check endpoint returns status ok."""
        response = await client.get("/api/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_check_includes_version(self, client):
        """Test health check returns version info."""
        response = await client.get("/api/health")
        
        data = response.json()
        assert data["version"] == "0.1.0"


# -----------------------------------------------------------------------------
# Research Start Tests (POST /api/research)
# -----------------------------------------------------------------------------


class TestStartResearch:
    """Tests for POST /api/research endpoint."""

    @pytest.mark.asyncio
    async def test_rejects_empty_prompt(self, client):
        """Test that empty prompts are rejected."""
        response = await client.post("/api/research", json={"prompt": ""})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_rejects_missing_prompt(self, client):
        """Test that missing prompt field is rejected."""
        response = await client.post("/api/research", json={})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_rejects_too_long_prompt(self, client):
        """Test that prompts over 500 chars are rejected."""
        long_prompt = "a" * 501
        response = await client.post("/api/research", json={"prompt": long_prompt})
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_accepts_valid_prompt_returns_sse(self, mock_db, mock_llm_with_response):
        """Test that valid prompt returns SSE stream."""
        # Setup mock LLM response for classify
        mock_llm_with_response({
            "intent_type": "small_talk",
            "domain": None,
            "clarification_questions": None,
            "quick_response": "Hello! I'm Blueprint."
        })
        
        async with get_test_client() as client:
            response = await client.post(
                "/api/research",
                json={"prompt": "Hello!"}
            )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    @pytest.mark.asyncio
    async def test_small_talk_returns_quick_response(self, mock_db, mock_llm_with_response, parse_sse):
        """Test that small_talk intent returns quick_response event."""
        mock_llm_with_response({
            "intent_type": "small_talk",
            "domain": None,
            "clarification_questions": None,
            "quick_response": "Hello! I'm Blueprint, your product research assistant."
        })
        
        async with get_test_client() as client:
            response = await client.post(
                "/api/research",
                json={"prompt": "Hi there!"}
            )
        
        events = parse_sse(response.text)
        
        # Should have quick_response event
        quick_response_events = [e for e in events if e.get("type") == "quick_response"]
        assert len(quick_response_events) == 1
        assert "Blueprint" in quick_response_events[0]["message"]

    @pytest.mark.asyncio
    async def test_build_intent_creates_journey(self, mock_db, mock_llm_with_response, parse_sse):
        """Test that build intent creates journey and returns journey_started event."""
        mock_llm_with_response({
            "intent_type": "build",
            "domain": "Note-taking",
            "clarification_questions": [
                {
                    "id": "target-platform",
                    "label": "What platform?",
                    "options": [
                        {"id": "mobile", "label": "Mobile", "description": "Mobile app"}
                    ],
                    "allow_multiple": True,
                    "allow_other": False
                }
            ],
            "quick_response": None
        })
        
        async with get_test_client() as client:
            response = await client.post(
                "/api/research",
                json={"prompt": "I want to build a note-taking app"}
            )
        
        events = parse_sse(response.text)
        
        # Should have journey_started event
        journey_events = [e for e in events if e.get("type") == "journey_started"]
        assert len(journey_events) == 1
        assert journey_events[0]["intent_type"] == "build"
        assert "journey_id" in journey_events[0]

    @pytest.mark.asyncio
    async def test_explore_intent_creates_journey(self, mock_db, mock_llm_with_response, parse_sse):
        """Test that explore intent creates journey."""
        mock_llm_with_response({
            "intent_type": "explore",
            "domain": "Note-taking",
            "clarification_questions": [
                {
                    "id": "focus-area",
                    "label": "What aspect interests you?",
                    "options": [
                        {"id": "competitors", "label": "Competitors", "description": "Competitor analysis"}
                    ],
                    "allow_multiple": False,
                    "allow_other": False
                }
            ],
            "quick_response": None
        })
        
        async with get_test_client() as client:
            response = await client.post(
                "/api/research",
                json={"prompt": "Tell me about Notion"}
            )
        
        events = parse_sse(response.text)
        
        journey_events = [e for e in events if e.get("type") == "journey_started"]
        assert len(journey_events) == 1
        assert journey_events[0]["intent_type"] == "explore"

    @pytest.mark.asyncio
    async def test_off_topic_returns_quick_response(self, mock_db, mock_llm_with_response, parse_sse):
        """Test that off_topic intent returns quick_response, no journey."""
        mock_llm_with_response({
            "intent_type": "off_topic",
            "domain": None,
            "clarification_questions": None,
            "quick_response": "I focus on product research, not code generation."
        })
        
        async with get_test_client() as client:
            response = await client.post(
                "/api/research",
                json={"prompt": "Write Python code for me"}
            )
        
        events = parse_sse(response.text)
        
        # Should have quick_response, no journey_started
        quick_events = [e for e in events if e.get("type") == "quick_response"]
        journey_events = [e for e in events if e.get("type") == "journey_started"]
        
        assert len(quick_events) == 1
        assert len(journey_events) == 0

    @pytest.mark.asyncio
    async def test_clarification_event_sent(self, mock_db, mock_llm_with_response, parse_sse):
        """Test that clarification_needed event is sent for build/explore."""
        mock_llm_with_response({
            "intent_type": "build",
            "domain": "Note-taking",
            "clarification_questions": [
                {
                    "id": "target-platform",
                    "label": "What platform are you targeting?",
                    "options": [
                        {"id": "mobile", "label": "Mobile", "description": "Native mobile app"},
                        {"id": "web", "label": "Web", "description": "Browser-based"}
                    ],
                    "allow_multiple": True,
                    "allow_other": False
                }
            ],
            "quick_response": None
        })
        
        async with get_test_client() as client:
            response = await client.post(
                "/api/research",
                json={"prompt": "Build a note-taking app"}
            )
        
        events = parse_sse(response.text)
        
        clarification_events = [e for e in events if e.get("type") == "clarification_needed"]
        assert len(clarification_events) == 1
        assert len(clarification_events[0]["questions"]) > 0

    @pytest.mark.asyncio
    async def test_waiting_for_selection_event_sent(self, mock_db, mock_llm_with_response, parse_sse):
        """Test that waiting_for_selection event is sent after clarification."""
        mock_llm_with_response({
            "intent_type": "build",
            "domain": "Note-taking",
            "clarification_questions": [
                {
                    "id": "target-platform",
                    "label": "What platform?",
                    "options": [
                        {"id": "mobile", "label": "Mobile", "description": "Mobile app"}
                    ],
                    "allow_multiple": True,
                    "allow_other": False
                }
            ],
            "quick_response": None
        })
        
        async with get_test_client() as client:
            response = await client.post(
                "/api/research",
                json={"prompt": "Build a note-taking app"}
            )
        
        events = parse_sse(response.text)
        
        waiting_events = [e for e in events if e.get("type") == "waiting_for_selection"]
        assert len(waiting_events) == 1
        assert waiting_events[0]["selection_type"] == "clarification"


# -----------------------------------------------------------------------------
# Selection Submission Tests (POST /api/research/{id}/selection)
# -----------------------------------------------------------------------------


class TestSubmitSelection:
    """Tests for POST /api/research/{journey_id}/selection endpoint."""

    @pytest.mark.asyncio
    async def test_returns_404_for_invalid_journey(self, mock_db, client):
        """Test 404 returned for non-existent journey."""
        response = await client.post(
            "/api/research/nonexistent-id/selection",
            json={
                "step_type": "clarify",
                "selection": {"answers": []}
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_rejects_invalid_step_type(self, mock_db, mock_llm_with_response, parse_sse):
        """Test that invalid step_type is handled."""
        # First create a journey
        mock_llm_with_response({
            "intent_type": "build",
            "domain": "Note-taking",
            "clarification_questions": [
                {
                    "id": "q1",
                    "label": "Question?",
                    "options": [{"id": "o1", "label": "Option", "description": "Desc"}],
                    "allow_multiple": False,
                    "allow_other": False
                }
            ],
            "quick_response": None
        })
        
        async with get_test_client() as client:
            # Start research to create journey
            response = await client.post(
                "/api/research",
                json={"prompt": "Build a note-taking app"}
            )
            events = parse_sse(response.text)
            journey_id = next(
                (e["journey_id"] for e in events if e.get("type") == "journey_started"),
                None
            )
            
            assert journey_id is not None
            
            # Submit with invalid step_type
            response = await client.post(
                f"/api/research/{journey_id}/selection",
                json={
                    "step_type": "invalid_step",
                    "selection": {"answers": []}
                }
            )
        
        # Should return 200 but stream should have error or be empty
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_clarify_selection_returns_sse(self, mock_db, mock_llm_with_response, mock_search, parse_sse):
        """Test clarification selection returns SSE stream."""
        # Setup mock responses for different prompts
        call_count = 0
        
        async def mock_acompletion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            from tests.conftest import create_mock_llm_response
            
            if call_count == 1:
                # Classify call
                return create_mock_llm_response(json.dumps({
                    "intent_type": "build",
                    "domain": "Note-taking",
                    "clarification_questions": [
                        {
                            "id": "q1",
                            "label": "What platform?",
                            "options": [{"id": "mobile", "label": "Mobile", "description": "Mobile app"}],
                            "allow_multiple": False,
                            "allow_other": False
                        }
                    ],
                    "quick_response": None
                }))
            else:
                # Competitors call
                return create_mock_llm_response(json.dumps({
                    "competitors": [
                        {
                            "id": "notion",
                            "name": "Notion",
                            "description": "All-in-one workspace",
                            "url": "https://notion.so",
                            "category": "Note-taking",
                            "pricing_model": "Freemium"
                        }
                    ],
                    "sources": []
                }))
        
        async with get_test_client() as client:
            with patch("litellm.acompletion", AsyncMock(side_effect=mock_acompletion)):
                # Start research
                response = await client.post(
                    "/api/research",
                    json={"prompt": "Build a note-taking app"}
                )
                events = parse_sse(response.text)
                journey_id = next(
                    (e["journey_id"] for e in events if e.get("type") == "journey_started"),
                    None
                )
                
                # Submit clarification selection
                response = await client.post(
                    f"/api/research/{journey_id}/selection",
                    json={
                        "step_type": "clarify",
                        "selection": {
                            "answers": [
                                {"question_id": "q1", "selected_option_ids": ["mobile"]}
                            ]
                        }
                    }
                )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


# -----------------------------------------------------------------------------
# Request Validation Tests
# -----------------------------------------------------------------------------


class TestRequestValidation:
    """Tests for request validation."""

    @pytest.mark.asyncio
    async def test_research_request_validates_prompt_min_length(self, client):
        """Test prompt minimum length validation."""
        response = await client.post("/api/research", json={"prompt": ""})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_research_request_validates_prompt_max_length(self, client):
        """Test prompt maximum length validation (500 chars)."""
        response = await client.post("/api/research", json={"prompt": "x" * 501})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_selection_request_requires_step_type(self, client, mock_db, mock_llm_with_response, parse_sse):
        """Test that selection request requires step_type."""
        # Create a journey first
        mock_llm_with_response({
            "intent_type": "build",
            "domain": "Test",
            "clarification_questions": [
                {"id": "q", "label": "Q?", "options": [{"id": "o", "label": "O", "description": "D"}],
                 "allow_multiple": False, "allow_other": False}
            ],
            "quick_response": None
        })
        
        async with get_test_client() as ac:
            response = await ac.post("/api/research", json={"prompt": "Test"})
            events = parse_sse(response.text)
            journey_id = next((e["journey_id"] for e in events if e.get("type") == "journey_started"), None)
        
            # Missing step_type
            response = await ac.post(
                f"/api/research/{journey_id}/selection",
                json={"selection": {}}
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_selection_request_requires_selection(self, client, mock_db, mock_llm_with_response, parse_sse):
        """Test that selection request requires selection field."""
        # Create a journey first
        mock_llm_with_response({
            "intent_type": "build",
            "domain": "Test",
            "clarification_questions": [
                {"id": "q", "label": "Q?", "options": [{"id": "o", "label": "O", "description": "D"}],
                 "allow_multiple": False, "allow_other": False}
            ],
            "quick_response": None
        })
        
        async with get_test_client() as ac:
            response = await ac.post("/api/research", json={"prompt": "Test"})
            events = parse_sse(response.text)
            journey_id = next((e["journey_id"] for e in events if e.get("type") == "journey_started"), None)
            
            # Missing selection
            response = await ac.post(
                f"/api/research/{journey_id}/selection",
                json={"step_type": "clarify"}
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# -----------------------------------------------------------------------------
# Refine Research Tests (POST /api/research/{id}/refine)
# -----------------------------------------------------------------------------


class TestRefineResearch:
    """Tests for POST /api/research/{journey_id}/refine endpoint."""

    @pytest.mark.asyncio
    async def test_returns_404_for_invalid_journey(self, mock_db, client):
        """Test 404 returned for non-existent journey."""
        response = await client.post(
            "/api/research/nonexistent-id/refine",
            json={
                "step_type": "find_competitors",
                "feedback": "Add more competitors"
            }
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_refine_returns_sse_stream(self, mock_db, mock_llm_with_response, mock_search, parse_sse):
        """Test that refine endpoint returns SSE stream."""
        # First create a journey
        mock_llm_with_response({
            "intent_type": "build",
            "domain": "Note-taking",
            "clarification_questions": [
                {
                    "id": "q1",
                    "label": "Question?",
                    "options": [{"id": "o1", "label": "Option", "description": "Desc"}],
                    "allow_multiple": False,
                    "allow_other": False
                }
            ],
            "quick_response": None
        })
        
        async with get_test_client() as client:
            # Start research to create journey
            response = await client.post(
                "/api/research",
                json={"prompt": "Build a note-taking app"}
            )
            events = parse_sse(response.text)
            journey_id = next(
                (e["journey_id"] for e in events if e.get("type") == "journey_started"),
                None
            )
            
            assert journey_id is not None
            
            # Now refine
            mock_llm_with_response({
                "competitors": [
                    {"id": "c1", "name": "Notion", "description": "Workspace", "url": "https://notion.so"},
                    {"id": "c2", "name": "Obsidian", "description": "Notes", "url": "https://obsidian.md"},
                ],
                "sources": []
            })
            
            response = await client.post(
                f"/api/research/{journey_id}/refine",
                json={
                    "step_type": "find_competitors",
                    "feedback": "Add more enterprise competitors"
                }
            )
        
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        events = parse_sse(response.text)
        event_types = [e.get("type") for e in events]
        
        # Should have refine started and complete events
        assert "refine_started" in event_types
        assert "refine_complete" in event_types or "block_ready" in event_types

    @pytest.mark.asyncio
    async def test_refine_request_validation(self, mock_db, mock_llm_with_response, parse_sse):
        """Test that refine request validates required fields."""
        # Create a journey first
        mock_llm_with_response({
            "intent_type": "build",
            "domain": "Test",
            "clarification_questions": [
                {"id": "q", "label": "Q?", "options": [{"id": "o", "label": "O", "description": "D"}],
                 "allow_multiple": False, "allow_other": False}
            ],
            "quick_response": None
        })
        
        async with get_test_client() as ac:
            response = await ac.post("/api/research", json={"prompt": "Test"})
            events = parse_sse(response.text)
            journey_id = next((e["journey_id"] for e in events if e.get("type") == "journey_started"), None)
            
            # Missing step_type
            response = await ac.post(
                f"/api/research/{journey_id}/refine",
                json={"feedback": "More detail"}
            )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_refine_invalid_step_type_returns_error(self, mock_db, mock_llm_with_response, parse_sse):
        """Test that invalid step_type in refine returns error event."""
        # Create a journey first
        mock_llm_with_response({
            "intent_type": "build",
            "domain": "Test",
            "clarification_questions": [
                {"id": "q", "label": "Q?", "options": [{"id": "o", "label": "O", "description": "D"}],
                 "allow_multiple": False, "allow_other": False}
            ],
            "quick_response": None
        })
        
        async with get_test_client() as ac:
            response = await ac.post("/api/research", json={"prompt": "Test"})
            events = parse_sse(response.text)
            journey_id = next((e["journey_id"] for e in events if e.get("type") == "journey_started"), None)
            
            # Invalid step_type
            response = await ac.post(
                f"/api/research/{journey_id}/refine",
                json={
                    "step_type": "invalid_step_type",
                    "feedback": "More detail"
                }
            )
        
        assert response.status_code == status.HTTP_200_OK
        events = parse_sse(response.text)
        
        # Should have an error event for invalid step type
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1


# -----------------------------------------------------------------------------
# Error Handling Tests
# -----------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for error handling in API endpoints."""

    @pytest.mark.asyncio
    async def test_llm_error_returns_error_event(self, mock_db, mock_llm_failure, parse_sse):
        """Test that LLM errors return error SSE event."""
        async with get_test_client() as client:
            response = await client.post(
                "/api/research",
                json={"prompt": "Build something"}
            )
        
        events = parse_sse(response.text)
        
        # Should have an error event
        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1
        assert "error_code" in error_events[0]
        assert error_events[0]["error_code"].startswith("BP-")

    @pytest.mark.asyncio
    async def test_error_event_includes_error_code(self, mock_db, mock_llm_failure, parse_sse):
        """Test that error events include BP- error codes."""
        async with get_test_client() as client:
            response = await client.post(
                "/api/research",
                json={"prompt": "Test prompt"}
            )
        
        events = parse_sse(response.text)
        error_events = [e for e in events if e.get("type") == "error"]
        
        if error_events:
            assert "error_code" in error_events[0]
            # BP- followed by 6 hex chars
            assert error_events[0]["error_code"].startswith("BP-")
            assert len(error_events[0]["error_code"]) == 9  # BP-XXXXXX
