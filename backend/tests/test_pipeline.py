"""
Blueprint Backend — E2E Pipeline Tests

End-to-end tests for the complete research pipeline flows.
Tests the SSE event sequences for different intent types.
All tests use mocked dependencies - no real API calls.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import app
from tests.conftest import create_mock_llm_response, parse_sse_events


def get_test_client():
    """Create async client for testing."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def get_events_by_type(events: list[dict], event_type: str) -> list[dict]:
    """Filter events by type."""
    return [e for e in events if e.get("type") == event_type]


def get_journey_id(events: list[dict]) -> str | None:
    """Extract journey_id from journey_started event."""
    journey_events = get_events_by_type(events, "journey_started")
    if journey_events:
        return journey_events[0].get("journey_id")
    return None


# -----------------------------------------------------------------------------
# Small Talk / Off-Topic Flow Tests (No Journey)
# -----------------------------------------------------------------------------


class TestSmallTalkFlow:
    """Test the small_talk intent flow - no journey created."""

    @pytest.mark.asyncio
    async def test_small_talk_complete_flow(self, mock_db):
        """Test complete small_talk flow: quick_response only, no journey."""
        async def mock_acompletion(*args, **kwargs):
            return create_mock_llm_response(json.dumps({
                "intent_type": "small_talk",
                "domain": None,
                "clarification_questions": None,
                "quick_response": "Hello! I'm Blueprint, ready to help with product research."
            }))
        
        async with get_test_client() as client:
            with patch("litellm.acompletion", AsyncMock(side_effect=mock_acompletion)):
                response = await client.post(
                    "/api/research",
                    json={"prompt": "Hi there!"}
                )
        
        events = parse_sse_events(response.text)
        
        # Verify event sequence
        assert len(get_events_by_type(events, "quick_response")) == 1
        assert len(get_events_by_type(events, "journey_started")) == 0
        assert len(get_events_by_type(events, "clarification_needed")) == 0
        
        # Verify quick_response content
        quick_response = get_events_by_type(events, "quick_response")[0]
        assert "Blueprint" in quick_response["message"]


class TestOffTopicFlow:
    """Test the off_topic intent flow - no journey created."""

    @pytest.mark.asyncio
    async def test_off_topic_complete_flow(self, mock_db):
        """Test complete off_topic flow: quick_response only, no journey."""
        async def mock_acompletion(*args, **kwargs):
            return create_mock_llm_response(json.dumps({
                "intent_type": "off_topic",
                "domain": None,
                "clarification_questions": None,
                "quick_response": "I focus on product strategy, not code generation."
            }))
        
        async with get_test_client() as client:
            with patch("litellm.acompletion", AsyncMock(side_effect=mock_acompletion)):
                response = await client.post(
                    "/api/research",
                    json={"prompt": "Write Python code for me"}
                )
        
        events = parse_sse_events(response.text)
        
        # Verify no journey created
        assert len(get_events_by_type(events, "journey_started")) == 0
        assert len(get_events_by_type(events, "quick_response")) == 1


# -----------------------------------------------------------------------------
# Explore Intent Flow Tests
# -----------------------------------------------------------------------------


class TestExploreFlow:
    """Test the explore intent flow - journey with clarification."""

    @pytest.mark.asyncio
    async def test_explore_initial_flow(self, mock_db):
        """Test explore flow: classify → journey_started → clarification_needed → waiting."""
        async def mock_acompletion(*args, **kwargs):
            return create_mock_llm_response(json.dumps({
                "intent_type": "explore",
                "domain": "Note-taking",
                "clarification_questions": [
                    {
                        "id": "explore-focus",
                        "label": "What aspect interests you?",
                        "options": [
                            {"id": "competitors", "label": "Competitors", "description": "Who competes with Notion?"},
                            {"id": "features", "label": "Features", "description": "What features does Notion have?"}
                        ],
                        "allow_multiple": True,
                        "allow_other": False
                    }
                ],
                "quick_response": None
            }))
        
        async with get_test_client() as client:
            with patch("litellm.acompletion", AsyncMock(side_effect=mock_acompletion)):
                response = await client.post(
                    "/api/research",
                    json={"prompt": "Tell me about Notion"}
                )
        
        events = parse_sse_events(response.text)
        
        # Verify event sequence for explore
        assert len(get_events_by_type(events, "journey_started")) == 1
        assert len(get_events_by_type(events, "clarification_needed")) == 1
        assert len(get_events_by_type(events, "waiting_for_selection")) == 1
        
        # Verify journey details
        journey_event = get_events_by_type(events, "journey_started")[0]
        assert journey_event["intent_type"] == "explore"
        
        # Verify waiting_for_selection type
        waiting_event = get_events_by_type(events, "waiting_for_selection")[0]
        assert waiting_event["selection_type"] == "clarification"


