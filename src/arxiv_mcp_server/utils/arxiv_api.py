"""ArXiv API client with rate limiting and XML parsing."""
from typing import Optional

import feedparser
import httpx
import structlog

from .rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
RATE_LIMIT_SECONDS = 5.0


class ArxivClient:
    """ArXiv API async client with rate limiting."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = RateLimiter(RATE_LIMIT_SECONDS)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={"User-Agent": "mcp-server-arxiv/0.1 (mailto:isago@example.com)"},
            )
        return self._client

    async def search(
        self,
        query: str,
        start: int = 0,
        max_results: int = 5,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> list[dict]:
        """Search arXiv and return structured paper list."""
        await self._rate_limiter.acquire()

        params = {
            "search_query": query,
            "start": start,
            "max_results": min(max_results, 100),
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        logger.info("arxiv_search", query=query, max_results=max_results)
        client = await self._get_client()
        response = await client.get(ARXIV_API, params=params)
        response.raise_for_status()

        return self._parse_feed(response.text)

    def _parse_feed(self, xml_text: str) -> list[dict]:
        feed = feedparser.parse(xml_text)
        if feed.bozo and not feed.entries:
            logger.warning("arxiv_parse_warning", bozo_exception=str(feed.bozo_exception))
        return self._entries_to_papers(feed.entries)

    def _entries_to_papers(self, entries) -> list[dict]:
        papers = []
        for entry in entries:
            links = entry.get("links", [])
            pdf_link = None
            for link in links:
                if link.get("title") == "pdf":
                    pdf_link = link.get("href")
                    break

            categories = [t["term"] for t in entry.get("tags", [])]

            def _safe_text(value, default=""):
                if isinstance(value, str):
                    return value
                if isinstance(value, dict):
                    return value.get("#text", default)
                return default

            papers.append({
                "id": entry.id.split("/abs/")[-1],
                "title": " ".join(entry.title.split()),
                "summary": entry.get("summary", "").strip(),
                "authors": [a.get("name", "") for a in entry.get("authors", [])],
                "published": entry.get("published", ""),
                "updated": entry.get("updated", ""),
                "pdf_url": pdf_link,
                "categories": categories,
                "comment": _safe_text(entry.get("arxiv_comment")),
                "doi": _safe_text(entry.get("arxiv_doi")),
                "journal_ref": _safe_text(entry.get("arxiv_journal_ref")),
            })
        return papers

    async def get_paper(self, paper_id: str) -> Optional[dict]:
        """Get single paper by ID."""
        await self._rate_limiter.acquire()

        # Strip version suffix
        import re
        normalized_id = re.sub(r'v\d+$', '', paper_id)

        params = {
            "search_query": f"id:{normalized_id}",
            "start": 0,
            "max_results": 1,
        }

        logger.info("arxiv_get_paper", paper_id=paper_id, normalized_id=normalized_id)
        client = await self._get_client()
        response = await client.get(ARXIV_API, params=params)
        response.raise_for_status()

        papers = self._parse_feed(response.text)
        return papers[0] if papers else None

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None