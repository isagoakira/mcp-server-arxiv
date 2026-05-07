"""MCP tool for getting single paper details (FastMCP)."""

import re

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from ..models import ArxivPaperInput, PaperResult
from ..utils.arxiv_api import ArxivClient


def normalize_paper_id(paper_id: str) -> str:
    """Strip version suffix from arXiv ID.

    Args:
        paper_id: arXiv paper ID, possibly with version suffix (e.g., "1706.03762v5").

    Returns:
        str: Paper ID with version suffix removed (e.g., "1706.03762").
    """
    return re.sub(r"v\d+$", "", paper_id)


def build_pdf_link(paper_id: str) -> str:
    """Generate direct PDF download link from arXiv ID.

    Args:
        paper_id: arXiv paper ID (e.g., "1706.03762" or "1706.03762v5").

    Returns:
        str: Full PDF URL (e.g., "https://arxiv.org/pdf/1706.03762.pdf").
    """
    base_id = paper_id.split("v")[0] if "v" in paper_id else paper_id
    return f"https://arxiv.org/pdf/{base_id}.pdf"


def format_paper_details(paper: dict, include_pdf_link: bool = True) -> str:
    """Format paper details as Markdown.

    Args:
        paper: Paper metadata dict with keys: title, id, authors, published, updated,
               categories, summary, comment, doi, journal_ref, pdf_url.
        include_pdf_link: Whether to include a PDF download link (default True).

    Returns:
        str: Markdown formatted paper details with all available metadata fields.
    """
    lines = [
        f"## {paper.get('title', 'Untitled')}",
        f"\n**arXiv ID:** `{paper.get('id', '')}`",
        f"\n**Authors:** {', '.join(paper.get('authors', []))}",
        f"\n**Published:** {(paper.get('published') or '')[:10]}",
        f"\n**Updated:** {(paper.get('updated') or '')[:10]}",
    ]

    categories = paper.get("categories", [])
    if categories:
        lines.append(f"\n**Categories:** {', '.join(categories)}")

    lines.append(f"\n## Abstract\n{paper.get('summary', '')}")

    if paper.get("comment"):
        lines.append(f"\n## Author Comment\n{paper['comment']}")

    if paper.get("doi"):
        lines.append(f"\n**DOI:** {paper['doi']}")

    if paper.get("journal_ref"):
        lines.append(f"\n**Journal Reference:** {paper['journal_ref']}")

    if include_pdf_link:
        pdf_url = build_pdf_link(paper.get("id", ""))
        lines.append(f"\n**PDF:** {pdf_url}")

    return "\n".join(lines)


def format_paper_details_json(paper: dict) -> str:
    """Format paper details as structured JSON string using Pydantic model.

    Args:
        paper: Paper metadata dict with keys: title, id, authors, published, updated,
               categories, summary, doi, journal_ref, pdf_url.

    Returns:
        str: JSON-formatted string with all paper metadata fields.
    """
    result = PaperResult(
        title=paper.get("title", ""),
        arxiv_id=paper.get("id", ""),
        authors=paper.get("authors", []),
        published=paper.get("published", ""),
        updated=paper.get("updated", ""),
        categories=paper.get("categories", []),
        summary=paper.get("summary", ""),
        doi=paper.get("doi"),
        journal_ref=paper.get("journal_ref"),
        pdf_url=paper.get("pdf_url"),
    )
    return result.model_dump_json(indent=2)


async def arxiv_get_paper(
    client: ArxivClient,
    paper_id: str,
    include_pdf_link: bool = True,
    response_format: str = "markdown",
) -> str:
    """Get full metadata for a specific arXiv paper by ID.

    Args:
        client: ArxivClient instance for API calls.
        paper_id: arXiv paper ID (e.g., "1706.03762" or "1706.03762v5").
        include_pdf_link: Whether to include PDF download URL in the response (default True).
        response_format: Output format — "markdown" or "json".

    Returns:
        str: Markdown or JSON formatted paper details.

        Markdown includes: title, ID, authors, dates, categories, abstract, comment, DOI, journal ref, PDF link.
        JSON format: {"title": str, "arxiv_id": str, "authors": [str], "summary": str, ...}

    Raises:
        ValueError: If paper ID format is invalid or paper not found.
    """
    # Note: Pydantic ArxivPaperInput validates paper_id format via min_length/max_length.
    # ArxivClient.get_paper() also validates internally as an API-layer defense.

    paper = await client.get_paper(normalize_paper_id(paper_id))

    if not paper:
        raise ValueError(f"Paper '{paper_id}' not found. Verify the ID is correct and try again.")

    if response_format == "json":
        return format_paper_details_json(paper)

    return format_paper_details(paper, include_pdf_link)


def register_tools(mcp):
    """Register arxiv_get_paper tool with FastMCP.

    Registers a tool named "arxiv_get_paper" that accepts ArxivPaperInput Pydantic model
    and returns formatted paper details.

    Args:
        mcp: The FastMCP server instance to register the tool on.
    """

    @mcp.tool(
        name="arxiv_get_paper",
        description="Get full metadata for a specific paper by arXiv ID",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=True,
        ),
    )
    async def paper_tool(
        ctx: Context,
        params: ArxivPaperInput,
    ) -> str:
        """Get full metadata for a specific arXiv paper.

        Accepts a Pydantic model ArxivPaperInput with fields:
        paper_id, include_pdf_link, response_format.

        Args:
            ctx: FastMCP context for lifespan state.
            params: Pydantic model with paper lookup parameters.

        Returns:
            str: Markdown or JSON formatted paper details.
        """
        client = ctx.request_context.lifespan_state["client"]
        return await arxiv_get_paper(
            client=client,
            paper_id=params.paper_id,
            include_pdf_link=params.include_pdf_link,
            response_format=params.response_format.value,
        )