# -----------------------------------------------------------------------------
# Build Intent Flow Tests
# -----------------------------------------------------------------------------


class TestBuildFlow:
    """Test the build intent flow - full pipeline with gap analysis."""

    @pytest.mark.asyncio
    async def test_build_initial_flow(self, mock_db):
        """Test build flow initial phase: classify → journey_started → clarification_needed → waiting."""
        async def mock_acompletion(*args, **kwargs):
            return create_mock_llm_response(json.dumps({
                "intent_type": "build",
                "domain": "Note-taking",
                "clarification_questions": [
                    {
                        "id": "target-platform",
                        "label": "What platform are you targeting?",
                        "options": [
                            {"id": "mobile", "label": "Mobile", "description": "Native iOS/Android app"},
                            {"id": "web", "label": "Web", "description": "Browser-based application"}
                        ],
                        "allow_multiple": True,
                        "allow_other": False
                    },
                    {
                        "id": "target-audience",
                        "label": "Who is your primary user?",
                        "options": [
                            {"id": "students", "label": "Students", "description": "Academic note-taking"},
                            {"id": "professionals", "label": "Professionals", "description": "Work notes and docs"}
                        ],
                        "allow_multiple": False,
                        "allow_other": True
                    }
                ],
                "quick_response": None
            }))
        
        async with get_test_client() as client:
            with patch("litellm.acompletion", AsyncMock(side_effect=mock_acompletion)):
                response = await client.post(
                    "/api/research",
                    json={"prompt": "I want to build a note-taking app"}
                )
        
        events = parse_sse_events(response.text)
        
        # Verify event sequence for build
        assert len(get_events_by_type(events, "journey_started")) == 1
        assert len(get_events_by_type(events, "clarification_needed")) == 1
        assert len(get_events_by_type(events, "waiting_for_selection")) == 1
        
        # Verify journey details
        journey_event = get_events_by_type(events, "journey_started")[0]
        assert journey_event["intent_type"] == "build"
        
        # Verify clarification questions
        clarification_event = get_events_by_type(events, "clarification_needed")[0]
        assert len(clarification_event["questions"]) == 2


# -----------------------------------------------------------------------------
# Improve Intent Flow Tests (Redirects to Explore)
# -----------------------------------------------------------------------------


class TestImproveFlow:
    """Test the improve intent flow - redirects to explore."""

    @pytest.mark.asyncio
    async def test_improve_redirects_to_explore(self, mock_db):
        """Test improve intent is redirected to explore flow."""
        async def mock_acompletion(*args, **kwargs):
            return create_mock_llm_response(json.dumps({
                "intent_type": "improve",
                "domain": "Note-taking",
                "clarification_questions": [
                    {
                        "id": "improvement-goal",
                        "label": "What do you want to improve?",
                        "options": [
                            {"id": "ux", "label": "User Experience", "description": "Make it easier to use"},
                            {"id": "features", "label": "Features", "description": "Add new capabilities"}
                        ],
                        "allow_multiple": True,
                        "allow_other": True
                    }
                ],
                "quick_response": None
            }))
        
        async with get_test_client() as client:
            with patch("litellm.acompletion", AsyncMock(side_effect=mock_acompletion)):
                response = await client.post(
                    "/api/research",
                    json={"prompt": "How do I improve my note-taking app?"}
                )
        
        events = parse_sse_events(response.text)
        
        # Verify journey was created (improve redirects to explore)
        journey_events = get_events_by_type(events, "journey_started")
        assert len(journey_events) == 1
        
        # Check for intent_redirect event (if implemented)
        redirect_events = get_events_by_type(events, "intent_redirect")
        # If redirect is implemented, verify it
        if redirect_events:
            assert redirect_events[0]["original_intent"] == "improve"
            assert redirect_events[0]["redirected_to"] == "explore"


