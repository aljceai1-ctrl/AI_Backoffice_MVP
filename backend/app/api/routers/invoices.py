"""Invoice endpoints: upload, list, detail, approve, reject, mark-paid."""
import os
import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.db.session import get_db
from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_exception import InvoiceException
from app.models.payment import Payment
from app.models.user import Role, User
from app.schemas.invoice import InvoiceListResponse, InvoiceResponse
from app.services.validation import validate_invoice

router = APIRouter(prefix="/invoices", tags=["invoices"])

ALL_ROLES = [r.value for r in Role]
WRITE_ROLES = [Role.ADMIN.value, Role.APPROVER.value, Role.UPLOADER.value]


def _inv_to_response(inv: Invoice) -> InvoiceResponse:
    return InvoiceResponse(
        id=str(inv.id),
        tenant_id=str(inv.tenant_id),
        vendor=inv.vendor or "",
        invoice_number=inv.invoice_number or "",
        invoice_date=inv.invoice_date.isoformat() if inv.invoice_date else None,
        amount=float(inv.amount) if inv.amount is not None else None,
        currency=inv.currency or "AED",
        status=inv.status,
        source=inv.source,
        original_filename=inv.original_filename or "",
        created_at=inv.created_at.isoformat() if inv.created_at else "",
        updated_at=inv.updated_at.isoformat() if inv.updated_at else "",
        exceptions=[
            dict(id=str(e.id), code=e.code, message=e.message, severity=e.severity,
                 created_at=e.created_at.isoformat() if e.created_at else "",
                 resolved_at=e.resolved_at.isoformat() if e.resolved_at else None)
            for e in (inv.exceptions or [])
        ],
        approvals=[
            dict(id=str(a.id), decided_by_user_id=str(a.decided_by_user_id),
                 decision=a.decision, decided_at=a.decided_at.isoformat() if a.decided_at else "",
                 notes=a.notes or "")
            for a in (inv.approvals or [])
        ],
        payments=[
            dict(id=str(p.id), paid_amount=float(p.paid_amount), paid_currency=p.paid_currency,
                 paid_at=p.paid_at.isoformat() if p.paid_at else "",
                 payment_method=p.payment_method or "", reference=p.reference or "")
            for p in (inv.payments or [])
        ],
    )


@router.post("/upload", response_model=InvoiceResponse, status_code=201)
def upload_invoice(
    file: UploadFile = File(...),
    vendor: str = Form(""),
    invoice_number: str = Form(""),
    invoice_date: str = Form(""),
    amount: str = Form(""),
    currency: str = Form("AED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*WRITE_ROLES)),
):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename or "file")[1]
    save_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")
    with open(save_path, "wb") as f:
        content = file.file.read()
        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")
        f.write(content)

    parsed_date = None
    if invoice_date:
        try:
            parsed_date = date.fromisoformat(invoice_date)
        except ValueError:
            pass

    parsed_amount = None
    if amount:
        try:
            parsed_amount = float(amount)
        except ValueError:
            pass

    inv = Invoice(
        tenant_id=current_user.tenant_id,
        vendor=vendor,
        invoice_number=invoice_number,
        invoice_date=parsed_date,
        amount=parsed_amount,
        currency=currency,
        file_path=save_path,
        original_filename=file.filename or "",
        source="UPLOAD",
    )
    db.add(inv)
    db.flush()

    # Run validation
    exceptions = validate_invoice(inv, current_user.tenant)
    for exc in exceptions:
        exc.tenant_id = current_user.tenant_id
        db.add(exc)

    if exceptions:
        inv.status = InvoiceStatus.VALIDATED.value
    else:
        inv.status = InvoiceStatus.APPROVAL_PENDING.value

    db.add(AuditEvent(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="INVOICE_UPLOADED",
        entity_type="invoice",
        entity_id=str(inv.id),
        metadata_json={"filename": file.filename, "vendor": vendor},
    ))
    db.commit()
    db.refresh(inv)
    return _inv_to_response(inv)


@router.get("", response_model=InvoiceListResponse)
def list_invoices(
    status_filter: str | None = None,
    vendor: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Invoice).filter(Invoice.tenant_id == current_user.tenant_id)
    if status_filter:
        q = q.filter(Invoice.status == status_filter)
    if vendor:
        q = q.filter(Invoice.vendor.ilike(f"%{vendor}%"))
    if from_date:
        try:
            q = q.filter(Invoice.created_at >= datetime.fromisoformat(from_date))
        except ValueError:
            pass
    if to_date:
        try:
            q = q.filter(Invoice.created_at <= datetime.fromisoformat(to_date + "T23:59:59"))
        except ValueError:
            pass

    total = q.count()
    items = q.order_by(Invoice.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return InvoiceListResponse(
        items=[_inv_to_response(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _inv_to_response(inv)


@router.get("/{invoice_id}/download")
def download_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id).first()
    if not inv or not inv.file_path or not os.path.exists(inv.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(inv.file_path, filename=inv.original_filename or "invoice")


@router.post("/{invoice_id}/approve", response_model=InvoiceResponse)
def approve_invoice(
    invoice_id: uuid.UUID,
    notes: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN.value, Role.APPROVER.value)),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.status not in (InvoiceStatus.APPROVAL_PENDING.value, InvoiceStatus.VALIDATED.value):
        raise HTTPException(status_code=400, detail=f"Cannot approve invoice in status {inv.status}")

    inv.status = InvoiceStatus.APPROVED.value
    db.add(Approval(
        tenant_id=current_user.tenant_id, invoice_id=inv.id,
        decided_by_user_id=current_user.id, decision="APPROVED", notes=notes,
    ))
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_user_id=current_user.id,
        action="INVOICE_APPROVED", entity_type="invoice", entity_id=str(inv.id),
    ))
    db.commit()
    db.refresh(inv)
    return _inv_to_response(inv)


@router.post("/{invoice_id}/reject", response_model=InvoiceResponse)
def reject_invoice(
    invoice_id: uuid.UUID,
    notes: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN.value, Role.APPROVER.value)),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    inv.status = InvoiceStatus.REJECTED.value
    db.add(Approval(
        tenant_id=current_user.tenant_id, invoice_id=inv.id,
        decided_by_user_id=current_user.id, decision="REJECTED", notes=notes,
    ))
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_user_id=current_user.id,
        action="INVOICE_REJECTED", entity_type="invoice", entity_id=str(inv.id),
    ))
    db.commit()
    db.refresh(inv)
    return _inv_to_response(inv)


@router.post("/{invoice_id}/mark-paid", response_model=InvoiceResponse)
def mark_paid(
    invoice_id: uuid.UUID,
    paid_amount: float | None = None,
    payment_method: str = "",
    reference: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN.value, Role.APPROVER.value)),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.status != InvoiceStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail="Only approved invoices can be marked as paid")

    amount = paid_amount if paid_amount is not None else (float(inv.amount) if inv.amount else 0)
    inv.status = InvoiceStatus.PAID.value
    payment = Payment(
        tenant_id=current_user.tenant_id,
        invoice_id=inv.id,
        paid_amount=amount,
        paid_currency=inv.currency,
        payment_method=payment_method,
        reference=reference,
        created_by_user_id=current_user.id,
    )
    db.add(payment)
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id, actor_user_id=current_user.id,
        action="INVOICE_PAID", entity_type="invoice", entity_id=str(inv.id),
        metadata_json={"amount": amount, "method": payment_method},
    ))
    db.commit()
    db.refresh(inv)
    return _inv_to_response(inv)
