FROM python:3.12-slim

# Install Node.js 20 (for mcp-gdelt)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN uv sync --no-dev

EXPOSE 8080

CMD ["uv", "run", "python", "src/server.py"]
