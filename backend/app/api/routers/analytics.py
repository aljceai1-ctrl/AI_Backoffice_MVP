"""Analytics endpoints for dashboards."""
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case, extract
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.models.ingestion_run import IngestionRun
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_exception import InvoiceException
from app.models.payment import Payment
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _parse_date(s: str | None, default_days_ago: int = 90) -> date:
    if s:
        try:
            return date.fromisoformat(s)
        except ValueError:
            pass
    return date.today() - timedelta(days=default_days_ago)


@router.get("/overview")
def overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tid = current_user.tenant_id
    total = db.query(func.count(Invoice.id)).filter(Invoice.tenant_id == tid).scalar() or 0
    by_status = (
        db.query(Invoice.status, func.count(Invoice.id))
        .filter(Invoice.tenant_id == tid)
        .group_by(Invoice.status)
        .all()
    )
    total_paid = (
        db.query(func.sum(Payment.paid_amount))
        .filter(Payment.tenant_id == tid)
        .scalar()
    ) or 0
    total_exceptions = db.query(func.count(InvoiceException.id)).filter(InvoiceException.tenant_id == tid).scalar() or 0
    clean_invoices = total - db.query(func.count(func.distinct(InvoiceException.invoice_id))).filter(InvoiceException.tenant_id == tid).scalar()

    return {
        "total_invoices": total,
        "by_status": {s: c for s, c in by_status},
        "total_paid": float(total_paid),
        "total_exceptions": total_exceptions,
        "clean_invoice_count": max(0, clean_invoices),
        "clean_invoice_pct": round(max(0, clean_invoices) / total * 100, 1) if total > 0 else 0,
    }


