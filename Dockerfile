FROM python:3.14-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --link-mode=copy --no-install-project

COPY . .

RUN uv sync --frozen --no-dev  --link-mode=copy

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/logs \
    && chown -R app:app /app/logs

USER app

CMD ["uv", "run", "--no-sync", "mcp-data-gw"]
