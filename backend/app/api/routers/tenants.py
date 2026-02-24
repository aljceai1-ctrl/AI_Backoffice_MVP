"""Tenant settings endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.tenant import Tenant
from app.models.user import Role, User

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantSettingsResponse(BaseModel):
    id: str
    name: str
    inbound_email_alias: str
    allowed_currencies: str
    created_at: str


class TenantSettingsUpdate(BaseModel):
    name: str | None = None
    allowed_currencies: str | None = None


@router.get("/settings", response_model=TenantSettingsResponse)
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(require_roles(Role.ADMIN.value))):
    t = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantSettingsResponse(
        id=str(t.id), name=t.name, inbound_email_alias=t.inbound_email_alias,
        allowed_currencies=t.allowed_currencies or "",
        created_at=t.created_at.isoformat() if t.created_at else "",
    )


@router.patch("/settings", response_model=TenantSettingsResponse)
def update_settings(
    body: TenantSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN.value)),
):
    t = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if body.name is not None:
        t.name = body.name
    if body.allowed_currencies is not None:
        t.allowed_currencies = body.allowed_currencies
    db.commit()
    db.refresh(t)
    return TenantSettingsResponse(
        id=str(t.id), name=t.name, inbound_email_alias=t.inbound_email_alias,
        allowed_currencies=t.allowed_currencies or "",
        created_at=t.created_at.isoformat() if t.created_at else "",
    )
