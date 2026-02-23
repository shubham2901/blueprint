"""
Blueprint Backend — Search Module Unit Tests

Tests for search.py: provider fallback, result parsing, error handling.
All tests use mocked HTTP calls - no real API requests.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.search import (
    search,
    search_reddit,
    SearchResult,
    SearchError,
    _tavily_search,
    _serper_search,
    _duckduckgo_search,
)


# -----------------------------------------------------------------------------
# SearchResult Tests
# -----------------------------------------------------------------------------


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_creates_search_result(self):
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet"
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"


# -----------------------------------------------------------------------------
# Tavily Search Tests
# -----------------------------------------------------------------------------


class TestTavilySearch:
    """Tests for _tavily_search function."""

    @pytest.mark.asyncio
    async def test_successful_tavily_search(self, monkeypatch):
        """Test successful Tavily API response parsing."""
        mock_response_data = {
            "results": [
                {
                    "title": "Notion vs Obsidian",
                    "url": "https://example.com/comparison",
                    "content": "A detailed comparison of note-taking apps.",
                },
                {
                    "title": "Best Note Apps 2024",
                    "url": "https://example.com/best-apps",
                    "content": "Top note-taking applications reviewed.",
                },
            ]
        }

        async def mock_post(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = mock_response_data
            return mock_resp

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.post = AsyncMock(side_effect=mock_post)
            mock_client.return_value = mock_instance

            results = await _tavily_search("note-taking apps", num_results=5)

        assert len(results) == 2
        assert results[0].title == "Notion vs Obsidian"
        assert results[0].url == "https://example.com/comparison"
        assert "comparison" in results[0].snippet

    @pytest.mark.asyncio
    async def test_tavily_search_handles_http_error(self, monkeypatch):
        """Test that HTTP errors raise SearchError."""
        async def mock_post(*args, **kwargs):
            raise httpx.HTTPError("Connection failed")

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.post = AsyncMock(side_effect=mock_post)
            mock_client.return_value = mock_instance

            with pytest.raises(SearchError):
                await _tavily_search("test query")

    @pytest.mark.asyncio
    async def test_tavily_search_handles_empty_results(self, monkeypatch):
        """Test handling of empty results from Tavily."""
        mock_response_data = {"results": []}

        async def mock_post(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = mock_response_data
            return mock_resp

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.post = AsyncMock(side_effect=mock_post)
            mock_client.return_value = mock_instance

            results = await _tavily_search("obscure query")

        assert len(results) == 0


# -----------------------------------------------------------------------------
# Serper Search Tests
# -----------------------------------------------------------------------------


class TestSerperSearch:
    """Tests for _serper_search function."""

    @pytest.mark.asyncio
    async def test_successful_serper_search(self, monkeypatch):
        """Test successful Serper API response parsing."""
        mock_response_data = {
            "organic": [
                {
                    "title": "Serper Result 1",
                    "link": "https://serper.example.com/1",
                    "snippet": "First serper result snippet.",
                },
                {
                    "title": "Serper Result 2",
                    "link": "https://serper.example.com/2",
                    "snippet": "Second serper result snippet.",
                },
            ]
        }

        async def mock_post(*args, **kwargs):
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = mock_response_data
            return mock_resp

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.post = AsyncMock(side_effect=mock_post)
            mock_client.return_value = mock_instance

            results = await _serper_search("test query", num_results=5)

        assert len(results) == 2
        assert results[0].title == "Serper Result 1"
        assert results[0].url == "https://serper.example.com/1"

    @pytest.mark.asyncio
    async def test_serper_search_handles_http_error(self, monkeypatch):
        """Test that HTTP errors raise SearchError."""
        async def mock_post(*args, **kwargs):
            raise httpx.HTTPError("API error")

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.post = AsyncMock(side_effect=mock_post)
            mock_client.return_value = mock_instance

            with pytest.raises(SearchError):
                await _serper_search("test query")


# -----------------------------------------------------------------------------
# DuckDuckGo Search Tests
# -----------------------------------------------------------------------------


class TestDuckDuckGoSearch:
    """Tests for _duckduckgo_search function."""

    @pytest.mark.asyncio
    async def test_successful_ddg_search(self, monkeypatch):
        """Test successful DuckDuckGo search parsing."""
        mock_results = [
            {"title": "DDG Result 1", "href": "https://ddg.example.com/1", "body": "DDG snippet 1"},
            {"title": "DDG Result 2", "href": "https://ddg.example.com/2", "body": "DDG snippet 2"},
        ]

        mock_ddgs = MagicMock()
        mock_ddgs.text.return_value = mock_results

        with patch("app.search.DDGS", return_value=mock_ddgs):
            results = await _duckduckgo_search("test query", num_results=5)

        assert len(results) == 2
        assert results[0].title == "DDG Result 1"
        assert results[0].url == "https://ddg.example.com/1"

    @pytest.mark.asyncio
    async def test_ddg_search_handles_exception(self, monkeypatch):
        """Test that exceptions raise SearchError."""
        mock_ddgs = MagicMock()
        mock_ddgs.text.side_effect = Exception("DDG rate limited")

        with patch("app.search.DDGS", return_value=mock_ddgs):
            with pytest.raises(SearchError):
                await _duckduckgo_search("test query")


# -----------------------------------------------------------------------------
# Main Search Function Tests
# -----------------------------------------------------------------------------


class TestSearch:
    """Tests for main search function with fallback chain."""

    @pytest.mark.asyncio
    async def test_search_uses_tavily_first(self, monkeypatch):
        """Test that search uses Tavily as primary provider."""
        tavily_results = [
            SearchResult(title="Tavily Result", url="https://tavily.example.com", snippet="From Tavily")
        ]

        async def mock_tavily(*args, **kwargs):
            return tavily_results

        monkeypatch.setattr("app.search._tavily_search", AsyncMock(side_effect=mock_tavily))

        results = await search("test query")

        assert len(results) == 1
        assert results[0].title == "Tavily Result"

    @pytest.mark.asyncio
    async def test_search_falls_back_to_serper(self, monkeypatch):
        """Test fallback to Serper when Tavily fails."""
        serper_results = [
            SearchResult(title="Serper Result", url="https://serper.example.com", snippet="From Serper")
        ]

        async def mock_tavily(*args, **kwargs):
            raise SearchError("Tavily failed")

        async def mock_serper(*args, **kwargs):
            return serper_results

        monkeypatch.setattr("app.search._tavily_search", AsyncMock(side_effect=mock_tavily))
        monkeypatch.setattr("app.search._serper_search", AsyncMock(side_effect=mock_serper))
        # Ensure serper_api_key is set so fallback is attempted
        monkeypatch.setattr("app.search.settings.serper_api_key", "test-serper-key")

        results = await search("test query")

        assert len(results) == 1
        assert results[0].title == "Serper Result"

    @pytest.mark.asyncio
    async def test_search_falls_back_to_ddg(self, monkeypatch):
        """Test fallback to DuckDuckGo when Tavily and Serper fail."""
        ddg_results = [
            SearchResult(title="DDG Result", url="https://ddg.example.com", snippet="From DDG")
        ]

        async def mock_tavily(*args, **kwargs):
            raise SearchError("Tavily failed")

        async def mock_serper(*args, **kwargs):
            raise SearchError("Serper failed")

        async def mock_ddg(*args, **kwargs):
            return ddg_results

        monkeypatch.setattr("app.search._tavily_search", AsyncMock(side_effect=mock_tavily))
        monkeypatch.setattr("app.search._serper_search", AsyncMock(side_effect=mock_serper))
        monkeypatch.setattr("app.search._duckduckgo_search", AsyncMock(side_effect=mock_ddg))
        # Need to ensure serper_api_key is set for fallback to be attempted
        monkeypatch.setattr("app.search.settings.serper_api_key", "test-key")

        results = await search("test query")

        assert len(results) == 1
        assert results[0].title == "DDG Result"

    @pytest.mark.asyncio
    async def test_search_returns_empty_on_all_failures(self, monkeypatch):
        """Test that search returns empty list when all providers fail."""
        async def mock_fail(*args, **kwargs):
            raise SearchError("Failed")

        monkeypatch.setattr("app.search._tavily_search", AsyncMock(side_effect=mock_fail))
        monkeypatch.setattr("app.search._serper_search", AsyncMock(side_effect=mock_fail))
        monkeypatch.setattr("app.search._duckduckgo_search", AsyncMock(side_effect=mock_fail))
        monkeypatch.setattr("app.search.settings.serper_api_key", "test-key")

        results = await search("test query")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_skips_serper_without_api_key(self, monkeypatch):
        """Test that Serper is skipped when no API key is configured."""
        ddg_results = [
            SearchResult(title="DDG Result", url="https://ddg.example.com", snippet="From DDG")
        ]

        async def mock_tavily(*args, **kwargs):
            raise SearchError("Tavily failed")

        async def mock_ddg(*args, **kwargs):
            return ddg_results

        serper_mock = AsyncMock()

        monkeypatch.setattr("app.search._tavily_search", AsyncMock(side_effect=mock_tavily))
        monkeypatch.setattr("app.search._serper_search", serper_mock)
        monkeypatch.setattr("app.search._duckduckgo_search", AsyncMock(side_effect=mock_ddg))
        monkeypatch.setattr("app.search.settings.serper_api_key", "")  # No API key

        results = await search("test query")

        # Serper should not have been called
        serper_mock.assert_not_called()
        assert results[0].title == "DDG Result"


# -----------------------------------------------------------------------------
# Reddit Search Tests
# -----------------------------------------------------------------------------


class TestSearchReddit:
    """Tests for search_reddit function."""

    @pytest.mark.asyncio
    async def test_reddit_search_adds_site_prefix(self, monkeypatch):
        """Test that Reddit search adds site:reddit.com prefix."""
        captured_query = None

        async def mock_search(query, num_results=10, journey_id=None):
            nonlocal captured_query
            captured_query = query
            return []

        monkeypatch.setattr("app.search.search", AsyncMock(side_effect=mock_search))

        await search_reddit("notion alternatives")

        assert captured_query == "site:reddit.com notion alternatives"

    @pytest.mark.asyncio
    async def test_reddit_search_passes_num_results(self, monkeypatch):
        """Test that num_results is passed correctly."""
        captured_num_results = None

        async def mock_search(query, num_results=10, journey_id=None):
            nonlocal captured_num_results
            captured_num_results = num_results
            return []

        monkeypatch.setattr("app.search.search", AsyncMock(side_effect=mock_search))

        await search_reddit("test", num_results=3)

        assert captured_num_results == 3

    @pytest.mark.asyncio
    async def test_reddit_search_passes_journey_id(self, monkeypatch):
        """Test that journey_id is passed for logging correlation."""
        captured_journey_id = None

        async def mock_search(query, num_results=10, journey_id=None):
            nonlocal captured_journey_id
            captured_journey_id = journey_id
            return []

        monkeypatch.setattr("app.search.search", AsyncMock(side_effect=mock_search))

        await search_reddit("test", journey_id="journey-123")

        assert captured_journey_id == "journey-123"
