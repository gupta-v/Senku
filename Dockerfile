FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install deps first (layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

RUN chmod +x docker-entrypoint.sh

EXPOSE 8000
EXPOSE 8081 8082 8083 8084

# APP_MODE=api (default) → uvicorn FastAPI
# APP_MODE=mcp           → MCP servers (8081-8084)
ENTRYPOINT ["./docker-entrypoint.sh"]
