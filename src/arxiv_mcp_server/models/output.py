"""Pydantic output models for structured tool responses.

Provides type-validated output schemas that replace raw json.dumps() calls
in the JSON-formatted tool responses. These models ensure consistent field
naming, typing, and serialization across all tools.
"""

from typing import Optional

from pydantic import BaseModel, Field


class PaperResult(BaseModel):
    """Structured paper metadata output model.

    Represents a single arXiv paper with all metadata fields.
    Used by search, paper, and summarize tools for JSON-formatted responses.
    """

    title: str = Field(description="Paper title")
    arxiv_id: str = Field(description="arXiv paper ID (e.g., 1706.03762v1)")
    authors: list[str] = Field(description="List of author names")
    published: str = Field(description="Publication date (ISO 8601)")
    updated: str = Field(description="Last update date (ISO 8601)")
    categories: list[str] = Field(description="arXiv category labels")
    summary: str = Field(description="Paper abstract text")
    doi: Optional[str] = Field(default=None, description="Digital Object Identifier")
    journal_ref: Optional[str] = Field(default=None, description="Journal reference string")
    pdf_url: Optional[str] = Field(default=None, description="Direct PDF download URL")


class SearchResult(BaseModel):
    """Structured search results with pagination metadata.

    Returned when arxiv_search is called with response_format="json".
    Includes total result count, current page info, and next-page offset
    for implementing client-side pagination.
    """

    total: int = Field(description="Total number of matching results")
    count: int = Field(description="Number of results in this response")
    start: int = Field(description="Zero-based offset of the current page")
    has_more: bool = Field(description="Whether more results are available")
    next_offset: Optional[int] = Field(
        default=None,
        description="Offset for the next page, or None if on the last page",
    )
    results: list[PaperResult] = Field(description="List of paper results on this page")


class SummarizeResult(BaseModel):
    """Structured summarization output model.

    Returned when arxiv_summarize is called with response_format="json".
    Contains the generated summary along with paper metadata and processing info.
    """

    title: str = Field(description="Paper title")
    arxiv_id: str = Field(description="arXiv paper ID")
    model: str = Field(description="LLM model used for summarization")
    style: str = Field(description="Summary style (technical, beginner-friendly, bullet-points)")
    summary: str = Field(description="Generated summary text")
    text_length: int = Field(description="Length of the extracted PDF text in characters")
    paper_url: Optional[str] = Field(default=None, description="URL to the paper PDF")
