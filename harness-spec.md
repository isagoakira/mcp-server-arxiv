# 技术规范: arXiv MCP Server 标准化改进

## 目标

将现有 arXiv MCP Server 从底层 `mcp.server.Server` API 迁移到 `FastMCP` 框架，
并落实 MCP 最佳实践规范。

## 架构变更

### 当前架构 (底层 Server API)
```
server.py → 低层 Server + stdio transport
  ├── tools/search.py  → 手动 list_tools/call_tool 模式
  ├── tools/paper.py   → 同上
  └── tools/summarize.py → 同上
```

### 目标架构 (FastMCP)
```
server.py → FastMCP + lifespan 管理
  ├── models/         → 共享 Pydantic 输入模型 (新增)
  ├── tools/search.py  → @mcp.tool 装饰器
  ├── tools/paper.py   → @mcp.tool 装饰器
  └── tools/summarize.py → @mcp.tool 装饰器 + Context 进度
```

## 关键设计决策

### 1. FastMCP 命名
```
mcp = FastMCP("arxiv_mcp")
```

### 2. ArxivClient 单例管理
通过 FastMCP lifespan 管理客户端生命周期：
```python
@asynccontextmanager
async def app_lifespan():
    client = ArxivClient()
    yield {"client": client}
    await client.close()
```

### 3. 共享 Pydantic 模型
```
models/__init__.py → 导出所有模型
models/search.py   → ArxivSearchInput (query/max_results/search_in/sort_by/start/response_format)
models/paper.py    → ArxivPaperInput (paper_id/include_pdf_link)
models/summarize.py → ArxivSummarizeInput (paper_id/model/style)
```

### 4. 工具注解策略
| 工具 | readOnlyHint | destructiveHint | idempotentHint | openWorldHint |
|------|-------------|----------------|---------------|--------------|
| arxiv_search | true | false | true | true |
| arxiv_get_paper | true | false | true | true |
| arxiv_summarize | false | false | false | true |

### 5. 响应格式
- 默认: Markdown (人类可读)
- 支持 `response_format="json"` 参数返回 JSON

### 6. 错误处理
- 使用 `isError: true` 结构化错误响应
- 错误消息包含可行的下一步建议

## 保留的现有行为
- DOI: 10.48550/arXiv.XXXXX → 显示为超链接
- PDF 链接: https://arxiv.org/pdf/XXXXX.pdf
- 分类标签: cs.CV, cs.LG 格式
- 摘要截断: 500 字符
- 作者截断: 前 3 个 + "et al."
- arXiv ID 验证模式
- 速率限制: 5 秒间隔
