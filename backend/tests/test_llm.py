"""
Blueprint Backend — LLM Module Unit Tests

Tests for llm.py: fallback chain, retry logic, validation, error handling.
All tests use mocked LLM calls - no real API requests.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from app.llm import (
    call_llm,
    call_llm_structured,
    LLMError,
    LLMValidationError,
    _strip_code_fences,
    _is_rate_limit_error,
    _inject_system_prompt,
    RATE_LIMIT_COOLDOWN_SECONDS,
)
from app.models import ClassifyResult, CompetitorList, CompetitorInfo
from tests.conftest import create_mock_llm_response, MockLLMResponse


# -----------------------------------------------------------------------------
# Helper Function Tests
# -----------------------------------------------------------------------------


class TestStripCodeFences:
    """Tests for _strip_code_fences helper."""

    def test_strips_json_code_fence(self):
        text = '```json\n{"key": "value"}\n```'
        assert _strip_code_fences(text) == '{"key": "value"}'

    def test_strips_plain_code_fence(self):
        text = '```\n{"key": "value"}\n```'
        assert _strip_code_fences(text) == '{"key": "value"}'

    def test_handles_no_code_fence(self):
        text = '{"key": "value"}'
        assert _strip_code_fences(text) == '{"key": "value"}'

    def test_handles_whitespace(self):
        text = '  ```json\n{"key": "value"}\n```  '
        assert _strip_code_fences(text) == '{"key": "value"}'

    def test_handles_empty_string(self):
        assert _strip_code_fences("") == ""

    def test_handles_none(self):
        assert _strip_code_fences(None) is None

    def test_handles_multiline_json(self):
        text = '```json\n{\n  "key": "value",\n  "nested": {"a": 1}\n}\n```'
        expected = '{\n  "key": "value",\n  "nested": {"a": 1}\n}'
        assert _strip_code_fences(text) == expected


class TestIsRateLimitError:
    """Tests for _is_rate_limit_error helper."""

    def test_detects_rate_limit(self):
        assert _is_rate_limit_error(Exception("rate_limit_exceeded"))
        assert _is_rate_limit_error(Exception("Error 429: Too many requests"))
        assert _is_rate_limit_error(Exception("RATE_LIMIT error"))

    def test_detects_quota_error(self):
        assert _is_rate_limit_error(Exception("quota exceeded"))
        assert _is_rate_limit_error(Exception("resource_exhausted"))

    def test_detects_timeout(self):
        assert _is_rate_limit_error(Exception("Request timed out"))
        assert _is_rate_limit_error(Exception("timeout"))

    def test_non_rate_limit_errors(self):
        assert not _is_rate_limit_error(Exception("Invalid API key"))
        assert not _is_rate_limit_error(Exception("Model not found"))
        assert not _is_rate_limit_error(Exception("Internal server error"))


class TestInjectSystemPrompt:
    """Tests for _inject_system_prompt helper."""

    def test_injects_system_prompt(self):
        messages = [{"role": "user", "content": "Hello"}]
        result = _inject_system_prompt(messages)
        
        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert "Blueprint" in result[0]["content"]
        assert result[1] == messages[0]

    def test_does_not_mutate_input(self):
        messages = [{"role": "user", "content": "Hello"}]
        original_len = len(messages)
        _inject_system_prompt(messages)
        assert len(messages) == original_len


# -----------------------------------------------------------------------------
# call_llm Tests
# -----------------------------------------------------------------------------


class TestCallLLM:
    """Tests for call_llm function."""

    @pytest.mark.asyncio
    async def test_successful_call(self, mock_llm, mock_db):
        """Test successful LLM call returns content."""
        response_content = '{"test": "response"}'
        mock_llm.side_effect = None
        mock_llm.return_value = create_mock_llm_response(response_content)
        
        result = await call_llm([{"role": "user", "content": "test"}])
        
        assert result == response_content
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_on_rate_limit(self, mock_db, monkeypatch):
        """Test fallback to next provider on rate limit error."""
        call_count = 0
        
        async def mock_acompletion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 rate_limit_exceeded")
            return create_mock_llm_response('{"success": true}')
        
        mock = AsyncMock(side_effect=mock_acompletion)
        monkeypatch.setattr("litellm.acompletion", mock)
        
        result = await call_llm([{"role": "user", "content": "test"}])
        
        assert result == '{"success": true}'
        assert call_count == 2  # First provider failed, second succeeded

    @pytest.mark.asyncio
    async def test_all_providers_fail_raises_llm_error(self, mock_llm_failure, mock_db):
        """Test LLMError raised when all providers fail."""
        with pytest.raises(LLMError, match="All LLM providers failed"):
            await call_llm([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_empty_content_triggers_fallback(self, mock_db, monkeypatch):
        """Test that empty content triggers fallback to next provider."""
        call_count = 0
        
        async def mock_acompletion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call returns empty content
                return MockLLMResponse(
                    choices=[type('Choice', (), {'message': type('Msg', (), {'content': '', 'reasoning_content': None})()})()]
                )
            return create_mock_llm_response('{"result": "success"}')
        
        mock = AsyncMock(side_effect=mock_acompletion)
        monkeypatch.setattr("litellm.acompletion", mock)
        
        result = await call_llm([{"role": "user", "content": "test"}])
        
        assert result == '{"result": "success"}'
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_journey_id_passed_for_logging(self, mock_llm, mock_db):
        """Test that journey_id is properly passed (for logging correlation)."""
        mock_llm.side_effect = None
        mock_llm.return_value = create_mock_llm_response('{"test": true}')
        
        result = await call_llm(
            [{"role": "user", "content": "test"}],
            journey_id="test-journey-123"
        )
        
        assert result == '{"test": true}'


# -----------------------------------------------------------------------------
# call_llm_structured Tests
# -----------------------------------------------------------------------------


class TestCallLLMStructured:
    """Tests for call_llm_structured function."""

    @pytest.mark.asyncio
    async def test_returns_validated_model(self, mock_db, monkeypatch):
        """Test successful parsing and validation of structured response."""
        response_data = {
            "intent_type": "build",
            "domain": "Note-taking",
            "clarification_questions": None,
            "quick_response": None,
        }
        
        async def mock_acompletion(*args, **kwargs):
            return create_mock_llm_response(json.dumps(response_data))
        
        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        
        result = await call_llm_structured(
            [{"role": "user", "content": "test"}],
            ClassifyResult
        )
        
        assert isinstance(result, ClassifyResult)
        assert result.intent_type == "build"
        assert result.domain == "Note-taking"

    @pytest.mark.asyncio
    async def test_strips_code_fences_before_parsing(self, mock_db, monkeypatch):
        """Test that markdown code fences are stripped before JSON parsing."""
        response_data = {
            "intent_type": "explore",
            "domain": "Fintech",
            "clarification_questions": None,
            "quick_response": None,
        }
        
        async def mock_acompletion(*args, **kwargs):
            return create_mock_llm_response(f"```json\n{json.dumps(response_data)}\n```")
        
        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        
        result = await call_llm_structured(
            [{"role": "user", "content": "test"}],
            ClassifyResult
        )
        
        assert isinstance(result, ClassifyResult)
        assert result.intent_type == "explore"

    @pytest.mark.asyncio
    async def test_retry_on_validation_error(self, mock_db, monkeypatch):
        """Test that validation errors trigger a retry with fix prompt."""
        call_count = 0
        
        async def mock_acompletion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call returns invalid JSON
                return create_mock_llm_response('{"invalid": "missing required fields"}')
            # Second call (retry) returns valid JSON
            return create_mock_llm_response(json.dumps({
                "intent_type": "build",
                "domain": "Test",
                "clarification_questions": None,
                "quick_response": None,
            }))
        
        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        
        result = await call_llm_structured(
            [{"role": "user", "content": "test"}],
            ClassifyResult
        )
        
        assert isinstance(result, ClassifyResult)
        assert call_count == 2  # Initial + retry

    @pytest.mark.asyncio
    async def test_raises_validation_error_after_retry_fails(self, mock_db, monkeypatch):
        """Test LLMValidationError raised when retry also fails validation."""
        async def mock_acompletion(*args, **kwargs):
            # Always return invalid JSON
            return create_mock_llm_response('{"invalid": "data"}')
        
        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        
        with pytest.raises(LLMValidationError) as exc_info:
            await call_llm_structured(
                [{"role": "user", "content": "test"}],
                ClassifyResult
            )
        
        assert "invalid" in exc_info.value.raw_output

    @pytest.mark.asyncio
    async def test_handles_malformed_json(self, mock_db, monkeypatch):
        """Test handling of completely malformed JSON triggers retry."""
        call_count = 0
        
        async def mock_acompletion(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return create_mock_llm_response('not valid json at all {{{')
            return create_mock_llm_response(json.dumps({
                "intent_type": "small_talk",
                "domain": None,
                "clarification_questions": None,
                "quick_response": "Hello!",
            }))
        
        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        
        result = await call_llm_structured(
            [{"role": "user", "content": "test"}],
            ClassifyResult
        )
        
        assert isinstance(result, ClassifyResult)
        assert result.intent_type == "small_talk"

    @pytest.mark.asyncio
    async def test_complex_model_validation(self, mock_db, monkeypatch):
        """Test validation with complex nested model (CompetitorList)."""
        response_data = {
            "competitors": [
                {
                    "id": "notion",
                    "name": "Notion",
                    "description": "All-in-one workspace",
                    "url": "https://notion.so",
                    "category": "Productivity",
                    "pricing_model": "Freemium",
                }
            ],
            "sources": ["https://example.com"],
        }
        
        async def mock_acompletion(*args, **kwargs):
            return create_mock_llm_response(json.dumps(response_data))
        
        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        
        result = await call_llm_structured(
            [{"role": "user", "content": "test"}],
            CompetitorList
        )
        
        assert isinstance(result, CompetitorList)
        assert len(result.competitors) == 1
        assert result.competitors[0].name == "Notion"


# -----------------------------------------------------------------------------
# Rate Limiting and Cooldown Tests
# -----------------------------------------------------------------------------


class TestRateLimitCooldown:
    """Tests for rate limit cooldown behavior."""

    @pytest.mark.asyncio
    async def test_rate_limited_provider_skipped(self, mock_db, monkeypatch):
        """Test that rate-limited providers are skipped."""
        import app.llm as llm_module
        import time
        
        # Manually mark first provider as rate-limited
        llm_module._rate_limited_until["gemini/gemini-3-flash-preview"] = (
            time.monotonic() + RATE_LIMIT_COOLDOWN_SECONDS
        )
        
        providers_tried = []
        
        async def mock_acompletion(model, *args, **kwargs):
            providers_tried.append(model)
            return create_mock_llm_response('{"success": true}')
        
        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        
        await call_llm([{"role": "user", "content": "test"}])
        
        # First provider should have been skipped
        assert "gemini/gemini-3-flash-preview" not in providers_tried
        assert len(providers_tried) == 1

    @pytest.mark.asyncio
    async def test_cooldown_clears_when_all_providers_blocked(self, mock_db, monkeypatch):
        """Test that cooldowns are cleared when all providers are blocked."""
        import app.llm as llm_module
        import time
        from app.config import LLM_CONFIG
        
        # Mark ALL providers as rate-limited
        for provider in LLM_CONFIG["fallback_chain"]:
            llm_module._rate_limited_until[provider] = (
                time.monotonic() + RATE_LIMIT_COOLDOWN_SECONDS
            )
        
        async def mock_acompletion(*args, **kwargs):
            return create_mock_llm_response('{"success": true}')
        
        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        
        # Should clear cooldowns and retry
        result = await call_llm([{"role": "user", "content": "test"}])
        
        assert result == '{"success": true}'
        # Cooldowns should have been cleared
        assert len(llm_module._rate_limited_until) == 0
