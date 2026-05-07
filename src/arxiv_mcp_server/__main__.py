"""Main entry point for arxiv_mcp_server.

Usage:

    # Default: stdio transport (for local integration)
    python -m arxiv_mcp_server

    # HTTP transport (for remote deployment)
    python -m arxiv_mcp_server --transport http --port 8000
"""

from .server import run

if __name__ == "__main__":
    run()
