"""MCP tool for searching arXiv papers."""
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


def create_search_tool(server: Server):
    """Create arxiv_search tool and register to server."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="arxiv_search",
                description="Search arXiv papers by query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {"type": "integer", "default": 5, "description": "Max results (default 5)"},
                        "search_in": {"type": "string", "default": "all", "description": "Search field: all/title/abstract/author"},
                        "sort_by": {"type": "string", "default": "relevance", "description": "Sort by: relevance/relevance/submittedDate"},
                        "start": {"type": "integer", "default": 0, "description": "Result offset"},
                    },
                    "required": ["query"],
                },
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> str:
        if name != "arxiv_search":
            raise ValueError(f"Unknown tool: {name}")

        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)
        search_in = arguments.get("search_in", "all")
        sort_by = arguments.get("sort_by", "relevance")
        start = arguments.get("start", 0)

        # Map search_in to API field prefix
        field_mapping = {
            "all": "all",
            "title": "ti",
            "abstract": "abs",
            "author": "au",
        }
        field_prefix = field_mapping.get(search_in, "all")
        search_query = f"{field_prefix}:{query}"

        # Get client and search
        client = get_client()
        papers = await client.search(
            query=search_query,
            start=start,
            max_results=max_results,
            sort_by=sort_by,
        )

        # Format as Markdown
        if not papers:
            return "No papers found."

        lines = [f"## Found {len(papers)} paper(s)\n"]
        for i, paper in enumerate(papers, 1):
            # Truncate abstract to 500 chars
            abstract = paper["summary"]
            if len(abstract) > 500:
                abstract = abstract[:500] + "..."

            # Show first 3 authors
            authors = paper["authors"]
            author_str = ", ".join(authors[:3])
            if len(authors) > 3:
                author_str += " et al."

            lines.append(f"### {i}. {paper['title']}")
            lines.append(f"**arXiv ID:** `{paper['id']}`")
            lines.append(f"**Authors:** {author_str}")
            lines.append(f"**Published:** {paper['published'][:10]}")
            lines.append(f"**Categories:** {', '.join(paper['categories'][:3])}")
            lines.append(f"\n**Abstract:** {abstract}\n")

            if paper.get("pdf_url"):
                lines.append(f"**PDF:** {paper['pdf_url']}")

            lines.append("---\n")

        return "\n".join(lines)


# For standalone usage (testing)
async def arxiv_search(
    query: str,
    max_results: int = 5,
    search_in: str = "all",
    sort_by: str = "relevance",
    start: int = 0,
) -> str:
    """Direct call to arxiv_search (not via MCP server)."""
    client = get_client()
    field_mapping = {"all": "all", "title": "ti", "abstract": "abs", "author": "au"}
    field_prefix = field_mapping.get(search_in, "all")
    search_query = f"{field_prefix}:{query}"

    papers = await client.search(
        query=search_query,
        start=start,
        max_results=max_results,
        sort_by=sort_by,
    )

    if not papers:
        return "No papers found."

    lines = [f"## Found {len(papers)} paper(s)\n"]
    for i, paper in enumerate(papers, 1):
        abstract = paper["summary"]
        if len(abstract) > 500:
            abstract = abstract[:500] + "..."

        authors = paper["authors"]
        author_str = ", ".join(authors[:3])
        if len(authors) > 3:
            author_str += " et al."

        lines.append(f"### {i}. {paper['title']}")
        lines.append(f"**arXiv ID:** `{paper['id']}`")
        lines.append(f"**Authors:** {author_str}")
        lines.append(f"**Published:** {paper['published'][:10]}")
        lines.append(f"\n**Abstract:** {abstract}\n")
        if paper.get("pdf_url"):
            lines.append(f"**PDF:** {paper['pdf_url']}")
        lines.append("---\n")

    return "\n".join(lines)