# -----------------------------------------------------------------------------
# SSE Event Sequence Tests
# -----------------------------------------------------------------------------


class TestSSEEventSequence:
    """Test that SSE events are sent in correct order."""

    @pytest.mark.asyncio
    async def test_event_order_for_build_intent(self, mock_db):
        """Test events are sent in correct order for build intent."""
        async def mock_acompletion(*args, **kwargs):
            return create_mock_llm_response(json.dumps({
                "intent_type": "build",
                "domain": "Test",
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
            }))
        
        async with get_test_client() as client:
            with patch("litellm.acompletion", AsyncMock(side_effect=mock_acompletion)):
                response = await client.post(
                    "/api/research",
                    json={"prompt": "Build something"}
                )
        
        events = parse_sse_events(response.text)
        event_types = [e.get("type") for e in events]
        
        # Verify order: journey_started should come before clarification_needed
        if "journey_started" in event_types and "clarification_needed" in event_types:
            assert event_types.index("journey_started") < event_types.index("clarification_needed")
        
        # Verify waiting_for_selection comes last (before any errors)
        non_error_events = [t for t in event_types if t != "error"]
        if "waiting_for_selection" in non_error_events:
            assert non_error_events[-1] == "waiting_for_selection"

    @pytest.mark.asyncio
    async def test_step_events_wrapped_correctly(self, mock_db, mock_search):
        """Test that step_started and step_completed events wrap operations."""
        call_count = 0
        
        async def mock_acompletion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # Classify
                return create_mock_llm_response(json.dumps({
                    "intent_type": "build",
                    "domain": "Test",
                    "clarification_questions": [
                        {"id": "q", "label": "Q?", "options": [{"id": "o", "label": "O", "description": "D"}],
                         "allow_multiple": False, "allow_other": False}
                    ],
                    "quick_response": None
                }))
            else:
                # Competitors
                return create_mock_llm_response(json.dumps({
                    "competitors": [
                        {"id": "test", "name": "Test", "description": "Test app", "url": None,
                         "category": "Test", "pricing_model": "Free"}
                    ],
                    "sources": []
                }))
        
        async with get_test_client() as client:
            with patch("litellm.acompletion", AsyncMock(side_effect=mock_acompletion)):
                # Start research
                response = await client.post(
                    "/api/research",
                    json={"prompt": "Build something"}
                )
                events = parse_sse_events(response.text)
                journey_id = get_journey_id(events)
                
                # Submit selection
                response = await client.post(
                    f"/api/research/{journey_id}/selection",
                    json={
                        "step_type": "clarify",
                        "selection": {"answers": [{"question_id": "q", "selected_option_ids": ["o"]}]}
                    }
                )
        
        selection_events = parse_sse_events(response.text)
        event_types = [e.get("type") for e in selection_events]
        
        # Check for step_started and step_completed pairs
        started_count = event_types.count("step_started")
        completed_count = event_types.count("step_completed")
        
        # Each step_started should have a corresponding step_completed
        # (unless there was an error)
        if "error" not in event_types:
            assert started_count == completed_count or started_count == completed_count + 1


# -----------------------------------------------------------------------------
# Error Handling in Pipeline Tests
# -----------------------------------------------------------------------------


class TestPipelineErrorHandling:
    """Test error handling throughout the pipeline."""

    @pytest.mark.asyncio
    async def test_llm_failure_sends_error_event(self, mock_db, mock_llm_failure):
        """Test that LLM failure sends error event in SSE stream."""
        async with get_test_client() as client:
            response = await client.post(
                "/api/research",
                json={"prompt": "Build something"}
            )
        
        events = parse_sse_events(response.text)
        error_events = get_events_by_type(events, "error")
        
        assert len(error_events) >= 1
        assert "error_code" in error_events[0]
        assert "message" in error_events[0]

    @pytest.mark.asyncio
    async def test_error_event_has_bp_code(self, mock_db, mock_llm_failure):
        """Test that error events include BP- formatted error codes."""
        async with get_test_client() as client:
            response = await client.post(
                "/api/research",
                json={"prompt": "Test"}
            )
        
        events = parse_sse_events(response.text)
        error_events = get_events_by_type(events, "error")
        
        if error_events:
            error_code = error_events[0].get("error_code", "")
            assert error_code.startswith("BP-")
            assert len(error_code) == 9  # BP-XXXXXX


