"""
Blueprint Backend — Tests for Code Generation (LLM vision, code fence stripping)

Tests for call_llm_vision and strip_code_fences. Uses mocked litellm — no real API calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm import call_llm_vision, strip_code_fences, LLMError
from app.config import CODE_GEN_MODEL
from tests.conftest import create_mock_llm_response


# -----------------------------------------------------------------------------
# strip_code_fences Tests
# -----------------------------------------------------------------------------


class TestStripCodeFences:
    """Tests for strip_code_fences (JSX/TSX/JavaScript extraction)."""

    def test_strip_jsx_fences(self):
        """```jsx\ncode\n``` → code."""
        text = "```jsx\nconst x = 1;\n```"
        assert strip_code_fences(text) == "const x = 1;"

    def test_strip_tsx_fences(self):
        """```tsx\ncode\n``` → code."""
        text = "```tsx\nconst x: number = 1;\n```"
        assert strip_code_fences(text) == "const x: number = 1;"

    def test_strip_javascript_fences(self):
        """```javascript\ncode\n``` → code."""
        text = "```javascript\nfunction foo() {}\n```"
        assert strip_code_fences(text) == "function foo() {}"

    def test_strip_plain_fences(self):
        """```\ncode\n``` → code."""
        text = "```\n<div>Hello</div>\n```"
        assert strip_code_fences(text) == "<div>Hello</div>"

    def test_no_fences_returns_original(self):
        """Plain text returned as-is."""
        text = "export default function App() { return <div>Hi</div>; }"
        assert strip_code_fences(text) == text

    def test_empty_string(self):
        """Empty string handled."""
        assert strip_code_fences("") == ""
        assert strip_code_fences("   ") == ""

    def test_preserves_inner_backticks(self):
        """Code with backticks inside not broken."""
        text = "```jsx\nconst s = `template ${x}`;\n```"
        assert strip_code_fences(text) == "const s = `template ${x}`;"


# -----------------------------------------------------------------------------
# call_llm_vision Tests (mocked litellm)
# -----------------------------------------------------------------------------


class TestCallLlmVision:
    """Tests for call_llm_vision with mocked litellm."""

    @pytest.mark.asyncio
    async def test_vision_call_text_only(self, mock_llm_vision):
        """Messages without image, returns content."""
        messages = [{"role": "user", "content": "Generate React code"}]
        result = await call_llm_vision(messages, image_base64=None, session_id="s1")
        assert "App" in result or "div" in result
        mock_llm_vision.assert_called_once()

    @pytest.mark.asyncio
    async def test_vision_call_with_image(self, mock_llm_vision):
        """Image_base64 provided, message content becomes list with image_url part."""
        messages = [{"role": "user", "content": "Generate from this design"}]
        await call_llm_vision(messages, image_base64="abc123", session_id="s1")
        call_kwargs = mock_llm_vision.call_args[1]
        msg_list = call_kwargs["messages"]
        user_msg = next((m for m in msg_list if m.get("role") == "user"), None)
        assert user_msg is not None
        content = user_msg["content"]
        assert isinstance(content, list)
        has_image = any(
            p.get("type") == "image_url" for p in content if isinstance(p, dict)
        )
        assert has_image

    @pytest.mark.asyncio
    async def test_vision_call_uses_code_gen_model(self, mock_llm_vision):
        """Verify model kwarg is CODE_GEN_MODEL."""
        await call_llm_vision(
            [{"role": "user", "content": "test"}],
            image_base64=None,
            session_id="s1",
        )
        call_kwargs = mock_llm_vision.call_args[1]
        assert call_kwargs["model"] == CODE_GEN_MODEL

    @pytest.mark.asyncio
    async def test_vision_call_no_response_format(self, mock_llm_vision):
        """Verify response_format NOT passed (Gemini conflict)."""
        await call_llm_vision(
            [{"role": "user", "content": "test"}],
            image_base64=None,
            session_id="s1",
        )
        call_kwargs = mock_llm_vision.call_args[1]
        assert "response_format" not in call_kwargs

    @pytest.mark.asyncio
    async def test_vision_call_empty_content_returns_empty(self, monkeypatch):
        """Empty response content returns empty string."""
        async def mock_acompletion(*args, **kwargs):
            return create_mock_llm_response("")

        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        result = await call_llm_vision(
            [{"role": "user", "content": "test"}],
            image_base64=None,
            session_id="s1",
        )
        assert result == ""

    @pytest.mark.asyncio
    async def test_vision_call_logs_on_success(self, mock_llm_vision, monkeypatch):
        """Verify log called with correct args on success."""
        log_calls = []

        def capture_log(level, message, **ctx):
            log_calls.append((level, message, ctx))

        monkeypatch.setattr("app.llm.log", capture_log)
        await call_llm_vision(
            [{"role": "user", "content": "test"}],
            image_base64=None,
            session_id="s1",
        )
        success_logs = [
            (l, m, c)
            for l, m, c in log_calls
            if "vision call succeeded" in m or "vision call started" in m
        ]
        assert len(success_logs) >= 1

    @pytest.mark.asyncio
    async def test_vision_call_logs_on_failure(self, monkeypatch):
        """Verify error logged with error_code on failure."""
        async def mock_acompletion(*args, **kwargs):
            raise Exception("API error")

        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        log_calls = []

        def capture_log(level, message, **ctx):
            log_calls.append((level, message, ctx))

        monkeypatch.setattr("app.llm.log", capture_log)
        with pytest.raises(LLMError):
            await call_llm_vision(
                [{"role": "user", "content": "test"}],
                image_base64=None,
                session_id="s1",
            )
        error_logs = [
            (l, m, c)
            for l, m, c in log_calls
            if "vision call failed" in m or "failed" in m
        ]
        assert len(error_logs) >= 1
        # At least one should have error_code
        has_error_code = any("error_code" in str(c) for _, _, c in error_logs)
        assert has_error_code
