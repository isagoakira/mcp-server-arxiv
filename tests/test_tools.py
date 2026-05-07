"""Tests for MCP tool output formatting and validation."""

import json

import pytest
import respx
import httpx

from arxiv_mcp_server.tools.search import (
    arxiv_search,
    format_search_results,
    format_search_results_paginated,
    build_search_query,
)
from arxiv_mcp_server.tools.paper import (
    arxiv_get_paper,
    format_paper_details,
    format_paper_details_json,
    normalize_paper_id,
    build_pdf_link,
)
from arxiv_mcp_server.tools.summarize import arxiv_summarize
from arxiv_mcp_server.utils.arxiv_api import validate_paper_id, ArxivClient


# ---- search helpers ----


class TestBuildSearchQuery:
    def test_all_field(self):
        assert build_search_query("all", "transformer") == "all:transformer"

    def test_title_field(self):
        assert build_search_query("title", "attention") == "ti:attention"

    def test_abstract_field(self):
        assert build_search_query("abstract", "neural") == "abs:neural"

    def test_author_field(self):
        assert build_search_query("author", "smith") == "au:smith"

    def test_invalid_field_falls_back_to_all(self):
        assert build_search_query("unknown", "test") == "all:test"


class TestFormatSearchResults:
    def test_empty_results(self):
        assert format_search_results([]) == "No papers found."

    def test_single_result(self):
        papers = [
            {
                "id": "2301.00001",
                "title": "Test Paper",
                "summary": "This is a test abstract.",
                "authors": ["Alice", "Bob"],
                "published": "2023-01-01T00:00:00Z",
                "categories": ["cs.CV", "cs.LG"],
                "pdf_url": "https://arxiv.org/pdf/2301.00001",
            }
        ]
        result = format_search_results(papers)
        assert "Test Paper" in result
        assert "2301.00001" in result
        assert "Alice, Bob" in result
        assert "2023-01-01" in result
        assert "cs.CV, cs.LG" in result
        assert "https://arxiv.org/pdf/2301.00001" in result

    def test_abstract_truncation(self):
        papers = [
            {
                "id": "2301.00001",
                "title": "Test",
                "summary": "x" * 600,
                "authors": ["Alice"],
                "published": "2023-01-01",
                "categories": ["cs.CV"],
            }
        ]
        result = format_search_results(papers)
        assert len(result) < 1200  # truncated


class TestFormatSearchResultsPaginated:
    def test_pagination_metadata(self):
        result = format_search_results_paginated([], 0)
        assert result == "No papers found."

    def test_with_papers(self):
        papers = [
            {
                "id": "2301.00001",
                "title": "Test Paper",
                "summary": "Abstract here.",
                "authors": ["Alice"],
                "published": "2023-01-01",
                "categories": ["cs.CV"],
            }
        ]
        result = format_search_results_paginated(papers, 1)
        assert "Search Results" in result
        assert "Total found:" in result
        assert "Showing" in result
        assert "1 result" in result

    def test_has_more_flag(self):
        papers = [
            {
                "id": "2301.00001",
                "title": "Test",
                "summary": "x",
                "authors": ["A"],
                "published": "2023-01-01",
                "categories": ["cs.CV"],
            }
        ]
        result = format_search_results_paginated(papers, 100)
        assert "Has more" in result

    def test_no_more_flag(self):
        papers = [
            {
                "id": "2301.00001",
                "title": "Test",
                "summary": "x",
                "authors": ["A"],
                "published": "2023-01-01",
                "categories": ["cs.CV"],
            }
        ]
        result = format_search_results_paginated(papers, 1)
        assert "Has more: true" not in result


# ---- paper helpers ----


class TestValidatePaperId:
    def test_valid_new_format(self):
        assert validate_paper_id("2301.00001") is True

    def test_valid_with_version(self):
        assert validate_paper_id("2301.00001v5") is True

    def test_valid_old_format(self):
        assert validate_paper_id("cs/0709123") is True

    def test_empty_id(self):
        assert validate_paper_id("") is False

    def test_too_long(self):
        assert validate_paper_id("x" * 101) is False

    def test_rejects_shell_chars(self):
        assert validate_paper_id("2301.00001; rm -rf /") is False
        assert validate_paper_id("2301.00001`id`") is False
        assert validate_paper_id("2301.00001$(whoami)") is False


class TestNormalizePaperId:
    def test_strips_version(self):
        assert normalize_paper_id("2301.00001v5") == "2301.00001"

    def test_no_version(self):
        assert normalize_paper_id("2301.00001") == "2301.00001"


