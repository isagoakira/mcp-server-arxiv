"""Tests for pdf_downloader.py."""

import os
import pytest
import respx
import httpx

from arxiv_mcp_server.utils.pdf_downloader import PDFDownloader


@pytest.fixture
def downloader():
    """Create a fresh PDFDownloader for each test."""
    inst = PDFDownloader()
    yield inst


class TestPDFDownloader:
    @pytest.mark.asyncio
    async def test_download_success(self, downloader, tmp_path, monkeypatch):
        """Test successful PDF download."""
        # Point cache to tmp dir
        monkeypatch.setattr("arxiv_mcp_server.utils.pdf_downloader._downloaded_pdfs", set())

        pdf_content = b"%PDF-1.4 fake pdf content for testing"
        with respx.mock:
            route = respx.get("https://arxiv.org/pdf/2301.00001").mock(
                return_value=httpx.Response(
                    200,
                    content=pdf_content,
                    headers={"content-type": "application/pdf"},
                )
            )

            # Use download method - it writes to /tmp/ so we can't easily mock the path
            # Instead, test that the HTTP call is made correctly
            try:
                path = await downloader.download("2301.00001", "https://arxiv.org/pdf/2301.00001")
                assert os.path.exists(path)
                with open(path, "rb") as f:
                    assert f.read() == pdf_content
            finally:
                # Cleanup
                if os.path.exists(path):
                    os.remove(path)

            assert route.called

    @pytest.mark.asyncio
    async def test_download_verifies_pdf_magic_bytes(self, downloader):
        """Test that non-PDF content raises ValueError."""
        with respx.mock:
            respx.get("https://arxiv.org/pdf/2301.00001").mock(
                return_value=httpx.Response(
                    200,
                    content=b"not a pdf",
                    headers={"content-type": "text/html"},
                )
            )

            with pytest.raises(ValueError, match="did not return a PDF"):
                await downloader.download("2301.00001", "https://arxiv.org/pdf/2301.00001")

    @pytest.mark.asyncio
    async def test_download_http_error(self, downloader):
        """Test that HTTP errors propagate."""
        with respx.mock:
            respx.get("https://arxiv.org/pdf/2301.00001").mock(return_value=httpx.Response(404))

            with pytest.raises(httpx.HTTPStatusError):
                await downloader.download("2301.00001", "https://arxiv.org/pdf/2301.00001")

    def test_get_downloader_singleton(self):
        """Test that get_downloader returns singleton."""
        from arxiv_mcp_server.utils.pdf_downloader import get_downloader

        d1 = get_downloader()
        d2 = get_downloader()
        assert d1 is d2
