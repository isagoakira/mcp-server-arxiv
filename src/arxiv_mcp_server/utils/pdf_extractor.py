"""PDF text extraction using PyMuPDF."""

from typing import Optional

try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None


MAX_TEXT_LENGTH = 8000


class PDFExtractor:
    """Extract text from PDF files using PyMuPDF."""

    def extract(self, pdf_path: str) -> str:
        """Extract text from PDF, truncated to MAX_TEXT_LENGTH."""
        if not PYMUPDF_AVAILABLE:
            raise RuntimeError("PyMuPDF not installed. Run: pip install PyMuPDF")

        doc = fitz.open(pdf_path)
        try:
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            full_text = "\n".join(text_parts)
        finally:
            doc.close()

        # Truncate if too long
        if len(full_text) > MAX_TEXT_LENGTH:
            return full_text[:MAX_TEXT_LENGTH] + "\n... (truncated)"
        return full_text


# Global instance
_extractor: Optional[PDFExtractor] = None


def get_extractor() -> PDFExtractor:
    global _extractor
    if _extractor is None:
        _extractor = PDFExtractor()
    return _extractor
