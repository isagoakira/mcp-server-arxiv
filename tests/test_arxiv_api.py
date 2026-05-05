"""Tests for arxiv_api.py - ArxivClient class."""
import pytest
import respx
import httpx



@pytest.mark.asyncio
async def test_parse_single_entry(arxiv_client, sample_xml):
    """Test parsing a single entry from XML."""
    papers = arxiv_client._parse_feed(sample_xml)
    assert len(papers) == 1
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
    papers = arxiv_client._parse_feed(sample_xml_multi)
    assert len(papers) == 2
    assert papers[0]["id"] == "2301.00001v1"
    assert papers[1]["id"] == "2301.00002v1"


@pytest.mark.asyncio
async def test_search_with_mock(arxiv_client, sample_xml):
    """Test search with mocked HTTP response."""
    with respx.mock:
        respx.get("http://export.arxiv.org/api/query").mock(
            return_value=httpx.Response(200, text=sample_xml)
        )
        results = await arxiv_client.search("test query", max_results=5)
        assert len(results) == 1
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