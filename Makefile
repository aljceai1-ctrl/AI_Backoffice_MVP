# =============================================================================
# AI Backoffice MVP — Developer Makefile
# All targets are meant to be run from the repo root.
# Requires Docker Desktop (docker compose v2) for service targets.
#
# QUICK START
#   make venv          # one-time: create .venv + install all dev deps
#   make ci            # run the full local quality gate
#   make up            # start Docker services
#   make migrate       # apply Alembic migrations
#   make test          # end-to-end smoke test
# =============================================================================

.PHONY: venv install-dev pre-commit-install \
        lint format format-check type pytest ci \
        up down migrate test logs shell psql \
        help

# ── Virtual-environment paths ─────────────────────────────────────────────────
#
# All dev-tool targets (lint / format / type / pytest / ci) go through the
# repo-local .venv so you never need system-wide installs of ruff / mypy / etc.
#
#   One-time:   make venv
#   Daily use:  make ci      (no shell activation needed — paths are explicit)

VENV := .venv
BIN  := $(VENV)/bin

# Guard macro: print a helpful message and exit if the venv doesn't exist yet.
define _check_venv
	@if [ ! -f "$(BIN)/ruff" ]; then \
		echo ""; \
		echo "  ✗  $(BIN)/ruff not found — run  make venv  first."; \
		echo ""; \
		exit 1; \
	fi
endef

# ── Help ──────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  AI Backoffice MVP — available Make targets"
	@echo ""
	@echo "  ── One-time setup ─────────────────────────────────────────────"
	@echo "  make venv             Create .venv and install all dev deps"
	@echo "  make pre-commit-install  Install git pre-commit hooks"
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
	@echo "  make test     End-to-end smoke test (requires running stack)"
	@echo "  make pytest   Unit/integration suite (requires db_test on :5433)"
	@echo ""
	@echo "  ── Code quality (requires: make venv) ────────────────────────"
	@echo "  make lint         ruff check .  — show all lint violations"
	@echo "  make format       ruff format . — auto-fix formatting in place"
	@echo "  make format-check ruff format --check — fail if formatting differs"
	@echo "  make type         mypy app/ — static type analysis"
	@echo "  make ci           lint + format-check + type + pytest (full gate)"
	@echo ""

# ── Virtual environment ───────────────────────────────────────────────────────

# Create the venv and install all runtime + dev dependencies in one shot.
# Re-running is safe: pip will skip already-installed packages.
venv:
	python3 -m venv $(VENV)
	$(BIN)/python -m pip install --quiet --upgrade pip setuptools wheel
	$(BIN)/pip install --quiet -r requirements.txt -r requirements-dev.txt
	@echo ""
	@echo "  ✓  .venv ready — dev tools installed:"
	@$(BIN)/ruff --version
	@$(BIN)/mypy --version
	@$(BIN)/pytest --version
	@$(BIN)/pre-commit --version
	@echo ""
	@echo "  No shell activation needed for Make targets."
	@echo "  To activate manually (optional):  source $(VENV)/bin/activate"

# Legacy target kept for backwards compatibility.
install-dev:
	@$(MAKE) venv

# ── Pre-commit hooks ──────────────────────────────────────────────────────────

pre-commit-install:
	$(call _check_venv)
	$(BIN)/pre-commit install
	@echo "  ✓  Pre-commit hooks installed."

# ── Code quality ──────────────────────────────────────────────────────────────

lint:
	$(call _check_venv)
	$(BIN)/ruff check .

format:
	$(call _check_venv)
	$(BIN)/ruff format .

format-check:
	$(call _check_venv)
	$(BIN)/ruff format --check .

type:
	$(call _check_venv)
	$(BIN)/mypy app/

# Full local CI gate — mirrors the GitHub Actions quality + tests jobs.
ci: lint format-check type pytest

# ── Unit / integration tests (local, needs Postgres db_test on :5433) ────────

pytest:
	$(call _check_venv)
	$(BIN)/pytest -q --tb=short

# ── Service lifecycle ─────────────────────────────────────────────────────────

up:
	docker compose up -d --build
	@echo ""
	@echo "  Services started.  Run 'make migrate' then 'make test'."
	@echo "  Docs: http://localhost:8000/docs"

down:
	docker compose down -v
	@echo "  All containers and volumes removed."

# ── Database ──────────────────────────────────────────────────────────────────

migrate:
	docker compose exec app alembic upgrade head
	@echo "  Migrations applied."

# ── End-to-end smoke test (needs running stack) ───────────────────────────────

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
