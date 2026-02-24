# =============================================================================
# AI Backoffice MVP — Monorepo Developer Makefile
# =============================================================================

.PHONY: up down logs migrate seed test smoke ci \
        lint format format-check type pytest \
        venv install-dev \
        shell psql help

# ── Virtual-environment paths (for backend local dev) ────────────────────────
VENV := backend/.venv
BIN  := $(VENV)/bin

define _check_venv
	@if [ ! -f "$(BIN)/ruff" ]; then \
		echo ""; \
		echo "  ✗  $(BIN)/ruff not found — run  make venv  first."; \
		echo ""; \
		exit 1; \
	fi
endef

# ── Help ─────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  AI Backoffice MVP — Monorepo"
	@echo ""
	@echo "  ── Docker (primary workflow) ──────────────────────────────────"
	@echo "  make up         Build and start all services (backend, frontend, postgres, mailhog)"
	@echo "  make down       Stop and remove all containers + volumes"
	@echo "  make logs       Tail logs"
	@echo "  make test       Run backend pytest suite in Docker"
	@echo "  make smoke      Health-check backend + frontend URLs"
	@echo "  make seed       Re-seed demo data"
	@echo "  make migrate    Run Alembic migrations"
	@echo ""
	@echo "  ── Code quality (backend) ────────────────────────────────────"
	@echo "  make venv       Create backend/.venv and install all deps"
	@echo "  make ci         Run full quality gate: lint + format + type + tests"
	@echo "  make lint       ruff check"
	@echo "  make format     ruff format (auto-fix)"
	@echo "  make type       mypy"
	@echo "  make pytest     pytest (needs postgres_test on :5433)"
	@echo ""
	@echo "  ── Frontend ─────────────────────────────────────────────────"
	@echo "  make fe-dev     Run frontend in dev mode"
	@echo "  make fe-lint    Run Next.js lint"
	@echo ""
	@echo "  URLs:"
	@echo "    Frontend:    http://localhost:3000"
	@echo "    Backend API: http://localhost:8000/docs"
	@echo "    MailHog:     http://localhost:8025"
	@echo ""

# ── Docker lifecycle ─────────────────────────────────────────────────────────
up:
	docker compose up -d --build
	@echo ""
	@echo "  ✓ Services starting..."
	@echo "    Frontend:    http://localhost:3000"
	@echo "    Backend API: http://localhost:8000/docs"
	@echo "    MailHog:     http://localhost:8025"

down:
	docker compose down -v
	@echo "  All containers and volumes removed."

logs:
	docker compose logs -f --tail=200

migrate:
	docker compose exec backend python scripts/run_migrations.py

seed:
	docker compose exec backend python scripts/seed.py

# ── Backend virtual environment (local dev) ──────────────────────────────────
venv:
	cd backend && python3 -m venv .venv
	$(BIN)/python -m pip install --quiet --upgrade pip setuptools wheel
	$(BIN)/pip install --quiet -r backend/requirements.txt -r backend/requirements-dev.txt
	@echo ""
	@echo "  ✓  backend/.venv ready"

install-dev:
	@$(MAKE) venv

# ── Code quality ─────────────────────────────────────────────────────────────
lint:
	$(call _check_venv)
	cd backend && .venv/bin/ruff check .

format:
	$(call _check_venv)
	cd backend && .venv/bin/ruff format .

format-check:
	$(call _check_venv)
	cd backend && .venv/bin/ruff format --check .

type:
	$(call _check_venv)
	cd backend && .venv/bin/mypy app/

ci: lint format-check type pytest

pytest:
	$(call _check_venv)
	cd backend && .venv/bin/pytest -q --tb=short

# ── Frontend ─────────────────────────────────────────────────────────────────
fe-dev:
	cd frontend && npm run dev

fe-lint:
	cd frontend && npm run lint

fe-build:
	cd frontend && npm run build

# ── Convenience shells ───────────────────────────────────────────────────────
shell:
	docker compose exec backend bash

psql:
	docker compose exec postgres psql -U backoffice -d backoffice

test:
	docker compose exec backend python -m pytest -q --tb=short

smoke:
	@echo "Running backend health check..."
	@curl -sf http://localhost:8000/api/health && echo " ✓ Backend OK" || echo " ✗ Backend not ready"
	@echo "Running frontend check..."
	@curl -sf http://localhost:3000 > /dev/null && echo " ✓ Frontend OK" || echo " ✗ Frontend not ready"
