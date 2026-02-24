"""Export endpoints: payment pack CSV, weekly report markdown."""
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment
from app.models.user import User

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/payment-pack.csv")
def payment_pack_csv(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = current_user.tenant_id
    fd = date.fromisoformat(from_date)
    td = date.fromisoformat(to_date)
    fd_dt = datetime(fd.year, fd.month, fd.day, tzinfo=UTC)
    td_dt = datetime(td.year, td.month, td.day, 23, 59, 59, tzinfo=UTC)

    rows = (
        db.query(Invoice, Payment)
        .join(Payment, Payment.invoice_id == Invoice.id)
        .filter(Invoice.tenant_id == tid, Payment.paid_at.between(fd_dt, td_dt))
        .all()
    )

    lines = ["invoice_number,vendor,amount,currency,paid_amount,paid_currency,paid_at,payment_method,reference"]
    for inv, pay in rows:
        lines.append(
            f"{inv.invoice_number},{inv.vendor},{inv.amount},{inv.currency},"
            f"{pay.paid_amount},{pay.paid_currency},{pay.paid_at.isoformat() if pay.paid_at else ''},"
            f"{pay.payment_method},{pay.reference}"
        )

    return PlainTextResponse("\n".join(lines), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=payment-pack-{from_date}-{to_date}.csv"})


@router.get("/weekly-pack.md")
def weekly_pack_md(
    week_start: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tid = current_user.tenant_id
    ws = date.fromisoformat(week_start)
    we = ws + __import__("datetime").timedelta(days=7)
    ws_dt = datetime(ws.year, ws.month, ws.day, tzinfo=UTC)
    we_dt = datetime(we.year, we.month, we.day, tzinfo=UTC)

    invoices = db.query(Invoice).filter(Invoice.tenant_id == tid, Invoice.created_at.between(ws_dt, we_dt)).all()
    payments = (
        db.query(Payment).join(Invoice, Payment.invoice_id == Invoice.id)
        .filter(Invoice.tenant_id == tid, Payment.paid_at.between(ws_dt, we_dt))
        .all()
    )

    md = f"# Weekly Report: {ws.isoformat()} to {we.isoformat()}\n\n"
    md += f"## Invoices\n\n"
    md += f"- Total received: {len(invoices)}\n"
    status_counts: dict[str, int] = {}
    for inv in invoices:
        status_counts[inv.status] = status_counts.get(inv.status, 0) + 1
    for s, c in sorted(status_counts.items()):
        md += f"- {s}: {c}\n"

    md += f"\n## Payments\n\n"
    md += f"- Total payments: {len(payments)}\n"
    total_paid = sum(float(p.paid_amount) for p in payments)
    md += f"- Total amount paid: {total_paid:,.2f}\n"

    md += f"\n---\n*Generated at {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}*\n"

    return PlainTextResponse(md, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=weekly-pack-{week_start}.md"})
