"""Pydantic models for arxiv_search tool."""

from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class ResponseFormat(str, Enum):
    """Output format for search results."""

    MARKDOWN = "markdown"
    JSON = "json"


class ArxivSearchInput(BaseModel):
    """Input parameters for arxiv_search tool."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Search query",
        min_length=1,
        max_length=500,
    )
    max_results: int = Field(
        default=5,
        description="Maximum number of results (1-100)",
        ge=1,
        le=100,
    )
    search_in: str = Field(
        default="all",
        description="Search field: all, title, abstract, author",
    )
    sort_by: str = Field(
        default="relevance",
        description="Sort by: relevance, submittedDate",
    )
    start: int = Field(
        default=0,
        description="Result offset for pagination",
        ge=0,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: markdown or json",
    )
