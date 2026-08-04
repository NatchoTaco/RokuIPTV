COMPOSE := docker compose

.PHONY: dev up down migrate api-lint api-typecheck api-test dashboard-lint dashboard-typecheck dashboard-test test health openapi

dev:
	$(COMPOSE) up --build

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) run --rm api alembic -c apps/api/alembic.ini upgrade head

api-lint:
	$(COMPOSE) run --rm api ruff check apps/api

api-typecheck:
	$(COMPOSE) run --rm api mypy apps/api/streamforge_api

api-test:
	$(COMPOSE) run --rm api pytest apps/api/tests

dashboard-lint:
	$(COMPOSE) run --rm dashboard npm run lint

dashboard-typecheck:
	$(COMPOSE) run --rm dashboard npm run typecheck

dashboard-test:
	$(COMPOSE) run --rm dashboard npm run test:run

test: api-lint api-typecheck api-test dashboard-lint dashboard-typecheck dashboard-test

health:
	pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/health-check.ps1

openapi:
	$(COMPOSE) run --rm api python scripts/export-openapi.py
