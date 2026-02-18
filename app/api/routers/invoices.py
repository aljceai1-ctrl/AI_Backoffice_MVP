"""Invoice lifecycle endpoints."""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_request_id, require_api_key
from app.models.approval import Approval
from app.models.exception import InvoiceException
from app.models.invoice import Invoice
from app.schemas.approval import ApprovalRequest, ApprovalResponse
from app.schemas.exception import ExceptionResponse
from app.schemas.invoice import InvoiceDetail, InvoiceExtract, InvoiceResponse
from app.services import approval as approval_svc
from app.services import extraction, storage, validation
from app.services.audit import record_event

router = APIRouter(prefix="/invoices", tags=["Invoices"])

# ─── Dependency type aliases ──────────────────────────────────────────────────
DB = Annotated[Session, Depends(get_db)]
Auth = Annotated[str, Depends(require_api_key)]
ReqID = Annotated[str, Depends(get_request_id)]


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "/upload",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an invoice file",
)
async def upload_invoice(
    db: DB,
    auth: Auth,
    request_id: ReqID,
    file: UploadFile = File(..., description="PDF or image invoice file"),
) -> Invoice:
    """Accept a multipart invoice upload, persist it to disk, create a DB record
    with status NEW, and write an audit event.
    """
    filename, storage_path = storage.save_upload(file)

    invoice = Invoice(filename=filename, storage_path=storage_path, status="NEW")
    db.add(invoice)
    db.flush()

    record_event(
        db,
        event_type="INVOICE_UPLOADED",
        entity_type="invoice",
        entity_id=invoice.id,
        request_id=request_id,
        notes=f"filename={filename}",
    )
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post(
    "/{invoice_id}/extract",
    response_model=InvoiceResponse,
    summary="Apply extracted fields (manual or future LLM/OCR)",
)
async def extract_invoice(
    invoice_id: uuid.UUID,
    fields: InvoiceExtract,
    db: DB,
    auth: Auth,
    request_id: ReqID,
) -> Invoice:
    """Write structured fields onto an invoice and advance status to EXTRACTED."""
    invoice = _get_or_404(db, invoice_id)
    extraction.extract_fields(db, invoice, fields)

    record_event(
        db,
        event_type="INVOICE_EXTRACTED",
        entity_type="invoice",
        entity_id=invoice.id,
        actor="system",
        request_id=request_id,
        source="manual",
        notes=f"fields={list(fields.model_dump(exclude_unset=True).keys())}",
    )
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post(
    "/{invoice_id}/validate",
    response_model=InvoiceResponse,
    summary="Run validation rules and create exceptions",
)
async def validate_invoice(
    invoice_id: uuid.UUID,
    db: DB,
    auth: Auth,
    request_id: ReqID,
) -> Invoice:
    """Execute all validation rules; create InvoiceException rows for failures;
    advance invoice to VALIDATED or APPROVAL_PENDING.
    """
    invoice = _get_or_404(db, invoice_id)
    exceptions = validation.validate_invoice(db, invoice)

    record_event(
        db,
        event_type="INVOICE_VALIDATED",
        entity_type="invoice",
        entity_id=invoice.id,
        request_id=request_id,
        notes=f"{len(exceptions)} exception(s); new_status={invoice.status}",
    )
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post(
    "/{invoice_id}/approve",
    response_model=ApprovalResponse,
    summary="Human approval or rejection",
)
async def approve_invoice(
    invoice_id: uuid.UUID,
    req: ApprovalRequest,
    db: DB,
    auth: Auth,
    request_id: ReqID,
) -> Approval:
    """Record a human approve/reject decision.

    The invoice must be in VALIDATED or APPROVAL_PENDING status.
    No autopay is performed — this is an approval-only, export-driven system.
    """
    invoice = _get_or_404(db, invoice_id)
    if invoice.status not in ("VALIDATED", "APPROVAL_PENDING"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Invoice status '{invoice.status}' is not eligible for approval. "
                "Expected VALIDATED or APPROVAL_PENDING."
            ),
        )

    approval = approval_svc.process_approval(db, invoice, req)

    record_event(
        db,
        event_type=f"INVOICE_{req.decision.upper()}D",
        entity_type="invoice",
        entity_id=invoice.id,
        actor=req.decided_by,
        request_id=request_id,
        notes=req.notes,
    )
    db.commit()
    db.refresh(approval)
    return approval


@router.get(
    "",
    response_model=list[InvoiceResponse],
    summary="List invoices with optional filters",
)
async def list_invoices(
    db: DB,
    auth: Auth,
    filter_status: Optional[str] = Query(None, alias="status", description="Filter by status"),
    from_date: Optional[date] = Query(None, alias="from", description="Created on or after (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, alias="to", description="Created on or before (YYYY-MM-DD)"),
) -> list[Invoice]:
    """Return invoices, newest first, filtered by status and/or creation date."""
    q = db.query(Invoice)
    if filter_status:
        q = q.filter(Invoice.status == filter_status.upper())
    if from_date:
        from_dt = datetime(from_date.year, from_date.month, from_date.day, tzinfo=UTC)
        q = q.filter(Invoice.created_at >= from_dt)
    if to_date:
        to_dt = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59, tzinfo=UTC)
        q = q.filter(Invoice.created_at <= to_dt)
    return q.order_by(Invoice.created_at.desc()).all()


@router.get(
    "/{invoice_id}",
    response_model=InvoiceDetail,
    summary="Get invoice detail (includes exceptions and approvals)",
)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: DB,
    auth: Auth,
) -> InvoiceDetail:
    """Retrieve a single invoice with its full exception and approval history."""
    invoice = _get_or_404(db, invoice_id)
    exceptions = (
        db.query(InvoiceException)
        .filter(InvoiceException.invoice_id == invoice.id)
        .order_by(InvoiceException.created_at)
        .all()
    )
    approvals = (
        db.query(Approval)
        .filter(Approval.invoice_id == invoice.id)
        .order_by(Approval.created_at)
        .all()
    )

    detail = InvoiceDetail.model_validate(invoice)
    detail.exceptions = [ExceptionResponse.model_validate(e) for e in exceptions]
    detail.approvals = [ApprovalResponse.model_validate(a) for a in approvals]
    return detail


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_or_404(db: Session, invoice_id: uuid.UUID) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found.",
        )
    return invoice
