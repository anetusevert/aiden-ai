# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set uv environment variables
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_SYSTEM_PYTHON=1

# Copy dependency files first for better caching
# README.md is required by pyproject.toml during dependency resolution
COPY pyproject.toml uv.lock* README.md ./

# Install dependencies (avoid --frozen when lockfile lags pyproject, e.g. new deps)
RUN uv sync --no-dev

# Copy source code
COPY . .

# Install the project with dev dependencies for development
RUN uv sync

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
