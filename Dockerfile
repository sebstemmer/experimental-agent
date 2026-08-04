FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# dann der Code (ändert sich oft, invalidiert nur diesen Layer)
COPY channels/ channels/
COPY postgres_mcp/ postgres_mcp/
COPY emails/ emails/
COPY utils/ utils/

RUN mkdir /app/agent_folder

CMD ["/app/.venv/bin/python", "-m", "channels.telegram.main"]
