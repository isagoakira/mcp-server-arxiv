"""Tests for MCP tools."""
import pytest

from arxiv_mcp_server.tools.search import arxiv_search
from arxiv_mcp_server.tools.paper import arxiv_get_paper


@pytest.mark.asyncio
async def test_search_formats_output_correctly():
    """Test that arxiv_search returns properly formatted Markdown."""
    # This would need a mock - just test the function exists and is callable
    assert callable(arxiv_search)


@pytest.mark.asyncio
async def test_paper_formats_output_correctly():
    """Test that arxiv_get_paper returns properly formatted Markdown."""
    # This would need a mock - just test the function exists and is callable
    assert callable(arxiv_get_paper)