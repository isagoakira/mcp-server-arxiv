# Claude Code 使用示例

## 在 Claude Code 中使用 mcp-server-arxiv

### 1. 配置

首先在 `~/.claude/settings.json` 中添加配置：

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

### 2. 验证配置

启动 Claude Code 并输入 `/mcp` 检查 arxiv 是否在列表中。

### 3. 使用示例

#### 搜索论文

```
Search for 5 recent papers on transformer attention mechanisms
```

Claude Code 会调用 `arxiv_search` 工具，返回格式化后的论文列表。

#### 获取论文详情

```
Get details for paper 1706.03762
```

#### 总结论文

```
Summarize paper 2305.12345 in bullet-point style using claude-sonnet-4-6
```

### 4. 工作流程示例

```
User: Find recent papers on diffusion models for image generation
User: Summarize the most cited one in technical style
User: Show me the PDF link for the first paper
```

## 提示

- 使用 `search_in` 参数可以限定搜索范围：`title`、`abstract`、`author`
- `sort_by` 可以是 `relevance`、`submittedDate`、`lastUpdatedDate`
- 总结风格支持：`technical`、`beginner-friendly`、`bullet-points`

## 降级处理

如果 `arxiv_summarize` 失败（PyMuPDF 未安装），错误信息会明确提示：

```
Error: PyMuPDF not installed. Run: pip install PyMuPDF
```

同类工具 `arxiv_search` 和 `arxiv_get_paper` 不依赖 PDF，无影响。