class TestBuildPdfLink:
    def test_basic_link(self):
        assert build_pdf_link("2301.00001") == "https://arxiv.org/pdf/2301.00001.pdf"

    def test_with_version(self):
        assert build_pdf_link("2301.00001v5") == "https://arxiv.org/pdf/2301.00001.pdf"


class TestFormatPaperDetails:
    def test_basic_formatting(self):
        paper = {
            "id": "1706.03762v7",
            "title": "Attention Is All You Need",
            "authors": ["Vaswani", "Shazeer", "Parmar"],
            "published": "2017-06-12T00:00:00Z",
            "updated": "2023-01-15T00:00:00Z",
            "categories": ["cs.CL", "cs.LG"],
            "summary": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
            "comment": "15 pages, 5 figures",
            "doi": "10.48550/arXiv.1706.03762",
            "journal_ref": "NeurIPS 2017",
            "pdf_url": "https://arxiv.org/pdf/1706.03762",
        }
        result = format_paper_details(paper)
        assert "Attention Is All You Need" in result
        assert "1706.03762v7" in result
        assert "Vaswani, Shazeer, Parmar" in result
        assert "2017-06-12" in result
        assert "cs.CL, cs.LG" in result
        assert "10.48550/arXiv.1706.03762" in result
        assert "NeurIPS 2017" in result
        assert "https://arxiv.org/pdf/1706.03762.pdf" in result
        assert "15 pages, 5 figures" in result


class TestFormatPaperDetailsJson:
    def test_basic_json(self):
        paper = {
            "id": "1706.03762v7",
            "title": "Attention Is All You Need",
            "authors": ["Vaswani", "Shazeer", "Parmar"],
            "published": "2017-06-12T00:00:00Z",
            "updated": "2023-01-15T00:00:00Z",
            "categories": ["cs.CL", "cs.LG"],
            "summary": "The dominant sequence transduction models.",
            "doi": "10.48550/arXiv.1706.03762",
            "journal_ref": "NeurIPS 2017",
            "pdf_url": "https://arxiv.org/pdf/1706.03762",
        }
        result = json.loads(format_paper_details_json(paper))
        assert result["arxiv_id"] == "1706.03762v7"
        assert result["title"] == "Attention Is All You Need"
        assert result["authors"] == ["Vaswani", "Shazeer", "Parmar"]
        assert result["doi"] == "10.48550/arXiv.1706.03762"
        assert result["journal_ref"] == "NeurIPS 2017"
        assert result["pdf_url"] == "https://arxiv.org/pdf/1706.03762"


# ---- Mocked tool integration tests ----

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
<feed xmlns="http://www.w3.org/2005/Atom">
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


@pytest.mark.asyncio
async def test_arxiv_search_mocked():
    """Test that arxiv_search returns formatted output with mocked API."""
    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=SAMPLE_XML_SINGLE)
        )
        result = await arxiv_search(client, "test query", max_results=5)
        assert "Sample Paper Title" in result
        assert "2301.00001v1" in result
        assert "Test Author" in result


@pytest.mark.asyncio
async def test_arxiv_search_no_results():
    """Test arxiv_search with no results returned."""
    EMPTY_FEED = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
    </feed>"""
    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=EMPTY_FEED)
        )
        result = await arxiv_search(client, "nonexistent_xyzzy_2025")
        assert result == "No papers found."


@pytest.mark.asyncio
async def test_arxiv_search_json_format():
    """Test arxiv_search with JSON response format."""
    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=SAMPLE_XML_SINGLE)
        )
        result = await arxiv_search(client, "test query", response_format="json")
        data = json.loads(result)
        assert data["total"] == 1
        assert data["count"] == 1
        assert data["has_more"] is False
        assert len(data["results"]) == 1


@pytest.mark.asyncio
async def test_arxiv_search_multi_json():
    """Test arxiv_search with multiple results in JSON format."""
    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=SAMPLE_XML_MULTI)
        )
        result = await arxiv_search(client, "test", max_results=10, response_format="json")
        data = json.loads(result)
        assert data["total"] == 2
        assert len(data["results"]) == 2


@pytest.mark.asyncio
async def test_arxiv_get_paper_mocked():
    """Test that arxiv_get_paper returns formatted output."""
    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=SAMPLE_XML_SINGLE)
        )
        result = await arxiv_get_paper(client, "2301.00001")
        assert "Sample Paper Title" in result
        assert "Test Author" in result


@pytest.mark.asyncio
async def test_arxiv_get_paper_not_found():
    """Test arxiv_get_paper with non-existent paper raises error."""
    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(
                200, text="""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"/>"""
            )
        )
        with pytest.raises(ValueError, match="not found"):
            await arxiv_get_paper(client, "0000.00000")


