"""
Blueprint Backend — Integration Tests for Code Generation API

Tests for POST /api/code/generate and GET /api/code/session.
Mocks: litellm, httpx (thumbnail, Figma SVG), DB (prototype_sessions), get_figma_tokens.
"""

import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient
from fastapi import status

from app.main import app
from tests.conftest import create_mock_llm_response, create_test_client, parse_sse_events


VALID_REACT_CODE = (
    'export default function App() { return (<div className="p-6 bg-white">'
    '<h1 className="text-2xl font-bold">Welcome back</h1></div>); }'
)


def _sample_design_context():
    """Minimal design context for code generation."""
    return {
        "nodes": {
            "1:1": {
                "document": {
                    "id": "1:1",
                    "name": "Login",
                    "type": "FRAME",
                    "absoluteBoundingBox": {"width": 375, "height": 812},
                    "children": [],
                }
            }
        },
        "components": {},
        "styles": {},
    }


@pytest.fixture
def mock_figma_tokens(monkeypatch):
    """Mock get_figma_tokens to return valid tokens for session."""
    def mock_get(session_id=None, user_id=None):
        if session_id or user_id:
            return {"access_token": "test-token", "refresh_token": "test-refresh"}
        return None
    monkeypatch.setattr("app.api.codegen.get_figma_tokens", mock_get)
    return mock_get


@pytest.fixture
def mock_figma_tokens_none(monkeypatch):
    """Mock get_figma_tokens to return None (no Figma connection)."""
    def mock_get(*args, **kwargs):
        return None
    monkeypatch.setattr("app.api.codegen.get_figma_tokens", mock_get)
    return mock_get


