"""MCP tool for getting single paper details."""
import re
from typing import Optional

from mcp.server import Server
from mcp.types import Tool

from ..utils.arxiv_api import ArxivClient

# Global client instance
_client: Optional[ArxivClient] = None


def get_client() -> ArxivClient:
    global _client
    if _client is None:
        _client = ArxivClient()
    return _client


def create_paper_tool(server: Server):
    """Create arxiv_get_paper tool and register to server."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="arxiv_get_paper",
                description="Get full metadata for a specific paper by arXiv ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "paper_id": {"type": "string", "description": "arXiv ID (e.g., 1706.03762 or 1706.03762v5)"},
                        "include_pdf_link": {"type": "boolean", "default": True, "description": "Include PDF download link"},
                    },
                    "required": ["paper_id"],
                },
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> str:
        if name != "arxiv_get_paper":
            raise ValueError(f"Unknown tool: {name}")

        paper_id = arguments.get("paper_id", "")
        include_pdf_link = arguments.get("include_pdf_link", True)

        # Normalize ID (strip version suffix)
        normalized_id = re.sub(r'v\d+$', '', paper_id)

        # Get paper
        client = get_client()
        paper = await client.get_paper(normalized_id)

        if not paper:
            return f"Error: Paper '{paper_id}' not found."

        # Format as Markdown
        lines = [
            f"## {paper['title']}",
            f"\n**arXiv ID:** `{paper['id']}`",
            f"\n**Authors:** {', '.join(paper['authors'])}",
            f"\n**Published:** {paper['published'][:10]}",
            f"\n**Updated:** {paper['updated'][:10]}",
        ]

        if paper.get("categories"):
            lines.append(f"\n**Categories:** {', '.join(paper['categories'])}")

        lines.append(f"\n## Abstract\n{paper['summary']}")

        if paper.get("comment"):
            lines.append(f"\n## Author Comment\n{paper['comment']}")

        if paper.get("doi"):
            lines.append(f"\n**DOI:** {paper['doi']}")

        if paper.get("journal_ref"):
            lines.append(f"\n**Journal Reference:** {paper['journal_ref']}")

        if include_pdf_link and paper.get("pdf_url"):
            # Generate direct PDF link
            base_id = paper["id"].split("v")[0] if "v" in paper["id"] else paper["id"]
            pdf_link = f"https://arxiv.org/pdf/{base_id}.pdf"
            lines.append(f"\n**PDF:** {pdf_link}")

        return "\n".join(lines)


# For standalone usage (testing)
async def arxiv_get_paper(paper_id: str, include_pdf_link: bool = True) -> str:
    """Direct call to arxiv_get_paper (not via MCP server)."""
    normalized_id = re.sub(r'v\d+$', '', paper_id)
    client = get_client()
    paper = await client.get_paper(normalized_id)

    if not paper:
        return f"Error: Paper '{paper_id}' not found."

    lines = [
        f"## {paper['title']}",
        f"\n**arXiv ID:** `{paper['id']}`",
        f"\n**Authors:** {', '.join(paper['authors'])}",
        f"\n**Published:** {paper['published'][:10]}",
        f"\n**Updated:** {paper['updated'][:10]}",
    ]

    if paper.get("categories"):
        lines.append(f"\n**Categories:** {', '.join(paper['categories'])}")

    lines.append(f"\n## Abstract\n{paper['summary']}")

    if paper.get("doi"):
        lines.append(f"\n**DOI:** {paper['doi']}")

    if include_pdf_link:
        base_id = paper["id"].split("v")[0] if "v" in paper["id"] else paper["id"]
        pdf_link = f"https://arxiv.org/pdf/{base_id}.pdf"
        lines.append(f"\n**PDF:** {pdf_link}")

    return "\n".join(lines)