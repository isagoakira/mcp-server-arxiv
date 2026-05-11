"""ArXiv API client with rate limiting and XML parsing."""

import re
from typing import Optional

import feedparser
import httpx
import structlog

from .rate_limiter import RateLimiter

logger = structlog.get_logger(__name__)

ARXIV_API = "https://export.arxiv.org/api/query"
RATE_LIMIT_SECONDS = 5.0

# Module-level client singleton — avoids dependency on MCP lifespan_context
# which breaks across MCP SDK versions (e.g., RequestContext.lifespan_state missing).
_client: Optional["ArxivClient"] = None


async def get_client() -> "ArxivClient":
    """Return a module-level ArxivClient singleton, creating it lazily."""
    global _client
    if _client is None:
        _client = ArxivClient()
    return _client


async def close_client():
    """Close and release the module-level client singleton."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None

# arXiv ID validation pattern
_ARXIV_ID_PATTERN = re.compile(r'^[\w.-]+/?(?!.*[<>"\'\x60;|&$()])[\w.-]*$')


def validate_paper_id(paper_id: str) -> bool:
    """Validate arXiv paper ID format.

    arXiv IDs are typically YYYYMM.NNNNN(vV) or old-style category/YYYYMM.
    Rejects empty, overly long, or shell-injection-risk characters.

    Args:
        paper_id: String to validate as an arXiv paper ID.

    Returns:
        bool: True if the ID format is valid, False otherwise.
    """
    if not paper_id or len(paper_id) > 100:
        return False
    return bool(_ARXIV_ID_PATTERN.match(paper_id))


class ArxivClient:
    """ArXiv API async client with rate limiting.

    Provides async search and paper retrieval methods with automatic rate limiting
    (1 request per RATE_LIMIT_SECONDS). Uses httpx for HTTP calls and feedparser
    for Atom XML response parsing.

    Handles HTTP errors with actionable messages for 404, 403, 429, and timeout scenarios.
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limiter = RateLimiter(RATE_LIMIT_SECONDS)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the underlying httpx AsyncClient.

        Returns:
            httpx.AsyncClient: Shared HTTP client instance.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={"User-Agent": "arxiv-mcp-server/1.0 (https://github.com/anthropics/arxiv-mcp-server)"},
            )
        return self._client

    def _handle_http_error(self, response: httpx.Response) -> None:
        """Classify HTTP errors with actionable messages.

        Args:
            response: The httpx Response object with a non-2xx status code.

        Raises:
            RuntimeError: With a descriptive message based on status code.
                          For unexpected codes, raises the original httpx.HTTPStatusError.
        """
        if response.status_code == 404:
            raise RuntimeError(
                "arXiv API resource not found. The service endpoint may have changed."
            )
        elif response.status_code == 403:
            raise RuntimeError(
                "Access denied by arXiv API. Your request may be rate-limited or blocked."
            )
        elif response.status_code == 429:
            raise RuntimeError("Rate limit exceeded. Please wait a few seconds before retrying.")
        else:
            response.raise_for_status()

    async def search(
        self,
        query: str,
        start: int = 0,
        max_results: int = 5,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> tuple[list[dict], int]:
        """Search arXiv and return (structured paper list, total results count).

        Args:
            query: arXiv API search query with field prefix (e.g., "all:transformer").
            start: Zero-based offset for pagination (default 0).
            max_results: Maximum results to return, capped at 100 (default 5).
            sort_by: Sort field — "relevance" or "submittedDate".
            sort_order: Sort direction — "ascending" or "descending".

        Returns:
            tuple[list[dict], int]: (list of paper metadata dicts, total result count).

        Raises:
            RuntimeError: If the API returns a 404, 403, or 429 status, or on timeout.
            httpx.HTTPStatusError: For unexpected HTTP errors.
        """
        await self._rate_limiter.acquire()

        params = {
            "search_query": query,
            "start": start,
            "max_results": min(max_results, 100),
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        logger.info("arxiv_search", query=query, max_results=max_results)

        try:
            client = await self._get_client()
            response = await client.get(ARXIV_API, params=params)
            self._handle_http_error(response)
        except httpx.TimeoutException:
            raise RuntimeError(
                "arXiv API request timed out. The service may be slow or unavailable."
            )

        return self._parse_feed(response.text)

    def _parse_feed(self, xml_text: str) -> tuple[list[dict], int]:
        """Parse Atom XML feed and return (papers, total_results).

        Extracts paper entries and opensearch:totalResults from the Atom XML response.

        Args:
            xml_text: Raw Atom XML string from the arXiv API.

        Returns:
            tuple[list[dict], int]: (parsed paper list, total count from API metadata).
                Falls back to len(entries) if opensearch:totalResults is absent.
        """
        feed = feedparser.parse(xml_text)
        if feed.bozo and not feed.entries:
            logger.warning("arxiv_parse_warning", bozo_exception=str(feed.bozo_exception))
        total = int(feed.feed.get("opensearch_totalresults", len(feed.entries)))
        papers = self._entries_to_papers(feed.entries)
        return papers, total

    def _entries_to_papers(self, entries) -> list[dict]:
        """Convert feedparser entries to structured paper dicts.

        Args:
            entries: List of feedparser entry objects.

        Returns:
            list[dict]: Paper dicts with keys: id, title, summary, authors,
                       published, updated, pdf_url, categories, comment, doi, journal_ref.
        """
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

            papers.append(
                {
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
                }
            )
        return papers

    async def get_paper(self, paper_id: str) -> Optional[dict]:
        """Get single paper by ID.

        Validates the paper ID format, strips version suffix, and queries the arXiv API.
        Retains its own validate_paper_id call as an API-layer defense even though
        the tool-level Pydantic models also validate input format.

        Args:
            paper_id: arXiv paper ID (e.g., "1706.03762" or "1706.03762v5").

        Returns:
            Optional[dict]: Paper metadata dict, or None if not found.

        Raises:
            ValueError: If paper_id format is invalid.
            RuntimeError: If the API returns a 404, 403, or 429 status, or on timeout.
            httpx.HTTPStatusError: For unexpected HTTP errors.
        """
        await self._rate_limiter.acquire()

        if not validate_paper_id(paper_id):
            raise ValueError(
                f"Invalid arXiv paper ID format: '{paper_id}'. "
                f"Expected format like '1706.03762' or '1706.03762v5'."
            )

        # Strip version suffix
        normalized_id = re.sub(r"v\d+$", "", paper_id)

        params = {
            "search_query": f"id:{normalized_id}",
            "start": 0,
            "max_results": 1,
        }

        logger.info("arxiv_get_paper", paper_id=paper_id, normalized_id=normalized_id)

        try:
            client = await self._get_client()
            response = await client.get(ARXIV_API, params=params)
            self._handle_http_error(response)
        except httpx.TimeoutException:
            raise RuntimeError(
                "arXiv API request timed out. The service may be slow or unavailable."
            )

        papers, _ = self._parse_feed(response.text)
        return papers[0] if papers else None

    async def close(self):
        """Close the underlying HTTP client connection.

        Safe to call multiple times. No-op if the client has not been initialized
        or has already been closed.
        """
        if self._client:
            await self._client.aclose()
            self._client = None
