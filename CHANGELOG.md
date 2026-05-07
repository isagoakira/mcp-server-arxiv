# Changelog

## [0.2.0] — 2026-05-07

### Added
- Docker multi-stage build support (Dockerfile + .dockerignore)
- GitHub Actions workflow for PyPI publishing
- CHANGELOG.md for version tracking
- Input validation for arXiv paper IDs
- Temp file cleanup mechanism for downloaded PDFs
- Helper functions: `build_search_query()`, `format_search_results()`, `normalize_paper_id()`, `format_paper_details()`, `build_pdf_link()`

### Changed
- Refactored search.py and paper.py to eliminate duplicated code between MCP handlers and standalone functions
- Version bumped from 0.1.0 → 0.2.0
- Updated pyproject.toml classifiers, author email, and project URLs
- Improved README with complete installation instructions

### Fixed
- Fixed typo in search tool description: "relevance/relevance/submittedDate" → "relevance/submittedDate"
- Added proper error handling to `arxiv_summarize()` standalone function
- Fixed placeholder URLs in README_zh.md

## [0.1.0] — 2026-05-06

### Added
- Initial MCP server implementation with stdio transport
- `arxiv_search` tool — search papers with query/filter/sort options
- `arxiv_get_paper` tool — retrieve full metadata by arXiv ID
- `arxiv_summarize` tool — download PDF and summarize via LLM
- ArxivClient with rate-limited async HTTP (5s interval)
- PDF downloader with caching and content-type verification
- PDF text extractor using PyMuPDF (8000 char truncation)
- Multi-backend LLM summarizer (Anthropic Claude)
- Structured logging via structlog
- Test suite: rate limiter, API parsing, mock HTTP, smoke tests, integration tests
- CI pipeline (GitHub Actions): lint + test on 3.10/3.11/3.12 + build
- Documentation: README (EN/ZH), CLAUDE.md, examples, dev-plan, TODO
