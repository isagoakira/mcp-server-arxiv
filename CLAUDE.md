# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`mcp-server-arxiv` — an MCP Server that exposes arXiv paper search and summarization as standard Tool interfaces for AI Coding Agents (Claude Code, Cursor, OpenCode).

## Common Commands

```bash
# Install dependencies
pip install -e ".[pdf,anthropic,dev]"

# Run MCP server (stdio mode)
python -m arxiv_mcp_server

# Run tests (skip integration tests by default)
pytest tests/ -v -m "not integration"

# Run with coverage
pytest tests/ --cov=arxiv_mcp_server --cov-report=term-missing

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Build distribution
pip install build && python -m build
```

## Architecture

```
src/arxiv_mcp_server/
├── server.py          # MCP Server instance — merges all tool MCPs
├── tools/
│   ├── search.py      # arxiv_search tool
│   ├── paper.py       # arxiv_get_paper tool
│   └── summarize.py   # arxiv_summarize tool (PDF + LLM)
└── utils/
    ├── arxiv_api.py    # ArxivClient — async HTTP client with rate limiting (5s/request)
    ├── pdf_downloader.py
    ├── pdf_extractor.py
    └── summarizer.py   # LLM calls (Anthropic/OpenAI/Ollama)
```

**Key tech choices:**
- `feedparser` for Atom XML parsing (arXiv API returns Atom XML)
- `httpx` async client with `follow_redirects=True` for PDF downloads
- Rate limit: 1 request / 3 seconds (code enforces 5s gap)
- PDF text truncated to 8000 chars before sending to LLM

## Important Conventions

- MCP tools use `@mcp.tool()` decorator
- ArxivClient is a shared singleton; rate limiting uses `time.monotonic()`
- Paper IDs: strip `v\d+` suffix before API query (handles both `1706.03762` and `1706.03762v5`)
- Search query prefixes: `all`, `ti` (title), `abs` (abstract), `au` (author), `cat` (category)
- All API responses logged via `structlog`