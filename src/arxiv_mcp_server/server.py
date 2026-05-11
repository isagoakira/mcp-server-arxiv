"""MCP Server for arXiv paper search and summarization using FastMCP."""

import argparse
import asyncio
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP
import structlog

from .tools.search import register_tools as register_search_tools
from .tools.paper import (
    register_tools as register_paper_tools,
    normalize_paper_id,
    format_paper_details,
)
from .tools.summarize import register_tools as register_summarize_tools
from .tools.search import build_search_query, format_search_results_paginated
from .utils.arxiv_api import get_client, close_client

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def app_lifespan(server):
    """Manage ArxivClient lifecycle via FastMCP lifespan."""
    try:
        logger.info("arxiv_mcp_server_starting")
        yield
    finally:
        logger.info("arxiv_mcp_server_shutting_down")
        await close_client()


# Create FastMCP server instance
mcp = FastMCP("arxiv_mcp", lifespan=app_lifespan)

# Register all tools
register_search_tools(mcp)
register_paper_tools(mcp)
register_summarize_tools(mcp)


# ---- MCP Resources (P1) ----


@mcp.resource("arxiv://papers/{paper_id}")
async def get_paper_resource(paper_id: str) -> str:
    """Get paper metadata by arXiv ID as a resource.

    Registers a resource template at ``arxiv://papers/{paper_id}``.
    Clients can fetch structured paper data by visiting this URI.

    Args:
        paper_id: arXiv paper ID (e.g., "1706.03762" or "1706.03762v5").

    Returns:
        str: Markdown-formatted paper details.

    Raises:
        ValueError: If the paper is not found.
    """
    client = await get_client()
    try:
        paper = await client.get_paper(normalize_paper_id(paper_id))
        if not paper:
            raise ValueError(f"Paper '{paper_id}' not found.")
        return format_paper_details(paper)


@mcp.resource("arxiv://search/{query}")
async def search_resource(query: str) -> str:
    """Search arXiv papers by keyword as a resource.

    Registers a resource template at ``arxiv://search/{query}``.
    Returns the top 10 search results in Markdown format.

    Args:
        query: Search query string (searches in all fields).

    Returns:
        str: Markdown-formatted search results with pagination metadata.
    """
    client = await get_client()
    try:
        papers, total = await client.search(
            query=build_search_query("all", query),
            max_results=10,
        )
        return format_search_results_paginated(papers, total)


# ---- Entry points (P3: Streamable HTTP support) ----


async def main():
    """Run the MCP server with stdio transport."""
    await mcp.run_stdio_async()


def run_http(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the MCP server with Streamable HTTP transport.

    Args:
        host: Host address to bind to (default "127.0.0.1").
        port: Port number to listen on (default 8000).
    """
    mcp.run(transport="streamable_http", host=host, port=port)


def run():
    """Entry point for ``python -m arxiv_mcp_server``.

    Supports ``--transport http --host 0.0.0.0 --port 8000`` for remote
    deployment via Streamable HTTP.  Default is stdio (local integration).

    Command-line arguments::

        --transport {stdio,http}   Transport protocol (default: stdio)
        --host TEXT                HTTP host (default: 127.0.0.1)
        --port INT                 HTTP port (default: 8000)
    """
    parser = argparse.ArgumentParser(
        description="arXiv MCP Server — MCP tools for arXiv paper search and summarization",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="HTTP port (default: 8000)",
    )

    args = parser.parse_args()

    if args.transport == "http":
        run_http(host=args.host, port=args.port)
    else:
        asyncio.run(main())
