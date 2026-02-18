# =============================================================================
# AI Backoffice MVP — Developer Makefile
# All targets are meant to be run from the repo root.
# Requires Docker Desktop (docker compose v2).
# =============================================================================

.PHONY: up down migrate test logs shell psql \
        lint format format-check type ci \
        install-dev pre-commit-install help

# Default target
help:
	@echo ""
	@echo "  AI Backoffice MVP — available targets"
	@echo ""
	@echo "  ── Service lifecycle ──────────────────────────────────────────"
	@echo "  make up       Build images and start all services in the background"
	@echo "  make down     Stop and remove containers + volumes (full wipe)"
	@echo "  make migrate  Run Alembic migrations inside the app container"
	@echo "  make logs     Tail application logs (Ctrl-C to stop)"
	@echo "  make shell    Open a bash shell inside the app container"
	@echo "  make psql     Open psql inside the db container"
	@echo ""
	@echo "  ── Testing ────────────────────────────────────────────────────"
	@echo "  make test     Run the end-to-end smoke test (requires running stack)"
	@echo "  make pytest   Run the pytest unit/integration suite (local Postgres)"
	@echo ""
	@echo "  ── Code quality ───────────────────────────────────────────────"
	@echo "  make lint         ruff check — show all lint violations"
	@echo "  make format       ruff format — auto-fix formatting in place"
	@echo "  make format-check ruff format --check — fail if formatting differs"
	@echo "  make type         mypy — static type check of app/"
	@echo "  make ci           lint + format-check + type + pytest (full local CI)"
	@echo ""
	@echo "  ── Setup ──────────────────────────────────────────────────────"
	@echo "  make install-dev        pip install -r requirements-dev.txt"
	@echo "  make pre-commit-install Install git hooks via pre-commit"
	@echo ""

# ── Lifecycle ─────────────────────────────────────────────────────────────────

up:
	docker compose up -d --build
	@echo ""
	@echo "  Services started. Run 'make migrate' then 'make test'."
	@echo "  Docs: http://localhost:8000/docs"

down:
	docker compose down -v
	@echo "  All containers and volumes removed."

# ── Database ──────────────────────────────────────────────────────────────────

migrate:
	docker compose exec app alembic upgrade head
	@echo "  Migrations applied."

# ── Smoke test (end-to-end, needs running stack) ──────────────────────────────

test:
	@bash scripts/smoke_test.sh

# ── Unit / integration tests (local, needs Postgres on 5433) ─────────────────

pytest:
	pytest -q --tb=short

# ── Observability ─────────────────────────────────────────────────────────────

logs:
	docker compose logs -f --tail=200

# ── Convenience shells ────────────────────────────────────────────────────────

shell:
	docker compose exec app bash

psql:
	docker compose exec db psql -U backoffice -d backoffice

# ── Code quality ─────────────────────────────────────────────────────────────

lint:
	ruff check .

format:
	ruff format .

format-check:
	ruff format --check .

type:
	mypy app/

# Run the full CI gate locally (same checks as GitHub Actions quality + tests).
ci: lint format-check type pytest

# ── Developer setup ───────────────────────────────────────────────────────────

install-dev:
	pip install -r requirements-dev.txt
	@echo "  Dev dependencies installed."

pre-commit-install:
	pre-commit install
	@echo "  Pre-commit hooks installed."
