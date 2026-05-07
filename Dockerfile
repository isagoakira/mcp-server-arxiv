# mcp-server-arxiv — Docker image
# Multi-stage build for minimal final image

FROM python:3.11-slim AS builder

WORKDIR /build
COPY . .

RUN pip install --no-cache-dir build && \
    pip install --no-cache-dir ".[pdf,anthropic]" && \
    python -m build --wheel

# ---- Runtime image ----
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/mcp_server_arxiv-*.whl && \
    rm /tmp/mcp_server_arxiv-*.whl

ENV ANTHROPIC_API_KEY=""
EXPOSE 8000

ENTRYPOINT ["arxiv-mcp"]
