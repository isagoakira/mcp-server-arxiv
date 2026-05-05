"""MCP tool for summarizing arXiv papers."""
import re
from typing import Optional

from mcp.server import Server
from mcp.types import Tool

from ..utils.arxiv_api import ArxivClient
from ..utils.pdf_downloader import get_downloader
from ..utils.pdf_extractor import get_extractor
from ..utils.summarizer import get_summarizer

# Global client instance
_client: Optional[ArxivClient] = None


def get_client() -> ArxivClient:
    global _client
    if _client is None:
        _client = ArxivClient()
    return _client


def create_summarize_tool(server: Server):
    """Create arxiv_summarize tool and register to server."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="arxiv_summarize",
                description="Download and summarize an arXiv paper using LLM",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "paper_id": {"type": "string", "description": "arXiv ID"},
                        "model": {"type": "string", "default": "claude-sonnet-4-6", "description": "LLM model"},
                        "style": {"type": "string", "default": "technical", "description": "Summary style: technical/beginner-friendly/bullet-points"},
                    },
                    "required": ["paper_id"],
                },
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> str:
        if name != "arxiv_summarize":
            raise ValueError(f"Unknown tool: {name}")

        paper_id = arguments.get("paper_id", "")
        model = arguments.get("model", "claude-sonnet-4-6")
        style = arguments.get("style", "technical")

        # Normalize ID (strip version suffix)
        normalized_id = re.sub(r'v\d+$', '', paper_id)

        # Get paper metadata
        client = get_client()
        paper = await client.get_paper(normalized_id)

        if not paper:
            return f"Error: Paper '{paper_id}' not found."

        if not paper.get("pdf_url"):
            return f"Error: Paper '{paper_id}' has no PDF URL."

        # Download PDF
        try:
            downloader = get_downloader()
            pdf_path = await downloader.download(paper_id, paper["pdf_url"])
        except Exception as e:
            return f"Error downloading PDF: {str(e)}"

        # Extract text
        try:
            extractor = get_extractor()
            text = extractor.extract(pdf_path)
        except Exception as e:
            return f"Error extracting text: {str(e)}"

        # Summarize
        try:
            summarizer = get_summarizer()
            summary = await summarizer.summarize(text, model=model, style=style)
        except Exception as e:
            return f"Error summarizing: {str(e)}"

        # Format response
        return (
            f"## Summary: {paper['title']}\n"
            f"**arXiv ID:** `{paper['id']}`\n"
            f"**Model:** {model}\n"
            f"**Style:** {style}\n\n"
            f"### Summary\n{summary}\n\n"
            f"*Generated from PDF - full text length: {len(text)} chars*"
        )


# For standalone usage (testing)
async def arxiv_summarize(
    paper_id: str,
    model: str = "claude-sonnet-4-6",
    style: str = "technical",
) -> str:
    """Direct call to arxiv_summarize (not via MCP server)."""
    normalized_id = re.sub(r'v\d+$', '', paper_id)
    client = get_client()
    paper = await client.get_paper(normalized_id)

    if not paper:
        return f"Error: Paper '{paper_id}' not found."

    if not paper.get("pdf_url"):
        return f"Error: Paper '{paper_id}' has no PDF URL."

    # Download PDF
    downloader = get_downloader()
    pdf_path = await downloader.download(paper_id, paper["pdf_url"])

    # Extract text
    extractor = get_extractor()
    text = extractor.extract(pdf_path)

    # Summarize
    summarizer = get_summarizer()
    summary = await summarizer.summarize(text, model=model, style=style)

    return (
        f"## Summary: {paper['title']}\n"
        f"**arXiv ID:** `{paper['id']}`\n\n"
        f"### Summary\n{summary}"
    )