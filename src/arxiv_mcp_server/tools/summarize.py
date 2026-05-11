"""MCP tool for summarizing arXiv papers (FastMCP)."""

import re

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from ..models import ArxivSummarizeInput, SummarizeResult
from ..utils.arxiv_api import ArxivClient
from ..utils.pdf_downloader import get_downloader
from ..utils.pdf_extractor import get_extractor
from ..utils.summarizer import get_summarizer, Summarizer


async def arxiv_summarize(
    client: ArxivClient,
    paper_id: str,
    model: str = "claude-sonnet-4-6",
    style: str = "technical",
    summarizer: Summarizer | None = None,
    response_format: str = "markdown",
    ctx: Context | None = None,
) -> str:
    """Download, extract and summarize an arXiv paper using LLM.

    Downloads the PDF, extracts text, and generates a summary using the specified LLM model.
    Reports progress at each stage when ctx is provided.

    Args:
        client: ArxivClient instance for paper metadata lookup.
        paper_id: arXiv paper ID to summarize (e.g., "1706.03762").
        model: LLM model name (default "claude-sonnet-4-6").
        style: Summary style — "technical", "beginner-friendly", or "bullet-points".
        summarizer: Optional Summarizer instance (uses singleton if None).
        response_format: Output format — "markdown" or "json".
        ctx: Optional FastMCP context for progress reporting and logging.

    Returns:
        str: Markdown or JSON formatted summary.

        Markdown includes: title, ID, model, style, generated summary, text length.
        JSON format: {"title": str, "arxiv_id": str, "model": str, "summary": str, ...}

    Raises:
        ValueError: If paper ID is invalid, paper not found, or no PDF URL available.
        RuntimeError: If PDF download, text extraction, or LLM summarization fails.
    """
    # Note: Pydantic ArxivSummarizeInput validates paper_id format via min_length/max_length.
    # ArxivClient.get_paper() also validates internally as an API-layer defense.

    # Normalize ID (strip version suffix)
    normalized_id = re.sub(r"v\d+$", "", paper_id)

    # Get paper metadata
    if ctx is not None:
        await ctx.report_progress(0, 4)
    paper = await client.get_paper(normalized_id)

    if not paper:
        raise ValueError(f"Paper '{paper_id}' not found. Verify the ID is correct and try again.")

    if not paper.get("pdf_url"):
        raise ValueError(
            f"Paper '{paper_id}' has no PDF URL available. "
            f"This paper may not have a downloadable PDF."
        )

    # Download PDF
    if ctx is not None:
        await ctx.report_progress(1, 4)
    try:
        downloader = get_downloader()
        pdf_path = await downloader.download(paper_id, paper["pdf_url"])
    except Exception as e:
        raise RuntimeError(
            f"Failed to download PDF: {str(e)}. Check network connectivity and paper availability."
        )

    # Extract text
    if ctx is not None:
        await ctx.report_progress(2, 4)
    try:
        extractor = get_extractor()
        text = extractor.extract(pdf_path)
    except Exception as e:
        raise RuntimeError(
            f"Failed to extract text from PDF: {str(e)}. The PDF may be scanned or corrupted."
        )

    # Summarize
    if ctx is not None:
        await ctx.report_progress(3, 4)
    try:
        svc = summarizer or get_summarizer()
        summary = await svc.summarize(text, model=model, style=style)
    except Exception as e:
        raise RuntimeError(
            f"Failed to summarize paper: {str(e)}. Check LLM API key and model availability."
        )

    if ctx is not None:
        await ctx.report_progress(4, 4)

    # Format response
    if response_format == "json":
        result = SummarizeResult(
            title=paper.get("title", ""),
            arxiv_id=paper.get("id", ""),
            model=model,
            style=style,
            summary=summary,
            text_length=len(text),
            paper_url=paper.get("pdf_url"),
        )
        return result.model_dump_json(indent=2)

    return (
        f"## Summary: {paper.get('title', 'Untitled')}\n"
        f"**arXiv ID:** `{paper.get('id', '')}`\n"
        f"**Model:** {model}\n"
        f"**Style:** {style}\n\n"
        f"### Summary\n{summary}\n\n"
        f"*Generated from PDF - full text length: {len(text)} chars*"
    )


def register_tools(mcp):
    """Register arxiv_summarize tool with FastMCP.

    Registers a tool named "arxiv_summarize" that accepts ArxivSummarizeInput Pydantic model
    and returns formatted summaries.

    Args:
        mcp: The FastMCP server instance to register the tool on.
    """

    @mcp.tool(
        name="arxiv_summarize",
        description="Download and summarize an arXiv paper using LLM",
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
            openWorldHint=True,
        ),
    )
    async def summarize_tool(
        ctx: Context,
        params: ArxivSummarizeInput,
    ) -> str:
        """Download, extract and summarize an arXiv paper.

        Accepts a Pydantic model ArxivSummarizeInput with fields:
        paper_id, model, style, response_format.

        Args:
            ctx: FastMCP context for lifespan state, progress reporting, and logging.
            params: Pydantic model with summarization parameters.

        Returns:
            str: Markdown or JSON formatted summary.
        """
        client = ctx.request_context.lifespan_context["client"]

        await ctx.log_info(
            "summarize_started",
            {
                "paper_id": params.paper_id,
                "model": params.model,
                "style": params.style,
            },
        )

        result = await arxiv_summarize(
            client=client,
            paper_id=params.paper_id,
            model=params.model,
            style=params.style,
            response_format=params.response_format.value,
            ctx=ctx,
        )

        await ctx.log_info(
            "summarize_completed",
            {
                "paper_id": params.paper_id,
            },
        )

        return result
