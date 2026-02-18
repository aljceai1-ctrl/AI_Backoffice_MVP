# =============================================================================
# AI Backoffice MVP — Developer Makefile
# All targets are meant to be run from the repo root.
# Requires Docker Desktop (docker compose v2).
# =============================================================================

.PHONY: up down migrate test logs shell psql lint help

# Default target
help:
	@echo ""
	@echo "  AI Backoffice MVP — available targets"
	@echo ""
	@echo "  make up       Build images and start all services in the background"
	@echo "  make down     Stop and remove containers + volumes (full wipe)"
	@echo "  make migrate  Run Alembic migrations inside the app container"
	@echo "  make test     Run the smoke test against http://localhost:8000"
	@echo "  make logs     Tail application logs (Ctrl-C to stop)"
	@echo "  make shell    Open a bash shell inside the app container"
	@echo "  make psql     Open psql inside the db container"
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

# ── Smoke test ────────────────────────────────────────────────────────────────

test:
	@bash scripts/smoke_test.sh

# ── Observability ─────────────────────────────────────────────────────────────

logs:
	docker compose logs -f --tail=200

# ── Convenience shells ────────────────────────────────────────────────────────

shell:
	docker compose exec app bash

psql:
	docker compose exec db psql -U backoffice -d backoffice
