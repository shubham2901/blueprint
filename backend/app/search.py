"""
Blueprint Backend — Web Search

Tavily (primary) → Serper (fallback) → DuckDuckGo (last-resort).
Uses httpx for Tavily and Serper; duckduckgo-search for DDG.
"""

import asyncio
import time
from dataclasses import dataclass

import httpx
from duckduckgo_search import DDGS

from app.config import settings, log, generate_error_code


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchError(Exception):
    pass


DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; Blueprint/1.0; +https://github.com/blueprint)"


async def search(query: str, num_results: int = 10) -> list[SearchResult]:
    """Search the web with fallback chain: Tavily → Serper → DuckDuckGo.

    Returns empty list if all providers fail (caller handles gracefully).
    """
    log("INFO", "search started", provider="tavily", query=query, num_results=num_results)

    start = time.monotonic()
    last_error = None

    try:
        results = await _tavily_search(query, num_results)
        log("INFO", "search completed", provider="tavily", results_count=len(results), duration_ms=int((time.monotonic() - start) * 1000))
        return results
    except SearchError as e:
        last_error = e
        log("WARN", "search provider failed, trying fallback", provider="tavily", error=str(e))

    if settings.serper_api_key:
        try:
            results = await _serper_search(query, num_results)
            log("INFO", "search completed", provider="serper", results_count=len(results), duration_ms=int((time.monotonic() - start) * 1000))
            return results
        except SearchError as e:
            last_error = e
            log("WARN", "search provider failed, trying fallback", provider="serper", error=str(e))

    try:
        results = await _duckduckgo_search(query, num_results)
        log("INFO", "search completed", provider="ddg", results_count=len(results), duration_ms=int((time.monotonic() - start) * 1000))
        return results
    except SearchError as e:
        last_error = e
        log("WARN", "search provider failed, trying fallback", provider="ddg", error=str(e))

    code = generate_error_code()
    log("ERROR", "search failed", provider="all", error=str(last_error), error_code=code, duration_ms=int((time.monotonic() - start) * 1000))
    return []


async def _tavily_search(query: str, num_results: int = 10) -> list[SearchResult]:
    """Tavily Search API (primary)."""
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": DEFAULT_USER_AGENT}) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "max_results": num_results,
                    "search_depth": "basic",
                },
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, httpx.RequestError, ValueError) as e:
        raise SearchError(str(e)) from e

    results = data.get("results", [])
    return [
        SearchResult(
            title=r.get("title", ""),
            url=r.get("url", ""),
            snippet=r.get("content", ""),
        )
        for r in results
    ]


async def _serper_search(query: str, num_results: int = 10) -> list[SearchResult]:
    """Serper API (fallback)."""
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": DEFAULT_USER_AGENT}) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": settings.serper_api_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": num_results},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, httpx.RequestError, ValueError) as e:
        raise SearchError(str(e)) from e

    organic = data.get("organic", [])
    return [
        SearchResult(
            title=r.get("title", ""),
            url=r.get("link", ""),
            snippet=r.get("snippet", ""),
        )
        for r in organic
    ]


async def _duckduckgo_search(query: str, num_results: int = 10) -> list[SearchResult]:
    """DuckDuckGo Search (last-resort)."""
    try:
        def _sync_search() -> list[SearchResult]:
            results = []
            for r in DDGS().text(query, max_results=num_results):
                results.append(
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", ""),
                    )
                )
            return results

        return await asyncio.to_thread(_sync_search)
    except Exception as e:
        raise SearchError(str(e)) from e


async def search_reddit(query: str, num_results: int = 5) -> list[SearchResult]:
    """Search Reddit via site:reddit.com query."""
    return await search(f"site:reddit.com {query}", num_results=num_results)