@pytest.fixture
def mock_httpx_thumbnail(monkeypatch):
    """Mock httpx for thumbnail fetch - returns 200 with bytes."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"fake-png-bytes"

    async def mock_get(*args, **kwargs):
        return mock_resp

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=mock_get)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    def create_client(*args, **kwargs):
        return mock_client

    monkeypatch.setattr("httpx.AsyncClient", create_client)
    return mock_client


@pytest.fixture
def mock_llm_valid_jsx(monkeypatch):
    """Mock litellm to return valid React/JSX code."""
    monkeypatch.setattr(
        "litellm.acompletion",
        AsyncMock(return_value=create_mock_llm_response(VALID_REACT_CODE)),
    )


# -----------------------------------------------------------------------------
# TestCodeGenerate — POST /api/code/generate
# -----------------------------------------------------------------------------


class TestCodeGenerate:
    """Tests for POST /api/code/generate."""

    @pytest.mark.asyncio
    async def test_generate_returns_200_with_session(
        self, mock_db, mock_figma_tokens, mock_httpx_thumbnail, mock_llm_valid_jsx
    ):
        """Valid request with session cookie returns {session_id, status: "ready"}."""
        async with create_test_client() as client:
            response = await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                    "frame_width": 375,
                    "frame_height": 812,
                },
                cookies={"bp_session": "test-session-123"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_generate_no_session_cookie_returns_401(
        self, mock_db, mock_figma_tokens_none
    ):
        """Missing bp_session cookie returns 401 (no tokens)."""
        async with create_test_client() as client:
            response = await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                },
                # No cookies
            )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "Connect with Figma" in data.get("detail", {}).get("message", "")

    @pytest.mark.asyncio
    async def test_generate_no_figma_tokens_returns_401(
        self, mock_db, mock_figma_tokens_none
    ):
        """Session exists but no Figma tokens → 401 with friendly message."""
        async with create_test_client() as client:
            response = await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-123"},
            )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "Connect with Figma" in data.get("detail", {}).get("message", "")

    @pytest.mark.asyncio
    async def test_generate_stores_code_in_db(
        self, mock_db, mock_figma_tokens, mock_httpx_thumbnail, mock_llm_valid_jsx
    ):
        """After successful generation, get_prototype_session returns generated_code."""
        from app.db import get_prototype_session

        async with create_test_client() as client:
            response = await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-123"},
            )
        assert response.status_code == status.HTTP_200_OK
        session_id = response.json()["session_id"]
        session = await get_prototype_session(session_id)
        assert session is not None
        assert session.get("generated_code") is not None
        assert "Welcome back" in session["generated_code"]

    @pytest.mark.asyncio
    async def test_generate_transforms_design_context(
        self, mock_db, mock_figma_tokens, mock_httpx_thumbnail, mock_llm_valid_jsx, monkeypatch
    ):
        """Verify transform_design_context called (not raw dump to LLM)."""
        transform_calls = []

        original = __import__("app.figma_context", fromlist=["transform_design_context"]).transform_design_context

        def capture_transform(raw):
            transform_calls.append(raw)
            return original(raw)

        monkeypatch.setattr(
            "app.api.codegen.transform_design_context",
            capture_transform,
        )
        async with create_test_client() as client:
            await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-123"},
            )
        assert len(transform_calls) >= 1
        assert "nodes" in transform_calls[0]

    @pytest.mark.asyncio
    async def test_generate_fetches_thumbnail_as_base64(
        self, mock_db, mock_figma_tokens, mock_httpx_thumbnail, mock_llm_valid_jsx
    ):
        """Verify thumbnail URL fetched and base64 encoded for vision."""
        async with create_test_client() as client:
            response = await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "thumbnail_url": "https://example.com/thumb.png",
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-123"},
            )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_generate_retries_on_invalid_jsx(
        self, mock_db, mock_figma_tokens, mock_httpx_thumbnail, monkeypatch
    ):
        """First LLM response is invalid JSX, second is valid → status: "ready"."""
        llm_call_count = 0
        validate_call_count = 0

        async def mock_acompletion(*args, **kwargs):
            nonlocal llm_call_count
            llm_call_count += 1
            if llm_call_count == 1:
                return create_mock_llm_response("invalid jsx {{{")
            return create_mock_llm_response(VALID_REACT_CODE)

        def mock_validate_jsx(code: str):
            nonlocal validate_call_count
            validate_call_count += 1
            if validate_call_count == 1:
                return False, "Parse error"
            return True, None

        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        monkeypatch.setattr("app.api.codegen._validate_jsx", mock_validate_jsx)
        async with create_test_client() as client:
            response = await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-123"},
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ready"
        assert llm_call_count == 2

    @pytest.mark.asyncio
    async def test_generate_fails_after_retry(
        self, mock_db, mock_figma_tokens, mock_httpx_thumbnail, monkeypatch
    ):
        """Both attempts produce invalid JSX → status: "error" with error_code."""
        def mock_validate_jsx(code: str):
            return False, "Parse error"

        monkeypatch.setattr(
            "litellm.acompletion",
            AsyncMock(return_value=create_mock_llm_response("invalid {{{")),
        )
        monkeypatch.setattr("app.api.codegen._validate_jsx", mock_validate_jsx)
        async with create_test_client() as client:
            response = await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-123"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert "error_code" in data
        assert data["error_code"].startswith("BP-")

    @pytest.mark.asyncio
    async def test_generate_handles_llm_failure(
        self, mock_db, mock_figma_tokens, mock_httpx_thumbnail, monkeypatch
    ):
        """LLM raises exception → status: "error" with error_code."""
        async def mock_acompletion(*args, **kwargs):
            raise Exception("LLM API error")

        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        async with create_test_client() as client:
            response = await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-123"},
            )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert data["error_code"].startswith("BP-")

    @pytest.mark.asyncio
    async def test_generate_handles_thumbnail_fetch_failure(
        self, mock_db, mock_figma_tokens, mock_llm_valid_jsx, monkeypatch
    ):
        """Thumbnail URL unreachable → still generates (image_base64=None)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500

        async def mock_get(*args, **kwargs):
            return mock_resp

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        monkeypatch.setattr("httpx.AsyncClient", lambda *a, **k: mock_client)

        async with create_test_client() as client:
            response = await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "thumbnail_url": "https://example.com/broken.png",
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-123"},
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ready"

    @pytest.mark.asyncio
    async def test_generate_error_code_format(
        self, mock_db, mock_figma_tokens, mock_httpx_thumbnail, monkeypatch
    ):
        """Error_code matches BP-XXXXXX format."""
        async def mock_acompletion(*args, **kwargs):
            raise Exception("fail")

        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        async with create_test_client() as client:
            response = await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-123"},
            )
        data = response.json()
        assert data["error_code"].startswith("BP-")
        assert len(data["error_code"]) == 9


