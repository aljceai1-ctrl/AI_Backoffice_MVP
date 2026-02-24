"""Invoice validation service: runs rules and creates InvoiceException records."""
from app.models.invoice import Invoice
from app.models.invoice_exception import InvoiceException
from app.models.tenant import Tenant


def validate_invoice(invoice: Invoice, tenant: Tenant | None = None) -> list[InvoiceException]:
    """Run all validation rules against an invoice. Returns list of exceptions (not yet committed)."""
    exceptions: list[InvoiceException] = []

    # Required fields
    if not invoice.vendor or not invoice.vendor.strip():
        exceptions.append(InvoiceException(
            invoice_id=invoice.id, code="MISSING_VENDOR",
            message="Vendor name is required", severity="ERROR",
        ))

    if not invoice.invoice_number or not invoice.invoice_number.strip():
        exceptions.append(InvoiceException(
            invoice_id=invoice.id, code="MISSING_NUMBER",
            message="Invoice number is required", severity="ERROR",
        ))

    if invoice.invoice_date is None:
        exceptions.append(InvoiceException(
            invoice_id=invoice.id, code="MISSING_DATE",
            message="Invoice date is required", severity="ERROR",
        ))

    if invoice.amount is None:
        exceptions.append(InvoiceException(
            invoice_id=invoice.id, code="MISSING_AMOUNT",
            message="Invoice amount is required", severity="ERROR",
        ))
    elif float(invoice.amount) <= 0:
        exceptions.append(InvoiceException(
            invoice_id=invoice.id, code="INVALID_AMOUNT",
            message="Invoice amount must be positive", severity="ERROR",
        ))

    # Currency check
    allowed = ["AED", "USD", "EUR", "GBP"]
    if tenant and tenant.allowed_currencies:
        allowed = [c.strip() for c in tenant.allowed_currencies.split(",")]
    if invoice.currency and invoice.currency not in allowed:
        exceptions.append(InvoiceException(
            invoice_id=invoice.id, code="INVALID_CURRENCY",
            message=f"Currency '{invoice.currency}' not in allowed list: {allowed}", severity="ERROR",
        ))

    # File check
    if not invoice.file_path:
        exceptions.append(InvoiceException(
            invoice_id=invoice.id, code="MISSING_FILE",
            message="No file attached to invoice", severity="WARNING",
        ))

    return exceptions
