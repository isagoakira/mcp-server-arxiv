"""Pydantic models for arxiv_get_paper tool."""

from pydantic import BaseModel, Field, ConfigDict

from .search import ResponseFormat


class ArxivPaperInput(BaseModel):
    """Input parameters for arxiv_get_paper tool."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    paper_id: str = Field(
        ...,
        description="arXiv paper ID (e.g., 1706.03762 or 1706.03762v5)",
        min_length=1,
        max_length=100,
    )
    include_pdf_link: bool = Field(
        default=True,
        description="Include PDF download link in the response",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: markdown or json",
    )
