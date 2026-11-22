# Project Mentat

A learning app built to learn anything, starting with the mathematics of No-Limit Hold'em.
See [SPEC.md](SPEC.md) for the product and technical spec.

## Stack

FastAPI · SQLAlchemy 2 (async) · Alembic · Postgres 16 · React 19 · TypeScript · Tailwind + shadcn/ui · Redux Toolkit + RTK Query · Docker Compose · nginx

## Prerequisites

Docker (with Compose v2), [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/) 10, Node 22.

## Quick start

```bash
make setup   # local deps (for IDE/lint), .env, pre-commit hooks
make up      # db + api + web; migrations and seed run on api start
```

| URL | What |
|---|---|
| http://localhost:5173 | Frontend (Vite, hot reload) |
| http://localhost:8000/api/docs | API docs (Swagger) |
| http://localhost:8000/api/v1/health | Health check |

## Common commands

```bash
make help                     # everything
make logs s=api               # tail a service
make migration m="add decks"  # autogenerate migration
make migrate                  # apply migrations
make gen-api                  # backend changed? regenerate the typed frontend client
make check                    # lint + typecheck + tests (stack must be up for api tests)
make psql                     # DB shell
```

**API contract workflow:** change Pydantic schemas or routes → `make gen-api` → commit
`frontend/openapi.json` and `frontend/src/api/generated.ts`. CI fails if they drift.

## Production (self-hosted)

```bash
make prod-up      # db + api + nginx on http://localhost (port 80)
make backup       # pg_dump to ./backups (14-day retention), cron this nightly
make restore f=backups/mentat-YYYYMMDD-HHMMSS.dump
```

Override the bind address/port with `HTTP_BIND` / `HTTP_PORT` in `.env`. Public access via a
Cloudflare Tunnel subdomain is planned (see SPEC §3); auth must land first.
