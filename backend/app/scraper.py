"""
Blueprint Backend — Web Scraping

Jina Reader (primary) + BeautifulSoup (fallback).
Gated by semaphore to respect rate limits.
"""

import asyncio
import re
import time
import httpx
from bs4 import BeautifulSoup

from app.config import settings, log, generate_error_code


_scrape_semaphore = asyncio.Semaphore(2)

DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; Blueprint/1.0; +https://github.com/blueprint)"


class ScraperError(Exception):
    pass


def _truncate_content(content: str, max_chars: int = 15000) -> str:
    """Truncate at last complete sentence before max_chars."""
    if len(content) <= max_chars:
        return content
    truncated = content[:max_chars]
    # Find last sentence boundary (., !, ?)
    last_sentence = max(
        truncated.rfind("."),
        truncated.rfind("!"),
        truncated.rfind("?"),
    )
    if last_sentence > max_chars // 2:
        return truncated[: last_sentence + 1].strip()
    return truncated.strip()


async def scrape(url: str) -> str:
    """Scrape URL with Jina (primary) then BS4 (fallback)."""
    async with _scrape_semaphore:
        log("INFO", "scrape started", url=url, method="jina")

        start = time.monotonic()
        try:
            content = await _jina_scrape(url)
            log("INFO", "scrape completed", url=url, content_length=len(content), duration_ms=int((time.monotonic() - start) * 1000))
            return content
        except ScraperError as e:
            log("WARN", "scrape failed, trying fallback", url=url, method="jina", error=str(e))

            try:
                content = await _bs4_scrape(url)
                log("INFO", "scrape completed", url=url, content_length=len(content), duration_ms=int((time.monotonic() - start) * 1000))
                return content
            except ScraperError as e2:
                code = generate_error_code()
                log("ERROR", "scrape failed all methods", url=url, error=str(e2), error_code=code)
                raise ScraperError(str(e2)) from e2


async def _jina_scrape(url: str) -> str:
    """Jina Reader API — returns markdown content."""
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "Accept": "text/markdown",
        "User-Agent": DEFAULT_USER_AGENT,
    }
    if settings.jina_api_key:
        headers["Authorization"] = f"Bearer {settings.jina_api_key}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(jina_url, headers=headers)
            response.raise_for_status()
    except (httpx.HTTPError, httpx.RequestError) as e:
        raise ScraperError(str(e)) from e

    content = response.text
    return _truncate_content(content)


async def _bs4_scrape(url: str) -> str:
    """BeautifulSoup fallback — HTML parsing."""
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text
    except (httpx.HTTPError, httpx.RequestError) as e:
        raise ScraperError(str(e)) from e

    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    # Clean whitespace: collapse multiple newlines/spaces
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r" +", " ", text)
    text = text.strip()

    return _truncate_content(text)
