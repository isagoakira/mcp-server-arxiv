"""PDF downloader for arXiv papers."""
import os
from typing import Optional

import httpx


class PDFDownloader:
    """Download arXiv PDFs with caching."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=60.0,
                follow_redirects=True,
                headers={"User-Agent": "mcp-server-arxiv/0.1 (mailto:isago@example.com)"},
            )
        return self._client

    async def download(self, paper_id: str, pdf_url: str) -> str:
        """Download PDF to /tmp/arxiv_{id}.pdf, return local path."""
        # Check cache
        cache_path = f"/tmp/arxiv_{paper_id.replace('/', '_')}.pdf"
        if os.path.exists(cache_path):
            return cache_path

        # Download
        client = await self._get_client()
        response = await client.get(pdf_url)
        response.raise_for_status()

        # Verify it's actually a PDF
        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not response.content.startswith(b"%PDF"):
            raise ValueError(f"URL did not return a PDF: {content_type}")

        # Save to cache
        with open(cache_path, "wb") as f:
            f.write(response.content)

        return cache_path

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# Global instance
_downloader: Optional[PDFDownloader] = None


def get_downloader() -> PDFDownloader:
    global _downloader
    if _downloader is None:
        _downloader = PDFDownloader()
    return _downloader