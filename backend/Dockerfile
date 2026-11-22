# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
WORKDIR /app

# ---------- dev: all deps, source mounted, reload ----------
FROM base AS dev
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project
COPY . .
CMD ["sh", "-c", "alembic upgrade head && python -m app.scripts.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]

# ---------- prod: runtime deps only ----------
FROM base AS prod
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY . .
RUN useradd --system --uid 1001 app && chown -R app /app
USER app
CMD ["sh", "-c", "alembic upgrade head && python -m app.scripts.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips='*'"]
