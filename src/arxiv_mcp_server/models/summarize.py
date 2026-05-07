"""Pydantic models for arxiv_summarize tool."""

from pydantic import BaseModel, Field, ConfigDict

from .search import ResponseFormat


class ArxivSummarizeInput(BaseModel):
    """Input parameters for arxiv_summarize tool."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    paper_id: str = Field(
        ...,
        description="arXiv paper ID to summarize",
        min_length=1,
        max_length=100,
    )
    model: str = Field(
        default="claude-sonnet-4-6",
        description="LLM model to use for summarization",
    )
    style: str = Field(
        default="technical",
        description="Summary style: technical, beginner-friendly, bullet-points",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: markdown or json",
    )
