FROM python:3.11-slim

WORKDIR /app

# Install uv for fast package installation
RUN pip install --no-cache-dir uv

# Copy package definition first for layer caching
COPY pyproject.toml README.md ./
COPY usaspending_mcp/ ./usaspending_mcp/

# Install the package (runtime deps only)
RUN uv pip install --system --no-cache .

ENV USASPENDING_MCP_TRANSPORT=http
ENV USASPENDING_MCP_HOST=0.0.0.0
ENV USASPENDING_MCP_PORT=8765

EXPOSE 8765

CMD ["usaspending-mcp-http"]
