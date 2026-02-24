from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str = ""
    role: str = "VIEWER"


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    tenant_id: str
    created_at: str

    class Config:
        from_attributes = True