@pytest.mark.asyncio
async def test_arxiv_get_paper_invalid_id():
    """Test arxiv_get_paper with invalid paper ID raises error."""
    client = ArxivClient()
    with pytest.raises(ValueError, match="Invalid arXiv paper ID format"):
        await arxiv_get_paper(client, "rm -rf /")


@pytest.mark.asyncio
async def test_arxiv_search_json_has_more():
    """Test has_more is True when totalResults exceeds returned count."""
    XML_WITH_TOTAL = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
      <opensearch:totalResults>100</opensearch:totalResults>
      <opensearch:startIndex>0</opensearch:startIndex>
      <opensearch:itemsPerPage>1</opensearch:itemsPerPage>
      <entry>
        <id>http://arxiv.org/abs/2301.00001v1</id>
        <title>Only One Paper</title>
        <summary>Abstract.</summary>
        <author><name>Author</name></author>
        <published>2023-01-01T00:00:00Z</published>
        <link title="pdf" href="https://arxiv.org/pdf/2301.00001v1"/>
        <category term="cs.CV"/>
      </entry>
    </feed>"""
    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=XML_WITH_TOTAL)
        )
        result = await arxiv_search(client, "test", max_results=1, response_format="json")
        data = json.loads(result)
        assert data["total"] == 100
        assert data["count"] == 1
        assert data["has_more"] is True


@pytest.mark.asyncio
async def test_arxiv_get_paper_json_format():
    """Test arxiv_get_paper with JSON response format."""
    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=SAMPLE_XML_SINGLE)
        )
        result = await arxiv_get_paper(client, "2301.00001", response_format="json")
        data = json.loads(result)
        assert data["arxiv_id"] == "2301.00001v1"
        assert data["title"] == "Sample Paper Title"
        assert data["authors"] == ["Test Author"]
        assert "summary" in data
        assert data["pdf_url"] == "https://arxiv.org/pdf/2301.00001v1"


@pytest.mark.asyncio
async def test_arxiv_search_error_handling():
    """Test arxiv_search handles API errors gracefully."""
    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(return_value=httpx.Response(500))
        with pytest.raises(httpx.HTTPStatusError):
            await arxiv_search(client, "test query")


# ---- next_offset tests ----

SAMPLE_XML_WITH_TOTAL = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <opensearch:totalResults>100</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>1</opensearch:itemsPerPage>
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>Only One Paper</title>
    <summary>Abstract.</summary>
    <author><name>Author</name></author>
    <published>2023-01-01T00:00:00Z</published>
    <link title="pdf" href="https://arxiv.org/pdf/2301.00001v1"/>
    <category term="cs.CV"/>
  </entry>
</feed>"""


@pytest.mark.asyncio
async def test_arxiv_search_json_next_offset():
    """Test JSON response includes next_offset when has_more is true."""
    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=SAMPLE_XML_WITH_TOTAL)
        )
        result = await arxiv_search(client, "test", max_results=1, start=0, response_format="json")
        data = json.loads(result)
        assert data["start"] == 0
        assert data["next_offset"] == 1
        assert data["has_more"] is True


@pytest.mark.asyncio
async def test_arxiv_search_json_next_offset_none_when_last_page():
    """Test next_offset is None when no more results."""
    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=SAMPLE_XML_MULTI)
        )
        result = await arxiv_search(client, "test", max_results=2, start=0, response_format="json")
        data = json.loads(result)
        assert data["next_offset"] is None
        assert data["has_more"] is False


# ---- isError tests ----


@pytest.mark.asyncio
async def test_arxiv_summarize_invalid_id_raises_error():
    """Test that arxiv_summarize raises ValueError for invalid paper IDs (isError scenario)."""
    client = ArxivClient()
    with pytest.raises(ValueError, match="Invalid arXiv paper ID format"):
        await arxiv_summarize(client, "rm -rf /")


@pytest.mark.asyncio
async def test_arxiv_get_paper_http_404_raises_runtime_error():
    """Test that arxiv_get_paper raises RuntimeError for HTTP 404 (isError scenario)."""
    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(return_value=httpx.Response(404))
        with pytest.raises(RuntimeError, match="not found"):
            await arxiv_get_paper(client, "2301.99999")


# ---- @mcp.tool integration tests ----


