"""Tests for arxiv_api.py - ArxivClient class."""

import pytest
import respx
import httpx


@pytest.mark.asyncio
async def test_parse_single_entry(arxiv_client, sample_xml):
    """Test parsing a single entry from XML."""
    papers, total = arxiv_client._parse_feed(sample_xml)
    assert len(papers) == 1
    assert total == 1
    assert papers[0]["id"] == "2301.00001v1"
    assert papers[0]["title"] == "Sample Paper Title"
    assert papers[0]["authors"] == ["Test Author", "Another Author"]
    assert papers[0]["pdf_url"] == "https://arxiv.org/pdf/2301.00001v1"
    assert papers[0]["categories"] == ["cs.CV", "cs.LG"]
    assert papers[0]["comment"] == "33 pages, 8 figures"
    assert papers[0]["doi"] == "10.48550/arXiv.2301.00001"


@pytest.mark.asyncio
async def test_parse_multiple_entries(arxiv_client, sample_xml_multi):
    """Test parsing multiple entries."""
    papers, total = arxiv_client._parse_feed(sample_xml_multi)
    assert len(papers) == 2
    assert total == 2
    assert papers[0]["id"] == "2301.00001v1"
    assert papers[1]["id"] == "2301.00002v1"


@pytest.mark.asyncio
async def test_search_with_mock(arxiv_client, sample_xml):
    """Test search with mocked HTTP response."""
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=sample_xml)
        )
        results, total = await arxiv_client.search("test query", max_results=5)
        assert len(results) == 1
        assert total == 1
        assert "title" in results[0]
        assert results[0]["id"] == "2301.00001v1"


@pytest.mark.asyncio
async def test_get_paper_by_id(arxiv_client, sample_xml):
    """Test getting a single paper by ID."""
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=sample_xml)
        )
        paper = await arxiv_client.get_paper("2301.00001")
        assert paper is not None
        assert paper["id"] == "2301.00001v1"


@pytest.mark.asyncio
async def test_get_paper_with_version_suffix(arxiv_client, sample_xml):
    """Test getting paper ID with version suffix stripped."""
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=sample_xml)
        )
        paper = await arxiv_client.get_paper("2301.00001v1")
        assert paper is not None
        assert paper["id"] == "2301.00001v1"


@pytest.mark.asyncio
async def test_search_params_passed_correctly(arxiv_client, sample_xml):
    """Test that search parameters are correctly passed to API."""
    with respx.mock:
        route = respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=sample_xml)
        )
        await arxiv_client.search("transformer", max_results=10, sort_by="submittedDate")

        # Check the request was made with correct params
        assert route.called
        request = route.calls[0].request
        # ArxivClient.search() receives raw query, field prefix added by caller
        assert "search_query=transformer" in str(request.url)
        assert "max_results=10" in str(request.url)
        assert "sortBy=submittedDate" in str(request.url)


@pytest.mark.asyncio
async def test_parse_feed_with_opensearch_total(arxiv_client):
    """Test parsing opensearch:totalResults from feed."""
    import textwrap

    xml_with_total = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
      <opensearch:totalResults>42</opensearch:totalResults>
      <opensearch:startIndex>0</opensearch:startIndex>
      <opensearch:itemsPerPage>10</opensearch:itemsPerPage>
      <entry>
        <id>http://arxiv.org/abs/2301.00001v1</id>
        <title>Test Paper</title>
        <summary>Abstract.</summary>
        <author><name>Author</name></author>
        <published>2023-01-01T00:00:00Z</published>
        <link title="pdf" href="https://arxiv.org/pdf/2301.00001v1"/>
        <category term="cs.CV"/>
      </entry>
    </feed>""")
    papers, total = arxiv_client._parse_feed(xml_with_total)
    assert total == 42
    assert len(papers) == 1


@pytest.mark.asyncio
async def test_parse_feed_without_opensearch_total(arxiv_client, sample_xml):
    """Test fallback to len(entries) when opensearch:totalResults absent."""
    papers, total = arxiv_client._parse_feed(sample_xml)
    assert total == len(papers)


# ---- HTTP error handling tests ----

SAMPLE_XML_SINGLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2301.00001v1</id>
    <title>Sample Paper Title</title>
    <summary>Abstract.</summary>
    <author><name>Test Author</name></author>
    <published>2023-01-01T00:00:00Z</published>
    <link title="pdf" href="https://arxiv.org/pdf/2301.00001v1"/>
    <category term="cs.CV"/>
  </entry>
</feed>"""


@pytest.mark.asyncio
async def test_search_http_404_raises_runtime_error(arxiv_client):
    """Test that search raises RuntimeError for HTTP 404."""
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(return_value=httpx.Response(404))
        with pytest.raises(RuntimeError, match="not found"):
            await arxiv_client.search("test query")


@pytest.mark.asyncio
async def test_search_http_403_raises_runtime_error(arxiv_client):
    """Test that search raises RuntimeError for HTTP 403."""
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(return_value=httpx.Response(403))
        with pytest.raises(RuntimeError, match="Access denied"):
            await arxiv_client.search("test query")


@pytest.mark.asyncio
async def test_search_http_429_raises_runtime_error(arxiv_client):
    """Test that search raises RuntimeError for HTTP 429 (rate limit)."""
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(return_value=httpx.Response(429))
        with pytest.raises(RuntimeError, match="Rate limit exceeded"):
            await arxiv_client.search("test query")


@pytest.mark.asyncio
async def test_search_http_500_raises_httpx_error(arxiv_client):
    """Test that search still raises httpx.HTTPStatusError for unexpected codes (500)."""
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(return_value=httpx.Response(500))
        with pytest.raises(httpx.HTTPStatusError):
            await arxiv_client.search("test query")


@pytest.mark.asyncio
async def test_get_paper_http_404_raises_runtime_error(arxiv_client):
    """Test that get_paper raises RuntimeError for HTTP 404."""
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(return_value=httpx.Response(404))
        with pytest.raises(RuntimeError, match="not found"):
            await arxiv_client.get_paper("2301.99999")


@pytest.mark.asyncio
async def test_get_paper_validates_id_in_api_layer(arxiv_client):
    """Test that ArxivClient.get_paper() still validates paper ID (API-layer defense)."""
    with pytest.raises(ValueError, match="Invalid arXiv paper ID format"):
        await arxiv_client.get_paper("rm -rf /")


@pytest.mark.asyncio
async def test_get_paper_passes_valid_id(arxiv_client):
    """Test that valid paper ID passes validation and calls API."""
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=SAMPLE_XML_SINGLE)
        )
        paper = await arxiv_client.get_paper("2301.00001")
        assert paper is not None
        assert paper["id"] == "2301.00001v1"