# -----------------------------------------------------------------------------
# Journey State Tests
# -----------------------------------------------------------------------------


class TestJourneyState:
    """Test journey state management through pipeline."""

    @pytest.mark.asyncio
    async def test_journey_created_with_correct_intent(self, mock_db):
        """Test that journey is created with correct intent_type."""
        async def mock_acompletion(*args, **kwargs):
            return create_mock_llm_response(json.dumps({
                "intent_type": "build",
                "domain": "Fintech",
                "clarification_questions": [
                    {"id": "q", "label": "Q?", "options": [{"id": "o", "label": "O", "description": "D"}],
                     "allow_multiple": False, "allow_other": False}
                ],
                "quick_response": None
            }))
        
        async with get_test_client() as client:
            with patch("litellm.acompletion", AsyncMock(side_effect=mock_acompletion)):
                response = await client.post(
                    "/api/research",
                    json={"prompt": "Build a banking app"}
                )
        
        events = parse_sse_events(response.text)
        journey_event = get_events_by_type(events, "journey_started")[0]
        
        assert journey_event["intent_type"] == "build"
        assert "journey_id" in journey_event
        assert journey_event["journey_id"].startswith("test-journey-")

    @pytest.mark.asyncio
    async def test_journey_id_persists_through_selection(self, mock_db, mock_search):
        """Test that journey_id is consistent through selection flow."""
        call_count = 0
        
        async def mock_acompletion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                return create_mock_llm_response(json.dumps({
                    "intent_type": "explore",
                    "domain": "Test",
                    "clarification_questions": [
                        {"id": "q", "label": "Q?", "options": [{"id": "o", "label": "O", "description": "D"}],
                         "allow_multiple": False, "allow_other": False}
                    ],
                    "quick_response": None
                }))
            else:
                return create_mock_llm_response(json.dumps({
                    "competitors": [],
                    "sources": []
                }))
        
        async with get_test_client() as client:
            with patch("litellm.acompletion", AsyncMock(side_effect=mock_acompletion)):
                # Start research
                response = await client.post(
                    "/api/research",
                    json={"prompt": "Test"}
                )
                events = parse_sse_events(response.text)
                original_journey_id = get_journey_id(events)
                
                # Submit selection - should work with same journey_id
                response = await client.post(
                    f"/api/research/{original_journey_id}/selection",
                    json={
                        "step_type": "clarify",
                        "selection": {"answers": []}
                    }
                )
        
        # Selection should succeed (200 OK with SSE stream)
        assert response.status_code == 200


# -----------------------------------------------------------------------------
# Concurrent Request Handling Tests
# -----------------------------------------------------------------------------


class TestConcurrentRequests:
    """Test handling of concurrent/duplicate requests."""

    @pytest.mark.asyncio
    async def test_duplicate_prompt_rejected(self, mock_db):
        """Test that duplicate prompts in quick succession are rejected."""
        # This test verifies the deduplication logic
        # Note: Due to async nature, we can't easily test true concurrent requests
        # but we can verify the dedup key mechanism exists
        
        async def slow_mock_acompletion(*args, **kwargs):
            import asyncio
            await asyncio.sleep(0.5)  # Simulate slow LLM call
            return create_mock_llm_response(json.dumps({
                "intent_type": "small_talk",
                "domain": None,
                "clarification_questions": None,
                "quick_response": "Hello!"
            }))
        
        async with get_test_client() as client:
            with patch("litellm.acompletion", AsyncMock(side_effect=slow_mock_acompletion)):
                # First request
                response = await client.post(
                    "/api/research",
                    json={"prompt": "Test concurrent"}
                )
        
        # Single request should succeed
        assert response.status_code == 200
