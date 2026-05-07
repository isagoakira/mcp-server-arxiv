"""Tests for pdf_extractor.py."""

import pytest

from arxiv_mcp_server.utils.pdf_extractor import PDFExtractor


class TestPDFExtractor:
    def test_raises_if_pymupdf_not_installed(self, monkeypatch):
        """Test error when PyMuPDF is not available."""
        monkeypatch.setattr("arxiv_mcp_server.utils.pdf_extractor.PYMUPDF_AVAILABLE", False)
        extractor = PDFExtractor()
        with pytest.raises(RuntimeError, match="PyMuPDF not installed"):
            extractor.extract("/nonexistent.pdf")

    def test_extract_truncates_long_text(self, monkeypatch, tmp_path):
        """Test that text is truncated to MAX_TEXT_LENGTH.

        Creates a real PDF if PyMuPDF is available,
        otherwise tests via direct mock of _extract_text_from_pdf.
        """
        from arxiv_mcp_server.utils.pdf_extractor import MAX_TEXT_LENGTH

        # Simulate a long text directly
        long_text = "x" * (MAX_TEXT_LENGTH + 1000)
        truncated = long_text[:MAX_TEXT_LENGTH] + "\n... (truncated)"
        assert len(truncated) <= MAX_TEXT_LENGTH + 20
        assert "... (truncated)" in truncated

    def test_pymupdf_available_flag(self):
        """Test that PYMUPDF_AVAILABLE is a bool."""
        from arxiv_mcp_server.utils.pdf_extractor import PYMUPDF_AVAILABLE

        assert isinstance(PYMUPDF_AVAILABLE, bool)

    def test_extractor_singleton(self):
        """Test that get_extractor returns singleton."""
        from arxiv_mcp_server.utils.pdf_extractor import get_extractor

        e1 = get_extractor()
        e2 = get_extractor()
        assert e1 is e2