@router.get("/payments")
def payment_analytics(
    from_date: str | None = None,
    to_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = current_user.tenant_id
    fd = _parse_date(from_date, 180)
    td = _parse_date(to_date, 0) if to_date else date.today()
    fd_dt = datetime(fd.year, fd.month, fd.day, tzinfo=UTC)
    td_dt = datetime(td.year, td.month, td.day, 23, 59, 59, tzinfo=UTC)

    # Payments over time (by month)
    over_time = (
        db.query(
            func.date_trunc("month", Payment.paid_at).label("month"),
            func.sum(Payment.paid_amount).label("total"),
            func.count(Payment.id).label("count"),
        )
        .filter(Payment.tenant_id == tid, Payment.paid_at.between(fd_dt, td_dt))
        .group_by("month")
        .order_by("month")
        .all()
    )

    # Top vendors by payment
    top_vendors = (
        db.query(
            Invoice.vendor,
            func.sum(Payment.paid_amount).label("total"),
            func.count(Payment.id).label("count"),
        )
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(Payment.tenant_id == tid, Payment.paid_at.between(fd_dt, td_dt))
        .group_by(Invoice.vendor)
        .order_by(func.sum(Payment.paid_amount).desc())
        .limit(10)
        .all()
    )

    return {
        "over_time": [
            {"month": r.month.isoformat() if r.month else "", "total": float(r.total or 0), "count": r.count}
            for r in over_time
        ],
        "top_vendors": [
            {"vendor": r.vendor or "Unknown", "total": float(r.total or 0), "count": r.count}
            for r in top_vendors
        ],
    }


@router.get("/effectiveness")
def effectiveness_analytics(
    from_date: str | None = None,
    to_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = current_user.tenant_id
    fd = _parse_date(from_date, 180)
    td = _parse_date(to_date, 0) if to_date else date.today()
    fd_dt = datetime(fd.year, fd.month, fd.day, tzinfo=UTC)
    td_dt = datetime(td.year, td.month, td.day, 23, 59, 59, tzinfo=UTC)

    # Exception rate over time (by week)
    exc_over_time = (
        db.query(
            func.date_trunc("week", InvoiceException.created_at).label("week"),
            func.count(InvoiceException.id).label("count"),
        )
        .filter(InvoiceException.tenant_id == tid, InvoiceException.created_at.between(fd_dt, td_dt))
        .group_by("week")
        .order_by("week")
        .all()
    )

    # Top exception codes
    top_codes = (
        db.query(InvoiceException.code, func.count(InvoiceException.id).label("count"))
        .filter(InvoiceException.tenant_id == tid, InvoiceException.created_at.between(fd_dt, td_dt))
        .group_by(InvoiceException.code)
        .order_by(func.count(InvoiceException.id).desc())
        .limit(10)
        .all()
    )

    # Mean time to approval (approved invoices)
    approved = (
        db.query(
            func.avg(
                extract("epoch", Approval.decided_at) - extract("epoch", Invoice.created_at)
            ).label("avg_seconds")
        )
        .join(Invoice, Approval.invoice_id == Invoice.id)
        .filter(Approval.tenant_id == tid, Approval.decision == "APPROVED")
        .filter(Invoice.created_at.between(fd_dt, td_dt))
        .scalar()
    )

    # Mean time to resolve exceptions
    resolved = (
        db.query(
            func.avg(
                extract("epoch", InvoiceException.resolved_at) - extract("epoch", InvoiceException.created_at)
            ).label("avg_seconds")
        )
        .filter(
            InvoiceException.tenant_id == tid,
            InvoiceException.resolved_at.isnot(None),
            InvoiceException.created_at.between(fd_dt, td_dt),
        )
        .scalar()
    )

    # Clean invoice percentage
    total_inv = db.query(func.count(Invoice.id)).filter(Invoice.tenant_id == tid, Invoice.created_at.between(fd_dt, td_dt)).scalar() or 0
    inv_with_exc = db.query(func.count(func.distinct(InvoiceException.invoice_id))).filter(
        InvoiceException.tenant_id == tid, InvoiceException.created_at.between(fd_dt, td_dt)
    ).scalar() or 0

    return {
        "exception_rate_over_time": [
            {"week": r.week.isoformat() if r.week else "", "count": r.count} for r in exc_over_time
        ],
        "top_exception_codes": [{"code": r.code, "count": r.count} for r in top_codes],
        "mean_time_to_approval_hours": round(float(approved or 0) / 3600, 1),
        "mean_time_to_resolve_hours": round(float(resolved or 0) / 3600, 1),
        "clean_invoice_pct": round((total_inv - inv_with_exc) / total_inv * 100, 1) if total_inv > 0 else 0,
        "total_invoices_in_range": total_inv,
    }


@router.get("/ingestion")
def ingestion_analytics(
    from_date: str | None = None,
    to_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = current_user.tenant_id
    fd = _parse_date(from_date, 90)
    td = _parse_date(to_date, 0) if to_date else date.today()
    fd_dt = datetime(fd.year, fd.month, fd.day, tzinfo=UTC)
    td_dt = datetime(td.year, td.month, td.day, 23, 59, 59, tzinfo=UTC)

    # Emails processed per day
    daily = (
        db.query(
            func.date_trunc("day", IngestionRun.run_started_at).label("day"),
            func.sum(IngestionRun.emails_processed).label("processed"),
            func.sum(IngestionRun.failures_count).label("failures"),
            func.sum(IngestionRun.retries_count).label("retries"),
        )
        .filter(IngestionRun.run_started_at.between(fd_dt, td_dt))
        .filter((IngestionRun.tenant_id == tid) | (IngestionRun.tenant_id.is_(None)))
        .group_by("day")
        .order_by("day")
        .all()
    )

    # Retry distribution
    retry_dist = (
        db.query(IngestionRun.retries_count, func.count(IngestionRun.id))
        .filter(IngestionRun.run_started_at.between(fd_dt, td_dt))
        .filter((IngestionRun.tenant_id == tid) | (IngestionRun.tenant_id.is_(None)))
        .group_by(IngestionRun.retries_count)
        .order_by(IngestionRun.retries_count)
        .all()
    )

    total_processed = sum(r.processed or 0 for r in daily)
    total_failures = sum(r.failures or 0 for r in daily)

    return {
        "daily": [
            {
                "day": r.day.isoformat() if r.day else "",
                "processed": int(r.processed or 0),
                "failures": int(r.failures or 0),
                "retries": int(r.retries or 0),
                "failure_rate": round(int(r.failures or 0) / max(1, int(r.processed or 0)) * 100, 1),
            }
            for r in daily
        ],
        "retry_distribution": [{"retries": r[0], "count": r[1]} for r in retry_dist],
        "total_processed": int(total_processed),
        "total_failures": int(total_failures),
        "overall_failure_rate": round(total_failures / max(1, total_processed) * 100, 1),
    }


@router.get("/audit-effectiveness")
def audit_effectiveness(
    from_date: str | None = None,
    to_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = current_user.tenant_id
    fd = _parse_date(from_date, 180)
    td = _parse_date(to_date, 0) if to_date else date.today()
    fd_dt = datetime(fd.year, fd.month, fd.day, tzinfo=UTC)
    td_dt = datetime(td.year, td.month, td.day, 23, 59, 59, tzinfo=UTC)

    # Approvals per approver
    per_approver = (
        db.query(Approval.decided_by_user_id, func.count(Approval.id))
        .filter(Approval.tenant_id == tid, Approval.decided_at.between(fd_dt, td_dt))
        .group_by(Approval.decided_by_user_id)
        .all()
    )

    # Rejection rate
    total_decisions = db.query(func.count(Approval.id)).filter(Approval.tenant_id == tid, Approval.decided_at.between(fd_dt, td_dt)).scalar() or 0
    rejections = db.query(func.count(Approval.id)).filter(Approval.tenant_id == tid, Approval.decision == "REJECTED", Approval.decided_at.between(fd_dt, td_dt)).scalar() or 0

    # Manual edits vs automatic (count audit events)
    manual_edits = db.query(func.count(AuditEvent.id)).filter(
        AuditEvent.tenant_id == tid, AuditEvent.action.in_(["INVOICE_UPLOADED", "INVOICE_MANUAL_EDIT"]),
        AuditEvent.timestamp.between(fd_dt, td_dt),
    ).scalar() or 0
    auto_extractions = db.query(func.count(AuditEvent.id)).filter(
        AuditEvent.tenant_id == tid, AuditEvent.action.in_(["EMAIL_RECEIVED", "INVOICE_AUTO_EXTRACTED"]),
        AuditEvent.timestamp.between(fd_dt, td_dt),
    ).scalar() or 0

    # Look up user names
    from app.models.user import User as UserModel
    user_map = {}
    if per_approver:
        user_ids = [uid for uid, _ in per_approver]
        users = db.query(UserModel).filter(UserModel.id.in_(user_ids)).all()
        user_map = {str(u.id): u.full_name or u.email for u in users}

    return {
        "approvals_per_approver": [
            {"user_id": str(uid), "name": user_map.get(str(uid), "Unknown"), "count": cnt}
            for uid, cnt in per_approver
        ],
        "total_decisions": total_decisions,
        "rejections": rejections,
        "rejection_rate": round(rejections / max(1, total_decisions) * 100, 1),
        "manual_edits": manual_edits,
        "auto_extractions": auto_extractions,
    }
