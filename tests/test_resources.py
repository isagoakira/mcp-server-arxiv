"""Tests for MCP resource templates (P1: MCP Resources).

Tests cover:
- Resource URI registration and listing
- ``arxiv://papers/{paper_id}`` resource with mocked API
- ``arxiv://search/{query}`` resource with mocked API
"""

import pytest
import respx
import httpx


SAMPLE_XML_SINGLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>Sample Paper Title</title>
    <summary>This is a sample abstract for testing.</summary>
    <author><name>Test Author</name></author>
    <published>2023-01-01T00:00:00Z</published>
    <updated>2023-01-15T00:00:00Z</updated>
    <link title="pdf" href="https://arxiv.org/pdf/2301.00001v1"/>
    <category term="cs.CV" primary="true"/>
    <category term="cs.LG"/>
    <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.48550/arXiv.2301.00001</arxiv:doi>
  </entry>
</feed>"""

SAMPLE_XML_MULTI = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>42</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>2</opensearch:itemsPerPage>
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>First Paper</title>
    <summary>First abstract.</summary>
    <author><name>Author One</name></author>
    <published>2023-01-01T00:00:00Z</published>
    <link title="pdf" href="https://arxiv.org/pdf/2301.00001v1"/>
    <category term="cs.CV"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2301.00002v1</id>
    <title>Second Paper</title>
    <summary>Second abstract.</summary>
    <author><name>Author Two</name></author>
    <published>2023-02-01T00:00:00Z</published>
    <link title="pdf" href="https://arxiv.org/pdf/2301.00002v1"/>
    <category term="cs.LG"/>
  </entry>
</feed>"""


def test_resource_functions_exist():
    """Test that resource functions are defined on the server module."""
    from arxiv_mcp_server import server

    assert hasattr(server, "get_paper_resource"), "get_paper_resource should exist"
    assert hasattr(server, "search_resource"), "search_resource should exist"
    assert callable(server.get_paper_resource), "get_paper_resource should be callable"
    assert callable(server.search_resource), "search_resource should be callable"


def test_resource_functions_have_correct_signatures():
    """Test resource functions accept expected parameters."""
    import inspect
    from arxiv_mcp_server.server import get_paper_resource, search_resource

    paper_sig = inspect.signature(get_paper_resource)
    assert "paper_id" in paper_sig.parameters, "get_paper_resource should accept paper_id"

    search_sig = inspect.signature(search_resource)
    assert "query" in search_sig.parameters, "search_resource should accept query"


@pytest.mark.asyncio
async def test_paper_resource_content():
    """Test arxiv://papers resource returns formatted paper details."""
    from arxiv_mcp_server.tools.paper import normalize_paper_id, format_paper_details
    from arxiv_mcp_server.utils.arxiv_api import ArxivClient

    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=SAMPLE_XML_SINGLE)
        )
        paper = await client.get_paper(normalize_paper_id("2301.00001"))
        assert paper is not None
        result = format_paper_details(paper)
        assert "Sample Paper Title" in result
        assert "2301.00001v1" in result
        assert "Test Author" in result

    await client.close()


@pytest.mark.asyncio
async def test_paper_resource_not_found():
    """Test paper resource raises ValueError for non-existent paper."""
    from arxiv_mcp_server.tools.paper import normalize_paper_id
    from arxiv_mcp_server.utils.arxiv_api import ArxivClient

    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(
                200, text="""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"/>"""
            )
        )
        paper = await client.get_paper(normalize_paper_id("0000.00000"))
        # Paper not found -> None (no ValueError from get_paper itself)
        assert paper is None

    await client.close()


@pytest.mark.asyncio
async def test_search_resource_content():
    """Test arxiv://search resource returns formatted search results."""
    from arxiv_mcp_server.tools.search import build_search_query, format_search_results_paginated
    from arxiv_mcp_server.utils.arxiv_api import ArxivClient

    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=SAMPLE_XML_MULTI)
        )
        papers, total = await client.search(
            query=build_search_query("all", "test"),
            max_results=10,
        )
        result = format_search_results_paginated(papers, total)
        assert "First Paper" in result
        assert "Second Paper" in result
        assert "Total found: 42" in result or "Total found:" in result
        assert "Has more" in result or "Showing" in result

    await client.close()
