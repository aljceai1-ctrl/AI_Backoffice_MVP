"""Health-check endpoint — no auth required."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict:
    """Returns ``{"status": "ok"}`` — used by load balancers and bootstrap checks."""
    return {"status": "ok"}
