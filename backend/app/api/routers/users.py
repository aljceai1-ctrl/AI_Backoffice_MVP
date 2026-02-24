"""User management endpoints (admin only)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models.audit_event import AuditEvent
from app.models.user import Role, User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN.value)),
):
    users = db.query(User).filter(User.tenant_id == current_user.tenant_id).all()
    return [_to_response(u) for u in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN.value)),
):
    if body.role not in [r.value for r in Role]:
        raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        tenant_id=current_user.tenant_id,
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(user)
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="USER_CREATED",
        entity_type="user",
        entity_id=str(user.id),
        metadata_json={"email": body.email, "role": body.role},
    ))
    db.commit()
    db.refresh(user)
    return _to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(Role.ADMIN.value)),
):
    user = db.query(User).filter(User.id == user_id, User.tenant_id == current_user.tenant_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        if body.role not in [r.value for r in Role]:
            raise HTTPException(status_code=400, detail=f"Invalid role: {body.role}")
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    db.add(AuditEvent(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
        action="USER_UPDATED",
        entity_type="user",
        entity_id=str(user.id),
    ))
    db.commit()
    db.refresh(user)
    return _to_response(user)


def _to_response(u: User) -> UserResponse:
    return UserResponse(
        id=str(u.id),
        email=u.email,
        full_name=u.full_name,
        role=u.role,
        is_active=u.is_active,
        tenant_id=str(u.tenant_id),
        created_at=u.created_at.isoformat() if u.created_at else "",
    )
