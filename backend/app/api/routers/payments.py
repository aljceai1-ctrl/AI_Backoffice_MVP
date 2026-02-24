"""Payment endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment
from app.models.user import Role, User
from app.schemas.payment import PaymentCreate, PaymentResponse

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=list[PaymentResponse])
def list_payments(
    from_date: str | None = None,
    to_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Payment).filter(Payment.tenant_id == current_user.tenant_id)
    if from_date:
        from datetime import datetime
        try:
            q = q.filter(Payment.paid_at >= datetime.fromisoformat(from_date))
        except ValueError:
            pass
    if to_date:
        from datetime import datetime
        try:
            q = q.filter(Payment.paid_at <= datetime.fromisoformat(to_date + "T23:59:59"))
        except ValueError:
            pass
    payments = q.order_by(Payment.paid_at.desc()).limit(500).all()
    return [_to_response(p) for p in payments]


@router.post("", response_model=PaymentResponse, status_code=201)
def create_payment(
    body: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN.value, Role.APPROVER.value)),
):
    inv = db.query(Invoice).filter(
        Invoice.id == uuid.UUID(body.invoice_id),
        Invoice.tenant_id == current_user.tenant_id,
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if inv.status not in (InvoiceStatus.APPROVED.value, InvoiceStatus.PAID.value):
        raise HTTPException(status_code=400, detail="Invoice must be approved first")

    payment = Payment(
        tenant_id=current_user.tenant_id,
        invoice_id=inv.id,
        paid_amount=body.paid_amount,
        paid_currency=body.paid_currency,
        payment_method=body.payment_method,
        reference=body.reference,
        created_by_user_id=current_user.id,
    )
    db.add(payment)
    inv.status = InvoiceStatus.PAID.value
    db.commit()
    db.refresh(payment)
    return _to_response(payment)


def _to_response(p: Payment) -> PaymentResponse:
    return PaymentResponse(
        id=str(p.id),
        tenant_id=str(p.tenant_id),
        invoice_id=str(p.invoice_id),
        paid_amount=float(p.paid_amount),
        paid_currency=p.paid_currency,
        paid_at=p.paid_at.isoformat() if p.paid_at else "",
        payment_method=p.payment_method or "",
        reference=p.reference or "",
        created_by_user_id=str(p.created_by_user_id) if p.created_by_user_id else None,
        created_at=p.created_at.isoformat() if p.created_at else "",
    )
