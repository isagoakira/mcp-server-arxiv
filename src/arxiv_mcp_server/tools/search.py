"""MCP tool for searching arXiv papers (FastMCP)."""

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from ..models import ArxivSearchInput, SearchResult, PaperResult
from ..utils.arxiv_api import ArxivClient

# Field prefix mapping for arXiv API
FIELD_MAPPING = {"all": "all", "title": "ti", "abstract": "abs", "author": "au"}


def build_search_query(search_in: str, query: str) -> str:
    """Build arXiv API search query with field prefix.

    Args:
        search_in: Search field scope — "all", "title", "abstract", or "author".
        query: Raw search query string.

    Returns:
        str: Formatted query with field prefix (e.g., "all:transformer" or "ti:attention").
        Falls back to "all:" prefix if search_in is not recognized.
    """
    field_prefix = FIELD_MAPPING.get(search_in, "all")
    return f"{field_prefix}:{query}"


def _format_paper_entry(paper: dict, index: int | None = None) -> list[str]:
    """Format a single paper entry as Markdown lines.

    Args:
        paper: Paper metadata dict with keys: id, title, summary, authors, published,
               categories, pdf_url.
        index: Optional 1-based index to prepend to the title heading.

    Returns:
        list[str]: Markdown-formatted lines representing the paper entry.
    """
    abstract = paper.get("summary", "")
    if len(abstract) > 500:
        abstract = abstract[:500] + "..."

    authors = paper.get("authors", [])
    author_str = ", ".join(authors[:3])
    if len(authors) > 3:
        author_str += " et al."

    heading = (
        f"### {index}. {paper.get('title', 'Untitled')}"
        if index
        else f"### {paper.get('title', 'Untitled')}"
    )
    lines = [heading]
    lines.append(f"**arXiv ID:** `{paper.get('id', '')}`")
    lines.append(f"**Authors:** {author_str}")
    lines.append(f"**Published:** {(paper.get('published') or '')[:10]}")
    categories = paper.get("categories", [])
    if categories:
        lines.append(f"**Categories:** {', '.join(categories[:3])}")
    lines.append(f"\n**Abstract:** {abstract}\n")
    if paper.get("pdf_url"):
        lines.append(f"**PDF:** {paper['pdf_url']}")
    lines.append("---\n")

    return lines


def format_search_results(papers: list[dict]) -> str:
    """Format search results as Markdown (simple, no pagination metadata).

    Args:
        papers: List of paper metadata dicts.

    Returns:
        str: Markdown formatted string. Returns "No papers found." for empty list.
    """
    if not papers:
        return "No papers found."

    lines = [f"## Found {len(papers)} paper(s)\n"]
    for i, paper in enumerate(papers, 1):
        lines.extend(_format_paper_entry(paper, index=i))

    return "\n".join(lines)


def format_search_results_paginated(papers: list[dict], total_results: int, start: int = 0) -> str:
    """Format search results as Markdown with pagination metadata.

    Args:
        papers: List of paper metadata dicts.
        total_results: Total number of matching papers from the API.
        start: Zero-based offset of the current page (default 0).

    Returns:
        str: Markdown formatted string with pagination info and next-page hint.
    """
    if not papers:
        return "No papers found."

    lines = [
        "## Search Results",
        f"**Total found:** {total_results}",
        f"**Showing:** {len(papers)} result(s)",
    ]
    has_more = total_results > start + len(papers)
    if has_more:
        lines.append("**Has more:** true")
        next_offset = start + len(papers)
        lines.append(f"**Next page:** start={next_offset}")
    lines.append("")

    for i, paper in enumerate(papers, 1):
        lines.extend(_format_paper_entry(paper, index=i))

    return "\n".join(lines)


async def arxiv_search(
    client: ArxivClient,
    query: str,
    max_results: int = 5,
    search_in: str = "all",
    sort_by: str = "relevance",
    start: int = 0,
    response_format: str = "markdown",
) -> str:
    """Search arXiv papers and return results in specified format.

    Args:
        client: ArxivClient instance for API calls.
        query: Search query string with optional field prefix (e.g., "all:transformer" or "ti:attention").
        max_results: Maximum number of results to return (1-100, default 5).
        search_in: Search field scope — "all", "title", "abstract", or "author".
        sort_by: Sort order — "relevance" or "submittedDate".
        start: Result offset for pagination (default 0).
        response_format: Output format — "markdown" (human-readable) or "json" (structured data).

    Returns:
        str: Markdown or JSON formatted search results.

        Markdown format includes: total count, per-paper title/ID/authors/date/categories/abstract/PDF link.
        JSON format: {"total": int, "count": int, "start": int, "has_more": bool,
                       "next_offset": int | None, "results": [...]}

        Returns "No papers found." for empty results.

    Example:
        - Search by keyword: query="transformer attention"
        - Search by author: query="hinton", search_in="author"
        - Search by title: query="attention is all you need", search_in="title"
        - Paginated: start=10, max_results=10 (get page 2)
    """
    papers, total = await client.search(
        query=build_search_query(search_in, query),
        start=start,
        max_results=max_results,
        sort_by=sort_by,
    )

    if response_format == "json":
        has_more = total > start + len(papers)
        result = SearchResult(
            total=total,
            count=len(papers),
            start=start,
            has_more=has_more,
            next_offset=start + len(papers) if has_more else None,
            results=[
                PaperResult(
                    title=p.get("title", ""),
                    arxiv_id=p.get("id", ""),
                    authors=p.get("authors", []),
                    published=p.get("published", ""),
                    updated=p.get("updated", ""),
                    categories=p.get("categories", []),
                    summary=p.get("summary", ""),
                    doi=p.get("doi"),
                    journal_ref=p.get("journal_ref"),
                    pdf_url=p.get("pdf_url"),
                )
                for p in papers
            ],
        )
        return result.model_dump_json(indent=2)

    return format_search_results_paginated(papers, total, start)


def register_tools(mcp):
    """Register arxiv_search tool with FastMCP.

    Registers a tool named "arxiv_search" that accepts ArxivSearchInput Pydantic model
    and returns formatted search results.

    Args:
        mcp: The FastMCP server instance to register the tool on.
    """

    @mcp.tool(
        name="arxiv_search",
        description="Search arXiv papers by query with pagination and format options",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def search_tool(
        ctx: Context,
        params: ArxivSearchInput,
    ) -> str:
        """Search arXiv papers and return results in specified format.

        Accepts a Pydantic model ArxivSearchInput with fields:
        query, max_results, search_in, sort_by, start, response_format.

        Args:
            ctx: FastMCP context for lifespan state and logging.
            params: Pydantic model with search parameters.

        Returns:
            str: Markdown or JSON formatted search results.
        """
        client = ctx.request_context.lifespan_context["client"]
        return await arxiv_search(
            client=client,
            query=params.query,
            max_results=params.max_results,
            search_in=params.search_in,
            sort_by=params.sort_by,
            start=params.start,
            response_format=params.response_format.value,
        )
