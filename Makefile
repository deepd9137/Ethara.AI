.DEFAULT_GOAL := help

help: ## Show this help
	@awk 'BEGIN{FS=":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: ## One-shot dev setup (run after clone)
	corepack enable
	pnpm install
	cd apps/api && uv venv && uv sync
	cp -n apps/api/.env.example apps/api/.env || true
	cp -n apps/web/.env.example apps/web/.env || true
	docker compose up -d postgres
	cd apps/api && .venv/bin/alembic upgrade head

up: ## Start postgres
	docker compose up -d postgres

down: ## Stop postgres
	docker compose down

api: ## Run API dev server
	cd apps/api && .venv/bin/uvicorn app.main:app --reload --port 8000

web: ## Run web dev server
	cd apps/web && pnpm dev

dev: ## Instructions for running both servers
	@echo "Run 'make api' and 'make web' in separate terminals"

migrate: ## Apply all pending migrations
	cd apps/api && .venv/bin/alembic upgrade head

migration: ## Create migration: make migration name="add users table"
	cd apps/api && .venv/bin/alembic revision --autogenerate -m "$(name)"

seed: ## Seed demo data (creates demo@ethara.example / DemoPass123!)
	cd apps/api && .venv/bin/python -m app.scripts.seed

test: ## Run all tests
	cd apps/api && .venv/bin/pytest
	cd apps/web && pnpm test --run

fmt: ## Format all code
	cd apps/api && .venv/bin/black . && .venv/bin/ruff check . --fix
	pnpm format

lint: ## Lint all code
	cd apps/api && .venv/bin/ruff check . && .venv/bin/black --check . && .venv/bin/mypy .
	cd apps/web && pnpm lint && pnpm typecheck

reset-db: ## Drop and recreate database
	docker compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS ttm;"
	docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE ttm;"
	$(MAKE) migrate

openapi: ## Export OpenAPI spec to openapi.json
	cd apps/api && .venv/bin/python -c "from app.main import app; import json; print(json.dumps(app.openapi()))" > openapi.json

.PHONY: help bootstrap up down api web dev migrate migration seed test fmt lint reset-db openapi
