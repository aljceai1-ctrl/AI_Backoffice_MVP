"""Export service — generates payment pack CSV.

Only APPROVED invoices are included.  This is a read-only export;
no autopay or payment execution is performed or triggered.
"""

import csv
import io
import logging
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.models.invoice import Invoice

logger = logging.getLogger(__name__)

_CSV_COLUMNS = [
    "vendor",
    "invoice_number",
    "amount",
    "currency",
    "due_date",
    "storage_path",
]


def generate_payment_pack(
    db: Session,
    from_date: date,
    to_date: date,
) -> tuple[str, int]:
    """Build a CSV string of APPROVED invoices created within the date range.

    The date range is inclusive and filters on ``invoices.created_at`` (UTC).

    Args:
        db:        Active session.
        from_date: Start of range (inclusive).
        to_date:   End of range (inclusive).

    Returns:
        Tuple of (csv_content_string, row_count).
    """
    from_dt = datetime(from_date.year, from_date.month, from_date.day, tzinfo=UTC)
    to_dt = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59, tzinfo=UTC)

    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.status == "APPROVED",
            Invoice.created_at >= from_dt,
            Invoice.created_at <= to_dt,
        )
        .order_by(Invoice.due_date.asc().nullslast(), Invoice.created_at.asc())
        .all()
    )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()

    for inv in invoices:
        writer.writerow(
            {
                "vendor": inv.vendor or "",
                "invoice_number": inv.invoice_number or "",
                "amount": str(inv.amount) if inv.amount is not None else "",
                "currency": inv.currency or "",
                "due_date": inv.due_date or "",
                "storage_path": inv.storage_path,
            }
        )

    row_count = len(invoices)
    logger.info(
        "Payment pack: %d approved invoice(s) from %s to %s",
        row_count,
        from_date,
        to_date,
    )
    return output.getvalue(), row_count
