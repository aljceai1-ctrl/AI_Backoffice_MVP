from pydantic import BaseModel


class PaymentCreate(BaseModel):
    invoice_id: str
    paid_amount: float
    paid_currency: str = "AED"
    payment_method: str = ""
    reference: str = ""


class PaymentResponse(BaseModel):
    id: str
    tenant_id: str
    invoice_id: str
    paid_amount: float
    paid_currency: str
    paid_at: str
    payment_method: str
    reference: str
    created_by_user_id: str | None = None
    created_at: str

    class Config:
        from_attributes = True