@pytest.mark.asyncio
async def test_tool_registration_and_listing():
    """Test that tools are properly registered with FastMCP (verifies @mcp.tool decorator)."""
    from mcp.server.fastmcp import FastMCP

    test_mcp = FastMCP("test_arxiv")
    from arxiv_mcp_server.tools.search import register_tools as reg_search
    from arxiv_mcp_server.tools.paper import register_tools as reg_paper
    from arxiv_mcp_server.tools.summarize import register_tools as reg_summarize

    reg_search(test_mcp)
    reg_paper(test_mcp)
    reg_summarize(test_mcp)

    tools = await test_mcp.list_tools()
    tool_names = [t.name for t in tools]

    assert "arxiv_search" in tool_names, "arxiv_search tool should be registered"
    assert "arxiv_get_paper" in tool_names, "arxiv_get_paper tool should be registered"
    assert "arxiv_summarize" in tool_names, "arxiv_summarize tool should be registered"

    # Verify Pydantic model schema is included in input schema definitions
    search_tool = next(t for t in tools if t.name == "arxiv_search")
    assert "ArxivSearchInput" in search_tool.inputSchema.get("$defs", {}), (
        "Pydantic model ArxivSearchInput should be defined in tool input schema $defs"
    )


# ---- P2: Structured Output tests ----


class TestPaperResultModel:
    """Test PaperResult Pydantic output model."""

    def test_paper_result_basic(self):
        from arxiv_mcp_server.models import PaperResult

        result = PaperResult(
            title="Test Paper",
            arxiv_id="2301.00001v1",
            authors=["Alice", "Bob"],
            published="2023-01-01T00:00:00Z",
            updated="2023-01-15T00:00:00Z",
            categories=["cs.CV", "cs.LG"],
            summary="Test abstract.",
            doi="10.48550/arXiv.2301.00001",
            journal_ref="NeurIPS 2023",
            pdf_url="https://arxiv.org/pdf/2301.00001",
        )
        assert result.title == "Test Paper"
        assert result.arxiv_id == "2301.00001v1"
        assert result.authors == ["Alice", "Bob"]
        assert result.doi == "10.48550/arXiv.2301.00001"

    def test_paper_result_optional_fields(self):
        from arxiv_mcp_server.models import PaperResult

        result = PaperResult(
            title="Minimal Paper",
            arxiv_id="2301.00002",
            authors=["Author"],
            published="2023-01-01",
            updated="2023-01-01",
            categories=[],
            summary="Minimal.",
        )
        assert result.doi is None
        assert result.journal_ref is None
        assert result.pdf_url is None

    def test_paper_result_serializes_to_json(self):
        from arxiv_mcp_server.models import PaperResult
        import json

        result = PaperResult(
            title="JSON Paper",
            arxiv_id="2301.00003",
            authors=["Test"],
            published="2023-01-01",
            updated="2023-01-01",
            categories=["cs.AI"],
            summary="JSON test.",
        )
        json_str = result.model_dump_json(indent=2)
        data = json.loads(json_str)
        assert data["title"] == "JSON Paper"
        assert data["arxiv_id"] == "2301.00003"
        assert data["authors"] == ["Test"]
        assert data["doi"] is None


