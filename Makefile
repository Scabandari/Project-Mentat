SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE      := docker compose
COMPOSE_PROD := docker compose -f docker-compose.yml -f docker-compose.prod.yml
API          := $(COMPOSE) exec api
DB_USER      ?= mentat
DB_NAME      ?= mentat

.PHONY: help setup up down restart build ps logs prod-up prod-down prod-logs \
        migrate migration downgrade seed psql db-reset backup restore \
        test test-api test-web lint fmt typecheck check gen-api \
        shell-api shell-web clean

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-14s\033[0m %s\n", $$1, $$2}'

# ---------- Setup ----------
setup: ## Install local deps (uv, pnpm), create .env, install pre-commit
	@test -f .env || cp .env.example .env
	cd backend && uv sync
	cd frontend && pnpm install
	uvx pre-commit install

# ---------- Dev stack ----------
up: ## Start dev stack (db, api, web) and wait until healthy
	$(COMPOSE) up -d --build --wait

down: ## Stop dev stack
	$(COMPOSE) down

restart: ## Restart a service: make restart s=api
	$(COMPOSE) restart $(s)

build: ## Rebuild images
	$(COMPOSE) build

ps: ## List running services
	$(COMPOSE) ps

logs: ## Tail logs (all, or s=api)
	$(COMPOSE) logs -f $(s)

# ---------- Prod stack ----------
prod-up: ## Start prod stack (db, api, nginx)
	$(COMPOSE_PROD) up -d --build --wait

prod-down: ## Stop prod stack
	$(COMPOSE_PROD) down

prod-logs: ## Tail prod logs (s=service)
	$(COMPOSE_PROD) logs -f $(s)

# ---------- Database ----------
migrate: ## Apply all migrations
	$(API) uv run alembic upgrade head

migration: ## Autogenerate a migration: make migration m="add cards"
	@test -n "$(m)" || (echo 'usage: make migration m="message"'; exit 1)
	$(API) uv run alembic revision --autogenerate -m "$(m)"

downgrade: ## Roll back one migration
	$(API) uv run alembic downgrade -1

seed: ## Upsert content packs into the DB
	$(API) uv run python -m app.scripts.seed

psql: ## Open psql shell
	$(COMPOSE) exec db psql -U $(DB_USER) -d $(DB_NAME)

db-reset: ## Destroy DB volume, then migrate + seed
	$(COMPOSE) down -v
	$(COMPOSE) up -d --build --wait
	$(MAKE) migrate seed

backup: ## pg_dump to ./backups (prod stack), keep 14 days
	@mkdir -p backups
	$(COMPOSE_PROD) exec -T db pg_dump -U $(DB_USER) -d $(DB_NAME) -Fc > backups/mentat-$$(date +%Y%m%d-%H%M%S).dump
	find backups -name 'mentat-*.dump' -mtime +14 -delete

restore: ## Restore a dump into prod DB: make restore f=backups/x.dump
	@test -n "$(f)" || (echo 'usage: make restore f=backups/file.dump'; exit 1)
	$(COMPOSE_PROD) exec -T db pg_restore -U $(DB_USER) -d $(DB_NAME) --clean --if-exists < $(f)

# ---------- Quality ----------
test: test-api test-web ## Run all tests

test-api: ## Backend tests (inside api container, uses db)
	$(API) uv run pytest $(args)

test-web: ## Frontend tests
	cd frontend && pnpm vitest run

lint: ## Lint backend + frontend
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm lint && pnpm format:check

fmt: ## Auto-format backend + frontend
	cd backend && uv run ruff check --fix . && uv run ruff format .
	cd frontend && pnpm format

typecheck: ## mypy + tsc
	cd backend && uv run mypy app tests
	cd frontend && pnpm typecheck

check: lint typecheck test ## Everything CI runs

gen-api: ## Export OpenAPI and regenerate RTK Query client
	cd backend && uv run python -m app.scripts.export_openapi > ../frontend/openapi.json
	cd frontend && pnpm gen:api

# ---------- Shells ----------
shell-api: ## Shell into api container
	$(API) bash

shell-web: ## Shell into web container
	$(COMPOSE) exec web sh

clean: ## Remove caches and build output
	find backend -type d \( -name __pycache__ -o -name .pytest_cache -o -name .mypy_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
	rm -rf frontend/dist frontend/node_modules/.vite
