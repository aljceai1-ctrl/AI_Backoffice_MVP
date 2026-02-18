"""Export endpoints — payment pack CSV and weekly Markdown report."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_id, require_api_key
from app.services.audit import record_event
from app.services.exports import generate_payment_pack
from app.services.reporting import generate_weekly_pack

router = APIRouter(tags=["Exports"])

DB = Annotated[Session, Depends(get_db)]
Auth = Annotated[str, Depends(require_api_key)]
ReqID = Annotated[str, Depends(get_request_id)]


@router.get(
    "/payment-pack.csv",
    response_class=PlainTextResponse,
    summary="Export approved invoices as payment pack CSV",
)
async def payment_pack(
    db: DB,
    auth: Auth,
    request_id: ReqID,
    from_date: date = Query(..., alias="from", description="Start date YYYY-MM-DD"),
    to_date: date = Query(..., alias="to", description="End date YYYY-MM-DD"),
) -> PlainTextResponse:
    """Generate and return a CSV of all APPROVED invoices in the date range.

    Columns: vendor, invoice_number, amount, currency, due_date, storage_path

    **No autopay or payment execution is performed.**
    """
    csv_content, row_count = generate_payment_pack(db, from_date, to_date)

    # Audit the export action
    import uuid as _uuid
    export_id = _uuid.uuid4()
    record_event(
        db,
        event_type="PAYMENT_PACK_EXPORTED",
        entity_type="export",
        entity_id=export_id,
        request_id=request_id,
        notes=f"from={from_date} to={to_date} rows={row_count}",
    )
    db.commit()

    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=payment-pack-{from_date}-{to_date}.csv"},
    )


@router.get(
    "/weekly-pack.md",
    response_class=PlainTextResponse,
    summary="Generate weekly finance ops report (Markdown)",
)
async def weekly_pack(
    db: DB,
    auth: Auth,
    request_id: ReqID,
    week_start: date = Query(..., description="Start of the 7-day week (YYYY-MM-DD)"),
) -> PlainTextResponse:
    """Return a Markdown finance ops pack for the week starting on ``week_start``.

    Includes: summary counts, exceptions breakdown, top pending approvals,
    action list, and audit summary.
    """
    md_content = generate_weekly_pack(db, week_start)

    import uuid as _uuid
    report_id = _uuid.uuid4()
    record_event(
        db,
        event_type="WEEKLY_PACK_GENERATED",
        entity_type="report",
        entity_id=report_id,
        request_id=request_id,
        notes=f"week_start={week_start}",
    )
    db.commit()

    return PlainTextResponse(
        content=md_content,
        media_type="text/markdown",
    )