class TestSearchResultModel:
    """Test SearchResult Pydantic output model."""

    def test_search_result_basic(self):
        from arxiv_mcp_server.models import SearchResult, PaperResult

        result = SearchResult(
            total=100,
            count=2,
            start=0,
            has_more=True,
            next_offset=2,
            results=[
                PaperResult(
                    title="Paper 1",
                    arxiv_id="2301.00001",
                    authors=["A"],
                    published="2023-01-01",
                    updated="2023-01-01",
                    categories=[],
                    summary="S1",
                ),
                PaperResult(
                    title="Paper 2",
                    arxiv_id="2301.00002",
                    authors=["B"],
                    published="2023-01-02",
                    updated="2023-01-02",
                    categories=[],
                    summary="S2",
                ),
            ],
        )
        assert result.total == 100
        assert result.count == 2
        assert result.has_more is True
        assert result.next_offset == 2
        assert len(result.results) == 2
        assert result.results[0].title == "Paper 1"

    def test_search_result_no_more(self):
        from arxiv_mcp_server.models import SearchResult, PaperResult

        result = SearchResult(
            total=1,
            count=1,
            start=0,
            has_more=False,
            next_offset=None,
            results=[
                PaperResult(
                    title="Only Paper",
                    arxiv_id="2301.00001",
                    authors=["A"],
                    published="2023-01-01",
                    updated="2023-01-01",
                    categories=[],
                    summary="S1",
                ),
            ],
        )
        assert result.has_more is False
        assert result.next_offset is None

    def test_search_result_serializes_to_json(self):
        from arxiv_mcp_server.models import SearchResult, PaperResult
        import json

        result = SearchResult(
            total=50,
            count=1,
            start=0,
            has_more=True,
            next_offset=1,
            results=[
                PaperResult(
                    title="JSON Search",
                    arxiv_id="2301.00001",
                    authors=["A"],
                    published="2023-01-01",
                    updated="2023-01-01",
                    categories=["cs.CV"],
                    summary="S1",
                ),
            ],
        )
        json_str = result.model_dump_json(indent=2)
        data = json.loads(json_str)
        assert data["total"] == 50
        assert data["has_more"] is True
        assert data["next_offset"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["title"] == "JSON Search"


class TestSummarizeResultModel:
    """Test SummarizeResult Pydantic output model."""

    def test_summarize_result_basic(self):
        from arxiv_mcp_server.models import SummarizeResult

        result = SummarizeResult(
            title="Summarized Paper",
            arxiv_id="2301.00001",
            model="claude-sonnet-4-6",
            style="technical",
            summary="This is a generated summary.",
            text_length=5000,
            paper_url="https://arxiv.org/pdf/2301.00001",
        )
        assert result.title == "Summarized Paper"
        assert result.model == "claude-sonnet-4-6"
        assert result.style == "technical"
        assert result.summary == "This is a generated summary."
        assert result.text_length == 5000

    def test_summarize_result_optional_fields(self):
        from arxiv_mcp_server.models import SummarizeResult

        result = SummarizeResult(
            title="T",
            arxiv_id="2301.00001",
            model="m",
            style="technical",
            summary="S",
            text_length=100,
        )
        assert result.paper_url is None

    def test_summarize_result_serializes_to_json(self):
        from arxiv_mcp_server.models import SummarizeResult
        import json

        result = SummarizeResult(
            title="JSON Summary",
            arxiv_id="2301.00001",
            model="claude-sonnet-4-6",
            style="bullet-points",
            summary="- Point 1\n- Point 2",
            text_length=3000,
            paper_url="https://arxiv.org/pdf/2301.00001.pdf",
        )
        json_str = result.model_dump_json(indent=2)
        data = json.loads(json_str)
        assert data["title"] == "JSON Summary"
        assert data["style"] == "bullet-points"
        assert data["text_length"] == 3000
        assert data["paper_url"] == "https://arxiv.org/pdf/2301.00001.pdf"


@pytest.mark.asyncio
async def test_arxiv_search_json_uses_pydantic_model():
    """Test that arxiv_search JSON path outputs consistent structure via Pydantic."""
    import json
    from arxiv_mcp_server.utils.arxiv_api import ArxivClient
    from arxiv_mcp_server.tools.search import arxiv_search

    client = ArxivClient()
    SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/2301.00001v1</id>
        <title>Test Paper</title>
        <summary>Abstract text here.</summary>
        <author><name>Author</name></author>
        <published>2023-01-01T00:00:00Z</published>
        <link title="pdf" href="https://arxiv.org/pdf/2301.00001v1"/>
        <category term="cs.CV"/>
      </entry>
    </feed>"""
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=SAMPLE)
        )
        result = await arxiv_search(client, "test", response_format="json")
        data = json.loads(result)
        # Verify Pydantic-structured output
        assert "results" in data
        assert isinstance(data["results"], list)
        if data["results"]:
            paper = data["results"][0]
            assert "arxiv_id" in paper  # Pydantic uses arxiv_id, not id
            assert "title" in paper
            assert "authors" in paper
            assert "summary" in paper
            assert "doi" in paper  # Optional field should be present (null)


@pytest.mark.asyncio
async def test_arxiv_get_paper_json_uses_pydantic_model():
    """Test that arxiv_get_paper JSON path uses PaperResult model."""
    import json
    from arxiv_mcp_server.utils.arxiv_api import ArxivClient
    from arxiv_mcp_server.tools.paper import arxiv_get_paper

    client = ArxivClient()
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=SAMPLE_XML_SINGLE)
        )
        result = await arxiv_get_paper(client, "2301.00001", response_format="json")
        data = json.loads(result)
        # Verify Pydantic-structured fields
        assert data["arxiv_id"] == "2301.00001v1"
        assert data["title"] == "Sample Paper Title"
        assert isinstance(data["authors"], list)
        assert isinstance(data["categories"], list)
        # Optional fields should be present
        assert "doi" in data
        assert "journal_ref" in data
        assert "pdf_url" in data
