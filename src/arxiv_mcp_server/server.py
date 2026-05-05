"""MCP Server for arXiv paper search and summarization."""
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
import structlog

from .tools.search import create_search_tool
from .tools.paper import create_paper_tool
from .tools.summarize import create_summarize_tool

logger = structlog.get_logger(__name__)

# Create server instance
server = Server("arxiv-mcp-server")

# Register all tools
create_search_tool(server)
create_paper_tool(server)
create_summarize_tool(server)


async def main():
    """Run the MCP server with stdio transport."""
    logger.info("arxiv_mcp_server_starting")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run():
    """Entry point for python -m arxiv_mcp_server."""
    asyncio.run(main())


# Export for __main__.py
def main_wrapper():
    asyncio.run(main())