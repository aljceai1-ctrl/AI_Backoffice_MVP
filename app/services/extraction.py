"""Extraction service — applies structured fields to an invoice record.

Current implementation: manual field ingestion via the /extract endpoint.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FUTURE INTEGRATION POINT — LLM / OCR Extraction
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
To add automated extraction:

1. Create ``_automated_extract(storage_path: str) -> InvoiceExtract`` that
   calls your chosen OCR / LLM API and returns a populated InvoiceExtract.

2. In ``extract_fields``, call ``_automated_extract`` when the ``fields``
   argument is not supplied (or always, depending on your product decision).

3. Pass the model's confidence score as ``confidence`` when calling the
   audit service in the router.

The interface is intentionally thin so this swap-in is trivial.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import logging

from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceExtract

logger = logging.getLogger(__name__)


def extract_fields(db: Session, invoice: Invoice, fields: InvoiceExtract) -> Invoice:
    """Apply extracted field values to ``invoice`` and advance its status.

    Only fields that were explicitly set in the request payload are written,
    so partial updates work correctly (``exclude_unset=True``).

    Args:
        db:      Active session.
        invoice: Invoice ORM object to update.
        fields:  Validated extraction payload from the API caller.

    Returns:
        The mutated (flushed) Invoice.
    """
    updates = fields.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        setattr(invoice, field_name, value)

    # Persist the raw extraction payload for auditability / re-processing
    invoice.extracted_json = {
        k: str(v) if v is not None else None for k, v in updates.items()
    }
    invoice.status = "EXTRACTED"
    db.flush()

    logger.info(
        "Invoice %s: extracted fields %s",
        invoice.id,
        list(updates.keys()),
    )
    return invoice
