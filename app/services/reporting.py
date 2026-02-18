"""Reporting service — generates the weekly finance ops pack in Markdown."""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.exception import InvoiceException
from app.models.invoice import Invoice

logger = logging.getLogger(__name__)

_STATUS_LABELS: Dict[str, str] = {
    "NEW": "Received (New)",
    "EXTRACTED": "Extracted",
    "VALIDATED": "Validated",
    "APPROVAL_PENDING": "Pending Approval",
    "APPROVED": "Approved",
    "REJECTED": "Rejected",
}


def generate_weekly_pack(db: Session, week_start: date) -> str:
    """Produce a Markdown weekly finance ops report.

    Covers the 7-day period starting on ``week_start`` (Mon–Sun recommended).

    Args:
        db:         Active session.
        week_start: The first day (inclusive) of the report week.

    Returns:
        Markdown string suitable for direct rendering or email.
    """
    week_end = week_start + timedelta(days=6)
    from_dt = datetime(week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc)
    to_dt = datetime(week_end.year, week_end.month, week_end.day, 23, 59, 59, tzinfo=timezone.utc)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── 1. Status counts ─────────────────────────────────────────────────────
    status_counts: Dict[str, int] = {s: 0 for s in _STATUS_LABELS}
    rows = (
        db.query(Invoice.status, func.count(Invoice.id).label("cnt"))
        .filter(Invoice.created_at >= from_dt, Invoice.created_at <= to_dt)
        .group_by(Invoice.status)
        .all()
    )
    for row in rows:
        if row.status in status_counts:
            status_counts[row.status] = row.cnt
    total = sum(status_counts.values())

    # ── 2. Exceptions breakdown ───────────────────────────────────────────────
    exc_rows = (
        db.query(InvoiceException.type, func.count(InvoiceException.id).label("cnt"))
        .join(Invoice, Invoice.id == InvoiceException.invoice_id)
        .filter(Invoice.created_at >= from_dt, Invoice.created_at <= to_dt)
        .group_by(InvoiceException.type)
        .order_by(func.count(InvoiceException.id).desc())
        .all()
    )

    # ── 3. Top 10 pending approval by amount ─────────────────────────────────
    top_pending = (
        db.query(Invoice)
        .filter(
            Invoice.status == "APPROVAL_PENDING",
            Invoice.created_at >= from_dt,
            Invoice.created_at <= to_dt,
        )
        .order_by(Invoice.amount.desc().nullslast())
        .limit(10)
        .all()
    )

    # ── Build Markdown ────────────────────────────────────────────────────────
    lines = [
        "# Weekly Finance Ops Pack",
        "",
        f"**Week:** {week_start.isoformat()} → {week_end.isoformat()}  ",
        f"**Generated:** {generated_at}",
        "",
        "---",
        "",
        "## 1. Invoice Summary",
        "",
        "| Status | Count |",
        "|--------|------:|",
    ]
    for status, label in _STATUS_LABELS.items():
        lines.append(f"| {label} | {status_counts[status]} |")
    lines += [
        f"| **Total** | **{total}** |",
        "",
        "---",
        "",
        "## 2. Exceptions Breakdown",
        "",
    ]
    if exc_rows:
        lines += ["| Exception Type | Count |", "|----------------|------:|"]
        for row in exc_rows:
            lines.append(f"| `{row.type}` | {row.cnt} |")
    else:
        lines.append("_No exceptions recorded this week._")

    lines += [
        "",
        "---",
        "",
        "## 3. Top 10 Invoices Pending Approval (by Amount)",
        "",
    ]
    if top_pending:
        lines += [
            "| # | Vendor | Invoice # | Amount | Currency | Due Date |",
            "|---|--------|-----------|-------:|---------:|----------|",
        ]
        for i, inv in enumerate(top_pending, 1):
            lines.append(
                f"| {i} | {inv.vendor or '—'} | {inv.invoice_number or '—'} "
                f"| {inv.amount or '—'} | {inv.currency or '—'} | {inv.due_date or '—'} |"
            )
    else:
        lines.append("_No invoices pending approval this week._")

    lines += [
        "",
        "---",
        "",
        "## 4. Recommended Actions",
        "",
        "1. **Approve / Reject** all `APPROVAL_PENDING` invoices listed above before payment cut-off.",
        "2. **Resolve open exceptions** — especially `MISSING_FIELD` and `DUPLICATE_INVOICE` items.",
        "3. **Export payment pack** once approvals are complete: `GET /payment-pack.csv?from=...&to=...`",
        "4. **Escalate** any `INVALID_AMOUNT` or `INVALID_CURRENCY` exceptions to the finance team.",
        "",
        "---",
        "",
        "## 5. Audit Summary",
        "",
        f"- **Reporting period:** {from_dt.strftime('%Y-%m-%d %H:%M UTC')} – {to_dt.strftime('%Y-%m-%d %H:%M UTC')}",
        "- **Data source:** AI Backoffice MVP — PostgreSQL `invoices`, `invoice_exceptions`, `audit_events`",
        "- **Report generated by:** system / reporting service",
        "",
        "_This report is auto-generated. Verify all figures against source invoices before taking action._",
    ]

    return "\n".join(lines)