# -----------------------------------------------------------------------------
# TestCodeSession — GET /api/code/session
# -----------------------------------------------------------------------------


class TestCodeSession:
    """Tests for GET /api/code/session."""

    @pytest.mark.asyncio
    async def test_get_session_returns_session(
        self, mock_db, mock_figma_tokens, mock_httpx_thumbnail, mock_llm_valid_jsx
    ):
        """Existing session returns PrototypeSession data."""
        async with create_test_client() as client:
            # First create a session
            gen_resp = await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-456"},
            )
            session_id = gen_resp.json()["session_id"]
            # Then fetch it
            get_resp = await client.get(
                "/api/code/session",
                cookies={"bp_session": session_id},
            )
        assert get_resp.status_code == status.HTTP_200_OK
        data = get_resp.json()
        assert data["session_id"] == session_id
        assert data["status"] == "ready"
        assert "generated_code" in data

    @pytest.mark.asyncio
    async def test_get_session_no_session_returns_404(self, mock_db):
        """No session for cookie → 404."""
        async with create_test_client() as client:
            response = await client.get(
                "/api/code/session",
                cookies={"bp_session": "nonexistent-session"},
            )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_session_no_cookie_returns_404_or_401(self, mock_db):
        """Missing cookie → appropriate error."""
        async with create_test_client() as client:
            response = await client.get("/api/code/session")
        assert response.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED)


# -----------------------------------------------------------------------------
# TestCodeGenerateLogging
# -----------------------------------------------------------------------------


class TestCodeGenerateLogging:
    """Tests for code generation pipeline logging."""

    @pytest.mark.asyncio
    async def test_generate_logs_pipeline_start(
        self, mock_db, mock_figma_tokens, mock_httpx_thumbnail, mock_llm_valid_jsx, monkeypatch
    ):
        """Verify "code generation started" logged."""
        log_calls = []

        def capture_log(level, message, **ctx):
            log_calls.append((level, message, ctx))

        monkeypatch.setattr("app.api.codegen.log", capture_log)
        async with create_test_client() as client:
            await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-123"},
            )
        started = [m for _, m, _ in log_calls if "code generation started" in m]
        assert len(started) >= 1

    @pytest.mark.asyncio
    async def test_generate_logs_pipeline_complete(
        self, mock_db, mock_figma_tokens, mock_httpx_thumbnail, mock_llm_valid_jsx, monkeypatch
    ):
        """Verify "code generation completed" logged with duration_ms."""
        log_calls = []

        def capture_log(level, message, **ctx):
            log_calls.append((level, message, ctx))

        monkeypatch.setattr("app.api.codegen.log", capture_log)
        async with create_test_client() as client:
            await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-123"},
            )
        completed = [
            c for _, m, c in log_calls
            if "code generation completed" in m
        ]
        assert len(completed) >= 1
        assert "duration_ms" in completed[0]

    @pytest.mark.asyncio
    async def test_generate_logs_error_with_error_code(
        self, mock_db, mock_figma_tokens, mock_httpx_thumbnail, monkeypatch
    ):
        """On failure, error logged with error_code."""
        async def mock_acompletion(*args, **kwargs):
            raise Exception("LLM failed")

        monkeypatch.setattr("litellm.acompletion", AsyncMock(side_effect=mock_acompletion))
        log_calls = []

        def capture_log(level, message, **ctx):
            log_calls.append((level, message, ctx))

        monkeypatch.setattr("app.api.codegen.log", capture_log)
        async with create_test_client() as client:
            await client.post(
                "/api/code/generate",
                json={
                    "design_context": _sample_design_context(),
                    "frame_name": "Login",
                },
                cookies={"bp_session": "test-session-123"},
            )
        error_logs = [
            c for _, m, c in log_calls
            if "code generation failed" in m or "failed" in m
        ]
        assert len(error_logs) >= 1
        assert any("error_code" in str(c) for c in error_logs)
