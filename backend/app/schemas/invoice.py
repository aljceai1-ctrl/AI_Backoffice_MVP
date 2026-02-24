from pydantic import BaseModel


class InvoiceUploadMeta(BaseModel):
    vendor: str = ""
    invoice_number: str = ""
    invoice_date: str | None = None
    amount: float | None = None
    currency: str = "AED"


class ExceptionResponse(BaseModel):
    id: str
    code: str
    message: str
    severity: str
    created_at: str
    resolved_at: str | None = None

    class Config:
        from_attributes = True


class ApprovalResponse(BaseModel):
    id: str
    decided_by_user_id: str
    decision: str
    decided_at: str
    notes: str

    class Config:
        from_attributes = True


class PaymentBrief(BaseModel):
    id: str
    paid_amount: float
    paid_currency: str
    paid_at: str
    payment_method: str
    reference: str

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: str
    tenant_id: str
    vendor: str
    invoice_number: str
    invoice_date: str | None = None
    amount: float | None = None
    currency: str
    status: str
    source: str
    original_filename: str
    created_at: str
    updated_at: str
    exceptions: list[ExceptionResponse] = []
    approvals: list[ApprovalResponse] = []
    payments: list[PaymentBrief] = []

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
