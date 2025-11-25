# Build stage
FROM python:3.12-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Add source code
ADD src /app/src
RUN touch ./README.md

# Install dependencies and build the project
RUN uv sync --frozen --no-dev

# Runtime stage
FROM python:3.12-slim

# add labels
LABEL author="Tim M. Schendzielorz <docker@tim.schendzielorz.com>"
LABEL version="0.3.0"
LABEL description="A Model Context Protocol server that provides access to BigQuery. This server enables LLMs to inspect database schemas and execute queries."

# Create non-root user
RUN groupadd -r mcpuser && useradd -r -g mcpuser -u 1000 mcpuser

# Set working directory
WORKDIR /app

# Copy only the virtual environment and source from builder
COPY --from=builder --chown=mcpuser:mcpuser /app/.venv /app/.venv
COPY --from=builder --chown=mcpuser:mcpuser /app/src /app/src

# Set environment to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Set default transport to stdio (can be overridden with MCP_TRANSPORT env var)
ENV MCP_TRANSPORT=stdio

# Switch to non-root user
USER mcpuser

WORKDIR /app/src

# Define the entry point
ENTRYPOINT ["mcp-server-bigquery"]

# Example commands:
# For stdio: CMD []
# For HTTP: Set MCP_TRANSPORT=http and optionally PORT=8080
# CMD ["--transport", "http", "--port", "8080"]
