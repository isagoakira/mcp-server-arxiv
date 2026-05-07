# mcp-server-arxiv

> ArXiv 论文搜索与摘要的 MCP Server。
> 让 AI Coding Agent 直接搜索、获取、总结 arXiv 论文。

## 功能特性

- **论文搜索** — 支持按标题/作者/摘要/分类筛选搜索 arXiv
- **论文详情** — 获取单篇论文的完整元信息
- **AI 摘要** — 下载 PDF 并用 LLM 总结核心贡献

## 安装

```bash
pip install mcp-server-arxiv
```

或从源码安装：

```bash
git clone https://github.com/isagoakira/mcp-server-arxiv.git
cd mcp-server-arxiv
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[pdf,anthropic,dev]"
```

## Claude Code 配置

添加到 `~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "arxiv": {
      "command": "python",
      "args": ["-m", "arxiv_mcp_server"],
      "env": {
        "ANTHROPIC_API_KEY": "your-key-here"
      }
    }
  }
}
```

## 工具列表

| 工具 | 说明 |
|------|------|
| `arxiv_search` | 搜索 arXiv 论文，支持查询、排序和筛选 |
| `arxiv_get_paper` | 根据 ID 获取论文完整元数据 |
| `arxiv_summarize` | 下载 PDF 并用 LLM 摘要 |

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

## 使用示例

```
用户：搜索 5 篇关于 hyperspectral image fusion 的最新论文
用户：用 bullet-point 风格总结 2305.12345 这篇论文
用户：谁写了 "Attention Is All You Need"？
```

## 开发

```bash
# 克隆并设置
git clone https://github.com/yourname/mcp-server-arxiv.git
cd mcp-server-arxiv

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e ".[pdf,anthropic,dev]"

# 运行测试
pytest tests/ -v

# 带覆盖率
pytest tests/ --cov=arxiv_mcp_server --cov-report=term-missing

# 代码格式化
ruff format src/ tests/

# 代码检查
ruff check src/ tests/
```

## 许可证

MIT