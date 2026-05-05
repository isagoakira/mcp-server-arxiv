# mcp-server-arxiv

> MCP Server for ArXiv paper search and summarization.
> Enable AI Coding Agents to search, retrieve, and summarize ArXiv papers.

[![PyPI version](https://img.shields.io/pypi/v/mcp-server-arxiv.svg)](https://pypi.org/project/mcp-server-arxiv/)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Features

- **Paper Search** — Search ArXiv with title/author/abstract/category filters
- **Paper Details** — Get full metadata for a specific paper
- **AI Summarization** — Download PDF and summarize with LLM

## Installation

### From PyPI (coming soon)

```bash
pip install mcp-server-arxiv
```

### From Source

```bash
git clone https://github.com/isagoakira/mcp-server-arxiv.git

## Quick Start

```bash
# Activate virtual environment
source .venv/bin/activate  # macOS/Linux

# Run MCP server (stdio mode — start from Claude Code)
python -m arxiv_mcp_server

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
```

## Claude Code Setup

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "arxiv": {
      "command": "python",
      "args": ["-m", "arxiv_mcp_server"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

Or from project directory (for development):

```json
{
  "mcpServers": {
    "arxiv": {
      "command": "/path/to/mcp-server-arxiv/.venv/bin/python",
      "args": ["-m", "arxiv_mcp_server"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `arxiv_search` | Search arXiv papers with query, sort, and filter options |
| `arxiv_get_paper` | Get full metadata for a specific paper by ID |
| `arxiv_summarize` | Download PDF and summarize with LLM |

### arxiv_search

```json
{
  "query": "transformer attention",
  "max_results": 5,
  "search_in": "all",
  "sort_by": "relevance"
}
```

### arxiv_get_paper

```json
{
  "paper_id": "1706.03762",
  "include_pdf_link": true
}
```

### arxiv_summarize

```json
{
  "paper_id": "1706.03762",
  "model": "claude-sonnet-4-6",
  "style": "technical"
}
```

Supported styles: `technical`, `beginner-friendly`, `bullet-points`

## Usage Examples

```
User: Find 5 recent papers on hyperspectral image fusion
User: Summarize paper 2305.12345 in bullet-point style
User: Who wrote "Attention Is All You Need"?
```

## Development

```bash
# Clone and setup
git clone https://github.com/isago/mcp-server-arxiv.git
cd mcp-server-arxiv

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[pdf,anthropic,dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=arxiv_mcp_server --cov-report=term-missing

# Lint and format
ruff check src/ tests/ --fix
ruff format src/ tests/
```

## Architecture

```
src/arxiv_mcp_server/
├── server.py          # MCP Server (stdio transport)
├── __main__.py        # Entry: python -m arxiv_mcp_server
├── tools/
│   ├── search.py      # arxiv_search
│   ├── paper.py       # arxiv_get_paper
│   └── summarize.py  # arxiv_summarize
└── utils/
    ├── arxiv_api.py    # ArxivClient (rate-limited HTTP)
    ├── rate_limiter.py
    ├── pdf_downloader.py
    ├── pdf_extractor.py
    └── summarizer.py   # Multi-backend LLM
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please open an issue or submit a PR.