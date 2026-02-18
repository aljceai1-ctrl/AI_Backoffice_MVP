"""AI Backoffice MVP — FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.api.routers import audit, exports, health, invoices
from app.core.logging_config import setup_logging
from app.core.middleware import RequestIDMiddleware
from app.core.settings import get_settings

# ── Bootstrap ─────────────────────────────────────────────────────────────────

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


# ── Startup table check ───────────────────────────────────────────────────────

def _check_db_schema() -> None:
    """Probe the DB on startup and emit a loud warning if migrations are missing.

    This does NOT prevent the app from starting — it just surfaces the problem
    immediately in the logs rather than on the first real request.

    Fix: run  ``make migrate``  (or: docker compose exec app alembic upgrade head)
    """
    from sqlalchemy import text

    from app.db.engine import get_engine

    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1 FROM invoices LIMIT 1"))
        logger.info("DB schema check passed — all tables present")
    except (ProgrammingError, OperationalError) as exc:
        msg = str(exc)
        if "relation" in msg.lower() or "does not exist" in msg.lower():
            logger.warning(
                "\n"
                "  ╔══════════════════════════════════════════════════════════╗\n"
                "  ║  DATABASE TABLES ARE MISSING — run migrations first!     ║\n"
                "  ║                                                          ║\n"
                "  ║  Quickfix:  make migrate                                 ║\n"
                "  ║  Manual:    docker compose exec app alembic upgrade head ║\n"
                "  ╚══════════════════════════════════════════════════════════╝"
            )
        else:
            logger.warning("DB connectivity issue at startup: %s", exc)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("AI Backoffice MVP starting — log_level=%s", settings.LOG_LEVEL)
    _check_db_schema()
    yield
    logger.info("AI Backoffice MVP shutting down")


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Backoffice MVP",
    description=(
        "Invoice processing system for Dubai SMEs / property management. "
        "Supports upload → extract → validate → human approval → CSV export. "
        "**No autopay** — this system is export-only."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(RequestIDMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router)   # /health — no auth
app.include_router(invoices.router)
app.include_router(exports.router)
app.include_router(audit.router)


# ── Exception handlers ────────────────────────────────────────────────────────

_MIGRATION_HINT = (
    "Database schema is not initialised. "
    "Run migrations first: make migrate  "
    "(or: docker compose exec app alembic upgrade head)"
)


@app.exception_handler(ProgrammingError)
async def sqlalchemy_programming_error_handler(
    request: Request, exc: ProgrammingError
) -> JSONResponse:
    """Return a 503 with a helpful hint when the DB tables don't exist yet."""
    msg = str(exc)
    request_id = getattr(request.state, "request_id", "unknown")
    if "relation" in msg.lower() or "does not exist" in msg.lower():
        logger.error(
            "DB schema missing on %s %s — %s",
            request.method,
            request.url.path,
            exc,
            extra={"request_id": request_id},
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": _MIGRATION_HINT,
                "request_id": request_id,
            },
        )
    # Not a missing-table error — fall through to the generic handler
    return await unhandled_exception_handler(request, exc)


@app.exception_handler(OperationalError)
async def sqlalchemy_operational_error_handler(
    request: Request, exc: OperationalError
) -> JSONResponse:
    """Return a 503 when the DB is unreachable (e.g. container still starting)."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "DB unreachable on %s %s — %s",
        request.method,
        request.url.path,
        exc,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database is unavailable. Check that the db container is running.",
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )
